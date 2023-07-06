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

#TODO: use ast instead of cst for compilation
def urcl_instruction_to_x86_assembly(instruction: urcl.urclcst.InstructionCSTNode):
    
        result = x86asm.Program(0, [])
        if instruction.mnemonic in [urcl.Mnemonic.HLT, urcl.Mnemonic.NOP, urcl.Mnemonic.RET]:
            if len(instruction.operands) != 0:
                return Traceback([Message(f"Incorrect number of operands supplied to {instruction.mnemonic.value.upper()} instruction - found {len(instruction.operands)}, expected 0.", 0, 0)], [])
            if instruction.mnemonic == urcl.Mnemonic.HLT:
                result.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EAX, 1])
                result.add_instruction(x86asm.Mnemonic.INT, [0x80])
            elif instruction.mnemonic == urcl.Mnemonic.NOP:
                result.add_instruction(x86asm.Mnemonic.NOP, [])
            elif instruction.mnemonic == urcl.Mnemonic.RET:
                result.add_instruction(x86asm.Mnemonic.RETN, [])
            else:
                return Traceback([Message(f"No x86 translation for for URCL instruction {instruction.mnemonic.name}", 0, 0)], [])
         
        elif instruction.mnemonic in urcl.TWO_OPERAND_ARITHMETIC_MNEMONICS:
            if not instruction.operands or len(instruction.operands) > 2:
                return Traceback([Message(f"Incorrect number of operands supplied to {instruction.mnemonic.value.upper()} instruction - found {len(instruction.operands)}, expected 2.", 0, 0)], [])
            destination = get_x86_destination_register(instruction)
            if not destination:
                return Traceback([Message(f"{instruction.mnemonic.value.upper()} instruction received incorrect operand type (expected register).", 0, 0)], [])
            urcl_source_operand = instruction.operands[len(instruction.operands) - 1]
            x86_source_operand = urcl_operand_to_x86(urcl_source_operand)
            if x86_source_operand is None:
                return Traceback([Message("Invalid source operand", urcl_source_operand.line_number, urcl_source_operand.column_number)], [])
            if instruction.operands[0] != urcl_source_operand:
                result.add_instruction(x86asm.Mnemonic.MOV, [destination, x86_source_operand.value])
            if instruction.mnemonic == urcl.Mnemonic.MOV:
                pass
            elif instruction.mnemonic == urcl.Mnemonic.INC:
                result.add_instruction(x86asm.Mnemonic.INC, [destination])
            elif instruction.mnemonic == urcl.Mnemonic.DEC:
                result.add_instruction(x86asm.Mnemonic.DEC, [destination])
            elif instruction.mnemonic == urcl.Mnemonic.NEG:
                result.add_instruction(x86asm.Mnemonic.NEG, [destination])
            elif instruction.mnemonic == urcl.Mnemonic.LSH:
                result.add_instruction(x86asm.Mnemonic.ROL, [destination])
                result.add_instruction(x86asm.Mnemonic.AND, [destination, (2**31 - 1) << 1])
            elif instruction.mnemonic == urcl.Mnemonic.RSH:
                result.add_instruction(x86asm.Mnemonic.ROL, [destination])
                result.add_instruction(x86asm.Mnemonic.AND, [destination, 2**31])
            else:
                return Traceback([Message(f"No x86 translation for for URCL instruction {instruction.mnemonic.name}", 0, 0)], [])
        
        elif instruction.mnemonic in [urcl.Mnemonic.ADD, urcl.Mnemonic.SUB, urcl.Mnemonic.XOR, urcl.Mnemonic.OR]:
            if len(instruction.operands) != 3:
                return Traceback([Message(f"Incorrect number of operands supplied to {instruction.mnemonic.value.upper()} instruction - found {len(instruction.operands)}, expected 3.", 0, 0)], [])
            destination = get_x86_destination_register(instruction)
            if not destination:
                return Traceback([Message(f"{instruction.mnemonic.value.upper()} instruction received incorrect destination type (expected register).", 0, 0)], [])
            source_1 = urcl_operand_to_x86(instruction.operands[1])
            source_2 = urcl_operand_to_x86(instruction.operands[2])
            if source_1 is None:
                return None
            if source_2 is None:
                return None
            if instruction.operands[0] != instruction.operands[1]:
                result.add_instruction(x86asm.Mnemonic.MOV, [destination, source_1.value])
            arithmetic_mapping: dict[urcl.Mnemonic, x86asm.Mnemonic] = {
                urcl.Mnemonic.ADD: x86asm.Mnemonic.ADD,
                urcl.Mnemonic.SUB: x86asm.Mnemonic.SUB,
                urcl.Mnemonic.XOR: x86asm.Mnemonic.XOR,
            }
            x86_mnemonic = arithmetic_mapping.get(instruction.mnemonic)
            if x86_mnemonic:
                result.add_instruction(x86_mnemonic, [destination, source_2.value])
            else:
                return Traceback([Message(f"No x86 translation for for URCL instruction {instruction.mnemonic.name.upper()}", 0, 0)], [])
        
        elif instruction.mnemonic in [urcl.Mnemonic.JMP, urcl.Mnemonic.CAL]:
            destination_operand = get_jump_target(instruction)
            if len(instruction.operands) != 1:
                return Traceback([Message(f"Incorrect number of operands supplied to {instruction.mnemonic.name.upper()} instruction - found {len(instruction.operands)}, expected 1.", 0, 0)], [])
            if isinstance(destination_operand, urcl.urclcst.Label):
                if instruction.mnemonic == urcl.Mnemonic.JMP:
                    result.add_instruction(x86asm.Mnemonic.JMP, [x86asm.Label(destination_operand.name)])
                elif instruction.mnemonic == urcl.Mnemonic.CAL:
                    result.add_instruction(x86asm.Mnemonic.CALL, [x86asm.Label(destination_operand.name)])
                else:
                    return Traceback([Message(f"No x86 translation for for URCL instruction {instruction.mnemonic.name.upper()}", 0, 0)], [])
            else:
                return Traceback([Message(f"JMP instruction operand 1 is of incorrect type (expected Label).", 0, 0)], [])
        
        elif instruction.mnemonic in urcl.TWO_OPERAND_CONDITION_JUMP_MNEMONICS:
            destination_operand = get_jump_target(instruction)
            if not isinstance(destination_operand, urcl.urclcst.Label):
                return Traceback([Message(f"{instruction.mnemonic.name} instruction operand 1 is of incorrect type (expected label).", 0, 0)], [])
            if len(instruction.operands) != 2:
                return Traceback([Message(f"Incorrect number of operands supplied to {instruction.mnemonic.name} instruction - found {len(instruction.operands)}, expected 2.", 0, 0)], [])
            x86_source_operand = urcl_operand_to_x86(instruction.operands[1])
            if x86_source_operand is None:
                return None
            result.add_instruction(x86asm.Mnemonic.CMP, [x86_source_operand.value, 0])
            if not isinstance(destination_operand, urcl.urclcst.Label):
                return None
            if instruction.mnemonic == urcl.Mnemonic.BNZ:
                result.add_instruction(x86asm.Mnemonic.JNZ, [x86asm.Label(destination_operand.name)])
            elif instruction.mnemonic == urcl.Mnemonic.BRZ:
                result.add_instruction(x86asm.Mnemonic.JZ, [x86asm.Label(destination_operand.name)])
            elif instruction.mnemonic == urcl.Mnemonic.BRP:
                result.add_instruction(x86asm.Mnemonic.JGE, [x86asm.Label(destination_operand.name)])
            else:
                return Traceback([Message(f"No x86 translation for for URCL instruction {instruction.mnemonic.name.upper()}", 0, 0)], [])
        
        elif instruction.mnemonic in urcl.THREE_OPERAND_CONDITION_JUMP_MNEMONICS:
            destination_operand = get_jump_target(instruction)
            if not isinstance(destination_operand, urcl.urclcst.Label):
                return Traceback([Message(f"{instruction.mnemonic.name} instruction operand 1 '{destination_operand}' is of incorrect type (expected label).", 0, 0)], [])
            if len(instruction.operands) != 3:
                return Traceback([Message(f"Incorrect number of operands supplied to {instruction.mnemonic.name} instruction - found {len(instruction.operands)}, expected 3.", 0, 0)], [])
            x86_source_operand_1 = urcl_operand_to_x86(instruction.operands[1])
            x86_source_operand_2 = urcl_operand_to_x86(instruction.operands[2])
            if x86_source_operand_1 is None:
                return None
            if x86_source_operand_2 is None:
                return None
            result.add_instruction(x86asm.Mnemonic.CMP, [x86_source_operand_1.value, x86_source_operand_2.value])
            if not isinstance(destination_operand, urcl.urclcst.Label):
                return None
            if instruction.mnemonic == urcl.Mnemonic.BLE:
                result.add_instruction(x86asm.Mnemonic.JBE, [x86asm.Label(destination_operand.name)])
            elif instruction.mnemonic == urcl.Mnemonic.BGE:
                result.add_instruction(x86asm.Mnemonic.JGE, [x86asm.Label(destination_operand.name)])
            elif instruction.mnemonic == urcl.Mnemonic.BRE:
                result.add_instruction(x86asm.Mnemonic.JZ, [x86asm.Label(destination_operand.name)])
            elif instruction.mnemonic == urcl.Mnemonic.BNE:
                result.add_instruction(x86asm.Mnemonic.JNZ, [x86asm.Label(destination_operand.name)])
            else:
                return Traceback([Message(f"No x86 translation for for URCL instruction {instruction.mnemonic.name.upper()}", 0, 0)], [])
        
        #TODO: smaller translations
        elif instruction.mnemonic == urcl.Mnemonic.OUT:
            if len(instruction.operands) != 2:
                return Traceback([Message(f"Incorrect number of operands supplied to OUT instruction - found {len(instruction.operands)}, expected 2.", 0, 0)], [])
            if isinstance(instruction.operands[0], urcl.urclcst.Port):
                port = instruction.operands[0]
            if not isinstance(instruction.operands[0], int):
                port = urcl.urclcst.Port(instruction.operands[0].value)
            else:
                port = None
            if port is None:
                return Traceback([Message(f"OUT instruction operand 1 '{instruction.operands[0]}' is not a valid port", 0, 0)], [])
            x86_source_operand = urcl_operand_to_x86(instruction.operands[1])
            if not x86_source_operand:
                return None
            #if not isinstance(instruction.operands[1], int):
            #    return Traceback([Message(f"OUT instruction operand 2 is of incorrect type (expected int).", 0, 0)], [])
            result.add_instruction(x86asm.Mnemonic.PUSH, [x86asm.Register.EAX])
            result.add_instruction(x86asm.Mnemonic.PUSH, [x86asm.Register.EBX])
            result.add_instruction(x86asm.Mnemonic.PUSH, [x86asm.Register.ECX])
            result.add_instruction(x86asm.Mnemonic.PUSH, [x86asm.Register.EDX])
            result.add_instruction(x86asm.Mnemonic.PUSH, [x86_source_operand.value])
            result.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EAX, 4])
            result.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EBX, 1])
            result.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.ECX, x86asm.Register.ESP])
            result.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EDX, 1])
            result.add_instruction(x86asm.Mnemonic.INT, [0x80])
            result.add_instruction(x86asm.Mnemonic.ADD, [x86asm.Register.ESP, 0x4])
            result.add_instruction(x86asm.Mnemonic.POP, [x86asm.Register.EDX])
            result.add_instruction(x86asm.Mnemonic.POP, [x86asm.Register.ECX])
            result.add_instruction(x86asm.Mnemonic.POP, [x86asm.Register.EBX])
            result.add_instruction(x86asm.Mnemonic.POP, [x86asm.Register.EAX])
            
        elif instruction.mnemonic in [urcl.Mnemonic.PSH]:
            if len(instruction.operands) != 1:
                return Traceback([Message(f"Incorrect number of operands supplied to {instruction.mnemonic.value.upper()} instruction - found {len(instruction.operands)}, expected 1.", 0, 0)], [])
            x86_source_operand = urcl_operand_to_x86(instruction.operands[0])
            if x86_source_operand is None:
                return None
            result.add_instruction(x86asm.Mnemonic.PUSH, [x86_source_operand.value])
        
        elif instruction.mnemonic in [urcl.Mnemonic.POP]:
            if len(instruction.operands) != 1:
                return Traceback([Message(f"Incorrect number of operands supplied to {instruction.mnemonic.value.upper()} instruction - found {len(instruction.operands)}, expected 1.", 0, 0)], [])
            x86_register = get_x86_destination_register(instruction)
            if x86_register is None:
                return None
            result.add_instruction(x86asm.Mnemonic.POP, [x86_register])
            
        elif instruction.mnemonic in [urcl.Mnemonic.DIV, urcl.Mnemonic.MOD]:
            if len(instruction.operands) != 3:
                return Traceback([Message(f"Incorrect number of operands supplied to {instruction.mnemonic.value.upper()} instruction - found {len(instruction.operands)}, expected 3.", 0, 0)], [])
            destination = get_x86_destination_register(instruction)
            if not destination:
                return Traceback([Message(f"{instruction.mnemonic.value.upper()} instruction received incorrect destination type (expected register).", 0, 0)], [])
            source_1 = urcl_operand_to_x86(instruction.operands[1])
            source_2 = urcl_operand_to_x86(instruction.operands[2])
            if source_1 is None:
                return None
            if source_2 is None:
                return None
            temp_regs: list[x86asm.Register] = []
            for reg in [x86asm.Register.EAX, x86asm.Register.EBX, x86asm.Register.EDX]:
                if reg != destination:
                    result.add_instruction(x86asm.Mnemonic.PUSH, [reg])
                    temp_regs.append(reg)
            result.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EAX, source_1.value])
            result.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EDX, 0])
            result.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EBX, source_2.value])
            result.add_instruction(x86asm.Mnemonic.DIV, [x86asm.Register.EBX])
            if instruction.mnemonic == urcl.Mnemonic.DIV:
                result.add_instruction(x86asm.Mnemonic.MOV, [destination, x86asm.Register.EAX])
            else:
                result.add_instruction(x86asm.Mnemonic.MOV, [destination, x86asm.Register.EDX])
            for reg in temp_regs.__reversed__():
                result.add_instruction(x86asm.Mnemonic.POP, [reg])
        else:
            return Traceback([Message(f"No x86 translation for for URCL instruction {instruction.mnemonic.name}", 0, 0)], [])
    
        return result

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
            return Traceback([Message("Instruction could not be compiled", 0, 0)], [])
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
        error.elaborate("Unable to assemble x86 assembly")
        return error
    machine_code = bytes()
    for instruction in assembled_x86:
        machine_code += bytes(instruction)
    
    return machine_code

