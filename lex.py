import enum
from dataclasses import dataclass

from error import Traceback, Message

class TokenType(enum.Enum):
    INTEGER = enum.auto()
    LABEL = enum.auto()
    GENERAL_REGISTER = enum.auto()
    CHARACTER = enum.auto()
    IDENTIFIER = enum.auto()
    NEWLINE = enum.auto()
    RELATIVE_JUMP = enum.auto()
    MACRO = enum.auto()
    PORT = enum.auto()

@dataclass
class Token:
    type: TokenType
    line_number: int
    column_number: int
    value: "str | int | None"

    def __str__(self) -> str:
        
        result = f"<{self.type.name} {self.line_number}:{self.column_number}"
        if self.value is not None:
            result += f" - {self.value}>"
        else:
            result += ">"
        
        return result

#TODO:  better software design
#FIXME: hex and negative literals don't work
class Lexer:

    def __init__(self, source: str) -> None:
        
        self.index = 0
        self.line_number = 1
        self.column_number = 1
        self.tokens: TokenStream = TokenStream([])
        self.source = source
        self.current_char = self.source[self.index]
        self.macros: dict[str, Token] = {}
    
    def lex(self) -> "TokenStream | Traceback":

        inside_multiline_comment = False
        inside_line_comment = False
        while self.index < len(self.source):
            if self.source[self.index:].startswith("//"):
                inside_line_comment = True
                self.advance()
                self.advance()
                continue
            if self.source[self.index:].startswith("/*"):
                inside_multiline_comment = True
                self.advance()
                self.advance()
                continue
            if self.current_char == "\n":
                inside_line_comment = False
            if self.source[self.index:].startswith("*/"):
                inside_multiline_comment = False
                self.advance()
                self.advance()
                continue
            if inside_line_comment or inside_multiline_comment:
                self.advance()
                continue
            if self.current_char.isspace():
                self.advance()
                continue
            
            token_index = self.index
            token_line_number = self.line_number
            token_column_number = self.column_number
            token_value: "str | int" = ""
            if self.current_char == ".":
                token_type = TokenType.LABEL
                while self.index < len(self.source):
                    if not self.current_char.isspace():
                        token_value += self.current_char
                        self.advance()
                    else:
                        break
            elif self.current_char in ["r", "R", "$"]:
                token_type = TokenType.GENERAL_REGISTER
                token_value = ""
                while self.index < len(self.source):
                    if not self.current_char.isspace():
                        token_value += self.current_char
                        self.advance()
                    else:
                        break
                try:
                    token_value = int(token_value[1:])
                except ValueError:
                    pass
            elif self.current_char == "~":
                token_type = TokenType.RELATIVE_JUMP
                while self.index < len(self.source):
                    if not self.current_char.isspace():
                        token_value += self.current_char
                        self.advance()
                    else:
                        break
                try:
                    token_value = int(token_value[1:])
                except ValueError:
                    return Traceback([Message(f"Malformed relative jump '{token_value}'", self.line_number, self.column_number)], [])
            
            elif self.current_char in "-0123456789":
                token_type = TokenType.INTEGER
                token_value = ""
                while self.index < len(self.source):
                    if self.current_char.lower() in "0123456789":
                        token_value += self.current_char
                        self.advance()
                    else:
                        break
                try:
                    token_value = int(token_value, base=0)
                except ValueError:
                    return Traceback([Message(f"Malformed int '{token_value}'", self.line_number, self.column_number)], [])
            
            elif self.current_char == "'" and self.source[self.index+2] == "'" and self.index - 3 <= len(self.source):
                token_type = TokenType.CHARACTER
                token_value = self.source[self.index+1]
                self.advance()
                self.advance()
                self.advance()
            
            elif self.current_char.lower() in "abcdefghijklmnopqrstuvwxyz":
                token_type = TokenType.IDENTIFIER
                token_value = ""
                while self.index < len(self.source):
                    if self.current_char.lower() in "abcdefghijklmnopqrstuvwxyz0123456789-_":
                        token_value += self.current_char
                        self.advance()
                    else:
                        break
            
            elif self.current_char == "@":
                token_type = TokenType.MACRO
                token_value = ""
                self.advance()
                while self.index < len(self.source):
                    if self.current_char.lower() in "abcdefghijklmnopqrstuvwxyz_":
                        token_value += self.current_char
                        self.advance()
                    else:
                        break
            
            elif self.current_char == "%":
                token_type = TokenType.PORT
                token_value = ""
                self.advance()
                while self.index < len(self.source):
                    if self.current_char.lower() in "abcdefghijklmnopqrstuvwxyz_":
                        token_value += self.current_char
                        self.advance()
                    else:
                        break
            
            else:
                return Traceback([Message(f"Unexpected '{self.current_char}'", self.line_number, self.column_number)], [])
            token = Token(token_type, token_line_number, token_column_number, token_value)
            self.tokens.append(token)
        index = 0
        for line in self.tokens.split_lines():
            if line[0].type == TokenType.MACRO:
                if len(line) != 3:
                    return Traceback([Message(f"Macro definition is malformed", line[0].line_number, line[0].column_number)], [])
                self.macros.update({line[1].value: line[2]})
                index += 3
            else:
                for token in line.tokens:
                    if token.value in self.macros.keys():
                        line_number = token.line_number
                        column_number = token.column_number
                        self.tokens[index] = Token(self.macros[str(token.value)].type, self.tokens[index].line_number, self.tokens[index].column_number, self.macros[str(token.value)].value)
                        self.tokens[index].line_number = line_number
                        self.tokens[index].column_number = column_number
                    index += 1
        return self.tokens
    
    def advance(self):
        self.column_number += 1
        if self.source[self.index] == "\n":
            self.line_number += 1
            self.column_number = 1
        self.index += 1
        if self.index < len(self.source):
            self.current_char = self.source[self.index]

@dataclass
class TokenStream:

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
    
    def __getitem__(self, index):
        return self.tokens.__getitem__(index)

    def __setitem__(self, index, value):
        return self.tokens.__setitem__(index, value)

    def __len__(self):
        return len(self.tokens)

    def __str__(self) -> str:
        
        lines: list[str] = []
        for line in self.split_lines():
            lines.append(" ".join([str(token) for token in line.tokens]))
        
        return "\n".join(lines)

def tokenize(source: str):

    return Lexer(source).lex()


def main():
    with open("./source.urcl", "r") as file:
        source = file.read()
    tokens = tokenize(source)
    print(tokens)
    
if __name__ == "__main__":
    main()