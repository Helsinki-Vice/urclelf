"This module contains all of the logic required to convert x86 assembly into machine code."
from x86.encoding.encode import assemble
from x86.encoding.output import AssembledMachineCode

__all__ = ["assemble", "AssembledMachineCode"]