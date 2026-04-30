from dataclasses import dataclass
from typing import Literal

import urcl
import x86
from error import Traceback
import translation.reg2reg as reg2reg
import translation.instructioninfo as instructioninfo

def urcl_operand_to_x86(operand: urcl.urclcst.OperandCSTNode, bits: Literal[16, 32, 64]) -> x86.Operand | Traceback:

    if isinstance(operand.value, urcl.urclcst.Label):
        return x86.Operand(x86.Label(operand.value.name))
    elif isinstance(operand.value, (urcl.GeneralRegister, urcl.BasePointer, urcl.StackPointer)):
        register = reg2reg.convert_urcl_register_to_x86(operand.value, bits)
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
    elif isinstance(operand.value, urcl.PortType):
        return x86.Operand(operand.value.id)
    elif isinstance(operand.value, urcl.DefinedImmediate):
        return x86.Operand(0) # FIXME
    else:
        return Traceback.new(f"URCL operand {operand} has no x86/x64 equivalent")

def get_jump_target(instruction: urcl.InstructionCSTNode, bits) -> x86.Label | x86.Register | Traceback:

    if not instruction.operands:
        return Traceback.new(f"{instruction.mnemonic.name.upper()} instruction is missing operands, expected a label or register", line_number=instruction.line_number, column_number=instruction.column_number)
    destination = urcl_operand_to_x86(instruction.operands[0], bits)
    if isinstance(destination, Traceback):
        error = destination
        error.elaborate(f"Jump target for instruction {instruction.mnemonic.name.upper()} is invalid")
        return error
    if not isinstance(destination.value, (x86.Label, x86.Register)):
        return Traceback.new(f"{instruction.mnemonic.name.upper()} instruction expected first operand to be a label or register", line_number=instruction.operands[0].line_number, column_number=instruction.operands[0].column_number)
    
    return destination.value

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

def get_instruction_info(instruction: urcl.InstructionCSTNode, bits: Literal[16, 32, 64], requires_jump_target: bool=False, writes_to_register: bool=False, required_sources: int=0, source_start_index: int=1) -> instructioninfo.InstructionInfo | Traceback:

    urcl_jump_target = get_jump_target(instruction, bits)
    if isinstance(urcl_jump_target, Traceback):
        error = urcl_jump_target
        urcl_jump_target = None
        if requires_jump_target:
            return error
    
    x86_destination_register = reg2reg.get_x86_destination_register(instruction, bits)
    if isinstance(x86_destination_register, Traceback):
        error = x86_destination_register
        x86_destination_register = None
        if writes_to_register:
            return error
    
    if required_sources and len(instruction.operands) - source_start_index < required_sources:
        return Traceback.new(f"Instruction {instruction.mnemonic.name.upper()} requires {required_sources} data sources, only {len(instruction.operands) - 1} were found")
    
    sources = []
    for operand in instruction.operands[source_start_index:]:
        source = urcl_operand_to_x86(operand, bits)
        if isinstance(source, Traceback):
            return source
        sources.append(source)

    port_locations: dict[urcl.Mnemonic, int] = {
        urcl.Mnemonic.OUT: 0,
        urcl.Mnemonic.IN: 1
    }
    
    port = None
    port_index = port_locations.get(instruction.mnemonic)
    port_is_required = port_index is not None
    if port_is_required:
        if len(instruction.operands) <= port_index:
            return Traceback.new(f"Instruction {instruction.mnemonic.name.upper()} requires a port argument, but not enough operands were provided")
        operand = instruction.operands[port_index]
        if isinstance(operand.value, urcl.PortType):
            port = operand.value
        elif isinstance(operand.value, int):
            port = urcl.PortType(operand.value, "UNKNOWN")
        else:
            pass
    
    if port_is_required and port is None:
        return Traceback.new(f"Instruction {instruction.mnemonic.name.upper()} requires a port argument, but one was not provided")


    return instructioninfo.InstructionInfo(urcl_jump_target, x86_destination_register, sources, instruction.mnemonic, reg2reg.URCL_X86_MNEMONIC_MAPPING.get(instruction.mnemonic), port, instruction.operands[source_start_index:], instruction.line_number, instruction.column_number)
