import math
from typing import Literal
from x86.machine import Register, ModRegRM, AddressingMode, ScaleIndexByte, ThreeBits
from x86.asm import EffectiveAddress


def calculate_sib_scale(effective_address: EffectiveAddress):

    scale = round(math.log2(effective_address.scale))
    # Don't change to "scale in [0, 1, 2, 3]"" or pylance will get mad 
    if scale == 0 or scale == 1 or scale == 2 or scale == 3:
        return scale


def calculate_sib_index(effective_address: EffectiveAddress):

    if effective_address.base == Register.ESP and effective_address.index is None:
        return 4 # Special case for [esp] addressing
    if effective_address.index is None:
        return None
    index = effective_address.index.value.code
    if index == 4: # Technically it's register eiz but that's too bad
        return None
    
    return index


def calculate_sib_base(effective_address: EffectiveAddress, mod: AddressingMode) -> ThreeBits | None:

    if effective_address.base is None:
        return 5 # Tells the cpu to look for 32 bit displacement
    
    return effective_address.base.value.code


def calculate_sib(effective_address: EffectiveAddress | Register | None, mod_reg_rm: ModRegRM | None) -> ScaleIndexByte | None:

    if mod_reg_rm is None:
        return None
    if not (mod_reg_rm.mod != AddressingMode.DIRECT and mod_reg_rm.rm == 4):
        return None
    if not isinstance(effective_address, EffectiveAddress):
        return None
    scale = calculate_sib_scale(effective_address)
    index = calculate_sib_index(effective_address)
    base = calculate_sib_base(effective_address, mod_reg_rm.mod)
    
    if scale is None or index is None or base is None:
        return None
    return ScaleIndexByte(scale, index, base)