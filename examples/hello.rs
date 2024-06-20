// Hello world using the URCL standard library.

extern "C" {
    fn urcl_port_text_out(symbol: u32);
    fn urcl_port_numb_out(number: u32);
    fn urcl_halt();
}

const MESSAGE: &str = "Hello, URCL! ";

pub fn main() {
    unsafe 
    {
        for i in 0..6 {
            for j in 0..13 {
                urcl_port_text_out(MESSAGE.as_bytes()[j as usize] as u32);
            }
            urcl_port_numb_out(i);
            urcl_port_text_out('\n' as u32);
        }

        urcl_halt();
    }
}