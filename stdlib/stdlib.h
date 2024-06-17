/*
    C header file for calling URCL stdlib functions in C.
*/

void urcl_port_text_out(int symbol);
void urcl_port_numb_out(int number);
void urcl_port_x_out(int x);
void urcl_port_y_out(int y);
void urcl_port_color_out(int color);
void urcl_port_int_out(int number);
void urcl_port_wait_out(int deciseconds);

int urcl_port_text_in();
int urcl_port_numb_in();
int urcl_port_int_in();
int urcl_port_rng_in();
int urcl_port_wait_in();

void urcl_io_init();
void urcl_io_close();
void urcl_halt();