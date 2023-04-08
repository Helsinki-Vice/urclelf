

import struct
import math
import enum

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
    EXECUTABLE = bytes([2, 0])

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
PF_X = 1
SHT_NULL = 0
SHT_PROGBITS = 1
SHT_STRTAB = 3
SHF_ALLOC = 2
SHF_EXECINSTR = 4

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
        self.file_size = file_offset                 # sh_size
        self.link_index = link_index                 # sh_link
        self.info = info                             # sh_info
        self.align = align                           # sh_addralign
        self.entry_size = entry_size                 # sh_entsize
    
    def __bytes__(self):
        
        return struct.pack("I", self.name_index) + self.header_type.value + struct.pack("IIIIIIII", self.flags, self.virtual_address, self.file_offset, self.file_size, self.link_index, self.info, self.align, self.entry_size)


#executable ELF binary file
class ELF():
    
    def __init__(self, elf_header: ELFHeader, program_header_table: list[ProgramHeader], section_header_table: list[SectionHeader], program_image: bytes):
        
        self.elf_header = elf_header
        self.program_header_table = program_header_table
        self.section_header_table = section_header_table
        self.program_image = program_image
    
    
    #converts entire ELF to machine-ready executable
    def __bytes__(self):
        
        elf_header_bin = bytearray(bytes(self.elf_header))
        program_header_table_bin = bytearray()
        section_header_table_bin = bytearray()
        
        for program_header in self.program_header_table:
            program_header_table_bin.extend(bytes(program_header))
        
        for section_header in self.section_header_table:
            section_header_table_bin.extend(bytes(section_header))
        
        file_elements = {
            0: elf_header_bin,
            self.elf_header.program_header_offset: program_header_table_bin,
        }
        if self.elf_header.section_header_offset and section_header_table_bin:
            file_elements.update({self.elf_header.section_header_offset: section_header_table_bin})
        
        file_size = 0
        for offset, data in file_elements.items():
            required_size = offset + len(data)
            if required_size > file_size:
                file_size = required_size
        result = bytearray(file_size)
        for offset, data in file_elements.items():
            result = result[:offset] + data + result[offset+len(data):]
        
        return bytes(result) + self.program_image

class Section:
    
    def __init__(self):
        
        self.name = 0
        self.address = 0
        self.writable = 0
        self.executable = 0
        self.data = bytes()
    
    
    def __len__(self):
        return len(self.data)
    
    
    def __bytes__(self):
        
        return 0

class Program:

    def __init__(self, text: bytes) -> None:
        
        self.text = text
    
    def assemble(self):

        elf_header = ELFHeader(entry_point=0x8048000+52+32, program_header_offset=52, section_header_offset=0, program_header_entry_size=32, program_header_count=1, section_header_entry_size=40, section_header_count=0, section_header_name_index=0)
        program_header = ProgramHeader(file_offset=0, virtual_address=0x8048000, physical_address=0, file_size=52+32+len(self.text), memory_size=52+32+len(self.text), align=1024)
        
        return ELF(elf_header, [program_header], [], self.text)