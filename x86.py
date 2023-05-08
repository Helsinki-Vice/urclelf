import enum
import struct
from dataclasses import dataclass

class Mnemonic(enum.Enum):
    ADD = "add"
    SUB = "sub"
    MOV = "mov"
    INT = "int"
    NOP = "nop"
    JMP = "jmp"
    JNZ = "jnz"
    JZ  = "jz"
    JBE = "jbe"
    JNBE = "jnbe"
    CMP = "cmp"
    PUSH = "push"
    INC = "inc"
    DEC = "dec"
    PUSHAD = "pushad"
    POPAD = "popad"
    CALL = "call"
    RETN = "retn"
    JGE = "jge"
    NEG = "neg"
    POP = "pop"
    DIV = "div"

BRANCH_MNEMONICS = [
    Mnemonic.JMP,
    Mnemonic.JBE,
    Mnemonic.JNBE,
    Mnemonic.JGE,
    Mnemonic.JNZ,
    Mnemonic.JZ,
    Mnemonic.CALL
]

class AddressingMode(enum.IntEnum):
    INDIRECT = 0
    INDIRECT_WITH_BYTE_DISPLACEMENT = 1
    INDIRECT_WITH_FOUR_BYTE_DISPACEMENT = 2
    DIRECT = 3

class RegisterCode(enum.IntEnum):
    AL_AX_EAX = 0
    CL_CX_ECX = 1
    DL_DX_EDX = 2
    BL_BX_EBX = 3
    AH_SP_ESP = 4
    CH_BP_EBP = 5
    DH_SI_ESI = 6
    BH_DI_EDI = 7

class RegisterType:

    def __init__(self, name: str, code: RegisterCode, size: int) -> None:
        
        self.name = name
        self.code = code
        self.size = size
    
    def __str__(self) -> str:
        return self.name

class Register(enum.Enum):
    AL = RegisterType("al", RegisterCode.AL_AX_EAX, 8)
    AX = RegisterType("ax", RegisterCode.AL_AX_EAX, 16)
    EAX = RegisterType("eax", RegisterCode.AL_AX_EAX, 32)
    BL = RegisterType("bl", RegisterCode.BL_BX_EBX, 8)
    BX = RegisterType("bx", RegisterCode.BL_BX_EBX, 16)
    EBX = RegisterType("ebx", RegisterCode.BL_BX_EBX, 32)
    CL = RegisterType("cl", RegisterCode.CL_CX_ECX, 8)
    CX = RegisterType("cx", RegisterCode.CL_CX_ECX, 16)
    ECX = RegisterType("ecx", RegisterCode.CL_CX_ECX, 32)
    DL = RegisterType("dl", RegisterCode.DL_DX_EDX, 8)
    DX = RegisterType("dx", RegisterCode.DL_DX_EDX, 16)
    EDX = RegisterType("edx", RegisterCode.DL_DX_EDX, 32)
    AH = RegisterType("ah", RegisterCode.AH_SP_ESP, 8)
    SP = RegisterType("sp", RegisterCode.AH_SP_ESP, 16)
    ESP = RegisterType("esp", RegisterCode.AH_SP_ESP, 32)
    CH = RegisterType("ch", RegisterCode.CH_BP_EBP, 8)
    BP = RegisterType("bp", RegisterCode.CH_BP_EBP, 16)
    EBP = RegisterType("ebp", RegisterCode.CH_BP_EBP, 32)
    DH = RegisterType("dh", RegisterCode.DH_SI_ESI, 8)
    SI = RegisterType("si", RegisterCode.DH_SI_ESI, 16)
    ESI = RegisterType("esi", RegisterCode.DH_SI_ESI, 32)
    BH = RegisterType("bh", RegisterCode.BH_DI_EDI, 8)
    DI = RegisterType("di", RegisterCode.BH_DI_EDI, 16)
    EDI = RegisterType("edi", RegisterCode.BH_DI_EDI, 32)

    def __str__(self):
        return str(self.value)

class InstructionPrefix:

    def __init__(self) -> None:
        
        self.prefix = None
        self.address_size_prefix = None
        self.operand_size_prefix = None
        self.segment_override = None
    
    def __bytes__(self):
        return bytes()

class Opcode:
    
    def __init__(self, value: bytes) -> None:
        
        self.value = value
        
    def is_immediate(self):
        return bool(self.value[-1] & 0b10000000)
    
    def get_direction_bit(self):
        return bool(self.value[-1] & 0b00000010)
    
    def get_size_bit(self):
        return bool(self.value[-1] & 0b00000001)
    
    def get_operand_size(self):
        
        if self.get_size_bit():
            return 32
        else:
            return 8
        
    def __bytes__(self):

        return self.value


class ModRegRM:

    def __init__(self, mod: AddressingMode, reg: "RegisterCode | int", rm: "RegisterCode | int") -> None:
        
        self.mod = mod
        self.reg = reg
        self.rm = rm
    
    def __bytes__(self):
        return bytes([self.mod.value << 6 | self.reg << 3 | self.rm])
    
    def __str__(self) -> str:
        return f"[{self.mod.name} {self.reg} {self.rm}]"
    
class X86Instruction:

    def __init__(self, prefix: "InstructionPrefix | None", opcode: "Opcode | bytes", mod_reg_rm: "ModRegRM | None", displacement: bytes, immediate: bytes):
        
        self.prefix = prefix
        self.opcode = opcode
        self.mod_reg_rm = mod_reg_rm
        self.sib = bytes()
        self.displacement = displacement
        self.immediate = immediate
    
    def __bytes__(self):

        machine_code = bytes()
        if self.prefix:
            machine_code += bytes(self.prefix)
        machine_code += bytes(self.opcode)
        if self.mod_reg_rm:
            machine_code += bytes(self.mod_reg_rm)
        machine_code += bytes(self.sib)
        machine_code += bytes(self.displacement)
        machine_code += bytes(self.immediate)

        return machine_code

class MachineCode:

    def __init__(self) -> None:
        
        self.instructions: list[X86Instruction] = []