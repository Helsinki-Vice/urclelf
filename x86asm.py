"This module provides types for respresenting x86 assembly and uses the x86 module to convert ASM to x86 machine code."
import enum
from dataclasses import dataclass
import struct

from x86 import Register, X86Instruction, Opcode, ModRegRM, AddressingMode
from error import Traceback, Message

class OperandEncodingFormat(enum.Enum):
    OPCODE = enum.auto()
    MODREGRM_REGISTER_FIELD = enum.auto()
    MODREGRM_RM_FIELD = enum.auto()
    IMMEDIATE_8_BITS = enum.auto()
    IMMEDIATE_32_BITS = enum.auto()

class Mnemonic(enum.Enum):
    ADD = "add"
    AND = "and"
    CALL = "call"
    CMP = "cmp"
    DEC = "dec"
    DIV = "div"
    IDIV = "idiv"
    INC = "inc"
    IMUL = "imul"
    INT = "int"
    JBE = "jbe"
    JGE = "jge"
    JMP = "jmp"
    JNZ = "jnz"
    JNBE = "jnbe"
    JO = "jo"
    JZ  = "jz"
    NEG = "neg"
    NOP = "nop"
    NOT = "not"
    MOV = "mov"
    MUL = "mul"
    OR = "or"
    POP = "pop"
    POPAD = "popad"
    PUSH = "push"
    PUSHAD = "pushad"
    RETN = "retn"
    ROL = "rol"
    ROR = "ror"
    SUB = "sub"
    XOR = "xor"

BRANCH_MNEMONICS = [
    Mnemonic.JMP,
    Mnemonic.JBE,
    Mnemonic.JNBE,
    Mnemonic.JGE,
    Mnemonic.JNZ,
    Mnemonic.JZ,
    Mnemonic.CALL
]

LINUX_WRITE = 4
LINUX_STDOUT = 1
LINUX_EXIT = 1

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
class InstructionEncoding: #FIXME: Hacks all around!

    opcodes: list[Opcode]
    mnemonics: "Mnemonic | tuple[Mnemonic, Mnemonic, Mnemonic, Mnemonic, Mnemonic, Mnemonic, Mnemonic, Mnemonic]"
    operand_format: list[OperandEncodingFormat]

    def encode(self, instruction: X86ASMInstruction) -> "X86Instruction | None":

        if not self.opcodes:
            return None
        if isinstance(self.mnemonics, Mnemonic):
            if instruction.mnemonic != self.mnemonics:
                return None
            opcode_extention = 0
        else:
            try:
                opcode_extention = self.mnemonics.index(instruction.mnemonic)
            except ValueError:
                return None
        if len(instruction.operands) != len(self.operand_format):
            return None
        
        opcode = self.opcodes[0]
        mod_field = instruction.addressing_mode
        reg_field = None
        rm_field = None
        if self.opcodes[0].is_immediate():
            if opcode_extention:
                reg_field = opcode_extention
        immediate = bytes()
        for operand_index in range(len(instruction.operands)):
            format = self.operand_format[operand_index]
            operand = instruction.operands[operand_index]
            if format == OperandEncodingFormat.OPCODE:
                if not isinstance(operand.value, Register):
                    return None
                opcode = Opcode(bytes([(self.opcodes[0].get_primary_byte() & 0b11111000) | (operand.value.value.code)]))
            elif format == OperandEncodingFormat.MODREGRM_REGISTER_FIELD:
                if operand.get_register_size() != self.opcodes[0].get_operand_size():
                    return None
                reg_field = operand.value
            elif format == OperandEncodingFormat.MODREGRM_RM_FIELD:
                if operand.get_register_size() != self.opcodes[0].get_operand_size():
                    return None
                rm_field = operand.value
            elif format == OperandEncodingFormat.IMMEDIATE_32_BITS:
                if isinstance(operand.value, Register):
                    return None
                elif isinstance(operand.value, int):
                    if operand.value > (2**32) or operand.value < -(2**31):
                        return None
                    value = operand.value % 2**32
                    immediate = struct.pack("I", value)
                else:
                    immediate = bytes([0,0,0,0])
            elif format == OperandEncodingFormat.IMMEDIATE_8_BITS:
                if isinstance(operand.value, Register):
                    return None
                elif isinstance(operand.value, int):
                    if operand.value < -128 or operand.value > 255:
                        return None
                    else:
                        value = operand.value % 256
                        immediate = struct.pack("B", value)
                else:
                    immediate = bytes([0])
            else:
                return None
        if isinstance(reg_field, Register):
            reg_field = int(reg_field.value.code)
        if isinstance(rm_field, Register):
            rm_field = int(rm_field.value.code)
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
        return X86Instruction(None, opcode, mod_reg_rm, None, bytes(), immediate)

