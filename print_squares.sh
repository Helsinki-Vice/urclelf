python3 ./ stdlib.urcl -lib -o stdlib.o
python3 ./ examples/print_squares.urcl -o print_squares.o
ld print_squares.o stdlib.o --no-pie -m elf_i386 -o a.out
./a.out
