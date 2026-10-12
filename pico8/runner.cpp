// Deterministic cart route shared by native, RV32 QEMU and checkpoint replay.
#include "p8p/cart.h"
#include "p8p/runtime.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifndef PICO_NATIVE
#include "frame.h"
#endif

#ifndef PICO_WARMUP_FRAMES
#define PICO_WARMUP_FRAMES 180
#endif
#ifndef PICO_MEASURED_FRAMES
#define PICO_MEASURED_FRAMES 3
#endif
#ifndef PICO_TRACE_FRAMES
#define PICO_TRACE_FRAMES 600
#endif
#ifdef P8P_BENCH_HASH_SEED
extern "C" void pico_bench_snapshot(p8p_runtime_t *, unsigned *);
#endif
#ifdef PICO_TRACE_GC
#include "trace.h"
#ifdef PICO_NATIVE
#include <time.h>
#endif
PicoBench pico_bench = {};
uint64_t pico_bench_clock() {
#ifdef PICO_NATIVE
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ull + ts.tv_nsec;
#else
    return frame_host ? 0 : *(volatile unsigned *)0x40000004u;
#endif
}
void *pico_bench_alloc(void *(*fn)(void *,void *,size_t,size_t), void *ud,
                      void *ptr, size_t old_size, size_t new_size) {
    uint64_t begin = pico_bench_clock();
    void *out = fn(ud, ptr, old_size, new_size);
    uint64_t elapsed = pico_bench_clock() - begin;
    pico_bench.alloc_time += elapsed;
    if(pico_bench.depth) pico_bench.alloc_gc_time += elapsed;
    if(!ptr) ++pico_bench.new_calls;
    else if(!new_size) ++pico_bench.free_calls;
    else ++pico_bench.resize_calls;
    if(new_size && !out) ++pico_bench.failed_calls;
    else { pico_bench.requested += new_size;
           pico_bench.released += ptr ? old_size : 0; }
    return out;
}
static void profile(void *, p8p_runtime_profile_event_t event) {
    if(event == P8P_PROFILE_UPDATE_BEGIN) pico_bench.phase=1;
    else if(event == P8P_PROFILE_DRAW_BEGIN) pico_bench.phase=2;
    else pico_bench.phase=3;
}
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

