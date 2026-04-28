import urcl
from error import Traceback
import x86
import math
from typing import Callable, Literal
import sysv
from dataclasses import dataclass

PARSING_ERROR_MESSAGE = "Could not parse urcl source"
NO_ERROR_EXIT_CODE = 0

@dataclass(frozen=True)
class InstructionInfo:
    urcl_jump_target: x86.Label | x86.Register | None
    x86_destination_register: x86.Register | x86.EffectiveAddress | x86.Immediate | None
    x86_sources: list[x86.Operand]
    urcl_nnemonic: urcl.Mnemonic
    x86_nnemonic: x86.Mnemonic | None
    urcl_port: urcl.PortType | None
    urcl_sources: list[urcl.OperandCSTNode]
    line_number: int
    column_number: int

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

def compile_zero_operand_instruction(bits: Literal[16, 32, 64], instruction_info: InstructionInfo):
    
    x86_code = x86.ASMCode(0, [])
    if instruction_info.urcl_nnemonic == urcl.Mnemonic.HLT:
        sysv.add_syscall_exit(x86_code, None, bits)
    elif instruction_info.x86_nnemonic:
        x86_code.add_instruction(instruction_info.x86_nnemonic, [])
    else:
        assert(False)
    
    return x86_code

def compile_unconditional_jump_instruction(entry_point: int, instruction_info: InstructionInfo):
    
    x86_code = x86.ASMCode(entry_point, [])
    if instruction_info.x86_nnemonic and instruction_info.urcl_jump_target:
        x86_code.add_instruction(instruction_info.x86_nnemonic, [x86.Label(instruction_info.urcl_jump_target.name)])
    
    return x86_code

def compile_two_operand_jump_instruction(bits: Literal[16, 32, 64], instruction_info: InstructionInfo) -> x86.ASMCode | Traceback:
    
    x86_code = x86.ASMCode(0, [])
    if instruction_info.urcl_nnemonic in urcl.TWO_OPERAND_CONDITION_JUMP_MNEMONICS and instruction_info.urcl_jump_target is not None:
        x86_code.add_instruction(x86.Mnemonic.CMP, [instruction_info.x86_sources[0].value, 0])
        if instruction_info.urcl_nnemonic == urcl.Mnemonic.BNZ:
            x86_code.add_instruction(x86.Mnemonic.JNE, [x86.Label(instruction_info.urcl_jump_target.name)])
        elif instruction_info.urcl_nnemonic == urcl.Mnemonic.BRZ:
            x86_code.add_instruction(x86.Mnemonic.JE, [x86.Label(instruction_info.urcl_jump_target.name)])
        elif instruction_info.urcl_nnemonic == urcl.Mnemonic.BRP:
            x86_code.add_instruction(x86.Mnemonic.JGE, [x86.Label(instruction_info.urcl_jump_target.name)])
    
    return x86_code

def compile_three_operand_jump_instruction(bits: Literal[16, 32, 64], instruction_info: InstructionInfo):
    
    x86_code = x86.ASMCode(0, [])
    if instruction_info.urcl_nnemonic in urcl.THREE_OPERAND_CONDITION_JUMP_MNEMONICS and instruction_info.urcl_jump_target is not None and instruction_info.x86_nnemonic:
        x86_code.add_instruction(x86.Mnemonic.CMP, [instruction_info.x86_sources[0].value, instruction_info.x86_sources[1].value])
        x86_code.add_instruction(instruction_info.x86_nnemonic, [x86.Label(instruction_info.urcl_jump_target.name)])
    
    return x86_code

# FIXME: x64 support
def compile_division_instruction(bits: Literal[16, 32, 64], instruction_info: InstructionInfo):
    
    x86_code = x86.ASMCode(0, [])
    if instruction_info.urcl_nnemonic in [urcl.Mnemonic.DIV, urcl.Mnemonic.MOD] and instruction_info.x86_destination_register is not None:
        x86_code = x86.generate_division_code(x86.Operand(instruction_info.x86_destination_register), instruction_info.x86_sources[0], instruction_info.x86_sources[1], bits, do_modulo=instruction_info.urcl_nnemonic==urcl.Mnemonic.MOD)

    return x86_code

