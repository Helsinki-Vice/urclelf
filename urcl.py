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
    MLT = "mlt"
    DIV = "div"
    MOD = "mod"
    BSR = "bsr"
    BSL = "bsl"
    SRS = "srs"
    BSS = "bss"
    SETE = "sete"
    SETNE = "setne"
    SETG = "setg"
    SETL = "setl"
    SETGE = "setge"
    SETLE = "setle"
    SETC = "setc"
    SETNC = "setnc"
    LLOD = "llod"
    LSTR = "lstr"
    SDIV = "sdiv"
    SBRL = "sbrl"
    SBRG = "sbrg"
    SSETL = "ssetl"
    SSETG = "ssetg"
    SSETLE = "ssetle"
    SSETGE = "ssetge"
    ABS = "abs"
    UMLT = "umlt"
    IN = "in"
    OUT = "out"
    DW = "dw"

    def __str__(self) -> str:
        return self.value

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
    Mnemonic.CAL
]

class DefinedImmediate(enum.Enum):
    BITS = "BITS"
    MINREG = "MINREG"
    MINHEAP = "MINHEAP"
    MINSTACK = "MINSTACK"
    HEAP = "HEAP"
    MSB = "MSB"
    SMSB = "SMSB"
    MAX = "MAX"
    SMAX = "SMAX"
    UHALF = "UHALF"
    LHALF = "LHALF"

@dataclass
class PortType:
    id: int
    name: str

class Port(enum.Enum):
    TEXT = PortType(1, "text")

    @classmethod
    def from_value(cls, value: "int | str"):

        for port in Port:
            if isinstance(value, str):
                if port.value.name.lower() == value.lower():
                    return port
            else:
                if port.value.id == value:
                    return port
    
    def __str__(self) -> str:
        return f"%{self.value.name}"

class OperandType(enum.Enum):
    INTEGER = enum.auto()
    LABEL = enum.auto()
    GENERAL_REGISTER = enum.auto()
    CHARACTER = enum.auto()
    PORT = enum.auto

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

@dataclass
class Character:

    char: str
    def __str__(self) -> str:
        return f"'{self.char}'"

Operand = Union[Label, GeneralRegister, int, RelativeAddress, Character, Port]

class Instruction:

    def __init__(self, mnemonic: Mnemonic, operands: list[Operand]) -> None:

        self.mnemonic = mnemonic
        self.operands = operands
    
    @classmethod
    def parse(cls, words: lex.TokenStream) -> "Instruction | Traceback":

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
                return Traceback([Message("Operand must not be empty.", token.line_number, token.column_number)], [])
            
            if token.type == lex.TokenType.LABEL:
                operands.append(Label(str(token.value)))
            
            elif token.type == lex.TokenType.GENERAL_REGISTER:
                if not isinstance(token.value, int):
                    return Traceback([Message(f"Invalid register number: '{token.value}'", token.line_number, token.column_number)], [])
                operands.append(GeneralRegister(token.value))
            
            elif token.type == lex.TokenType.INTEGER:
                if not isinstance(token.value, int):
                    return Traceback([Message(f"Invalid integer: '{token.value}'", token.line_number, token.column_number)], [])
                operands.append(token.value)
            
            elif token.type == lex.TokenType.RELATIVE_JUMP:
                if not isinstance(token.value, int):
                    return Traceback([Message(f"Invalid relative jump: '{token.value}'", token.line_number, token.column_number)], [])
                operands.append(RelativeAddress(token.value))
            
            elif token.type == lex.TokenType.CHARACTER:
                if not isinstance(token.value, str) or not token.value:
                    return Traceback([Message(f"Invalid character: '{token.value}'", token.line_number, token.column_number)], [])
                operands.append(Character(token.value))
            
            elif token.type == lex.TokenType.PORT:
                if not isinstance(token.value, str) or not token.value:
                    return Traceback([Message(f"Invalid Port: '{token.value}'", token.line_number, token.column_number)], [])
                port = Port.from_value(token.value)
                if port:
                    operands.append(port)
                else:
                    return Traceback([Message(f"Unknown Port: '{token.value}'", token.line_number, token.column_number)], [])
            
            elif token.type == lex.TokenType.MACRO:
                if isinstance(token.value, str):
                    try:
                        defined_immediate = DefinedImmediate(token.value.upper())
                    except ValueError:
                        defined_immediate = None
                else:
                    defined_immediate = None
                if not defined_immediate:
                    return Traceback([Message(f"Invalid defined immediate: '{token.value}'", token.line_number, token.column_number)], [])
                if defined_immediate == DefinedImmediate.BITS:
                    operands.append(32)
                elif defined_immediate == DefinedImmediate.MINREG:
                    operands.append(4)
                elif defined_immediate == DefinedImmediate.MINHEAP:
                    operands.append(0) #TODO: implement headers
                elif defined_immediate == DefinedImmediate.MINSTACK:
                    operands.append(20)
                elif defined_immediate == DefinedImmediate.HEAP:
                    operands.append(0)
                elif defined_immediate == DefinedImmediate.MSB:
                    operands.append(2**31)
                elif defined_immediate == DefinedImmediate.SMSB:
                    operands.append(2**30)
                elif defined_immediate == DefinedImmediate.MAX:
                    operands.append(2**32 - 1)
                elif defined_immediate == DefinedImmediate.SMAX:
                    operands.append(2**31 - 1)
                elif defined_immediate == DefinedImmediate.UHALF:
                    operands.append((2**16 - 1) << 16)
                elif defined_immediate == DefinedImmediate.LHALF:
                    operands.append(2**16)
                else:
                    return Traceback([Message(f"Defined immediate: '@{defined_immediate.name}' not yet implemented", token.line_number, token.column_number)], [])
            
            else:
                return Traceback([Message(f"Unsupported operand '{token}'", token.line_number, token.column_number)], [])
        
        return Instruction(mnemonic, operands)
    
    def get_jump_target(self):

        if self.mnemonic not in [Mnemonic.JMP, Mnemonic.BNZ, Mnemonic.CAL, Mnemonic.BRZ, Mnemonic.BRP]:
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
        if not isinstance(tokens, lex.TokenStream):
            error = tokens
            error.push(Message("Invalid tokens", 0, 0))
            return error
        
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

            if words[0].type == lex.TokenType.MACRO:
                continue # The lexer already expanded macros
            
            instruction = Instruction.parse(line)
            if not isinstance(instruction, Instruction):
                instruction.push(Message(f"Invalid instruction", 0, 0))
                return instruction
            
            program.code.append(instruction)
        return program
    
    @classmethod
    def parse_str(cls, source: str) -> "Program | Traceback":

        tokens = lex.tokenize(source)
        if not isinstance(tokens, lex.TokenStream):
            error = tokens
            error.push(Message("Invalid tokens", 0, 0))
            return error
        
        return Program.parse(tokens)
    
    def __str__(self) -> str:
        return "\n".join([str(line) for line in self.code])

def main():
    with open("./source.urcl", "r") as file:
        source = file.read()
    print(Program.parse_str(source))

if __name__ == "__main__":
    main()