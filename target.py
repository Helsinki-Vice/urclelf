from dataclasses import dataclass
import enum

class Isa(enum.Enum):
    X86 = enum.auto()
    X64 = enum.auto()
    ARM32 = enum.auto()
    RISCV = enum.auto()

class ByteOrder(enum.Enum):
    LITTLE = enum.auto()
    BIG = enum.auto()

class OsAbi(enum.Enum):
    SYSV = enum.auto()
    WINDOWS_NT_32 = enum.auto()
    UEFI = enum.auto()

class ExecutableFormat(enum.Enum):
    FLAT = enum.auto()
    ELF = enum.auto()
    COFF = enum.auto()

class ExecutableType(enum.Enum):
    OBJECT = enum.auto()
    EXECUTABLE = enum.auto()

@dataclass
class Target:
    isa: Isa
    byte_order: ByteOrder
    os_abi: OsAbi

@dataclass
class CompileOptions:
    target: Target
    executable_type: ExecutableType
    executable_format: ExecutableFormat
    is_main: bool
