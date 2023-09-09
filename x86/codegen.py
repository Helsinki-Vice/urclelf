from dataclasses import dataclass
import enum
import struct
import math
from typing import Literal, Self
from x86.machine import Register, ModRegRM, Opcode, X86Instruction, AddressingMode, InstructionPrefixes, ScaleIndexByte, ThreeBits
from x86.asm import Mnemonic, EffectiveAddress, ASMInstruction, Program, Label, Operand, Immediate
from error import Traceback, Message

LINUX_WRITE = 4
LINUX_STDOUT = 1
LINUX_EXIT = 1

@dataclass(frozen=True)
class ImmediateType:
    size: Literal[1, 2, 4]
    is_relative: bool = False

@dataclass(frozen=True)
class RegisterSize:
    size: Literal[8, 16, 32] | None = None

OperandType = RegisterSize | ImmediateType | Register

class CodeGenError(enum.Enum):
    UNKNOWN = enum.auto()
    WRONG_MNEMONIC = enum.auto()
    INCORRECT_OPERAND_COUNT = enum.auto()
    BAD_RM_TYPE = enum.auto()
    BAD_DISPLACEMENT = enum.auto()
    BAD_IMMEDIATE = enum.auto()
    INCORRECT_REGISTER_SIZE = enum.auto()
    INCORRECT_OPERAND_TYPE = enum.auto()

def match_operand(operand: Operand, operand_type: OperandType):

    if isinstance(operand_type, RegisterSize):
        return operand.get_register_size() == operand_type.size
    elif isinstance(operand_type, ImmediateType):
        if not isinstance(operand.value, int):
            return False
        return True
    else:
        return operand.value == operand_type

@dataclass
class InstructionEncoding:
    mnemonic: Mnemonic
    opcode: Opcode
    opcode_extention: ThreeBits | None
    operands: list[OperandType]
    
    @staticmethod
    def from_str(encoding: str):

        opcode = Opcode(False, 0)
        if ":" not in encoding:
            return Traceback.new(f"Encoding '{encoding}' is missing ':'")
        opcode_str, rest = encoding.split(":", maxsplit=1)
        if "." in opcode_str:
            opcode_str, opcode_extention_str = opcode_str.split(".", maxsplit=1)
            opcode_extention = int(opcode_extention_str)
            if not (opcode_extention == 0 or opcode_extention == 1 or opcode_extention == 2 or opcode_extention == 3 or opcode_extention == 4 or opcode_extention == 5 or opcode_extention == 6 or opcode_extention == 7):
                return Traceback.new(f"Opcode '{opcode_str}' has invalid extention {opcode_extention}")
        else:
            opcode_extention = None
        opcode = Opcode.from_bytes(bytes.fromhex(opcode_str))
        rest = rest.split()
        if not rest:
            return Traceback.new(f"Encoding of opcode {bytes(opcode).hex()} is missing")
        mnemonic_str, *operands = rest
        mnemonic = Mnemonic(mnemonic_str)
        operand_formats: list[OperandType] = []
        for operand in operands:
            reg = Register.from_name(operand)
            if reg:
                operand_formats.append(reg)
            elif operand == "r":
                operand_formats.append(RegisterSize(32 if opcode.get_register_size_bit() else 8))
            elif operand == "r8":
                operand_formats.append(RegisterSize(8))
            elif operand == "r16": #FIXME: 16-bit does not work yet
                operand_formats.append(RegisterSize(16))
            elif operand == "r32":
                operand_formats.append(RegisterSize(32))
            elif operand == "i8":
                operand_formats.append(ImmediateType(1, False))
            elif operand == "i16":
                operand_formats.append(ImmediateType(2, False))
            elif operand == "i32":
                operand_formats.append(ImmediateType(4, False))
            elif operand == "rel8":
                operand_formats.append(ImmediateType(1, True))
            elif operand == "rel16":
                operand_formats.append(ImmediateType(2, True))
            elif operand == "rel32":
                operand_formats.append(ImmediateType(4, True))
            elif operand == "es":
                pass
            else:
                return Traceback.new(f"Unknown operand for opcode {bytes(opcode).hex()}: '{operand}'")
        
        return InstructionEncoding(mnemonic, opcode, opcode_extention, operand_formats)
    
    def get_immediate(self):

        for operand_format in self.operands:
            if isinstance(operand_format, ImmediateType):
                return operand_format
    
    def get_regrm_operands(self, instruction: ASMInstruction, direction_bit: bool):

        operands: list[Register | EffectiveAddress] = []
        for index, operand_format in enumerate(self.operands):
            if isinstance(operand_format, RegisterSize):
                # Ignore if it is an immediate or an implied operand
                operand = instruction.operands[index]
                if not isinstance(operand.value, (Register, EffectiveAddress)):
                    return CodeGenError.INCORRECT_OPERAND_TYPE
                if operand.get_register_size() != operand_format.size:
                    return CodeGenError.INCORRECT_REGISTER_SIZE
                operands.append(operand.value)
        
        if not operands:
            return None
        if len(operands) == 1:
            # Ignore direction bit, there's probably an opcode extention in reg anyway
            reg, rm = (None, operands[0])
            return (None, operands[0])
        elif len(operands) == 2:
            # Direction bit swaps the operands, wowsers
            if direction_bit:
                reg, rm = (operands[0], operands[1])
            else:
                reg, rm = (operands[1], operands[0])
    
        else:
            # Too many operands, wtf
            return CodeGenError.INCORRECT_OPERAND_COUNT
        
        if isinstance(reg, EffectiveAddress):
            # Sir this is a Wendy's 💀
            return CodeGenError.INCORRECT_OPERAND_TYPE
        
        if isinstance(rm, EffectiveAddress):
            if rm.base:
                #NOTE: We are assuming the cpu is not in real or long mode
                if rm.base.value.size != 32:
                    return CodeGenError.INCORRECT_REGISTER_SIZE
        else:
            if reg.value.size != rm.value.size:
                return CodeGenError.INCORRECT_REGISTER_SIZE

        return reg, rm

