MAKEFLAGS += --silent

stdlibc:
	python3 ./ stdlib/stdlib.urcl -o bin/stdlib.o -lib

graphics_runtime64:
	gcc stdlib/stdlib_sdl2.c -c -o bin/stdlib_graphics.o -no-pie -lSDL2

halt:
	python3 ./ examples/halt.urcl -o bin/halt.o
	ld bin/halt.o -m elf_i386 -o bin/halt
	bin/halt

halt64:
	python3 ./ examples/halt.urcl -o bin/halt64.o -m x64
	ld bin/halt64.o -o bin/halt64
	bin/halt64

hang:
	python3 ./ examples/hang.urcl -o bin/hang.o
	ld bin/hang.o -m elf_i386 -o bin/hang
	bin/hang

hello_c: stdlibc
	gcc examples/hello.c -c -m32 --no-pie -o bin/hello.o
	ld bin/hello.o bin/stdlib.o --no-pie -m elf_i386 -o bin/hello
	./bin/hello

hello:
	python3 ./ examples/hello.urcl -o bin/hello.o
	ld bin/hello.o -m elf_i386 -o bin/hello
	bin/hello

hello64: # No worky
	python3 ./ examples/hello.urcl -o bin/hello64.o -m x64
	ld bin/hello64.o -o bin/hello64
	bin/hello64

squares: stdlibc
	python3 ./ examples/print_squares.urcl -o bin/print_squares.o
	ld bin/print_squares.o bin/stdlib.o --no-pie -m elf_i386 -o bin/print_squares
	./bin/print_squares

alphabet:
	python3 ./ examples/alphabet.urcl -o bin/alphabet.o
	ld bin/alphabet.o --no-pie -m elf_i386 -o bin/alphabet
	./bin/alphabet

m0:
	gcc stdlib/m0.c -c -o bin/m0.o -m32 -no-pie

mandelbrot: stdlibc m0 # No worky, using assembler output for now
	python3 ./ examples/mandelbrot.urcl -o bin/mandelbrot.s -f asm
	
glibc_test:
	python3 ./ examples/glibc_test.urcl -lib -o bin/glibc_test.o
	gcc bin/glibc_test.o -m32 -no-pie -o bin/glibc_test
	bin/glibc_test

hello_rust: stdlibc m0
	rustc examples/hello.rs -o bin/hello_rust --target i686-unknown-linux-gnu -Clink-arg=./bin/stdlib.o
	bin/hello_rust

graphics:
	python3 ./ examples/alphabet.urcl -o bin/alphabet.o
	ld bin/alphabet.o --no-pie -m elf_i386 -o bin/alphabet
	./bin/alphabet

dw: # Work in progress
	python3 ./ examples/dw.urcl -o bin/dw.o

clean:
	rm bin/*
	clear