from dataclasses import dataclass
import enum
from error import Traceback

class Isa(enum.Enum):
    X86 = "x86"
    X64 = "x64"
    ARM32 = "arm32"

class ByteOrder(enum.Enum):
    LITTLE = enum.auto()
    BIG = enum.auto()

class OsAbi(enum.Enum):
    SYSV = enum.auto()
    UEFI = enum.auto()

class ExecutableFormat(enum.Enum):
    FLAT = enum.auto()
    ELF = enum.auto()
    ASM = enum.auto()

class ExecutableType(enum.Enum):
    OBJECT = enum.auto()
    EXECUTABLE = enum.auto()

@dataclass
class Target:
    isa: Isa
    byte_order: ByteOrder
    os_abi: OsAbi

    def get_word_size(self):

        if self.isa == Isa.X64:
            return 64
        elif self.isa in [Isa.X86, Isa.ARM32]:
            return 32
        
        return Traceback.new(f"The architecture {self.isa} is not currently supported")

@dataclass
class CompileOptions:
    target: Target
    executable_type: ExecutableType
    executable_format: ExecutableFormat
    is_main: bool