static void run(const char *path, unsigned total, bool long_trace=false) {
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
#ifdef P8P_BENCH_HASH_SEED
    unsigned initial[5]; pico_bench_snapshot(rt, initial);
    if(initial[0] != (unsigned)P8P_BENCH_HASH_SEED) fail("final hash seed mismatch", 0);
    char seed_line[96];
    snprintf(seed_line, sizeof(seed_line), "PICOSEED %u\n", initial[0]); emit(seed_line);
#endif
#ifdef PICO_TRACE_GC
    p8p_runtime_set_profile_hook(rt, profile, NULL);
#ifdef PICO_NATIVE
    emit("PICOTIME unit=ns source=CLOCK_MONOTONIC\n");
#else
    emit(frame_host ? "PICOTIME unit=none source=QEMU\n" : "PICOTIME unit=cycles source=RTL_MMIO\n");
#endif
#endif
    unsigned rng = 7;
    int16_t pcm[1600 * 2];
    for (unsigned frame = 0; frame < total; ++frame) {
#ifndef PICO_NATIVE
        if (!long_trace && frame == PICO_WARMUP_FRAMES) frame_suspend();
#ifdef PICO_CPU_HZ
        if (!frame_host && frame == PICO_WARMUP_FRAMES) {
            unsigned hz = *(volatile unsigned *)0x400000d4u;
            if (hz != PICO_CPU_HZ) fail("CPU clock register mismatch", frame);
            char clock_line[64];
            snprintf(clock_line, sizeof(clock_line), "PICOCPU %u\n", hz); emit(clock_line);
        }
#endif
        frame_clock = (uint64_t)frame * 1000000000ull / (unsigned)p8p_runtime_target_fps(rt);
#endif
        unsigned buttons = input(frame, &rng);
#ifndef PICO_NATIVE
        unsigned begin = frame_host ? 0 : *(volatile unsigned *)0x40000004u;
#endif
#ifdef PICO_TRACE_GC
        memset(&pico_bench, 0, sizeof(pico_bench));
        pico_bench.frame_start=pico_bench_clock();
#endif
        if (p8p_runtime_step(rt, (uint8_t)buttons)) fail(p8p_runtime_error(rt), frame);
        unsigned fps = (unsigned)p8p_runtime_target_fps(rt);
        unsigned pairs = 48000u / fps;
        if (pairs > 1600) fail("unexpected target FPS", frame);
#ifdef PICO_TRACE_GC
        pico_bench.phase=4;
#endif
        p8p_runtime_audio_render(rt, pcm, pairs);
#ifndef PICO_NATIVE
        unsigned elapsed = frame_host ? 0 : *(volatile unsigned *)0x40000004u - begin;
#else
        unsigned elapsed = 0;
#endif
#ifdef PICO_TRACE_GC
        pico_bench.frame_time=pico_bench_clock()-pico_bench.frame_start;
        if(pico_bench.depth) fail("unbalanced GC trace scope", frame);
#endif
        unsigned row[8] = {frame, hash(p8p_runtime_framebuffer(rt), 128 * 128),
            hash(p8p_runtime_screen_palette(rt), 16), hash(pcm, pairs * 4), pairs, buttons, fps, 0};
#ifndef PICO_NATIVE
        if (!long_trace && frame < PICO_WARMUP_FRAMES) continue;
        if (!frame_host && memcmp(row, frame_expected[frame - PICO_WARMUP_FRAMES], sizeof(row)))
            fail("pixel/palette/PCM/input/FPS oracle", frame);
#endif
        char line[256];
        snprintf(line, sizeof(line), "PICOFRAME %u %u %08x %08x %08x %u %u %u\n",
            frame, elapsed, row[1], row[2], row[3], pairs, buttons, fps);
        emit(line);
#ifdef PICO_TRACE_GC
        unsigned state[5]; pico_bench_snapshot(rt, state);
        char trace[768];
        // Times are inclusive; allocation inside GC is explicitly reported to avoid double counting.
        snprintf(trace, sizeof(trace),
            "PICOGC %u %llu %u %u %u %u %llu %llu %llu %llu %llu %u %u %u %u %d %u %u %llu %llu %llu %llu %llu %llu %llu %u %u %u %u %u %u\n",
            frame, (unsigned long long)pico_bench.frame_time,
            pico_bench.new_calls, pico_bench.resize_calls, pico_bench.free_calls, pico_bench.failed_calls,
            (unsigned long long)pico_bench.requested, (unsigned long long)pico_bench.released,
            (unsigned long long)pico_bench.alloc_time, (unsigned long long)pico_bench.alloc_gc_time,
            (unsigned long long)pico_bench.gc_time, pico_bench.gc_calls, pico_bench.full_calls,
            pico_bench.completed, state[1], (int)state[2], state[3], state[4],
            (unsigned long long)pico_bench.atomic_time, (unsigned long long)pico_bench.finalizer_time,
            (unsigned long long)pico_bench.gc_phase_time[0], (unsigned long long)pico_bench.gc_phase_time[1],
            (unsigned long long)pico_bench.gc_phase_time[2], (unsigned long long)pico_bench.gc_phase_time[3],
            (unsigned long long)pico_bench.gc_phase_time[4],
            pico_bench.steps[0],pico_bench.steps[1],pico_bench.steps[2],
            pico_bench.steps[3],pico_bench.steps[4],pico_bench.steps[5]);
        emit(trace);
#endif
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
extern "C" void frame_host_main(void) {
    FILE *marker=fopen("trace-long", "rb");
    bool long_trace=marker!=NULL;
    if(marker) fclose(marker);
    run("cart.bin", long_trace ? PICO_TRACE_FRAMES : PICO_WARMUP_FRAMES + PICO_MEASURED_FRAMES, long_trace);
}

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