def compile_inout_instruction(instruction_info: InstructionInfo, bits: Literal[16, 32, 64], mnemonic: urcl.Mnemonic, text_encoding: str):
    
    x86_code = x86.ASMCode(0, [])

    registers = x86.get_registers(bits)
    if instruction_info.urcl_port is None:
        return x86_code
    
    port_symbol = x86.Label(f"urcl_port_{instruction_info.urcl_port.name.lower()}_{mnemonic.name.lower()}")
   
    if (instruction_info.urcl_port.name == urcl.Port.TEXT.value.name) and (mnemonic == urcl.Mnemonic.OUT):
        
        urcl_source = instruction_info.urcl_sources[0].value
        if isinstance(urcl_source, str):
            # NOTE: outputting strings to %TEXT is non-standard
            output_string = urcl_source.encode(text_encoding)
        else:
            source = instruction_info.x86_sources[0].value
            if isinstance(source, int):
                output_string = chr(source).encode(text_encoding)
            elif isinstance(source, x86.Register):
                output_string = source
            else:
                return Traceback.new(f"{mnemonic.name} instruction operand 2 '{urcl_source}' cannot be output onto a port.", instruction_info.line_number, instruction_info.column_number)
        
        x86_code.add_instructions_to_save_general_registers(registers)
        if isinstance(output_string, x86.Register):
            string_length_bytes = bits // 8
            int_count = 1
            x86_code.add_instruction(x86.Mnemonic.PUSH, [output_string])
        else:
            int_count = math.ceil(len(output_string) / (4))
            string_length_bytes = len(output_string)
            for uint in bytes_to_stack_ints(output_string, 4):
                x86_code.add_instruction(x86.Mnemonic.PUSH, [uint])
        sysv.add_syscall_fwrite(x86_code, registers.sp, string_length_bytes, sysv.File.STDOUT, bits)
        x86_code.add_instruction(x86.Mnemonic.ADD, [registers.sp, int_count * 4])
        x86_code.add_instructions_to_restore_general_registers(registers)
    else:
        registers = x86.get_registers(bits)   
        x86_code.add_instruction(x86.Mnemonic.PUSH, [registers.a])
        x86_code.add_instruction(x86.Mnemonic.PUSH, [registers.c])
        x86_code.add_instruction(x86.Mnemonic.PUSH, [registers.d])
        use_arguments = instruction_info.urcl_nnemonic == urcl.Mnemonic.OUT
        use_return_value = instruction_info.urcl_nnemonic == urcl.Mnemonic.IN
        if use_arguments:
            x86_code.add_instruction(x86.Mnemonic.PUSH, [instruction_info.x86_sources[0].value])
        x86_code.add_instruction(x86.Mnemonic.CALL, [port_symbol])
        if use_return_value:
            assert(instruction_info.x86_destination_register is not None)
            x86_code.add_move(instruction_info.x86_destination_register, registers.a)
        if use_arguments:
            x86_code.add_instruction(x86.Mnemonic.POP, [registers.d])
        x86_code.add_instruction(x86.Mnemonic.POP, [registers.d])
        x86_code.add_instruction(x86.Mnemonic.POP, [registers.c])
        x86_code.add_instruction(x86.Mnemonic.POP, [registers.a])

    return x86_code

def compile_out_instruction(bits: Literal[16, 32, 64], instruction_info: InstructionInfo):
    
    return compile_inout_instruction(instruction_info, bits, urcl.Mnemonic.OUT, "utf-8")

def compile_in_instruction(bits: Literal[16, 32, 64], instruction_info: InstructionInfo):
    
    return compile_inout_instruction(instruction_info, bits, urcl.Mnemonic.IN, "utf-8")

