# urclelf
urclelf is a compiler for the URCL assembly language that produces lightweight, statically-linked elf executables. Currently, it only supports approximately half of urcl opcodes. Notably, LOD, STR, and DW are not yet implemented. Linux x86-32 LSB is the only supported target for now.
## Running
urclelf requires Python 3.11, but no external packages. Simply `cd` into the project directory and `python3 ./ -h` to get started. I recommend creating an alias using `alias urclelf="python3 /path/to/project/folder/"`
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
## Unsupported features:
- array literals
- octal literals
- about half of all urcl opcodes
- headers
- all ports except %TEXT
- LOD/STR
- real/long modes
- etc.
## Maybe one day...
- object files / linking
- C interoperability
- graphics via sdl2/opengl
- windows support
- riscv/arm/x64 support
