import subprocess
import argparse
import sys
import os
import pathlib

old_cwd = os.getcwd()
stay = pathlib.Path(__file__).parent.resolve()
os.chdir(stay)

from compile import compile_urcl_to_executable
import linux

def command_line_compile(source_path: str, output_path: str, small_file: bool, run: bool, stack_size: int, load_address: int):

    with open(source_path, "r") as file:
        program = compile_urcl_to_executable(file.read(), small_filesize=small_file, stack_size=stack_size, load_address=load_address)
        if not isinstance(program, bytes):
            print(program)
            exit()
        else:
            os.system(f"chmod 777 {output_path}")
            with open(output_path, "w+b") as file:
                file.write(program)
    if run:
        os.system(f"chmod 777 {output_path}")
        return_code = subprocess.run(output_path)
        print(f"(returned {return_code.returncode})")

def main():
    argument_parser = argparse.ArgumentParser(description="Compiles URCL code to x86 executables.")
    argument_parser.add_argument("source_file", nargs="?")
    argument_parser.add_argument("-o", dest="output_file")
    argument_parser.add_argument("-Os", "--no_sections", dest="no_sections", action="store_true", help="reduce filesize by not including section header table")
    argument_parser.add_argument("-r", "--autorun", dest="autorun", action="store_true", help="run the file automaticly after compiling")
    argument_parser.add_argument("-stack", nargs="?", type=int, help="size of the stack", default=512)
    argument_parser.add_argument("-addr", nargs="?", type=int, help="address where the program loads", default=linux.SEGMENT_START_ADDRESS)
    k = argument_parser.parse_args(sys.argv[1:])
    if k.source_file:
        source = k.source_file
    else:
        source = "./programs/hello_world.urcl"
    if k.output_file:
        output = k.output_file
    else:
        output = "./bin/" + source.split("/")[-1].split(".")[0]
    assert(isinstance(source, str))
    assert(isinstance(output, str))
    command_line_compile(source, output, small_file=k.no_sections,run=k.autorun, stack_size=k.stack, load_address=k.addr)

main()