def compile_two_operand_arithmetic_instruction(bits: Literal[16, 32, 64], instruction_info: InstructionInfo):
    
    x86_code = x86.ASMCode(0, [])
    if instruction_info.urcl_nnemonic in urcl.TWO_OPERAND_ARITHMETIC_MNEMONICS and instruction_info.x86_destination_register is not None:
        x86_code.add_move(instruction_info.x86_destination_register, instruction_info.x86_sources[0].value)
        if instruction_info.x86_nnemonic:
            x86_code.add_instruction(instruction_info.x86_nnemonic, [instruction_info.x86_destination_register])
            return x86_code
        if instruction_info.urcl_nnemonic in [urcl.Mnemonic.MOV, urcl.Mnemonic.IMM]:
            pass # Move does not perform a calculation, consider it NOP
        elif instruction_info.urcl_nnemonic == urcl.Mnemonic.LSH:
            x86_code.add_instruction(x86.Mnemonic.ROL, [instruction_info.x86_destination_register])
            x86_code.add_instruction(x86.Mnemonic.AND, [instruction_info.x86_destination_register, (2**(bits-1) - 1) << 1])
        elif instruction_info.urcl_nnemonic == urcl.Mnemonic.RSH:
            x86_code.add_instruction(x86.Mnemonic.ROL, [instruction_info.x86_destination_register])
            x86_code.add_instruction(x86.Mnemonic.AND, [instruction_info.x86_destination_register, 2**(bits-1) - 1])
    
    return x86_code

def compile_three_operand_arithmetic_instruction(bits: Literal[16, 32, 64], instruction_info: InstructionInfo):
    
    x86_code = x86.ASMCode(0, [])
    if instruction_info.x86_destination_register is None:
        return x86_code
    
    x86_code.add_move(instruction_info.x86_destination_register, instruction_info.x86_sources[0].value)
    
    if instruction_info.urcl_nnemonic in [urcl.Mnemonic.BSL, urcl.Mnemonic.BSR]:
        
        if instruction_info.urcl_nnemonic == urcl.Mnemonic.BSL:
            opcode = x86.Mnemonic.ROL
            bit_mask = (2**(bits-1) - 1) << 1
        else:
            opcode = x86.Mnemonic.ROR
            bit_mask = 2**(bits-1) - 1
        
        if not isinstance(instruction_info.x86_sources[1].value, int):
            return Traceback.new(f"{instruction_info.urcl_nnemonic.name.upper()} instruction only supports shifting by a constant number of bits")
        for _ in range(instruction_info.x86_sources[1].value):
            x86_code.add_instruction(opcode, [instruction_info.x86_destination_register])
            x86_code.add_instruction(x86.Mnemonic.AND, [instruction_info.x86_destination_register, bit_mask])

    elif instruction_info.urcl_nnemonic in urcl.THREE_OPERAND_ARITHMETIC_MNEMONICS:
        if instruction_info.x86_destination_register != instruction_info.x86_sources[0]:
            x86_code.add_move(instruction_info.x86_destination_register, instruction_info.x86_sources[0].value)
        if instruction_info.x86_nnemonic:
            x86_code.add_instruction(instruction_info.x86_nnemonic, [instruction_info.x86_destination_register, instruction_info.x86_sources[1].value])
    else:
        ...
    
    return x86_code

def compile_push_instruction(bits: Literal[16, 32, 64], instruction_info: InstructionInfo):
    
    x86_code = x86.ASMCode(0, [])
    if instruction_info.urcl_nnemonic in [urcl.Mnemonic.PSH]:
        x86_code.add_instruction(x86.Mnemonic.PUSH, [instruction_info.x86_sources[0].value])
    
    return x86_code

def compile_pop_instruction(bits: Literal[16, 32, 64], instruction_info: InstructionInfo):
    
    x86_code = x86.ASMCode(0, [])
    if instruction_info.urcl_nnemonic in [urcl.Mnemonic.POP] and instruction_info.x86_destination_register is not None:
        x86_code.add_instruction(x86.Mnemonic.POP, [instruction_info.x86_destination_register])
    
    return x86_code

