import sys
from dataclasses import dataclass
from typing import Literal

import urcl
import x86
import elf
from error import Traceback
import compile_x86
import target
import elf

URCL_X86_REGISTER_MAPPING: dict[urcl.GeneralRegister | urcl.BasePointer | urcl.StackPointer, x86.Register] = {
    urcl.GeneralRegister(1): x86.Register.EAX,
    urcl.GeneralRegister(2): x86.Register.EBX,
    urcl.GeneralRegister(3): x86.Register.ECX,
    urcl.GeneralRegister(4): x86.Register.EDX,
    urcl.GeneralRegister(5): x86.Register.EDI,
    urcl.GeneralRegister(6): x86.Register.ESI,
    urcl.BasePointer(): x86.Register.EBP,
    urcl.StackPointer(): x86.Register.ESP
}

URCL_X86_REGISTER_MAPPING_16BIT: dict[urcl.GeneralRegister | urcl.BasePointer | urcl.StackPointer, x86.Register] = {
    urcl.GeneralRegister(1): x86.Register.AX,
    urcl.GeneralRegister(2): x86.Register.BX,
    urcl.GeneralRegister(3): x86.Register.CX,
    urcl.GeneralRegister(4): x86.Register.DX,
    urcl.GeneralRegister(5): x86.Register.DI,
    urcl.GeneralRegister(6): x86.Register.SI,
    urcl.BasePointer(): x86.Register.BP,
    urcl.StackPointer(): x86.Register.SP
}

URCL_X64_REGISTER_MAPPING: dict[urcl.GeneralRegister | urcl.BasePointer | urcl.StackPointer, x86.Register] = {
    urcl.GeneralRegister(1): x86.Register.RAX,
    urcl.GeneralRegister(2): x86.Register.RBX,
    urcl.GeneralRegister(3): x86.Register.RCX,
    urcl.GeneralRegister(4): x86.Register.RDX,
    urcl.GeneralRegister(5): x86.Register.RDI,
    urcl.GeneralRegister(6): x86.Register.RSI,
    urcl.BasePointer(): x86.Register.RBP,
    urcl.StackPointer(): x86.Register.RSP,
    urcl.GeneralRegister(8): x86.Register.R8,
    urcl.GeneralRegister(9): x86.Register.R9,
    urcl.GeneralRegister(10): x86.Register.R10,
    urcl.GeneralRegister(11): x86.Register.R11,
    urcl.GeneralRegister(8): x86.Register.R12,
    urcl.GeneralRegister(9): x86.Register.R13,
    urcl.GeneralRegister(10): x86.Register.R14,
    urcl.GeneralRegister(11): x86.Register.R15
}

URCL_X86_MNEMONIC_MAPPING: dict[urcl.Mnemonic, x86.Mnemonic] = {
    urcl.Mnemonic.NOP: x86.Mnemonic.NOP,
    urcl.Mnemonic.RET: x86.Mnemonic.RET,
    urcl.Mnemonic.JMP: x86.Mnemonic.JMP,
    urcl.Mnemonic.CAL: x86.Mnemonic.CALL,
    urcl.Mnemonic.BNZ: x86.Mnemonic.JNE,
    urcl.Mnemonic.BRZ: x86.Mnemonic.JE,
    urcl.Mnemonic.BRP: x86.Mnemonic.JGE,
    urcl.Mnemonic.INC: x86.Mnemonic.INC,
    urcl.Mnemonic.DEC: x86.Mnemonic.DEC,
    urcl.Mnemonic.NEG: x86.Mnemonic.NEG,
    urcl.Mnemonic.ADD: x86.Mnemonic.ADD,
    urcl.Mnemonic.SUB: x86.Mnemonic.SUB,
    urcl.Mnemonic.XOR: x86.Mnemonic.XOR,
    urcl.Mnemonic.OR: x86.Mnemonic.OR,
    urcl.Mnemonic.AND: x86.Mnemonic.AND,
    urcl.Mnemonic.BLE: x86.Mnemonic.JLE,
    urcl.Mnemonic.BGE: x86.Mnemonic.JGE,
    urcl.Mnemonic.BRE: x86.Mnemonic.JE,
    urcl.Mnemonic.BNE: x86.Mnemonic.JNE,
    urcl.Mnemonic.BRL: x86.Mnemonic.JL
}

PARSING_ERROR_MESSAGE = "Could not parse urcl source"
NO_ERROR_EXIT_CODE = 0

