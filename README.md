urclelf is a compiler for the URCL assembly language that produces lightweight, statically-linked elf executables. Currently, it only supports approximately half of urcl opcodes. Notably, LOD, STR, and DW are not yet implemented. Linux x86-32 LSB is the only supported target for now.

Supported features:
 - comments
 - labels
 - string literals
 - char literals
 - utf-8 strings
 - hex and binary literals
 - %TEXT port
 - outputting strings directly to %TEXT
 - PSH and POP
 - branching
 - @DEFINE
 - defined immediates (currently broken)
 - line/column numbers for errors

Unsupported features:
 - array literals
 - octal literals
 - about half of all urcl opcodes
 - all ports except %TEXT
 - LOD/STR
 - 8/32 bit modes
 - x86 SIB addressing
 - debug symbols
 - linking
 - etc.