def compile_list_load_instruction(bits: Literal[16, 32, 64], instruction_info: InstructionInfo):
    
    x86_code = x86.ASMCode(0, [])
    if len(instruction_info.x86_sources) != 2:
        return x86_code 
    pointer = instruction_info.x86_sources[0].value
    index = instruction_info.x86_sources[1].value
    if isinstance(pointer, (x86.Register, int)) and isinstance(index, x86.Label):
        tmp = pointer
        pointer = index
        index = tmp
    if instruction_info.urcl_nnemonic in [urcl.Mnemonic.LOD, urcl.Mnemonic.LLOD] and instruction_info.x86_destination_register is not None:
        #if len(instruction_info.x86_sources) == 2:
        #    if not isinstance(index, (int, x86.Register)):
        #        return Traceback.new("LLOD index must be an integer or register", line_number=instruction_info.urcl_sources[1].line_number, column_number=instruction_info.urcl_sources[1].column_number)
        #else:
        #    index = 0
        
        if isinstance(pointer, x86.EffectiveAddress):
            return Traceback.new(f"Source operand for load instruction must be a register, not {pointer}")
        if isinstance(index, x86.EffectiveAddress):
            return Traceback.new(f"Offset operand for load instruction must be a register, not {index}")
        address_parts: list[int | x86.Label | x86.Register] = [pointer, index]
        if isinstance(pointer, x86.Register) and pointer not in [x86.Register.BP, x86.Register.SP, x86.Register.EBP, x86.Register.ESP]:
            address_parts.append(x86.Label("urcl_m0"))
        effective_address = x86.sum_into_effective_address(address_parts, x86.PointerSize.from_bits(bits))
        if isinstance(effective_address, Traceback):
            error = effective_address
            error.elaborate(f"{instruction_info.urcl_nnemonic.name} target address cannot be translated to x86")
            return error
            
        x86_code.add_instruction(x86.Mnemonic.MOV, [instruction_info.x86_destination_register, effective_address])
    
    return x86_code

def compile_list_store_instruction(bits: Literal[16, 32, 64], instruction_info: InstructionInfo):
    
    x86_code = x86.ASMCode(0, [])
    if instruction_info.urcl_nnemonic in [urcl.Mnemonic.LSTR] and instruction_info.x86_destination_register is not None:
        destination = instruction_info.x86_destination_register
        source = instruction_info.x86_sources[0]
        index = instruction_info.x86_sources[1]
        assert(not isinstance(index.value, x86.EffectiveAddress))
        if isinstance(destination, x86.EffectiveAddress):
            effective_address = destination
        else:
            memory = [destination, index.value]
            if destination in [x86.get_registers(bits)]:
                memory.append(x86.Label("urcl_m0"))
            effective_address = x86.sum_into_effective_address(memory, x86.PointerSize.from_bits(bits))
        if isinstance(effective_address, Traceback):
            error = effective_address
            error.elaborate(f"{instruction_info.urcl_nnemonic.name} destination address cannot be translated to x86")
            return error
        x86_code.add_instruction(x86.Mnemonic.MOV, [effective_address, source.value])
    
    return x86_code

