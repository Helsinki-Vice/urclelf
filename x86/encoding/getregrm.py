from x86.asm import ASMInstruction, EffectiveAddress, Operand
from x86.register import Register
from x86.encoding.encodings import RegisterSize, InstructionEncodingFormat
from error import Traceback

def get_effective_address_register_size(effective_address: EffectiveAddress):
    if isinstance(effective_address.base, Register):
        return effective_address.base.value.size

def get_operand_register_size(operand: Operand):
    
    if isinstance(operand.value, Register):
        return operand.value.value.size
    elif isinstance(operand.value, EffectiveAddress):
        return get_effective_address_register_size(operand.value)
    else:
        return None

def get_regrm_operands(instruction: ASMInstruction, encoding: InstructionEncodingFormat, direction_bit: bool):

        operands: list[Register | EffectiveAddress] = []
        for index, operand_format in enumerate(encoding.permitted_operands):
            if isinstance(operand_format, RegisterSize):
                # Ignore if it is an immediate or an implied operand
                operand = instruction.operands[index]
                if isinstance(operand.value, Register):
                    if get_operand_register_size(operand) != operand_format.size:
                        return Traceback.new(f"Invalid register size for operand index {index}: exprected {operand_format.size} bits, found {get_operand_register_size(operand)}.")
                    operands.append(operand.value)
                    pass
                elif isinstance(operand.value, EffectiveAddress):
                    operands.append(operand.value)
                    pass
                else:
                    return Traceback.new(f"Expected register or memory operand, found an immediate instead.")
        
        if not operands:
            return None
        if len(operands) == 1:
            # Ignore direction bit, there's probably an opcode extention in reg anyway
            reg, rm = (None, operands[0])
            return (None, operands[0])
        elif len(operands) == 2:
            # Direction bit swaps the operands, wowsers
            if direction_bit:
                reg, rm = (operands[0], operands[1])
            else:
                reg, rm = (operands[1], operands[0])
    
        else:
            # Too many operands, wtf
            return Traceback.new(f"There are too many register/memory operands.")
        
        if isinstance(reg, EffectiveAddress):
            # Sir this is a Wendy's 💀
            return Traceback.new("r/m field can only contain a register.")
        
        if isinstance(rm, EffectiveAddress):
            if rm.base:
                #NOTE: We are assuming the cpu is not in real or long mode
                if rm.base.value.size != 32:
                    return Traceback.new(f"Only 32 bit memory is currently supported.")
        else:
            if reg.value.size != rm.value.size:
                return Traceback.new(f"Register {reg} and {rm} are not the same size.")

        return reg, rm