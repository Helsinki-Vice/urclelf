// Hello world using the URCL standard library.

#include "../stdlib/stdlib.h"
extern int urcl_m0[];

void _start() {
    urcl_m0[0] = 65;
    urcl_port_numb_out(urcl_m0[5]);
    urcl_halt();
}