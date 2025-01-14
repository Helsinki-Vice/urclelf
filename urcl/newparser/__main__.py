import __init__
import sys

from lex import TokenStream
if __name__ == "__main__":
    toks = __init__.tokenize(sys.stdin.read())
    if isinstance(toks, TokenStream):
        print(__init__.create_program_cst(toks))