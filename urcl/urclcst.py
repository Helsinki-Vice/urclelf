"This module takes a stream of URCL tokens and parses it into a concrete syntax tree"
import enum
from dataclasses import dataclass
from typing import Union, Type, Self

from urcl.types import Mnemonic, Label, RelativeAddress, Character, Port, GeneralRegister, DefinedImmediate
import urcl.lex
from error import Traceback, Message

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
    value: Union[Label, GeneralRegister, int, RelativeAddress, Character, Port, DefinedImmediate, list[Self]]
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
    
    @classmethod
    def success(cls, value: OperandCSTNode, tokens_consumed: int):
        return OperandParseResult(value, tokens_consumed)

def parse_operand(tokens: urcl.lex.TokenStream) -> OperandParseResult:

        for token in tokens:

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
        
        return OperandParseResult(None, 0)

def get_operand_type(value: OperandCSTNode):

    mapping = {
        Label: OperandType.LABEL,
        GeneralRegister: OperandType.GENERAL_REGISTER,
        int: OperandType.INTEGER,
        RelativeAddress: OperandType.RELATIVE_ADDERESS,
        GeneralRegister: OperandType.CHARACTER,
        GeneralRegister: OperandType.PORT,
        list: OperandType.ARRAY
    }
    
    t: Type = type(value)
    return mapping.get(t)

class InstructionCSTNode:

    def __init__(self, mnemonic: Mnemonic, operands: list[OperandCSTNode], line_number=0, column_number=0) -> None:

        self.mnemonic = mnemonic
        self.operands = operands
        self.line_number = line_number
        self.column_number = column_number
    
    @classmethod
    def parse(cls, words: urcl.lex.TokenStream) -> "InstructionCSTNode | Traceback":

        if not words:
            return Traceback([Message("Instruction must not be empty.", 0, 0)], [])
        if not words.tokens[0].value:
            return Traceback([Message("Instruction must have a mnemoric", words.tokens[0].line_number, words.tokens[0].column_number)], [])
        try:
            mnemonic = Mnemonic(str(words.tokens[0].value).lower())
        except ValueError:
            return Traceback([Message(f"Unknown mnemonic '{words.tokens[0].value}'", words.tokens[0].line_number, words.tokens[0].column_number)], [])
        
        operands: list[OperandCSTNode] = []
        for token in words.tokens[1:]:

            if token.type == urcl.lex.TokenType.COMMA:
                continue #allow commas TODO: add warning in parser output

            if token.value is None:
                return Traceback([Message("Operand must not be empty.", token.line_number, token.column_number)], [])
            
            if token.type == urcl.lex.TokenType.LABEL:
                operands.append(OperandCSTNode(Label(str(token.value)), token.line_number, token.column_number))
            
            elif token.type == urcl.lex.TokenType.GENERAL_REGISTER:
                if not isinstance(token.value, GeneralRegister):
                    return Traceback([Message(f"Invalid register token '{token.value}' has value of type {type(token.value).__name__}", token.line_number, token.column_number)], [])
                operands.append(OperandCSTNode(token.value, token.line_number, token.column_number))
            
            elif token.type == urcl.lex.TokenType.INTEGER:
                if not isinstance(token.value, int):
                    return Traceback([Message(f"Invalid integer: '{token.value}'", token.line_number, token.column_number)], [])
                operands.append(OperandCSTNode(token.value, token.line_number, token.column_number))
            
            elif token.type == urcl.lex.TokenType.RELATIVE_JUMP:
                if not isinstance(token.value, int):
                    return Traceback([Message(f"Invalid relative jump: '{token.value}'", token.line_number, token.column_number)], [])
                operands.append(OperandCSTNode(RelativeAddress(token.value), token.line_number, token.column_number))
            
            elif token.type == urcl.lex.TokenType.CHARACTER:
                if not isinstance(token.value, str) or not token.value:
                    return Traceback([Message(f"Invalid character: '{token.value}'", token.line_number, token.column_number)], [])
                operands.append(OperandCSTNode(Character(token.value), token.line_number, token.column_number))
            
            elif token.type == urcl.lex.TokenType.PORT:
                if not isinstance(token.value, str) or not token.value:
                    return Traceback([Message(f"Invalid Port: '{token.value}'", token.line_number, token.column_number)], [])
                port = Port.from_value(token.value)
                if port:
                    operands.append(OperandCSTNode(port, token.line_number, token.column_number))
                else:
                    return Traceback([Message(f"Unknown Port: '{token.value}'", token.line_number, token.column_number)], [])
            
            elif token.type == urcl.lex.TokenType.MACRO:
                if isinstance(token.value, str):
                    try:
                        defined_immediate = DefinedImmediate(token.value.upper())
                    except ValueError:
                        defined_immediate = None
                else:
                    defined_immediate = None
                if not defined_immediate:
                    return Traceback([Message(f"Invalid defined immediate: '{token.value}'", token.line_number, token.column_number)], [])
                operands.append(OperandCSTNode(defined_immediate, token.line_number, token.column_number))
                continue
                if defined_immediate == DefinedImmediate.BITS:
                    operands.append(OperandCSTNode(32, token.line_number, token.column_number))
                elif defined_immediate == DefinedImmediate.MINREG:
                    operands.append(OperandCSTNode(4, token.line_number, token.column_number))
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
        
        return InstructionCSTNode(mnemonic, operands, words[0].line_number, words[0].column_number)
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
    @classmethod
    def parse_str(cls, source: str):
        
        tokens = urcl.lex.tokenize(source)
        if not isinstance(tokens, urcl.lex.TokenStream):
            error = tokens
            error.elaborate("Invalid tokens")
            return error
        
        return InstructionCSTNode.parse(tokens)
    
    def __str__(self) -> str:
        
        operands = " ".join([str(operand) for operand in self.operands])
        return f"{self.mnemonic.value} {operands}"

