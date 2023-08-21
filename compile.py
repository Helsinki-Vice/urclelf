import math

import urcl
import x86
import elf
from error import Traceback, Message

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
def urcl_instruction_to_x86_assembly(instruction: urcl.urclcst.InstructionCSTNode) -> x86.Program | Traceback:
    
        x86_code = x86.Program(0, [])
        if instruction.mnemonic in [urcl.Mnemonic.HLT, urcl.Mnemonic.NOP, urcl.Mnemonic.RET]:
            if len(instruction.operands) != 0:
                return Traceback.new(f"Incorrect number of operands supplied to {instruction.mnemonic.value.upper()} instruction - found {len(instruction.operands)}, expected 0.", instruction.line_number, instruction.column_number)
            if instruction.mnemonic == urcl.Mnemonic.HLT:
                x86_code.add_move(x86.Register.EAX, x86.LINUX_EXIT)
                x86_code.add_instruction(x86.Mnemonic.INT, [0x80])
            elif instruction.mnemonic == urcl.Mnemonic.NOP:
                x86_code.add_instruction(x86.Mnemonic.NOP, [])
            elif instruction.mnemonic == urcl.Mnemonic.RET:
                x86_code.add_instruction(x86.Mnemonic.RETN, [])
            else:
                return Traceback.new(f"No x86 translation for for URCL instruction {instruction.mnemonic.name}", instruction.line_number, instruction.column_number)
         
        elif instruction.mnemonic in urcl.TWO_OPERAND_ARITHMETIC_MNEMONICS:

            if not instruction.operands or len(instruction.operands) > 2:
                return Traceback.new(f"Incorrect number of operands supplied to {instruction.mnemonic.value.upper()} instruction - found {len(instruction.operands)}, expected 2.", instruction.line_number, instruction.column_number)
            destination = get_x86_destination_register(instruction)
            if not destination:
                return Traceback.new(f"{instruction.mnemonic.value.upper()} instruction received incorrect operand type (expected register).", instruction.line_number, instruction.column_number)
            urcl_source_operand = instruction.operands[len(instruction.operands) - 1]
            x86_source_operand = urcl_operand_to_x86(urcl_source_operand)

            if x86_source_operand is None:
                return Traceback.new(f"Invalid source operand {urcl_source_operand}", urcl_source_operand.line_number, urcl_source_operand.column_number)
            x86_code.add_move(destination, x86_source_operand.value)
            if instruction.mnemonic == urcl.Mnemonic.MOV:
                pass # Move does not perform a calculation, consider it NOP
            elif instruction.mnemonic == urcl.Mnemonic.INC:
                x86_code.add_instruction(x86.Mnemonic.INC, [destination])
            elif instruction.mnemonic == urcl.Mnemonic.DEC:
                x86_code.add_instruction(x86.Mnemonic.DEC, [destination])
            elif instruction.mnemonic == urcl.Mnemonic.NEG:
                x86_code.add_instruction(x86.Mnemonic.NEG, [destination])
            elif instruction.mnemonic == urcl.Mnemonic.LSH:
                x86_code.add_instruction(x86.Mnemonic.ROL, [destination])
                x86_code.add_instruction(x86.Mnemonic.AND, [destination, (2**31 - 1) << 1])
            elif instruction.mnemonic == urcl.Mnemonic.RSH:
                x86_code.add_instruction(x86.Mnemonic.ROL, [destination])
                x86_code.add_instruction(x86.Mnemonic.AND, [destination, 2**31])
            else:
                return Traceback.new(f"No x86 translation for for URCL instruction {instruction.mnemonic.name}", instruction.line_number, instruction.column_number)
        
        elif instruction.mnemonic in [urcl.Mnemonic.ADD, urcl.Mnemonic.SUB, urcl.Mnemonic.XOR, urcl.Mnemonic.OR]:
            if len(instruction.operands) != 3:
                return Traceback.new(f"Incorrect number of operands supplied to {instruction.mnemonic.value.upper()} instruction - found {len(instruction.operands)}, expected 3.", instruction.line_number, instruction.column_number)
            destination = get_x86_destination_register(instruction)
            if not destination:
                return Traceback.new(f"{instruction.mnemonic.value.upper()} instruction received incorrect destination type (expected register).", instruction.line_number, instruction.column_number)
            source_1 = urcl_operand_to_x86(instruction.operands[1])
            source_2 = urcl_operand_to_x86(instruction.operands[2])
            if source_1 is None:
                return Traceback.new("TODO")
            if source_2 is None:
                return Traceback.new("TODO")
            if instruction.operands[0] != instruction.operands[1]:
                x86_code.add_move(destination, source_1.value)
            arithmetic_mapping: dict[urcl.Mnemonic, x86.Mnemonic] = {
                urcl.Mnemonic.ADD: x86.Mnemonic.ADD,
                urcl.Mnemonic.SUB: x86.Mnemonic.SUB,
                urcl.Mnemonic.XOR: x86.Mnemonic.XOR,
            }
            x86_mnemonic = arithmetic_mapping.get(instruction.mnemonic)
            if x86_mnemonic:
                x86_code.add_instruction(x86_mnemonic, [destination, source_2.value])
            else:
                return Traceback.new(f"No x86 translation for for URCL instruction {instruction.mnemonic.name.upper()}", instruction.line_number, instruction.column_number)
        
        elif instruction.mnemonic in [urcl.Mnemonic.JMP, urcl.Mnemonic.CAL]:
            destination_operand = get_jump_target(instruction)
            if len(instruction.operands) != 1:
                return Traceback.new(f"Incorrect number of operands supplied to {instruction.mnemonic.name.upper()} instruction - found {len(instruction.operands)}, expected 1.", instruction.line_number, instruction.column_number)
            if isinstance(destination_operand, urcl.urclcst.Label):
                if instruction.mnemonic == urcl.Mnemonic.JMP:
                    x86_code.add_instruction(x86.Mnemonic.JMP, [x86.Label(destination_operand.name)])
                elif instruction.mnemonic == urcl.Mnemonic.CAL:
                    x86_code.add_instruction(x86.Mnemonic.CALL, [x86.Label(destination_operand.name)])
                else:
                    return Traceback.new(f"No x86 translation for for URCL instruction {instruction.mnemonic.name.upper()}", instruction.line_number, instruction.column_number)
            else:
                return Traceback.new(f"JMP instruction operand 1 is of incorrect type (expected Label).", instruction.line_number, instruction.column_number)
        
        elif instruction.mnemonic in urcl.TWO_OPERAND_CONDITION_JUMP_MNEMONICS:
            destination_operand = get_jump_target(instruction)
            if not isinstance(destination_operand, urcl.urclcst.Label):
                return Traceback.new(f"{instruction.mnemonic.name} instruction operand 1 is of incorrect type (expected label).", instruction.line_number, instruction.column_number)
            if len(instruction.operands) != 2:
                return Traceback.new(f"Incorrect number of operands supplied to {instruction.mnemonic.name} instruction - found {len(instruction.operands)}, expected 2.", instruction.line_number, instruction.column_number)
            x86_source_operand = urcl_operand_to_x86(instruction.operands[1])
            if x86_source_operand is None:
                return Traceback.new("TODO")
            x86_code.add_instruction(x86.Mnemonic.CMP, [x86_source_operand.value, 0])
            if instruction.mnemonic == urcl.Mnemonic.BNZ:
                x86_code.add_instruction(x86.Mnemonic.JNE, [x86.Label(destination_operand.name)])
            elif instruction.mnemonic == urcl.Mnemonic.BRZ:
                x86_code.add_instruction(x86.Mnemonic.JE, [x86.Label(destination_operand.name)])
            elif instruction.mnemonic == urcl.Mnemonic.BRP:
                x86_code.add_instruction(x86.Mnemonic.JGE, [x86.Label(destination_operand.name)])
            else:
                return Traceback.new(f"No x86 translation for for URCL instruction {instruction.mnemonic.name.upper()}", instruction.line_number, instruction.column_number)
        
        elif instruction.mnemonic in urcl.THREE_OPERAND_CONDITION_JUMP_MNEMONICS:
            destination_operand = get_jump_target(instruction)
            if not isinstance(destination_operand, urcl.urclcst.Label):
                return Traceback.new(f"{instruction.mnemonic.name} instruction operand 1 '{destination_operand}' is of incorrect type (expected label).", instruction.line_number, instruction.column_number)
            if len(instruction.operands) != 3:
                return Traceback.new(f"Incorrect number of operands supplied to {instruction.mnemonic.name} instruction - found {len(instruction.operands)}, expected 3.", instruction.line_number, instruction.column_number)
            x86_source_operand_1 = urcl_operand_to_x86(instruction.operands[1])
            x86_source_operand_2 = urcl_operand_to_x86(instruction.operands[2])
            if x86_source_operand_1 is None:
                return Traceback.new("TODO")
            if x86_source_operand_2 is None:
                return Traceback.new("TODO")
            x86_code.add_instruction(x86.Mnemonic.CMP, [x86_source_operand_1.value, x86_source_operand_2.value])
            if instruction.mnemonic == urcl.Mnemonic.BLE:
                x86_code.add_instruction(x86.Mnemonic.JBE, [x86.Label(destination_operand.name)])
            elif instruction.mnemonic == urcl.Mnemonic.BGE:
                x86_code.add_instruction(x86.Mnemonic.JGE, [x86.Label(destination_operand.name)])
            elif instruction.mnemonic == urcl.Mnemonic.BRE:
                x86_code.add_instruction(x86.Mnemonic.JE, [x86.Label(destination_operand.name)])
            elif instruction.mnemonic == urcl.Mnemonic.BNE:
                x86_code.add_instruction(x86.Mnemonic.JNE, [x86.Label(destination_operand.name)])
            else:
                return Traceback.new(f"No x86 translation for for URCL instruction {instruction.mnemonic.name.upper()}", instruction.line_number, instruction.column_number)
        
        elif instruction.mnemonic == urcl.Mnemonic.OUT:
            if len(instruction.operands) != 2:
                return Traceback.new(f"Incorrect number of operands supplied to OUT instruction - found {len(instruction.operands)}, expected 2.", instruction.line_number, instruction.column_number)
            if isinstance(instruction.operands[0].value, urcl.Port):
                port = instruction.operands[0].value
            elif isinstance(instruction.operands[0].value, int):
                port = urcl.Port.from_value(instruction.operands[0].value)
            else:
                port = None
            if port is None:
                return Traceback.new(f"OUT instruction operand 1 '{instruction.operands[0]}' is not a valid port", instruction.line_number, instruction.column_number)
           
            # URCL standard requires ascii encoding but we use utf-8 instead
            # don't tell ModPunchTree
            if isinstance(instruction.operands[1].value, int):
                output_string = chr(instruction.operands[1].value).encode("utf-8")
            elif isinstance(instruction.operands[1].value, str):
                # NOTE: outputting strings to %TEXT is non-standard
                output_string = instruction.operands[1].value.encode("utf-8")
            elif isinstance(instruction.operands[1].value, urcl.Character):
                output_string = instruction.operands[1].value.char.encode("utf-8")
            elif isinstance(instruction.operands[1].value, urcl.GeneralRegister):
                output_string = instruction.operands[1].value
            else:
                return Traceback.new(f"OUT instruction operand 2 '{instruction.operands[1]}' cannot be output onto a port.", instruction.line_number, instruction.column_number)
            
            x86_code.add_instructions_to_save_general_registers()

            if isinstance(output_string, urcl.GeneralRegister):
                string_length_bytes = 4
                uint32_count = 1
                x86_code.add_instruction(x86.Mnemonic.PUSH, [URCL_X86_REGISTER_MAPPING[output_string]])
            else:
                uint32_count = math.ceil(len(output_string) / 4)
                string_length_bytes = len(output_string)
                for u32 in bytes_to_stack_ints(output_string):
                    x86_code.add_instruction(x86.Mnemonic.PUSH, [u32])
            x86_code.add_fwrite_linux_syscall(x86.Register.ESP, string_length_bytes, x86.LINUX_STDOUT)
            x86_code.add_instruction(x86.Mnemonic.ADD, [x86.Register.ESP, uint32_count * 4])
            x86_code.add_instructions_to_restore_general_registers()
            
        elif instruction.mnemonic in [urcl.Mnemonic.PSH]:
            if len(instruction.operands) != 1:
                return Traceback.new(f"Incorrect number of operands supplied to {instruction.mnemonic.value.upper()} instruction - found {len(instruction.operands)}, expected 1.", instruction.line_number, instruction.column_number)
            x86_source_operand = urcl_operand_to_x86(instruction.operands[0])
            if x86_source_operand is None:
                return Traceback.new("TODO")
            x86_code.add_instruction(x86.Mnemonic.PUSH, [x86_source_operand.value])
        
        elif instruction.mnemonic in [urcl.Mnemonic.POP]:
            if len(instruction.operands) != 1:
                return Traceback.new(f"Incorrect number of operands supplied to {instruction.mnemonic.value.upper()} instruction - found {len(instruction.operands)}, expected 1.", instruction.line_number, instruction.column_number)
            x86_register = get_x86_destination_register(instruction)
            if x86_register is None:
                return Traceback.new("TODO")
            x86_code.add_instruction(x86.Mnemonic.POP, [x86_register])
            
        elif instruction.mnemonic in [urcl.Mnemonic.DIV, urcl.Mnemonic.MOD]:
            if len(instruction.operands) != 3:
                return Traceback.new(f"Incorrect number of operands supplied to {instruction.mnemonic.value.upper()} instruction - found {len(instruction.operands)}, expected 3.", instruction.line_number, instruction.column_number)
            destination = get_x86_destination_register(instruction)
            if not destination:
                return Traceback.new(f"{instruction.mnemonic.value.upper()} instruction received incorrect destination type (expected register).", instruction.line_number, instruction.column_number)
            source_1 = urcl_operand_to_x86(instruction.operands[1])
            source_2 = urcl_operand_to_x86(instruction.operands[2])
            if source_1 is None:
                return Traceback.new("TODO")
            if source_2 is None:
                return Traceback.new("TODO")
            temp_regs: list[x86.Register] = []
            for reg in [x86.Register.EAX, x86.Register.EBX, x86.Register.EDX]:
                if reg != destination:
                    x86_code.add_instruction(x86.Mnemonic.PUSH, [reg])
                    temp_regs.append(reg)
            x86_code.add_move(x86.Register.EAX, source_1.value)
            x86_code.add_move(x86.Register.EDX, 0)
            x86_code.add_move(x86.Register.EBX, source_2.value)
            x86_code.add_instruction(x86.Mnemonic.DIV, [x86.Register.EBX])
            if instruction.mnemonic == urcl.Mnemonic.DIV:
                x86_code.add_move(destination, x86.Register.EAX)
            else:
                x86_code.add_move(destination, x86.Register.EDX)
            for reg in temp_regs.__reversed__():
                x86_code.add_instruction(x86.Mnemonic.POP, [reg])
        
        elif instruction.mnemonic in [urcl.Mnemonic.MLT]:
            if len(instruction.operands) != 3:
                return Traceback.new(f"Incorrect number of operands supplied to {instruction.mnemonic.value.upper()} instruction - found {len(instruction.operands)}, expected 3.", instruction.line_number, instruction.column_number)
            destination = get_x86_destination_register(instruction)
            if not destination:
                return Traceback.new(f"{instruction.mnemonic.value.upper()} instruction received incorrect destination type (expected register).", instruction.line_number, instruction.column_number)
            source_1 = urcl_operand_to_x86(instruction.operands[1])
            source_2 = urcl_operand_to_x86(instruction.operands[2])
            if source_1 is None:
                return Traceback.new("TODO")
            if source_2 is None:
                return Traceback.new("TODO")
            if destination != x86.Register.EAX:
                x86_code.add_instruction(x86.Mnemonic.PUSH, [x86.Register.EAX])
            if destination != x86.Register.EDX:
                x86_code.add_instruction(x86.Mnemonic.PUSH, [x86.Register.EDX])
            x86_code.add_move(x86.Register.EAX, source_1.value)
            
            x86_code.add_instruction(x86.Mnemonic.MUL, [source_2.value])
            x86_code.add_move(destination, x86.Register.EAX)
            
            if destination != x86.Register.EDX:
                x86_code.add_instruction(x86.Mnemonic.POP, [x86.Register.EDX])
            if destination != x86.Register.EAX:
                x86_code.add_instruction(x86.Mnemonic.POP, [x86.Register.EAX])
            
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

        x86_instruction = urcl_instruction_to_x86_assembly(line)
        if isinstance(x86_instruction, Traceback):
            x86_instruction.elaborate("Instruction could not be compiled")
            return x86_instruction
        for x86_instruction in x86_instruction.code:
            if isinstance(x86_instruction, x86.Label):
                continue
            x86_assembly_code.add_instruction(x86_instruction.mnemonic, [op.value for op in x86_instruction.operands])

        
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
    first_pass_executable = elf.Program(first_pass_binary, stack_size, use_section_header_table=not small_filesize)
    second_pass_binary = compile_urcl_source_to_flat_binary(source, first_pass_executable.entry_point, first_pass_executable.calculate_stack_base_address() + first_pass_executable.stack_size)
    if isinstance(second_pass_binary, Traceback):
        error = second_pass_binary
        error.elaborate("Unable to generate x86 assembly (Unreachable error?!)")
        return error
    #print(second_pass_binary.hex())

    return bytes(elf.Program(second_pass_binary, stack_size).assemble(use_section_header_table=not small_filesize))