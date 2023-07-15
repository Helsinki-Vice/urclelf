"This module takes URCL source code and performs lexical analysis"
import enum
from dataclasses import dataclass
from typing import Union, Callable
import string
import urcl.types

import error

LEGAL_LABEL_CHARACTERS = string.ascii_letters + string.digits + "._"
LEGAL_IDENTIFIER_FIRST_CHARACTERS = string.ascii_letters + "_"
LEGAL_IDENTIFIER_CONTINUATION_CHARACTERS = LEGAL_IDENTIFIER_FIRST_CHARACTERS + string.digits

class TokenType(enum.Enum):
    INTEGER = "integer"
    LABEL = "label"
    GENERAL_REGISTER = "general register"
    CHARACTER = "character"
    IDENTIFIER = "identifier"
    WHITESPACE = "whitespace"
    RELATIVE_JUMP = "relative jump"
    MACRO = "macro"
    PORT = "port"
    HEADER_INEQUALITY = "header inequality"
    LEFT_BRACKET = "["
    RIGHT_BRACKET = "]"
    COMMA = ","
    STRING = "string"


# It's a type that holds a token's value
TokenValue = Union[str, int, urcl.types.GeneralRegister, None]

@dataclass
class Token:
    type: TokenType
    line_number: int
    column_number: int
    value: TokenValue

    def __str__(self) -> str:
        
        result = f"<{self.type.name} {self.line_number}:{self.column_number}"
        if self.value is not None:
            result += f" - {self.value}>"
        else:
            result += ">"
        
        return result

@dataclass
class TokenStream: #TODO: add __getitem__ and __setitem__

    tokens: list[Token]

    def split_lines(self):

        current_line_number = 1
        lines: list[TokenStream] = []
        current_line: list[Token] = []
        for token in self.tokens:
            if token.line_number == current_line_number:
                current_line.append(token)
            else:
                if current_line:
                    lines.append(TokenStream(current_line))
                current_line_number = token.line_number
                current_line = [token]
        if current_line:
            lines.append(TokenStream(current_line))
        
        return lines
    
    def append(self, token: Token):
        self.tokens.append(token)
    
    def __iter__(self):
        return self.tokens.__iter__()
    
    def __len__(self):
        return len(self.tokens)

    def __str__(self) -> str:
        
        lines: list[str] = []
        for line in self.split_lines():
            lines.append(" ".join([str(token) for token in line.tokens]))
        
        return "\n".join(lines)

@dataclass
class TokenParseResult:
    data: Token | str | None
    chars_consumed: int

    @classmethod
    def miss(cls):
        return TokenParseResult(None, 0)
    
    @classmethod
    def success(cls, type: TokenType, value: TokenValue, chars_consumed: int):
        return TokenParseResult(Token(type, 1, 1, value), chars_consumed)


# Regex? what's that?
def extract_label_token(source: str) -> TokenParseResult:

    if not source.startswith("."): return TokenParseResult.miss()
    index = 1
    while index < len(source):
        if source[index] not in LEGAL_LABEL_CHARACTERS:
            break
        index += 1
    
    return TokenParseResult.success(TokenType.LABEL, source[1:index], index)


def extract_space_token(source: str) -> TokenParseResult:

    if not source: return TokenParseResult.miss()
    index = 0
    while index < len(source):
        if not source[index].isspace():
            break
        index += 1
    if index:
        return TokenParseResult.success(TokenType.WHITESPACE, None, index)

    return TokenParseResult.miss()


def extract_multiline_comment_token(source: str) -> TokenParseResult:

    if not source.startswith("/*"): return TokenParseResult.miss()
    index = 2
    while index < len(source):
        if source[:index].endswith("*/"):
            break
        index += 1
    
    return TokenParseResult.success(TokenType.WHITESPACE, None, index)


