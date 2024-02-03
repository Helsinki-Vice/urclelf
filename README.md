# urclelf
urclelf is a compiler for the URCL assembly language that produces lightweight, ld-compatible object files in the ELF format. Currently, it only supports approximately half of urcl opcodes. x86-32 LSB unix is the only supported target for now.
## What's URCL?
URCL (or urcl) is a low-level assembly-like langauge created by computer nerds to write portable software for custom computers built in the game Minecraft. It is intended to run on very limited 8-bit RISC computers. URCL can also be emulated, the de-facto reference implemention lives [here.](https://bramotte.github.io/urcl-explorer/)
## Running
urclelf requires Python 3.11, but no external packages. Simply `cd` into the project directory and `./hello.sh` to get started. I recommend creating an alias using `alias urclelf="python3 /path/to/project/folder/"`. Add to `~/.bashrc` for best results.
### C Interop
Objects produced by urclelf are similar to those produced by nasm and gcc and should be interoperable. To get gcc to produce a suitable output, run `gcc path/to/my_c_program.c -c -m32 --no-pie`. If you don't use compiler calling conventions (System V), your code will crash. urclelf can't link to the C standard library yet.
## Linking
You will need a few flags to link multiple files together with ld: `ld my_file_1.o my_file_2.o -m elf_i386 --no-pie`. For `.urcl` files that are not the entry point, pass `-lib` to urclelf. If the entry point is in C, use the `_start` symbol.
## What about URCL 1.6?
urclelf will be using URCL version 1.5 until support for the langauge is complete (this may be never!) The goal is to one day support many dialects and past versions of URCL using user-specified flags.
## Supported features:
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
- %TEXT port
## Unsupported features:
- array literals
- octal literals
- about half of all urcl opcodes
- headers
- most ports %TEXT
- LOD/STR (LLOD kinda works)
- real/long modes
- etc.
## Maybe one day...
- graphics via sdl2/opengl
- windows/mac support
- riscv/arm/x64 support
- custom linker
- baremetal (efi) support
- DWARF debugging
- complete URCL support in multiple dialects