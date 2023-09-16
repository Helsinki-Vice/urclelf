import urcl
from error import Traceback
import x86
import math
from typing import Callable, TypeVar, Generic
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

def get_destination_register(instruction: urcl.InstructionCSTNode) -> urcl.GeneralRegister | None:

    if not instruction.operands:
        return None
    urcl_destination_register = instruction.operands[0].value
    if not isinstance(urcl_destination_register, urcl.GeneralRegister):
        return None
    
    return urcl_destination_register

def get_x86_destination_register(instruction: urcl.InstructionCSTNode) -> x86.Register | None:

    urcl_destination_register = get_destination_register(instruction)
    if not urcl_destination_register:
        return None
    x86_destination_register = URCL_X86_REGISTER_MAPPING.get(urcl_destination_register)
    if not x86_destination_register:
        return None
    
    return x86_destination_register

def get_jump_target(instruction: urcl.InstructionCSTNode) -> urcl.Label | None:

    if not instruction.operands:
        return None
    urcl_destination = instruction.operands[0].value
    if not isinstance(urcl_destination, urcl.Label):
        return None
    
    return urcl_destination

def urcl_operand_to_x86(operand: urcl.urclcst.OperandCSTNode) -> x86.Operand | None:

    if isinstance(operand.value, urcl.urclcst.Label):
        return x86.Operand(x86.Label(operand.value.name))
    elif isinstance(operand.value, (urcl.GeneralRegister, urcl.BasePointer, urcl.StackPointer)):
        register = URCL_X86_REGISTER_MAPPING.get(operand.value)
        if register:
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
        return None

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

def no_translation(instruction: urcl.InstructionCSTNode):
    return Traceback.new(f"No x86 translation for for URCL instruction {instruction.mnemonic.name}", instruction.line_number, instruction.column_number)
"""
T = TypeVar("T")
@dataclass
class InstructionFamily(Generic[T]):
    mnemonics: list[urcl.Mnemonic]
    parse: Callable[[urcl.Mnemonic, T, int], x86.Program | Traceback]
"""
def compile_zero_operand_instruction(instruction: urcl.InstructionCSTNode, entry_point: int):
    
    x86_code = x86.Program(entry_point, [])
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
    
    x86_code = x86.Program(entry_point, [])
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
            no_translation(instruction)
    
    return x86_code

def compile_two_operand_jump_instruction(instruction: urcl.InstructionCSTNode, entry_point: int):
    
    x86_code = x86.Program(entry_point, [])
    if instruction.mnemonic in urcl.TWO_OPERAND_CONDITION_JUMP_MNEMONICS:
        destination_operand = get_jump_target(instruction)
        if not isinstance(destination_operand, urcl.urclcst.Label):
            return Traceback.new(f"{instruction.mnemonic.name} instruction operand 1 is of incorrect type (expected label).", instruction.line_number, instruction.column_number)
        x86_source_operand = urcl_operand_to_x86(instruction.operands[1])
        if x86_source_operand is None:
            return Traceback.new("TODO")
        x86_code.add_instruction(x86.Mnemonic.CMP, [x86_source_operand.value, 0])
        if instruction.mnemonic == urcl.Mnemonic.BNZ:
            x86_code.add_instruction(x86.Mnemonic.JNE, [x86.Label(destination_operand.name)])
        elif instruction.mnemonic == urcl.Mnemonic.BRZ:
            x86_code.add_instruction(x86.Mnemonic.JE, [x86.Label(destination_operand.name)])
        elif instruction.mnemonic == urcl.Mnemonic.BRP:
            x86_code.add_instruction(x86.Mnemonic.JGE, [x86.Label(destination_operand.name)])
        else:
            no_translation(instruction)
    
    return x86_code

