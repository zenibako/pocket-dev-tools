"""Optional per-case route: setup expression and input override."""
import json
import re


def validate(setup, buttons, hash_seed=None, warmup=180, measured=3, frames=600, trace_gc=False):
    route = {}
    if setup:
        # Becomes a C string literal and a "return EXPR" Lua chunk of at most 255 bytes.
        if not re.fullmatch(r'[ !#-\[\]-~]{1,200}', setup):
            raise ValueError('Setup expression must be 1-200 printable ASCII characters without quotes or backslashes')
        route['setup'] = setup
    if buttons != 'seed7':
        route['input'] = buttons
    if hash_seed is not None:
        if type(hash_seed) is not int or not 0 <= hash_seed <= 0xffffffff:
            raise ValueError('Hash seed must be an unsigned 32-bit integer')
        route['hash_seed'] = hash_seed
    if not (0 <= warmup <= 100000 and 1 <= measured <= 60 and warmup + measured <= frames <= 100000):
        raise ValueError('Invalid warmup/measured/trace frame counts')
    if (warmup, measured, frames) != (180, 3, 600):
        route.update(warmup_frames=warmup, measured_frames=measured, native_frames=frames)
    if trace_gc:
        if hash_seed is None: raise ValueError('GC traces require an explicit final hash seed')
        route['trace_gc'] = True
    return route


def flags(folder):
    path = folder / 'route.json'
    route = json.loads(path.read_text()) if path.exists() else {}
    out = []
    if route.get('setup'):
        out += ['-DP8P_RUNTIME_DEBUG', '-DPICO_SETUP="' + route['setup'] + '"']
    if route.get('input') == 'none':
        out.append('-DPICO_INPUT_NONE')
    if 'hash_seed' in route:
        seed = route['hash_seed']
        validate(None, 'seed7', seed)
        source = folder.parent / 'source/.deps/fake-08/libs/z8lua/lstate.c'
        if 'P8P_BENCH_HASH_SEED' not in source.read_text():
            raise ValueError('Final Lua seed hook missing')
        out.append(f'-DP8P_BENCH_HASH_SEED={seed}u')
    for key, macro in [('warmup_frames','PICO_WARMUP_FRAMES'), ('measured_frames','PICO_MEASURED_FRAMES'),
                       ('native_frames','PICO_TRACE_FRAMES')]:
        if key in route: out.append(f'-D{macro}={route[key]}')
    if route.get('trace_gc'): out.append('-DPICO_TRACE_GC')
    return out
