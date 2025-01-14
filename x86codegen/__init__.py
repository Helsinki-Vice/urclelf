"Emits x86/x64 assembly from URCL code."
from x86codegen.compile import compile_urcl_to_executable, compile_urcl_to_intel_assembly

__all__ = ["compile_urcl_to_executable", "compile_urcl_to_intel_assembly"]