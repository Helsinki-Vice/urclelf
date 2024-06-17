import urcl
from error import Traceback
import x86
import math
from typing import Callable, Literal
import sysv
from dataclasses import dataclass

import x86.register

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

PARSING_ERROR_MESSAGE = "Could not parse urcl source"
NO_ERROR_EXIT_CODE = 0

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
    
        #effective_address = x86.sum_into_effective_address([], x86.PointerSize.DWORD)
        #if isinstance(effective_address, Traceback):
        #    error = effective_address
        #    error.elaborate(f"URCL register {register} could not be mapped to a memory address")
        #    return error
        #return x86.Operand(effective_address)
    
def get_destination_register(instruction: urcl.InstructionCSTNode, bits: Literal[32, 64]) -> urcl.GeneralRegister | urcl.BasePointer | urcl.StackPointer | Traceback:

    if not instruction.operands:
        return Traceback.new(f"{instruction.mnemonic.name.upper()} instruction is missing operands, expected a register", line_number=instruction.line_number, column_number=instruction.column_number)
    urcl_destination_register = instruction.operands[0].value
    if not isinstance(urcl_destination_register, (urcl.GeneralRegister, urcl.BasePointer, urcl.StackPointer)):
        return Traceback.new(f"{instruction.mnemonic.name.upper()} instruction expected first operand to be a register.", line_number=instruction.operands[0].line_number, column_number=instruction.operands[0].column_number)
    
    return urcl_destination_register

def get_x86_destination_register(instruction: urcl.InstructionCSTNode, bits: Literal[32, 64]) -> x86.Register | x86.EffectiveAddress | x86.Immediate | Traceback:

    urcl_destination_register = get_destination_register(instruction, bits)
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

def get_jump_target(instruction: urcl.InstructionCSTNode) -> urcl.Label | Traceback:

    if not instruction.operands:
        return Traceback.new(f"{instruction.mnemonic.name.upper()} instruction is missing operands, expected a label", line_number=instruction.line_number, column_number=instruction.column_number)
    urcl_destination = instruction.operands[0].value
    if not isinstance(urcl_destination, urcl.Label):
        return Traceback.new(f"{instruction.mnemonic.name.upper()} instruction expected first operand to be a label", line_number=instruction.operands[0].line_number, column_number=instruction.operands[0].column_number)
    
    return urcl_destination

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

