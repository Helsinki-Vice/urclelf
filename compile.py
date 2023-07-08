import math

import urcl
import x86asm
import elf
from error import Traceback, Message

URCL_X86_REGISTER_MAPPING: dict[urcl.types.GeneralRegister, x86asm.Register] = {
    urcl.types.GeneralRegister(1): x86asm.Register.EAX,
    urcl.types.GeneralRegister(2): x86asm.Register.EBX,
    urcl.types.GeneralRegister(3): x86asm.Register.ECX,
    urcl.types.GeneralRegister(4): x86asm.Register.EDX,
    urcl.types.GeneralRegister(5): x86asm.Register.EBP,
    urcl.types.GeneralRegister(6): x86asm.Register.ESP
}

def get_destination_register(instruction: urcl.InstructionCSTNode) -> urcl.types.GeneralRegister | None:

    if not instruction.operands:
        return None
    urcl_destination_register = instruction.operands[0].value
    if not isinstance(urcl_destination_register, urcl.types.GeneralRegister):
        return None
    
    return urcl_destination_register

def get_x86_destination_register(instruction: urcl.InstructionCSTNode) -> x86asm.Register | None:

    urcl_destination_register = get_destination_register(instruction)
    if not urcl_destination_register:
        return None
    x86_destination_register = URCL_X86_REGISTER_MAPPING.get(urcl_destination_register)
    if not x86_destination_register:
        return None
    
    return x86_destination_register

def get_jump_target(instruction: urcl.InstructionCSTNode) -> urcl.types.Label | None:

    if not instruction.operands:
        return None
    urcl_destination = instruction.operands[0].value
    if not isinstance(urcl_destination, urcl.types.Label):
        return None
    
    return urcl_destination

def urcl_operand_to_x86(operand: urcl.urclcst.OperandCSTNode) -> "x86asm.Operand | None":

    if isinstance(operand.value, urcl.urclcst.Label):
        return x86asm.Operand(x86asm.Label(operand.value.name))
    elif isinstance(operand.value, urcl.urclcst.GeneralRegister):
        register = URCL_X86_REGISTER_MAPPING.get(operand.value)
        if register:
            return x86asm.Operand(register)
    elif isinstance(operand.value, int):
        return x86asm.Operand(operand.value)
    elif isinstance(operand.value, urcl.urclcst.RelativeAddress):
        return x86asm.Operand(operand.value.offset)
    elif isinstance(operand.value, urcl.urclcst.Character):
        return x86asm.Operand(ord(operand.value.char))
    elif isinstance(operand.value, urcl.types.Port):
        return x86asm.Operand(operand.value.value.id)
    else:
        return None

