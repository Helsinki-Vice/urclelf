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
    x86asm.Register.EDX
]

def get_destination_register(instruction: urcl.Instruction):

    urcl_destination_register = instruction.get_destination_register()
    if not urcl_destination_register:
        return None
    x86_destination_register = URCL_X86_REGISTER_MAPPING[urcl_destination_register.index]
    if not x86_destination_register:
        return None
    
    return x86_destination_register

def compile_urcl(source: str) -> "Traceback | bytes":

    result = urcl.Program.parse_str(source)
    if not isinstance(result, urcl.Program):
        result.push(Message("could not compile", 1, 1))
        return result
    label_addresses: dict[str, int] = {}
    elf_program = elf.Program(bytes())
    x86_code = x86asm.Program([], {}, elf_program.entry_point)
    x86_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EBX, 0])
    x86_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EBP, elf_program.virtual_address + 1000])
    x86_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.ESP, elf_program.virtual_address + 1000])
    for instruction in result.code:

        if isinstance(instruction, urcl.Label):
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
        
        elif instruction.mnemonic == urcl.Mnemonic.MOV:
            destination = get_destination_register(instruction)
            if not destination:
                continue
            source_operand = instruction.operands[1]
            if not isinstance(source_operand, int):
                return Traceback([Message(f"Register-to-register moves not yet supported.", 0, 0)], [])
            x86_code.add_instruction(x86asm.Mnemonic.MOV, [destination, source_operand])
        
        elif instruction.mnemonic == urcl.Mnemonic.INC:
            if len(instruction.operands) != 1:
                return Traceback([Message(f"Incorrect number of operands supplied to INC instruction - found {len(instruction.operands)}, expected 1.", 0, 0)], [])
            destination = get_destination_register(instruction)
            if not destination:
                return Traceback([Message(f"INC instruction received incorrect operand type (expected register).", 0, 0)], [])
            x86_code.add_instruction(x86asm.Mnemonic.ADD, [destination, 1])
        
        elif instruction.mnemonic == urcl.Mnemonic.ADD:
            if len(instruction.operands) != 3:
                return Traceback([Message(f"Incorrect number of operands supplied to ADD instruction - found {len(instruction.operands)}, expected 3.", 0, 0)], [])
            if instruction.operands[0] != instruction.operands[1]:
                return Traceback([Message(f"Only increments are supported currently: ({instruction.operands[0]} != {instruction.operands[1]})", 0, 0)], [])
            destination = get_destination_register(instruction)
            if not destination:
                return Traceback([Message(f"INC instruction received incorrect operand type (expected register).", 0, 0)], [])
            source_r = instruction.operands[2]
            if not destination:
                return Traceback([Message(f"INC instruction received incorrect operand type (expected register).", 0, 0)], [])
            if not isinstance(source_r, int):
                return Traceback([Message(f"Register-to-register moves not yet supported.", 0, 0)], [])
            x86_code.add_instruction(x86asm.Mnemonic.ADD, [destination, source_r])
        
        elif instruction.mnemonic == urcl.Mnemonic.DEC:
            if len(instruction.operands) != 1:
                return Traceback([Message(f"Incorrect number of operands supplied to DEC instruction - found {len(instruction.operands)}, expected 1.", 0, 0)], [])
            destination = get_destination_register(instruction)
            if not destination:
                continue
            x86_code.add_instruction(x86asm.Mnemonic.SUB, [destination, 1])
        
        elif instruction.mnemonic == urcl.Mnemonic.JMP:
            destination_operand = instruction.get_jump_target()
            if not isinstance(destination_operand, urcl.RelativeAddress):
                return Traceback([Message(f"JMP instruction operand 1 is of incorrect type (expected relative address).", 0, 0)], [])
            if len(instruction.operands) != 1:
                return Traceback([Message(f"Incorrect number of operands supplied to JMP instruction - found {len(instruction.operands)}, expected 1.", 0, 0)], [])
            x86_code.add_instruction(x86asm.Mnemonic.JNZ, [0])
            urcl_jump_offset = destination_operand.offset
            x86_jump_address = x86_code.instruction_addresses[len(x86_code.code) - 2 + urcl_jump_offset]
            x86_jump_offset = x86_jump_address - (x86_code.instruction_addresses[-1] + x86_code.instruction_sizes[-1])
            x86_code.code[-1].operands[0] = x86asm.Operand(x86_jump_offset)
        
        elif instruction.mnemonic == urcl.Mnemonic.BNZ:
            destination_operand = instruction.get_jump_target()
            if not isinstance(destination_operand, urcl.RelativeAddress):
                return Traceback([Message(f"JNZ instruction operand 1 is of incorrect type (expected relative address).", 0, 0)], [])
            if len(instruction.operands) != 2:
                return Traceback([Message(f"Incorrect number of operands supplied to JNZ instruction - found {len(instruction.operands)}, expected 2.", 0, 0)], [])
            source_operand = instruction.operands[1]
            if not isinstance(source_operand, urcl.GeneralRegister):
                return Traceback([Message(f"JNZ instruction operand 2 is of incorrect type (expected register).", 0, 0)], [])
            source_register = URCL_X86_REGISTER_MAPPING[source_operand.index]
            if not source_register:
                continue
            x86_code.add_instruction(x86asm.Mnemonic.CMP, [source_register, 0])
            x86_code.add_instruction(x86asm.Mnemonic.JNZ, [0])
            urcl_jump_offset = destination_operand.offset
            x86_jump_address = x86_code.instruction_addresses[len(x86_code.code) - 2 + urcl_jump_offset]
            x86_jump_offset = x86_jump_address - (x86_code.instruction_addresses[-1] + x86_code.instruction_sizes[-1])
            x86_code.code[-1].operands[0] = x86asm.Operand(x86_jump_offset)
            print(555)
            [print(c) for c in x86_code.code]
        elif instruction.mnemonic == urcl.Mnemonic.OUT:
            if len(instruction.operands) != 2:
                return Traceback([Message(f"Incorrect number of operands supplied to OUT instruction - found {len(instruction.operands)}, expected 2.", 0, 0)], [])
            if instruction.operands[0] != 1:
                return Traceback([Message(f"OUT instruction operand 1 is of incorrect type (expected port).", 0, 0)], [])
            if not isinstance(instruction.operands[1], int):
                return Traceback([Message(f"OUT instruction operand 2 is of incorrect type (expected int).", 0, 0)], [])
            x86_code.add_instruction(x86asm.Mnemonic.PUSH, [instruction.operands[1]])
            x86_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EAX, 4])
            x86_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EBX, 1])
            x86_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.ECX, x86asm.Register.ESP])
            x86_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EDX, 1])
            x86_code.add_instruction(x86asm.Mnemonic.INT, [0x80])
            x86_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.ESP, x86asm.Register.EBP])
        
        else:
            return Traceback([Message(f"No x86 translation for for URCL instruction {instruction.mnemonic.name}", 0, 0)], [])
    for ins in x86_code.code:
        print(ins)
    machine_code = bytes()
    for instruction in x86_code.code:
        b = x86asm.encode(instruction)
        if b:
            machine_code += bytes(b)
        else:
            print(instruction, b)
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