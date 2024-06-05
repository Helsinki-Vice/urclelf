python3 ./ stdlib/stdlib_sysv.urcl -lib -o bin/stdlib.o
gcc examples/hello.c -c -m32 --no-pie -o bin/hello.o
ld bin/hello.o bin/stdlib.o --no-pie -m elf_i386 -o bin/hello
./bin/hello
