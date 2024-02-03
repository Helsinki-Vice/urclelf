from dataclasses import dataclass

from error import Traceback
import x86
import elf.structs as elf

# TODO: Add CLI options of symbol behavior
def determine_symbol_binding(symbol_name: str):
    if symbol_name.startswith("."): # It's a section
        return elf.SymbolBinding.LOCAL
    elif symbol_name.startswith("_") and symbol_name != "_start": # Local use only
        return elf.SymbolBinding.GLOBAL # FIXME: Should be local, but that breaks the symbols by changing their order relative to reloc table
    else:
        return elf.SymbolBinding.GLOBAL

def determine_symbol_type(symbol_name: str):
    if symbol_name.startswith("."): # It's a section
        return elf.SymbolType.SECTION
    else:
        return elf.SymbolType.NONE

def make_symbol_table(defined_symbols: dict[str, int], undefined_symbols: list[str], symbol_name_table: bytes, section_index: int) -> elf.SymbolTable:

    entries: list[elf.Elf32SymbolTableEntry] = []
    for symbol_name in defined_symbols.keys():
        entries.append(elf.Elf32SymbolTableEntry(symbol_name_table.index(symbol_name.encode("ascii")), defined_symbols[symbol_name], 0, determine_symbol_type(symbol_name), determine_symbol_binding(symbol_name), 0, section_index))
    
    for symbol_name in undefined_symbols:
        entries.append(elf.Elf32SymbolTableEntry(symbol_name_table.index(symbol_name.encode("ascii")), 0, 0, elf.SymbolType.NONE, elf.SymbolBinding.GLOBAL, 0, 0))
    # All of the local symbols must come first
    entries.sort(key=lambda s: s.binding==elf.SymbolBinding.LOCAL, reverse=True)
    entries = [elf.Elf32SymbolTableEntry(0, 0, 0, elf.SymbolType.NONE, elf.SymbolBinding.GLOBAL, 0, 0)] + entries

    return elf.SymbolTable(entries)

def make_relocation_table(relocations: list[x86.Relocation], defined_symbol_names: list[str], symbol_table: elf.SymbolTable) -> elf.RelocationTable:

    entries: list[elf.RelocationTableEntryWithAddend] = []
    for relocation in relocations:
        symbol_index = 0
        for index, symbol_name in enumerate(defined_symbol_names, start=1):
            if symbol_name == relocation.symbol_name:
                symbol_index = index
                continue
        entries.append(elf.RelocationTableEntryWithAddend(relocation.index, elf.X86RelocationType.PC_RELATIVE_32, symbol_index, 0))
    
    return elf.RelocationTable(entries)

def make_simple_elf_header() -> elf.ElfHeader:

    return elf.ElfHeader(
        elf_identifier            = elf.ELFIdentifier(elf.ElfClass.BITS_32, elf.Endianess.LSB, elf.OSABI.GENERIC_UNIX),
        file_type                 = elf.FileType.RELOCATABLE,
        target_isa                = elf.TargetISA.X86,
        entry_point               = 0,
        program_header_offset     = 0,
        section_header_offset     = elf.ELF_HEADER_SIZE,
        flags                     = 0,
        elf_header_size           = elf.ELF_HEADER_SIZE,
        program_header_entry_size = 0,
        program_header_count      = 0,
        section_header_entry_size = elf.ELF32_SECTION_HEADER_SIZE,
        section_header_count      = 0,
        section_header_name_index = 0,
    )

