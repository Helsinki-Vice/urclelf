"This module provides types for representing x86 machine code"
import enum
from dataclasses import dataclass
from typing import Literal

# Links
# http://www.c-jump.com/CIS77/CPU/x86/lecture.html
# https://defuse.ca/online-x86-assembler.htm#disassembly
# http://ref.x86asm.net/coder32.html

ThreeBits = Literal[0, 1, 2, 3, 4, 5, 6, 7]
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
class X86Instruction:
    prefixes: InstructionPrefixes
    opcode: Opcode
    mod_reg_rm: ModRegRM | None
    sib: ScaleIndexByte | None
    displacement: bytes
    immediate: bytes
        
    def __bytes__(self):

        machine_code = bytes()
        if self.prefixes:
            machine_code += bytes(self.prefixes)
        machine_code += bytes(self.opcode)
        if self.mod_reg_rm:
            machine_code += bytes(self.mod_reg_rm)
        if self.sib:
            machine_code += bytes(self.sib)
        machine_code += bytes(self.displacement)
        machine_code += bytes(self.immediate)

        return machine_code

@dataclass
class RegisterType:
    name: str
    code: ThreeBits
    size: Literal[8, 16, 32]
        
    def __str__(self) -> str:
        return self.name

class Register(enum.Enum):
    AL = RegisterType("al", 0, 8)
    AX = RegisterType("ax", 0, 16)
    EAX = RegisterType("eax", 0, 32)
    BL = RegisterType("bl", 3, 8)
    BX = RegisterType("bx", 3, 16)
    EBX = RegisterType("ebx", 3, 32)
    CL = RegisterType("cl", 1, 8)
    CX = RegisterType("cx", 1, 16)
    ECX = RegisterType("ecx", 1, 32)
    DL = RegisterType("dl", 2, 8)
    DX = RegisterType("dx", 2, 16)
    EDX = RegisterType("edx", 2, 32)
    AH = RegisterType("ah", 4, 8)
    SP = RegisterType("sp", 4, 16)
    ESP = RegisterType("esp", 4, 32)
    CH = RegisterType("ch", 5, 8)
    BP = RegisterType("bp", 5, 16)
    EBP = RegisterType("ebp", 5, 32)
    DH = RegisterType("dh", 6, 8)
    SI = RegisterType("si", 6, 16)
    ESI = RegisterType("esi", 6, 32)
    BH = RegisterType("bh", 7, 8)
    DI = RegisterType("di", 7, 16)
    EDI = RegisterType("edi", 7, 32)

    @staticmethod
    def from_code(code: int, size: int):
        for register in Register:
            if register.value.code == code and register.value.size == size:
                return register
    
    @staticmethod
    def from_name(name: str):
        for register in Register:
            if register.value.name == name.lower():
                return register
    
    def get_code(self):
        return self.value.code
    
    def __str__(self):
        return str(self.value)