def bytes_to_stack_ints(value: bytes, bytes_per_int: int):
    """Givin a sequence of bytes, what little endian ints do we push
    to the stack to make the stack pointer point to the bytes?"""
    int_count = math.ceil(len(value) / bytes_per_int)
    result = [0] * int_count
    for i, byte in enumerate(value + bytes(int_count * bytes_per_int - len(value))):
        int_index = int_count - (i // bytes_per_int) - 1
        shift_amount = (i % bytes_per_int) * 8
        result[int_index] += byte << shift_amount
    
    return result

def emit_no_translation_error(instruction: urcl.InstructionCSTNode):
    return Traceback.new(f"No x86 translation for for URCL instruction {instruction.mnemonic.name}", instruction.line_number, instruction.column_number)

def compile_zero_operand_instruction(instruction: urcl.InstructionCSTNode, bits: Literal[32, 64]):
    
    x86_code = x86.ASMCode(0, [])
    if instruction.mnemonic == urcl.Mnemonic.HLT:
        sysv.add_syscall_exit(x86_code, None, bits)
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

def compile_two_operand_jump_instruction(instruction: urcl.InstructionCSTNode, bits: Literal[32, 64]) -> x86.ASMCode | Traceback:
    
    x86_code = x86.ASMCode(0, [])
    if instruction.mnemonic in urcl.TWO_OPERAND_CONDITION_JUMP_MNEMONICS:
        destination_operand = get_jump_target(instruction)
        if isinstance(destination_operand, Traceback):
            error = destination_operand
            error.elaborate(f"{instruction.mnemonic.name} instruction operand 1 is of incorrect type (expected label).", instruction.line_number, instruction.column_number)
            return error
        x86_source_operand = urcl_operand_to_x86(instruction.operands[1], bits)
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

def compile_three_operand_jump_instruction(instruction: urcl.InstructionCSTNode, bits: Literal[32, 64]):
    
    x86_code = x86.ASMCode(0, [])
    if instruction.mnemonic in urcl.THREE_OPERAND_CONDITION_JUMP_MNEMONICS:
        destination_operand = get_jump_target(instruction)
        if not isinstance(destination_operand, urcl.urclcst.Label):
            return Traceback.new(f"{instruction.mnemonic.name} instruction operand 1 '{destination_operand}' is of incorrect type (expected label).", instruction.line_number, instruction.column_number)
        x86_source_operand_1 = urcl_operand_to_x86(instruction.operands[1], bits)
        x86_source_operand_2 = urcl_operand_to_x86(instruction.operands[2], bits)
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
        elif instruction.mnemonic == urcl.Mnemonic.BRL:
            x86_code.add_instruction(x86.Mnemonic.JL, [x86.Label(destination_operand.name)])
        else:
            emit_no_translation_error(instruction)
    
    return x86_code

# FIXME: x64 support
def compile_division_instruction(instruction: urcl.InstructionCSTNode, bits: Literal[32, 64]):
    
    if instruction.mnemonic in [urcl.Mnemonic.DIV, urcl.Mnemonic.MOD]:
        destination = get_x86_destination_register(instruction, bits)
        if isinstance(destination, Traceback):
            return destination
        source_1 = urcl_operand_to_x86(instruction.operands[1], bits)
        source_2 = urcl_operand_to_x86(instruction.operands[2], bits)
        if isinstance(source_1, Traceback):
            return source_1
        if isinstance(source_2, Traceback):
            return source_2
        
    return x86.generate_division_code(x86.Operand(destination), source_1, source_2, bits, do_modulo=instruction.mnemonic==urcl.Mnemonic.MOD)

def compile_out_instruction(instruction: urcl.InstructionCSTNode, bits: Literal[32, 64]):
    
    registers = x86.get_registers(bits)
    
    x86_code = x86.ASMCode(0, [])
    if instruction.mnemonic == urcl.Mnemonic.OUT:
        if isinstance(instruction.operands[0].value, urcl.Port):
            port = instruction.operands[0].value
            port_name = instruction.operands[0].value
        elif isinstance(instruction.operands[0].value, int):
            port = urcl.Port.from_value(instruction.operands[0].value)
        else:
            port = None
        if port is None:
            return Traceback.new(f"OUT instruction operand 1 '{instruction.operands[0]}' is not a valid port", instruction.line_number, instruction.column_number)
        
        if port == urcl.Port.TEXT:
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

            x86_code.add_instructions_to_save_general_registers(registers)

            if isinstance(output_string, urcl.GeneralRegister):
                string_length_bytes = bits // 8
                int_count = 1
                destination = convert_urcl_register_to_x86(output_string, bits)
                if isinstance(destination, Traceback):
                    error = destination
                    error.elaborate(f"Destination register {output_string} for OUT instruction is invalid")
                    return error
                x86_code.add_instruction(x86.Mnemonic.PUSH, [destination.value])
            else:
                int_count = math.ceil(len(output_string) / (4))
                string_length_bytes = len(output_string)
                for uint in bytes_to_stack_ints(output_string, 4):
                    x86_code.add_instruction(x86.Mnemonic.PUSH, [uint])
            sysv.add_syscall_fwrite(x86_code, registers.sp, string_length_bytes, sysv.File.STDOUT, bits)
            x86_code.add_instruction(x86.Mnemonic.ADD, [registers.sp, int_count * 4])
            x86_code.add_instructions_to_restore_general_registers(registers)
        else:
            x86_code.add_instruction(x86.Mnemonic.PUSH, [urcl_operand_to_x86(instruction.operands[1], bits).value])
            x86_code.add_instruction(x86.Mnemonic.CALL, [x86.Label(f"urcl_port_{port.name.lower()}_out")])

    return x86_code

def compile_in_instruction(instruction: urcl.InstructionCSTNode, bits: Literal[32, 64]):
    
    registers = x86.get_registers(bits)
    x86_code = x86.ASMCode(0, [])
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
        
        x86_code.add_instructions_to_save_general_registers(registers)

        if isinstance(output_string, urcl.GeneralRegister):
            string_length_bytes = 4
            uint32_count = 1
            destination = convert_urcl_register_to_x86(output_string, bits)
            if isinstance(destination, Traceback):
                error = destination
                error.elaborate(f"Destination register {output_string} for OUT instruction is invalid")
                return error
            x86_code.add_instruction(x86.Mnemonic.PUSH, [destination.value])
        else:
            uint32_count = math.ceil(len(output_string) / 4)
            string_length_bytes = len(output_string)
            for u32 in bytes_to_stack_ints(output_string, 4):
                x86_code.add_instruction(x86.Mnemonic.PUSH, [u32])
        sysv.add_syscall_fwrite(x86_code, registers.sp, string_length_bytes, sysv.File.STDOUT, bits)
        x86_code.add_instruction(x86.Mnemonic.ADD, [registers.sp, uint32_count * 4])
        x86_code.add_instructions_to_restore_general_registers(registers)

    return x86_code

def compile_two_operand_arithmetic_instruction(instruction: urcl.InstructionCSTNode, bits: Literal[32, 64]):
    
    x86_code = x86.ASMCode(0, [])
    if instruction.mnemonic in urcl.TWO_OPERAND_ARITHMETIC_MNEMONICS:
        destination = get_x86_destination_register(instruction, bits)
        if isinstance(destination, Traceback):
            return destination
        urcl_source_operand = instruction.operands[len(instruction.operands) - 1]
        x86_source_operand = urcl_operand_to_x86(urcl_source_operand, bits)

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

def compile_three_operand_arithmetic_instruction(instruction: urcl.InstructionCSTNode, bits: Literal[32, 64]):
    
    x86_code = x86.ASMCode(0, [])
    if instruction.mnemonic in urcl.THREE_OPERAND_ARITHMETIC_MNEMONICS:
        destination = get_x86_destination_register(instruction, bits)
        if isinstance(destination, Traceback):
            return destination
        source_1 = urcl_operand_to_x86(instruction.operands[1], bits)
        source_2 = urcl_operand_to_x86(instruction.operands[2], bits)
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

def compile_push_instruction(instruction: urcl.InstructionCSTNode, bits: Literal[32, 64]):
    
    x86_code = x86.ASMCode(0, [])
    if instruction.mnemonic in [urcl.Mnemonic.PSH]:
        x86_source_operand = urcl_operand_to_x86(instruction.operands[0], bits)
        if isinstance(x86_source_operand, Traceback):
            return x86_source_operand
        x86_code.add_instruction(x86.Mnemonic.PUSH, [x86_source_operand.value])
    
    return x86_code

def compile_pop_instruction(instruction: urcl.InstructionCSTNode, bits: Literal[32, 64]):
    
    x86_code = x86.ASMCode(0, [])
    if instruction.mnemonic in [urcl.Mnemonic.POP]:
        x86_register = get_x86_destination_register(instruction, bits)
        if isinstance(x86_register, Traceback):
            return x86_register
        x86_code.add_instruction(x86.Mnemonic.POP, [x86_register])
    
    return x86_code

def compile_list_load_instruction(instruction: urcl.InstructionCSTNode, bits: Literal[32, 64]):
    
    x86_code = x86.ASMCode(0, [])
    if instruction.mnemonic in [urcl.Mnemonic.LOD, urcl.Mnemonic.LLOD]:
        x86_destination = get_x86_destination_register(instruction, bits)
        if isinstance(x86_destination, Traceback):
            error = x86_destination
            error.elaborate("LLOD instruction has invalid destination")
            return error
        source = urcl_operand_to_x86(instruction.operands[1], bits)
        if isinstance(source, Traceback):
            error = source
            error.elaborate(f"LLOD base address '{instruction.operands[1]}' is not valid")
            return error
        source.value
        #if isinstance(source.value, x86.EffectiveAddress):
        #    return Traceback.new(f"Source operand for load instruction must be a register, not {instruction.operands[1]}")
        if len(instruction.operands) == 3:
            index = instruction.operands[2].value
            if not isinstance(index, int):
                return Traceback.new("LLOD index must be an integer", line_number=instruction.operands[2].line_number, column_number=instruction.operands[2].column_number)
        else:
            index = 0
        if isinstance(source, Traceback):
            return source
        memory = x86.sum_into_effective_address([source.value, index], x86.PointerSize.DWORD)
        if isinstance(memory, Traceback):
            error = memory
            error.elaborate("LLOD target address cannot be translated to x86")
            return error
            
        x86_code.add_instruction(x86.Mnemonic.MOV, [x86_destination, memory])
    
    return x86_code

def compile_list_store_instruction(instruction: urcl.InstructionCSTNode, bits: Literal[32, 64]):
    
    x86_code = x86.ASMCode(0, [])
    if instruction.mnemonic in [urcl.Mnemonic.LSTR]:
        dest = urcl_operand_to_x86(instruction.operands[0], bits)
        source = urcl_operand_to_x86(instruction.operands[1], bits)
        index = urcl_operand_to_x86(instruction.operands[2], bits)
        if isinstance(source, Traceback):
            error = source
            error.elaborate(f"LSTR instruction got invalid source operand {instruction.operands[1]}")
            return error
        if isinstance(dest, Traceback):
            error = dest
            error.elaborate(f"LSTR instruction got invalid destination operand {instruction.operands[0]}")
            return error
        if isinstance(index, Traceback):
            error = index
            error.elaborate(f"LSTR index operand must be an int or register, not {instruction.operands[2]}")
            return index
        if not isinstance(index.value, (int, x86.Register)):
            return Traceback.new(f"LSTR index operand must be an int or register, not {instruction.operands[2]}")
        source = source.as_memory(scale=4, offset=index.value)
        dest = dest.value
            
        x86_code.add_instruction(x86.Mnemonic.MOV, [dest, source])
    
    return x86_code

def compile_load_instruction(instruction: urcl.InstructionCSTNode, bits: Literal[32, 64]):
    
    x86_code = x86.ASMCode(0, [])
    if instruction.mnemonic in [urcl.Mnemonic.LOD]:
        x86_register = get_x86_destination_register(instruction, bits)
        if isinstance(x86_register, Traceback):
            return x86_register
        source = urcl_operand_to_x86(instruction.operands[1], bits)
        if isinstance(source, Traceback):
            return source
        memory = source.as_memory(scale=4, offset=0)
        assert isinstance(x86_register, x86.Register)
        fixme = x86.sum_into_effective_address([x86.Label("urcl_m0"), x86_register], x86.PointerSize.DWORD)
        #print(fixme)
        assert not isinstance(fixme, Traceback)
        x86_code.add_instruction(x86.Mnemonic.MOV, [fixme, source.value])
    
    return x86_code

def compile_store_instruction(instruction: urcl.InstructionCSTNode, bits: Literal[32, 64]):
    
    x86_code = x86.ASMCode(0, [])
    if instruction.mnemonic in [urcl.Mnemonic.STR]:
        dest = urcl_operand_to_x86(instruction.operands[0], bits)
        source = urcl_operand_to_x86(instruction.operands[1], bits)
        if isinstance(source, Traceback):
            error = source
            error.elaborate(f"STR instruction got invalid source operand {instruction.operands[1]}")
            return error
        if isinstance(dest, Traceback):
            error = dest
            error.elaborate(f"STR instruction got invalid destination operand {instruction.operands[0]}")
            return error
        dest = dest.as_memory(scale=4, offset=0)
        source = source.value
            
        x86_code.add_instruction(x86.Mnemonic.MOV, [dest, source])
    
    return x86_code

def compile_multiply_instruction(instruction: urcl.InstructionCSTNode, bits: Literal[32, 64]):
    
    x86_code = x86.ASMCode(0, [])
    if bits == 64:
        multiplicand_1_register = x86.Register.RAX
        multiplicand_2_register = x86.Register.RDX
        result_register = x86.Register.RAX
    else:
        multiplicand_1_register = x86.Register.EAX
        multiplicand_2_register = x86.Register.EDX
        result_register = x86.Register.EAX
    
    if instruction.mnemonic in [urcl.Mnemonic.MLT]:
        destination = get_x86_destination_register(instruction, bits)
        if isinstance(destination, Traceback):
            return destination
        source_1 = urcl_operand_to_x86(instruction.operands[1], bits)
        source_2 = urcl_operand_to_x86(instruction.operands[2], bits)
        if isinstance(source_1, Traceback):
            return source_1
        if isinstance(source_2, Traceback):
            return source_2
        if destination != multiplicand_1_register:
            x86_code.add_instruction(x86.Mnemonic.PUSH, [multiplicand_1_register])
        if destination != multiplicand_2_register:
            x86_code.add_instruction(x86.Mnemonic.PUSH, [multiplicand_2_register])
        x86_code.add_move(multiplicand_1_register, source_1.value)
        
        x86_code.add_instruction(x86.Mnemonic.MUL, [source_2.value])
        x86_code.add_move(destination, result_register)
        
        if destination != multiplicand_2_register:
            x86_code.add_instruction(x86.Mnemonic.POP, [multiplicand_2_register])
        if destination != multiplicand_1_register:
            x86_code.add_instruction(x86.Mnemonic.POP, [multiplicand_1_register])
    
    return x86_code

@dataclass
class InstructionFamily:
    mnemonics: list[urcl.Mnemonic]
    compile: Callable[[urcl.InstructionCSTNode, Literal[32, 64]], x86.ASMCode | Traceback]
    operand_count: int

TRANSLATIONS: list[InstructionFamily] = [
    InstructionFamily(urcl.ZERO_OPERAND_MNEMONICS, compile_zero_operand_instruction, 0),
    InstructionFamily([urcl.Mnemonic.JMP, urcl.Mnemonic.CAL], compile_unconditional_jump_instruction, 1),
    InstructionFamily([urcl.Mnemonic.MLT], compile_multiply_instruction, 3),
    InstructionFamily(urcl.TWO_OPERAND_CONDITION_JUMP_MNEMONICS, compile_two_operand_jump_instruction, 2),
    InstructionFamily(urcl.THREE_OPERAND_CONDITION_JUMP_MNEMONICS, compile_three_operand_jump_instruction, 3),
    InstructionFamily([urcl.Mnemonic.DIV, urcl.Mnemonic.MOD], compile_division_instruction, 3),
    InstructionFamily([urcl.Mnemonic.OUT], compile_out_instruction, 2),
    InstructionFamily([urcl.Mnemonic.IN], compile_in_instruction, 2),
    InstructionFamily(urcl.TWO_OPERAND_ARITHMETIC_MNEMONICS, compile_two_operand_arithmetic_instruction, 2),
    InstructionFamily(urcl.THREE_OPERAND_ARITHMETIC_MNEMONICS, compile_three_operand_arithmetic_instruction, 3),
    InstructionFamily([urcl.Mnemonic.PSH], compile_push_instruction, 1),
    InstructionFamily([urcl.Mnemonic.POP], compile_pop_instruction, 1),
    InstructionFamily([urcl.Mnemonic.LLOD], compile_list_load_instruction, 3),
    InstructionFamily([urcl.Mnemonic.LSTR], compile_list_store_instruction, 3),
    InstructionFamily([urcl.Mnemonic.LOD], compile_load_instruction, 2),
    InstructionFamily([urcl.Mnemonic.STR], compile_store_instruction, 2)
]