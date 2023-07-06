"This module provides simple types for representing various URCL constructs"
import enum
from dataclasses import dataclass

class Mnemonic(enum.Enum):
    ADD = "add"
    RSH = "rsh"
    LOD = "lod"
    STR = "str"
    BGE = "bge"
    NOR = "nor"
    SUB = "sub"
    JMP = "jmp"
    MOV = "mov"
    NOP = "nop"
    IMM = "imm"
    LSH = "lsh"
    INC = "inc"
    DEC = "dec"
    NEG = "neg"
    AND = "and"
    OR = "or"  
    NOT = "not"
    XNOR = "xnor"
    XOR = "xor"
    NAND = "nand"
    BRE = "bre"
    BNE = "bne"
    BOD = "bod"
    BEV = "bev"
    BLE = "ble"
    BRZ = "brz"
    BNZ = "bnz"
    BRN = "brn"
    BRP = "brp"
    PSH = "psh"
    POP = "pop"
    CAL = "cal"
    RET = "ret"
    HLT = "hlt"
    CPY = "cpy"
    BRC = "brc"
    MLT = "mlt"
    DIV = "div"
    MOD = "mod"
    BSR = "bsr"
    BSL = "bsl"
    SRS = "srs"
    BSS = "bss"
    SETE = "sete"
    SETNE = "setne"
    SETG = "setg"
    SETL = "setl"
    SETGE = "setge"
    SETLE = "setle"
    SETC = "setc"
    SETNC = "setnc"
    LLOD = "llod"
    LSTR = "lstr"
    SDIV = "sdiv"
    SBRL = "sbrl"
    SBRG = "sbrg"
    SSETL = "ssetl"
    SSETG = "ssetg"
    SSETLE = "ssetle"
    SSETGE = "ssetge"
    ABS = "abs"
    UMLT = "umlt"
    IN = "in"
    OUT = "out"
    DW = "dw"

    def __str__(self) -> str:
        return self.value

class DefinedImmediate(enum.Enum):
    BITS = "BITS"
    MINREG = "MINREG"
    MINHEAP = "MINHEAP"
    MINSTACK = "MINSTACK"
    HEAP = "HEAP"
    MSB = "MSB"
    SMSB = "SMSB"
    MAX = "MAX"
    SMAX = "SMAX"
    UHALF = "UHALF"
    LHALF = "LHALF"

@dataclass
class PortType:
    id: int
    name: str

class Port(enum.Enum):
    TEXT = PortType(1, "text")

    @classmethod
    def from_value(cls, value: "int | str"):

        for port in Port:
            if isinstance(value, str):
                if port.value.name.lower() == value.lower():
                    return port
            else:
                if port.value.id == value:
                    return port
    
    def __str__(self) -> str:
        return f"%{self.value.name}"

@dataclass(unsafe_hash=True)
class Label:
    name: str
    def __str__(self) -> str:
        return self.name

@dataclass(unsafe_hash=True)
class GeneralRegister:
    index: int
    def __str__(self) -> str:
        return f"${self.index}"

@dataclass
class RelativeAddress:
    offset: int
    def __str__(self) -> str:
        return f"~{self.offset}"

@dataclass
class Character:
    char: str
    def __str__(self) -> str:
        return f"'{self.char}'"

class HeaderType(enum.Enum):
    BITS = enum.auto()
    MINREG = enum.auto()
    MINHEAP = enum.auto()
    RUN = enum.auto()
    MINSTACK = enum.auto()
    def __str__(self) -> str:
        return self.name.upper()

class HeaderInequalityType(enum.Enum):
    LESS_EQUAL = "<="
    EQUAL = "=="
    GREATER_EQUAL = ">="
    def __str__(self) -> str:
        return self.value

@dataclass
class Header:
    type: HeaderType
    inequality_type: HeaderInequalityType
    value: int

    def __str__(self) -> str:
        
        words: list[str] = [str(self.type)]
        if self.inequality_type != HeaderInequalityType.EQUAL:
            words.append(str(self.inequality_type))
        words.append(str(self.value))

        return " ".join(words)