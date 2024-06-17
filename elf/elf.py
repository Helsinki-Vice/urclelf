"""Definitions for the executable and linkable file format 'ELF'.
based on file:///usr/include/elf.h"""
# http://flint.cs.yale.edu/cs422/doc/ELF_Format.pdf

import struct
import enum
from dataclasses import dataclass
import structs

class ElfClass(enum.Enum):
    "Word size of the target machine"
    BITS_32 = bytes([1])
    BITS_64 = bytes([2])

class Endianess(enum.Enum):
    "Endianess of the target machine"
    LSB = bytes([1])
    MSB = bytes([2])

class ElfVersion(enum.Enum):
    "Always version 1"
    CURRENT = bytes([1, 0, 0, 0])

class OSABI(enum.Enum):
    "Operating system ABI of the target machine"
    GENERIC_UNIX = bytes([0])
    LINUX = bytes([3])

class FileType(enum.Enum):
    "Specifies the type of the file"
    UNKNOWN = bytes([0, 0])
    RELOCATABLE = bytes([1, 0])
    EXECUTABLE = bytes([2, 0])
    SHARED_OBJECT = bytes([3, 0])

class TargetISA(enum.Enum):
    "Instruction set of the target machine"
    UNKNOWN = bytes([0, 0])
    X86 = bytes([3, 0])

class ABIVersion(enum.Enum):
    "Operating system ABI of the target machine"
    CURRENT = bytes([0])

class Elf32SectionHeaderType(enum.Enum):
    "Determines what the contents of the section represent"
    NULL = bytes([0, 0, 0, 0])
    PROGRAM_DATA = bytes([1, 0, 0, 0])
    SYMBOL_TABLE = bytes([2, 0, 0, 0])
    STRING_TABLE = bytes([3, 0, 0, 0])
    RELOCATABLE = bytes([4, 0, 0, 0])

class Elf32ProgramHeaderType(enum.Enum):
    "Determines what the program header represents"
    NULL = bytes([0, 0, 0, 0])
    LOADABLE = bytes([1, 0, 0, 0])

E_IDENT_SIZE = 16
ELF_HEADER_SIZE_32_BIT = 52
ELF_HEADER_SIZE_64_BIT = 54
ELF32_PROGRAM_HEADER_SIZE = 32
ELF32_SECTION_HEADER_SIZE = 40

ELFCLASS32 = 1
ELFDATA2LSB = 1
EV_CURRENT = 1
ELF_OSABI_SYSV = 0
ET_EXEC = 2
EM_ARM = 40
PT_LOAD = 1
PF_R = 4
PF_W = 2
PF_X = 1
SHT_NULL = 0
SHT_PROGBITS = 1
SHT_STRTAB = 3
SHF_ALLOC = 2
SHF_EXECINSTR = 4
ELF32_SYMBOL_TABLE_ENTRY_SIZE = 16

class KnownSectionNames(enum.StrEnum):
    NULL = ".null"
    SECTION_HEADER_STRING_TABLE = ".shrtrtab"
    SYMBOL_TABLE = ".symtab"
    STRING_TABLE = ".strtab"
    TEXT = ".text"
    RELOCATION_TEXT = ".rel.text"

@dataclass
class ELFIdentifier:
    """identifies the ELF, goes in the header - AKA char* e_ident"""    
    magic = b"ELF"                 # e_ident[EI_MAG0:EI_MAG3]
    elf_class: ElfClass              # e_ident[EI_CLASS]
    endianess: Endianess             # e_ident[EI_DATA]
    version = bytes([1])             # e_ident[EI_VERSION]
    os_abi: OSABI                    # e_ident[EI_OSABI]
    abi_version = ABIVersion.CURRENT # e_ident[EI_ABIVERSION]
    padding = bytes(7)               # (ignored)
    
    def __bytes__(self):
        return self.magic + self.elf_class.value + self.endianess.value + self.version + self.os_abi.value + self.abi_version.value + self.padding


@dataclass
class Elf32ProgramHeader:
    "Defines a segment loaded into memory"

    header_type: Elf32ProgramHeaderType  # p_type
    file_offset: int                     # p_offset
    virtual_address: int                 # p_vaddr
    physical_address: int                # p_paddr
    file_size: int                       # p_filesz
    memory_size: int                     # p_memsz
    flags: int                           # p_flags
    align: int                           # p_align
    
    def __bytes__(self):
        return  self.header_type.value + struct.pack("IIIIIII", self.file_offset, self.virtual_address, self.physical_address, self.file_size, self.memory_size, self.flags, self.align)

@dataclass
class Elf32ProgramHeaderTable:
    entries: list[Elf32ProgramHeader]

