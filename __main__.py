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
import target
import compile
from error import Traceback

@dataclass
class CommandLineArguments:
    source_file: str
    output_file: str
    executable_format: target.ExecutableFormat
    machine_type: target.Isa
    is_main: bool
    use_stdin: bool
    use_stdout: bool

def command_line_compile(options: CommandLineArguments):

    if options.use_stdin:
        try:
            source_code = sys.stdin.buffer.read().decode("utf-8")
        except KeyboardInterrupt as error:
            exit(1)

    else:
         with open(options.source_file, "r") as file:
             source_code = file.read()
    
    compile_options = target.CompileOptions(
        target=target.Target(options.machine_type, target.ByteOrder.LITTLE, target.OsAbi.SYSV),
        executable_type=target.ExecutableType.OBJECT,
        executable_format=options.executable_format,
        is_main=options.is_main
    )
    
    program = compile_urcl_to_executable(source_code, compile_options)

    if isinstance(program, bytes):
        bytes_for_file = program
    else:
        print(program, file=sys.stderr)
        exit()
    
    if options.use_stdout:
        sys.stdout.buffer.write(bytes_for_file)
    else:
        with open(options.output_file, "w+b") as out_file:
            out_file.write(bytes_for_file)

def main():

    argument_parser = argparse.ArgumentParser(description="Compiles URCL code to x86 executables.")
    argument_parser.add_argument("source_file")
    argument_parser.add_argument("-o", dest="output_file")
    argument_parser.add_argument("-f", dest="executable_format", default="elf", help="output file format")
    argument_parser.add_argument("-lib", dest="lib", action="store_true", help="pass this if this file is not the entry point.")
    argument_parser.add_argument("-m", dest="machine", default="i386", help="instruction set of the target machine")
    k = argument_parser.parse_args(sys.argv[1:])
    
    if k.source_file == "-":
        in_filename = "/dev/stdin"
        use_stdin = True
    else:
        in_filename = k.source_file
        use_stdin = False

    if k.output_file == "-":
        out_filename = "/dev/stdin"
        use_stdout = True
    else:
        out_filename = k.output_file
        use_stdout = False

    if out_filename is None:
        out_filename = in_filename.split("/")[-1].split(".")[0] + ".o"
        output_path = OLD_CWD.joinpath(out_filename).resolve()
        k.output_file = str(output_path)
    
    if k.executable_format.lower() == "bin":
        executable_format = target.ExecutableFormat.FLAT
    elif k.executable_format.lower() in ["elf", None]:
        executable_format = target.ExecutableFormat.ELF
    elif k.executable_format.lower() == "asm":
        executable_format = target.ExecutableFormat.ASM
    else:
        print(f"Executable file format '{k.executable_format.lower()}' not known.", file=sys.stdout)
        exit()
    if k.machine.lower() == "i386":
        machine = target.Isa.X86
    elif k.machine.lower() == "x64":
        machine = target.Isa.X64
    else:
        print(f"Machine type '{k.exec_file_type.lower()}' not known.", file=sys.stderr)
        exit()
    
    arguments = CommandLineArguments(
        source_file=str(OLD_CWD.joinpath(in_filename).resolve()),
        output_file=str(OLD_CWD.joinpath(k.output_file).resolve()),
        executable_format=executable_format,
        is_main=not k.lib,
        machine_type=machine,
        use_stdin=use_stdin,
        use_stdout=use_stdout
    )
    command_line_compile(arguments)

main()