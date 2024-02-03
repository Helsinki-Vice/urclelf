import math
from dataclasses import dataclass
import enum

import urcl
import x86
import elf
from error import Traceback
import compile_x86
import target
import elf.relocation as relocation

URCL_X86_REGISTER_MAPPING: dict[urcl.GeneralRegister | urcl.BasePointer | urcl.StackPointer, x86.Register] = {
    urcl.GeneralRegister(1): x86.Register.EAX,
    urcl.GeneralRegister(2): x86.Register.EBX,
    urcl.GeneralRegister(3): x86.Register.ECX,
    urcl.GeneralRegister(4): x86.Register.EDX,
    urcl.BasePointer(): x86.Register.EBP,
    urcl.StackPointer(): x86.Register.ESP
}

PARSING_ERROR_MESSAGE = "Could not parse urcl source"
NO_ERROR_EXIT_CODE = 0

def urcl_instruction_to_x86_assembly(instruction: urcl.urclcst.InstructionCSTNode, entry_point: int) -> x86.ASMCode | Traceback:

    x86_code = x86.ASMCode(0, [])
    for family in compile_x86.TRANSLATIONS:
        if instruction.mnemonic in family.mnemonics:
            if len(instruction.operands) != family.operand_count:
                return Traceback.new(f"Incorrect number of operands to {instruction.mnemonic.name.upper()} - found {len(instruction.operands)}, expected {family.operand_count}", line_number=instruction.line_number, column_number=instruction.column_number)
            translation = family.compile(instruction, entry_point)
            if isinstance(translation, Traceback):
                error = translation
                return error
            else:
                x86_code.code.extend(translation.code)
                break
    else:
        return Traceback.new(f"No x86 translation for for URCL instruction {instruction.mnemonic.name}", instruction.line_number, instruction.column_number)

    return x86_code

def compile_urcl_to_x86_asm(urcl_program: urcl.CST, is_main: bool) -> x86.ASMCode | Traceback:
    
    x86_assembly_code = x86.ASMCode(None, [])
    #x86_assembly_code.code.append(x86.Label("_start"))
    #x86_assembly_code.add_move(x86.Register.EBP, x86.Label("urclelf_stack_top")) # Setting up stack
    #x86_assembly_code.add_move(x86.Register.ESP, x86.Label("urclelf_stack_top")) # Setting up stack

    if is_main:
        x86_assembly_code.code.append(x86.Label("urclelf_program_start"))
        x86_assembly_code.code.append(x86.Label("_start"))
    for line in urcl_program.lines:
        if isinstance(line, urcl.urclcst.Terminal):
            if isinstance(line.value, urcl.Label):
                x86_assembly_code.code.append(x86.Label(line.value.name))
                continue
            else:
                continue # TODO: Implement headers here
        
        x86_instruction = urcl_instruction_to_x86_assembly(line, 0)
        if isinstance(x86_instruction, Traceback):
            error = x86_instruction
            error.elaborate(f"URCL Instruction {line} could not be compiled into x86", line_number=line.line_number, column_number=line.column_number)
            return error
        for x86_instruction in x86_instruction.code:
            if isinstance(x86_instruction, x86.Label):
                continue
            x86_assembly_code.add_instruction(x86_instruction.mnemonic, [op.value for op in x86_instruction.operands])
    
    return x86_assembly_code

def compile_urcl_source_to_flat_binary(source: str, options: target.CompileOptions) -> x86.CodegenOutput | Traceback:

    urcl_program = urcl.parse(source)
    if isinstance(urcl_program, Traceback):
        error = urcl_program
        error.elaborate("Code cannot be parsed, aborting compilation")
        return error
    
    if options.target.isa == target.Isa.X86:
        x86_assembly_code = compile_urcl_to_x86_asm(urcl_program, options.is_main)
        if isinstance(x86_assembly_code, Traceback):
            error = x86_assembly_code
            error.elaborate("URCL code does not translate to x86")
            return error
        
        machine_code = x86.assemble(x86_assembly_code)
        if isinstance(machine_code, Traceback):
            error = machine_code
            error.elaborate("Assembled x86 program does not convert to machine code")
            return error
        
        return machine_code
    else:
        return Traceback.new("Only x86 is currently supported")

def compile_urcl_to_executable(source: str, options: target.CompileOptions):
    
    if options.executable_format == target.ExecutableFormat.FLAT:
        return compile_urcl_source_to_flat_binary(source, options)
    
    elif options.executable_format == target.ExecutableFormat.ELF:
        code = compile_urcl_source_to_flat_binary(source, options)
        if isinstance(code, Traceback):
            error = code
            error.elaborate("Machine code could not be generated")
            return error
        #return elf.SimpleElf32Executable(code.binary, options).assemble(True)
        return relocation.make_relocatable_elf(code)
    
    else:
        return Traceback.new(f"Executable format {options.executable_format} is not supported")

    #return bytes(elf.SimpleElf32Executable(second_pass_binary, options).assemble(not options.no_sections))