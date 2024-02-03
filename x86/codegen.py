from dataclasses import dataclass
import struct
import math
from typing import Literal, Self
from x86.machine import Register, ModRegRM, Opcode, X86Instruction, AddressingMode, InstructionPrefixes, ScaleIndexByte, ThreeBits
from x86.asm import Mnemonic, EffectiveAddress, ASMInstruction, ASMCode, Label, Operand, Immediate
from error import Traceback
from x86.modregrm import calculate_modregrm
from x86.sib import calculate_sib

@dataclass(frozen=True)
class ImmediateType:
    size: Literal[1, 2, 4]
    is_relative: bool = False

@dataclass(frozen=True)
class RegisterSize:
    size: Literal[8, 16, 32] | None = None

OperandType = RegisterSize | ImmediateType | Register

def match_operand(operand: Operand, operand_type: OperandType) -> bool:

    if isinstance(operand_type, RegisterSize):
        if isinstance(operand.value, Register):
            return operand.get_register_size() == operand_type.size
        else:
            return True
    elif isinstance(operand_type, ImmediateType):
        if isinstance(operand.value, int):
            return True
        if isinstance(operand.value, Label):
            return operand_type.size >= 4
        return False
    else:
        return operand.value == operand_type

@dataclass
class Relocation:
    symbol_name: str
    index: int
    size: int
    addend: int
    is_signed: bool
    is_relative: bool

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
                if isinstance(operand.value, Register):
                    if operand.get_register_size() != operand_format.size:
                        return Traceback.new(f"Invalid register size for operand index {index}: exprected {operand_format.size} bits, found {operand.get_register_size()}.")
                    operands.append(operand.value)
                    pass
                elif isinstance(operand.value, EffectiveAddress):
                    operands.append(operand.value)
                    pass
                else:
                    return Traceback.new(f"Expected register or memory operand, found an immediate instead.")
        
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
            return Traceback.new(f"There are too many register/memory operands.")
        
        if isinstance(reg, EffectiveAddress):
            # Sir this is a Wendy's 💀
            return Traceback.new("r/m field can only contain a register.")
        
        if isinstance(rm, EffectiveAddress):
            if rm.base:
                #NOTE: We are assuming the cpu is not in real or long mode
                if rm.base.value.size != 32:
                    return Traceback.new(f"Only 32 bit memory is currently supported.")
        else:
            if reg.value.size != rm.value.size:
                return Traceback.new(f"Register {reg} and {rm} are not the same size.")

        return reg, rm

def calculate_displacement(effective_address: Register | EffectiveAddress | None, mod_reg_rm: ModRegRM | None, sib: ScaleIndexByte | None) -> bytes | Relocation:

    if not isinstance(effective_address, EffectiveAddress):
        return bytes()
    if isinstance(effective_address.displacement, Label):
        return Relocation(effective_address.displacement.name, 0, 4, 0, False, False)
    else:
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
    
    assert not sib
    
    return bytes()