def calculate_mod(rm_operand: Register | EffectiveAddress) -> AddressingMode | None:
    
    if isinstance(rm_operand, Register):
        return AddressingMode.DIRECT
    if not isinstance(rm_operand.displacement, int):
        return None
    elif rm_operand.displacement == 0 or (rm_operand.base is None and rm_operand.index is None and rm_operand.displacement >= -0x80000000 and rm_operand.displacement < 0x80000000):
        return AddressingMode.INDIRECT
    elif rm_operand.displacement >= -0x80 and rm_operand.displacement < 0x80:
        return AddressingMode.INDIRECT_WITH_BYTE_DISPLACEMENT
    elif rm_operand.displacement >= -0x80000000 and rm_operand.displacement < 0x80000000:
        return AddressingMode.INDIRECT_WITH_FOUR_BYTE_DISPACEMENT
    else:
        return None
    

def calculate_reg(operand: Register | EffectiveAddress | None, opcode_extention: Literal[0, 1, 2, 3, 4, 5, 6, 7] | None) -> ThreeBits | None:
    
    if opcode_extention is not None:
        return opcode_extention
    elif isinstance(operand, Register):
        return operand.value.code
    elif isinstance(operand, EffectiveAddress):
        return None
    else:
        return None

def get_rm_code(effective_address: EffectiveAddress):

    if effective_address.index is not None:
        return 4
    elif effective_address.displacement and (effective_address.base is None):
        return 5
    elif effective_address.base:
        return effective_address.base.value.code
    else:
        return None

def calculate_rm(operand: Register | EffectiveAddress | None) -> ThreeBits | None:
    
    if isinstance(operand, EffectiveAddress):
        return get_rm_code(operand)
    elif isinstance(operand, Register):
        return operand.value.code
    else:
        return None

def calculate_modregrm(register: Register | None, register_or_memory: Register | EffectiveAddress | None, opcode_extention: ThreeBits | None) -> ModRegRM | None:
    
    if register_or_memory is None:
        return None
    mod = calculate_mod(register_or_memory)
    reg = calculate_reg(register, opcode_extention)
    rm = calculate_rm(register_or_memory)
    if mod is None or reg is None or rm is None:
        return None
    return ModRegRM(mod, reg, rm)

def calculate_sib_scale(effective_address: EffectiveAddress):

    scale = round(math.log2(effective_address.scale))
    # Don't change to "scale in [0, 1, 2, 3]"" or pylance will get mad 
    if scale == 0 or scale == 1 or scale == 2 or scale == 3:
        return scale
    
def calculate_sib_index(effective_address: EffectiveAddress):

    if effective_address.base == Register.ESP and effective_address.index is None:
        return 4 # Special case for [esp] addressing
    if effective_address.index is None:
        return None
    index = effective_address.index.value.code
    if index == 4: # Technically it's register eiz but that's too bad
        return None
    
    return index

def calculate_sib_base(effective_address: EffectiveAddress, mod: AddressingMode) -> Literal[0, 1, 2, 3, 4, 5, 6, 7, None]:

    if effective_address.base is None:
        return 5 # Tells the cpu to look for 32 bit displacement
    
    return effective_address.base.value.code

