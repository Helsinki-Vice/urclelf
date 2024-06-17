from typing import Literal
import x86
from dataclasses import dataclass
import enum

class Interupt(enum.IntEnum):
    WRITE = 4
    EXIT = 1

class File(enum.IntEnum):
    STDOUT = 1

Argument = x86.Immediate | x86.Register | None
def add_syscall(code: x86.ASMCode, type: Interupt, ebx: Argument, ecx: Argument, edx: Argument, bits: Literal[32, 64]):

    registers = x86.get_registers(bits)
    code.add_move(registers.a, type)
    if ebx is not None:
        code.add_move(registers.b, ebx)
    if ecx is not None:
        code.add_move(registers.c, ecx)
    if edx is not None:
        code.add_move(registers.d, edx)
    code.add_instruction(x86.Mnemonic.INT, [0x80])

def add_syscall_fwrite(code: x86.ASMCode, char_pointer: int | x86.Register | x86.Label, size: int | x86.Register | x86.Label, file_descriptor: int | x86.Register | x86.Label, bits: Literal[32, 64]):
    add_syscall(code, Interupt.WRITE, file_descriptor, char_pointer, size, bits)
    
def add_syscall_exit(code: x86.ASMCode, exit_code: Argument, bits: Literal[32, 64]):
    add_syscall(code, Interupt.EXIT, exit_code, None, None, bits)