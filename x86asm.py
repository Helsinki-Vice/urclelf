import enum
from dataclasses import dataclass
import struct

from x86 import Register, X86Instruction, Opcode, ModRegRM, AddressingMode, Mnemonic, BRANCH_MNEMONICS
from error import Traceback, Message

class OperandEncodingFormat(enum.Enum):
    OPCODE = enum.auto()
    MODREGRM_REGISTER_FIELD = enum.auto()
    MODREGRM_RM_FIELD = enum.auto()
    IMMEDIATE_8_BITS = enum.auto()
    IMMEDIATE_32_BITS = enum.auto()

@dataclass
class Label:
    name: str

    def __str__(self) -> str:
        return self.name

class Operand:

    def __init__(self, value: "int | Register | Label") -> None:

        self.value = value
    
    def get_register_size(self):

        if isinstance(self.value, Register):
            return self.value.value.size
        
    def __str__(self) -> str:
        return str(self.value)

class X86ASMInstruction:

    def __init__(self, mnemonic: Mnemonic, operands: list[Operand], addressing_mode: AddressingMode) -> None:
        
        self.mnemonic = mnemonic
        self.operands = operands
        self.addressing_mode = addressing_mode
    
    def __str__(self) -> str:

        result = str(self.mnemonic.value)
        operands = ", ".join([str(operand) for operand in self.operands])
        if operands:
            result += " " + str(operands)
        return f"{self.mnemonic.value} {operands}"

@dataclass
class InstructionEncoding:

    opcode: Opcode
    mnemonic: Mnemonic
    opcode_extention: int
    operand_format: list[OperandEncodingFormat]

    def encode(self, instruction: X86ASMInstruction) -> "X86Instruction | None":

        if instruction.mnemonic != self.mnemonic:
            return None
        if len(instruction.operands) != len(self.operand_format):
            return None
        
        mod_field = instruction.addressing_mode
        reg_field = None
        rm_field = None
        if self.opcode.is_immediate():
            if self.opcode_extention:
                reg_field = self.opcode_extention
        immediate = bytes()

        for operand_index in range(len(instruction.operands)):
            format = self.operand_format[operand_index]
            operand = instruction.operands[operand_index]
            if format == OperandEncodingFormat.OPCODE:
                if not isinstance(operand.value, Register):
                    return None
                if operand.value.value.code != self.opcode.value[-1] & 0b00000111:
                    return None
            elif format == OperandEncodingFormat.MODREGRM_REGISTER_FIELD:
                if operand.get_register_size() != self.opcode.get_operand_size():
                    return None
                reg_field = operand.value
            elif format == OperandEncodingFormat.MODREGRM_RM_FIELD:
                if operand.get_register_size() != self.opcode.get_operand_size():
                    return None
                rm_field = operand.value
            elif format == OperandEncodingFormat.IMMEDIATE_8_BITS:
                if isinstance(operand.value, Register):
                    return None
                    value: int = operand.value.value.code % 256
                elif isinstance(operand.value, int):
                    value = operand.value % 256
                    immediate = struct.pack("I", value)
                else:
                    return None
                immediate = struct.pack("B", value)
            elif format == OperandEncodingFormat.IMMEDIATE_32_BITS:
                if isinstance(operand.value, Register):
                    return None
                    value: int = operand.value.value.code % 256
                elif isinstance(operand.value, int):
                    value = operand.value % 2**32
                else:
                    value = 0
                immediate = struct.pack("I", value)
            else:
                return None
        if isinstance(reg_field, Register):
            reg_field = int(reg_field.value.code.value)
        if isinstance(rm_field, Register):
            rm_field = int(rm_field.value.code.value)
        if isinstance(reg_field, Label):
            return None
        if isinstance(rm_field, Label):
            return None
        if reg_field is not None or rm_field is not None:
            if reg_field is None:
                reg_field = 0
            if rm_field is None:
                rm_field = 0
            mod_reg_rm = ModRegRM(mod_field, reg_field, rm_field)
        else:
            mod_reg_rm = None
        return X86Instruction(None, self.opcode, mod_reg_rm, bytes(), immediate)

