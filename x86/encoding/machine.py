"This module provides types for representing x86 machine code"
import enum
from dataclasses import dataclass
from typing import Literal
from x86.register import Register
from x86.encoding.rex import RexPrefix

# Links
# http://www.c-jump.com/CIS77/CPU/x86/lecture.html
# https://defuse.ca/online-x86-assembler.htm#disassembly
# http://ref.x86asm.net/coder32.html
# https://wiki.osdev.org/X86-64_Instruction_Encoding

ThreeBits = Literal[0, 1, 2, 3, 4, 5, 6, 7]

# Map of the extended (with rex r field) mod/reg/rm "reg" field to an actual register. In addition to the reg field, the register size is needed.
REGISTER_CODES: dict[int, list[Register]] = {
    #   (8 bit)         (16 bit)      (32 bit)        (64 bit)
    0:  [Register.AL,   Register.AX,   Register.EAX,  Register.RAX],
    1:  [Register.CL,   Register.CX,   Register.ECX,  Register.RCX],
    2:  [Register.DL,   Register.DX,   Register.EDX,  Register.RDX],
    3:  [Register.BL,   Register.BX,   Register.EBX,  Register.RBX],
    4:  [Register.AH,   Register.SP,   Register.ESP,  Register.RSP],
    5:  [Register.CH,   Register.BP,   Register.EBP,  Register.RBP],
    6:  [Register.DH,   Register.SI,   Register.ESI,  Register.RSI],
    7:  [Register.BH,   Register.DI,   Register.EDI,  Register.RDI],
    8:  [Register.R8L,  Register.R8W,  Register.R8D,  Register.R8],
    9:  [Register.R9L,  Register.R9W,  Register.R9D,  Register.R9],
    10: [Register.R10L, Register.R10W, Register.R10D, Register.R10],
    11: [Register.R11L, Register.R11W, Register.R11D, Register.R11],
    12: [Register.R12L, Register.R12W, Register.R12D, Register.R12],
    13: [Register.R13L, Register.R13W, Register.R13D, Register.R13],
    14: [Register.R14L, Register.R14W, Register.R14D, Register.R14],
    15: [Register.R15L, Register.R15W, Register.R15D, Register.R15]
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
    rex_prefix: RexPrefix | None
    prefixes: InstructionPrefixes
    opcode: Opcode
    mod_reg_rm: ModRegRM | None
    sib: ScaleIndexByte | None
    displacement: bytes
    immediate: bytes
    
    def get_displacement_index(self):
        
        index = 0
        if self.rex_prefix:
            index += len(bytes(self.rex_prefix))
        index += len(bytes(self.prefixes) + bytes(self.opcode))
        if self.mod_reg_rm:
            index += len(bytes(self.mod_reg_rm))
        if self.sib:
            index += len(bytes(self.sib))
        
        return index
    
    def get_immediate_index(self):
        return self.get_displacement_index() + len(self.displacement)
    
    def __bytes__(self):

        machine_code = bytes()
        if self.rex_prefix:
            machine_code += bytes(self.rex_prefix)
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

def register_from_code(reg_field: ThreeBits, size: Literal[8, 16, 32, 64], rex_reg_extention: bool | None):

    register: Register | None = None
    for reg in REGISTER_CODES[(rex_reg_extention if rex_reg_extention is not None else 0) << 3 | reg_field]:
        if reg.value.size == size:
            register = reg
            break
    else:
        raise ValueError("Unreachable code (Uh Oh!)")
    
    # When the rex prefix is present the encoding changes slightly
    map_registers_unreachable_with_rex: dict[Register, Register] = {
        Register.AH: Register.SPL,
        Register.CL: Register.BPL,
        Register.DL: Register.SIL,
        Register.BL: Register.DIL
    }

    if register in map_registers_unreachable_with_rex.keys():
        return map_registers_unreachable_with_rex[register]
    
    return register