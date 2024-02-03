python3 ./ stdlib.urcl -lib -o stdlib.o
gcc examples/hello.c -c -m32 --no-pie -o hello.o
ld hello.o stdlib.o --no-pie -m elf_i386 -o a.out
./a.out
