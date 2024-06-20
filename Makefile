MAKEFLAGS += --silent

stdlib:
	python3 ./ stdlib/stdlib.urcl -lib -o bin/stdlib.o

stdlib64:
	python3 ./ stdlib/stdlib64.urcl -lib -o bin/stdlib.o -m x64

hello_c:
	make stdlib
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

squares:
	python3 ./ examples/print_squares.urcl -o bin/print_squares.o
	make stdlib
	ld bin/print_squares.o bin/stdlib.o --no-pie -m elf_i386 -o bin/print_squares
	./bin/print_squares

alphabet:
	python3 ./ examples/alphabet.urcl -o bin/alphabet.o
	ld bin/alphabet.o --no-pie -m elf_i386 -o bin/alphabet
	./bin/alphabet

mandelbrot: # No worky
	python3 ./ examples/mandelbrot.urcl -o bin/mandelbrot.o
	make stdlib
	gcc stdlib/m0.c -c -o bin/m0.o -m32 -no-pie
	ld bin/mandelbrot.o bin/stdlib.o bin/m0.o -o bin/mandelbrot -m elf_i386 --no-pie
	objdump bin/mandelbrot -d -M intel > mandelbrot_code.txt

glibc_test:
	python3 ./ examples/glibc_test.urcl -lib -o bin/glibc_test.o
	gcc bin/glibc_test.o -m32 -no-pie -o bin/glibc_test
	bin/glibc_test

hello_rust:
	make stdlib
	rustc examples/hello.rs -o bin/hello_rust --target i686-unknown-linux-gnu -Clink-arg=./bin/stdlib.o
	bin/hello_rust

clean:
	rm bin/*
	clear