"This module takes a URCL concrete syntax tree and parses it into a abstract syntax tree"
#TODO: make this module actully work
from dataclasses import dataclass
import typing
import enum

import urcl.urclcst as cst
import error
Mnemonic = cst.Mnemonic

ZERO_OPERAND_MNEMONICS = [
    Mnemonic.HLT,
    Mnemonic.NOP,
    Mnemonic.RET
]
BRANCH_MNEMONICS = [
    Mnemonic.JMP,
    Mnemonic.BRZ,
    Mnemonic.BNZ,
    Mnemonic.BLE,
    Mnemonic.BGE,
    Mnemonic.BRE,
    Mnemonic.BNE,
    Mnemonic.BRP,
    Mnemonic.BRN,
    Mnemonic.BRC,
    Mnemonic.CAL,
    Mnemonic.BOD,
    Mnemonic.BEV,
    Mnemonic.SBRG
]

TWO_OPERAND_CONDITION_JUMP_MNEMONICS = [
    Mnemonic.BRZ,
    Mnemonic.BNZ,
    Mnemonic.BRP,
    Mnemonic.BRN,
    Mnemonic.BOD,
    Mnemonic.BEV
]

THREE_OPERAND_CONDITION_JUMP_MNEMONICS = [
    Mnemonic.BLE,
    Mnemonic.BGE,
    Mnemonic.BRE,
    Mnemonic.BNE,
    Mnemonic.BRC,
    Mnemonic.SBRG
]

TWO_OPERAND_ARITHMETIC_MNEMONICS = [
    Mnemonic.RSH,
    Mnemonic.MOV,
    Mnemonic.IMM,
    Mnemonic.LSH,
    Mnemonic.INC,
    Mnemonic.DEC,
    Mnemonic.NEG,
    Mnemonic.NOT,
    Mnemonic.ABS
]

THREE_OPERAND_ARITHMETIC_MNEMONICS = [
    Mnemonic.ADD,
    Mnemonic.NOR,
    Mnemonic.SUB,
    Mnemonic.AND,
    Mnemonic.OR,
    Mnemonic.XNOR,
    Mnemonic.NAND,
    Mnemonic.MLT,
    Mnemonic.DIV,
    Mnemonic.MOD,
    Mnemonic.BSR,
    Mnemonic.BSL,
    Mnemonic.SDIV,
    Mnemonic.BSS
]

@dataclass
class Headers:
    bits: int
    minreg: int
    minheap: int
    run: int
    minstack: int

class OneInputOperation(enum.Enum):
    RSH = Mnemonic.RSH
    MOV = Mnemonic.MOV
    IMM = Mnemonic.IMM
    LSH = Mnemonic.LSH
    INC = Mnemonic.INC
    DEC = Mnemonic.DEC
    NEG = Mnemonic.NEG
    NOT = Mnemonic.NOT
    ABS = Mnemonic.ABS
    UMLT = Mnemonic.UMLT

class TwoInputOperation(enum.Enum):
    ADD = Mnemonic.ADD
    NOR = Mnemonic.NOR
    SUB = Mnemonic.SUB
    AND = Mnemonic.AND
    OR = Mnemonic.OR
    XNOR = Mnemonic.XNOR
    XOR = Mnemonic.XOR
    NAND = Mnemonic.NAND
    MLT = Mnemonic.MLT
    DIV = Mnemonic.DIV
    MOD = Mnemonic.MOD
    BSR = Mnemonic.BSR
    BSL = Mnemonic.BSL
    BSS = Mnemonic.BSS
    SETE = Mnemonic.SETE
    SETNE = Mnemonic.SETNE
    SETG = Mnemonic.SETG
    SETL = Mnemonic.SETL
    SETGE = Mnemonic.SETGE
    SETLE = Mnemonic.SETLE
    SETC = Mnemonic.SETC
    SETNC = Mnemonic.SETNC
    SDIV = Mnemonic.SDIV
    SSETL = Mnemonic.SSETL
    SSETG = Mnemonic.SSETG
    SSETLE = Mnemonic.SSETLE
    SSETGE = Mnemonic.SSETGE
    UMLT = Mnemonic.UMLT

# FIXME: type hell below

@dataclass
class OneInputInstruction:
    operation: OneInputOperation
    destination: cst.OperandCSTNode
    operand: cst.OperandCSTNode

    def __str__(self) -> str:
        return f"{self.operation.name} {self.destination} {self.operand}"

@dataclass
class TwoInputInstruction:
    operation: TwoInputOperation
    destination: cst.OperandCSTNode
    operand_1: cst.OperandCSTNode
    operand_2: cst.OperandCSTNode

    def __str__(self) -> str:
        return f"{self.operation.name} {self.destination} {self.operand_1} {self.operand_2}"

Calculation = typing.Union[OneInputInstruction, TwoInputInstruction]

class ConditionType(enum.Enum):
    EQUAL = enum.auto()
    NOT_EQUAL = enum.auto()
    LESS = enum.auto()
    LESS_EQUAL = enum.auto()
    GREATER = enum.auto()
    GREATER_EQUAL = enum.auto()
    EVEN = enum.auto()
    ODD = enum.auto()
    POSITIVE = enum.auto()
    NEGATIVE = enum.auto()