# The rather frightening code below does the majority of
# the work in translating urcl to x86 assembly. Don't like elif chains? Too bad!
# TODO: use ast instead of cst for compilation
def urcl_instruction_to_x86_assembly(instruction: urcl.urclcst.InstructionCSTNode):
    
        x86_code = x86asm.Program(0, [])
        if instruction.mnemonic in [urcl.Mnemonic.HLT, urcl.Mnemonic.NOP, urcl.Mnemonic.RET]:
            if len(instruction.operands) != 0:
                return Traceback([Message(f"Incorrect number of operands supplied to {instruction.mnemonic.value.upper()} instruction - found {len(instruction.operands)}, expected 0.", instruction.line_number, instruction.column_number)], [])
            if instruction.mnemonic == urcl.Mnemonic.HLT:
                x86_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EAX, 1])
                x86_code.add_instruction(x86asm.Mnemonic.INT, [0x80])
            elif instruction.mnemonic == urcl.Mnemonic.NOP:
                x86_code.add_instruction(x86asm.Mnemonic.NOP, [])
            elif instruction.mnemonic == urcl.Mnemonic.RET:
                x86_code.add_instruction(x86asm.Mnemonic.RETN, [])
            else:
                return Traceback([Message(f"No x86 translation for for URCL instruction {instruction.mnemonic.name}", instruction.line_number, instruction.column_number)], [])
         
        elif instruction.mnemonic in urcl.TWO_OPERAND_ARITHMETIC_MNEMONICS:
            if not instruction.operands or len(instruction.operands) > 2:
                return Traceback([Message(f"Incorrect number of operands supplied to {instruction.mnemonic.value.upper()} instruction - found {len(instruction.operands)}, expected 2.", instruction.line_number, instruction.column_number)], [])
            destination = get_x86_destination_register(instruction)
            if not destination:
                return Traceback([Message(f"{instruction.mnemonic.value.upper()} instruction received incorrect operand type (expected register).", instruction.line_number, instruction.column_number)], [])
            urcl_source_operand = instruction.operands[len(instruction.operands) - 1]
            x86_source_operand = urcl_operand_to_x86(urcl_source_operand)
            if x86_source_operand is None:
                return Traceback([Message("Invalid source operand", urcl_source_operand.line_number, urcl_source_operand.column_number)], [])
            if instruction.operands[0] != urcl_source_operand:
                x86_code.add_instruction(x86asm.Mnemonic.MOV, [destination, x86_source_operand.value])
            if instruction.mnemonic == urcl.Mnemonic.MOV:
                pass
            elif instruction.mnemonic == urcl.Mnemonic.INC:
                x86_code.add_instruction(x86asm.Mnemonic.INC, [destination])
            elif instruction.mnemonic == urcl.Mnemonic.DEC:
                x86_code.add_instruction(x86asm.Mnemonic.DEC, [destination])
            elif instruction.mnemonic == urcl.Mnemonic.NEG:
                x86_code.add_instruction(x86asm.Mnemonic.NEG, [destination])
            elif instruction.mnemonic == urcl.Mnemonic.LSH:
                x86_code.add_instruction(x86asm.Mnemonic.ROL, [destination])
                x86_code.add_instruction(x86asm.Mnemonic.AND, [destination, (2**31 - 1) << 1])
            elif instruction.mnemonic == urcl.Mnemonic.RSH:
                x86_code.add_instruction(x86asm.Mnemonic.ROL, [destination])
                x86_code.add_instruction(x86asm.Mnemonic.AND, [destination, 2**31])
            else:
                return Traceback([Message(f"No x86 translation for for URCL instruction {instruction.mnemonic.name}", instruction.line_number, instruction.column_number)], [])
        
        elif instruction.mnemonic in [urcl.Mnemonic.ADD, urcl.Mnemonic.SUB, urcl.Mnemonic.XOR, urcl.Mnemonic.OR]:
            if len(instruction.operands) != 3:
                return Traceback([Message(f"Incorrect number of operands supplied to {instruction.mnemonic.value.upper()} instruction - found {len(instruction.operands)}, expected 3.", instruction.line_number, instruction.column_number)], [])
            destination = get_x86_destination_register(instruction)
            if not destination:
                return Traceback([Message(f"{instruction.mnemonic.value.upper()} instruction received incorrect destination type (expected register).", instruction.line_number, instruction.column_number)], [])
            source_1 = urcl_operand_to_x86(instruction.operands[1])
            source_2 = urcl_operand_to_x86(instruction.operands[2])
            if source_1 is None:
                return None
            if source_2 is None:
                return None
            if instruction.operands[0] != instruction.operands[1]:
                x86_code.add_instruction(x86asm.Mnemonic.MOV, [destination, source_1.value])
            arithmetic_mapping: dict[urcl.Mnemonic, x86asm.Mnemonic] = {
                urcl.Mnemonic.ADD: x86asm.Mnemonic.ADD,
                urcl.Mnemonic.SUB: x86asm.Mnemonic.SUB,
                urcl.Mnemonic.XOR: x86asm.Mnemonic.XOR,
            }
            x86_mnemonic = arithmetic_mapping.get(instruction.mnemonic)
            if x86_mnemonic:
                x86_code.add_instruction(x86_mnemonic, [destination, source_2.value])
            else:
                return Traceback([Message(f"No x86 translation for for URCL instruction {instruction.mnemonic.name.upper()}", instruction.line_number, instruction.column_number)], [])
        
        elif instruction.mnemonic in [urcl.Mnemonic.JMP, urcl.Mnemonic.CAL]:
            destination_operand = get_jump_target(instruction)
            if len(instruction.operands) != 1:
                return Traceback([Message(f"Incorrect number of operands supplied to {instruction.mnemonic.name.upper()} instruction - found {len(instruction.operands)}, expected 1.", instruction.line_number, instruction.column_number)], [])
            if isinstance(destination_operand, urcl.urclcst.Label):
                if instruction.mnemonic == urcl.Mnemonic.JMP:
                    x86_code.add_instruction(x86asm.Mnemonic.JMP, [x86asm.Label(destination_operand.name)])
                elif instruction.mnemonic == urcl.Mnemonic.CAL:
                    x86_code.add_instruction(x86asm.Mnemonic.CALL, [x86asm.Label(destination_operand.name)])
                else:
                    return Traceback([Message(f"No x86 translation for for URCL instruction {instruction.mnemonic.name.upper()}", instruction.line_number, instruction.column_number)], [])
            else:
                return Traceback([Message(f"JMP instruction operand 1 is of incorrect type (expected Label).", instruction.line_number, instruction.column_number)], [])
        
        elif instruction.mnemonic in urcl.TWO_OPERAND_CONDITION_JUMP_MNEMONICS:
            destination_operand = get_jump_target(instruction)
            if not isinstance(destination_operand, urcl.urclcst.Label):
                return Traceback([Message(f"{instruction.mnemonic.name} instruction operand 1 is of incorrect type (expected label).", instruction.line_number, instruction.column_number)], [])
            if len(instruction.operands) != 2:
                return Traceback([Message(f"Incorrect number of operands supplied to {instruction.mnemonic.name} instruction - found {len(instruction.operands)}, expected 2.", instruction.line_number, instruction.column_number)], [])
            x86_source_operand = urcl_operand_to_x86(instruction.operands[1])
            if x86_source_operand is None:
                return None
            x86_code.add_instruction(x86asm.Mnemonic.CMP, [x86_source_operand.value, 0])
            if not isinstance(destination_operand, urcl.urclcst.Label):
                return None
            if instruction.mnemonic == urcl.Mnemonic.BNZ:
                x86_code.add_instruction(x86asm.Mnemonic.JNZ, [x86asm.Label(destination_operand.name)])
            elif instruction.mnemonic == urcl.Mnemonic.BRZ:
                x86_code.add_instruction(x86asm.Mnemonic.JZ, [x86asm.Label(destination_operand.name)])
            elif instruction.mnemonic == urcl.Mnemonic.BRP:
                x86_code.add_instruction(x86asm.Mnemonic.JGE, [x86asm.Label(destination_operand.name)])
            else:
                return Traceback([Message(f"No x86 translation for for URCL instruction {instruction.mnemonic.name.upper()}", instruction.line_number, instruction.column_number)], [])
        
        elif instruction.mnemonic in urcl.THREE_OPERAND_CONDITION_JUMP_MNEMONICS:
            destination_operand = get_jump_target(instruction)
            if not isinstance(destination_operand, urcl.urclcst.Label):
                return Traceback([Message(f"{instruction.mnemonic.name} instruction operand 1 '{destination_operand}' is of incorrect type (expected label).", instruction.line_number, instruction.column_number)], [])
            if len(instruction.operands) != 3:
                return Traceback([Message(f"Incorrect number of operands supplied to {instruction.mnemonic.name} instruction - found {len(instruction.operands)}, expected 3.", instruction.line_number, instruction.column_number)], [])
            x86_source_operand_1 = urcl_operand_to_x86(instruction.operands[1])
            x86_source_operand_2 = urcl_operand_to_x86(instruction.operands[2])
            if x86_source_operand_1 is None:
                return None
            if x86_source_operand_2 is None:
                return None
            x86_code.add_instruction(x86asm.Mnemonic.CMP, [x86_source_operand_1.value, x86_source_operand_2.value])
            if not isinstance(destination_operand, urcl.urclcst.Label):
                return None
            if instruction.mnemonic == urcl.Mnemonic.BLE:
                x86_code.add_instruction(x86asm.Mnemonic.JBE, [x86asm.Label(destination_operand.name)])
            elif instruction.mnemonic == urcl.Mnemonic.BGE:
                x86_code.add_instruction(x86asm.Mnemonic.JGE, [x86asm.Label(destination_operand.name)])
            elif instruction.mnemonic == urcl.Mnemonic.BRE:
                x86_code.add_instruction(x86asm.Mnemonic.JZ, [x86asm.Label(destination_operand.name)])
            elif instruction.mnemonic == urcl.Mnemonic.BNE:
                x86_code.add_instruction(x86asm.Mnemonic.JNZ, [x86asm.Label(destination_operand.name)])
            else:
                return Traceback([Message(f"No x86 translation for for URCL instruction {instruction.mnemonic.name.upper()}", instruction.line_number, instruction.column_number)], [])
        
        elif instruction.mnemonic == urcl.Mnemonic.OUT:
            if len(instruction.operands) != 2:
                return Traceback([Message(f"Incorrect number of operands supplied to OUT instruction - found {len(instruction.operands)}, expected 2.", instruction.line_number, instruction.column_number)], [])
            if isinstance(instruction.operands[0].value, urcl.types.Port):
                port = instruction.operands[0].value
            elif isinstance(instruction.operands[0].value, int):
                port = urcl.types.Port.from_value(instruction.operands[0].value)
            else:
                port = None
            if port is None:
                return Traceback([Message(f"OUT instruction operand 1 '{instruction.operands[0]}' is not a valid port", instruction.line_number, instruction.column_number)], [])
           
            # URCL standard requires ascii encoding but we use utf-8 instead
            # don't tell ModPunchTree
            if isinstance(instruction.operands[1].value, int):
                output_string = list(chr(instruction.operands[1].value).encode("utf-8"))
            elif isinstance(instruction.operands[1].value, str):
                output_string = list(instruction.operands[1].value.encode("utf-8"))
            elif isinstance(instruction.operands[1].value, urcl.types.Character):
                output_string = list(instruction.operands[1].value.char.encode("utf-8"))
            elif isinstance(instruction.operands[1].value, urcl.types.GeneralRegister):
                output_string = instruction.operands[1].value
            else:
                return Traceback([Message(f"OUT instruction operand 2 '{instruction.operands[1]}' cannot be output onto a port.", instruction.line_number, instruction.column_number)], [])
            
            x86_code.add_instructions_to_save_general_registers()

            if isinstance(output_string, urcl.types.GeneralRegister):
                string_length_bytes = 4
                x86_code.add_instruction(x86asm.Mnemonic.PUSH, [URCL_X86_REGISTER_MAPPING[output_string]])
            else:
                output_string = list(output_string.__reversed__())
                uint32_count = math.ceil(len(output_string) / 4)
                string_length_bytes = uint32_count * 4
                uint32_index = 0
                while uint32_index < uint32_count:
                    hh = 0
                    for char_index, char in enumerate(output_string[uint32_index*4:uint32_index*4+4]):
                        hh += char << (24 - (8 * char_index))
                    x86_code.add_instruction(x86asm.Mnemonic.PUSH, [hh])
                    uint32_index += 1
            
            x86_code.add_fwrite_linux_syscall(x86asm.Register.ESP, string_length_bytes, 1)
            x86_code.add_instruction(x86asm.Mnemonic.ADD, [x86asm.Register.ESP, string_length_bytes])
            x86_code.add_instructions_to_restore_general_registers()
            
        elif instruction.mnemonic in [urcl.Mnemonic.PSH]:
            if len(instruction.operands) != 1:
                return Traceback([Message(f"Incorrect number of operands supplied to {instruction.mnemonic.value.upper()} instruction - found {len(instruction.operands)}, expected 1.", instruction.line_number, instruction.column_number)], [])
            x86_source_operand = urcl_operand_to_x86(instruction.operands[0])
            if x86_source_operand is None:
                return None
            x86_code.add_instruction(x86asm.Mnemonic.PUSH, [x86_source_operand.value])
        
        elif instruction.mnemonic in [urcl.Mnemonic.POP]:
            if len(instruction.operands) != 1:
                return Traceback([Message(f"Incorrect number of operands supplied to {instruction.mnemonic.value.upper()} instruction - found {len(instruction.operands)}, expected 1.", instruction.line_number, instruction.column_number)], [])
            x86_register = get_x86_destination_register(instruction)
            if x86_register is None:
                return None
            x86_code.add_instruction(x86asm.Mnemonic.POP, [x86_register])
            
        elif instruction.mnemonic in [urcl.Mnemonic.DIV, urcl.Mnemonic.MOD]:
            if len(instruction.operands) != 3:
                return Traceback([Message(f"Incorrect number of operands supplied to {instruction.mnemonic.value.upper()} instruction - found {len(instruction.operands)}, expected 3.", instruction.line_number, instruction.column_number)], [])
            destination = get_x86_destination_register(instruction)
            if not destination:
                return Traceback([Message(f"{instruction.mnemonic.value.upper()} instruction received incorrect destination type (expected register).", instruction.line_number, instruction.column_number)], [])
            source_1 = urcl_operand_to_x86(instruction.operands[1])
            source_2 = urcl_operand_to_x86(instruction.operands[2])
            if source_1 is None:
                return None
            if source_2 is None:
                return None
            temp_regs: list[x86asm.Register] = []
            for reg in [x86asm.Register.EAX, x86asm.Register.EBX, x86asm.Register.EDX]:
                if reg != destination:
                    x86_code.add_instruction(x86asm.Mnemonic.PUSH, [reg])
                    temp_regs.append(reg)
            x86_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EAX, source_1.value])
            x86_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EDX, 0])
            x86_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EBX, source_2.value])
            x86_code.add_instruction(x86asm.Mnemonic.DIV, [x86asm.Register.EBX])
            if instruction.mnemonic == urcl.Mnemonic.DIV:
                x86_code.add_instruction(x86asm.Mnemonic.MOV, [destination, x86asm.Register.EAX])
            else:
                x86_code.add_instruction(x86asm.Mnemonic.MOV, [destination, x86asm.Register.EDX])
            for reg in temp_regs.__reversed__():
                x86_code.add_instruction(x86asm.Mnemonic.POP, [reg])
        else:
            return Traceback([Message(f"No x86 translation for for URCL instruction {instruction.mnemonic.name}", instruction.line_number, instruction.column_number)], [])
    
        return x86_code

