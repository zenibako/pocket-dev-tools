#ifndef PICO_TRACE_H
#define PICO_TRACE_H
#include <stdint.h>
#include <stddef.h>
// All hooks are inserted only in the private diagnostic snapshot.
struct PicoBench {
    unsigned phase, depth, new_calls, resize_calls, free_calls, failed_calls;
    uint64_t requested, released, alloc_time, alloc_gc_time, gc_time;
    uint64_t gc_phase_time[5], state_time[6], atomic_time, finalizer_time;
    unsigned gc_calls, full_calls, steps[6], completed;
    uint64_t frame_start, frame_time;
};
extern PicoBench pico_bench;
uint64_t pico_bench_clock();
void *pico_bench_alloc(void *(*fn)(void *,void *,size_t,size_t), void *ud,
                       void *ptr, size_t old_size, size_t new_size);
struct PicoGCScope {
    uint64_t start; unsigned phase; bool outer;
    explicit PicoGCScope(bool full) : start(pico_bench_clock()), phase(pico_bench.phase),
        outer(pico_bench.depth++ == 0) {
        if (outer) { ++pico_bench.gc_calls; if(full) ++pico_bench.full_calls; }
    }
    ~PicoGCScope() {
        --pico_bench.depth;
        if(outer) { uint64_t elapsed=pico_bench_clock()-start;
            pico_bench.gc_time+=elapsed; pico_bench.gc_phase_time[phase]+=elapsed; }
    }
};
struct PicoGCStep {
    uint64_t start; unsigned state; const unsigned char *current;
    explicit PicoGCStep(const unsigned char *s) : start(pico_bench_clock()), state(*s), current(s) {
        ++pico_bench.steps[state];
    }
    ~PicoGCStep() { pico_bench.state_time[state]+=pico_bench_clock()-start;
        if(*current==5 && state!=5) ++pico_bench.completed; }
};
struct PicoGCTimer {
    uint64_t start, *dest;
    explicit PicoGCTimer(uint64_t *p) : start(pico_bench_clock()), dest(p) {}
    ~PicoGCTimer() { *dest+=pico_bench_clock()-start; }
};
#endif
