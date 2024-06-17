// Hack to get URCL memory operations working.
// Link to m0.o when compiling programs that make use of LOD/STR.
int urcl_m0[0xFFFF] = {};