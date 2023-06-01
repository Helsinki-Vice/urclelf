

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

class ElfVersion:
    value = bytes([1, 0, 0, 0])
    "Always version 1"

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

class SectionHeaderType(enum.Enum):
    "Determines what the program header represents"
    NULL = bytes([0, 0, 0, 0])
    PROGRAM_DATA = bytes([1, 0, 0, 0])
    SYMBOL_TABLE = bytes([2, 0, 0, 0])
    STRING_TABLE = bytes([3, 0, 0, 0])

class ProgramHeaderType(enum.Enum):
    "Determines what the program header represents"
    NULL = bytes([0, 0, 0, 0])
    LOADABLE = bytes([1, 0, 0, 0])

E_IDENT_SIZE = 16
ELF_HEADER_SIZE = 52
PROGRAM_HEADER_SIZE = 32
SECTION_HEADER_SIZE = 40

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
LINUX_SEGMENT_START_ADDRESS = 0x8048000

# identifies the ELF, goes in the header
# AKA char* e_ident
class ELFIdentifier:
    """identifies the ELF, goes in the header
    \nAKA char* e_ident"""
    def __init__(self, elf_class=ElfClass.BITS_32, endianess=Endianess.LSB, os_abi=OSABI.LINUX, abi_version=ABIVersion.CURRENT):
        
        self.magic = b"ELF"               # e_ident[EI_MAG0:EI_MAG3]
        self.elf_class = ElfClass.BITS_32  # e_ident[EI_CLASS]
        self.endianess = endianess         # e_ident[EI_DATA]
        self.version = bytes([1])          # e_ident[EI_VERSION]
        self.os_abi = os_abi               # e_ident[EI_OSABI]
        self.abi_version = abi_version     # e_ident[EI_ABIVERSION]
        self.padding = bytes(7)            # (ignored)
    
    def __bytes__(self):
        
        return self.magic + self.elf_class.value + self.endianess.value + self.version + self.os_abi.value + self.abi_version.value + self.padding


# Provides important information about the ELF
#
class ELFHeader():
    """provides important information about the ELF"""
    
    def __init__(self, elf_identifier=ELFIdentifier(), file_type=FileType.EXECUTABLE, target_isa=TargetISA.X86, entry_point=0, program_header_offset=0, section_header_offset=0, flags=0, program_header_entry_size=0, program_header_count=0, section_header_entry_size=0, section_header_count=0, section_header_name_index=0):
        
        self.elf_identifier = elf_identifier                            # e_ident
        self.file_type = file_type                                      # e_type
        self.target_isa = target_isa                                    # e_machine
        self.elf_version = ElfVersion()                                 # e_version
        self.entry_point = entry_point                                  # e_entry
        self.program_header_offset = program_header_offset              # e_phoff
        self.section_header_offset = section_header_offset              # e_shoff
        self.flags = flags                                              # e_flags
        self.elf_header_size = ELF_HEADER_SIZE                          # e_ehsize
        self.program_header_entry_size = program_header_entry_size      # e_phentsize
        self.program_header_count = program_header_count                # e_phnum
        self.section_header_entry_size = section_header_entry_size      # e_shentsize
        self.section_header_count = section_header_count                # shnum
        self.section_header_name_index = section_header_name_index      # e_shstrndx
    
    
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
                    self.flags, self.elf_header_size,
                    self.program_header_entry_size,
                    self.program_header_count,
                    self.section_header_entry_size,
                    self.section_header_count,
                    self.section_header_name_index)
        return result

#defines a segment loaded into memory
class ProgramHeader():
    
    def __init__(self, header_type=ProgramHeaderType.LOADABLE, file_offset=0, physical_address=0, virtual_address=0, file_size=0, memory_size=0, flags=PF_R|PF_X, align=0):
        
        self.header_type = header_type                 # p_type
        self.file_offset = file_offset                 # p_offset
        self.virtual_address = virtual_address         # p_vaddr
        self.physical_address = physical_address       # p_paddr
        self.file_size = file_size                     # p_filesz
        self.memory_size = memory_size                 # p_memsz
        self.flags = flags                             # p_flags
        self.align = align                             # p_align
    
    def __bytes__(self):
        
        return  self.header_type.value + struct.pack("IIIIIII", self.file_offset, self.virtual_address, self.physical_address, self.file_size, self.memory_size, self.flags, self.align)


class SectionHeader():
    
    def __init__(self, name_index=0, header_type=SectionHeaderType.PROGRAM_DATA, flags=0, virtual_address=0, file_offset=0, file_size=0, link_index=0, info=0, align=1, entry_size=0):
        
        self.name_index = name_index                 # sh_name
        self.header_type = header_type               # sh_type
        self.flags = flags                           # sh_flags
        self.virtual_address = virtual_address       # sh_addr
        self.file_offset = file_offset               # sh_offset
        self.file_size = file_size                   # sh_size
        self.link_index = link_index                 # sh_link
        self.info = info                             # sh_info
        self.align = align                           # sh_addralign
        self.entry_size = entry_size                 # sh_entsize
    
    @staticmethod
    def null():
        return SectionHeader()
    
    def __bytes__(self):
        
        return struct.pack("I", self.name_index) + self.header_type.value + struct.pack("IIIIIIII", self.flags, self.virtual_address, self.file_offset, self.file_size, self.link_index, self.info, self.align, self.entry_size)

