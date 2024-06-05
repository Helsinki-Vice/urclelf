#include "../stdlib/stdlib.h"

char MESSAGE[] = "Hello, URCL! ";
void _start() {

    for(int i=0; i<6; i++) {
        for(int j=0; j<sizeof(MESSAGE); j++) {
            urcl_port_text_out(MESSAGE[j]);
        }
        urcl_port_numb_out(i);
    }

    urcl_halt();
}