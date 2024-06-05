from dataclasses import dataclass
import struct

from typing import Literal, Self
from x86.encoding.machine import ModRegRM, X86MachineInstruction, AddressingMode, InstructionPrefixes, ScaleIndexByte
from x86.register import Register
from x86.asm import EffectiveAddress, ASMInstruction, ASMCode, Label, Operand, Immediate
from error import Traceback
from x86.encoding.modregrm import calculate_modregrm
from x86.encoding.sib import calculate_sib
from x86.encoding.getregrm import get_operand_register_size, get_regrm_operands
from x86.encoding.encodings import load_instruction_set_data, InstructionEncodingFormat, ImmediateType, OperandType, RegisterSize
from x86.encoding.output import AssembledMachineCode, Relocation

def match_operand(operand: Operand, operand_type: OperandType) -> Literal[True] | Traceback:

    if isinstance(operand_type, RegisterSize):
        if isinstance(operand.value, (Register, EffectiveAddress)):
            if get_operand_register_size(operand) != operand_type.size:
                return Traceback.new(f"Expected {operand_type.size} bit register, got register {operand}")
            return True
        else:
            return Traceback.new(f"Expected {operand_type.size} bit register, got {operand}")
    elif isinstance(operand_type, ImmediateType):
        if not isinstance(operand.value, (int, Label)):
            return Traceback.new(f"Expected immediate (int or label), got {operand} instead")
        if isinstance(operand.value, int):
            if (operand.value < 0 or operand.value > 128) and operand_type.size != 4:
            # TODO: Allow immediates with size != 4 bytes
                return Traceback.new("Only 32 bit immediates are currently unsupported")
        return True
    else:
        if operand.value != operand_type:
            return Traceback.new(f"Expected register {operand_type}, got {operand.value}")
        return True

def get_mismatched_operand_errors(instruction: ASMInstruction, encoding: InstructionEncodingFormat) -> Traceback | None:

    if len(instruction.operands) != len(encoding.permitted_operands):
        return Traceback.new(f"Incorrect operand count of {len(instruction.operands)}, expected {len(encoding.permitted_operands)}")
    for index in range(len(encoding.permitted_operands)):
        match_test = match_operand(instruction.operands[index], encoding.permitted_operands[index])
        if isinstance(match_test, Traceback):
            error = match_test
            error.elaborate(f"Operand '{instruction.operands[index]}' is not of the expected type.")
            return error


def calculate_displacement(effective_address: Register | EffectiveAddress | None, mod_reg_rm: ModRegRM | None, sib: ScaleIndexByte | None) -> tuple[bytes, Relocation | None]:

    if not isinstance(effective_address, EffectiveAddress):
        return bytes(), None
    if isinstance(effective_address.displacement, Label):
        return bytes(4), Relocation(effective_address.displacement.name, 0, 4, 0, False, False)
    else:
        displacement = effective_address.displacement
    if mod_reg_rm:
        mod = mod_reg_rm.mod
        rm = mod_reg_rm.rm
        if mod == AddressingMode.INDIRECT_WITH_BYTE_DISPLACEMENT:
            return struct.pack("<b", displacement), None
        elif mod == AddressingMode.INDIRECT_WITH_FOUR_BYTE_DISPACEMENT:
            return struct.pack("<i", displacement), None
        elif mod == AddressingMode.INDIRECT and rm == 5:
            return struct.pack("<i", displacement), None
        else:
            return bytes(), None
    
    assert not sib
    
    return bytes(), None


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
    instruction_end_address = immediate_address + immediate_type.size
    immediate_value_relative = immediate_value - instruction_end_address if immediate_type.is_relative else immediate_value
    binary = int_as_bytes(immediate_value_relative, immediate_type.size * 8, immediate_type.is_relative)
    if isinstance(binary, Traceback):
        error = binary
        error.elaborate("Immediate out of range")
        return error
    
    return binary