def compile_three_operand_jump_instruction(instruction: urcl.InstructionCSTNode, entry_point: int):
    
    x86_code = x86.Program(entry_point, [])
    if instruction.mnemonic in urcl.THREE_OPERAND_CONDITION_JUMP_MNEMONICS:
        destination_operand = get_jump_target(instruction)
        if not isinstance(destination_operand, urcl.urclcst.Label):
            return Traceback.new(f"{instruction.mnemonic.name} instruction operand 1 '{destination_operand}' is of incorrect type (expected label).", instruction.line_number, instruction.column_number)
        x86_source_operand_1 = urcl_operand_to_x86(instruction.operands[1])
        x86_source_operand_2 = urcl_operand_to_x86(instruction.operands[2])
        if x86_source_operand_1 is None:
            return Traceback.new("TODO")
        if x86_source_operand_2 is None:
            return Traceback.new("TODO")
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
            no_translation(instruction)
    
    return x86_code

def compile_division_instruction(instruction: urcl.InstructionCSTNode, entry_point: int):
    
    x86_code = x86.Program(entry_point, [])
    if instruction.mnemonic in [urcl.Mnemonic.DIV, urcl.Mnemonic.MOD]:
        destination = get_x86_destination_register(instruction)
        if not destination:
            return Traceback.new(f"{instruction.mnemonic.value.upper()} instruction received incorrect destination type (expected register).", instruction.line_number, instruction.column_number)
        source_1 = urcl_operand_to_x86(instruction.operands[1])
        source_2 = urcl_operand_to_x86(instruction.operands[2])
        if source_1 is None:
            return Traceback.new("TODO")
        if source_2 is None:
            return Traceback.new("TODO")
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
    
    x86_code = x86.Program(entry_point, [])
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
    
    x86_code = x86.Program(entry_point, [])
    if instruction.mnemonic in urcl.TWO_OPERAND_ARITHMETIC_MNEMONICS:
        destination = get_x86_destination_register(instruction)
        if not destination:
            return Traceback.new(f"{instruction.mnemonic.value.upper()} instruction received incorrect operand type (expected register).", instruction.line_number, instruction.column_number)
        urcl_source_operand = instruction.operands[len(instruction.operands) - 1]
        x86_source_operand = urcl_operand_to_x86(urcl_source_operand)

        if x86_source_operand is None:
            return Traceback.new(f"Invalid source operand {urcl_source_operand}", urcl_source_operand.line_number, urcl_source_operand.column_number)
        x86_code.add_move(destination, x86_source_operand.value)
        if instruction.mnemonic == urcl.Mnemonic.MOV:
            pass # Move does not perform a calculation, consider it NOP
        elif instruction.mnemonic == urcl.Mnemonic.INC:
            x86_code.add_instruction(x86.Mnemonic.INC, [destination])
        elif instruction.mnemonic == urcl.Mnemonic.DEC:
            x86_code.add_instruction(x86.Mnemonic.DEC, [destination])
        elif instruction.mnemonic == urcl.Mnemonic.NEG:
            x86_code.add_instruction(x86.Mnemonic.NEG, [destination])
        elif instruction.mnemonic == urcl.Mnemonic.LSH:
            x86_code.add_instruction(x86.Mnemonic.ROL, [destination])
            x86_code.add_instruction(x86.Mnemonic.AND, [destination, (2**31 - 1) << 1])
        elif instruction.mnemonic == urcl.Mnemonic.RSH:
            x86_code.add_instruction(x86.Mnemonic.ROL, [destination])
            x86_code.add_instruction(x86.Mnemonic.AND, [destination, 2**31])
        else:
            no_translation(instruction)
    
    return x86_code

def compile_three_operand_arithmetic_instruction(instruction: urcl.InstructionCSTNode, entry_point: int):
    
    x86_code = x86.Program(entry_point, [])
    if instruction.mnemonic in urcl.THREE_OPERAND_ARITHMETIC_MNEMONICS:
        destination = get_x86_destination_register(instruction)
        if not destination:
            return Traceback.new(f"{instruction.mnemonic.value.upper()} instruction received incorrect destination type (expected register).", instruction.line_number, instruction.column_number)
        source_1 = urcl_operand_to_x86(instruction.operands[1])
        source_2 = urcl_operand_to_x86(instruction.operands[2])
        if source_1 is None:
            return Traceback.new("TODO")
        if source_2 is None:
            return Traceback.new("TODO")
        if instruction.operands[0] != instruction.operands[1]:
            x86_code.add_move(destination, source_1.value)
        arithmetic_mapping: dict[urcl.Mnemonic, x86.Mnemonic] = {
            urcl.Mnemonic.ADD: x86.Mnemonic.ADD,
            urcl.Mnemonic.SUB: x86.Mnemonic.SUB,
            urcl.Mnemonic.XOR: x86.Mnemonic.XOR,
        }
        x86_mnemonic = arithmetic_mapping.get(instruction.mnemonic)
        if x86_mnemonic:
            x86_code.add_instruction(x86_mnemonic, [destination, source_2.value])
        else:
            no_translation(instruction)
    
    return x86_code

