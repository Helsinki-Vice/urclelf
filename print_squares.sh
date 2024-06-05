python3 ./ stdlib/stdlib_sysv.urcl -lib -o bin/stdlib.o
python3 ./ examples/print_squares.urcl -o bin/print_squares.o
ld bin/print_squares.o bin/stdlib.o --no-pie -m elf_i386 -o bin/print_squares
./bin/print_squares
