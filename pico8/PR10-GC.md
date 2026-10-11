# PR10 fixed-seed allocation and GC traces

PR10's earlier Zombie Garden speedup does not reproduce with a fixed **final**
Lua hash seed. Longer controlled traces show nearly unchanged frame cost for
both tested carts, identical allocation/collection scheduling, and identical
pixels, display palette and PCM.

## Uninstrumented timing controls

Simulated os25 at 100 MHz, frames 180–191; 180 warm-up frames. These means
include runtime stepping and fixed PCM rendering, and exclude output hashing,
UART, OS scheduling, presentation and hardware audio pumping.

| Cart / scene | Target | Before PR10, ms | After PR10, ms | Frame cost change |
|---|---:|---:|---:|---:|
| Zombie Garden menu | 30 FPS | 22.4591 | 22.4962 | +0.166% |
| Mellow shared seed-7 route | 60 FPS | 42.8586 | 42.7116 | −0.343% |

The Zombie Garden estimate remains capped at 30 FPS. Mellow's runtime-capacity
estimate is 23.33 → 23.41 FPS. These are estimates from this 12-frame window,
not measured Pocket FPS or 600-frame averages. Pico8Pocket ships os20; the
harness uses os25. The interval starts with cold RTL caches. Small deltas can
reflect changed code/cache layout as well as instruction changes.

The window deliberately includes collection and paused phases. It overrepresents
GC compared with the full 600-frame route, especially in Mellow; do not use it
as a long-run average. This study tests these routes, not every PR10 workload.

## Longer allocation/GC scheduling traces

Each revision ran 600 frames twice natively and twice under RV32 QEMU, with
`P8P_BENCH_HASH_SEED=0x5eed1234`. The runner reads the actual Lua state and checks
that value. Every one of the 600 RV32 allocation/GC rows is identical between
revisions. The 12 checkpoint rows also exactly match the corresponding long
QEMU rows. QEMU scope times are zero and are never treated as hardware timings.

| RV32 totals over 600 frames | Zombie Garden | Mellow |
|---|---:|---:|
| Logical new allocation calls | 159,055 | 14,660 |
| Resize calls | 4,236 | 626 |
| Free calls | 156,177 | 11,875 |
| Requested-byte traffic | 7,506,960 | 1,825,320 |
| Released-byte traffic | 7,447,896 | 1,680,320 |
| Outer GC entries | 892 | 127 |
| Frames with GC | 191 | 66 |
| Completed GC cycles | 15 | 4 |

No allocation failures or outer full-GC entries occurred. Logical heap changes
agree with requested minus released bytes at every consecutive frame. Requested
traffic includes the full new size on realloc; it is not net growth or slab
reservation. A null allocation's old-size type tag is never counted as bytes.

Zombie Garden collects about every 40–42 frames, with completions at 21, 63,
104, 144, 185, 226, 266, 307, 347, 388, 428, 469, 510, 550 and 591. Mellow
completes cycles at 5, 190, 332 and 547. PR10 moves none of these events.

Zombie Garden remains on its menu throughout this six-button route: all 600
pixel hashes are the same while PCM advances. Its lawn draw loop constructs
three tables inside each of 40 iterations, plus nine tables in rectangle
helpers. The trace observes about 265 new Lua allocations per frame; the table
header/array allocations explain most of that traffic. The sampled Mellow route
has 477 distinct pixel hashes and its collection activity is much less frequent.

## GC and allocation timing

These values come from diagnostic RTL binaries over the same 12 frames. Scope
profiling changes timing, particularly when thousands of frees occur. Use the
uninstrumented controls above for PR10's speed delta.

| Diagnostic scope | Zombie before / after | Mellow before / after |
|---|---:|---:|
| Mean inclusive GC, ms/frame | 1.9955 / 1.9241 | 0.8026 / 0.7829 |
| Peak inclusive GC, ms | 11.7578 / 11.3159 | 2.2674 / 2.1895 |
| Mean allocator time outside GC, ms/frame | 0.1708 / 0.1683 | 0.1099 / 0.1167 |
| Whole diagnostic frame, mean ms | 23.5926 / 23.5483 | 43.4764 / 44.1954 |

Zombie Garden's frame 184 frees 5,710 blocks. Its diagnostic frame costs
33.4584 → 33.0259 ms, versus uninstrumented peaks of 28.2700 → 28.3213 ms.
That gap shows why inclusive diagnostic GC milliseconds must not be presented
as the uninstrumented collector's exact cost. PR10's nongc frames do not gain
materially; the controlled result is consistent with seed/GC-phase confounding in the
earlier three-frame result, rather than a demonstrated comparable
call-dispatch benefit.

