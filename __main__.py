import subprocess

import urcl
from compile import compile_urcl_to_executable

with open("./programs/print_squares.urcl", "r") as file:
    #p = urcl.parse(file.read())
    p = compile_urcl_to_executable(file.read())
    if not isinstance(p, bytes):
        print(p)
    else:
        with open("./run", "w+b") as file:
            file.write(p)
        subprocess.run("./run")