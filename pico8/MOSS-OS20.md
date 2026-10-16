# Moss Moss gameplay performance — 2026-10-16

Moss Moss is now tested alongside [Celeste 2](CELESTE2-OS20.md) using the same
Pico8Pocket source and pinned **os20/90 MHz** platform. Its sampled gameplay
runs at about **20 FPS of simulated runtime capacity**, against a 30 FPS target.
The principal opportunity is Lua iteration, callbacks and environment lookup.
Garbage collection contributes modest spikes but does not explain the sustained
frame cost.

| Gameplay window | Mean full frame, ms | Frame range, ms | Capacity, FPS | Target, FPS |
|---|---:|---:|---:|---:|
| Frames 180–191 | 49.831 | 41.101–53.047 | 20.07 | 30 |
| Frames 234–245, including GC completion | 50.579 | 49.165–54.191 | 19.77 | 30 |

These measurements include the runtime step and fixed PCM output. They exclude
presentation, OS scheduling, live audio delivery and adaptive frame skipping;
they are **not physical Pocket FPS**. Each 12-frame interval starts with cold
RTL CPU caches. [The CSV](MOSS-OS20.csv) retains exact values, scanout timing,
source and ELF hashes, and case identities. The first window needs roughly a
33% reduction in total runtime cost to fit 33.333 ms, before omitted costs.

The fixed final Lua seed is `0x5eed1234`, checked through runtime readback.
The existing seed-7 six-button route runs from a fresh cart for 600 frames.
Both sampled windows show active gameplay in room 19, verified by screenshots
and native/RV32 world counters. The player moves during these samples; they
are not whole-game averages or an imported hardware save.

There are **599 actors**, only **two in the current room**, and **550 actors
whose update function is the empty `noop`**. A separate current-source native
query verifies these counts at frames 180, 185, 191 and 237 while preserving
all 600 original pixel/palette/PCM/input/FPS rows. The cart updates the global
actor list through `foreach`, traverses it three times for drawing layers,
and scans it for player collisions. Off-room updates can have side effects,
so skipping them is not a generic behavior-preserving optimization.

Moss performs rendering inside `_update`; it has no separate `_draw` callback.
The overlay's zero draw time therefore does not mean rendering is free. Separate
diagnostic builds show the following inclusive scopes. Their timing and layout
differ from the clean FPS binaries, so these columns do not decompose the clean
frame means above. GC is contained within the runtime phases, not additional.

| Window | Update, ms | Separate draw, ms | PCM, ms | GC mean / peak, ms |
|---|---:|---:|---:|---:|
| 180–191 | 48.689 | 0 | 1.301 | 0.384 / 0.786 |
| 234–245 | 49.317 | 0 | 1.083 | 0.425 / 2.282 |

The later GC cycle completes at frame 237; its largest GC scope is at frame
234. Allocator time outside GC averages 0.248 and 0.203 ms respectively.
Neither allocation nor collection accounts for most of these roughly 50 ms
frames. PCM is also a small share of Moss's runtime compared with Celeste 2's
Trailhead sample.

An external instruction trace profiles the **unchanged clean 180–191 ELF**.
It preserves the reference output and validates two update boundary markers
per frame, with no draw phase. Across the interval it records 31,708,640
runtime-step instructions, about 2.64 million per frame:

| Work | Self instruction share |
|---|---:|
| Physical VM dispatch, `luaV_execute` | 48.04% |
| Call setup, `luaD_precall` | 7.22% |
| `all` iterator body | 6.95% |
| Call return, `luaD_poscall` | 3.77% |
| Table length, `luaH_getn` | 3.32% |
| Lookup/cache/environment helper union, including inline helpers | 15.86% |

The lookup union overlaps VM instructions and cannot be added to that row.
These are instruction shares, not cycle shares or recoverable speedup estimates.
The iterator body is entered 29,467 times over the 12 frames, about 2,456 times
per frame. No unvalidated single-lane os25 pipeline observer is used on os20.

The next shared-runtime experiments should cover both carts:

1. **Iterator and callback overhead.** `api_foreach` recomputes raw table length
   each iteration and fetches the current element again after the callback to
   preserve deletion behavior. Investigate direct table access and cheaper
   mutation-aware traversal; preserve holes, appends, deletion, errors, hooks
   and yields. `api_all_next` already uses direct table access and computes
   length only for empty slots; that delivered work must not be counted again.
2. **Trivial Lua calls and actor environments.** The 550 empty actor updates,
   callbacks and `_ENV` fallback tables make guarded reductions in call and
   lookup overhead worth measuring. Any shortcut must preserve observable
   hooks and side effects. This is a candidate direction, not a measured fix.
3. **Guard Celeste inheritance changes with Moss performance.** The previous
   forwarding-getter prototype improved old os20 Trailhead by 4.33% but regressed
   Moss by 5.66%, despite zero shortcut hits in Moss. Rework that implementation's
   compiler/BRAM tradeoff and require both carts' output and timing controls
   before accepting it. The fresh measurements here test the current baseline;
   they are not a new A/B test of that rejected prototype.

Both Moss windows should remain part of shared VM/API optimization validation,
together with Celeste's intro and Trailhead scenes. Recheck native/QEMU output,
the relevant RTL windows, scanout, memory and negative controls on both sides
of each future change. PCM output batching is a separate candidate, but Moss's
small audio scope makes it a lower priority for this cart.

All four clean/diagnostic cases pass two 600-frame native runs, repeated QEMU
checkpoints with native equality, quiet and scanout RTL output/memory checks,
and deliberately corrupted pixel oracles. Diagnostic output hashes equal the
clean output over all 600 native frames and both RV32 windows. Both diagnostics
also pass repeated 600-frame QEMU allocation/GC traces. Native raw pixel,
palette and PCM channels were exported and checked against the clean runner;
cross-build raw-byte identity is not claimed. The instruction parser's positive
fixture passes and its missing-marker negative fixture is rejected.

Successful private cases are
`experiments/pico8/moss-os20-steady-{clean,diagnostic}-20261016-r1/` and
`experiments/pico8/moss-os20-gc-{clean,diagnostic}-20261016-r2/`.
Launchers, full summaries, per-frame CSV, raw output, world queries, screenshots
and the instruction profile are under
`experiments/pico8-sources/moss-os20-20261016-r1/`.
`origin-final.json` identifies the successful cases; `study.py`, `resume.py`,
`profile.py`, `finish-native.py` and `summarize.py` preserve the procedure.
The disk-full cases and trace attempt remain separate. The redundant 91 MB
compiler-error log from the failed supplementary exporter was removed with
user approval; no completed measurement or baseline evidence was deleted.

Pico8Pocket source: `bc2e8b6f067ed7287bf0ddc85481c5fa5693e6c0`, clean checkout,
matching the Celeste study. Tooling is based on harness commit `180412a`, with
the pre-existing unrelated `.gitignore` edit preserved. CPU/simulator provenance,
GCC 13.2.0 flags, bounded allocator and physical timing limits match the
[Celeste report](CELESTE2-OS20.md) and [adapter guidance](README.md).
No production runtime, dependency pin or device installation changed.