def compile_urcl_to_executable(source: str, stack_size=512, small_filesize=False):
    
    first_pass_binary = compile_urcl_source_to_flat_binary(source, 0, 0)
    if isinstance(first_pass_binary, Traceback):
        error = first_pass_binary
        error.elaborate("Unable to assemble x86 assembly")
        return error
    first_pass_executable = elf.Program(first_pass_binary, stack_size, use_section_header_table=not small_filesize)
    second_pass_binary = compile_urcl_source_to_flat_binary(source, first_pass_executable.entry_point, first_pass_executable.calculate_stack_base_address() + first_pass_executable.stack_size)
    if isinstance(second_pass_binary, Traceback):
        error = second_pass_binary
        error.elaborate("Unable to assemble x86 assembly (Unreachable error?!)")
        return error
    #print(second_pass_binary.hex())

    return bytes(elf.Program(second_pass_binary, stack_size).assemble(use_section_header_table=not small_filesize))

def main():
    with open("./source.urcl", "r") as file:
        source = file.read()
    result = compile_urcl_to_executable(source, 512, True)
    #result = bytes(elf.Program(b"").assemble())
    if not isinstance(result, bytes):
        print(f"compile failed:\n{result}")
        exit()
    with open("./run", "w+b") as file:
        print("compiled")
        file.write(result)

if __name__ == "__main__":
    main()