#TODO: smaller/better instruction encodings
#this ungody array does all the legwork
INSTRUCTION_FORMATS = [
    InstructionEncoding([Opcode(bytes([0x00]))], Mnemonic.ADD, [OperandEncodingFormat.MODREGRM_RM_FIELD, OperandEncodingFormat.MODREGRM_REGISTER_FIELD]),
    InstructionEncoding([Opcode(bytes([0x01]))], Mnemonic.ADD, [OperandEncodingFormat.MODREGRM_RM_FIELD, OperandEncodingFormat.MODREGRM_REGISTER_FIELD]),
    InstructionEncoding([Opcode(bytes([0x40]))], Mnemonic.INC, [OperandEncodingFormat.OPCODE]),
    InstructionEncoding([Opcode(bytes([0x48]))], Mnemonic.DEC, [OperandEncodingFormat.OPCODE]),
    InstructionEncoding([Opcode(bytes([0x50]))], Mnemonic.PUSH, [OperandEncodingFormat.OPCODE]),
    InstructionEncoding([Opcode(bytes([0x58]))], Mnemonic.POP, [OperandEncodingFormat.OPCODE]),
    InstructionEncoding([Opcode(bytes([0x60]))], Mnemonic.PUSHAD, []),
    InstructionEncoding([Opcode(bytes([0x61]))], Mnemonic.POPAD, []),
    InstructionEncoding([Opcode(bytes([0x68]))], Mnemonic.PUSH, [OperandEncodingFormat.IMMEDIATE_32_BITS]),
    #InstructionEncoding([Opcode(bytes([0x6a]))], Mnemonic.PUSH, [OperandEncodingFormat.IMMEDIATE_8_BITS]),
    InstructionEncoding([Opcode(bytes([0x80]))], (Mnemonic.ADD, Mnemonic.OR, Mnemonic.NOP, Mnemonic.NOP, Mnemonic.AND, Mnemonic.SUB, Mnemonic.XOR, Mnemonic.CMP), [OperandEncodingFormat.MODREGRM_RM_FIELD, OperandEncodingFormat.IMMEDIATE_8_BITS]),
    InstructionEncoding([Opcode(bytes([0x81]))], (Mnemonic.ADD, Mnemonic.OR, Mnemonic.NOP, Mnemonic.NOP, Mnemonic.AND, Mnemonic.SUB, Mnemonic.XOR, Mnemonic.CMP), [OperandEncodingFormat.MODREGRM_RM_FIELD, OperandEncodingFormat.IMMEDIATE_32_BITS]),
    InstructionEncoding([Opcode(bytes([0x88]))], Mnemonic.MOV, [OperandEncodingFormat.MODREGRM_RM_FIELD, OperandEncodingFormat.MODREGRM_REGISTER_FIELD]),
    InstructionEncoding([Opcode(bytes([0x89]))], Mnemonic.MOV, [OperandEncodingFormat.MODREGRM_RM_FIELD, OperandEncodingFormat.MODREGRM_REGISTER_FIELD]),
    InstructionEncoding([Opcode(bytes([0x90]))], Mnemonic.NOP, []),
    InstructionEncoding([Opcode(bytes([0xc3]))], Mnemonic.RETN, []),
    InstructionEncoding([Opcode(bytes([0xc6]))], Mnemonic.MOV, [OperandEncodingFormat.MODREGRM_RM_FIELD, OperandEncodingFormat.IMMEDIATE_8_BITS]),
    InstructionEncoding([Opcode(bytes([0xc7]))], Mnemonic.MOV, [OperandEncodingFormat.MODREGRM_RM_FIELD, OperandEncodingFormat.IMMEDIATE_32_BITS]),
    InstructionEncoding([Opcode(bytes([0xcd]))], Mnemonic.INT, [OperandEncodingFormat.IMMEDIATE_8_BITS]),
    InstructionEncoding([Opcode(bytes([0xe8]))], Mnemonic.CALL, [OperandEncodingFormat.IMMEDIATE_32_BITS]),
    InstructionEncoding([Opcode(bytes([0xe9]))], Mnemonic.JMP, [OperandEncodingFormat.IMMEDIATE_32_BITS]),
    InstructionEncoding([Opcode(bytes([0xf7]))], (Mnemonic.NOP, Mnemonic.NOP, Mnemonic.NOT, Mnemonic.NEG, Mnemonic.MUL, Mnemonic.IMUL, Mnemonic.DIV, Mnemonic.IDIV), [OperandEncodingFormat.MODREGRM_RM_FIELD]),
    InstructionEncoding([Opcode(bytes([0xfe]))], (Mnemonic.DEC, Mnemonic.INC, Mnemonic.NOP, Mnemonic.NOP, Mnemonic.NOP, Mnemonic.NOP, Mnemonic.NOP, Mnemonic.NOP), [OperandEncodingFormat.MODREGRM_RM_FIELD]),
    InstructionEncoding([Opcode(bytes([0xff]))], (Mnemonic.INC, Mnemonic.DEC, Mnemonic.CALL, Mnemonic.NOP, Mnemonic.JMP, Mnemonic.NOP, Mnemonic.PUSH, Mnemonic.NOP), [OperandEncodingFormat.MODREGRM_RM_FIELD]),
    InstructionEncoding([Opcode(bytes([0x0f, 0x84]))], Mnemonic.JZ, [OperandEncodingFormat.IMMEDIATE_32_BITS]),
    InstructionEncoding([Opcode(bytes([0x0f, 0x85]))], Mnemonic.JNZ, [OperandEncodingFormat.IMMEDIATE_32_BITS]),
    InstructionEncoding([Opcode(bytes([0x0f, 0x86]))], Mnemonic.JBE, [OperandEncodingFormat.IMMEDIATE_32_BITS]),
    InstructionEncoding([Opcode(bytes([0x0f, 0x87]))], Mnemonic.JNBE, [OperandEncodingFormat.IMMEDIATE_32_BITS]),
    InstructionEncoding([Opcode(bytes([0x0f, 0x8d]))], Mnemonic.JGE, [OperandEncodingFormat.IMMEDIATE_32_BITS])
]