#TODO: smaller/better instruction encodings
INSTRUCTION_FORMATS = [
    InstructionEncoding(Opcode(bytes([0x00])), Mnemonic.ADD, 0, [OperandEncodingFormat.MODREGRM_RM_FIELD, OperandEncodingFormat.MODREGRM_REGISTER_FIELD]),
    InstructionEncoding(Opcode(bytes([0x01])), Mnemonic.ADD, 0, [OperandEncodingFormat.MODREGRM_RM_FIELD, OperandEncodingFormat.MODREGRM_REGISTER_FIELD]),
    InstructionEncoding(Opcode(bytes([0x50])), Mnemonic.PUSH, 0, [OperandEncodingFormat.OPCODE]),
    InstructionEncoding(Opcode(bytes([0x51])), Mnemonic.PUSH, 0, [OperandEncodingFormat.OPCODE]),
    InstructionEncoding(Opcode(bytes([0x52])), Mnemonic.PUSH, 0, [OperandEncodingFormat.OPCODE]),
    InstructionEncoding(Opcode(bytes([0x53])), Mnemonic.PUSH, 0, [OperandEncodingFormat.OPCODE]),
    InstructionEncoding(Opcode(bytes([0x54])), Mnemonic.PUSH, 0, [OperandEncodingFormat.OPCODE]),
    InstructionEncoding(Opcode(bytes([0x58])), Mnemonic.POP, 0, [OperandEncodingFormat.OPCODE]),
    InstructionEncoding(Opcode(bytes([0x59])), Mnemonic.POP, 0, [OperandEncodingFormat.OPCODE]),
    InstructionEncoding(Opcode(bytes([0x5a])), Mnemonic.POP, 0, [OperandEncodingFormat.OPCODE]),
    InstructionEncoding(Opcode(bytes([0x5b])), Mnemonic.POP, 0, [OperandEncodingFormat.OPCODE]),
    InstructionEncoding(Opcode(bytes([0x5c])), Mnemonic.POP, 0, [OperandEncodingFormat.OPCODE]),
    InstructionEncoding(Opcode(bytes([0x5d])), Mnemonic.POP, 0, [OperandEncodingFormat.OPCODE]),
    InstructionEncoding(Opcode(bytes([0x5e])), Mnemonic.POP, 0, [OperandEncodingFormat.OPCODE]),
    InstructionEncoding(Opcode(bytes([0x5f])), Mnemonic.POP, 0, [OperandEncodingFormat.OPCODE]),
    InstructionEncoding(Opcode(bytes([0x60])), Mnemonic.PUSHAD, 1, []),
    InstructionEncoding(Opcode(bytes([0x61])), Mnemonic.POPAD, 3, []),
    InstructionEncoding(Opcode(bytes([0x68])), Mnemonic.PUSH, 0, [OperandEncodingFormat.IMMEDIATE_32_BITS]),
    InstructionEncoding(Opcode(bytes([0x6a])), Mnemonic.PUSH, 0, [OperandEncodingFormat.IMMEDIATE_8_BITS]),
    InstructionEncoding(Opcode(bytes([0x80])), Mnemonic.ADD, 0, [OperandEncodingFormat.MODREGRM_RM_FIELD, OperandEncodingFormat.IMMEDIATE_8_BITS]),
    InstructionEncoding(Opcode(bytes([0x81])), Mnemonic.CMP, 7, [OperandEncodingFormat.MODREGRM_RM_FIELD, OperandEncodingFormat.IMMEDIATE_32_BITS]),
    InstructionEncoding(Opcode(bytes([0x81])), Mnemonic.ADD, 0, [OperandEncodingFormat.MODREGRM_RM_FIELD, OperandEncodingFormat.IMMEDIATE_32_BITS]),
    InstructionEncoding(Opcode(bytes([0x83])), Mnemonic.SUB, 5, [OperandEncodingFormat.MODREGRM_RM_FIELD, OperandEncodingFormat.IMMEDIATE_8_BITS]),
    InstructionEncoding(Opcode(bytes([0x88])), Mnemonic.MOV, 0, [OperandEncodingFormat.MODREGRM_RM_FIELD, OperandEncodingFormat.MODREGRM_REGISTER_FIELD]),
    InstructionEncoding(Opcode(bytes([0x89])), Mnemonic.MOV, 0, [OperandEncodingFormat.MODREGRM_RM_FIELD, OperandEncodingFormat.MODREGRM_REGISTER_FIELD]),
    InstructionEncoding(Opcode(bytes([0x90])), Mnemonic.NOP, 0, []),
    InstructionEncoding(Opcode(bytes([0xc3])), Mnemonic.RETN, 0, []),
    InstructionEncoding(Opcode(bytes([0xc6])), Mnemonic.MOV, 0, [OperandEncodingFormat.MODREGRM_RM_FIELD, OperandEncodingFormat.IMMEDIATE_8_BITS]),
    InstructionEncoding(Opcode(bytes([0xc7])), Mnemonic.MOV, 0, [OperandEncodingFormat.MODREGRM_RM_FIELD, OperandEncodingFormat.IMMEDIATE_32_BITS]),
    InstructionEncoding(Opcode(bytes([0xcd])), Mnemonic.INT, 0, [OperandEncodingFormat.IMMEDIATE_8_BITS]),
    InstructionEncoding(Opcode(bytes([0xe8])), Mnemonic.CALL, 0, [OperandEncodingFormat.IMMEDIATE_32_BITS]),
    InstructionEncoding(Opcode(bytes([0xe9])), Mnemonic.JMP, 0, [OperandEncodingFormat.IMMEDIATE_32_BITS]),
    InstructionEncoding(Opcode(bytes([0xf7])), Mnemonic.NEG, 3, [OperandEncodingFormat.MODREGRM_RM_FIELD]),
    InstructionEncoding(Opcode(bytes([0xf7])), Mnemonic.DIV, 6, [OperandEncodingFormat.MODREGRM_RM_FIELD]),
    InstructionEncoding(Opcode(bytes([0xfe])), Mnemonic.INC, 0, [OperandEncodingFormat.IMMEDIATE_8_BITS]),
    InstructionEncoding(Opcode(bytes([0xfe])), Mnemonic.DEC, 1, [OperandEncodingFormat.IMMEDIATE_8_BITS]),
    InstructionEncoding(Opcode(bytes([0xff])), Mnemonic.INC, 0, [OperandEncodingFormat.IMMEDIATE_32_BITS]),
    InstructionEncoding(Opcode(bytes([0xff])), Mnemonic.DEC, 1, [OperandEncodingFormat.IMMEDIATE_32_BITS]),
    InstructionEncoding(Opcode(bytes([0x0f, 0x84])), Mnemonic.JZ, 0, [OperandEncodingFormat.IMMEDIATE_32_BITS]),
    InstructionEncoding(Opcode(bytes([0x0f, 0x85])), Mnemonic.JNZ, 0, [OperandEncodingFormat.IMMEDIATE_32_BITS]),
    InstructionEncoding(Opcode(bytes([0x0f, 0x86])), Mnemonic.JBE, 0, [OperandEncodingFormat.IMMEDIATE_32_BITS]),
    InstructionEncoding(Opcode(bytes([0x0f, 0x87])), Mnemonic.JNBE, 0, [OperandEncodingFormat.IMMEDIATE_32_BITS]),
    InstructionEncoding(Opcode(bytes([0x0f, 0x8d])), Mnemonic.JGE, 0, [OperandEncodingFormat.IMMEDIATE_32_BITS])
]

