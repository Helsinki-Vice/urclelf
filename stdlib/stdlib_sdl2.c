/*
    Implemention of the urclelf stdlib in C using SDL2 and the C standard library.
*/

#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>
#include <locale.h>
#include <time.h>

#include <SDL2/SDL.h>
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>

#define URCL_PIXEL_SIZE 4
#define URCL_SCREEN_WIDTH 128
#define URCL_SCREEN_HEIGHT 128
#define URCL_COLOR_RED   0b1111100000000000
#define URCL_COLOR_GREEN 0b0000011111100000
#define URCL_COLOR_BLUE  0b0000000000011111
#define URCL_COLOR_WHITE URCL_COLOR_RED | URCL_COLOR_GREEN | URCL_COLOR_BLUE

static SDL_Window* window = NULL;
static SDL_Renderer* renderer = NULL;
static int global_x_coord = 0;
static int global_y_coord = 0;
static int global_color = 0;
static int global_sleep_time_deciseconds = 10;
static int global_current_buffer_state = 0;
static int global_graphics_are_init = 0;
static int global_port_supported_check = 0;
static int* global_data_pointer = 0;
static SDL_Cursor *global_cursor;
static int global_mouse_x = 6;
static int global_mouse_y = 10;
static int global_mouse_button_state = 0;


const int SUPPORTED_PORT_NUMBERS[] = {1, 2, 5, 8, 9, 10, 11, 16, 17, 19, 20, 24, 25, 26, 27, 28, 29, 32, 33, 40, 44};

void urcl_io_init() {
    if (SDL_Init(SDL_INIT_VIDEO) < 0) {
        fprintf(stderr, "could not initialize sdl2: %s\n", SDL_GetError());
    }

    SDL_CreateWindowAndRenderer(URCL_SCREEN_WIDTH * URCL_PIXEL_SIZE, URCL_SCREEN_HEIGHT * URCL_PIXEL_SIZE, 0, &window, &renderer);
    if (window == NULL) {
        fprintf(stderr, "could not create window: %s\n", SDL_GetError());
    }
    if (renderer == NULL) {
        fprintf(stderr, "could not create renderer: %s\n", SDL_GetError());
    }

    SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);
    SDL_RenderClear(renderer);
    SDL_RenderPresent(renderer);
    global_cursor = SDL_GetCursor();
    global_graphics_are_init = 1;
}

void urcl_io_close() {
    SDL_DestroyWindow(window);
    SDL_Quit();
}

void poll_for_events() {
    SDL_Event event;
    while (SDL_PollEvent(&event)) {
        if(event.type == SDL_QUIT) {
            exit(0);
        } else if(event.type == SDL_MOUSEBUTTONDOWN) {
            if(event.button.button == SDL_BUTTON_LEFT) {
                global_mouse_button_state |= 1;
            } else if(event.button.button == SDL_BUTTON_RIGHT) {
                global_mouse_button_state |= 2;
            } else {
                global_mouse_button_state |= 4;
            }
        }
        else if(event.type == SDL_MOUSEBUTTONUP) {
            global_mouse_button_state = 0;
        }
        
    }
}
// GENERAL

// 1
void urcl_port_text_out(int symbol) {
    putchar(symbol);
}
int urcl_port_text_in() {
    return getchar();
}

// 2
void urcl_port_numb_out(int number) {
    printf("%d", number);
}
int urcl_port_numb_in() {
    int result;
    scanf("%d", &result);
    return result;
}

// 5
void urcl_port_supported_out(int port) {
    global_port_supported_check = port;
}
int urcl_port_supported_in() {
    
    for(int i = 0; i < 21; i++) {
        if(SUPPORTED_PORT_NUMBERS[i] == global_port_supported_check) {
            return 0;
        }
    }
    return global_port_supported_check;
}

// GRAPHICS

// 8
void urcl_port_x_out(int x) {
    global_x_coord = x;
}
int urcl_port_x_in() {
    return URCL_SCREEN_WIDTH;
}

// 9
void urcl_port_y_out(int y) {
    global_y_coord = y;
}
int urcl_port_y_in() {
    return URCL_SCREEN_HEIGHT;
}

int urcl_port_mouse_x_in() {
    poll_for_events();
    SDL_GetMouseState(&global_mouse_x, NULL);
    
    return global_mouse_x / URCL_PIXEL_SIZE;
}
int urcl_port_mouse_y_in() {
    poll_for_events();
    SDL_GetMouseState(NULL, &global_mouse_y);

    return global_mouse_y / URCL_PIXEL_SIZE;
}

int urcl_port_mouse_buttons_in() {
    return global_mouse_button_state;
}

// 10
void urcl_port_color_out(int color) {
    global_color = color;
    int alpha = (color & 0b0000000000000000) >> 24; // Unused for now
    int red = (color &   0b1111100000000000) >> 11;
    int green = (color & 0b0000011111100000) >> 5;
    int blue = color &   0b0000000000011111;
    SDL_Rect rect = {global_x_coord * URCL_PIXEL_SIZE, global_y_coord * URCL_PIXEL_SIZE, URCL_PIXEL_SIZE, URCL_PIXEL_SIZE};
    SDL_SetRenderDrawColor(renderer, red << 3, green << 2, blue << 3, 255);
    SDL_RenderFillRect(renderer, &rect);
}
int urcl_port_color_in() {
    return 0;
}

// 11
void urcl_port_buffer_out(int buffer_state) {

    if(global_graphics_are_init == 0) {
        urcl_io_init();
    }
    if(buffer_state == 0) {
        SDL_RenderPresent(renderer);
        SDL_Rect rect = {0, 0, URCL_SCREEN_WIDTH * URCL_PIXEL_SIZE, URCL_SCREEN_HEIGHT * URCL_PIXEL_SIZE};
        SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);
        //SDL_RenderFillRect(renderer, &rect);
    }
}
int urcl_port_buffer_in() {
    return global_current_buffer_state;
}

// 16
void urcl_port_ascii8_out(int symbol) {putchar(symbol);}
int urcl_port_ascii8_in() {return getchar();}
// 17
void urcl_port_char5_out(int symbol) {putchar(symbol);}
int urcl_port_char5_in() {return getchar();}
// 18
void urcl_port_char6_out(int symbol) {putchar(symbol);}
int urcl_port_char6_in() {return getchar();}
// 19
void urcl_port_char7_out(int symbol) {putchar(symbol);}
int urcl_port_char7_in() {return getchar();}
// 20
void urcl_port_utf8_out(int symbol) {putchar(symbol);}
int urcl_port_utf8_in() {return getchar();}

// NUMBERS

// 24
void urcl_port_int_out(int number) {
    printf("%d", number);
};


//44
void urcl_port_wait_out(int deciseconds) {
    global_sleep_time_deciseconds = deciseconds;
}

int urcl_port_wait_in() {
    SDL_Delay((double)global_sleep_time_deciseconds * 100.0);
    return 0;
}