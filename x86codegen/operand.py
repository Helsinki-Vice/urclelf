import urcl
from error import Traceback
import x86
from typing import Literal

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

def convert_urcl_register_to_x86(register: urcl.GeneralRegister | urcl.BasePointer | urcl.StackPointer, bits: Literal[32, 64]) -> x86.Operand | Traceback:

    if bits == 64:
        register_mapping = URCL_X64_REGISTER_MAPPING
    else:
        register_mapping = URCL_X86_REGISTER_MAPPING
    x86_register = register_mapping.get(register)

    if x86_register:
        return x86.Operand(x86_register)
    else:
        # TODO: add memory-mapped registers
        return Traceback.new(f"URCL register {register} could not be mapped to a machine register or memory address")

def urcl_operand_to_x86(operand: urcl.urclcst.OperandCSTNode, bits: Literal[32, 64]) -> x86.Operand | Traceback:

    if isinstance(operand.value, urcl.urclcst.Label):
        return x86.Operand(x86.Label(operand.value.name))
    elif isinstance(operand.value, (urcl.GeneralRegister, urcl.BasePointer, urcl.StackPointer)):
        register = convert_urcl_register_to_x86(operand.value, bits)
        if isinstance(register, Traceback):
            error = register
            error.elaborate(f"URCL register {operand.value} has no x86/x64 equivalent")
            return error
        return register
    elif isinstance(operand.value, int):
        return x86.Operand(operand.value)
    elif isinstance(operand.value, urcl.urclcst.RelativeAddress):
        return x86.Operand(operand.value.offset) # FIXME
    elif isinstance(operand.value, urcl.urclcst.Character):
        return x86.Operand(ord(operand.value.char))
    elif isinstance(operand.value, urcl.Port):
        return x86.Operand(operand.value.value.id)
    elif isinstance(operand.value, urcl.DefinedImmediate):
        return x86.Operand(0) # FIXME
    else:
        return Traceback.new(f"URCL operand {operand} has no x86/x64 equivalent")