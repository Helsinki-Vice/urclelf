import urcl
import x86asm
import elf
from error import Traceback, Message

URCL_X86_REGISTER_MAPPING: "list[x86asm.Register | None]" = [
    None,
    x86asm.Register.EAX,
    x86asm.Register.EBX,
    x86asm.Register.ECX,
    x86asm.Register.EDX,
    x86asm.Register.EBP,
    x86asm.Register.ESP,
]

def get_destination_register(instruction: urcl.Instruction):

    urcl_destination_register = instruction.get_destination_register()
    if not urcl_destination_register:
        return None
    x86_destination_register = URCL_X86_REGISTER_MAPPING[urcl_destination_register.index]
    if not x86_destination_register:
        return None
    
    return x86_destination_register

def urcl_operand_to_x86(operand: urcl.Operand) -> "x86asm.Operand | None":

    if isinstance(operand, urcl.Label):
        return x86asm.Operand(x86asm.Label(operand.name))
    elif isinstance(operand, urcl.GeneralRegister):
        try:
            register = URCL_X86_REGISTER_MAPPING[operand.index]
        except ValueError:
            return None
        if register:
            return x86asm.Operand(register)
    elif isinstance(operand, int):
        return x86asm.Operand(operand)
    elif isinstance(operand, urcl.RelativeAddress):
        return x86asm.Operand(operand.offset)
    elif isinstance(operand, urcl.Character):
        return x86asm.Operand(ord(operand.char))
    elif isinstance(operand, urcl.Port):
        return x86asm.Operand(operand.value.id)
    else:
        return None

