"This module takes a stream of URCL tokens and parses it into a concrete syntax tree"
import enum
from dataclasses import dataclass
from typing import Union, Type, Self, Generic, TypeVar

from urcl.types import Mnemonic, Label, RelativeAddress, Character, Port, GeneralRegister, DefinedImmediate, BasePointer, StackPointer
import urcl.lex
from error import Traceback, Message

T = TypeVar("T")
@dataclass
class Terminal(Generic[T]):
    value: T
    line_number: int
    column_number: int

    def __str__(self) -> str:
        return str(self.value)


class OperandType(enum.Enum):
    INTEGER = enum.auto()
    LABEL = enum.auto()
    GENERAL_REGISTER = enum.auto()
    CHARACTER = enum.auto()
    PORT = enum.auto()
    RELATIVE_ADDERESS = enum.auto()
    ARRAY = enum.auto()

@dataclass
class OperandCSTNode:
    value: Union[Label, GeneralRegister, int, RelativeAddress, Character, Port, DefinedImmediate, str | BasePointer | StackPointer | list[Self]]
    line_number: int
    column_number: int

    def __str__(self) -> str:
        return str(self.value)

@dataclass
class OperandParseResult:
    data: OperandCSTNode | str | None
    tokens_consumed: int

    @classmethod
    def miss(cls):
        return OperandParseResult(None, 0)
    
def parse_operand(tokens: urcl.lex.TokenStream) -> OperandParseResult:
        
            index = 0
            
            token = tokens.tokens[index]
            if token.type == urcl.lex.TokenType.LABEL:
                return OperandParseResult(OperandCSTNode(Label(str(token.value)), token.line_number, token.column_number), 1)
            
            elif isinstance(token.value, GeneralRegister):
                return OperandParseResult(OperandCSTNode(token.value, token.line_number, token.column_number), 1)
            
            elif token.type == urcl.lex.TokenType.INTEGER:
                if not isinstance(token.value, int):
                    return OperandParseResult(f"Invalid integer: '{token.value}'", 0)
                return OperandParseResult(OperandCSTNode(token.value, token.line_number, token.column_number), 1)
            
            elif token.type == urcl.lex.TokenType.RELATIVE_JUMP:
                if not isinstance(token.value, int):
                    return OperandParseResult(f"Invalid relative jump: '{token.value}'", 0)
                return OperandParseResult(OperandCSTNode(RelativeAddress(token.value), token.line_number, token.column_number), 1)
            
            elif token.type == urcl.lex.TokenType.CHARACTER:
                if not isinstance(token.value, str) or not token.value:
                    return OperandParseResult(f"Invalid character: '{token.value}'", 1)
                return OperandParseResult(OperandCSTNode(Character(token.value), token.line_number, token.column_number), 1)
            
            elif token.type == urcl.lex.TokenType.STRING:
                if not isinstance(token.value, str) or not token.value:
                    return OperandParseResult(f"Invalid string: '{token.value}'", 1)
                return OperandParseResult(OperandCSTNode(token.value, token.line_number, token.column_number), 1)
            
            elif token.type == urcl.lex.TokenType.IDENTIFIER:
                if not isinstance(token.value, str) or not token.value:
                    return OperandParseResult(f"Invalid identifier: '{token.value}'", 1)
                if token.value.lower() == "bp":
                    return OperandParseResult(OperandCSTNode(BasePointer(), token.line_number, token.column_number), 1)
                elif token.value.lower() == "sp":
                    return OperandParseResult(OperandCSTNode(StackPointer(), token.line_number, token.column_number), 1)
                else:
                    return OperandParseResult.miss()
            
            elif token.type == urcl.lex.TokenType.PORT:
                if not isinstance(token.value, str) or not token.value:
                    return OperandParseResult(f"Invalid Port: '{token.value}'", 1)
                port = Port.from_value(token.value)
                if port:
                    return OperandParseResult(OperandCSTNode(port, token.line_number, token.column_number), 1)
                else:
                    return OperandParseResult(f"Unknown Port: '{token.value}'", 1)
            
            elif token.type == urcl.lex.TokenType.MACRO:
                if isinstance(token.value, str):
                    try:
                        defined_immediate = DefinedImmediate(token.value.upper())
                    except ValueError:
                        defined_immediate = None
                else:
                    defined_immediate = None
                if not defined_immediate:
                    return OperandParseResult(f"Invalid defined immediate: '{token.value}'", 1)
                return OperandParseResult(OperandCSTNode(defined_immediate, token.line_number, token.column_number), 1)
            
            elif token.type == urcl.lex.TokenType.LEFT_BRACKET:

                pp = 0
                while index < len(tokens):
                    token = tokens.tokens[index]
                    if token.type == urcl.lex.TokenType.RIGHT_BRACKET:
                        break
                    pp += 1 
                    index += 1
                else:
                    return OperandParseResult("Array literal was not closed", 0)

                return OperandParseResult(OperandCSTNode(pp, tokens.tokens[0].line_number, tokens.tokens[0].column_number), index + 1)
        
            return OperandParseResult.miss()

