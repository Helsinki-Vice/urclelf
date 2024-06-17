/*
    Implemention of the urclelf stdlib in C using SDL2 and the C standard library.
*/

#include <SDL2/SDL.h>
#include <stdlib.h>
#include <stdio.h>
#include "stdlib.h"
#include <unistd.h>

#define URCL_SCREEN_WIDTH 64
#define URCL_SCREEN_HEIGHT 64
#define URCL_PIXEL_SIZE 8

static SDL_Window* window = NULL;
static SDL_Renderer* renderer = NULL;
static int global_x_coord = 0;
static int global_y_coord = 0;
static int global_color = 0;
static int global_sleep_time_deciseconds = 10;

void urcl_io_init() {
    if (SDL_Init(SDL_INIT_VIDEO) < 0) {
        fprintf(stderr, "could not initialize sdl2: %s\n", SDL_GetError());
    }

    SDL_CreateWindowAndRenderer(URCL_SCREEN_WIDTH * URCL_PIXEL_SIZE, URCL_SCREEN_HEIGHT * URCL_PIXEL_SIZE, 0, &window, &renderer);
    if (window == NULL) {
        fprintf(stderr, "could not create window: %s\n", SDL_GetError());
    }

    SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);
    SDL_RenderClear(renderer);
}

void urcl_io_close() {
    SDL_DestroyWindow(window);
    SDL_Quit();
}

void urcl_port_text_out(int symbol) {
    putchar(symbol);
}
void urcl_port_numb_out(int number) {
    printf("%d", number);
}
void urcl_port_x_out(int x) {
    global_x_coord = x;
}
void urcl_port_y_out(int y) {
    global_y_coord = y;
}
void urcl_port_color_out(int color) {
    global_color = color;
    SDL_Rect rect = {global_x_coord * URCL_PIXEL_SIZE, global_y_coord * URCL_PIXEL_SIZE, URCL_PIXEL_SIZE, URCL_PIXEL_SIZE};
    SDL_SetRenderDrawColor(renderer, global_color, global_color, global_color, 255);
    SDL_RenderFillRect(renderer, &rect);
    SDL_RenderPresent(renderer);
}
void urcl_port_wait_out(int deciseconds) {
    global_sleep_time_deciseconds = deciseconds;
}

int urcl_port_text_in() {
    return getchar();
}
int urcl_port_wait_in() {
    SDL_Delay((double)global_sleep_time_deciseconds * 100.0);
    return 0;
}

void urcl_halt() {
    exit(0);
}