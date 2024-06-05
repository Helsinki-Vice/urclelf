"""This module provides types for representing, validating, and parsing URCL code.
URCL is a toy assembly-like langauge originally designed to target computers in Minecraft.
Informal documentation can be found at https://github.com/ModPunchtree/URCL"""

import error
import urcl.types as types
import urcl.lex as lex
import urcl.urclcst as urclcst
import urcl.urclast as urclast

from urcl.types import Mnemonic, GeneralRegister, BasePointer, StackPointer, Port, Label, Character
from urcl.lex import tokenize, TokenStream
from urcl.urclcst import CST, InstructionCSTNode, OperandCSTNode, OperandType, DefinedImmediate
from urcl.urclast import TWO_OPERAND_ARITHMETIC_MNEMONICS, TWO_OPERAND_CONDITION_JUMP_MNEMONICS, THREE_OPERAND_CONDITION_JUMP_MNEMONICS, ZERO_OPERAND_MNEMONICS, THREE_OPERAND_ARITHMETIC_MNEMONICS

def parse(source: str):

    tokens = tokenize(source)
    if isinstance(tokens, error.Traceback):
        err = tokens
        err.elaborate("Code contains an invalid token")
        return err
    
    cst = urclcst.CST.from_tokens(tokens)
    if isinstance(cst, error.Traceback):
        err = cst
        err.elaborate("Syntax error while forming syntax tree")
        return err
     
    return cst