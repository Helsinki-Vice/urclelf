from dataclasses import dataclass
from typing import Literal
import enum

@dataclass
class RegisterType:
    name: str
    size: Literal[8, 16, 32, 64]
        
    def __str__(self) -> str:
        return self.name

class Register(enum.Enum):
    AL = RegisterType("al", 8)
    AX = RegisterType("ax", 16)
    EAX = RegisterType("eax", 32)
    RAX = RegisterType("rax", 64)
    BL = RegisterType("bl", 8)
    BX = RegisterType("bx", 16)
    EBX = RegisterType("ebx", 32)
    RBX = RegisterType("rbx", 64)
    CL = RegisterType("cl", 8)
    CX = RegisterType("cx", 16)
    ECX = RegisterType("ecx", 32)
    RCX = RegisterType("rcx", 64)
    DL = RegisterType("dl", 8)
    DX = RegisterType("dx", 16)
    EDX = RegisterType("edx", 32)
    RDX = RegisterType("rdx", 64)
    AH = RegisterType("ah", 8)
    SPL = RegisterType("spl", 8)
    SP = RegisterType("sp", 16)
    ESP = RegisterType("esp", 32)
    RSP = RegisterType("rsp", 64)
    CH = RegisterType("ch", 8)
    BPL = RegisterType("bpl", 8)
    BP = RegisterType("bp", 16)
    EBP = RegisterType("ebp", 32)
    RBP = RegisterType("rbp", 64)
    DH = RegisterType("dh", 8)
    SIL = RegisterType("sil", 8)
    SI = RegisterType("si", 16)
    ESI = RegisterType("esi", 32)
    RSI = RegisterType("rsi", 64)
    BH = RegisterType("bh", 8)
    DIL = RegisterType("dil", 8)
    DI = RegisterType("di", 16)
    EDI = RegisterType("edi", 32)
    RDI = RegisterType("rdi", 64)
    R8L = RegisterType("r8l", 8)
    R8W = RegisterType("r8w", 16)
    R8D = RegisterType("r8d", 32)
    R8 = RegisterType("r8", 64)
    R9L = RegisterType("r9l", 8)
    R9W = RegisterType("r9w", 16)
    R9D = RegisterType("r9d", 32)
    R9 = RegisterType("r9", 64)
    R10L = RegisterType("r10l", 8)
    R10W = RegisterType("r10w", 16)
    R10D = RegisterType("r10d", 32)
    R10 = RegisterType( "r10", 64)
    R11L = RegisterType("r11l", 8)
    R11W = RegisterType("r11w", 16)
    R11D = RegisterType("r11d", 32)
    R11 = RegisterType( "r11", 64)
    R12L = RegisterType("r12l", 8)
    R12W = RegisterType("r12w", 16)
    R12D = RegisterType("r12d", 32)
    R12 = RegisterType( "r12", 64)
    R13L = RegisterType("r13l", 8)
    R13W = RegisterType("r13w", 16)
    R13D = RegisterType("r13d", 32)
    R13 = RegisterType( "r13", 64)
    R14L = RegisterType("r14l", 8)
    R14W = RegisterType("r14w", 16)
    R14D = RegisterType("r14d", 32)
    R14 = RegisterType( "r14", 64)
    R15L = RegisterType("r15l", 8)
    R15W = RegisterType("r15w", 16)
    R15D = RegisterType("r15d", 32)
    R15 = RegisterType( "r15", 64)
    

    @staticmethod
    def from_name(name: str):
        for register in Register:
            if register.value.name == name.lower():
                return register
    
    def __str__(self):
        return str(self.value)

@dataclass
class GeneralRegisters:
    a: Register
    b: Register
    c: Register
    d: Register
    sp: Register
    bp: Register
    di: Register
    si: Register

def get_registers(bits: Literal[32, 64]) -> GeneralRegisters:

    if bits == 64:
        return GeneralRegisters(
            Register.RAX,
            Register.RBX,
            Register.RCX,
            Register.RDX,
            Register.RSP,
            Register.RBP,
            Register.RDI,
            Register.RSI
        )
    else:
        return GeneralRegisters(
            Register.EAX,
            Register.EBX,
            Register.ECX,
            Register.EDX,
            Register.ESP,
            Register.EBP,
            Register.EDI,
            Register.ESI
        )