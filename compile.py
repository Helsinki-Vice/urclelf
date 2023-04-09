import urcl
from x86 import AddressingMode
import x86
import x86asm
from elf import ELFHeader, ProgramHeader, SectionHeader, SectionHeaderType, ELF, Program, LINUX_ENTRY_POINT

URCL_X86_REGISTER_MAPPING: "list[x86asm.Register | None]" = [
    None,
    x86asm.Register.AL,
    x86asm.Register.BL,
    x86asm.Register.CL,
    x86asm.Register.DL

]

def compile_urcl(source: str):

    program = urcl.Program.parse_str(source)
    if not program:
        return None
    label_addresses: dict[str, int] = {}
    current_address = LINUX_ENTRY_POINT
    x86_code: list[x86asm.X86ASMInstruction] = [x86asm.X86ASMInstruction(x86asm.Mnemonic.MOV, [x86asm.Operand(x86asm.Register.EBX), x86asm.Operand(0)], AddressingMode.DIRECT)]
    current_address += 6
    for instruction in program.code:
        if isinstance(instruction, urcl.Label):
            label_addresses.update({instruction.name: current_address})
            continue
        if instruction.mnemonic == urcl.Mnemonic.HLT:
            x86_code.extend([
            x86asm.X86ASMInstruction(x86asm.Mnemonic.MOV, [x86asm.Operand(x86asm.Register.EAX), x86asm.Operand(1)], AddressingMode.DIRECT),
            x86asm.X86ASMInstruction(x86asm.Mnemonic.INT, [x86asm.Operand(0x80)], AddressingMode.DIRECT)
        ])
            current_address += 8
        elif instruction.mnemonic == urcl.Mnemonic.NOP:
            x86_code.extend([x86asm.X86ASMInstruction(x86asm.Mnemonic.NOP, [], AddressingMode.DIRECT)])
            current_address += 1
        elif instruction.mnemonic == urcl.Mnemonic.MOV:
            urcl_destination = instruction.operands[0]
            if not isinstance(urcl_destination, urcl.GeneralRegister):
                return None
            x86_destination = URCL_X86_REGISTER_MAPPING[urcl_destination.index]
            if not x86_destination:
                continue
            source_operand = instruction.operands[1]
            if not isinstance(source_operand, int):
                return None
            x86_code.extend([x86asm.X86ASMInstruction(x86asm.Mnemonic.MOV, [x86asm.Operand(x86_destination), x86asm.Operand(source_operand)], AddressingMode.DIRECT)])
        elif instruction.mnemonic == urcl.Mnemonic.ADD:
            urcl_destination = instruction.operands[0]
            if not isinstance(urcl_destination, urcl.GeneralRegister):
                return None
            x86_destination = URCL_X86_REGISTER_MAPPING[urcl_destination.index]
            if not x86_destination:
                continue
            source_operand = instruction.operands[1]
            if not isinstance(source_operand, int):
                return None
            x86_code.extend([x86asm.X86ASMInstruction(x86asm.Mnemonic.ADD, [x86asm.Operand(x86_destination), x86asm.Operand(source_operand)], AddressingMode.DIRECT)])
        else:
            continue
    for ins in x86_code:
        print(ins)
    machine_code = bytes()
    for instruction in x86_code:
        b = x86asm.encode(instruction)
        if b:
            machine_code += bytes(b)
            print(machine_code.hex())
        else:
            print(instruction, b)
    
    return bytes(Program(machine_code).assemble())

def main():
    with open("./source.urcl", "r") as file:
        source = file.read()
    result = compile_urcl(source)
    if not result:
        exit()
    with open("./run", "w+b") as file:
        print("compiled")
        file.write(result)

if __name__ == "__main__":
    main()