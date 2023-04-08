import enum
from dataclasses import dataclass
import struct

from x86 import Register, X86Instruction, Opcode, ModRegRM, AddressingMode, Mnemonic

class OperandEncodingFormat(enum.Enum):
    OPCODE = enum.auto()
    MODREGRM_REGISTER_FIELD = enum.auto()
    MODREGRM_RM_FIELD = enum.auto()
    IMMEDIATE_8_BITS = enum.auto()
    IMMEDIATE_32_BITS = enum.auto()

class Operand:

    def __init__(self, value: "int | Register") -> None:

        self.value = value
    
    def get_register_size(self):

        if isinstance(self.value, Register):
            return self.value.value.size
        
    def __str__(self) -> str:
        return str(self.value)

class X86ASMInstruction:

    def __init__(self, mnemonic: Mnemonic, operands: list[Operand], addressing_mode: AddressingMode) -> None:
        
        self.mnemonic = mnemonic
        self.operands = operands
        self.addressing_mode = addressing_mode
    
    def __str__(self) -> str:

        operands = ", ".join([str(operand) for operand in self.operands])
        return f"{self.mnemonic.value} {operands}"

@dataclass
class InstructionEncoding:

    opcode: Opcode
    mnemonic: Mnemonic
    opcode_extention: int
    operand_format: list[OperandEncodingFormat]

    def encode(self, instruction: X86ASMInstruction):

        if instruction.mnemonic != self.mnemonic:
            return None
        if len(instruction.operands) != len(self.operand_format):
            return None
        
        mod_reg_rm = None
        mod_field = instruction.addressing_mode
        if self.opcode.is_immediate():
            reg_field = self.opcode_extention
        else:
            reg_field = None
        rm_field = None
        immediate = bytes()

        for operand_index in range(len(instruction.operands)):
            format = self.operand_format[operand_index]
            operand = instruction.operands[operand_index]
            if format == OperandEncodingFormat.OPCODE:
                if operand.value != self.opcode.value[-1] & 0b00000111:
                    return None
            elif format == OperandEncodingFormat.MODREGRM_REGISTER_FIELD:
                if operand.get_register_size() != self.opcode.get_operand_size():
                    return None
                reg_field = operand.value
            elif format == OperandEncodingFormat.MODREGRM_RM_FIELD:
                if operand.get_register_size() != self.opcode.get_operand_size():
                    return None
                rm_field = operand.value
            elif format == OperandEncodingFormat.IMMEDIATE_8_BITS:
                if isinstance(operand.value, Register):
                    value: int = operand.value.value.code % 256
                else:
                    value = operand.value % 256
                immediate = struct.pack("B", value)
            elif format == OperandEncodingFormat.IMMEDIATE_32_BITS:
                if isinstance(operand.value, Register):
                    value: int = operand.value.value.code % 256
                else:
                    value = operand.value % 2**32
                immediate = struct.pack("I", value)
            else:
                return None
        if mod_field is not None and reg_field is not None and rm_field is not None:
            if isinstance(reg_field, Register):
                reg_field = reg_field.value.code.value
            if isinstance(rm_field, Register):
                rm_field = rm_field.value.code.value
            mod_reg_rm = ModRegRM(mod_field, reg_field, rm_field)
        return X86Instruction(None, self.opcode, mod_reg_rm, bytes(), immediate)

INSTRUCTION_FORMATS = [
    InstructionEncoding(Opcode(bytes([0x00])), Mnemonic.ADD, 0, [OperandEncodingFormat.MODREGRM_RM_FIELD, OperandEncodingFormat.MODREGRM_REGISTER_FIELD]),
    InstructionEncoding(Opcode(bytes([0x01])), Mnemonic.ADD, 0, [OperandEncodingFormat.MODREGRM_RM_FIELD, OperandEncodingFormat.MODREGRM_REGISTER_FIELD]),
    InstructionEncoding(Opcode(bytes([0x80])), Mnemonic.ADD, 0, [OperandEncodingFormat.MODREGRM_RM_FIELD, OperandEncodingFormat.IMMEDIATE_8_BITS]),
    InstructionEncoding(Opcode(bytes([0x81])), Mnemonic.ADD, 0, [OperandEncodingFormat.MODREGRM_RM_FIELD, OperandEncodingFormat.IMMEDIATE_32_BITS]),
    InstructionEncoding(Opcode(bytes([0xcd])), Mnemonic.INT, 0, [OperandEncodingFormat.IMMEDIATE_8_BITS]),
    InstructionEncoding(Opcode(bytes([0xc6])), Mnemonic.MOV, 0, [OperandEncodingFormat.MODREGRM_RM_FIELD, OperandEncodingFormat.IMMEDIATE_8_BITS]),
    InstructionEncoding(Opcode(bytes([0xc7])), Mnemonic.MOV, 0, [OperandEncodingFormat.MODREGRM_RM_FIELD, OperandEncodingFormat.IMMEDIATE_32_BITS])
]

def encode(instruction: X86ASMInstruction):

    for format in INSTRUCTION_FORMATS:
        result = format.encode(instruction)
        if result:
            return result