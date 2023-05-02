import urcl
import x86
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
    else:
        return None
    
#TODO: fix spagetti
def compile_urcl(source: str) -> "Traceback | bytes":

    result = urcl.Program.parse_str(source)
    if not isinstance(result, urcl.Program):
        result.push(Message("Could not parse urcl source", 1, 1))
        return result
    elf_program = elf.Program(bytes())
    x86_code = x86asm.Program([], elf_program.entry_point)
    x86_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EBX, 0]) # Default return code
    x86_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EBP, elf_program.virtual_address + 1000]) # Setting up stack
    x86_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.ESP, elf_program.virtual_address + 1000]) # Setting up stack
    for instruction in result.code:

        if isinstance(instruction, urcl.Label):
            x86_code.code.append(x86asm.Label(instruction.name))
            continue

        if instruction.mnemonic == urcl.Mnemonic.HLT:
            if len(instruction.operands) != 0:
                return Traceback([Message(f"Incorrect number of operands supplied to HLT instruction - found {len(instruction.operands)}, expected 0.", 0, 0)], [])
            x86_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EAX, 1])
            x86_code.add_instruction(x86asm.Mnemonic.INT, [0x80])
        
        elif instruction.mnemonic == urcl.Mnemonic.NOP:
            if len(instruction.operands) != 0:
                return Traceback([Message(f"Incorrect number of operands supplied to NOP instruction - found {len(instruction.operands)}, expected 0.", 0, 0)], [])
            x86_code.add_instruction(x86asm.Mnemonic.NOP, [], )
        
        elif instruction.mnemonic == urcl.Mnemonic.RET:
            if len(instruction.operands) != 0:
                return Traceback([Message(f"Incorrect number of operands supplied to RET instruction - found {len(instruction.operands)}, expected 0.", 0, 0)], [])
            x86_code.add_instruction(x86asm.Mnemonic.RETN, [], )
        
        elif instruction.mnemonic == urcl.Mnemonic.MOV:
            destination = get_destination_register(instruction)
            if not destination:
                continue
            if len(instruction.operands) != 2:
                return Traceback([Message(f"Incorrect number of operands supplied to MOV instruction - found {len(instruction.operands)}, expected 0.", 0, 0)], [])
            source_operand = urcl_operand_to_x86(instruction.operands[1])
            if source_operand is None:
                continue
            x86_code.add_instruction(x86asm.Mnemonic.MOV, [destination, source_operand.value])
        
        elif instruction.mnemonic in [urcl.Mnemonic.INC, urcl.Mnemonic.DEC]:
            if len(instruction.operands) != 2:
                return Traceback([Message(f"Incorrect number of operands supplied to {instruction.mnemonic.value.upper()} instruction - found {len(instruction.operands)}, expected 1.", 0, 0)], [])
            destination = get_destination_register(instruction)
            if not destination:
                return Traceback([Message(f"{instruction.mnemonic.value.upper()} instruction received incorrect operand type (expected register).", 0, 0)], [])
            source_operand = urcl_operand_to_x86(instruction.operands[1])
            if source_operand is None:
                continue
            if instruction.operands[0] != instruction.operands[1]:
                x86_code.add_instruction(x86asm.Mnemonic.MOV, [destination, source_operand.value])
            if instruction.mnemonic == urcl.Mnemonic.INC:
                x86_code.add_instruction(x86asm.Mnemonic.ADD, [destination, 1])
            elif instruction.mnemonic == urcl.Mnemonic.DEC:
                x86_code.add_instruction(x86asm.Mnemonic.SUB, [destination, 1])
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
                x86_code.add_instruction(x86asm.Mnemonic.MOV, [destination, source_1.value])
            if instruction.mnemonic == urcl.Mnemonic.ADD:
                x86_code.add_instruction(x86asm.Mnemonic.ADD, [destination, source_2.value])
            elif instruction.mnemonic == urcl.Mnemonic.SUB:
                x86_code.add_instruction(x86asm.Mnemonic.SUB, [destination, source_2.value])
            else:
                return Traceback([Message(f"No x86 translation for for URCL instruction {instruction.mnemonic.name}", 0, 0)], [])
        
        elif instruction.mnemonic == urcl.Mnemonic.JMP:
            destination_operand = instruction.get_jump_target()
            if len(instruction.operands) != 1:
                return Traceback([Message(f"Incorrect number of operands supplied to JMP instruction - found {len(instruction.operands)}, expected 1.", 0, 0)], [])
            if isinstance(destination_operand, urcl.Label):
                x86_code.add_instruction(x86asm.Mnemonic.JMP, [x86asm.Label(destination_operand.name)])
            else:
                return Traceback([Message(f"JMP instruction operand 1 is of incorrect type (expected Label).", 0, 0)], [])
        
        elif instruction.mnemonic == urcl.Mnemonic.CAL:
            destination_operand = instruction.get_jump_target()
            if len(instruction.operands) != 1:
                return Traceback([Message(f"Incorrect number of operands supplied to CAL instruction - found {len(instruction.operands)}, expected 1.", 0, 0)], [])
            if isinstance(destination_operand, urcl.Label):
                x86_code.add_instruction(x86asm.Mnemonic.CALL, [x86asm.Label(destination_operand.name)])
            else:
                print(type(destination_operand))
                return Traceback([Message(f"CAL instruction operand 1 is of incorrect type (expected Label).", 0, 0)], [])
        
        elif instruction.mnemonic == urcl.Mnemonic.BNZ:
            destination_operand = instruction.get_jump_target()
            if not isinstance(destination_operand, urcl.Label):
                return Traceback([Message(f"JNZ instruction operand 1 is of incorrect type (expected label).", 0, 0)], [])
            if len(instruction.operands) != 2:
                return Traceback([Message(f"Incorrect number of operands supplied to JNZ instruction - found {len(instruction.operands)}, expected 2.", 0, 0)], [])
            source_operand = urcl_operand_to_x86(instruction.operands[1])
            if not source_operand is not None:
                continue
            x86_code.add_instruction(x86asm.Mnemonic.CMP, [source_operand.value, 0])
            x86_code.add_instruction(x86asm.Mnemonic.JNZ, [x86asm.Label(destination_operand.name)])
        
        elif instruction.mnemonic == urcl.Mnemonic.OUT:
            if len(instruction.operands) != 2:
                return Traceback([Message(f"Incorrect number of operands supplied to OUT instruction - found {len(instruction.operands)}, expected 2.", 0, 0)], [])
            if instruction.operands[0] != 1:
                return Traceback([Message(f"OUT instruction operand 1 is of incorrect type (expected port 1).", 0, 0)], [])
            source_operand = urcl_operand_to_x86(instruction.operands[1])
            if not source_operand:
                continue
            #if not isinstance(instruction.operands[1], int):
            #    return Traceback([Message(f"OUT instruction operand 2 is of incorrect type (expected int).", 0, 0)], [])
            x86_code.add_instruction(x86asm.Mnemonic.PUSHAD, [])
            x86_code.add_instruction(x86asm.Mnemonic.PUSH, [source_operand.value])
            x86_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EAX, 4])
            x86_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EBX, 1])
            x86_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.ECX, x86asm.Register.ESP])
            x86_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EDX, 1])
            x86_code.add_instruction(x86asm.Mnemonic.INT, [0x80])
            x86_code.add_instruction(x86asm.Mnemonic.ADD, [x86asm.Register.ESP, 0x04])
            x86_code.add_instruction(x86asm.Mnemonic.POPAD, [])
            x86_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.ESP, x86asm.Register.EBP])
            
        else:
            return Traceback([Message(f"No x86 translation for for URCL instruction {instruction.mnemonic.name}", 0, 0)], [])
    
    for instruction in x86_code.code:
        print(instruction)
    result = x86_code.assemble()
    if isinstance(result, Traceback):
        result.push(Message("Unable to assemble x86 assembly", 0, 0))
        return result
    machine_code = bytes()
    for instruction in result:
        machine_code += bytes(instruction)
    print(machine_code.hex())
    elf_program.text = machine_code
    return bytes(elf_program.assemble())

def main():
    with open("./source.urcl", "r") as file:
        source = file.read()
    result = compile_urcl(source)
    #result = bytes(elf.Program(b"").assemble())
    if not isinstance(result, bytes):
        print(f"compile failed:\n{result}")
        exit()
    with open("./run", "w+b") as file:
        print("compiled")
        file.write(result)

if __name__ == "__main__":
    main()