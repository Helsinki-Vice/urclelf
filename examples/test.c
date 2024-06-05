#include "../stdlib/stdlib.h"

void _start() {
    for(int i = 0; i < 10; i++) {
        urcl_port_numb_out(i);
    }
    urcl_port_text_out('\n');
    urcl_halt();
}