@dataclass
class Elf32SectionHeader:
        
    name_index: int                       # sh_name
    header_type: Elf32SectionHeaderType   # sh_type
    flags: int                            # sh_flags
    virtual_address: int                  # sh_addr
    file_offset: int                      # sh_offset
    file_size: int                        # sh_size
    link_index: int                       # sh_link
    info: int                             # sh_info
    align: int                            # sh_addralign
    entry_size: int                       # sh_entsize
    
    @staticmethod
    def null():
        return Elf32SectionHeader(
            name_index = 0,
            header_type = Elf32SectionHeaderType.NULL,
            flags = 0,
            virtual_address = 0,
            file_offset = 0,
            file_size = 0,
            link_index = 0,
            info = 0,
            align = 0,
            entry_size = 0
        )
    
    def __bytes__(self):
        return struct.pack("I", self.name_index) + self.header_type.value + struct.pack("IIIIIIII", self.flags, self.virtual_address, self.file_offset, self.file_size, self.link_index, self.info, self.align, self.entry_size)

@dataclass
class Elf32SectionHeaderTable:
    entries: list[Elf32SectionHeader]

@dataclass
class Section:
    name: str
    data: bytes
    memory_size: int
    type: Elf32SectionHeaderType
    is_executable: bool
    
    @classmethod
    def null(cls):
        return Section(KnownSectionNames.NULL, bytes(), 0, Elf32SectionHeaderType.NULL, False)
    
    @classmethod
    def section_names(cls, names: list[str]):

        name = KnownSectionNames.SECTION_HEADER_STRING_TABLE
        data = bytes()
        for section_name in names:
            data += section_name.encode("ascii") + bytes([0])
        memory_size = len(data)
        type = Elf32SectionHeaderType.STRING_TABLE
        is_executable = False

        return Section(name, data, memory_size, type, is_executable)

@dataclass
class Elf32:
    "ELF binary file"
    
    elf_header: structs.ElfHeader
    program_header_table: Elf32ProgramHeaderTable
    section_header_table: Elf32SectionHeaderTable
    sections: dict[int, bytes]
    
    #converts entire ELF to machine-ready executable
    def __bytes__(self):
        "Converts entire ELF to machine-ready executable"
        elf_header_bin = bytearray(bytes(self.elf_header))
        program_header_table_bin = bytearray()
        section_header_table_bin = bytearray()
        
        for program_header in self.program_header_table.entries:
            program_header_table_bin.extend(bytes(program_header))
        
        for section_header in self.section_header_table.entries:
            section_header_table_bin.extend(bytes(section_header))
        
        file_elements: list[tuple[int, bytearray]] = [(0, elf_header_bin)]

        if self.elf_header.program_header_offset and program_header_table_bin:
            file_elements.append((self.elf_header.program_header_offset, program_header_table_bin))
        
        if self.elf_header.section_header_offset and section_header_table_bin:
            file_elements.append((self.elf_header.section_header_offset, section_header_table_bin))
        
        for file_offset, data in self.sections.items():
            file_elements.append((file_offset, bytearray(data)))

        file_size = 0
        for offset, data in file_elements:
            required_size = offset + len(data)
            if required_size > file_size:
                file_size = required_size
        result = bytearray(file_size)
        for offset, data in file_elements:
            result = result[:offset] + data + result[offset+len(data):]
        
        return bytes(result)

class SymbolType(enum.IntEnum):
    NONE = 0
    DATA_OBJECT = 1
    FUNCTION = 2
    SECTION = 3
    FILENAME = 4
    COMMON = 5
    THREAD_LOCAL_STORAGE = 6

class SymbolBinding(enum.IntEnum):
    LOCAL = 0
    GLOBAL = 1
    WEAK = 2

@dataclass
class Elf32SymbolTableEntry:
    name_index: int         # st_name;
    value: int              # st_value;
    size: int               # st_size;
    type: SymbolType        # st_info (lower 4 bits);
    binding: SymbolBinding  # st_info (upper 4 bits);
    other: int              # st_other;
    section_index: int      # st_shndx;
    
    def __bytes__(self):
        return struct.pack("IIIBBH", self.name_index, self.value, self.size, (self.type) + (self.binding << 4), self.other, self.section_index)


#FIXME: I don't understand these, do not trust this enum
class X86RelocationType(enum.IntEnum):
    NONE = 0
    SIMPLE_32 = 1
    PC_RELATIVE_32 = 2
    GLOBAL_OFFSET_TABLE_INDEX_32 = 3
    PROCEDURE_LOOKUP_TABLE_ENTRY_RELATIVE_32 = 4
    COPY = 5
    SYMBOL_VALUE_NO_ADDEND_32 = 6
    JUMP_SLOT_32 = 7
    R_386_RELATIVE = 8
    LOAD_ADDRESS_RELATIVE_32 = 9
    R_386_GOTPC = 10

@dataclass
class RelocationTableEntryWithAddend:
    offset: int              # r_offset
    type: X86RelocationType  # r_info (lower 8 bits)
    symbol_index: int        # r_info (upper 24 bits)
    addend: int              # r_addend

    def __bytes__(self):
        return struct.pack("IIi", self.offset, (self.symbol_index << 8) + self.type, self.addend)


def make_null_terminated_string_table(strings: list[str]) -> bytes:
    return b"\0" + bytes([]).join([string.encode("ascii") + b"\0" for string in strings])