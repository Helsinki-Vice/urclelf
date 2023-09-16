"""Definitions for the executable and linkable file format 'ELF'.
based on file:///usr/include/elf.h"""
# http://flint.cs.yale.edu/cs422/doc/ELF_Format.pdf

import struct
import enum
from dataclasses import dataclass

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
    "Determines what the program header represents"
    NULL = bytes([0, 0, 0, 0])
    PROGRAM_DATA = bytes([1, 0, 0, 0])
    SYMBOL_TABLE = bytes([2, 0, 0, 0])
    STRING_TABLE = bytes([3, 0, 0, 0])

class Elf32ProgramHeaderType(enum.Enum):
    "Determines what the program header represents"
    NULL = bytes([0, 0, 0, 0])
    LOADABLE = bytes([1, 0, 0, 0])

E_IDENT_SIZE = 16
ELF_HEADER_SIZE = 52
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
    SYMBOL_TABLE = ".symbtab"
    TEXT = ".text"

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
class ElfHeader:
    """provides important information about the ELF"""
    
    elf_identifier: ELFIdentifier        # e_ident
    file_type: FileType                  # e_type
    target_isa: TargetISA                # e_machine
    elf_version = ElfVersion.CURRENT     # e_version
    entry_point: int                     # e_entry
    program_header_offset: int           # e_phoff
    section_header_offset: int           # e_shoff
    flags: int                           # e_flags
    elf_header_size: int                 # e_ehsize
    program_header_entry_size: int       # e_phentsize
    program_header_count: int            # e_phnum
    section_header_entry_size: int       # e_shentsize
    section_header_count: int            # shnum
    section_header_name_index: int       # e_shstrndx
    
    
    def __bytes__(self):
        
        result = bytes()
        result += bytes(self.elf_identifier)
        result += self.file_type.value
        result += self.target_isa.value
        result += self.elf_version.value
        result += struct.pack("IIIIHHHHHH",
            self.entry_point,
            self.program_header_offset,
            self.section_header_offset,
            self.flags,
            self.elf_header_size,
            self.program_header_entry_size,
            self.program_header_count,
            self.section_header_entry_size,
            self.section_header_count,
            self.section_header_name_index)
        return result

@dataclass
class Elf32ProgramHeader:
    "Defines a segment loaded into memory"

    header_type: Elf32ProgramHeaderType    # p_type
    file_offset: int                  # p_offset
    virtual_address: int              # p_vaddr
    physical_address: int             # p_paddr
    file_size: int                    # p_filesz
    memory_size: int                  # p_memsz
    flags: int                        # p_flags
    align: int                        # p_align
    
    def __bytes__(self):
        
        return  self.header_type.value + struct.pack("IIIIIII", self.file_offset, self.virtual_address, self.physical_address, self.file_size, self.memory_size, self.flags, self.align)

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
    "Executable ELF binary file"
    
    elf_header: ElfHeader
    program_header_table: list[Elf32ProgramHeader]
    section_header_table: list[Elf32SectionHeader]
    sections: dict[int, bytes]
    
    #converts entire ELF to machine-ready executable
    def __bytes__(self):
        "Converts entire ELF to machine-ready executable"
        elf_header_bin = bytearray(bytes(self.elf_header))
        program_header_table_bin = bytearray()
        section_header_table_bin = bytearray()
        
        for program_header in self.program_header_table:
            program_header_table_bin.extend(bytes(program_header))
        
        for section_header in self.section_header_table:
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

@dataclass
class Elf32SymbolTableEntry:
    name_index: int    # st_name;
    value: int         # st_value;
    size: int          # st_size;
    flags: int         # st_info;
    other: int         # st_other;
    section_index: int # st_shndx;
    
    def __bytes__(self):
        return struct.pack("IIIBBH", self.name_index, self.value, self.size, self.flags, self.other, self.section_index)


