from dataclasses import dataclass
import traceback
from typing import Self
import enum
from error import Traceback
from lex import Token, TokenStream
import json

class CSTNodeType(enum.Enum):
    PROGRAM = "PROGRAM"
    LINE = "LINE"
    INSTRUCTION = "INSTRUCTION"
    MACRO_DEFINITION = "MACRO_DEFINITION"
    HEADER = "INSTRUCTION"
    LABEL_DEFINITION = "LABEL_DEFINITION"
    MNEMONIC = "MNEMONIC"
    OPERAND = "OPERAND"
    DEFINE_KEYWORD = "DEFINE_KEYWORD"
    DEFINED_IDENTIFIER = "DEFINED_IDENTIFIER"
    DEFINITION = "DEFINITION"
    HEADER_KEYWORD = "HEADER_KEYWORD"
    INEQUALITY = "INEQUALITY"
    HEADER_VALUE = "HEADER_VALUE"

@dataclass
class CSTNode:
    node_type: CSTNodeType
    leaves: list[Self] | Token

    def __str__(self) -> str:

        if isinstance(self.leaves, list):
            value_str = f"[{','.join([str(leaf) for leaf in self.leaves])}]"
        else:
            value_str = f'"{self.leaves}"'
        
        return json.dumps(json.loads("{"+f"\"{self.node_type.value}\": {value_str}"+"}"), indent=4)

def create_line_cst(tokens: TokenStream) -> CSTNode | Traceback:

    if not len(tokens):
        return Traceback.new("PARSER BUG: empty lines should be filtered by now")
    
    return CSTNode(CSTNodeType.LINE, tokens.tokens[0])

def create_program_cst(tokens: TokenStream) -> CSTNode | Traceback:

    line_nodes: list[CSTNode] = []
    for line in tokens.split_lines():
        if not line:
            continue
        line_result = create_line_cst(line)
        if isinstance(line_result, Traceback):
            err = line_result
            err.elaborate(f"Syntax error on line {line.tokens[0].line_number}")
            return err
        line_nodes.append(line_result)
    
    return CSTNode(CSTNodeType.PROGRAM, line_nodes)