import x86
from dataclasses import dataclass
import enum
SEGMENT_START_ADDRESS = 0x8048000

class Interupt(enum.IntEnum):
    WRITE = 4
    EXIT = 1

class File(enum.IntEnum):
    STDOUT = 1

Argument = x86.Immediate | x86.Register | None
def add_syscall(code: x86.ASMCode, type: Interupt, ebx: Argument, ecx: Argument, edx: Argument):
    code.add_move(x86.Register.EAX, type)
    if ebx is not None:
        code.add_move(x86.Register.EBX, ebx)
    if ecx is not None:
        code.add_move(x86.Register.ECX, ecx)
    if edx is not None:
        code.add_move(x86.Register.EDX, edx)
    code.add_instruction(x86.Mnemonic.INT, [0x80])

def add_syscall_fwrite(code: x86.ASMCode, char_pointer: int | x86.Register | x86.Label, size: int | x86.Register | x86.Label, file_descriptor: int | x86.Register | x86.Label):
    add_syscall(code, Interupt.WRITE, file_descriptor, char_pointer, size)
    
def add_syscall_exit(code: x86.ASMCode, exit_code: Argument):
    add_syscall(code, Interupt.EXIT, exit_code, None, None)