#TODO: fix spagetti
def compile_urcl_source_to_flat_binary(source: str, entry_point: int, stack_base_pointer: int) -> "Traceback | bytes":

    parsed_urcl = urcl.CST.parse_str(source)
    if not isinstance(parsed_urcl, urcl.CST):
        error = parsed_urcl
        error.elaborate("Could not parse urcl source", 1, 1)
        return error
    x86_assembly_code = x86asm.Program(entry_point, [])
    x86_assembly_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EBX, 0]) # Default return code
    x86_assembly_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EBP, stack_base_pointer]) # Setting up stack
    x86_assembly_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.ESP, stack_base_pointer]) # Setting up stack
    
    for instruction in parsed_urcl.top_level_declerations:
        if isinstance(instruction, urcl.urclcst.Label):
            x86_assembly_code.code.append(x86asm.Label(instruction.name))
            continue
        x86_instruction = urcl_instruction_to_x86_assembly(instruction)
        if x86_instruction is None:
            return Traceback([Message("Instruction could not be compiled", instruction.line_number, instruction.column_number)], [])
        if isinstance(x86_instruction, Traceback):
            x86_instruction.elaborate("Instruction could not be compiled")
            return x86_instruction
        for x86_instruction in x86_instruction.code:
            if isinstance(x86_instruction, x86asm.Label):
                continue
            x86_assembly_code.add_instruction(x86_instruction.mnemonic, [op.value for op in x86_instruction.operands], x86_instruction.addressing_mode)

        
    assembled_x86 = x86_assembly_code.assemble()
    if isinstance(assembled_x86, Traceback):
        error = assembled_x86
        error.elaborate("Unable to generate x86 assembly")
        return error
    machine_code = bytes()
    for instruction in assembled_x86:
        machine_code += bytes(instruction)
    
    return machine_code

def compile_urcl_to_executable(source: str, stack_size=512, small_filesize=False):
    
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