def calculate_sib(effective_address: EffectiveAddress | Register | None, mod_reg_rm: ModRegRM | None) -> ScaleIndexByte | None:

    if mod_reg_rm is None:
        return None
    if not (mod_reg_rm.mod != AddressingMode.DIRECT and mod_reg_rm.rm == 4):
        return None
    if not isinstance(effective_address, EffectiveAddress):
        return None
    scale = calculate_sib_scale(effective_address)
    index = calculate_sib_index(effective_address)
    base = calculate_sib_base(effective_address, mod_reg_rm.mod)
    
    if scale is None or index is None or base is None:
        return None
    return ScaleIndexByte(scale, index, base)

def calculate_displacement(effective_address: Register | EffectiveAddress | None, mod_reg_rm: ModRegRM | None, sib: ScaleIndexByte | None):

    if not isinstance(effective_address, EffectiveAddress):
        return bytes()
    displacement = effective_address.displacement
    if mod_reg_rm:
        mod = mod_reg_rm.mod
        rm = mod_reg_rm.rm
        if mod == AddressingMode.INDIRECT_WITH_BYTE_DISPLACEMENT:
            return struct.pack("<b", displacement)
        elif mod == AddressingMode.INDIRECT_WITH_FOUR_BYTE_DISPACEMENT:
            return struct.pack("<i", displacement)
        elif mod == AddressingMode.INDIRECT and rm == 5:
            return struct.pack("<i", displacement)
        else:
            return bytes()
    
    assert(not sib)
    
    return bytes()

def encode_immediate(immediate_value: Immediate | None, immediate_type: ImmediateType | None, immediate_address: int):

    if immediate_type is None:
        return bytes()
    if not isinstance(immediate_value, int):
        return None
    instruction_end_address = immediate_address + immediate_type.size
    immediate_value_relative = immediate_value - instruction_end_address if immediate_type.is_relative else immediate_value
    if immediate_type.size == 1:
        if ((immediate_value_relative < -0x80 or immediate_value_relative >= 0x0100) and not immediate_type.is_relative) or ((immediate_value_relative < -0x80 or immediate_value_relative >= 0x80) and immediate_type.is_relative):
            return None
        return struct.pack("<b", ((immediate_value_relative + 128) % 256) - 128)
    elif immediate_type.size == 2:
        if (immediate_value_relative < -0x8000 or immediate_value_relative >= 0x8000):
            return None
        return struct.pack("<h", immediate_value_relative)
    else:
        if ((immediate_value_relative < -0x80000000 or immediate_value_relative >= 0x0100000000) and not immediate_type.is_relative) or ((immediate_value_relative < -0x80000000 or immediate_value_relative >= 0x80000000) and immediate_type.is_relative):
            return None
        return struct.pack("<i", ((immediate_value_relative + 2**31) % 2**32) - 2**31)


def encode_instruction_using_encoding(instruction: ASMInstruction, encoding: InstructionEncoding, instruction_address: int) -> X86Instruction | CodeGenError:
    if instruction.mnemonic != encoding.mnemonic:
        return CodeGenError.WRONG_MNEMONIC
    if len(instruction.operands) != len(encoding.operands):
        return CodeGenError.INCORRECT_OPERAND_COUNT
    
    prefixes = InstructionPrefixes(None, False, False, None)
    
    regrm_operands = encoding.get_regrm_operands(instruction, encoding.opcode.get_direction_bit())
    if isinstance(regrm_operands, CodeGenError):
        return regrm_operands
    elif regrm_operands is None:
        register, register_or_memory = None, None
        mod_reg_rm = None
    else:
        register, register_or_memory = regrm_operands
        mod_reg_rm = calculate_modregrm(register, register_or_memory, encoding.opcode_extention)
    sib = calculate_sib(register_or_memory, mod_reg_rm)
    
    displacement = calculate_displacement(register_or_memory, mod_reg_rm, sib)
    
    instruction_address += len(bytes(prefixes))
    instruction_address += len(bytes(encoding.opcode))
    if mod_reg_rm:
        instruction_address += len(bytes(mod_reg_rm))
    if sib:
        instruction_address += len(bytes(sib))
    instruction_address += len(displacement)

    immediate = encode_immediate(instruction.get_immediate(), encoding.get_immediate(), instruction_address)
    if immediate is None:
        return CodeGenError.BAD_IMMEDIATE
    
    for index in range(len(encoding.operands)):
        if not match_operand(instruction.operands[index], encoding.operands[index]):
            return CodeGenError.INCORRECT_OPERAND_TYPE

    return X86Instruction(prefixes, encoding.opcode, mod_reg_rm, sib, displacement, immediate)