def convert_urcl_register_to_x86(register: urcl.GeneralRegister | urcl.BasePointer | urcl.StackPointer | urcl.Label, bits: Literal[16, 32, 64]) -> x86.Operand | Traceback:

    if isinstance(register, urcl.Label):
        return x86.Operand(x86.Label(register.name))
    
    if bits == 64:
        register_mapping = URCL_X64_REGISTER_MAPPING
    elif bits == 16:
        register_mapping = URCL_X86_REGISTER_MAPPING_16BIT
    else:
        register_mapping = URCL_X86_REGISTER_MAPPING
    x86_register = register_mapping.get(register)

    if x86_register:
        return x86.Operand(x86_register)
    else:
        assert(isinstance(register, urcl.GeneralRegister))
        effective_address = x86.sum_into_effective_address([x86.Label("urcl_memory_registers"), register.index], x86.PointerSize.from_bits(bits))
        if isinstance(effective_address, Traceback):
            error = effective_address
            error.elaborate(f"URCL register {register} could not be mapped to a machine register or memory address")
            return error
        return x86.Operand(effective_address)

def get_x86_destination_register(instruction: urcl.InstructionCSTNode, bits: Literal[16, 32, 64]) -> x86.Register | x86.EffectiveAddress | x86.Immediate | Traceback:

    if not instruction.operands:
        return Traceback.new(f"{instruction.mnemonic.name.upper()} instruction is missing operands, expected a register", line_number=instruction.line_number, column_number=instruction.column_number)
    urcl_destination_register = instruction.operands[0].value
    if not isinstance(urcl_destination_register, (urcl.GeneralRegister, urcl.BasePointer, urcl.StackPointer, urcl.Label)):
        return Traceback.new(f"{instruction.mnemonic.name.upper()} instruction expected first operand to be a register.", line_number=instruction.operands[0].line_number, column_number=instruction.operands[0].column_number)

    if isinstance(urcl_destination_register, Traceback):
        error = urcl_destination_register
        error.elaborate(f"{instruction.mnemonic.name.upper()} instruction does not have valid register as a destination", line_number=instruction.line_number, column_number=instruction.column_number)
        return error
    x86_destination_register = convert_urcl_register_to_x86(urcl_destination_register, bits)
    if isinstance(x86_destination_register, Traceback):
        error = x86_destination_register
        error.elaborate(f"URCL register {urcl_destination_register} has no x86/x64 equivalent")
        return error
    
    return x86_destination_register.value

def urcl_operand_to_x86(operand: urcl.urclcst.OperandCSTNode, bits: Literal[16, 32, 64]) -> x86.Operand | Traceback:

    if isinstance(operand.value, urcl.urclcst.Label):
        return x86.Operand(x86.Label(operand.value.name))
    elif isinstance(operand.value, (urcl.GeneralRegister, urcl.BasePointer, urcl.StackPointer)):
        register = convert_urcl_register_to_x86(operand.value, bits)
        if isinstance(register, Traceback):
            error = register
            error.elaborate(f"URCL register {operand.value} has no x86/x64 equivalent")
            return error
        return register
    elif isinstance(operand.value, int):
        return x86.Operand(operand.value)
    elif isinstance(operand.value, urcl.urclcst.RelativeAddress):
        return x86.Operand(operand.value.offset) # FIXME
    elif isinstance(operand.value, urcl.urclcst.Character):
        return x86.Operand(ord(operand.value.char))
    elif isinstance(operand.value, urcl.PortType):
        return x86.Operand(operand.value.id)
    elif isinstance(operand.value, urcl.DefinedImmediate):
        return x86.Operand(0) # FIXME
    else:
        return Traceback.new(f"URCL operand {operand} has no x86/x64 equivalent")

def get_jump_target(instruction: urcl.InstructionCSTNode, bits) -> x86.Label | x86.Register | Traceback:

    if not instruction.operands:
        return Traceback.new(f"{instruction.mnemonic.name.upper()} instruction is missing operands, expected a label or register", line_number=instruction.line_number, column_number=instruction.column_number)
    destination = urcl_operand_to_x86(instruction.operands[0], bits)
    if isinstance(destination, Traceback):
        error = destination
        error.elaborate(f"Jump target for instruction {instruction.mnemonic.name.upper()} is invalid")
        return error
    if not isinstance(destination.value, (x86.Label, x86.Register)):
        return Traceback.new(f"{instruction.mnemonic.name.upper()} instruction expected first operand to be a label or register", line_number=instruction.operands[0].line_number, column_number=instruction.operands[0].column_number)
    
    return destination.value

