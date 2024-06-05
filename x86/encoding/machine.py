"This module provides types for representing x86 machine code"
import enum
from dataclasses import dataclass
from typing import Literal
from x86.register import Register

# Links
# http://www.c-jump.com/CIS77/CPU/x86/lecture.html
# https://defuse.ca/online-x86-assembler.htm#disassembly
# http://ref.x86asm.net/coder32.html

ThreeBits = Literal[0, 1, 2, 3, 4, 5, 6, 7]

REGISTER_CODES: dict[ThreeBits, list[Register]] = {
    0: [Register.AL, Register.AX, Register.EAX],
    1: [Register.CL, Register.CX, Register.ECX],
    2: [Register.DL, Register.DX, Register.EDX],
    3: [Register.BL, Register.BX, Register.EBX],
    4: [Register.AH, Register.SP, Register.ESP],
    5: [Register.CH, Register.BP, Register.EBP],
    6: [Register.DH, Register.SI, Register.ESI],
    7: [Register.BH, Register.DI, Register.EDI],
}

class AddressingMode(enum.IntEnum):
    INDIRECT = 0
    INDIRECT_WITH_BYTE_DISPLACEMENT = 1
    INDIRECT_WITH_FOUR_BYTE_DISPACEMENT = 2
    DIRECT = 3

class InstructionPrefix(enum.IntEnum):
    LOCK = 0x0f
    REPEAT_NOT_EQUAL = 0xf2
    REPEAT_EQUAL = 0xf3

class SegmentOverridePrefix(enum.IntEnum):
    STACK = 0x36
    DATA = 0x3e
    CODE = 0x2e
    EXTRA = 0x26

@dataclass
class InstructionPrefixes:
    instruction_prefix: InstructionPrefix | None
    address_size_override: bool
    operand_size_override: bool
    segment_override: SegmentOverridePrefix | None
    
    @staticmethod
    def none():
        return InstructionPrefixes(None, False, False, None)
    
    def __bytes__(self):

        result = bytes()
        if self.instruction_prefix:
            result += bytes([self.instruction_prefix])
        if self.address_size_override:
            result += bytes([0x67])
        if self.operand_size_override:
            result += bytes([0x66])
        if self.segment_override:
            result += bytes([self.segment_override])
        
        return result

@dataclass
class Opcode:
    expansion_prefix: bool
    value: int

    @classmethod
    def from_bytes(cls, value: bytes):
        return Opcode(value[0] == 0x0f, value[-1])
    
    def get_direction_bit(self):
        return bool(self.value & 0b00000010)
    
    def get_register_size_bit(self):
        return bool(self.value & 0b00000001)
    
    get_immediate_size_bit = get_register_size_bit
    def __bytes__(self):
        return bytes([0x0f])* self.expansion_prefix + bytes([self.value])

@dataclass
class ModRegRM:
    mod: AddressingMode
    reg: ThreeBits
    rm: ThreeBits
    
    def __bytes__(self):
        return bytes([self.mod.value << 6 | self.reg << 3 | self.rm])
    
    def __str__(self) -> str:
        return f"[{self.mod.name} {self.reg} {self.rm}]"

@dataclass
class ScaleIndexByte:
    scale: Literal[0, 1, 2, 3]
    index: ThreeBits
    base: ThreeBits
        
    def __bytes__(self):
        return bytes([self.scale << 6 | self.index << 3 | self.base])
    
    def __str__(self) -> str:
        return f"[{self.scale} {self.index} {self.base}]"

@dataclass
class X86MachineInstruction:
    prefixes: InstructionPrefixes
    opcode: Opcode
    mod_reg_rm: ModRegRM | None
    sib: ScaleIndexByte | None
    displacement: bytes
    immediate: bytes
    
    def get_displacement_index(self):
        
        index = len(bytes(self.prefixes) + bytes(self.opcode))
        if self.mod_reg_rm:
            index += len(bytes(self.mod_reg_rm))
        if self.sib:
            index += len(bytes(self.sib))
        
        return index
    
    def get_immediate_index(self):
        return self.get_displacement_index() + len(self.displacement)
    
    def __bytes__(self):

        machine_code = bytes()
        machine_code += bytes(self.prefixes)
        machine_code += bytes(self.opcode)
        if self.mod_reg_rm:
            machine_code += bytes(self.mod_reg_rm)
        if self.sib:
            machine_code += bytes(self.sib)
        machine_code += self.displacement
        machine_code += self.immediate

        return machine_code

def get_register_code(register: Register):
    for code in REGISTER_CODES:
        if register in REGISTER_CODES[code]:
            return code
    else:
        return 0 # Never hapens

def register_from_code(code: ThreeBits, size: Literal[8, 16, 32]):

    for register in REGISTER_CODES[code]:
        if register.value.size == size:
            return register
    else:
        raise ValueError("Unreachable code (Uh Oh!)")