"This module defines types for representing parsing/compilation errors"
from dataclasses import dataclass

@dataclass
class Message:
    message: str
    line: int
    column: int

@dataclass
class Traceback:
    errors: list[Message]
    
    @classmethod
    def new(cls, message: str, line_number:int=0, column_number:int=1):
        return Traceback([Message(message, line_number, column_number)])
    
    def elaborate(self, message: str, line_number:int=0, column_number:int=1):

        if not line_number:
            line_number = self.errors[0].line
            column_number = self.errors[0].column
        self.errors.insert(0, Message(message, line_number, column_number))
    
    
    def __str__(self) -> str:
        
        lines: list[str] = []
    
        lines.append("TRACEBACK")
        for error in self.errors:
            sub_lines = error.message.splitlines()
            lines.append(f"{error.line}:{error.column} {sub_lines[0]}")
            for line in sub_lines[1:]:
                lines.append(line)
        
        traceback_width = 0
        for line in lines:
            if len(line) > traceback_width:
                traceback_width = len(line)
        lines.insert(0, "=" * traceback_width)
        lines.append("=" * traceback_width)

        return "\n".join(lines)

#string = b"Hello from x86 URCL!\n"
#for char in string:
#    print(f"out 1 {char}")