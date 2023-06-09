"This module provides types for representing, validating, and parsing URCL code"

import error
import urcl.types as types
import urcl.lex as lex
import urcl.urclcst as urclcst
import urcl.urclast as urclast

from urcl.types import Mnemonic
from urcl.lex import tokenize, TokenStream
from urcl.urclcst import CST, InstructionCSTNode, OperandCSTNode
from urcl.urclast import AST, TWO_OPERAND_ARITHMETIC_MNEMONICS, TWO_OPERAND_CONDITION_JUMP_MNEMONICS, THREE_OPERAND_CONDITION_JUMP_MNEMONICS


SYNTAX_ERROR_MESSAGE = "Syntax error"

def parse(source: str):

    tokens = tokenize(source)
    if isinstance(tokens, error.Traceback):
        err = tokens
        err.elaborate(SYNTAX_ERROR_MESSAGE)
        return err
    
    cst = urclcst.CST.from_tokens(tokens)
    if isinstance(cst, error.Traceback):
        err = cst
        err.elaborate(SYNTAX_ERROR_MESSAGE)
        return err
    
    ast = AST.from_cst(cst)
    if isinstance(ast, error.Traceback):
        err = ast
        err.elaborate(SYNTAX_ERROR_MESSAGE)
        return err
    
    return ast