#TODO: fix spagetti
def compile_urcl_source_to_flat_binary(source: str, entry_point: int, stack_base_pointer: int) -> "Traceback | bytes":

    parsed_urcl = urcl.Program.parse_str(source)
    if not isinstance(parsed_urcl, urcl.Program):
        error = parsed_urcl
        error.push(Message("Could not parse urcl source", 1, 1))
        return error
    x86_assembly_code = x86asm.Program(entry_point, [])
    x86_assembly_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EBX, 0]) # Default return code
    x86_assembly_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EBP, stack_base_pointer]) # Setting up stack
    x86_assembly_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.ESP, stack_base_pointer]) # Setting up stack
    for instruction in parsed_urcl.code:

        if isinstance(instruction, urcl.Label):
            x86_assembly_code.code.append(x86asm.Label(instruction.name))
            continue

        if instruction.mnemonic in [urcl.Mnemonic.HLT, urcl.Mnemonic.NOP, urcl.Mnemonic.RET]:
            if len(instruction.operands) != 0:
                return Traceback([Message(f"Incorrect number of operands supplied to {instruction.mnemonic.value.upper()} instruction - found {len(instruction.operands)}, expected 0.", 0, 0)], [])
            if instruction.mnemonic == urcl.Mnemonic.HLT:
                x86_assembly_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EAX, 1])
                x86_assembly_code.add_instruction(x86asm.Mnemonic.INT, [0x80])
            elif instruction.mnemonic == urcl.Mnemonic.NOP:
                x86_assembly_code.add_instruction(x86asm.Mnemonic.NOP, [])
            elif instruction.mnemonic == urcl.Mnemonic.RET:
                x86_assembly_code.add_instruction(x86asm.Mnemonic.RETN, [])
            else:
                return Traceback([Message(f"No x86 translation for for URCL instruction {instruction.mnemonic.name}", 0, 0)], [])
         
        elif instruction.mnemonic in [urcl.Mnemonic.MOV, urcl.Mnemonic.INC, urcl.Mnemonic.DEC, urcl.Mnemonic.NEG]:
            if len(instruction.operands) != 2:
                return Traceback([Message(f"Incorrect number of operands supplied to {instruction.mnemonic.value.upper()} instruction - found {len(instruction.operands)}, expected 1.", 0, 0)], [])
            destination = get_destination_register(instruction)
            if not destination:
                return Traceback([Message(f"{instruction.mnemonic.value.upper()} instruction received incorrect operand type (expected register).", 0, 0)], [])
            source_operand = urcl_operand_to_x86(instruction.operands[1])
            if source_operand is None:
                continue
            if instruction.operands[0] != instruction.operands[1]:
                x86_assembly_code.add_instruction(x86asm.Mnemonic.MOV, [destination, source_operand.value])
            if instruction.mnemonic == urcl.Mnemonic.MOV:
                pass
            elif instruction.mnemonic == urcl.Mnemonic.INC:
                x86_assembly_code.add_instruction(x86asm.Mnemonic.ADD, [destination, 1])
            elif instruction.mnemonic == urcl.Mnemonic.DEC:
                x86_assembly_code.add_instruction(x86asm.Mnemonic.SUB, [destination, 1])
            elif instruction.mnemonic == urcl.Mnemonic.NEG:
                x86_assembly_code.add_instruction(x86asm.Mnemonic.NEG, [destination])
            else:
                return Traceback([Message(f"No x86 translation for for URCL instruction {instruction.mnemonic.name}", 0, 0)], [])
        
        elif instruction.mnemonic in [urcl.Mnemonic.ADD, urcl.Mnemonic.SUB]:
            if len(instruction.operands) != 3:
                return Traceback([Message(f"Incorrect number of operands supplied to {instruction.mnemonic.value.upper()} instruction - found {len(instruction.operands)}, expected 3.", 0, 0)], [])
            destination = get_destination_register(instruction)
            if not destination:
                return Traceback([Message(f"{instruction.mnemonic.value.upper()} instruction received incorrect destination type (expected register).", 0, 0)], [])
            source_1 = urcl_operand_to_x86(instruction.operands[1])
            source_2 = urcl_operand_to_x86(instruction.operands[2])
            if source_1 is None:
                continue
            if source_2 is None:
                continue
            if instruction.operands[0] != instruction.operands[1]:
                x86_assembly_code.add_instruction(x86asm.Mnemonic.MOV, [destination, source_1.value])
            if instruction.mnemonic == urcl.Mnemonic.ADD:
                x86_assembly_code.add_instruction(x86asm.Mnemonic.ADD, [destination, source_2.value])
            elif instruction.mnemonic == urcl.Mnemonic.SUB:
                x86_assembly_code.add_instruction(x86asm.Mnemonic.SUB, [destination, source_2.value])
            else:
                return Traceback([Message(f"No x86 translation for for URCL instruction {instruction.mnemonic.name.upper()}", 0, 0)], [])
        
        elif instruction.mnemonic in [urcl.Mnemonic.JMP, urcl.Mnemonic.CAL]:
            destination_operand = instruction.get_jump_target()
            if len(instruction.operands) != 1:
                return Traceback([Message(f"Incorrect number of operands supplied to {instruction.mnemonic.name.upper()} instruction - found {len(instruction.operands)}, expected 1.", 0, 0)], [])
            if isinstance(destination_operand, urcl.Label):
                if instruction.mnemonic == urcl.Mnemonic.JMP:
                    x86_assembly_code.add_instruction(x86asm.Mnemonic.JMP, [x86asm.Label(destination_operand.name)])
                elif instruction.mnemonic == urcl.Mnemonic.CAL:
                    x86_assembly_code.add_instruction(x86asm.Mnemonic.CALL, [x86asm.Label(destination_operand.name)])
                else:
                    return Traceback([Message(f"No x86 translation for for URCL instruction {instruction.mnemonic.name.upper()}", 0, 0)], [])
            else:
                return Traceback([Message(f"JMP instruction operand 1 is of incorrect type (expected Label).", 0, 0)], [])
        
        elif instruction.mnemonic in [urcl.Mnemonic.BNZ, urcl.Mnemonic.BRZ, urcl.Mnemonic.BRP]:
            destination_operand = instruction.get_jump_target()
            if not isinstance(destination_operand, urcl.Label):
                return Traceback([Message(f"JNZ instruction operand 1 is of incorrect type (expected label).", 0, 0)], [])
            if len(instruction.operands) != 2:
                return Traceback([Message(f"Incorrect number of operands supplied to JNZ instruction - found {len(instruction.operands)}, expected 2.", 0, 0)], [])
            source_operand = urcl_operand_to_x86(instruction.operands[1])
            if not source_operand is not None:
                continue
            x86_assembly_code.add_instruction(x86asm.Mnemonic.CMP, [source_operand.value, 0])
            if isinstance(destination_operand, urcl.Label):
                if instruction.mnemonic == urcl.Mnemonic.BNZ:
                    x86_assembly_code.add_instruction(x86asm.Mnemonic.JNZ, [x86asm.Label(destination_operand.name)])
                elif instruction.mnemonic == urcl.Mnemonic.BRZ:
                    x86_assembly_code.add_instruction(x86asm.Mnemonic.JZ, [x86asm.Label(destination_operand.name)])
                elif instruction.mnemonic == urcl.Mnemonic.BRP:
                    x86_assembly_code.add_instruction(x86asm.Mnemonic.JGE, [x86asm.Label(destination_operand.name)])
                else:
                    return Traceback([Message(f"No x86 translation for for URCL instruction {instruction.mnemonic.name.upper()}", 0, 0)], [])
        #TODO: smaller translations
        elif instruction.mnemonic == urcl.Mnemonic.OUT:
            if len(instruction.operands) != 2:
                return Traceback([Message(f"Incorrect number of operands supplied to OUT instruction - found {len(instruction.operands)}, expected 2.", 0, 0)], [])
            if isinstance(instruction.operands[0], urcl.Port):
                port = instruction.operands[0]
            if not isinstance(instruction.operands[0], int):
                port = urcl.Port(instruction.operands[0])
            else:
                port = None
            if port is None:
                return Traceback([Message(f"OUT instruction operand 1 '{instruction.operands[0]}' is not a valid port", 0, 0)], [])
            source_operand = urcl_operand_to_x86(instruction.operands[1])
            if not source_operand:
                continue
            #if not isinstance(instruction.operands[1], int):
            #    return Traceback([Message(f"OUT instruction operand 2 is of incorrect type (expected int).", 0, 0)], [])
            x86_assembly_code.add_instruction(x86asm.Mnemonic.PUSH, [x86asm.Register.EAX])
            x86_assembly_code.add_instruction(x86asm.Mnemonic.PUSH, [x86asm.Register.EBX])
            x86_assembly_code.add_instruction(x86asm.Mnemonic.PUSH, [x86asm.Register.ECX])
            x86_assembly_code.add_instruction(x86asm.Mnemonic.PUSH, [x86asm.Register.EDX])
            x86_assembly_code.add_instruction(x86asm.Mnemonic.PUSH, [source_operand.value])
            x86_assembly_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EAX, 4])
            x86_assembly_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EBX, 1])
            x86_assembly_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.ECX, x86asm.Register.ESP])
            x86_assembly_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EDX, 1])
            x86_assembly_code.add_instruction(x86asm.Mnemonic.INT, [0x80])
            x86_assembly_code.add_instruction(x86asm.Mnemonic.ADD, [x86asm.Register.ESP, 0x4])
            x86_assembly_code.add_instruction(x86asm.Mnemonic.POP, [x86asm.Register.EDX])
            x86_assembly_code.add_instruction(x86asm.Mnemonic.POP, [x86asm.Register.ECX])
            x86_assembly_code.add_instruction(x86asm.Mnemonic.POP, [x86asm.Register.EBX])
            x86_assembly_code.add_instruction(x86asm.Mnemonic.POP, [x86asm.Register.EAX])
            
        elif instruction.mnemonic in [urcl.Mnemonic.PSH]:
            if len(instruction.operands) != 1:
                return Traceback([Message(f"Incorrect number of operands supplied to {instruction.mnemonic.value.upper()} instruction - found {len(instruction.operands)}, expected 1.", 0, 0)], [])
            source_operand = urcl_operand_to_x86(instruction.operands[0])
            if source_operand is None:
                continue
            x86_assembly_code.add_instruction(x86asm.Mnemonic.PUSH, [source_operand.value])
        
        elif instruction.mnemonic in [urcl.Mnemonic.POP]:
            if len(instruction.operands) != 1:
                return Traceback([Message(f"Incorrect number of operands supplied to {instruction.mnemonic.value.upper()} instruction - found {len(instruction.operands)}, expected 1.", 0, 0)], [])
            urcl_register = instruction.get_destination_register()
            if not urcl_register:
                continue
            x86_register = urcl_operand_to_x86(urcl_register)
            if x86_register is None:
                continue
            x86_assembly_code.add_instruction(x86asm.Mnemonic.POP, [x86_register.value])
            
        elif instruction.mnemonic in [urcl.Mnemonic.DIV, urcl.Mnemonic.MOD]:
            if len(instruction.operands) != 3:
                return Traceback([Message(f"Incorrect number of operands supplied to {instruction.mnemonic.value.upper()} instruction - found {len(instruction.operands)}, expected 3.", 0, 0)], [])
            destination = get_destination_register(instruction)
            if not destination:
                return Traceback([Message(f"{instruction.mnemonic.value.upper()} instruction received incorrect destination type (expected register).", 0, 0)], [])
            source_1 = urcl_operand_to_x86(instruction.operands[1])
            source_2 = urcl_operand_to_x86(instruction.operands[2])
            if source_1 is None:
                continue
            if source_2 is None:
                continue
            temp_regs: list[x86asm.Register] = []
            for reg in [x86asm.Register.EAX, x86asm.Register.EBX, x86asm.Register.EDX]:
                if reg != destination:
                    x86_assembly_code.add_instruction(x86asm.Mnemonic.PUSH, [reg])
                    temp_regs.append(reg)
            x86_assembly_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EAX, source_1.value])
            x86_assembly_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EDX, 0])
            x86_assembly_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EBX, source_2.value])
            x86_assembly_code.add_instruction(x86asm.Mnemonic.DIV, [x86asm.Register.EBX])
            if instruction.mnemonic == urcl.Mnemonic.DIV:
                x86_assembly_code.add_instruction(x86asm.Mnemonic.MOV, [destination, x86asm.Register.EAX])
            else:
                x86_assembly_code.add_instruction(x86asm.Mnemonic.MOV, [destination, x86asm.Register.EDX])
            for reg in temp_regs.__reversed__():
                x86_assembly_code.add_instruction(x86asm.Mnemonic.POP, [reg])
        else:
            return Traceback([Message(f"No x86 translation for for URCL instruction {instruction.mnemonic.name}", 0, 0)], [])
    
    assembled_x86 = x86_assembly_code.assemble()
    if isinstance(assembled_x86, Traceback):
        error = assembled_x86
        error.push(Message("Unable to assemble x86 assembly", 0, 0))
        return error
    machine_code = bytes()
    for instruction in assembled_x86:
        machine_code += bytes(instruction)
    
    return machine_code

def compile_urcl_to_executable(source: str):
    
    first_pass_binary = compile_urcl_source_to_flat_binary(source, 0, 0)
    if isinstance(first_pass_binary, Traceback):
        error = first_pass_binary
        error.push(Message("Unable to assemble x86 assembly", 0, 0))
        return error
    first_pass_executable = elf.Program(first_pass_binary, 20)
    second_pass_binary = compile_urcl_source_to_flat_binary(source, first_pass_executable.entry_point, first_pass_executable.calculate_stack_base_address())
    if isinstance(second_pass_binary, Traceback):
        error = second_pass_binary
        error.push(Message("Unable to assemble x86 assembly (Unreachable error?!)", 0, 0))
        return error
    
    return bytes(elf.Program(second_pass_binary, 20).assemble())

def main():
    with open("./source.urcl", "r") as file:
        source = file.read()
    result = compile_urcl_to_executable(source)
    #result = bytes(elf.Program(b"").assemble())
    if not isinstance(result, bytes):
        print(f"compile failed:\n{result}")
        exit()
    with open("./run", "w+b") as file:
        print("compiled")
        file.write(result)

if __name__ == "__main__":
    main()