def extract_line_comment_token(source: str) -> TokenParseResult:

    if not source.startswith("//"): return TokenParseResult.miss()
    index = 2
    while index < len(source):
        if source[index] == "\n":
            index += 1
            break
        index += 1
    
    return TokenParseResult.success(TokenType.WHITESPACE, None, index)
    
    
def extract_relative_jump_token(source: str) -> TokenParseResult:

    if not source.startswith("~"): return TokenParseResult.miss()
    index = 1
    while index < len(source):
        if source[index].isspace():
            break
        index += 1
    
    try:
        token_value = int(source[1:index], base=0)
    except ValueError:
        return TokenParseResult(f"Malformed relative jump '{source[1:index]}'", 0)
            
    return TokenParseResult.success(TokenType.RELATIVE_JUMP, token_value, index)

def extract_register_token(source: str) -> TokenParseResult:

    if source[0].lower() not in ["r", "$"]: return TokenParseResult.miss()
    index = 1
    while index < len(source):
        if source[index] not in "0123456789":
            break
        index += 1
    
    if index == 1:
        return TokenParseResult.miss()
    try:
        token_value = urcl.types.GeneralRegister(int(source[1:index], base=0))
    except ValueError:
        return TokenParseResult(f"Malformed register '{source[1:index]}'", 0)
            
    return TokenParseResult.success(TokenType.GENERAL_REGISTER, token_value, index)

def extract_memory_address_token(source: str) -> TokenParseResult:

    if source[0].lower() not in ["m", "#"]: return TokenParseResult.miss()
    index = 1
    while index < len(source):
        if source[index] not in "0123456789":
            break
        index += 1
    
    if index == 1:
        return TokenParseResult.miss()
    try:
        token_value = urcl.types.GeneralRegister(int(source[1:index], base=0))
    except ValueError:
        return TokenParseResult(f"Malformed memory address '{source[1:index]}'", 0)
            
    return TokenParseResult.success(TokenType.GENERAL_REGISTER, token_value, index)

def extract_integer_token(source: str) -> TokenParseResult:

    if not source: return TokenParseResult.miss()
    index = 0
    if source[index] == "-":
        index += 1
    if source[index:index+2].lower() in ["0x", "0b", "0o"]:
        index += 2
    while index < len(source):
        if source[index] not in "0123456789":
            break
        index += 1
    
    if not index:
        return TokenParseResult.miss()
    try:
        token_value = int(source[:index], base=0)
    except ValueError:
        return TokenParseResult(f"Malformed integer '{source[:index]}'", 0)
            
    return TokenParseResult.success(TokenType.INTEGER, token_value, index)

def extract_string_token(source: str) -> TokenParseResult:

    if not source.startswith('"'): return TokenParseResult.miss()
    index = 1
    while index < len(source):
        if source[index] == '"':
            index += 1
            break
        if index == len(source) - 1:
            return TokenParseResult("String was never closed", 0)
        index += 1
    
    string_value = source[1:index-1]
    string_value = string_value.replace(r"\n", "\n").replace(r"\t", "\t").replace(r"\r", "\r")
    return TokenParseResult.success(TokenType.STRING, string_value, index)

def extract_character_token(source: str) -> TokenParseResult:

    if not source.startswith("'"): return TokenParseResult.miss()
    index = 1
    while index < len(source):
        if source[index] == "'":
            index += 1
            break
        if index == len(source) - 1:
            return TokenParseResult("Character literal was never closed", 0)
        index += 1
    
    string_value = source[1:index-1]
    string_value = string_value.replace(r"\n", "\n").replace(r"\t", "\t").replace(r"\r", "\r")
    if len(string_value) != 1:
        return TokenParseResult(f"Character literal is of length {len(string_value)} (expected 1)", 0)
    return TokenParseResult.success(TokenType.CHARACTER, string_value, index)

