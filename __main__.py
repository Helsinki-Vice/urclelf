import argparse
import sys
import os
import pathlib
from dataclasses import dataclass

OLD_CWD = pathlib.Path(os.getcwd()).resolve()
CURRENT_DIR = pathlib.Path(__file__).parent.resolve()
LIB_DIR = CURRENT_DIR.joinpath("lib").resolve().relative_to(CURRENT_DIR).resolve()
BIN_DIR = CURRENT_DIR.joinpath("bin").resolve().relative_to(CURRENT_DIR).resolve()
os.chdir(CURRENT_DIR)

from compile import compile_urcl_to_executable
from elf import Elf32
import target
import x86
from error import Traceback

@dataclass
class CommandLineArguments:
    source_file: str
    output_file: str
    executable_format: target.ExecutableFormat
    is_main: bool

def command_line_compile(source_path: str, options: CommandLineArguments):

    with open(source_path, "r") as file:
        program = compile_urcl_to_executable(
            file.read(),
            target.CompileOptions(
                target=target.Target(target.Isa.X86, target.ByteOrder.LITTLE, target.OsAbi.SYSV),
                executable_type=target.ExecutableType.OBJECT,
                executable_format=options.executable_format,
                is_main=options.is_main
            )
        )
        if isinstance(program, bytes):
            bytes_for_file = program
        else:
            print(program)
            exit()
        with open(options.output_file, "w+b") as file:
            file.write(bytes_for_file)

def main():

    argument_parser = argparse.ArgumentParser(description="Compiles URCL code to x86 executables.")
    argument_parser.add_argument("source_file")
    argument_parser.add_argument("-o", dest="output_file")
    argument_parser.add_argument("-f", dest="executable_format", default="elf")
    argument_parser.add_argument("-lib", dest="lib", action="store_true", help="pass this if this file is not the entry point.")
    k = argument_parser.parse_args(sys.argv[1:])
    if k.output_file is None:
        filename = k.source_file.split("/")[-1].split(".")[0] + ".o"
        output_path = BIN_DIR.joinpath(filename).resolve().relative_to(BIN_DIR).resolve()
        k.output_file = str(output_path)
    
    if k.executable_format.lower() == "bin":
        executable_format = target.ExecutableFormat.FLAT
    elif k.executable_format.lower() in ["elf", None]:
        executable_format = target.ExecutableFormat.ELF
    elif k.executable_format.lower() == "win32":
        executable_format = target.ExecutableFormat.COFF
    else:
        print(f"Executable file format '{k.exec_file_type.lower()}' not known.")
        exit()
    k = CommandLineArguments(
        source_file=k.source_file,
        output_file=k.output_file,
        executable_format=executable_format,
        is_main=not k.lib
    )
    command_line_compile(k.source_file, k)

main()