"""Derive benchmark hooks before the case's immutable file inventory is made."""
from pathlib import Path


def replace_once(path, old, new):
    text = path.read_text()
    if text.count(old) != 1:
        raise ValueError('Benchmark hook anchor missing/ambiguous: ' + str(path))
    path.write_text(text.replace(old, new))


def prepare(source, route):
    z = source / '.deps/fake-08/libs/z8lua'
    runtime = source / 'src/runtime/runtime.cpp'
    if 'hash_seed' in route:
        state = z / 'lstate.c'
        if 'P8P_BENCH_HASH_SEED' not in state.read_text():
            replace_once(state, '  g->seed = makeseed(L);', '''#if defined(P8P_BENCH_HASH_SEED)
  g->seed = (unsigned int)P8P_BENCH_HASH_SEED;
#else
  g->seed = makeseed(L);
#endif''')
        # Read the actual state rather than trusting flags or a source string.
        with runtime.open('a') as f:
            f.write('''\nextern "C" void pico_bench_snapshot(p8p_runtime_t *rt, unsigned *out) {
    global_State *g = G(rt->lua);
    out[0]=g->seed; out[1]=(unsigned)gettotalbytes(g);
    out[2]=(unsigned)g->GCdebt; out[3]=g->gcstate; out[4]=g->strt.nuse;
}\n''')
    if not route.get('trace_gc'):
        return
    replace_once(runtime, 'static void *lua_pool_alloc(void *, void *pointer, size_t old_size,',
                 'static void *lua_pool_alloc_impl(void *, void *pointer, size_t old_size,')
    anchor='/* Start a collection cycle when the heap reaches 4x the live data instead of'
    replace_once(runtime, anchor, '''#include "trace.h"
static void *lua_pool_alloc(void *ud, void *p, size_t old_size, size_t new_size) {
    return pico_bench_alloc(lua_pool_alloc_impl, ud, p, old_size, new_size);
}

''' + anchor)
    gc = z / 'lgc.c'
    replace_once(gc, '#include "lgc.h"', '#include "lgc.h"\n#include "trace.h"')
    for signature, hook in [
        ('void luaC_forcestep (lua_State *L) {', 'PicoGCScope bench_gc(false);'),
        ('void luaC_fullgc (lua_State *L, int isemergency) {', 'PicoGCScope bench_gc(true);'),
        ('static lu_mem singlestep (lua_State *L) {', 'PicoGCStep bench_step(&G(L)->gcstate);'),
        ('static l_mem atomic (lua_State *L) {', 'PicoGCTimer bench_atomic(&pico_bench.atomic_time);'),
        ('static void GCTM (lua_State *L, int propagateerrors) {', 'PicoGCTimer bench_finalizer(&pico_bench.finalizer_time);'),
    ]:
        replace_once(gc, signature, signature + '\n  ' + hook)
