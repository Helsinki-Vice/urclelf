import urcl
from x86 import AddressingMode
import x86
import x86asm
from elf import ELFHeader, ProgramHeader, SectionHeader, SectionHeaderType, ELF, Program


def compile_urcl(source: str):

    lines = source.splitlines()
    x86_code: list[x86asm.X86ASMInstruction] = [x86asm.X86ASMInstruction(x86asm.Mnemonic.MOV, [x86asm.Operand(x86asm.Register.EAX), x86asm.Operand(1)], AddressingMode.DIRECT)]
    for line in lines:
        if line == "HLT":
            x86_code.extend([
            x86asm.X86ASMInstruction(x86asm.Mnemonic.MOV, [x86asm.Operand(x86asm.Register.EBX), x86asm.Operand(0)], AddressingMode.DIRECT),
            x86asm.X86ASMInstruction(x86asm.Mnemonic.INT, [x86asm.Operand(0x80)], AddressingMode.DIRECT)
        ])
        elif line == "NOP":
            x86_code.extend([x86asm.X86ASMInstruction(x86asm.Mnemonic.NOP, [], AddressingMode.DIRECT)])
        else:
            continue
    
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
    source = "HLT"
    result = compile_urcl(source)
    if isinstance(result, str):
        print(result)
        exit()
    with open("./run", "w+b") as file:
        file.write(result)

if __name__ == "__main__":
    main()