class Program:

    def __init__(self, code: "list[X86ASMInstruction | Label]", entry_point: int) -> None:

        self.code = code
        self.entry_point = entry_point
        #self.instruction_addresses: list[int] = []
        #self.instruction_sizes: list[int] = []
        #self.current_address = self.entry_point

    def assemble(self):

        instruction_addresses: list[int] = []
        instruction_sizes: list[int] = []
        label_addresses: dict[str, int] = {}
        current_address = self.entry_point
        machine_code: list[X86Instruction] = []

        #first pass: resolve labels
        for instruction in self.code:
            if isinstance(instruction, Label):
                label_addresses.update({instruction.name: current_address})
                instruction_addresses.append(current_address)
                instruction_sizes.append(0)
                continue
            machine_instruction = encode(instruction)
            if not isinstance(machine_instruction, X86Instruction):
                machine_instruction.push(Message(f"Unable to encode instruction '{instruction}'", 0, 0))
                return machine_instruction
            machine_code_bytes = bytes(machine_instruction)
            instruction_addresses.append(current_address)
            current_address += len(machine_code_bytes)
            instruction_sizes.append(len(machine_code_bytes))
        
        #second pass: assemble
        for instruction_index, instruction in enumerate(self.code):
            if isinstance(instruction, Label):
                continue
            for operand_index, operand in enumerate(instruction.operands):
                if isinstance(operand.value, Label):
                    label_address = label_addresses.get(operand.value.name)
                    if not label_address:
                        return Traceback([], [Message(f"Cannot resolve label '{operand.value.name}'", 0, 0)])
                    if instruction.mnemonic in BRANCH_MNEMONICS and operand_index == 0:
                        operand.value = label_address - instruction_addresses[instruction_index] - instruction_sizes[instruction_index]
                    else:
                        operand.value = label_address
            machine_instruction = encode(instruction)
            if not isinstance(machine_instruction, X86Instruction):
                machine_instruction.push(Message(f"Unable to encode instruction '{instruction}'", 0, 0))
                return machine_instruction
            machine_code_bytes = bytes(machine_instruction)
            instruction_addresses.append(current_address)
            current_address += len(machine_code_bytes)
            instruction_sizes.append(len(machine_code_bytes))
            machine_code.append(machine_instruction)
        
        return machine_code

    def add_instruction(self, mnemonic: Mnemonic, operands: "list[int | Register | Label]", addressing_mode=AddressingMode.DIRECT):

        instruction = X86ASMInstruction(mnemonic, [], addressing_mode)
        for operand in operands:
            instruction.operands.append(Operand(operand))
        self.code.append(instruction)
    """
    def resolve_labels(self):

        for instruction_index, instruction in enumerate(self.code):
            for operand_index, operand in enumerate(instruction.operands):
                if isinstance(operand.value, Label):
                    label_address = self.labels.get(operand.value.name)
                    if not label_address:
                        return Traceback([], [Message(f"Cannot resolve label '{operand.value.name}'", 0, 0)])
                    operand.value = label_address - self.instruction_addresses[instruction_index] - self.instruction_sizes[instruction_index]
"""
def encode(instruction: X86ASMInstruction) -> "X86Instruction | Traceback":

    for format in INSTRUCTION_FORMATS:
        result = format.encode(instruction)
        if result:
            return result
    print("'" + str(instruction.mnemonic) + "'")
    return Traceback([Message(f"Cannot encode instruction '{instruction}'", 0, 0)], [])

def main():
    "[1-11101-1-1][11-011-000]"
    #print(bytes([0b11110111, 0b11011000]).hex())
    ins = encode(X86ASMInstruction(Mnemonic.DIV, [Operand(Register.EDX)], AddressingMode.INDIRECT))
    if isinstance(ins, X86Instruction):
        print(bytes(ins).hex())
        print(ins.mod_reg_rm)
    else:
        print(ins)

if __name__ == "__main__":
    main()