def int_as_bytes(value: int, size: Literal[8, 16, 32], is_signed: bool) -> bytes | Traceback:

    total_values = 2**size
    if is_signed:
        min_value = -(total_values // 2)
        max_value = (total_values // 2) - 1
    else:
        min_value = 0
        max_value = total_values - 1
    
    if (value < min_value) or (value > max_value):
        return Traceback.new(f"Value {value} is not in the range {min_value:#x} thru {max_value:#x})")
    
    symbol = {8: "B", 16: "H", 32: "I"}[size]
    symbol = symbol.lower() if is_signed else symbol
    
    return struct.pack(f"<{symbol}", value)

def encode_immediate(immediate_value: Immediate | None, immediate_type: ImmediateType | None, immediate_address: int) -> bytes | Relocation | Traceback:

    if immediate_type is None or immediate_value is None:
        return bytes()
    if not isinstance(immediate_value, int):
        return Relocation(immediate_value.name, 0, immediate_type.size, 0, True, immediate_type.is_relative)
        #return Traceback.new(f"Label '{immediate_value}' not yet resolved (?)")
        immediate_value = 0
    instruction_end_address = immediate_address + immediate_type.size
    immediate_value_relative = immediate_value - instruction_end_address if immediate_type.is_relative else immediate_value
    binary = int_as_bytes(immediate_value_relative, immediate_type.size * 8, immediate_type.is_relative)
    if isinstance(binary, Traceback):
        error = binary
        error.elaborate("Immediate out of range")
        return error
    
    return binary

def encode_instruction_using_encoding(instruction: ASMInstruction, encoding: InstructionEncoding, instruction_address: int) -> tuple[X86Instruction, list[Relocation], dict[str, int]] | Traceback:

    if instruction.mnemonic != encoding.mnemonic:
        return Traceback.new(f"Wrong Mnemonic {instruction.mnemonic} != {encoding.mnemonic}")
    if len(instruction.operands) != len(encoding.operands):
        return Traceback.new(f"Incorrect operand count of {len(instruction.operands)}, expected {len(encoding.operands)}")
    
    prefixes = InstructionPrefixes.none()
    
    regrm_operands = encoding.get_regrm_operands(instruction, encoding.opcode.get_direction_bit())
    if isinstance(regrm_operands, Traceback):
        error = regrm_operands
        error.elaborate("Cannot generate r/m field, bad operands.")
        return regrm_operands
    elif regrm_operands is None:
        register, register_or_memory = None, None
        mod_reg_rm = None
    else:
        register, register_or_memory = regrm_operands
        mod_reg_rm = calculate_modregrm(register, register_or_memory, encoding.opcode_extention)
        if isinstance(mod_reg_rm, Traceback):
            error = mod_reg_rm
            error.elaborate("Bad modregrm field")
            return error
    sib = calculate_sib(register_or_memory, mod_reg_rm)
    
    displacement = calculate_displacement(register_or_memory, mod_reg_rm, sib)
    if isinstance(displacement, Relocation):
        displacement_relocation = displacement
        displacement_bytes = bytes([0] * displacement.size)
    else:
        displacement_bytes = displacement
        displacement_relocation = None
    
    instruction_address += len(bytes(prefixes))
    instruction_address += len(bytes(encoding.opcode))
    if mod_reg_rm:
        instruction_address += len(bytes(mod_reg_rm))
    if sib:
        instruction_address += len(bytes(sib))
    instruction_address += len(displacement_bytes)

    immediate = encode_immediate(instruction.get_immediate(), encoding.get_immediate(), instruction_address)
    if isinstance(immediate, Relocation):
        immediate_relocation = immediate
        #fixme = encode_immediate(immediate_relocation.addend, encoding.get_immediate(), instruction_address)
        #assert isinstance(fixme, bytes)
        immediate_bytes = bytes.fromhex("fcffffff")
    elif isinstance(immediate, Traceback):
        error = immediate
        error.elaborate(f"Bad immediate {instruction.get_immediate()}")
        return error
    else:
        immediate_relocation = None
        immediate_bytes = bytes(immediate)
    for index in range(len(encoding.operands)):
        if not match_operand(instruction.operands[index], encoding.operands[index]):
            return Traceback.new(f"Operand '{instruction.operands[index]}' is not of the expected type.")

    machine_instruction = X86Instruction(prefixes, encoding.opcode, mod_reg_rm, sib, displacement_bytes, immediate_bytes)
    relocations = []
    if displacement_relocation:
        displacement_relocation.index = machine_instruction.get_displacement_index()
        relocations.append(displacement_relocation)
    if immediate_relocation:
        immediate_relocation.index = machine_instruction.get_immediate_index()
        if immediate_relocation.is_relative:
            immediate_relocation.addend = -(len(bytes(machine_instruction)) - machine_instruction.get_immediate_index())
        relocations.append(immediate_relocation)
    return machine_instruction, relocations, {}

@dataclass
class CodeGenIteration:
    origin: int
    instructions: list[ASMInstruction | Label]
    instruction_addresses: list[int]
    instruction_lengths: list[int]
    labels: dict[str, int]

    @classmethod
    def from_assembly(cls, program: ASMCode) -> Self:

        instructions: list[ASMInstruction | Label] = []
        labels: dict[str, int] = {}
        for instruction in program.code:
            instructions.append(instruction)
            if isinstance(instruction, Label):
                labels.update({instruction.name: 0})
        
        return cls(program.entry_point if program.entry_point else 0, instructions, [0] * len(instructions), [0] * len(instructions), labels)
    
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
            if isinstance(machine_instruction, Traceback):
                machine_instruction.elaborate(f"Unable to encode instruction '{instruction}'")
                return machine_instruction
            machine_code_bytes += bytes(machine_instruction[0])
            current_address += len(bytes(machine_instruction[0]))
        
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
            if isinstance(machine_instruction, Traceback):
                machine_instruction.elaborate(f"Unable to encode instruction '{instruction}'")
                return machine_instruction
            machine_code_bytes = bytes(machine_instruction[0])
            next_instruction_addresses.append(current_address)
            current_address += len(machine_code_bytes)
            next_instruction_sizes.append(len(machine_code_bytes))

        return self.__class__(self.origin, next_instructions, next_instruction_addresses, next_instruction_sizes, next_labels)


@dataclass
class CodegenOutput:
    binary: bytes
    relocations: list[Relocation]
    labels: dict[str, int]

    def get_undefined_label_names(self):

        undefined_symbol_names: list[str] = []
        for relocation in self.relocations:
            if relocation.symbol_name not in self.labels.keys():
                undefined_symbol_names.append(relocation.symbol_name)

        return undefined_symbol_names


def assemble(program: ASMCode) -> CodegenOutput | Traceback:
    
    program_bytes = bytes()
    relocations: list[Relocation] = []
    labels: dict[str, int] = {}
    for instruction in program.code:
        if isinstance(instruction, Label):
            labels.update({instruction.name: len(program_bytes)})
            continue
        encoded = encode(instruction, 0)
        if isinstance(encoded, Traceback):
            error = encoded
            error.elaborate("Code does not compile")
            return error
        for relocation in encoded[1]:
            relocation.index += len(program_bytes)
        program_bytes += bytes(encoded[0])
        relocations += encoded[1]
    return CodegenOutput(program_bytes, relocations, labels)

def load_instruction_set_data() -> list[InstructionEncoding] | Traceback:

    with open("./x86/isa_data_x86.txt", "r") as file:
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


def encode(instruction: ASMInstruction, instruction_address: int) -> tuple[X86Instruction, list[Relocation], dict[str, int]] | Traceback:

    instruction_formats = load_instruction_set_data()
    if isinstance(instruction_formats, Traceback):
        error = instruction_formats
        error.elaborate("x86 ISA data loading failed")
        return error
    smallest_encoding: tuple[X86Instruction, list[Relocation], dict[str, int]] | None = None
    failures: list[Traceback] = []
    for format in instruction_formats:
        encode_result = encode_instruction_using_encoding(instruction, format, instruction_address)
        if isinstance(encode_result, Traceback):
            if instruction.mnemonic == format.mnemonic:
                encode_result.elaborate(f"Failure to encode {instruction.mnemonic} with opcode {bytes(format.opcode).hex()}")
                failures.append(encode_result)
        else:
            encoded_instruction, relocations, labels = encode_result
            if not smallest_encoding:
                smallest_encoding = encoded_instruction, relocations, labels
            if len(bytes(encoded_instruction)) < len(bytes(smallest_encoding[0])):
                smallest_encoding = encoded_instruction, relocations, labels
    if smallest_encoding:
        return smallest_encoding
    msg = f"Cannot encode instruction '{instruction}'\n"
    for failure in failures:
        for megg in failure.errors:
            msg += megg.message + "\n"
        msg += "\n"
    return Traceback.new(msg)