class InstructionCSTNode:

    def __init__(self, mnemonic: Mnemonic, operands: list[OperandCSTNode], line_number:int=0, column_number:int=0) -> None:

        self.mnemonic = mnemonic
        self.operands = operands
        self.line_number = line_number
        self.column_number = column_number
    
    @classmethod
    def parse(cls, tokens: urcl.lex.TokenStream) -> "InstructionCSTNode | Traceback":

        if not tokens:
            return Traceback([Message("Instruction must not be empty.", 0, 0)], [])
        if not tokens.tokens[0].value:
            return Traceback([Message("Instruction must have a mnemoric", tokens.tokens[0].line_number, tokens.tokens[0].column_number)], [])
        try:
            mnemonic = Mnemonic(str(tokens.tokens[0].value).lower())
        except ValueError:
            return Traceback([Message(f"Unknown mnemonic '{tokens.tokens[0].value}'", tokens.tokens[0].line_number, tokens.tokens[0].column_number)], [])
        
        operands: list[OperandCSTNode] = []
        index = 1
        while index < len(tokens):
            result = parse_operand(urcl.lex.TokenStream(tokens.tokens[index:]))
            if isinstance(result.data, OperandCSTNode):
                operands.append(result.data)
                index += result.tokens_consumed
            elif isinstance(result.data, str):
                error = Traceback([Message(result.data, tokens.tokens[index].line_number, tokens.tokens[index].column_number)], [])
                error.elaborate("Invalid operand")
                return error
            else:
                return Traceback([Message("Invalid operand", tokens.tokens[index].line_number, tokens.tokens[index].column_number)], [])
        
        return InstructionCSTNode(mnemonic, operands, tokens.tokens[0].line_number, tokens.tokens[0].column_number)
    """
    def get_jump_target(self):

        if self.mnemonic not in BRANCH_MNEMONICS:
            return None
        if not self.operands:
            return None
        
        return self.operands[0]
    
    def get_destination_register(self):

        if not self.operands:
            return None
        if isinstance(self.operands[0], GeneralRegister):
            return self.operands[0]
    """
    
    def __str__(self) -> str:
        
        operands = " ".join([str(operand) for operand in self.operands])
        return f"{self.mnemonic.value} {operands}"

Line = InstructionCSTNode | Terminal[urcl.types.Label] | Terminal[urcl.types.Header]

def parse_line():
    ...

class CST:

    def __init__(self) -> None:
        
        self.lines: list[Line] = []
    
    @classmethod
    def from_tokens(cls, source: urcl.lex.TokenStream) -> "CST | Traceback":

        cst = CST()
        macros: dict[str, list[urcl.lex.Token]] = {}
        for line in source.split_lines():
            tokens = line.tokens
            
            if not tokens:
                continue
            
            if tokens[0].type == urcl.lex.TokenType.LABEL:
                if not tokens[0].value:
                    return Traceback([Message(f"Label must not be empty", tokens[0].line_number, tokens[0].column_number)], [])
                if len(tokens) > 1:
                    return Traceback([Message(f"Unexpected {tokens[1].type.value} after label .{tokens[0].value}", tokens[1].line_number, tokens[1].column_number)], [])
                cst.lines.append(Terminal(urcl.types.Label(str(tokens[0].value)), tokens[0].line_number, tokens[0].column_number))
                continue

            elif tokens[0].type == urcl.lex.TokenType.MACRO:
                if not isinstance(tokens[0].value, str):
                    return Traceback([Message(f"Malformed macro token has non-str value (?)", tokens[0].line_number, tokens[0].column_number)], [])
                if tokens[0].value.upper() != "DEFINE":
                    return Traceback([Message(f"Top-level macro token must have value of @DEFINE, found @{tokens[0].value.upper()}", tokens[0].line_number, tokens[0].column_number)], [])
                if len(tokens) <3: # ❤
                    return Traceback([Message(f"Macro definition is to short, use the syntax @DEFINE WORD DEFINITION", tokens[0].line_number, tokens[0].column_number)], [])
                if tokens[1].type != urcl.lex.TokenType.IDENTIFIER:
                    return Traceback([Message(f"Expected identifier, found {tokens[1].type.value}", tokens[1].line_number, tokens[1].column_number)], [])
                macros.update({str(tokens[1].value): tokens[2:]})
                continue

            else:
                result_tokens: list[urcl.lex.Token] = []
                for token in tokens:
                    if token.type == urcl.lex.TokenType.IDENTIFIER:
                        macro_value = macros.get(str(token.value))
                        if macro_value:
                            for macro_token in macro_value:
                                result_tokens.append(urcl.lex.Token(macro_token.type, token.line_number, token.column_number, macro_token.value))
                        else:
                            result_tokens.append(token)
                    else:
                        result_tokens.append(token)
            instruction = InstructionCSTNode.parse(urcl.lex.TokenStream(result_tokens))
            if not isinstance(instruction, InstructionCSTNode):
                instruction.elaborate("Invalid instruction", tokens[0].line_number, tokens[0].column_number)
                return instruction
            
            cst.lines.append(instruction)
        return cst
    
    def __str__(self) -> str:
        return "\n".join([str(line) for line in self.lines])