class ZeroOperandInstruction(enum.Enum):
    HLT = Mnemonic.HLT
    NOP = Mnemonic.NOP
    RET = Mnemonic.RET

@dataclass
class OneInputCondition:
    type: ConditionType
    operand: int

@dataclass
class TwoInputCondition:
    type: ConditionType
    operand_1: int
    operand_2: int

@dataclass
class JumpInstruction:
    destination: int
    condition: "OneInputCondition | TwoInputCondition"
    
    def __str__(self) -> str:

        if isinstance(self.condition, OneInputCondition):
            return f"BRANCH to {self.destination} if {self.condition.operand} {self.condition.type.name}"
        else:
            return f"BRANCH TO {self.destination} if {self.condition.operand_1} {self.condition.type.name} {self.condition.operand_2}"
"""
@dataclass
class Instruction:
    calculation: Calculation
    jump_target: int
    condition: int

    def __str__(self) -> str:
        return f"{self.calculation} (to {self.jump_target}) (if {self.condition})"
"""
Instruction = typing.Union[Calculation, JumpInstruction, ZeroOperandInstruction]
class CodePath:
    
    def __init__(self) -> None:

        self.next_path: "tuple[CodePath, CodePath] | None"
        self.code: list[Instruction] = []
    
    def add(self, instruction: Instruction):
        self.code.append(instruction)

class AST:

    def __init__(self, headers: Headers, code: list[Instruction], data_section: bytearray) -> None:
        
        self.headers = headers
        self.code: list[Instruction] = code
        self.data_section = data_section
    
    @classmethod
    def from_cst(cls, cst_code: cst.CST):

        instructions: list[Instruction] = []
        data = bytearray()
        code_index = 0
        instruction_index = 0
        labels: dict[cst.Label, int] = {}
        while code_index < len(cst_code.lines):
            instruction = cst_code.lines[code_index]
            if isinstance(instruction, cst.Label):
                for label in labels:
                    if instruction.name == label.name:
                        return error.Traceback([error.Message(f"Label '{instruction.name}' already defined on line {label}#FIXME: add line/column number", 0, 0)], [])
                labels.update({instruction: instruction_index})
                code_index += 1
                continue
            if instruction.mnemonic == Mnemonic.DW:
                if len(instruction.operands) == 1:
                    pass
                else:
                    return error.Traceback([error.Message(f"{instruction.mnemonic.name} takes no operands ({len(instruction.operands)} supplied)", instruction.line_number, instruction.column_number)], [])
            elif instruction.mnemonic in ZERO_OPERAND_MNEMONICS:
                if len(instruction.operands) == 0:
                    instructions.append(ZeroOperandInstruction(instruction.mnemonic))
                else:
                    return error.Traceback([error.Message(f"{instruction.mnemonic.name} takes 1 operand ({len(instruction.operands)} supplied)", instruction.line_number, instruction.column_number)], [])
            elif instruction.mnemonic in TWO_OPERAND_ARITHMETIC_MNEMONICS:
                if len(instruction.operands) == 2:
                    if not isinstance(instruction.operands[0].value, cst.GeneralRegister):
                        return error.Traceback([error.Message(f"Destination operand to {instruction.mnemonic.name} must be a register", instruction.operands[0].line_number, instruction.operands[1].column_number)], [])
                    instructions.append(OneInputInstruction(OneInputOperation(instruction.mnemonic), instruction.operands[0], instruction.operands[1]))
                else:
                    return error.Traceback([error.Message(f"{instruction.mnemonic.name} takes 2 operands ({len(instruction.operands)} supplied)", instruction.line_number, instruction.column_number)], [])
            elif instruction.mnemonic in THREE_OPERAND_ARITHMETIC_MNEMONICS:
                if len(instruction.operands) == 3:
                    if not isinstance(instruction.operands[0].value, cst.GeneralRegister):
                        return error.Traceback([error.Message(f"Destination operand to {instruction.mnemonic.name} must be a register", instruction.operands[0].line_number, instruction.operands[1].column_number)], [])
                    instructions.append(TwoInputInstruction(TwoInputOperation(instruction.mnemonic), instruction.operands[0], instruction.operands[1], instruction.operands[2]))
                else:
                    return error.Traceback([error.Message(f"{instruction.mnemonic.name} takes 3 operands ({len(instruction.operands)} supplied)", instruction.line_number, instruction.column_number)], [])
            else:
                return error.Traceback([error.Message(f"Unsuported instruction {instruction.mnemonic.name}", instruction.line_number, instruction.column_number)], [])
            
            code_index += 1
            instruction_index += 1
        
        return AST(Headers(0,0,0,0,0), instructions, bytearray())
    
    def __str__(self) -> str:
        
        lines: list[str] = []
        for index, instruction in enumerate(self.code):
            lines.append(str(instruction))
        
        return "\n".join(lines)