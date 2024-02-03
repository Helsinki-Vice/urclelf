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
    UNIX = enum.auto()
    MS_DOS = enum.auto()
    UEFI = enum.auto()

class ExecutableFormat(enum.Enum):
    FLAT = enum.auto()
    ELF = enum.auto()
    MS_PE = enum.auto()

class ExecutableType(enum.Enum):
    OBJECT = enum.auto()
    EXECUTABLE = enum.auto()

@dataclass
class Target:
    isa: Isa
    byte_order: ByteOrder
    os_abi: OsAbi

"""
@dataclass
class URCLMemoryLayout:
    load_to_address: int | None
    entry_point: int | None
    heap_address: int | None
    heap_size: int | None
    heap_is_preloaded: bool | None
    stack_top_address: int | None
    stack_size: int | None
    stack_is_preloaded: bool | None
    stack_pointer_is_preset: bool | None
"""

@dataclass
class CompileOptions:
    target: Target
    #memory: URCLMemoryLayout
    executable_type: ExecutableType
    executable_format: ExecutableFormat
    is_main: bool