def compile_load_instruction(bits: Literal[16, 32, 64], instruction_info: InstructionInfo):
    
    x86_code = x86.ASMCode(0, [])
    if instruction_info.urcl_nnemonic in [urcl.Mnemonic.LOD] and instruction_info.x86_destination_register is not None:
        source = instruction_info.x86_sources[0].value
        if isinstance(source, x86.EffectiveAddress):
            effective_address = source
        else:
            assert(not isinstance(instruction_info.x86_sources[0].value, x86.EffectiveAddress))
            address_parts = [instruction_info.x86_sources[0].value]
            if isinstance(instruction_info.x86_sources[0].value, x86.Register) and instruction_info.x86_sources[0].value not in [x86.Register.BP, x86.Register.SP, x86.Register.EBP, x86.Register.ESP]:
                address_parts.append(x86.Label("urcl_m0"))
            effective_address = x86.sum_into_effective_address(address_parts, x86.PointerSize.from_bits(bits))
        if isinstance(effective_address, Traceback):
            error = effective_address
            error.elaborate(f"{instruction_info.urcl_nnemonic.name} source address {instruction_info.urcl_sources[0].value} cannot be translated to x86", line_number=instruction_info.urcl_sources[0].line_number, column_number=instruction_info.urcl_sources[0].column_number)
            return error
        x86_code.add_instruction(x86.Mnemonic.MOV, [instruction_info.x86_destination_register, effective_address])
    
    return x86_code

def compile_store_instruction(bits: Literal[16, 32, 64], instruction_info: InstructionInfo):
    
    x86_code = x86.ASMCode(0, [])
    if instruction_info.urcl_nnemonic in [urcl.Mnemonic.STR] and instruction_info.x86_destination_register is not None:
        destination = instruction_info.x86_destination_register
        source = instruction_info.x86_sources[0]
        if isinstance(destination, x86.EffectiveAddress):
            effective_address = destination
        else:
            memory = [destination]
            if isinstance(destination, x86.Register):
                memory.append(x86.Label("urcl_m0"))
            effective_address = x86.sum_into_effective_address(memory, x86.PointerSize.from_bits(bits))
        if isinstance(effective_address, Traceback):
            error = effective_address
            error.elaborate(f"{instruction_info.urcl_nnemonic.name} destination address cannot be translated to x86")
            return error
        x86_code.add_instruction(x86.Mnemonic.MOV, [effective_address, source.value])
    
    return x86_code

def compile_multiply_instruction(bits: Literal[16, 32, 64], instruction_info: InstructionInfo):
    
    x86_code = x86.ASMCode(0, [])
    if bits == 64:
        multiplicand_1_register = x86.Register.RAX
        multiplicand_2_register = x86.Register.RDX
        result_register = x86.Register.RAX
    else:
        multiplicand_1_register = x86.Register.EAX
        multiplicand_2_register = x86.Register.EDX
        result_register = x86.Register.EAX
    
    if instruction_info.urcl_nnemonic in [urcl.Mnemonic.MLT] and instruction_info.x86_destination_register is not None:
        if instruction_info.x86_destination_register != multiplicand_1_register:
            x86_code.add_instruction(x86.Mnemonic.PUSH, [multiplicand_1_register])
        if instruction_info.x86_destination_register != multiplicand_2_register:
            x86_code.add_instruction(x86.Mnemonic.PUSH, [multiplicand_2_register])
        x86_code.add_move(multiplicand_1_register, instruction_info.x86_sources[0].value)
        
        x86_code.add_instruction(x86.Mnemonic.MUL, [instruction_info.x86_sources[1].value])
        x86_code.add_move(instruction_info.x86_destination_register, result_register)
        
        if instruction_info.x86_destination_register != multiplicand_2_register:
            x86_code.add_instruction(x86.Mnemonic.POP, [multiplicand_2_register])
        if instruction_info.x86_destination_register != multiplicand_1_register:
            x86_code.add_instruction(x86.Mnemonic.POP, [multiplicand_1_register])
    
    return x86_code

@dataclass
class InstructionFamily:
    mnemonics: list[urcl.Mnemonic]
    compile: Callable[[Literal[16, 32, 64], InstructionInfo], x86.ASMCode | Traceback]
    operand_count: int
    requires_jump_target: bool
    writes_to_register: bool
    required_sources: int
    source_start_index: int

