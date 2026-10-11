// Deterministic cart route shared by native, RV32 QEMU and checkpoint replay.
#include "p8p/cart.h"
#include "p8p/runtime.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifndef PICO_NATIVE
#include "frame.h"
#endif

static unsigned hash(const void *data, size_t size) {
    const unsigned char *p = (const unsigned char *)data;
    unsigned h = 2166136261u;
    while (size--) h = (h ^ *p++) * 16777619u;
    return h;
}

// Match compat_scan.cpp's seed-7 route, limited to the six game buttons.
static unsigned input(unsigned frame, unsigned *rng) {
#ifdef PICO_INPUT_NONE
    (void)frame; (void)rng;
    return 0;
#endif
    if (frame < 90) return 0;
    if (frame == 90 || frame == 150 || frame == 210) return 1u << 4;
    *rng = *rng * 1664525u + 1013904223u;
    unsigned b = 0, d = (*rng >> 28) & 7u;
    if (d < 4) b |= 1u << d;
    if (((*rng >> 8) & 15u) == 0) b |= 1u << 4;
    if (((*rng >> 16) & 15u) == 0) b |= 1u << 5;
    return b;
}

static void fail(const char *reason, unsigned frame) {
    char line[1024];
    snprintf(line, sizeof(line), "FRAMEHARNESS FAIL pico8 frame=%u %s\n", frame, reason);
#ifdef PICO_NATIVE
    fputs(line, stdout);
    exit(2);
#else
    frame_fail(line);
#endif
}

static void emit(const char *line) {
#ifdef PICO_NATIVE
    fputs(line, stdout);
#else
    frame_output(line);
#endif
}

static void run(const char *path, unsigned total) {
    FILE *f = fopen(path, "rb");
    if (!f) fail("cart file unavailable", 0);
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    rewind(f);
    if (size <= 0 || size > 16 * 1024 * 1024) fail("invalid cart size", 0);
    unsigned char *data = (unsigned char *)malloc((size_t)size);
    if (!data || fread(data, 1, (size_t)size, f) != (size_t)size) fail("cart read", 0);
    fclose(f);
    p8p_cart_t cart = {};
    int loaded = !memcmp(data, "\x89PNG", 4)
        ? p8p_cart_load_png_memory(data, (size_t)size, &cart)
        : p8p_cart_load_text_memory(data, (size_t)size, &cart);
    free(data);
    if (loaded) fail("cart decode", 0);
    p8p_runtime_t *rt = p8p_runtime_create();
    if (!rt || p8p_runtime_load(rt, &cart)) fail(rt ? p8p_runtime_error(rt) : "runtime allocation", 0);
#ifdef PICO_SETUP
    int setup_value = 0;
    if (p8p_runtime_debug_eval_int(rt, PICO_SETUP, &setup_value)) fail("setup expression", 0);
#endif
    unsigned rng = 7;
    int16_t pcm[1600 * 2];
    for (unsigned frame = 0; frame < total; ++frame) {
#ifndef PICO_NATIVE
        if (frame == 180) frame_suspend();
        frame_clock = (uint64_t)frame * 1000000000ull / (unsigned)p8p_runtime_target_fps(rt);
#endif
        unsigned buttons = input(frame, &rng);
#ifndef PICO_NATIVE
        unsigned begin = frame_host ? 0 : *(volatile unsigned *)0x40000004u;
#endif
        if (p8p_runtime_step(rt, (uint8_t)buttons)) fail(p8p_runtime_error(rt), frame);
        unsigned fps = (unsigned)p8p_runtime_target_fps(rt);
        unsigned pairs = 48000u / fps;
        if (pairs > 1600) fail("unexpected target FPS", frame);
        p8p_runtime_audio_render(rt, pcm, pairs);
#ifndef PICO_NATIVE
        unsigned elapsed = frame_host ? 0 : *(volatile unsigned *)0x40000004u - begin;
#else
        unsigned elapsed = 0;
#endif
        unsigned row[8] = {frame, hash(p8p_runtime_framebuffer(rt), 128 * 128),
            hash(p8p_runtime_screen_palette(rt), 16), hash(pcm, pairs * 4), pairs, buttons, fps, 0};
#ifndef PICO_NATIVE
        if (frame < 180) continue;
        if (!frame_host && memcmp(row, frame_expected[frame - 180], sizeof(row)))
            fail("pixel/palette/PCM/input/FPS oracle", frame);
#endif
        char line[256];
        snprintf(line, sizeof(line), "PICOFRAME %u %u %08x %08x %08x %u %u %u\n",
            frame, elapsed, row[1], row[2], row[3], pairs, buttons, fps);
        emit(line);
    }
    emit("PICOHARNESS PASS HAL init\n");
#ifndef PICO_NATIVE
    if (frame_host) frame_syscall(93, 0, 0, 0, 0, 0, 0);
    for (;;) {}
#else
    p8p_runtime_destroy(rt);
    p8p_cart_destroy(&cart);
#endif
}

#ifdef PICO_NATIVE
int main(int argc, char **argv) {
    if (argc != 3) return 64;
    run(argv[1], (unsigned)strtoul(argv[2], NULL, 10));
    return 0;
}
#else
extern "C" void frame_host_main(void) { run("cart.bin", 183); }

static void raw_file(const char *name, const void *data, unsigned size) {
    long fd = frame_syscall(56, -100, (long)name, 577, 0600, 0, 0);
    if (fd < 0) frame_fail("checkpoint open");
    const char *p = (const char *)data;
    while (size) {
        long n = frame_syscall(64, fd, (long)p, size, 0, 0, 0);
        if (n <= 0) frame_fail("checkpoint write");
        size -= (unsigned)n;
        p += n;
    }
    frame_syscall(57, fd, 0, 0, 0, 0, 0);
}
extern "C" void frame_checkpoint(void) {
    raw_file("checkpoint.bin", (void *)0x10400000u, (unsigned)frame_heap_cursor - 0x10400000u);
    raw_file("stack.bin", (void *)0x13f80000u, 0x7f000u);
}
#endif