def encode_instruction_using_encoding(instruction: ASMInstruction, encoding: InstructionEncodingFormat, instruction_address: int) -> AssembledMachineCode | Traceback:

    if instruction.mnemonic != encoding.mnemonic:
        return Traceback.new(f"Wrong Mnemonic {instruction.mnemonic} != {encoding.mnemonic}")
    
    bad_operand_error = get_mismatched_operand_errors(instruction, encoding)
    if bad_operand_error is not None:
        bad_operand_error.elaborate("Instruction contains invalid operand")
        return bad_operand_error

    prefixes = InstructionPrefixes.none()
    
    regrm_operands = get_regrm_operands(instruction, encoding, encoding.opcode.get_direction_bit())
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
    
    displacement_bytes, displacement_relocation = calculate_displacement(register_or_memory, mod_reg_rm, sib)
    
    machine_instruction = X86MachineInstruction(prefixes, encoding.opcode, mod_reg_rm, sib, displacement_bytes, bytes())

    immediate = encode_immediate(instruction.get_immediate(), encoding.get_immediate(), instruction_address + len(bytes(machine_instruction)))
    if isinstance(immediate, Relocation):
        immediate_relocation = immediate
        immediate_bytes = bytes.fromhex("fcffffff")
    elif isinstance(immediate, Traceback):
        error = immediate
        error.elaborate(f"Bad immediate {instruction.get_immediate()}")
        return error
    else:
        immediate_relocation = None
        immediate_bytes = bytes(immediate)

    machine_instruction = X86MachineInstruction(prefixes, encoding.opcode, mod_reg_rm, sib, displacement_bytes, immediate_bytes)
    relocations = []
    if displacement_relocation:
        displacement_relocation.index = machine_instruction.get_displacement_index()
        relocations.append(displacement_relocation)
    if immediate_relocation:
        immediate_relocation.index = machine_instruction.get_immediate_index()
        if immediate_relocation.is_relative:
            immediate_relocation.addend = -(len(bytes(machine_instruction)) - machine_instruction.get_immediate_index())
        relocations.append(immediate_relocation)
    
    return AssembledMachineCode(bytes(machine_instruction), relocations, {})


def assemble(program: ASMCode) -> AssembledMachineCode | Traceback:
    
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
            error.elaborate(f"x86 Assembly contains an invalid instruction '{instruction}'")
            return error
        for relocation in encoded.relocations:
            relocation.index += len(program_bytes)
        program_bytes += encoded.binary
        relocations += encoded.relocations
    
    return AssembledMachineCode(program_bytes, relocations, labels)


def encode(instruction: ASMInstruction, instruction_address: int) -> AssembledMachineCode | Traceback:

    instruction_formats = load_instruction_set_data()
    if isinstance(instruction_formats, Traceback):
        error = instruction_formats
        error.elaborate("x86 ISA data loading failed")
        return error
    smallest_encoding: AssembledMachineCode | None = None
    failures: list[Traceback] = []
    for format in instruction_formats:
        encode_result = encode_instruction_using_encoding(instruction, format, instruction_address)
        if isinstance(encode_result, Traceback):
            if instruction.mnemonic == format.mnemonic:
                encode_result.elaborate(f"Failure to encode {instruction.mnemonic} with opcode {bytes(format.opcode).hex()}")
                failures.append(encode_result)
        else:
            encoded_instruction = encode_result
            if not smallest_encoding:
                smallest_encoding = encoded_instruction
            if len(encoded_instruction.binary) < len(smallest_encoding.binary):
                smallest_encoding = encoded_instruction
    if smallest_encoding:
        return smallest_encoding
    msg = f"Cannot encode instruction '{instruction}'\n"
    for failure in failures:
        for megg in failure.errors:
            msg += megg.message + "\n"
        msg += "\n"
    return Traceback.new(msg)


def as_memory(self, scale: Literal[1, 2, 4], offset: Register | int) -> EffectiveAddress:
    if isinstance(self.value, Register):
        if isinstance(offset, Register):
            memory = EffectiveAddress(base=self.value, scale=scale, index=offset)
        else:
            memory = EffectiveAddress(base=self.value, scale=scale, displacement=offset)
    elif isinstance(self.value, EffectiveAddress):
        memory = self.value
    else:
        if isinstance(offset, Register):
            memory = EffectiveAddress(displacement=self.value)
        else:
            memory = EffectiveAddress(displacement=self.value)
    
    return memory


def get_immediate(self):

        for operand in self.operands:
            if isinstance(operand.value, Immediate):
                return operand.value
