from dataclasses import dataclass
from typing import Literal
import enum

@dataclass
class RegisterType:
    name: str
    size: Literal[8, 16, 32]
        
    def __str__(self) -> str:
        return self.name

class Register(enum.Enum):
    AL = RegisterType("al", 8)
    AX = RegisterType("ax", 16)
    EAX = RegisterType("eax", 32)
    BL = RegisterType("bl", 8)
    BX = RegisterType("bx", 16)
    EBX = RegisterType("ebx", 32)
    CL = RegisterType("cl", 8)
    CX = RegisterType("cx", 16)
    ECX = RegisterType("ecx", 32)
    DL = RegisterType("dl", 8)
    DX = RegisterType("dx", 16)
    EDX = RegisterType("edx", 32)
    AH = RegisterType("ah", 8)
    SP = RegisterType("sp", 16)
    ESP = RegisterType("esp", 32)
    CH = RegisterType("ch", 8)
    BP = RegisterType("bp", 16)
    EBP = RegisterType("ebp", 32)
    DH = RegisterType("dh", 8)
    SI = RegisterType("si", 16)
    ESI = RegisterType("esi", 32)
    BH = RegisterType("bh", 8)
    DI = RegisterType("di", 16)
    EDI = RegisterType("edi", 32)

    @staticmethod
    def from_name(name: str):
        for register in Register:
            if register.value.name == name.lower():
                return register
    
    def __str__(self):
        return str(self.value)