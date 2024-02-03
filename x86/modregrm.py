from x86.machine import Register, ModRegRM, AddressingMode, ThreeBits
from x86.asm import EffectiveAddress
from error import Traceback


def calculate_mod(rm_operand: Register | EffectiveAddress) -> AddressingMode | Traceback:
    
    if isinstance(rm_operand, Register):
        return AddressingMode.DIRECT
    if not isinstance(rm_operand.displacement, int):
        rm_operand = EffectiveAddress(rm_operand.segment, rm_operand.base, rm_operand.index, rm_operand.scale, 0)
    assert isinstance(rm_operand.displacement, int)
    if rm_operand.displacement == 0 or (rm_operand.base is None and rm_operand.index is None and rm_operand.displacement >= -0x80000000 and rm_operand.displacement < 0x80000000):
        return AddressingMode.INDIRECT
    elif rm_operand.displacement >= -0x80 and rm_operand.displacement < 0x80:
        return AddressingMode.INDIRECT_WITH_BYTE_DISPLACEMENT
    elif rm_operand.displacement >= -0x80000000 and rm_operand.displacement < 0x80000000:
        return AddressingMode.INDIRECT_WITH_FOUR_BYTE_DISPACEMENT
    else:
        return Traceback.new(f"Displacement value of {rm_operand.displacement} is too large to be encoded in 32 bits")


def calculate_reg(operand: Register | EffectiveAddress | None, opcode_extention: ThreeBits | None) -> ThreeBits | Traceback:
    
    if opcode_extention is not None:
        return opcode_extention
    elif isinstance(operand, Register):
        return operand.value.code
    elif isinstance(operand, EffectiveAddress):
        return Traceback.new(f"Register field of the modregrm byte cannot hold a memory address ({operand} supplied)")
    elif operand is None:
        return Traceback.new("Register field of the modregrm byte cannot be empty")
    else:
        return operand


def get_rm_code(effective_address: EffectiveAddress):

    if effective_address.index is not None:
        return 4
    elif effective_address.displacement and (effective_address.base is None):
        return 5
    elif effective_address.base:
        return effective_address.base.value.code
    else:
        return Traceback.new(f"Supplied address of {effective_address} cannot be encoded in the r/m field")


def calculate_rm(operand: Register | EffectiveAddress | None) -> ThreeBits | Traceback:
    
    if isinstance(operand, EffectiveAddress):
        return get_rm_code(operand)
    elif isinstance(operand, Register):
        return operand.value.code
    elif operand is None:
        return Traceback.new("r/m field cannot be empty")
    else:
        return operand


def calculate_modregrm(register: Register | None, register_or_memory: Register | EffectiveAddress | None, opcode_extention: ThreeBits | None) -> ModRegRM | Traceback:
    
    if register_or_memory is None:
        return Traceback.new("At least one operand is reqired to generate a modregrm byte")
    mod = calculate_mod(register_or_memory)
    reg = calculate_reg(register, opcode_extention)
    rm = calculate_rm(register_or_memory)
    if isinstance(mod, Traceback):
        error = mod
        error.elaborate("Bad mod field")
        return error
    if isinstance(reg, Traceback):
        error = reg
        error.elaborate("Bad reg field")
        return error
    if isinstance(rm, Traceback):
        error = rm
        error.elaborate("Bad r/m field")
        return error
    return ModRegRM(mod, reg, rm)