@dataclass
class CodeGenIteration:
    origin: int
    instructions: list[ASMInstruction | Label]
    instruction_addresses: list[int]
    instruction_lengths: list[int]
    labels: dict[str, int]

    @classmethod
    def from_assembly(cls, program: Program) -> Self:

        instructions: list[ASMInstruction | Label] = []
        labels: dict[str, int] = {}
        for instruction in program.code:
            instructions.append(instruction)
            if isinstance(instruction, Label):
                labels.update({instruction.name: 0})
        
        return CodeGenIteration(program.entry_point, instructions, [0] * len(instructions), [0] * len(instructions), labels)
    
    def as_bytes(self):

        current_address = self.origin
        machine_code_bytes = bytes()
        for instruction in self.instructions:
            if isinstance(instruction, Label):
                continue
            instruction_with_labels_resolved = ASMInstruction(instruction.mnemonic, [])
            for operand in instruction.operands:
                if isinstance(operand.value, Label):
                    address = self.labels.get(operand.value.name)
                    if address is None:
                        address = 0
                    instruction_with_labels_resolved.operands.append(Operand(address))
                else:
                    instruction_with_labels_resolved.operands.append(operand)
            machine_instruction = encode(instruction_with_labels_resolved, current_address)
            if not isinstance(machine_instruction, X86Instruction):
                machine_instruction.elaborate(f"Unable to encode instruction '{instruction}'")
                return machine_instruction
            machine_code_bytes += bytes(machine_instruction)
            current_address += len(bytes(machine_instruction))
        
        return machine_code_bytes

    def next(self) -> Self | Traceback:

        next_instructions: list[ASMInstruction | Label] = self.instructions
        next_instruction_addresses: list[int] = []
        next_instruction_sizes: list[int] = []
        next_labels: dict[str, int] = {}
        current_address = self.origin

        for instruction in self.instructions:
            if isinstance(instruction, Label):
                next_labels.update({instruction.name: current_address})
                next_instruction_addresses.append(current_address)
                next_instruction_sizes.append(0)
                continue
            instruction_with_labels_resolved = ASMInstruction(instruction.mnemonic, [])
            for operand in instruction.operands:
                if isinstance(operand.value, Label):
                    address = self.labels.get(operand.value.name)
                    if address is None:
                        address = 0
                    instruction_with_labels_resolved.operands.append(Operand(address))
                else:
                    instruction_with_labels_resolved.operands.append(operand)
            machine_instruction = encode(instruction_with_labels_resolved, current_address)
            if not isinstance(machine_instruction, X86Instruction):
                machine_instruction.elaborate(f"Unable to encode instruction '{instruction}'")
                return machine_instruction
            machine_code_bytes = bytes(machine_instruction)
            next_instruction_addresses.append(current_address)
            current_address += len(machine_code_bytes)
            next_instruction_sizes.append(len(machine_code_bytes))

        return CodeGenIteration(self.origin, next_instructions, next_instruction_addresses, next_instruction_sizes, next_labels)

def assemble(program: Program) -> bytes | Traceback:
    
    last_iteration = CodeGenIteration.from_assembly(program)
    current_iteration = None
    iteration_count = 0
    while current_iteration != last_iteration:
        if current_iteration:
            last_iteration = current_iteration
        current_iteration = last_iteration.next()
        if isinstance(current_iteration, Traceback):
            error = current_iteration
            error.elaborate("Code does not compile")
            return error
        if iteration_count > 8:
            return Traceback.new("Codegen took too long, aborted.")
        if isinstance(current_iteration, bytes):
            return current_iteration
        iteration_count += 1
    
    assert(current_iteration is not None)
    as_bytes = current_iteration.as_bytes()
    assert(not isinstance(as_bytes, Traceback))
    return as_bytes

def load_instruction_set_data() -> list[InstructionEncoding] | Traceback:

    with open("./x86/isa_data.txt", "r") as file:
        formats = file.read().splitlines()
        encodings: list[InstructionEncoding] = []
        for format in formats:
            encoding = InstructionEncoding.from_str(format)
            if isinstance(encoding, Traceback):
                error = encoding
                error.elaborate(f"x86 ISA data contains an invalid line '{format}'")
                return error
            encodings.append(encoding)
        
        return encodings


def encode(instruction: ASMInstruction, instruction_address: int) -> X86Instruction | Traceback:
    instruction_formats = load_instruction_set_data()
    if isinstance(instruction_formats, Traceback):
        error = instruction_formats
        error.elaborate("x86 ISA data loading failed")
        return error
    smallest_encoding: "X86Instruction | None" = None
    for format in instruction_formats:
        encoded = encode_instruction_using_encoding(instruction, format, instruction_address)
        if isinstance(encoded, X86Instruction):
            if not smallest_encoding:
                smallest_encoding = encoded
            if len(bytes(encoded)) < len(bytes(smallest_encoding)):
                smallest_encoding = encoded
    if smallest_encoding:
        return smallest_encoding
    
    return Traceback.new(f"Cannot encode instruction '{instruction}'")