class Program:

    def __init__(self, entry_point: int, code: "list[X86ASMInstruction | Label]") -> None:

        self.entry_point = entry_point
        self.code = code
    
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
                machine_instruction.elaborate(f"Unable to encode instruction '{instruction}'")
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
                machine_instruction.elaborate(f"Unable to encode instruction '{instruction}'")
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
    
    def add_move(self, destination: Register, source: int | Register | Label):
        if destination != source:
            self.add_instruction(Mnemonic.MOV, [destination, source])
    
    #TODO: get pushad/popad instructions working
    def add_instructions_to_save_general_registers(self):
        self.add_instruction(Mnemonic.PUSH, [Register.EAX])
        self.add_instruction(Mnemonic.PUSH, [Register.EBX])
        self.add_instruction(Mnemonic.PUSH, [Register.ECX])
        self.add_instruction(Mnemonic.PUSH, [Register.EDX])
            
    def add_instructions_to_restore_general_registers(self):
        self.add_instruction(Mnemonic.POP, [Register.EDX])
        self.add_instruction(Mnemonic.POP, [Register.ECX])
        self.add_instruction(Mnemonic.POP, [Register.EBX])
        self.add_instruction(Mnemonic.POP, [Register.EAX])
    
    def add_fwrite_linux_syscall(self, char_pointer: int | Register | Label, size: int | Register | Label, file_descriptor: int | Register | Label):
        self.add_move(Register.EAX, LINUX_WRITE)
        self.add_move(Register.EBX, file_descriptor)
        self.add_move(Register.ECX, char_pointer)
        self.add_move(Register.EDX, size)
        self.add_instruction(Mnemonic.INT, [0x80])
            
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

    smallest_encoding: "X86Instruction | None" = None
    for format in INSTRUCTION_FORMATS:
        encoded = format.encode(instruction)
        if encoded:
            if not smallest_encoding:
                smallest_encoding = encoded
            if len(bytes(encoded)) < len(bytes(smallest_encoding)):
                smallest_encoding = encoded
    if smallest_encoding:
        return smallest_encoding
    print("'" + str(instruction.mnemonic) + "'")
    return Traceback([Message(f"Cannot encode instruction '{instruction}'", 0, 0)], [])

def main():
    "[1-11101-1-1][11-011-000]"
    #print(bytes([0b11110111, 0b11011000]).hex())
    print(Opcode(bytes([0xc6])).get_operand_size())
    ins = InstructionEncoding([Opcode(bytes([0x40]))], Mnemonic.INC, [OperandEncodingFormat.OPCODE]).encode(X86ASMInstruction(Mnemonic.INC, [Operand(Register.EAX)], AddressingMode.DIRECT))
    if isinstance(ins, X86Instruction):
        print(bytes(ins).hex())
        print(ins.mod_reg_rm)
    else:
        print(ins)

if __name__ == "__main__":
    main()