def extract_identifier_token(source: str) -> TokenParseResult:

    if source[0] not in LEGAL_IDENTIFIER_FIRST_CHARACTERS: return TokenParseResult.miss()
    index = 1
    while index < len(source):
        if source[index] not in LEGAL_IDENTIFIER_CONTINUATION_CHARACTERS:
            break
        index += 1
    
    return TokenParseResult.success(TokenType.IDENTIFIER, source[:index], index)

def extract_macro_token(source: str) -> TokenParseResult:

    if not source.startswith("@"): return TokenParseResult.miss()
    index = 1
    while index < len(source):
        if source[index] not in LEGAL_LABEL_CHARACTERS:
            break
        index += 1
    
    return TokenParseResult.success(TokenType.MACRO, source[1:index], index)

def extract_port_token(source: str) -> TokenParseResult:

    if not source.startswith("%"): return TokenParseResult.miss()
    index = 1
    while index < len(source):
        if source[index] not in LEGAL_LABEL_CHARACTERS:
            break
        index += 1
    
    return TokenParseResult.success(TokenType.PORT, source[1:index], index)

def extract_header_inequality_token(source: str) -> TokenParseResult:

    for inequality in ["==", "<=", ">="]:
        if source.startswith(inequality):
            return TokenParseResult.success(TokenType.HEADER_INEQUALITY, source[:2], 2)
    
    return TokenParseResult.miss()

def extract_left_bracket_token(source: str) -> TokenParseResult:

    if source.startswith("["):
        return TokenParseResult.success(TokenType.LEFT_BRACKET, None, 1)
    
    return TokenParseResult.miss()

def extract_right_bracket_token(source: str) -> TokenParseResult:

    if source.startswith("]"):
        return TokenParseResult.success(TokenType.RIGHT_BRACKET, None, 1)
    
    return TokenParseResult.miss()
    
def extract_comma_token(source: str) -> TokenParseResult:

    if source.startswith(","):
        return TokenParseResult.success(TokenType.COMMA, None, 1)
    
    return TokenParseResult.miss()

TOKEN_EXTRACTION_FUNCTIONS: list[Callable[[str], TokenParseResult]] = [
    extract_label_token, 
    extract_space_token, 
    extract_multiline_comment_token,
    extract_line_comment_token,
    extract_relative_jump_token,
    extract_integer_token,
    extract_character_token,
    extract_string_token,
    extract_register_token,
    extract_memory_address_token,
    extract_identifier_token,
    extract_macro_token,
    extract_header_inequality_token,
    extract_left_bracket_token,
    extract_right_bracket_token,
    extract_comma_token,
    extract_port_token

]

#TODO:  better software design
class Lexer:

    def __init__(self, source: str) -> None:
        
        self.index = 0
        self.line_number = 1
        self.column_number = 1
        self.source = source
        
    def remaining_source(self):
        return self.source[self.index:]
    
    def lex(self) -> TokenStream | error.Traceback:

        tokens = TokenStream([])
        while self.index < len(self.source):
            for token_extraction_function in TOKEN_EXTRACTION_FUNCTIONS:
                result = token_extraction_function(self.remaining_source())
                if not result.data:
                    continue
                if isinstance(result.data, str):
                    return error.Traceback([error.Message(result.data, self.line_number, self.column_number)], [])
                if result.data.type != TokenType.WHITESPACE:
                    tokens.append(Token(result.data.type, self.line_number, self.column_number, result.data.value))
                self.advance(result.chars_consumed)
                break
            else:
                return error.Traceback([error.Message(f"Unexpected characters: '{self.remaining_source()[:5]}...'", self.line_number, self.column_number)], [])
        
        return tokens

    def advance(self, amount:int=1):

        if amount < 1:
            return
        for _ in range(amount):
            if self.index == len(self.source):
                return
            self.column_number += 1
            if self.source[self.index] == "\n":
                self.line_number += 1
                self.column_number = 1
            self.index += 1
        
def tokenize(source: str):
    return Lexer(source).lex()