class CST:

    def __init__(self) -> None:
        
        self.top_level_declerations: "list[InstructionCSTNode | Label]" = []
    
    @classmethod
    def from_tokens(cls, source: urcl.lex.TokenStream) -> "CST | Traceback":

        cst = CST()
        macros: dict[str, list[urcl.lex.Token]] = {}
        for line in source.split_lines():
            words = line.tokens

            if not words:
                continue
            
            if words[0].type == urcl.lex.TokenType.LABEL:
                if not words[0].value:
                    return Traceback([Message(f"Label must not be empty", words[0].line_number, words[0].column_number)], [])
                if len(words) > 1:
                    return Traceback([Message(f"Unexpected {words[1].type.value} after label .{words[0].value}", words[1].line_number, words[1].column_number)], [])
                cst.top_level_declerations.append(Label(str(words[0].value)))
                continue

            if words[0].type == urcl.lex.TokenType.MACRO:
                if not isinstance(words[0].value, str):
                    return Traceback([Message(f"Malformed macro token has non-str value (?)", words[0].line_number, words[0].column_number)], [])
                if words[0].value.upper() != "DEFINE":
                    return Traceback([Message(f"Top-level macro token must have value of @DEFINE, found @{words[0].value.upper()}", words[0].line_number, words[0].column_number)], [])
                if len(words) <3: # ❤
                    return Traceback([Message(f"Macro definition is to short, use the syntax @DEFINE WORD DEFINITION", words[0].line_number, words[0].column_number)], [])
                if words[1].type != urcl.lex.TokenType.IDENTIFIER:
                    return Traceback([Message(f"Expected identifier, found {words[1].type.value}", words[1].line_number, words[1].column_number)], [])
                macros.update({str(words[1].value): words[2:]})
                continue
            pee_pee: list[urcl.lex.Token] = []
            for blah in words:
                if blah.type == urcl.lex.TokenType.IDENTIFIER:
                    poo = macros.get(str(blah.value))
                    if poo:
                        for turd in poo:
                            pee_pee.append(urcl.lex.Token(turd.type, blah.line_number, blah.column_number, turd.value))
                    else:
                        pee_pee.append(blah)
                else:
                    pee_pee.append(blah)
            instruction = InstructionCSTNode.parse(urcl.lex.TokenStream(pee_pee))
            if not isinstance(instruction, InstructionCSTNode):
                instruction.elaborate("Invalid instruction")
                return instruction
            
            cst.top_level_declerations.append(instruction)
        return cst
    
    @classmethod
    def parse_str(cls, source: str) -> "CST | Traceback":

        tokens = urcl.lex.tokenize(source)
        if not isinstance(tokens, urcl.lex.TokenStream):
            error = tokens
            error.elaborate("Invalid tokens")
            return error
        
        return CST.from_tokens(tokens)
    
    def __str__(self) -> str:
        return "\n".join([str(line) for line in self.top_level_declerations])