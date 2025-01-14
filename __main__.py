import argparse
import sys
import os
import pathlib
from dataclasses import dataclass

OLD_CWD = pathlib.Path(os.getcwd()).resolve(True)
CURRENT_DIR = pathlib.Path(__file__).parent.resolve(True)
BIN_DIR = CURRENT_DIR.joinpath("bin").resolve().relative_to(CURRENT_DIR).resolve(True)
os.chdir(CURRENT_DIR)

import urcl
from x86codegen import compile_urcl_to_executable, compile_urcl_to_intel_assembly
from x86 import ASMCode
import target
from error import Traceback

@dataclass
class CommandLineArguments:
    source_file: str
    output_file: str
    executable_format: target.ExecutableFormat
    machine_type: target.Isa
    is_main: bool

def command_line_compile(source_path: str, options: CommandLineArguments):

    with open(OLD_CWD.joinpath(pathlib.Path(source_path).resolve(True)), "r") as file:
        compile_options = target.CompileOptions(
            target=target.Target(options.machine_type, target.ByteOrder.LITTLE, target.OsAbi.SYSV),
            executable_type=target.ExecutableType.OBJECT,
            executable_format=options.executable_format,
            is_main=options.is_main
        )
        if compile_options.executable_format == target.ExecutableFormat.ASSEMBLY:
            program = str(compile_urcl_to_intel_assembly(file.read(), compile_options))
        elif compile_options.executable_format == target.ExecutableFormat.URCL:
            program = str(urcl.parse(file.read()))
        else:
            program = compile_urcl_to_executable(file.read(), compile_options)
        if isinstance(program, (str, bytes)):
            output = program
        else:
            print(program)
            exit()
        with open(options.output_file, "w+" if isinstance(output, str) else "w+b") as file:
            file.write(output)

def main():

    argument_parser = argparse.ArgumentParser(description="Compiles URCL code to x86 executables.")
    argument_parser.add_argument("source_file")
    argument_parser.add_argument("-o", dest="output_file")
    argument_parser.add_argument("-f", dest="executable_format", default="elf", help="output file format")
    argument_parser.add_argument("-lib", dest="lib", action="store_true", help="pass this if this file is not the entry point.")
    argument_parser.add_argument("-m", dest="machine", default="i386", help="instruction set of the target machine")
    k = argument_parser.parse_args(sys.argv[1:])
    if k.output_file is None:
        filename = k.source_file.split("/")[-1].split(".")[0] + ".o"
        output_path = BIN_DIR.joinpath(filename).resolve(True)
        k.output_file = str(output_path)
    
    if k.executable_format.lower() == "bin":
        executable_format = target.ExecutableFormat.FLAT
    elif k.executable_format.lower() in ["elf", None]:
        executable_format = target.ExecutableFormat.ELF
    elif k.executable_format.lower() == "asm":
        executable_format = target.ExecutableFormat.ASSEMBLY
    elif k.executable_format.lower() == "urcl":
        executable_format = target.ExecutableFormat.URCL
    else:
        print(f"Executable file format '{k.executable_format.lower()}' not known.")
        exit()
    if k.machine.lower() in ["i386", "x86", "i686", "x86_32"]:
        machine = target.Isa.X86
    elif k.machine.lower() in ["x64", "amd64", "x86_64"]:
        machine = target.Isa.X64
    else:
        print(f"Machine type '{k.exec_file_type.lower()}' not known.")
        exit()
    k = CommandLineArguments(
        source_file=k.source_file,
        output_file=k.output_file,
        executable_format=executable_format,
        is_main=not k.lib,
        machine_type=machine
    )
    command_line_compile(k.source_file, k)

main()