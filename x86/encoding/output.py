from dataclasses import dataclass

@dataclass
class Relocation:
    symbol_name: str
    index: int
    size: int
    addend: int
    is_signed: bool
    is_relative: bool

@dataclass
class AssembledMachineCode:
    binary: bytes
    relocations: list[Relocation]
    symbols: dict[str, int]

    def get_undefined_label_names(self):

        undefined_symbol_names: list[str] = []
        for relocation in self.relocations:
            if relocation.symbol_name not in self.symbols.keys():
                undefined_symbol_names.append(relocation.symbol_name)

        return undefined_symbol_names