TRANSLATIONS: list[InstructionFamily] = [
    InstructionFamily(
        urcl.ZERO_OPERAND_MNEMONICS,
        compile_zero_operand_instruction,
        0,
        requires_jump_target = False,
        writes_to_register = False,
        required_sources = 0,
        source_start_index = 1
    ),
    InstructionFamily(
        [urcl.Mnemonic.JMP, urcl.Mnemonic.CAL],
        compile_unconditional_jump_instruction,
        1,
        requires_jump_target = False,
        writes_to_register = False,
        required_sources = 0,
        source_start_index = 1
    ),
    InstructionFamily(
        [urcl.Mnemonic.MLT],
        compile_multiply_instruction, 
        3, 
        requires_jump_target = False,
        writes_to_register = False, 
        required_sources = 2,
        source_start_index = 1
    ),
    InstructionFamily(
        urcl.TWO_OPERAND_CONDITION_JUMP_MNEMONICS,
        compile_two_operand_jump_instruction, 2,
        requires_jump_target = False, 
        writes_to_register = False,
        required_sources = 1, 
        source_start_index = 1
    ),
    InstructionFamily(
        urcl.THREE_OPERAND_CONDITION_JUMP_MNEMONICS, 
        compile_three_operand_jump_instruction, 
        3,
        requires_jump_target = False, 
        writes_to_register = False,
        required_sources = 2,
        source_start_index = 1
    ),
    InstructionFamily(
        [urcl.Mnemonic.DIV, urcl.Mnemonic.MOD],
        compile_division_instruction,
        3, 
        requires_jump_target = False,
        writes_to_register = False,
        required_sources = 2, 
        source_start_index = 1
    ),
    InstructionFamily(
        [urcl.Mnemonic.OUT],
        compile_out_instruction,
        2,
        requires_jump_target = False, 
        writes_to_register = False, 
        required_sources = 1,
        source_start_index = 1
    ),
    InstructionFamily(
        [urcl.Mnemonic.IN],
        compile_in_instruction,
        2,
        requires_jump_target = False,
        writes_to_register = False,
        required_sources = 1, 
        source_start_index = 1
    ),
    InstructionFamily(
        urcl.TWO_OPERAND_ARITHMETIC_MNEMONICS,
        compile_two_operand_arithmetic_instruction, 
        2,
        requires_jump_target = False, 
        writes_to_register = False,
        required_sources = 1,
        source_start_index = 1
    ),
    InstructionFamily(
        urcl.THREE_OPERAND_ARITHMETIC_MNEMONICS,
        compile_three_operand_arithmetic_instruction,
        3, 
        requires_jump_target = False, 
        writes_to_register = False, 
        required_sources = 2, 
        source_start_index = 1
    ),
    InstructionFamily(
        [urcl.Mnemonic.PSH], 
        compile_push_instruction, 
        1,
        requires_jump_target = False,
        writes_to_register = False, 
        required_sources = 1,
        source_start_index = 0
    ),
    InstructionFamily(
        [urcl.Mnemonic.POP], 
        compile_pop_instruction, 
        1,
        requires_jump_target = False,
        writes_to_register = False, 
        required_sources = 0,
        source_start_index = 1
    ),
    InstructionFamily(
        [urcl.Mnemonic.LLOD],
        compile_list_load_instruction, 
        3,
        requires_jump_target = False,
        writes_to_register = False, 
        required_sources = 2,
        source_start_index = 1
    ),
    InstructionFamily(
        [urcl.Mnemonic.LSTR],
        compile_list_store_instruction, 
        3,
        requires_jump_target = False,
        writes_to_register = False,
        required_sources = 2, 
        source_start_index = 1
    ),
    InstructionFamily(
        [urcl.Mnemonic.LOD], 
        compile_load_instruction,
        2, 
        requires_jump_target = False,
        writes_to_register = False,
        required_sources = 1, 
        source_start_index = 1
    ),
    InstructionFamily(
        [urcl.Mnemonic.STR], 
        compile_store_instruction,
        2, 
        requires_jump_target = False,
        writes_to_register = False,
        required_sources = 1,
        source_start_index = 1
    )
]