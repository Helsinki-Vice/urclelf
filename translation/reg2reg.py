from typing import Literal

import urcl
import x86
from error import Traceback

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