import enum
from dataclasses import dataclass

import lex

class Mnemonic(enum.Enum):
    ADD = "add"
    MOV = "mov"
    NOP = "nop"
    JMP = "jmp"
    HLT = "hlt"
    INC = "inc"
    JNZ = "jnz"
    OUT = "out"

    def __str__(self) -> str:
        return self.value

class OperandType(enum.Enum):
    INTEGER = enum.auto()
    LABEL = enum.auto()
    GENERAL_REGISTER = enum.auto()
    CHARACTER = enum.auto()

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

class Instruction:

    def __init__(self, mnemonic: Mnemonic, operands: "list[Label | GeneralRegister | int | RelativeAddress]") -> None:

        self.mnemonic = mnemonic
        self.operands = operands
    
    @classmethod
    def parse(cls, source: lex.TokenStream):

        words = source
        if not words:
            return None
        if not words.tokens[0].value:
            return None
        try:
            mnemonic = Mnemonic(words.tokens[0].value.lower())
        except ValueError:
            return None
        operands: "list[GeneralRegister | Label | int | RelativeAddress]" = []
        for op in words.tokens[1:]:
            if op.value is None:
                return None
            if op.type == lex.TokenType.LABEL:
                operands.append(Label(op.value))
            elif op.type == lex.TokenType.GENERAL_REGISTER:
                if not isinstance(op.value, int):
                    return None
                operands.append(GeneralRegister(op.value))
            elif op.type == lex.TokenType.INTEGER:
                if not isinstance(op.value, int):
                    return None
                operands.append(op.value)
            elif op.type == lex.TokenType.RELATIVE_JUMP:
                if not isinstance(op.value, int):
                    return None
                operands.append(RelativeAddress(op.value))
            else:
                pass
        
        return Instruction(mnemonic, operands)
    
    def get_jump_target(self):

        if self.mnemonic not in [Mnemonic.JMP, Mnemonic.JNZ]:
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
    def parse(cls, source: lex.TokenStream):

        program = Program()
        for line in source.split_lines():
            words = line.tokens
            if not words:
                continue
            if words[0].type == lex.TokenType.LABEL:
                if len(words) > 1:
                    return None
                if not words[0].value:
                    return None
                program.code.append(Label(words[0].value))
                continue
            instruction = Instruction.parse(line)
            if not instruction:
                return None
            program.code.append(instruction)
        print(program)
        return program
    
    @classmethod
    def parse_str(cls, source: str):

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