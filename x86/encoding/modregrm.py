from x86.encoding.machine import ModRegRM, AddressingMode, ThreeBits, get_register_code
from x86.register import Register
from x86.asm import EffectiveAddress, PointerSize, Label
from error import Traceback

def calculate_mod_field(rm_operand: Register | EffectiveAddress) -> AddressingMode | Traceback:
    
    if isinstance(rm_operand, Register):
        return AddressingMode.DIRECT
    if isinstance(rm_operand.displacement, Label):
        return AddressingMode.INDIRECT_WITH_FOUR_BYTE_DISPACEMENT
    if not isinstance(rm_operand.displacement, int):
        rm_operand = EffectiveAddress(PointerSize.DWORD, rm_operand.segment, rm_operand.base, rm_operand.index, rm_operand.scale, 0)
    assert isinstance(rm_operand.displacement, int)
    if rm_operand.displacement == 0 or (rm_operand.base is None and rm_operand.index is None and rm_operand.displacement >= -0x80000000 and rm_operand.displacement < 0x80000000):
        return AddressingMode.INDIRECT
    elif rm_operand.displacement >= -0x80 and rm_operand.displacement < 0x80:
        return AddressingMode.INDIRECT_WITH_BYTE_DISPLACEMENT
    elif rm_operand.displacement >= -0x80000000 and rm_operand.displacement < 0x80000000:
        return AddressingMode.INDIRECT_WITH_FOUR_BYTE_DISPACEMENT
    else:
        return Traceback.new(f"Displacement value of {rm_operand.displacement} is too large to be encoded in 32 bits")


def calculate_reg_field(operand: Register | EffectiveAddress | None, opcode_extention: ThreeBits | None) -> ThreeBits | Traceback:
    
    if opcode_extention is not None:
        return opcode_extention
    elif isinstance(operand, Register):
        result = get_register_code(operand)
        # For the type checker...
        assert result == 0 or result == 1 or result == 2 or result == 3 or result == 4 or result == 5 or result == 6 or result == 7
        return result
    elif isinstance(operand, EffectiveAddress):
        return Traceback.new(f"Register field of the modregrm byte cannot hold a memory address ({operand} supplied)")
    elif operand is None:
        return Traceback.new("Register field of the modregrm byte cannot be empty")
    else:
        return operand


def get_rm_field_from_effective_address(effective_address: EffectiveAddress):

    if effective_address.index is not None:
        return 4 # Tells the CPU to look for sib byte
    elif effective_address.displacement and (effective_address.base is None):
        return 5 # Tells the CPU to use displacement-only addressing mode
    elif effective_address.base:
        return get_register_code(effective_address.base)
    else:
        return Traceback.new(f"Supplied address of {effective_address} cannot be encoded in the r/m field")


def calculate_rm_field(operand: Register | EffectiveAddress | None) -> ThreeBits | Traceback:
    
    if isinstance(operand, EffectiveAddress):
        result = get_rm_field_from_effective_address(operand)
    elif isinstance(operand, Register):
        result = get_register_code(operand)
    elif operand is None:
        result = Traceback.new("r/m field cannot be empty")
    else:
        return operand
    
    # For the type checker...
    assert isinstance(result, Traceback) or result == 0 or result == 1 or result == 2 or result == 3 or result == 4 or result == 5 or result == 6 or result == 7
    return result

def calculate_modregrm(register: Register | None, register_or_memory: Register | EffectiveAddress | None, opcode_extention: ThreeBits | None) -> ModRegRM | Traceback:
    
    if register_or_memory is None:
        return Traceback.new("At least one operand is reqired to generate a modregrm byte")
    mod = calculate_mod_field(register_or_memory)
    reg = calculate_reg_field(register, opcode_extention)
    rm = calculate_rm_field(register_or_memory)
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