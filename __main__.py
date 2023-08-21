import subprocess
from compile import compile_urcl_to_executable
import x86.codegen
#enc = x86.InstructionEncoding(mnemonic=x86.Mnemonic.INT, opcode=x86.Opcode(expansion_prefix=False, value=205), opcode_extention=None, operands=[x86.ImmediateType(size=1, is_relative=False)])
#ins = x86.ASMInstruction(x86.Mnemonic.INT, [x86.Operand(125)])
#print(x86.encode_instruction_using_encoding())
with open("./programs/print_squares.urcl", "r") as file:
    #p = urcl.parse(file.read())
    p = compile_urcl_to_executable(file.read())
    if not isinstance(p, bytes):
        print(p)
    else:
        with open("./run", "w+b") as file:
            file.write(p)
        return_code = subprocess.run("./run")
        print(f"(returned {return_code.returncode})")