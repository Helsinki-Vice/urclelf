from dataclasses import dataclass

@dataclass
class Message:
    message: str
    line: int
    column: int

@dataclass
class Traceback:
    errors: list[Message]
    warnings: list[Message]

    def push(self, error_message: Message):
        self.errors.insert(0, error_message)
    
    def warn(self, message: Message):
        self.warnings.append(message)
    
    def __str__(self) -> str:
        
        lines: list[str] = []
        for warning in self.warnings:
            lines.append(f"WARNING: {warning.message}")
        
        lines.append("TRACEBACK (most recent call last)")
        for indent, error in enumerate(self.errors):
            lines.append(f"{error.line}:{error.column} " + "    " * (indent - 1) + "+-->" * (indent > 0) + f"{error.message}")
        
        traceback_width = 0
        for line in lines:
            if len(line) > traceback_width:
                traceback_width = len(line)
        lines.insert(0, "=" * traceback_width)
        lines.append("=" * traceback_width)

        return "\n".join(lines)

string = b"Hello, world!\n"
for char in string:
    print(f"out 1 {char} // {chr(char)}")