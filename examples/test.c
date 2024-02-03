
void urcl_port_numb_out(int value);
void urcl_halt(void);

void _start() {
    for(int i = 0; i < 10; i++) {
        urcl_port_numb_out(i);
    }
    urcl_halt();
}