import subprocess
from compile import compile_urcl_to_executable

with open("./programs/memory.urcl", "r") as file:
    
    program = compile_urcl_to_executable(file.read())
    if not isinstance(program, bytes):
        print(program)
    else:
        with open("./run", "w+b") as file:
            file.write(program)
        return_code = subprocess.run("./run")
        print(f"(returned {return_code.returncode})")