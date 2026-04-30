from dataclasses import dataclass
from typing import Literal, Callable

import urcl
import x86
from error import Traceback
from translation.instructioninfo import InstructionInfo

@dataclass
class InstructionFamily:
    mnemonics: list[urcl.Mnemonic]
    compile: Callable[[Literal[16, 32, 64], InstructionInfo], x86.ASMCode | Traceback]
    operand_count: int
    requires_jump_target: bool
    writes_to_register: bool
    required_sources: int
    source_start_index: int