def get_instruction_info(instruction: urcl.InstructionCSTNode, bits: Literal[16, 32, 64], requires_jump_target: bool=False, writes_to_register: bool=False, required_sources: int=0, source_start_index: int=1) -> compile_x86.InstructionInfo | Traceback:

    urcl_jump_target = get_jump_target(instruction, bits)
    if isinstance(urcl_jump_target, Traceback):
        error = urcl_jump_target
        urcl_jump_target = None
        if requires_jump_target:
            return error
    
    x86_destination_register = get_x86_destination_register(instruction, bits)
    if isinstance(x86_destination_register, Traceback):
        error = x86_destination_register
        x86_destination_register = None
        if writes_to_register:
            return error
    
    if required_sources and len(instruction.operands) - source_start_index < required_sources:
        return Traceback.new(f"Instruction {instruction.mnemonic.name.upper()} requires {required_sources} data sources, only {len(instruction.operands) - 1} were found")
    
    sources = []
    for operand in instruction.operands[source_start_index:]:
        source = urcl_operand_to_x86(operand, bits)
        if isinstance(source, Traceback):
            return source
        sources.append(source)

    port_locations: dict[urcl.Mnemonic, int] = {
        urcl.Mnemonic.OUT: 0,
        urcl.Mnemonic.IN: 1
    }
    
    port = None
    port_index = port_locations.get(instruction.mnemonic)
    port_is_required = port_index is not None
    if port_is_required:
        if len(instruction.operands) <= port_index:
            return Traceback.new(f"Instruction {instruction.mnemonic.name.upper()} requires a port argument, but not enough operands were provided")
        operand = instruction.operands[port_index]
        if isinstance(operand.value, urcl.PortType):
            port = operand.value
        elif isinstance(operand.value, int):
            port = urcl.PortType(operand.value, "UNKNOWN")
        else:
            pass
    
    if port_is_required and port is None:
        return Traceback.new(f"Instruction {instruction.mnemonic.name.upper()} requires a port argument, but one was not provided")


    return compile_x86.InstructionInfo(urcl_jump_target, x86_destination_register, sources, instruction.mnemonic, URCL_X86_MNEMONIC_MAPPING.get(instruction.mnemonic), port, instruction.operands[source_start_index:], instruction.line_number, instruction.column_number)

def urcl_instruction_to_x86_assembly(instruction: urcl.urclcst.InstructionCSTNode, bits: Literal[16, 32, 64]) -> x86.ASMCode | Traceback:

    x86_code = x86.ASMCode(0, [])
    for family in compile_x86.TRANSLATIONS:
        if instruction.mnemonic in family.mnemonics:
            if len(instruction.operands) != family.operand_count:
                return Traceback.new(f"Incorrect number of operands to {instruction.mnemonic.name.upper()} - found {len(instruction.operands)}, expected {family.operand_count}", line_number=instruction.line_number, column_number=instruction.column_number)
            instruction_info = get_instruction_info(instruction, bits, family.requires_jump_target, family.writes_to_register, required_sources=family.required_sources, source_start_index=family.source_start_index)
            if isinstance(instruction_info, Traceback):
                error = instruction_info
                error.elaborate(f"Operands passed to {instruction.mnemonic.name} instruction are not consistent with the expected format")
                return error
            translation = family.compile(bits, instruction_info)
            if isinstance(translation, Traceback):
                error = translation
                return error
            else:
                if len(translation.code) > 0:
                    x86_code.code.extend(translation.code)
                    break
                else:
                    print(instruction_info, file=sys.stderr)
                    return Traceback.new(f"Translation for for URCL instruction {instruction.mnemonic.name} with family {",".join([f.name for f in family.mnemonics])} failed", instruction.line_number, instruction.column_number)
    else:
        return Traceback.new(f"No x86 translation for for URCL instruction {instruction.mnemonic.name}", instruction.line_number, instruction.column_number)

    return x86_code

def compile_urcl_to_x86_asm(urcl_program: urcl.CST, is_main: bool, bits: Literal[16, 32, 64]) -> x86.ASMCode | Traceback:
    
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
            error.elaborate(f"URCL instruction {line} could not be compiled into x86", line_number=line.line_number, column_number=line.column_number)
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
        error.elaborate(f"URCL code does not translate to {options.target.isa.value}")
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
    
    if options.executable_format == target.ExecutableFormat.TOKENS:
        tokens = urcl.tokenize(source)
        if isinstance(tokens, Traceback):
            return tokens
        return str(tokens).encode("utf-8") + b"\n"
        
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