"This module provides types for representing and emitting x86 machine code"
import enum
from dataclasses import dataclass

# Links
# http://www.c-jump.com/CIS77/CPU/x86/lecture.html
# https://defuse.ca/online-x86-assembler.htm#disassembly
# http://ref.x86asm.net/coder32.html

class AddressingMode(enum.IntEnum):
    INDIRECT = 0
    INDIRECT_WITH_BYTE_DISPLACEMENT = 1
    INDIRECT_WITH_FOUR_BYTE_DISPACEMENT = 2
    DIRECT = 3

@dataclass
class RegisterType:

    name: str
    code: int
    size: int
        
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

    def __str__(self):
        return str(self.value)

# Unused for now
class InstructionPrefix:

    def __init__(self, operand_size_prefix: bool) -> None:
        
        self.prefix = None
        self.address_size_prefix = None
        self.operand_size_prefix = operand_size_prefix
        self.segment_override = None
    
    def __bytes__(self):

        result = bytes()
        if self.operand_size_prefix:
            result += bytes([0x66])
        
        return result

class Opcode:
    
    def __init__(self, value: bytes) -> None:
        self.value = value
    
    def get_primary_byte(self):

        if not self.value:
            raise ValueError()
        return self.value[-1]
    
    def is_immediate(self):
        return bool(self.get_primary_byte() & 0b10000000)
    
    def get_direction_bit(self):
        return bool(self.get_primary_byte() & 0b00000010)
    
    def get_size_bit(self):
        return bool(self.get_primary_byte() & 0b00000001)
    
    def get_operand_size(self):
        
        if self.get_size_bit():
            return 32
        else:
            return 8
        
    def __bytes__(self):

        return self.value


class ModRegRM:

    def __init__(self, mod: AddressingMode, reg: int, rm: int) -> None:
        
        self.mod = mod
        self.reg = reg
        self.rm = rm
    
    def __bytes__(self):
        return bytes([self.mod.value << 6 | self.reg << 3 | self.rm])
    
    def __str__(self) -> str:
        return f"[{self.mod.name} {self.reg} {self.rm}]"

class ScaledIndexByte:

    def __init__(self, scale: int, index: int, base: int) -> None:
        
        self.scale = scale
        self.index = index
        self.base = base
    
    def __bytes__(self):
        return bytes([self.scale << 6 | self.index << 3 | self.base])
    
    def __str__(self) -> str:
        return f"[{self.scale} {self.index} {self.base}]"

class X86Instruction:

    def __init__(self, prefix: "InstructionPrefix | None", opcode: "Opcode | bytes", mod_reg_rm: "ModRegRM | None", sib: "ScaledIndexByte | None", displacement: bytes, immediate: bytes):
        
        self.prefix = prefix
        self.opcode = opcode
        self.mod_reg_rm = mod_reg_rm
        self.sib = sib
        self.displacement = displacement
        self.immediate = immediate
    
    def __bytes__(self):

        machine_code = bytes()
        if self.prefix:
            machine_code += bytes(self.prefix)
        machine_code += bytes(self.opcode)
        if self.mod_reg_rm:
            machine_code += bytes(self.mod_reg_rm)
        if self.sib:
            machine_code += bytes(self.sib)
        machine_code += bytes(self.displacement)
        machine_code += bytes(self.immediate)

        return machine_code