class Elf32Exec:

    def __init__(self, text: bytes, stack_size: int, address: int, use_section_header_table:bool=True) -> None:
        
        self.text = text
        self.virtual_address = address
        self.program_header_count = 2
        self.section_header_count = 4
        self.stack_size = stack_size
        self.entry_point = 0
        self.symbols: dict[str, int] = {}
        self.assemble(use_section_header_table) # hack to calculate entry point
        self.symbols.update({"_start": self.entry_point})
    
    def calculate_stack_base_address(self):
        return self.entry_point + len(self.text)
    
    def calculate_program_headers(self, text_section_file_offset: int, stack_section_file_offset: int):
        
        text_program_header = Elf32ProgramHeader(
            header_type      = Elf32ProgramHeaderType.LOADABLE,
            file_offset      = text_section_file_offset,
            virtual_address  = self.virtual_address + text_section_file_offset,
            physical_address = 0,
            file_size        = len(self.text),
            memory_size      = len(self.text),
            flags            = PF_R | PF_X | PF_W,
            align            = 0
        )
        stack_program_header = Elf32ProgramHeader(
            header_type      = Elf32ProgramHeaderType.LOADABLE,
            file_offset      = stack_section_file_offset,
            virtual_address  = self.virtual_address + stack_section_file_offset,
            physical_address = 0,
            file_size        = 0,
            memory_size      = self.stack_size,
            flags            = PF_R | PF_W,
            align            = 0
        )
        
        return [text_program_header, stack_program_header]
    
    def calculate_section_headers(self,
        section_names_buffer: bytes,
        string_table_file_offset: int,
        symbol_table_file_offset: int,
        section_name_section: Section,
        text_address: int,
        use_section_header_table: bool,
        text_section_offset: int,
        section_names: list[str]):

        if use_section_header_table:
            section_names_section_header = Elf32SectionHeader(
                name_index      = section_names_buffer.index(KnownSectionNames.SECTION_HEADER_STRING_TABLE.encode("utf-8")),
                header_type     = Elf32SectionHeaderType.STRING_TABLE,
                flags           = 0,
                virtual_address = 0,
                file_offset     = string_table_file_offset,
                file_size       = len(section_name_section.data),
                link_index      = 0,
                info            = 0,
                align           = 0,
                entry_size      = 0
            )
            symbol_table_section_header = Elf32SectionHeader(
                name_index      = section_names_buffer.index(KnownSectionNames.SYMBOL_TABLE.encode("utf-8")),
                header_type     = Elf32SectionHeaderType.SYMBOL_TABLE,
                flags           = 0,
                virtual_address = 0,
                file_size       = ELF32_SYMBOL_TABLE_ENTRY_SIZE,
                file_offset     = symbol_table_file_offset,
                link_index      = section_names.index(KnownSectionNames.SECTION_HEADER_STRING_TABLE),
                info            = 0,
                align           = 0,
                entry_size      = ELF32_SYMBOL_TABLE_ENTRY_SIZE
            )
            text_section_header = Elf32SectionHeader(
                name_index      = section_names_buffer.index(KnownSectionNames.TEXT.encode("utf-8")),
                header_type     = Elf32SectionHeaderType.PROGRAM_DATA,
                flags           = SHF_ALLOC | SHF_EXECINSTR,
                virtual_address = text_address,
                file_size       = len(self.text),
                file_offset     = text_section_offset,
                link_index      = 0,
                info            = 0,
                align           = 0,
                entry_size      = 0
            )
            section_headers : list[Elf32SectionHeader] = []
            for section_name in section_names:
                match section_name:
                    case KnownSectionNames.NULL:
                        section_headers.append(Elf32SectionHeader.null())
                    case KnownSectionNames.SECTION_HEADER_STRING_TABLE:
                        section_headers.append(section_names_section_header)
                    case KnownSectionNames.SYMBOL_TABLE:
                        section_headers.append(symbol_table_section_header)
                    case KnownSectionNames.TEXT:
                        section_headers.append(text_section_header)
                    case _:
                        pass
        else:
            section_headers = []

        return section_headers
    
    def calculate_elf_header(self, program_header_table_offset: int, section_header_table_offset: int, program_header_count: int, section_header_count: int, section_header_name_index: int):
        
        return ElfHeader(
            elf_identifier            = ELFIdentifier(ElfClass.BITS_32, Endianess.LSB, OSABI.LINUX),
            file_type                 = FileType.EXECUTABLE,
            target_isa                = TargetISA.X86,
            entry_point               = self.entry_point,
            program_header_offset     = program_header_table_offset,
            section_header_offset     = section_header_table_offset,
            flags                     = 0,
            elf_header_size           = ELF_HEADER_SIZE,
            program_header_entry_size = ELF32_PROGRAM_HEADER_SIZE,
            program_header_count      = program_header_count,
            section_header_entry_size = ELF32_SECTION_HEADER_SIZE,
            section_header_count      = section_header_count,
            section_header_name_index = section_header_name_index,
        )

    def calculate_symbol_table_entries(self):
        
        symbol_table_entries: list[Elf32SymbolTableEntry] = []
        for name, value in self.symbols.items():
            ...
        
        return symbol_table_entries
    
    def assemble(self, use_section_header_table:bool=True):

        section_names: list[str] = [KnownSectionNames.NULL, KnownSectionNames.SECTION_HEADER_STRING_TABLE, KnownSectionNames.SYMBOL_TABLE, KnownSectionNames.TEXT, "_start"]
        section_name_section = Section.section_names(section_names)
        section_names_buffer = section_name_section.data

        file_index = ELF_HEADER_SIZE

        program_header_table_offset = file_index
        file_index += ELF32_PROGRAM_HEADER_SIZE * self.program_header_count

        if use_section_header_table:
            section_header_table_offset = file_index
            file_index += ELF32_SECTION_HEADER_SIZE * self.section_header_count

            string_table_offset = file_index
            file_index += len(section_names_buffer)

            symbol_table_section_offset = file_index
            file_index += ELF32_SYMBOL_TABLE_ENTRY_SIZE
        else:
            section_header_table_offset = 0
            string_table_offset = 0
            symbol_table_section_offset = 0

        text_section_offset = file_index
        file_index += len(self.text)

        stack_section_offset = file_index
        file_index += 0

        text_address = self.virtual_address + text_section_offset
        self.entry_point = text_address

        program_headers = self.calculate_program_headers(text_section_offset, stack_section_offset)

        section_headers = self.calculate_section_headers(
            section_names_buffer,
            string_table_offset,
            symbol_table_section_offset,
            section_name_section,
            text_address,
            use_section_header_table,
            text_section_offset,
            section_names
        )

        elf_header = self.calculate_elf_header(program_header_table_offset, section_header_table_offset, len(program_headers), len(section_headers), section_names.index(KnownSectionNames.SECTION_HEADER_STRING_TABLE))

        if use_section_header_table:
            sections = {
                string_table_offset: section_name_section.data,
                symbol_table_section_offset: bytes(Elf32SymbolTableEntry(section_names_buffer.index("_start".encode("utf-8")), self.entry_point, len(self.text), 16, 0, section_names.index(KnownSectionNames.TEXT))),
                text_section_offset: self.text
            }
        else:
            sections = {
                text_section_offset: self.text
            }
        
        return Elf32(elf_header, program_headers, section_headers, sections)