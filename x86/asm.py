"This module provides types for respresenting x86 assembly"
from dataclasses import dataclass
import enum
from typing import Literal, Self
from x86.machine import Register
from error import Traceback

class Mnemonic(enum.StrEnum):
    ADC = "adc"
    ADD = "add"
    AND = "and"
    CALL = "call"
    CALLF = "callf"
    CMP = "cmp"
    CWD = "cwd"
    CWDE = "cwde"
    DEC = "dec"
    DIV = "div"
    IDIV = "idiv"
    INC = "inc"
    IMUL = "imul"
    INT = "int"
    JBE = "jbe"
    JC = "jc"
    JGE = "jge"
    JLE = "jle"
    JNO = "jno"
    JAE = "jae"
    JMP = "jmp"
    JMPF = "jmpf"
    JB = "jb"
    JL = "jl"
    JNB = "jnb"
    JNE = "jne"
    JNS = "jns"
    JNBE = "jnbe"
    JNC = "jnc"
    JNP = "jnp"
    JP = "jp"
    JO = "jo"
    JS = "js"
    JE  = "je"
    JA = "ja"
    JG = "jg"
    LEA = "lea"
    LOOP = "loop"
    LOOPNZ = "loopnz"
    LOOPZ = "loopz"
    NEG = "neg"
    NOP = "nop"
    NOT = "not"
    MOV = "mov"
    MUL = "mul"
    OR = "or"
    POP = "pop"
    POPAD = "popad"
    PUSH = "push"
    PUSHAD = "pushad"
    RCL = "rcl"
    RCR = "rcr"
    RET = "ret"
    ROL = "rol"
    ROR = "ror"
    SAL = "sal"
    SALC = "salc"
    SAR = "sar"
    SBB = "sbb"
    SUB = "sub"
    SHL = "shl"
    SHR = "shr"
    TEST = "test"
    XCHG = "xchg"
    XOR = "xor"

@dataclass(frozen=True)
class Label:
    name: str

    def __str__(self) -> str:
        return f"{self.name}"

class Segment(enum.StrEnum):
    DEFAULT = ""
    STACK = "ss"
    DATA = "ds"
    CODE = "cs"
    EXTRA = "es"

Immediate = int | Label

@dataclass(frozen=True)
class EffectiveAddress:
    segment: Segment = Segment.DEFAULT
    base: Register | None = None
    index: Register | None = None
    scale: Literal[1, 2, 4, 8] = 1
    displacement: Immediate = 0
    
    def get_register_size(self):
        if isinstance(self.base, Register):
            return self.base.value.size
        
    def __str__(self) -> str:

        terms: list[str] = []
        if self.base:
            terms.append(str(self.base))
        if self.index:
            terms.append(str(self.index) + (f"*{self.scale}" if self.scale != 1 else ""))
        if self.displacement or not terms:
            terms.append(str(self.displacement))
        
        result = "["
        if self.segment != Segment.DEFAULT:
            result += f"{self.segment}:"
        result += "+".join(terms) + "]"
        
        return result

@dataclass(frozen=True)
class Operand:
    value: Register | EffectiveAddress | Immediate

    def get_register_size(self):

        if isinstance(self.value, Register):
            return self.value.value.size
        elif isinstance(self.value, EffectiveAddress):
            return self.value.get_register_size()
        else:
            return None
    
    def as_memory(self, scale: Literal[1, 2, 4], offset: Register | int) -> EffectiveAddress:
        if isinstance(self.value, Register):
            if isinstance(offset, Register):
                memory = EffectiveAddress(base=self.value, scale=scale, index=offset)
            else:
                memory = EffectiveAddress(base=self.value, scale=scale, displacement=offset)
        elif isinstance(self.value, EffectiveAddress):
            memory = self.value
        else:
            if isinstance(offset, Register):
                memory = EffectiveAddress(displacement=self.value)
            else:
                memory = EffectiveAddress(displacement=self.value)
        
        return memory
    
    def __str__(self) -> str:
        return str(self.value)

@dataclass(frozen=True)
class ASMInstruction:
    mnemonic: Mnemonic
    operands: list[Operand]
    
    def get_immediate(self):

        for operand in self.operands:
            if isinstance(operand.value, Immediate):
                return operand.value
    
    def __str__(self) -> str:

        result = self.mnemonic.value
        operands = ", ".join([str(operand) for operand in self.operands])
        if operands:
            result += " " + str(operands)

        return result


class ASMCode:

    def __init__(self, origin: int | None, code: list[ASMInstruction | Label]) -> None:

        self.entry_point = origin
        self.code = code
    
    def add_instruction(self, mnemonic: Mnemonic, operands: list[EffectiveAddress | Register | Immediate]):

        instruction = ASMInstruction(mnemonic, [])
        for operand in operands:
            instruction.operands.append(Operand(operand))
        self.code.append(instruction)
    
    def add_move(self, destination: Register, source: Register | EffectiveAddress | Immediate):
        if destination != source:
            self.add_instruction(Mnemonic.MOV, [destination, source])
    
    #TODO: get pushad/popad instructions working
    def add_instructions_to_save_general_registers(self):
        self.add_instruction(Mnemonic.PUSH, [Register.EAX])
        self.add_instruction(Mnemonic.PUSH, [Register.EBX])
        self.add_instruction(Mnemonic.PUSH, [Register.ECX])
        self.add_instruction(Mnemonic.PUSH, [Register.EDX])
            
    def add_instructions_to_restore_general_registers(self):
        self.add_instruction(Mnemonic.POP, [Register.EDX])
        self.add_instruction(Mnemonic.POP, [Register.ECX])
        self.add_instruction(Mnemonic.POP, [Register.EBX])
        self.add_instruction(Mnemonic.POP, [Register.EAX])
    
    def __eq__(self, other: Self):
        return self.entry_point == other.entry_point and self.code == other.code
    
    def __str__(self) -> str:

        lines: list[str] = []
        for instruction in self.code:
            if isinstance(instruction, Label):
                lines.append(f"{instruction}:")
            else:
                lines.append(str(instruction))
        return "\n".join(lines)

def sum_into_effective_address(values: list[int | Label | Register]) -> EffectiveAddress | Traceback:

    registers: list[Register] = []
    displacement = 0
    symbol: Label | None = None
    for value in values:
        if isinstance(value, int):
            displacement += value
        elif isinstance(value, Register):
            registers.append(value)
        else:
            if symbol is None:
                symbol = value
            else:
                return Traceback.new(f"Effective address cannot contain two symbol references ('{symbol.name}' and '{value.name}')")
    
    if displacement and symbol:
        Traceback.new(f"Effective address that contain memory literal cannot also have symbolic reference to '{symbol.name}'")
    if symbol:
        displacement = symbol
    
    base = None
    index = None
    if len(registers) == 0:
        pass
    elif len(registers) == 1:
        base = registers[0]
    elif len(registers) == 2:
        base = registers[0]
        index = registers[1]
    else:
        return Traceback.new("Effective address cannot contain more than two registers")
    
    return EffectiveAddress(base=base, index=index, displacement=displacement)