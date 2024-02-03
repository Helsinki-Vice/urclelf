import urcl
from error import Traceback
import x86
import math
from typing import Callable
import linux
from dataclasses import dataclass

URCL_X86_REGISTER_MAPPING: dict[urcl.GeneralRegister | urcl.BasePointer | urcl.StackPointer, x86.Register] = {
    urcl.GeneralRegister(1): x86.Register.EAX,
    urcl.GeneralRegister(2): x86.Register.EBX,
    urcl.GeneralRegister(3): x86.Register.ECX,
    urcl.GeneralRegister(4): x86.Register.EDX,
    urcl.BasePointer(): x86.Register.EBP,
    urcl.StackPointer(): x86.Register.ESP
}

PARSING_ERROR_MESSAGE = "Could not parse urcl source"
NO_ERROR_EXIT_CODE = 0

def get_destination_register(instruction: urcl.InstructionCSTNode) -> urcl.GeneralRegister | urcl.BasePointer | urcl.StackPointer | Traceback:

    if not instruction.operands:
        return Traceback.new(f"{instruction.mnemonic.name.upper()} instruction is missing operands, expected a register", line_number=instruction.line_number, column_number=instruction.column_number)
    urcl_destination_register = instruction.operands[0].value
    if not isinstance(urcl_destination_register, (urcl.GeneralRegister, urcl.BasePointer, urcl.StackPointer)):
        return Traceback.new(f"{instruction.mnemonic.name.upper()} instruction expected first operand to be a register.", line_number=instruction.operands[0].line_number, column_number=instruction.operands[0].column_number)
    
    return urcl_destination_register

def get_x86_destination_register(instruction: urcl.InstructionCSTNode) -> x86.Register | Traceback:

    urcl_destination_register = get_destination_register(instruction)
    if isinstance(urcl_destination_register, Traceback):
        error = urcl_destination_register
        error.elaborate(f"{instruction.mnemonic.name.upper()} instruction does not have valid register as a destination", line_number=instruction.line_number, column_number=instruction.column_number)
        return error
    x86_destination_register = URCL_X86_REGISTER_MAPPING.get(urcl_destination_register)
    if not x86_destination_register:
        return Traceback.new(f"URCL register {urcl_destination_register} has no x86 equivalent")
    
    return x86_destination_register

def get_jump_target(instruction: urcl.InstructionCSTNode) -> urcl.Label | Traceback:

    if not instruction.operands:
        return Traceback.new(f"{instruction.mnemonic.name.upper()} instruction is missing operands, expected a label", line_number=instruction.line_number, column_number=instruction.column_number)
    urcl_destination = instruction.operands[0].value
    if not isinstance(urcl_destination, urcl.Label):
        return Traceback.new(f"{instruction.mnemonic.name.upper()} instruction expected first operand to be a label", line_number=instruction.operands[0].line_number, column_number=instruction.operands[0].column_number)
    
    return urcl_destination

def urcl_operand_to_x86(operand: urcl.urclcst.OperandCSTNode) -> x86.Operand | Traceback:

    if isinstance(operand.value, urcl.urclcst.Label):
        return x86.Operand(x86.Label(operand.value.name))
    elif isinstance(operand.value, (urcl.GeneralRegister, urcl.BasePointer, urcl.StackPointer)):
        register = URCL_X86_REGISTER_MAPPING.get(operand.value)
        if register is None:
            return Traceback.new(f"URCL register {operand.value} has no x86 equivalent")
        return x86.Operand(register)
    elif isinstance(operand.value, int):
        return x86.Operand(operand.value)
    elif isinstance(operand.value, urcl.urclcst.RelativeAddress):
        return x86.Operand(operand.value.offset)
    elif isinstance(operand.value, urcl.urclcst.Character):
        return x86.Operand(ord(operand.value.char))
    elif isinstance(operand.value, urcl.Port):
        return x86.Operand(operand.value.value.id)
    else:
        return Traceback.new(f"URCL operand {operand} has no x86 equivalent")

