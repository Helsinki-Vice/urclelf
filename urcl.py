import enum
from dataclasses import dataclass
from typing import Union

import lex
from error import Traceback, Message

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
    BNC = "bnc"
    OUT = "out"
    DW = "dw"

    def __str__(self) -> str:
        return self.value

class OperandType(enum.Enum):
    INTEGER = enum.auto()
    LABEL = enum.auto()
    GENERAL_REGISTER = enum.auto()
    CHARACTER = enum.auto()

@dataclass
class InstructionFormat:
    mnemonic: Mnemonic
    operands: list[set[OperandType]]

@dataclass
class Label:

    name: str
    def __str__(self) -> str:
        return self.name

@dataclass
class GeneralRegister:

    index: int
    def __str__(self) -> str:
        return f"${self.index}"

@dataclass
class RelativeAddress:

    offset: int
    def __str__(self) -> str:
        return f"~{self.offset}"

Operand = Union[Label, GeneralRegister, int, RelativeAddress]

class Instruction:

    def __init__(self, mnemonic: Mnemonic, operands: list[Operand]) -> None:

        self.mnemonic = mnemonic
        self.operands = operands
    
    @classmethod
    def parse(cls, source: lex.TokenStream) -> "Instruction | Traceback":

        words = source
        if not words:
            return Traceback([Message("Instruction must not be empty.", 0, 0)], [])
        if not words.tokens[0].value:
            return Traceback([Message("Instruction must have a mnemoric", 0, 0)], [])
        try:
            mnemonic = Mnemonic(str(words.tokens[0].value).lower())
        except ValueError:
            return Traceback([Message(f"Unknown mnemoric '{words.tokens[0].value}'", 0, 0)], [])
        operands: list[Operand] = []
        for token in words.tokens[1:]:
            if token.value is None:
                return Traceback([Message("Operand must not be empty.", 0, 0)], [])
            if token.type == lex.TokenType.LABEL:
                operands.append(Label(str(token.value)))
            elif token.type == lex.TokenType.GENERAL_REGISTER:
                if not isinstance(token.value, int):
                    return Traceback([Message(f"Invalid register number: '{token.value}'", 0, 0)], [])
                operands.append(GeneralRegister(token.value))
            elif token.type == lex.TokenType.INTEGER:
                if not isinstance(token.value, int):
                    return Traceback([Message(f"Invalid integer: '{token.value}'", 0, 0)], [])
                operands.append(token.value)
            elif token.type == lex.TokenType.RELATIVE_JUMP:
                if not isinstance(token.value, int):
                    return Traceback([Message(f"line {token.line_number}:{token.column_number} - Invalid relative jump: {token.value}", 0, 0)], [])
                operands.append(RelativeAddress(token.value))
            else:
                pass
        
        return Instruction(mnemonic, operands)
    
    def get_jump_target(self):

        if self.mnemonic not in [Mnemonic.JMP, Mnemonic.BNZ]:
            return None
        if not self.operands:
            return None
        
        return self.operands[0]
    
    def get_destination_register(self):

        if not self.operands:
            return None
        if isinstance(self.operands[0], GeneralRegister):
            return self.operands[0]
    
    @classmethod
    def parse_str(cls, source: str):

        tokens = lex.tokenize(source)
        return Instruction.parse(tokens)
    
    def __str__(self) -> str:
        
        operands = " ".join([str(operand) for operand in self.operands])
        return f"{self.mnemonic.value} {operands}"

class Program:

    def __init__(self) -> None:
        
        self.code: "list[Instruction | Label]" = []
    
    @classmethod
    def parse(cls, source: lex.TokenStream) -> "Program | Traceback":

        program = Program()
        for line in source.split_lines():
            words = line.tokens
            if not words:
                continue
            if words[0].type == lex.TokenType.LABEL:
                if not words[0].value:
                    return Traceback([Message(f"Malformed label token has no value (?)", words[0].line_number, words[0].column_number)], [])
                if len(words) > 1:
                    return Traceback([Message(f"Unexpected token after label {words[0].value}: '{words[1].value}'", words[1].line_number, words[1].column_number)], [])
                program.code.append(Label(str(words[0].value)))
                continue
            instruction = Instruction.parse(line)
            if not isinstance(instruction, Instruction):
                instruction.push(Message(f"Invalid instruction", 0, 0))
                return instruction
            program.code.append(instruction)
        return program
    
    @classmethod
    def parse_str(cls, source: str) -> "Program | Traceback":

        tokens = lex.tokenize(source)
        return Program.parse(tokens)
    
    def __str__(self) -> str:
        return "\n".join([str(line) for line in self.code])

def main():
    with open("./source.urcl", "r") as file:
        source = file.read()
    print(Program.parse_str(source))

if __name__ == "__main__":
    main()