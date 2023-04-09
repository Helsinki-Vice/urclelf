import enum
from dataclasses import dataclass

class TokenType(enum.Enum):
    INTEGER = enum.auto()
    LABEL = enum.auto()
    GENERAL_REGISTER = enum.auto()
    CHARACTER = enum.auto()
    IDENTIFIER = enum.auto()
    NEWLINE = enum.auto()

@dataclass
class Token:
    type: TokenType
    line_number: int
    column_number: int
    value: "str | None"

    def __str__(self) -> str:
        
        result = f"<{self.type.name} {self.line_number}:{self.column_number}"
        if self.value is not None:
            result += f" - {self.value}>"
        else:
            result += ">"
        
        return result

class Lexer:

    def __init__(self, source: str) -> None:
        
        self.index = 0
        self.line_number = 1
        self.column_number = 1
        self.tokens: list[Token] = []
        self.source = source
        self.current_char = self.source[self.index]
        self.lex()
    
    def lex(self):

        while self.index < len(self.source):
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
                while self.index < len(self.source):
                    if not self.current_char.isspace():
                        token_value += self.current_char
                        self.advance()
                    else:
                        try:
                            token_value = int(token_value[1:])
                        except ValueError:
                            return None
                        break
            else:
                token_type = TokenType.IDENTIFIER
                while self.index < len(self.source):
                    if not self.current_char.isspace():
                        token_value += self.current_char
                        self.advance()
                    else:
                        try:
                            token_value = int(token_value, base=0)
                        except ValueError:
                            break
                        except TypeError:
                            break
                        token_type = TokenType.INTEGER
            self.tokens.append(Token(token_type, token_line_number, token_column_number, token_value))
    
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
                lines.append(TokenStream(current_line))
                current_line_number += token.line_number - current_line_number
                current_line = [token]
        if current_line:
            lines.append(TokenStream(current_line))
        
        return lines
    
    def __str__(self) -> str:
        
        lines: list[str] = []
        for line in self.split_lines():
            lines.append(" ".join([str(token) for token in line.tokens]))
        
        return "\n".join(lines)

def tokenize(source: str):

    return TokenStream(Lexer(source).tokens)


with open("./source.urcl", "r") as file:
    source = file.read()
toks = tokenize(source)
print(toks)