class Section:

    def __init__(self, name: str, data: bytes, memory_size: int, type: SectionHeaderType, is_executable: bool) -> None:

        self.name = name
        self.data = data
        self.memory_size = memory_size
        self.type = type
        self.is_executable = is_executable
    
    @classmethod
    def null(cls):
        return Section(".null", bytes(), 0, SectionHeaderType.NULL, False)
    
    @classmethod
    def section_names(cls, names: list[str]):

        name = ".shrtrtab"
        data = bytes()
        for section_name in names:
            data += section_name.encode("ascii") + bytes([0])
        memory_size = len(data)
        type = SectionHeaderType.STRING_TABLE
        is_executable = False

        return Section(name, data, memory_size, type, is_executable)


#executable ELF binary file
class ELF():
    
    def __init__(self, elf_header: ELFHeader, program_header_table: list[ProgramHeader], section_header_table: list[SectionHeader], sections: dict[int, bytes]):
        
        self.elf_header = elf_header
        self.program_header_table = program_header_table
        self.section_header_table = section_header_table
        self.sections = sections
    
    #converts entire ELF to machine-ready executable
    def __bytes__(self):
        
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
class SymbolTableEntry:
    name_index: int    # st_name;
    value: int         # st_value;
    size: int          # st_size;
    flags: int         # st_info;
    visibility: int    # st_other;
    section_index: int # st_shndx;
    
    def __bytes__(self):
        return struct.pack("IIIBBH", self.name_index, self.value, self.size, self.flags, self.visibility, self.section_index)


class Program:

    def __init__(self, text: bytes, stack_size: int) -> None:
        
        self.text = text
        self.virtual_address = 0x10000
        self.program_header_count = 2
        self.section_header_count = 4
        self.stack_size = stack_size
        self.entry_point = 0
        self.symbols: dict[str, int] = {}
        sections: list[Section] = [
            Section.null(),
            Section.section_names([]),
            Section(
                name = ".symbtab",
                data = bytes(),
                memory_size = 0,
                type = SectionHeaderType.SYMBOL_TABLE,
                is_executable = False
            ),
            Section(
                name = ".text",
                data = text,
                memory_size = len(text),
                type = SectionHeaderType.PROGRAM_DATA,
                is_executable = True
            )
        ]
        self.assemble() # hack to calculate entry point
    
    def calculate_stack_base_address(self):
        return self.virtual_address + len(self.text)
    
    def assemble(self, use_section_header_table=True):

        section_names = Section.section_names([".null", ".shrtrtab", ".symbtab", ".text"])

        file_index = ELF_HEADER_SIZE

        program_header_table_offset = file_index
        file_index += PROGRAM_HEADER_SIZE * self.program_header_count

        if use_section_header_table:
            section_header_table_offset = file_index
            file_index += SECTION_HEADER_SIZE * self.section_header_count

            string_table_offset = file_index
            file_index += len(section_names.data)

            symbol_table_section_offset = file_index
            file_index += 16
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

        text_program_header = ProgramHeader(
            file_offset      = text_section_offset,
            virtual_address  = self.virtual_address + text_section_offset,
            physical_address = 0,
            file_size        = len(self.text),
            memory_size      = len(self.text),
            align            = 0
        )
        stack_program_header = ProgramHeader(
            file_offset      = stack_section_offset,
            virtual_address  = self.virtual_address + stack_section_offset,
            physical_address = 0,
            file_size        = 0,
            memory_size      = self.stack_size, flags = PF_R | PF_W,
            align            = 0
        )
        program_headers = [text_program_header, stack_program_header]

        if use_section_header_table:
            section_names_section_header = SectionHeader(
                name_index      = 6,
                header_type     = SectionHeaderType.STRING_TABLE,
                file_offset     = string_table_offset,
                file_size       = len(section_names.data),
            )
            symbol_table_section_header = SectionHeader(
                name_index      = 16,
                header_type     = SectionHeaderType.SYMBOL_TABLE,
                entry_size      = 16,
                file_size       = 16,
                file_offset     = symbol_table_section_offset,
                link_index      = 1
            )
            text_section_header = SectionHeader(
                name_index      = 25,
                header_type     = SectionHeaderType.PROGRAM_DATA,
                flags           = SHF_ALLOC | SHF_EXECINSTR,
                virtual_address = text_address,
                file_offset     = text_section_offset,
                file_size       = len(self.text),
            )
            section_headers = [SectionHeader.null(), section_names_section_header, symbol_table_section_header, text_section_header]
        else:
            section_headers = []

        elf_header = ELFHeader(
            entry_point               = self.entry_point,
            program_header_offset     = program_header_table_offset,
            program_header_entry_size = PROGRAM_HEADER_SIZE,
            section_header_offset     = section_header_table_offset,
            program_header_count      = len(program_headers),
            section_header_entry_size = SECTION_HEADER_SIZE,
            section_header_count      = len(section_headers),
            section_header_name_index = 1
        )

        if use_section_header_table:
            sections = {
                string_table_offset: section_names.data,
                symbol_table_section_offset: bytes(SymbolTableEntry(1, self.entry_point, len(self.text), 0, 0, 3)),
                text_section_offset: self.text
            }
        else:
            sections = {
                text_section_offset: self.text
            }
        
        return ELF(elf_header, program_headers, section_headers, sections)