import urcl
import compile

with open("./source.urcl", "r") as file:
    #p = urcl.parse(file.read())
    p = compile.compile_urcl_to_executable(file.read())
    if not isinstance(p, bytes):
        print(p)
    else:
        with open("./run", "w+b") as file:
            file.write(p)
