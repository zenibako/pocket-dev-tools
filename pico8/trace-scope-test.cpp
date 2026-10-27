#include "trace.h"
#include <assert.h>
PicoBench pico_bench={};
static uint64_t tick;
uint64_t pico_bench_clock(){return ++tick;}
int main(){
 pico_bench.phase=2;
 { PicoGCScope outer(false); {PicoGCScope nested(true);} }
 assert(pico_bench.depth==0 && pico_bench.gc_calls==1 && pico_bench.full_calls==0);
 assert(pico_bench.gc_time==pico_bench.gc_phase_time[2] && pico_bench.gc_time>0);
 { PicoGCScope full(true); }
 assert(pico_bench.gc_calls==2 && pico_bench.full_calls==1);
 unsigned char state=4;
 {PicoGCStep step(&state);state=5;}
 assert(pico_bench.completed==1 && pico_bench.steps[4]==1);
}
