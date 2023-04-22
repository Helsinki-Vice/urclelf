import urcl
import x86
import x86asm
import elf

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

def compile_urcl(source: str):

    urcl_program = urcl.Program.parse_str(source)
    if not urcl_program:
        return None
    label_addresses: dict[str, int] = {}
    elf_program = elf.Program(bytes())
    x86_code = x86asm.Program([], {}, elf_program.entry_point)
    x86_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EBX, 0])
    #x86_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EBP, elf_program.entry_point + 512])
    #x86_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.ESP, elf_program.entry_point + 512])
    for instruction in urcl_program.code:

        if isinstance(instruction, urcl.Label):
            continue

        if instruction.mnemonic == urcl.Mnemonic.HLT:
            x86_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EAX, 1])
            x86_code.add_instruction(x86asm.Mnemonic.INT, [0x80])
        
        elif instruction.mnemonic == urcl.Mnemonic.NOP:
            x86_code.add_instruction(x86asm.Mnemonic.NOP, [], )
        
        elif instruction.mnemonic == urcl.Mnemonic.MOV:
            destination = get_destination_register(instruction)
            if not destination:
                continue
            source_operand = instruction.operands[1]
            if not isinstance(source_operand, int):
                return None
            x86_code.add_instruction(x86asm.Mnemonic.MOV, [destination, source_operand])
        
        elif instruction.mnemonic == urcl.Mnemonic.INC:
            destination = get_destination_register(instruction)
            if not destination:
                continue
            x86_code.add_instruction(x86asm.Mnemonic.ADD, [destination, 1])
        
        elif instruction.mnemonic == urcl.Mnemonic.JNZ:
            destination_operand = instruction.get_jump_target()
            if not isinstance(destination_operand, urcl.RelativeAddress):
                return None
            if len(instruction.operands) != 2:
                return None
            source_operand = instruction.operands[1]
            if not isinstance(source_operand, urcl.GeneralRegister):
                return None
            source_register = URCL_X86_REGISTER_MAPPING[source_operand.index]
            if not source_register:
                continue
            x86_code.add_instruction(x86asm.Mnemonic.CMP, [source_register, 0])
            x86_code.add_instruction(x86asm.Mnemonic.JNZ, [0])
            urcl_jump_offset = destination_operand.offset
            x86_jump_address = x86_code.instruction_addresses[len(x86_code.code) - 2 + urcl_jump_offset]
            x86_jump_offset = x86_jump_address - (x86_code.instruction_addresses[-1] + x86_code.instruction_sizes[-1])
            x86_code.code[-1].operands[0] = x86asm.Operand(x86_jump_offset)
        
        elif instruction.mnemonic == urcl.Mnemonic.OUT:
            if len(instruction.operands) != 2:
                return None
            if instruction.operands[0] != 1:
                return None
            if not isinstance(instruction.operands[1], int):
                return None
            #x86_code.add_instruction(x86asm.Mnemonic.PUSH, [instruction.operands[1]])
            #x86_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EAX, 4])
            #x86_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EBX, x86asm.Register.ESP])
            #x86_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.EDX, 1])
            #x86_code.add_instruction(x86asm.Mnemonic.INT, [0x80])
            #x86_code.add_instruction(x86asm.Mnemonic.MOV, [x86asm.Register.ESP, x86asm.Register.EBP])
            
        
        else:
            continue
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
    if not result:
        print("compile failed")
        exit()
    with open("./run", "w+b") as file:
        print("compiled")
        file.write(result)

if __name__ == "__main__":
    main()