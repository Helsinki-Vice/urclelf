import math
from dataclasses import dataclass
import enum

import urcl
import x86
import elf
from error import Traceback, Message
import translations

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

def get_destination_register(instruction: urcl.InstructionCSTNode) -> urcl.GeneralRegister | None:

    if not instruction.operands:
        return None
    urcl_destination_register = instruction.operands[0].value
    if not isinstance(urcl_destination_register, urcl.GeneralRegister):
        return None
    
    return urcl_destination_register

def get_x86_destination_register(instruction: urcl.InstructionCSTNode) -> x86.Register | None:

    urcl_destination_register = get_destination_register(instruction)
    if not urcl_destination_register:
        return None
    x86_destination_register = URCL_X86_REGISTER_MAPPING.get(urcl_destination_register)
    if not x86_destination_register:
        return None
    
    return x86_destination_register

def get_jump_target(instruction: urcl.InstructionCSTNode) -> urcl.Label | None:

    if not instruction.operands:
        return None
    urcl_destination = instruction.operands[0].value
    if not isinstance(urcl_destination, urcl.Label):
        return None
    
    return urcl_destination

def urcl_operand_to_x86(operand: urcl.urclcst.OperandCSTNode) -> x86.Operand | None:

    if isinstance(operand.value, urcl.urclcst.Label):
        return x86.Operand(x86.Label(operand.value.name))
    elif isinstance(operand.value, (urcl.GeneralRegister, urcl.BasePointer, urcl.StackPointer)):
        register = URCL_X86_REGISTER_MAPPING.get(operand.value)
        if register:
            return x86.Operand(register)
    elif isinstance(operand.value, int):
        return x86.Operand(operand.value)
    elif isinstance(operand.value, urcl.urclcst.RelativeAddress):
        return x86.Operand(operand.value.offset)
    elif isinstance(operand.value, urcl.urclcst.Character):
        return x86.Operand(ord(operand.value.char))
    elif isinstance(operand.value, urcl.Port):
        return x86.Operand(operand.value.value.id)
    else:
        return None

def bytes_to_stack_ints(value: bytes):
    """Givin a sequence of bytes, what 32 bit little endian ints do we push
    to the stack to make the stack pointer point to the bytes?"""
    int_count = math.ceil(len(value) / 4)
    result = [0] * int_count
    for i, byte in enumerate(value + bytes(int_count * 4 - len(value))):
        int_index = int_count - (i // 4) - 1
        shift_amount = (i % 4) * 8
        result[int_index] += byte << shift_amount
    
    return result

# The rather frightening code below does the majority of
# the work in translating urcl to x86 assembly. Don't like elif chains? Too bad!
# TODO: use ast instead of cst for compilation
# TODO: fix spagetti
def urcl_instruction_to_x86_assembly(instruction: urcl.urclcst.InstructionCSTNode, entry_point: int) -> x86.Program | Traceback:

        x86_code = x86.Program(0, [])
        for mnemonics, compiler_function in translations.TRANSLATIONS:
            if instruction.mnemonic in mnemonics:
                translation = compiler_function(instruction, entry_point)
                if isinstance(translation, Traceback):
                    error = translation
                    return error
                else:
                    x86_code.code.extend(translation.code)
                    break
        else:
            return Traceback.new(f"No x86 translation for for URCL instruction {instruction.mnemonic.name}", instruction.line_number, instruction.column_number)
    
        return x86_code

def compile_urcl_source_to_flat_binary(source: str, entry_point: int, stack_base_pointer: int) -> "Traceback | bytes":

    error = None
    tokens = urcl.tokenize(source)
    if not isinstance(tokens, urcl.TokenStream):
        error = tokens
        error.elaborate(PARSING_ERROR_MESSAGE)
        return error
    
    urcl_program = urcl.CST.from_tokens(tokens)
    if not isinstance(urcl_program, urcl.CST):
        error = urcl_program
        error.elaborate(PARSING_ERROR_MESSAGE)
        return error
    
    x86_assembly_code = x86.Program(entry_point, [])
    x86_assembly_code.add_move(x86.Register.EBX, NO_ERROR_EXIT_CODE) # Default return code
    x86_assembly_code.add_move(x86.Register.EBP, stack_base_pointer) # Setting up stack
    x86_assembly_code.add_move(x86.Register.ESP, stack_base_pointer) # Setting up stack
    
    for line in urcl_program.lines:
        if isinstance(line, urcl.urclcst.Terminal):
            if isinstance(line.value, urcl.Label):
                x86_assembly_code.code.append(x86.Label(line.value.name))
                continue
            else:
                continue # TODO: Implement headers here

        x86_instruction = urcl_instruction_to_x86_assembly(line, 0)
        if isinstance(x86_instruction, Traceback):
            x86_instruction.elaborate("Instruction could not be compiled")
            return x86_instruction
        for x86_instruction in x86_instruction.code:
            if isinstance(x86_instruction, x86.Label):
                continue
            x86_assembly_code.add_instruction(x86_instruction.mnemonic, [op.value for op in x86_instruction.operands])
    x86_assembly_code.code.append(x86.Label("URCL_M0"))
        
    machine_code = x86.assemble(x86_assembly_code)
    if isinstance(machine_code, Traceback):
        error = machine_code
        error.elaborate("Unable to generate x86 assembly")
        return error
    
    return machine_code

def compile_urcl_to_executable(source: str, stack_size:int=512, small_filesize:bool=False):
    
    # We need to compile twice because of a chicken-and-egg situation:
    # We can't resolve labels/relatives (and therefore compile) without knowing the entry point,
    # but we don't know the entry point without compiling first.
    # After compiling with an assumed entry point of 0, the entry point can be
    # extracted from the executable and fed into the compiler.
    first_pass_binary = compile_urcl_source_to_flat_binary(source, 0, 0)
    if isinstance(first_pass_binary, Traceback):
        error = first_pass_binary
        error.elaborate("Unable to generate x86 assembly")
        return error
    first_pass_executable = elf.Elf32Exec(first_pass_binary, stack_size, use_section_header_table=not small_filesize)
    second_pass_binary = compile_urcl_source_to_flat_binary(source, first_pass_executable.entry_point, first_pass_executable.calculate_stack_base_address() + first_pass_executable.stack_size)
    if isinstance(second_pass_binary, Traceback):
        error = second_pass_binary
        error.elaborate("Unable to generate x86 assembly (Unreachable error?!)")
        return error

    return bytes(elf.Elf32Exec(second_pass_binary, stack_size).assemble(use_section_header_table=not small_filesize))