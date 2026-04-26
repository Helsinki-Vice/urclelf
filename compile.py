import math
from dataclasses import dataclass
import enum
from typing import Literal, Callable

import urcl
import x86
import elf
from error import Traceback
import compile_x86
import target
import elf

PARSING_ERROR_MESSAGE = "Could not parse urcl source"
NO_ERROR_EXIT_CODE = 0

def urcl_instruction_to_x86_assembly(instruction: urcl.urclcst.InstructionCSTNode, bits: Literal[32, 64]) -> x86.ASMCode | Traceback:

    x86_code = x86.ASMCode(0, [])
    for family in compile_x86.TRANSLATIONS:
        if instruction.mnemonic in family.mnemonics:
            if len(instruction.operands) != family.operand_count:
                return Traceback.new(f"Incorrect number of operands to {instruction.mnemonic.name.upper()} - found {len(instruction.operands)}, expected {family.operand_count}", line_number=instruction.line_number, column_number=instruction.column_number)
            translation = family.compile(instruction, bits)
            if isinstance(translation, Traceback):
                error = translation
                return error
            else:
                x86_code.code.extend(translation.code)
                break
    else:
        return Traceback.new(f"No x86 translation for for URCL instruction {instruction.mnemonic.name}", instruction.line_number, instruction.column_number)

    return x86_code

def compile_urcl_to_x86_asm(urcl_program: urcl.CST, is_main: bool, bits: Literal[32, 64]) -> x86.ASMCode | Traceback:
    
    x86_assembly_code = x86.ASMCode(None, [])
    
    if is_main:
        x86_assembly_code.code.append(x86.Label("_start"))
    for line in urcl_program.lines:
        if isinstance(line, urcl.urclcst.Terminal):
            if isinstance(line.value, urcl.Label):
                x86_assembly_code.code.append(x86.Label(line.value.name))
                continue
            else:
                continue # TODO: Implement headers here
        
        x86_instruction = urcl_instruction_to_x86_assembly(line, bits)
        if isinstance(x86_instruction, Traceback):
            error = x86_instruction
            error.elaborate(f"URCL Instruction {line} could not be compiled into x86", line_number=line.line_number, column_number=line.column_number)
            return error
        for x86_instruction in x86_instruction.code:
            if isinstance(x86_instruction, x86.Label):
                continue
            x86_assembly_code.add_instruction(x86_instruction.mnemonic, [op.value for op in x86_instruction.operands])
    
    return x86_assembly_code

def compile_urcl_source_to_x86_asm(source: str, options: target.CompileOptions) -> x86.ASMCode | Traceback:

    urcl_program = urcl.parse(source)
    if isinstance(urcl_program, Traceback):
        error = urcl_program
        error.elaborate("Code cannot be parsed, aborting compilation")
        return error
    
    bits = options.target.get_word_size()
    if isinstance(bits, Traceback):
        error = bits
        return error
    
    assembly_code = compile_urcl_to_x86_asm(urcl_program, options.is_main, bits)
    if isinstance(assembly_code, Traceback):
        error = assembly_code
        error.elaborate(f"URCL code does not translate to {options.target.isa}")
        return error
    
    return assembly_code

def compile_urcl_source_to_flat_binary(source: str, options: target.CompileOptions) -> x86.AssembledMachineCode | Traceback:

    asm = compile_urcl_source_to_x86_asm(source, options)
    if isinstance(asm, Traceback):
        return asm
    
    bits = options.target.get_word_size()
    if isinstance(bits, Traceback):
        error = bits
        return error
    
    machine_code = x86.assemble(asm, bits)
    if isinstance(machine_code, Traceback):
        error = machine_code
        error.elaborate(f"Assembled {options.target.isa} program does not convert to machine code")
        return error
    
    return machine_code

def compile_urcl_to_executable(source: str, options: target.CompileOptions) -> bytes | Traceback:
    
    if options.executable_format == target.ExecutableFormat.ASM:
        asm = compile_urcl_source_to_x86_asm(source, options)
        if isinstance(asm, Traceback):
            return asm
        return str(asm).encode("utf-8") + b"\n"
        
    else:
        flat_binary = compile_urcl_source_to_flat_binary(source, options)
        if isinstance(flat_binary, Traceback):
            error = flat_binary
            error.elaborate("Machine code could not be generated")
            return error

        if options.executable_format == target.ExecutableFormat.FLAT:
            output_binary = flat_binary.binary
        elif options.executable_format == target.ExecutableFormat.ELF:
            output_binary = elf.make_relocatable_elf(flat_binary, is_64_bit=(options.target.isa==target.Isa.X64))
        else:
            return Traceback.new(f"Executable format {options.executable_format} is not supported")

        return bytes(output_binary)