# urclelf
urclelf is a compiler for the URCL assembly language that produces lightweight object files in the ELF format. Currently, it only targets System V i386 (unix) machines and supports approximately half of urcl opcodes.

## What's URCL?
URCL (or urcl) is a low-level assembly-like langauge created by computer nerds to write portable software for custom computers built in the game Minecraft. It is intended to run on very limited 8-bit RISC computers. URCL can also be emulated, the de-facto reference implemention lives [here.](https://bramotte.github.io/urcl-explorer/)

## Getting Started
urclelf requires Python 3.11, but no external packages. Simply `cd` into the project directory and `make hello` to get started. I recommend creating an alias using `alias urclelf="python3 /path/to/project/folder/"`. Add to `~/.bashrc` for best results.

## Application Binary Interface
urclelf only produces 32-bit, non-position-independent, relocatable ELF objects using the i386 supplement of the System V ABI. These objects should be interoperable with those produced by other compilers like nasm and gcc. x64 codegen is in the works, but is mostly broken — pass -m x64 to urclelf to enable.

### nasm
`nasm my_program.asm -f elf32 -o my_program.o`

### gcc
`gcc my_program.c -c -m32 -no-pie -o my_program.o -nostartfiles` (omit `-nostartfiles` if you have defined `main`)

## Linking
The linker `ld` is used to convert urclelf's output into a runnable executable. Once all of the files (urcl and otherwise) are compiled to object files of the same ABI, link using `ld my_file_1.o my_file_2.o -m elf_i386 --no-pie`. Note that the special symbol `_start` is the first instruction (entry point) and can be defined once. Because urclelf automaticly declares `_start` at the top of each file, you will need to pass `-lib` to urclelf for each file that is not the entry point. If the entry point is in C and `-nostartfiles` has not been passed, declare ` void _start() {...}` instead of `int main() {...}`. Please read the makefile! It has many examples of multi-file compilation.

## What About URCL 1.6?
urclelf will be using URCL version 1.5 until support for the langauge is complete (this may be never!) The goal is to one day support many dialects and past versions of URCL using user-specified flags.

## Supported Features:
- comments
- labels
- string literals
- char literals
- utf-8 strings
- hex and binary literals
- memory literals
- %TEXT port
- outputting strings directly to %TEXT
- PSH and POP
- branching
- @DEFINE
- defined immediates (currently broken)
- line/column numbers for errors
- %NUMB port

## Unsupported Features:
- array literals
- octal literals
- about half of all urcl opcodes
- headers
- most ports
- LOD/STR (LLOD kinda works)
- most x64 features
- etc.

## Maybe One Day...
- graphics via sdl2/opengl
- windows/mac support
- riscv/arm support
- custom linker
- baremetal (efi) support
- DWARF debugging
- complete URCL support in multiple dialects