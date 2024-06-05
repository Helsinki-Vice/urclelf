import x86
from dataclasses import dataclass
import struct
import enum

class StorageClass(enum.IntEnum):
    NONE = 0
    AUTO = 1

@dataclass
class CoffHeader:
    machine: int               # u16
    section_count: int         # u16
    timestamp: int             # u32
    symbol_table_pointer: int  # u32
    symbol_count: int          # u32
    optional_header_size: int  # u16
    characteristics: int       # u16

    def __bytes__(self):
        return struct.pack("HHIIIHH",
            self.machine,
            self.section_count,
            self.timestamp,
            self.symbol_table_pointer,
            self.symbol_count,
            self.optional_header_size,
            self.characteristics
        )

@dataclass
class SectionHeader:
    name: bytes                   # u8[8]
    virtual_size: int             # u32
    virtual_address: int          # u32
    data_size: int                # u32
    data_file_offset: int         # u32
    relocations_file_offset: int  # u32
    line_numbers_file_offset: int # u32
    relocation_count: int         # u16
    line_number_count: int        # u16
    characteristics: int          # u32

    def __bytes__(self):
        return self.name + struct.pack("IIIIIIHHI",
            self.virtual_size,
            self.virtual_address,
            self.data_size,
            self.data_file_offset,
            self.relocations_file_offset,
            self.line_numbers_file_offset,
            self.relocation_count,
            self.line_number_count,
            self.characteristics
        )

# http://www.delorie.com/djgpp/doc/coff/symtab.html
@dataclass
class SymbolTableEntry:
    inlined_name: bytes           # u8 e_name[8] [UNION]
    name_is_inlined: int          # u32 e_zeroes [UNION]
    offset_of_name: int           # u32 e_offset [UNION]
    symbol_value: int             # u32 long e_value;
    section_number: int           # u16 e_scnum;
    symbol_type: int              # u16 e_type;
    storage_class: StorageClass   # u8 e_sclass;
    aux_entry_count: int          # u8 e_numaux;

    def __bytes__(self):
        return bytes(18)

def string_table_from(code: x86.AssembledMachineCode) -> bytes:

    long_symbol_names = bytes()
    for symbol in code.symbols:
        if len(symbol) > 8:
            long_symbol_names += symbol.encode("ascii") + bytes(1)
    
    return long_symbol_names

def compile_to_relocatable_file(relocatable_code: x86.AssembledMachineCode) -> bytes:
    
    pe_header = bytes(CoffHeader(0x14c,1,0,0x3c,len(relocatable_code.symbols),0,0x0))
    symbol_table = bytes()
    string_table = string_table_from(relocatable_code)
    for symbol in relocatable_code.symbols:
        symbol_table += (symbol.encode("ascii") + bytes(8))[:8] + bytes([42,0,0,0, 255,255, 1,0, 1, 0])
    section_header = bytes(SectionHeader(b".text\0\0\0", len(relocatable_code.binary), 0, len(relocatable_code.binary), 0x3c + len(relocatable_code.symbols) * 18 + len(string_table), 0, 0, 0, 0, 0))
    file = pe_header + section_header + symbol_table + string_table + relocatable_code.binary
    return file