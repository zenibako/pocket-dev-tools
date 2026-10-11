"""Long fixed-seed RV32 traces and native allocation/GC diagnostics.

QEMU provides counters and GC scheduling, never hardware time. RTL scopes use
100 MHz cycles; native scopes use monotonic nanoseconds. Inclusive GC includes
allocator work; alloc_gc_time must be subtracted when partitioning total time.
"""
import json
import re

FIELDS = ('frame frame_time new_calls resize_calls free_calls failed_calls requested released '
          'alloc_time alloc_gc_time gc_time gc_calls full_calls completed heap_bytes debt gc_state strings '
          'atomic_time finalizer_time gc_setup gc_update gc_draw gc_release gc_audio '
          'step_propagate step_atomic step_sweepstring step_sweepudata step_sweep step_pause').split()
TIMES = {key for key in FIELDS if key.endswith('_time') or key.startswith('gc_') and key not in {'gc_calls', 'gc_state'}}


def read(log, count, first=0):
    rows = []
    text = log.read_text()
    if '=== UART BEGIN ===' in text:
        transcripts = re.findall(r'=== UART BEGIN ===\n(.*?)\n=== UART END ===', text, re.S)
        if len(transcripts) != 1: raise ValueError('Missing or duplicate UART transcript')
        text = transcripts[0]
    for line in text.splitlines():
        if line.startswith('PICOGC '):
            values = [int(v) for v in line.split()[1:]]
            if len(values) != len(FIELDS): raise ValueError('Malformed GC record')
            row = dict(zip(FIELDS, values))
            if row['alloc_gc_time'] > row['alloc_time'] or row['alloc_gc_time'] > row['gc_time']:
                raise ValueError('Invalid allocation/GC overlap')
            if sum(row[k] for k in ('gc_setup','gc_update','gc_draw','gc_release','gc_audio')) != row['gc_time']:
                raise ValueError('GC phase total mismatch')
            rows.append(row)
    if len(rows) != count or [r['frame'] for r in rows] != list(range(first, first+count)):
        raise ValueError('Incomplete GC trace')
    return rows


def counters(rows):
    return [{k:v for k,v in row.items() if k not in TIMES} for row in rows]


def collect(case, cart, api):
    manifest = api.checked(case)
    if not manifest['route'].get('trace_gc'): raise ValueError('Case has no GC hooks')
    folder = case / 'carts' / cart['id']
    count = manifest['native_frames']
    native = [read(folder / f'native-{r}.log', count) for r in range(2)]
    if counters(native[0]) != counters(native[1]): raise ValueError('Native counters do not repeat')
    status = dict(passed=False, frames=count, seed=manifest['route']['hash_seed'], native=native,
                  logs={f'native-{r}.log':api.sha(folder / f'native-{r}.log') for r in range(2)})
    qemu, outputs = [], []
    for repeat in range(2):
        work = folder / f'long-qemu-{repeat}'
        work.mkdir()
        (work / 'cart.bin').symlink_to('../cart.bin')
        (work / 'trace-long').write_text(f'{count}-frame route; no checkpoint\n')
        log = work / 'trace.log'
        code = api.execute(api.docker(case, ['qemu-riscv32', '-B', '0x100000000', '/work/build/pico8/program.elf'],
                                      str(work.relative_to(case))), log, timeout=600)
        if code: raise ValueError('Long QEMU failed: '+str(code))
        seed = re.findall(r'^PICOSEED (\d+)$', log.read_text(), re.M)
        if seed != [str(status['seed'])]: raise ValueError('Final seed readback failed')
        outputs.append(api.parse(log, count, 0)[0])
        qemu.append(read(log, count))
        if any(row[key] for row in qemu[-1] for key in TIMES):
            raise ValueError('QEMU scope timing must be zero; hardware timing requires RTL')
        status['logs'][str(log.relative_to(folder))] = api.sha(log)
        status['logs'][str((work/'trace-long').relative_to(folder))] = api.sha(work/'trace-long')
    if qemu[0] != qemu[1] or outputs[0] != outputs[1]: raise ValueError('Long RV32 trace does not repeat')
    n = api.parse(folder / 'native-0.log', count, 0)[0]
    if api.parse(folder / 'native-1.log', count, 0)[0] != n:
        raise ValueError('Native outputs do not repeat')
    status.update(passed=outputs[0]==n, qemu=qemu, native_output_equal=outputs[0]==n,
                  timing='native ns only; QEMU counters only, all time fields zero')
    api.save(folder / 'trace.json', status)
    return dict(passed=status['passed'], frames=count, gc_cycles=sum(r['completed'] for r in qemu[0]))