Mellow's largest whole-frame cost is frame 181, while its peak GC scope is
frame 187. Its frame cost is predominantly outside the collector. The diagnostic
whole-frame result even points in the opposite direction to the clean control,
which is another reason not to compare instrumented binaries as speed tests.

GC occurs outside update/draw as well. In the old diagnostic window, Zombie's
GC totals 1.8233 ms in setup and 22.1225 ms in draw across 12 frames. Mellow's
GC totals 2.3717 ms in setup, 5.0358 ms in update and 2.2237 ms in draw. Setup
includes the collector check before allocating the frame coroutine. Release and
audio show no GC in these windows. Allocation inside GC is separately recorded;
subtract it from allocator time before adding allocator and inclusive GC costs.
Atomic/finalizer scopes are nested observations, not additional frame costs.

For further work, Zombie Garden points toward heap churn and collection pacing,
with menu-only coverage clearly separated from gameplay. Mellow points toward
interpreter/API/drawing work rather than GC as the main sustained cost. Reusing
only the frame coroutine would remove a small share of Zombie's allocations,
so these results do not establish it as a large quick win.

## Benchmark seed repair and reproducibility

The old `-Dluai_makeseed()=0u` flag replaces only an input to Lua's seed mixer;
addresses still change the final value. The port's benchmark patch replaces
`g->seed` after mixing, only when `P8P_BENCH_HASH_SEED` is defined. The scanner
validates `HASH_SEED` and uses that hook; production seeding is unchanged. It
also runs on macOS without requiring Linux `setarch`/`realpath -m`.

Port fix: signed local commit `a7c37a9`, in the isolated source clone
`experiments/pico8-sources/calls-gc-20261011/candidate`. It is based on merged
PR10 main `442a83625d2c`; the active port checkout was not edited. Old source is
`033762e00f4d`. The only compiled source difference between the A/B snapshots
is z8lua `lvm.c`; the seed hook, allocator, route, diagnostic code, compiler
flags, CPU and simulator are matched. Cart payload hashes match all four cases. All BRAM placements fit the 14,336-byte
harness limit: old 13,510 bytes, PR10 clean 14,084, PR10 diagnostic 14,040.
No CPU, allocator policy, GC pause or dependency pin was changed.
The inner diagnostic frame clock excludes counter reset/bookkeeping included
in `PICOFRAME`; the wrapper gap is 155–824 cycles (at most 0.00824 ms).

The harness transforms copied sources before inventory, records the route,
checks final-seed readback, supports configurable replay windows, and separates
native monotonic-nanosecond timings, QEMU counters and RTL cycle timings. The
measured runner, hook injector and C++ profiling header match the final tools.

Verification: final seed 0, 0x5eed1234 and 0xffffffff across eight fresh states
each; deliberately wrong expected seed rejected; production preprocessing
identical with the macro absent; scanner repeat comparison on both carts;
44 harness tests; repeated QEMU checkpoints; exact 600-frame native and RV32
output agreement across revisions and instrumented/clean builds; all eight
quiet RTL replays and negative output controls. All eight scanout controls also pass, with memory-delivery and output
oracles intact.

Private raw evidence is preserved under `experiments/pico8/`:
`pr10-gc-main-r1`, `pr10-gc-candidate-r1`, `pr10-clean-main-r1` and
`pr10-clean-candidate-r1`. Reproduction/analysis scripts, per-frame `TRACES.csv`,
summary JSON and source clones live under
`experiments/pico8-sources/calls-gc-20261011/`. Earlier PR10 and mget experiments
remain preserved. Use [the adapter commands](README.md#fixed-final-hash-seeds-and-longer-gc-traces)
to create new immutable cases rather than modifying these inputs.

[Open the per-frame trace CSV](../experiments/pico8-sources/calls-gc-20261011/TRACES.csv),
[verified summary and evidence hashes](../experiments/pico8-sources/calls-gc-20261011/SUMMARY.json),
or [the result bundle](../experiments/pico8-sources/calls-gc-20261011/PR10-GC-results.zip).

![Allocation/GC scheduling and clean/diagnostic frame timings](/Users/chanderson/Projects/undertale-pocket/openfpga-os25-harness/experiments/pico8-sources/calls-gc-20261011/PR10-GC.png)