def bytes_to_stack_ints(value: bytes):
    """Givin a sequence of bytes, what 32 bit little endian ints do we push
    to the stack to make the stack pointer point to the bytes?"""
    int_count = math.ceil(len(value) / 4)
    result = [0] * int_count
    for i, byte in enumerate(value + bytes(int_count * 4 - len(value))):
        int_index = int_count - (i // 4) - 1
        shift_amount = (i % 4) * 8
        result[int_index] += byte << shift_amount
    
    return result

def emit_no_translation_error(instruction: urcl.InstructionCSTNode):
    return Traceback.new(f"No x86 translation for for URCL instruction {instruction.mnemonic.name}", instruction.line_number, instruction.column_number)
"""
T = TypeVar("T")
@dataclass
class InstructionFamily(Generic[T]):
    mnemonics: list[urcl.Mnemonic]
    parse: Callable[[urcl.Mnemonic, T, int], x86.Program | Traceback]
"""
def compile_zero_operand_instruction(instruction: urcl.InstructionCSTNode, entry_point: int):
    
    x86_code = x86.ASMCode(entry_point, [])
    if instruction.mnemonic == urcl.Mnemonic.HLT:
        linux.add_syscall_exit(x86_code, None)
    elif instruction.mnemonic == urcl.Mnemonic.NOP:
        x86_code.add_instruction(x86.Mnemonic.NOP, [])
    elif instruction.mnemonic == urcl.Mnemonic.RET:
        x86_code.add_instruction(x86.Mnemonic.RET, [])
    else:
        assert(False)
    
    return x86_code

def compile_unconditional_jump_instruction(instruction: urcl.InstructionCSTNode, entry_point: int):
    
    x86_code = x86.ASMCode(entry_point, [])
    if instruction.mnemonic in [urcl.Mnemonic.JMP, urcl.Mnemonic.CAL]:
        destination_operand = get_jump_target(instruction)
        if isinstance(destination_operand, urcl.urclcst.Label):
            if instruction.mnemonic == urcl.Mnemonic.JMP:
                x86_code.add_instruction(x86.Mnemonic.JMP, [x86.Label(destination_operand.name)])
            elif instruction.mnemonic == urcl.Mnemonic.CAL:
                x86_code.add_instruction(x86.Mnemonic.CALL, [x86.Label(destination_operand.name)])
            else:
                return Traceback.new(f"No x86 translation for for URCL instruction {instruction.mnemonic.name.upper()}", instruction.line_number, instruction.column_number)
        else:
            emit_no_translation_error(instruction)
    
    return x86_code

def compile_two_operand_jump_instruction(instruction: urcl.InstructionCSTNode, entry_point: int) -> x86.ASMCode | Traceback:
    
    x86_code = x86.ASMCode(entry_point, [])
    if instruction.mnemonic in urcl.TWO_OPERAND_CONDITION_JUMP_MNEMONICS:
        destination_operand = get_jump_target(instruction)
        if isinstance(destination_operand, Traceback):
            error = destination_operand
            error.elaborate(f"{instruction.mnemonic.name} instruction operand 1 is of incorrect type (expected label).", instruction.line_number, instruction.column_number)
            return error
        x86_source_operand = urcl_operand_to_x86(instruction.operands[1])
        if isinstance(x86_source_operand, Traceback):
            error = x86_source_operand
            return error
        x86_code.add_instruction(x86.Mnemonic.CMP, [x86_source_operand.value, 0])
        if instruction.mnemonic == urcl.Mnemonic.BNZ:
            x86_code.add_instruction(x86.Mnemonic.JNE, [x86.Label(destination_operand.name)])
        elif instruction.mnemonic == urcl.Mnemonic.BRZ:
            x86_code.add_instruction(x86.Mnemonic.JE, [x86.Label(destination_operand.name)])
        elif instruction.mnemonic == urcl.Mnemonic.BRP:
            x86_code.add_instruction(x86.Mnemonic.JGE, [x86.Label(destination_operand.name)])
        else:
            emit_no_translation_error(instruction)
    
    return x86_code

def compile_three_operand_jump_instruction(instruction: urcl.InstructionCSTNode, entry_point: int):
    
    x86_code = x86.ASMCode(entry_point, [])
    if instruction.mnemonic in urcl.THREE_OPERAND_CONDITION_JUMP_MNEMONICS:
        destination_operand = get_jump_target(instruction)
        if not isinstance(destination_operand, urcl.urclcst.Label):
            return Traceback.new(f"{instruction.mnemonic.name} instruction operand 1 '{destination_operand}' is of incorrect type (expected label).", instruction.line_number, instruction.column_number)
        x86_source_operand_1 = urcl_operand_to_x86(instruction.operands[1])
        x86_source_operand_2 = urcl_operand_to_x86(instruction.operands[2])
        if isinstance(x86_source_operand_1, Traceback):
            return x86_source_operand_1
        if isinstance(x86_source_operand_2, Traceback):
            return x86_source_operand_2
        x86_code.add_instruction(x86.Mnemonic.CMP, [x86_source_operand_1.value, x86_source_operand_2.value])
        if instruction.mnemonic == urcl.Mnemonic.BLE:
            x86_code.add_instruction(x86.Mnemonic.JBE, [x86.Label(destination_operand.name)])
        elif instruction.mnemonic == urcl.Mnemonic.BGE:
            x86_code.add_instruction(x86.Mnemonic.JGE, [x86.Label(destination_operand.name)])
        elif instruction.mnemonic == urcl.Mnemonic.BRE:
            x86_code.add_instruction(x86.Mnemonic.JE, [x86.Label(destination_operand.name)])
        elif instruction.mnemonic == urcl.Mnemonic.BNE:
            x86_code.add_instruction(x86.Mnemonic.JNE, [x86.Label(destination_operand.name)])
        else:
            emit_no_translation_error(instruction)
    
    return x86_code

def compile_division_instruction(instruction: urcl.InstructionCSTNode, entry_point: int):
    
    x86_code = x86.ASMCode(entry_point, [])
    if instruction.mnemonic in [urcl.Mnemonic.DIV, urcl.Mnemonic.MOD]:
        destination = get_x86_destination_register(instruction)
        if isinstance(destination, Traceback):
            return destination
        source_1 = urcl_operand_to_x86(instruction.operands[1])
        source_2 = urcl_operand_to_x86(instruction.operands[2])
        if isinstance(source_1, Traceback):
            return source_1
        if isinstance(source_2, Traceback):
            return source_2
        temp_regs: list[x86.Register] = []
        for reg in [x86.Register.EAX, x86.Register.EBX, x86.Register.EDX]:
            if reg != destination:
                x86_code.add_instruction(x86.Mnemonic.PUSH, [reg])
                temp_regs.append(reg)
        x86_code.add_move(x86.Register.EAX, source_1.value)
        x86_code.add_move(x86.Register.EDX, 0)
        x86_code.add_move(x86.Register.EBX, source_2.value)
        x86_code.add_instruction(x86.Mnemonic.DIV, [x86.Register.EBX])
        if instruction.mnemonic == urcl.Mnemonic.DIV:
            x86_code.add_move(destination, x86.Register.EAX)
        else:
            x86_code.add_move(destination, x86.Register.EDX)
        for reg in temp_regs.__reversed__():
            x86_code.add_instruction(x86.Mnemonic.POP, [reg])
    
    return x86_code

def compile_out_instruction(instruction: urcl.InstructionCSTNode, entry_point: int):
    
    x86_code = x86.ASMCode(entry_point, [])
    if instruction.mnemonic == urcl.Mnemonic.OUT:
        if isinstance(instruction.operands[0].value, urcl.Port):
            port = instruction.operands[0].value
        elif isinstance(instruction.operands[0].value, int):
            port = urcl.Port.from_value(instruction.operands[0].value)
        else:
            port = None
        if port is None:
            return Traceback.new(f"OUT instruction operand 1 '{instruction.operands[0]}' is not a valid port", instruction.line_number, instruction.column_number)
        
        # URCL standard requires ascii encoding but we use utf-8 instead
        # don't tell ModPunchTree
        if isinstance(instruction.operands[1].value, int):
            output_string = chr(instruction.operands[1].value).encode("utf-8")
        elif isinstance(instruction.operands[1].value, str):
            # NOTE: outputting strings to %TEXT is non-standard
            output_string = instruction.operands[1].value.encode("utf-8")
        elif isinstance(instruction.operands[1].value, urcl.Character):
            output_string = instruction.operands[1].value.char.encode("utf-8")
        elif isinstance(instruction.operands[1].value, urcl.GeneralRegister):
            output_string = instruction.operands[1].value
        else:
            return Traceback.new(f"OUT instruction operand 2 '{instruction.operands[1]}' cannot be output onto a port.", instruction.line_number, instruction.column_number)
        
        x86_code.add_instructions_to_save_general_registers()

        if isinstance(output_string, urcl.GeneralRegister):
            string_length_bytes = 4
            uint32_count = 1
            x86_code.add_instruction(x86.Mnemonic.PUSH, [URCL_X86_REGISTER_MAPPING[output_string]])
        else:
            uint32_count = math.ceil(len(output_string) / 4)
            string_length_bytes = len(output_string)
            for u32 in bytes_to_stack_ints(output_string):
                x86_code.add_instruction(x86.Mnemonic.PUSH, [u32])
        linux.add_syscall_fwrite(x86_code, x86.Register.ESP, string_length_bytes, linux.File.STDOUT)
        x86_code.add_instruction(x86.Mnemonic.ADD, [x86.Register.ESP, uint32_count * 4])
        x86_code.add_instructions_to_restore_general_registers()

    return x86_code

def compile_two_operand_arithmetic_instruction(instruction: urcl.InstructionCSTNode, entry_point: int):
    
    x86_code = x86.ASMCode(entry_point, [])
    if instruction.mnemonic in urcl.TWO_OPERAND_ARITHMETIC_MNEMONICS:
        destination = get_x86_destination_register(instruction)
        if isinstance(destination, Traceback):
            return destination
        urcl_source_operand = instruction.operands[len(instruction.operands) - 1]
        x86_source_operand = urcl_operand_to_x86(urcl_source_operand)

        if isinstance(x86_source_operand, Traceback):
            error = x86_source_operand
            error.elaborate(f"Invalid source operand {urcl_source_operand}", urcl_source_operand.line_number, urcl_source_operand.column_number)
            return error
        x86_code.add_move(destination, x86_source_operand.value)
        if instruction.mnemonic in [urcl.Mnemonic.MOV, urcl.Mnemonic.IMM]:
            pass # Move does not perform a calculation, consider it NOP
        elif instruction.mnemonic == urcl.Mnemonic.INC:
            x86_code.add_instruction(x86.Mnemonic.INC, [destination])
        elif instruction.mnemonic == urcl.Mnemonic.DEC:
            x86_code.add_instruction(x86.Mnemonic.DEC, [destination])
        elif instruction.mnemonic == urcl.Mnemonic.NEG:
            x86_code.add_instruction(x86.Mnemonic.NEG, [destination])
        elif instruction.mnemonic == urcl.Mnemonic.NOT:
            x86_code.add_instruction(x86.Mnemonic.NOT, [destination])
        elif instruction.mnemonic == urcl.Mnemonic.LSH:
            x86_code.add_instruction(x86.Mnemonic.ROL, [destination])
            x86_code.add_instruction(x86.Mnemonic.AND, [destination, (2**31 - 1) << 1])
        elif instruction.mnemonic == urcl.Mnemonic.RSH:
            x86_code.add_instruction(x86.Mnemonic.ROL, [destination])
            x86_code.add_instruction(x86.Mnemonic.AND, [destination, 2**31 - 1])
        else:
            emit_no_translation_error(instruction)
    
    return x86_code

def compile_three_operand_arithmetic_instruction(instruction: urcl.InstructionCSTNode, entry_point: int):
    
    x86_code = x86.ASMCode(entry_point, [])
    if instruction.mnemonic in urcl.THREE_OPERAND_ARITHMETIC_MNEMONICS:
        destination = get_x86_destination_register(instruction)
        if isinstance(destination, Traceback):
            return destination
        source_1 = urcl_operand_to_x86(instruction.operands[1])
        source_2 = urcl_operand_to_x86(instruction.operands[2])
        if isinstance(source_1, Traceback):
            return source_1
        if isinstance(source_2, Traceback):
            return source_2
        if instruction.operands[0] != instruction.operands[1]:
            x86_code.add_move(destination, source_1.value)
        arithmetic_mapping: dict[urcl.Mnemonic, x86.Mnemonic] = {
            urcl.Mnemonic.ADD: x86.Mnemonic.ADD,
            urcl.Mnemonic.SUB: x86.Mnemonic.SUB,
            urcl.Mnemonic.XOR: x86.Mnemonic.XOR
        }
        x86_mnemonic = arithmetic_mapping.get(instruction.mnemonic)
        if x86_mnemonic:
            x86_code.add_instruction(x86_mnemonic, [destination, source_2.value])
        else:
            emit_no_translation_error(instruction)
    
    return x86_code

def compile_push_instruction(instruction: urcl.InstructionCSTNode, entry_point: int):
    
    x86_code = x86.ASMCode(entry_point, [])
    if instruction.mnemonic in [urcl.Mnemonic.PSH]:
        x86_source_operand = urcl_operand_to_x86(instruction.operands[0])
        if isinstance(x86_source_operand, Traceback):
            return x86_source_operand
        x86_code.add_instruction(x86.Mnemonic.PUSH, [x86_source_operand.value])
    
    return x86_code

def compile_pop_instruction(instruction: urcl.InstructionCSTNode, entry_point: int):
    
    x86_code = x86.ASMCode(entry_point, [])
    if instruction.mnemonic in [urcl.Mnemonic.POP]:
        x86_register = get_x86_destination_register(instruction)
        if isinstance(x86_register, Traceback):
            return x86_register
        x86_code.add_instruction(x86.Mnemonic.POP, [x86_register])
    
    return x86_code

def compile_list_load_instruction(instruction: urcl.InstructionCSTNode, entry_point: int):
    
    x86_code = x86.ASMCode(entry_point, [])
    if instruction.mnemonic in [urcl.Mnemonic.LOD, urcl.Mnemonic.LLOD]:
        x86_register = get_x86_destination_register(instruction)
        if isinstance(x86_register, Traceback):
            return x86_register
        source = urcl_operand_to_x86(instruction.operands[1])
        if isinstance(source, Traceback):
            error = source
            error.elaborate(f"LLOD base address '{instruction.operands[1]}' is not valid")
            return error
        assert not isinstance(source.value, x86.EffectiveAddress)
        if len(instruction.operands) == 3:
            index = instruction.operands[2].value
            if not isinstance(index, int):
                return Traceback.new("LLOD index must be an integer", line_number=instruction.operands[2].line_number, column_number=instruction.operands[2].column_number)
        else:
            index = 0
        if isinstance(source, Traceback):
            return source
        memory = x86.sum_into_effective_address([source.value, index])
        if isinstance(memory, Traceback):
            error = memory
            error.elaborate("LLOD target address cannot be translated to x86")
            return error
            
        x86_code.add_instruction(x86.Mnemonic.MOV, [x86_register, memory])
    
    return x86_code

def compile_load_instruction(instruction: urcl.InstructionCSTNode, entry_point: int):
    
    x86_code = x86.ASMCode(entry_point, [])
    if instruction.mnemonic in [urcl.Mnemonic.LOD]:
        x86_register = get_x86_destination_register(instruction)
        if isinstance(x86_register, Traceback):
            return x86_register
        source = urcl_operand_to_x86(instruction.operands[1])
        if isinstance(source, Traceback):
            return source
        memory = source.as_memory(scale=4)
            
        x86_code.add_instruction(x86.Mnemonic.MOV, [x86_register, memory])
    
    return x86_code

def compile_store_instruction(instruction: urcl.InstructionCSTNode, entry_point: int):
    
    x86_code = x86.ASMCode(entry_point, [])
    if instruction.mnemonic in [urcl.Mnemonic.STR]:
        dest = urcl_operand_to_x86(instruction.operands[0])
        source = urcl_operand_to_x86(instruction.operands[1])
        if isinstance(source, Traceback):
            return source
        if isinstance(dest, Traceback):
            return dest
        source = source.as_memory(scale=4)
        dest = dest.value
            
        x86_code.add_instruction(x86.Mnemonic.MOV, [dest, source])
    
    return x86_code

def compile_multiply_instruction(instruction: urcl.InstructionCSTNode, entry_point: int):
    
    x86_code = x86.ASMCode(entry_point, [])
    if instruction.mnemonic in [urcl.Mnemonic.MLT]:
        destination = get_x86_destination_register(instruction)
        if isinstance(destination, Traceback):
            return destination
        source_1 = urcl_operand_to_x86(instruction.operands[1])
        source_2 = urcl_operand_to_x86(instruction.operands[2])
        if isinstance(source_1, Traceback):
            return source_1
        if isinstance(source_2, Traceback):
            return source_2
        if destination != x86.Register.EAX:
            x86_code.add_instruction(x86.Mnemonic.PUSH, [x86.Register.EAX])
        if destination != x86.Register.EDX:
            x86_code.add_instruction(x86.Mnemonic.PUSH, [x86.Register.EDX])
        x86_code.add_move(x86.Register.EAX, source_1.value)
        
        x86_code.add_instruction(x86.Mnemonic.MUL, [source_2.value])
        x86_code.add_move(destination, x86.Register.EAX)
        
        if destination != x86.Register.EDX:
            x86_code.add_instruction(x86.Mnemonic.POP, [x86.Register.EDX])
        if destination != x86.Register.EAX:
            x86_code.add_instruction(x86.Mnemonic.POP, [x86.Register.EAX])
    
    return x86_code

@dataclass
class InstructionFamily:
    mnemonics: list[urcl.Mnemonic]
    compile: Callable[[urcl.InstructionCSTNode, int], x86.ASMCode | Traceback]
    operand_count: int

TRANSLATIONS: list[InstructionFamily] = [
    InstructionFamily(urcl.ZERO_OPERAND_MNEMONICS, compile_zero_operand_instruction, 0),
    InstructionFamily([urcl.Mnemonic.JMP, urcl.Mnemonic.CAL], compile_unconditional_jump_instruction, 1),
    InstructionFamily([urcl.Mnemonic.MLT], compile_multiply_instruction, 3),
    InstructionFamily(urcl.TWO_OPERAND_CONDITION_JUMP_MNEMONICS, compile_two_operand_jump_instruction, 2),
    InstructionFamily(urcl.THREE_OPERAND_CONDITION_JUMP_MNEMONICS, compile_three_operand_jump_instruction, 3),
    InstructionFamily([urcl.Mnemonic.DIV, urcl.Mnemonic.MOD], compile_division_instruction, 3),
    InstructionFamily([urcl.Mnemonic.OUT], compile_out_instruction, 2),
    InstructionFamily(urcl.TWO_OPERAND_ARITHMETIC_MNEMONICS, compile_two_operand_arithmetic_instruction, 2),
    InstructionFamily(urcl.THREE_OPERAND_ARITHMETIC_MNEMONICS, compile_three_operand_arithmetic_instruction, 3),
    InstructionFamily([urcl.Mnemonic.PSH], compile_push_instruction, 1),
    InstructionFamily([urcl.Mnemonic.POP], compile_pop_instruction, 1),
    InstructionFamily([urcl.Mnemonic.LLOD], compile_list_load_instruction, 3),
    InstructionFamily([urcl.Mnemonic.LOD], compile_load_instruction, 2),
    InstructionFamily([urcl.Mnemonic.STR], compile_store_instruction, 2)
]