def make_relocatable_elf(relocatable_code: x86.CodegenOutput) -> elf.Elf32:
    
    file_offset = 0

    elf_header = make_simple_elf_header()
    elf_header.section_header_offset = elf_header.elf_header_size
    elf_header.section_header_count = 6
    file_offset += elf_header.elf_header_size

    null_section_header               = elf.Elf32SectionHeader.null()
    section_names_section_header      = elf.Elf32SectionHeader.blank_of_type(elf.Elf32SectionHeaderType.STRING_TABLE)
    symbol_table_names_section_header = elf.Elf32SectionHeader.blank_of_type(elf.Elf32SectionHeaderType.STRING_TABLE)
    symbol_table_section_header       = elf.Elf32SectionHeader.blank_of_type(elf.Elf32SectionHeaderType.SYMBOL_TABLE)
    relocation_section_header         = elf.Elf32SectionHeader.blank_of_type(elf.Elf32SectionHeaderType.RELOCATABLE)
    text_section_header               = elf.Elf32SectionHeader.blank_of_type(elf.Elf32SectionHeaderType.PROGRAM_DATA)
    
    section_names = elf.make_null_terminated_string_table([elf.KnownSectionNames.NULL.value, elf.KnownSectionNames.SECTION_HEADER_STRING_TABLE.value, elf.KnownSectionNames.STRING_TABLE, elf.KnownSectionNames.SYMBOL_TABLE.value, elf.KnownSectionNames.RELOCATION_TEXT.value, elf.KnownSectionNames.TEXT.value])
    section_names_section_header.name_index      = section_names.index(elf.KnownSectionNames.SECTION_HEADER_STRING_TABLE.value.encode("ascii"))
    symbol_table_names_section_header.name_index = section_names.index(elf.KnownSectionNames.STRING_TABLE.value.encode("ascii"))
    symbol_table_section_header.name_index       = section_names.index(elf.KnownSectionNames.SYMBOL_TABLE.value.encode("ascii"))
    relocation_section_header.name_index         = section_names.index(elf.KnownSectionNames.RELOCATION_TEXT.value.encode("ascii"))
    text_section_header.name_index               = section_names.index(elf.KnownSectionNames.TEXT.value.encode("ascii"))

    file_offset += elf_header.section_header_entry_size * 6

    section_header_table = elf.Elf32SectionHeaderTable([
        null_section_header,
        section_names_section_header,
        symbol_table_names_section_header,
        symbol_table_section_header,
        relocation_section_header,
        text_section_header
    ])

    elf_header.section_header_name_index = section_header_table.entries.index(section_names_section_header)
    relocation_section_header.link_index = section_header_table.entries.index(symbol_table_section_header)
    relocation_section_header.info = section_header_table.entries.index(text_section_header)
    text_section_header.flags = elf.SHF_ALLOC | elf.SHF_EXECINSTR

    undefined_symbol_names = relocatable_code.get_undefined_label_names()
    all_symbol_names = list(relocatable_code.labels.keys()) + undefined_symbol_names
    symbol_name_table_bytes = elf.make_null_terminated_string_table(all_symbol_names)
    symbol_table = make_symbol_table(relocatable_code.labels, undefined_symbol_names, symbol_name_table_bytes, 5)
    symbol_table_section_header.info = symbol_table.get_symbol_index_of_first_nonlocal_symbol()
    symbol_table_section_header.link_index = section_header_table.entries.index(symbol_table_names_section_header)
    symbol_table_section_header.entry_size = 16
    relocation_section_header.entry_size = 12
    symbol_table_bytes = bytes(symbol_table)
    reloaction_table_bytes = bytes(make_relocation_table(relocatable_code.relocations, all_symbol_names, symbol_table))

    section_data = [b"", section_names, symbol_name_table_bytes, symbol_table_bytes, reloaction_table_bytes, relocatable_code.binary]
    sections: dict[int, bytes] = {}
    for section_index in range(1, len(section_header_table.entries)):
        section_header_table.entries[section_index].file_offset = file_offset
        section_header_table.entries[section_index].file_size = len(section_data[section_index])
        sections.update({section_header_table.entries[section_index].file_offset: section_data[section_index]})
        file_offset += len(section_data[section_index])

    return elf.Elf32(elf_header, elf.Elf32ProgramHeaderTable([]), section_header_table, sections)