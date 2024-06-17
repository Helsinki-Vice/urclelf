import x86

from dataclasses import dataclass

@dataclass
class RexPrefix:
    w_use_64_bit_operand: bool      # When 1, a 64-bit operand size is used. Otherwise, when 0, the default operand size is used
    r_modregrm_reg_extention: bool  # This 1-bit value is an extension to the MODRM.reg field
    x_sib_index_extention: bool     # This 1-bit value is an extension to the SIB.index field
    b_field: bool                   # This 1-bit value is an extension to the MODRM.rm field or the SIB.base field

    def __bytes__(self):
        return bytes([0b0100 << 4 | self.w_use_64_bit_operand << 3 | self.r_modregrm_reg_extention << 2 | self.r_modregrm_reg_extention << 1 | self.b_field])

def register_extention_required(register: x86.Register) -> bool:
    return False # FIXME

def rex_prefix_from(reg_field: x86.Register | None, sib_base_field: x86.Register | None, rm_field: x86.Register | None) -> RexPrefix | None:
    
    w, r, x, b = False, False, False, False

    if reg_field:
        w = reg_field.value.size == 64
        r = register_extention_required(reg_field)
    
    if rm_field:
        w = rm_field.value.size == 64
        b = register_extention_required(rm_field)
    
    if sib_base_field:
        x = register_extention_required(sib_base_field)
    
    if not w and not r and not x and not b:
        return None
    else:
        return RexPrefix(w, r, x, b)
