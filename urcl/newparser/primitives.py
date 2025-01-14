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
    BRL = "brl"
    BRG = "brg"
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
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    UP = "UP"
    DOWN = "DOWN"

@dataclass
class PortType:
    id: int
    name: str

class Port(enum.Enum):
    CPUBUS = PortType(0, "CPUBUS")
    TEXT = PortType(1, "TEXT")
    NUMB = PortType(2, "NUMB")
    SUPPORTED = PortType(5, "SUPPORTED")
    SPECIAL = PortType(6, "SPECIAL")
    PROFILE = PortType(7, "PROFILE")
    X = PortType(8, "X")
    Y = PortType(9, "Y")
    COLOR = PortType(10, "COLOR")
    BUFFER = PortType(11, "BUFFER")
    FREEZE = PortType(12, "FREEZE")
    UNFREEZE = PortType(13, "UNFREEZE")
    CLEAR = PortType(14, "CLEAR")
    GSPECIAL = PortType(15, "GSPECIAL")
    ASCII8 = PortType(16, "ASCII8")
    CHAR5 = PortType(17, "CHAR5")
    CHAR6 = PortType(18, "CHAR6")
    ASCII7 = PortType(19, "ASCII7")
    UTF8 = PortType(20, "UTF8")
    TSPECIAL = PortType(23, "TSPECIAL")
    INT = PortType(24, "INT")
    UINT = PortType(25, "UINT")
    BIN = PortType(26, "BIN")
    HEX = PortType(27, "HEX")
    FLOAT = PortType(28, "FLOAT")
    FIXED = PortType(29, "FIXED")
    N_SPECIAL = PortType(31, "N_SPECIAL")
    ADDR = PortType(32, "ADDR")
    BUS = PortType(33, "BUS")
    SSPECIAL = PortType(39, "SSPECIAL")
    RNG = PortType(40, "RNG")
    NOTE = PortType(41, "NOTE")
    INSTR = PortType(42, "INSTR")
    NLEG = PortType(43, "NLEG")
    WAIT = PortType(44, "WAIT")
    NADDR = PortType(45, "NADDR")
    DATA = PortType(46, "DATA")
    MSPECIAL = PortType(47, "MSPECIAL")
    GAMEPAD = PortType(65, "GAMEPAD")
    GAMEPAD_INFO = PortType(66, "GAMEPAD_INFO")
    KEY = PortType(67, "KEY")
    MOUSE_X = PortType(68, "MOUSE_X")
    MOUSE_Y = PortType(69, "MOUSE_Y")
    MOUSE_DX = PortType(70, "MOUSE_DX")
    MOUSE_DY = PortType(71, "MOUSE_DY")
    MOUSE_DWHEEL = PortType(72, "MOUSE_DWHEEL")
    MOUSE_BUTTONS = PortType(73, "MOUSE_BUTTONS")

    @classmethod
    def from_value(cls, value: int | str):

        for port in Port:
            if isinstance(value, str):
                if port.value.name.upper() == value.upper():
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
        return f".{self.name}"

@dataclass(unsafe_hash=True)
class GeneralRegister:
    index: int
    def __str__(self) -> str:
        return f"${self.index}"

@dataclass(unsafe_hash=True)
class HeapAddress:
    index: int
    def __str__(self) -> str:
        return f"#{self.index}"

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

@dataclass(unsafe_hash=True)
class BasePointer:
    def __str__(self) -> str:
        return "BP"

@dataclass(unsafe_hash=True)
class StackPointer:
    def __str__(self) -> str:
        return "SP"

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