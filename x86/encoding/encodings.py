"This module is responsible for representing and loading the specific instruction encoding formats for each opcode."

from dataclasses import dataclass
from typing import Literal, Self
from x86.encoding.machine import Opcode, ThreeBits
from x86.register import Register
from x86.asm import Mnemonic
from error import Traceback

@dataclass(frozen=True)
class ImmediateType:
    size: Literal[1, 2, 4, 8]
    is_relative: bool = False

@dataclass(frozen=True)
class RegisterSize:
    size: Literal[8, 16, 32, 64] | None = None

OperandType = RegisterSize | ImmediateType | Register

@dataclass
class InstructionEncodingFormat:
    mnemonic: Mnemonic
    opcode: Opcode
    opcode_extention: ThreeBits | None
    permitted_operands: list[OperandType]
    
    @staticmethod
    def from_str(encoding: str, bits: Literal[32, 64]):

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
                operand_formats.append(RegisterSize(bits if opcode.get_register_size_bit() else 8))
            elif operand == "r8":
                operand_formats.append(RegisterSize(8))
            elif operand == "r16": #FIXME: 16-bit does not work yet
                operand_formats.append(RegisterSize(16))
            elif operand == "r32":
                operand_formats.append(RegisterSize(32))
            elif operand == "r64":
                operand_formats.append(RegisterSize(64))
            elif operand == "i8":
                operand_formats.append(ImmediateType(1, False))
            elif operand == "i16":
                operand_formats.append(ImmediateType(2, False))
            elif operand == "i32":
                operand_formats.append(ImmediateType(4, False))
            elif operand == "i64":
                operand_formats.append(ImmediateType(8, False))
            elif operand == "rel8":
                operand_formats.append(ImmediateType(1, True))
            elif operand == "rel16":
                operand_formats.append(ImmediateType(2, True))
            elif operand == "rel32":
                operand_formats.append(ImmediateType(4, True))
            elif operand == "rel64":
                operand_formats.append(ImmediateType(8, True))
            elif operand == "es":
                pass
            else:
                return Traceback.new(f"Unknown operand for opcode {bytes(opcode).hex()}: '{operand}'")
        
        return InstructionEncodingFormat(mnemonic, opcode, opcode_extention, operand_formats)
    
    def get_immediate(self):

        for operand_format in self.permitted_operands:
            if isinstance(operand_format, ImmediateType):
                return operand_format

def load_instruction_set_data(bits: Literal[32, 64]) -> list[InstructionEncodingFormat] | Traceback:

    if bits == 64:
        path = "./x86/encoding/isa_data_x64.txt"
    else:
        path = "./x86/encoding/isa_data_x86.txt"
    
    with open(path, "r") as file:
        formats = file.read().splitlines()
        encodings: list[InstructionEncodingFormat] = []
        for format in formats:
            encoding = InstructionEncodingFormat.from_str(format, bits)
            if isinstance(encoding, Traceback):
                error = encoding
                error.elaborate(f"x86 ISA data contains an invalid line '{format}'")
                return error
            encodings.append(encoding)
        
        return encodings