def compile_push_instruction(instruction: urcl.InstructionCSTNode, entry_point: int):
    
    x86_code = x86.Program(entry_point, [])
    if instruction.mnemonic in [urcl.Mnemonic.PSH]:
        x86_source_operand = urcl_operand_to_x86(instruction.operands[0])
        if x86_source_operand is None:
            return Traceback.new("TODO")
        x86_code.add_instruction(x86.Mnemonic.PUSH, [x86_source_operand.value])
    
    return x86_code

def compile_pop_instruction(instruction: urcl.InstructionCSTNode, entry_point: int):
    
    x86_code = x86.Program(entry_point, [])
    if instruction.mnemonic in [urcl.Mnemonic.POP]:
        x86_register = get_x86_destination_register(instruction)
        if x86_register is None:
            return Traceback.new("TODO")
        x86_code.add_instruction(x86.Mnemonic.POP, [x86_register])
    
    return x86_code

def compile_load_instruction(instruction: urcl.InstructionCSTNode, entry_point: int):
    
    x86_code = x86.Program(entry_point, [])
    if instruction.mnemonic in [urcl.Mnemonic.LOD]:
        x86_register = get_x86_destination_register(instruction)
        if x86_register is None:
            return Traceback.new(f"{instruction.mnemonic.value.upper()} instruction did not find a register destination.")
        todo = urcl_operand_to_x86(instruction.operands[1])
        if todo is None:
            return Traceback.new("TODO")
        source = todo.value
            
        if isinstance(source, x86.Register):
            memory = x86.EffectiveAddress(base=source, scale=4)
        elif isinstance(source, x86.EffectiveAddress):
            memory = source
        else:
            memory = x86.EffectiveAddress(displacement=source)
        x86_code.add_instruction(x86.Mnemonic.MOV, [x86_register, memory])
    
    return x86_code

def compile_store_instruction(instruction: urcl.InstructionCSTNode, entry_point: int):
    
    x86_code = x86.Program(entry_point, [])
    if instruction.mnemonic in [urcl.Mnemonic.STR]:
        dest = urcl_operand_to_x86(instruction.operands[0])
        source = urcl_operand_to_x86(instruction.operands[1])
        if dest is None or source is None:
            return Traceback.new("TODO")
        source = source.value
        dest = dest.value
            
        if isinstance(dest, x86.Register):
            memory = x86.EffectiveAddress(base=dest, scale=4)
        elif isinstance(dest, x86.EffectiveAddress):
            memory = source
        else:
            memory = x86.EffectiveAddress(displacement=dest)
        x86_code.add_instruction(x86.Mnemonic.MOV, [dest, memory])
    
    return x86_code

def compile_multiply_instruction(instruction: urcl.InstructionCSTNode, entry_point: int):
    
    x86_code = x86.Program(entry_point, [])
    if instruction.mnemonic in [urcl.Mnemonic.MLT]:
        destination = get_x86_destination_register(instruction)
        if not destination:
            return Traceback.new(f"{instruction.mnemonic.value.upper()} instruction received incorrect destination type (expected register).", instruction.line_number, instruction.column_number)
        source_1 = urcl_operand_to_x86(instruction.operands[1])
        source_2 = urcl_operand_to_x86(instruction.operands[2])
        if source_1 is None:
            return Traceback.new("TODO")
        if source_2 is None:
            return Traceback.new("TODO")
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
    compile: Callable[[urcl.InstructionCSTNode, int], x86.Program | Traceback]
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
    InstructionFamily([urcl.Mnemonic.LOD], compile_load_instruction, 2),
    InstructionFamily([urcl.Mnemonic.STR], compile_store_instruction, 2)
]