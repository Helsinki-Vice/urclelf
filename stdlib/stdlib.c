/*
    Implemention of the urclelf stdlib in C.
*/

#include <stdlib.h>
#include <stdio.h>

void urcl_port_text_out(int symbol) {
    putchar(symbol);
}
void urcl_port_numb_out(int number) {
    printf("%d", number);
}
void urcl_halt() {
    exit(0);
}