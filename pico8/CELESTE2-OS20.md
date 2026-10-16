# Celeste 2 intro and Trailhead performance — 2026-10-16

The stationary intro scenes fit the 30 FPS runtime budget. Trailhead, the first
named level, takes **43.263 ms per complete frame**, equivalent to **23.11 FPS**
of simulated runtime capacity. Its larger object workload adds update and Lua
lookup/call work while drawing remains expensive. Garbage collection is a small
part of this window.

These are **simulated os20/90 MHz** measurements, not physical Pocket FPS.
The runner measures the runtime step plus fixed stereo PCM generation. It
excludes presentation, OS scheduling and the application's adaptive draw
skipping. The shipped application's logical and visible FPS can therefore differ
from this table. Its scheduler can halve rendering for overloaded 30 FPS carts;
23.11 is the measured capacity with every draw executed, not a prediction of
the visible FPS counter. See [the adapter's limits](README.md).

| Scene | Cart level index | Objects | Mean full frame, ms | Frame range, ms | Capacity, FPS | Capped at target, FPS |
|---|---:|---:|---:|---:|---:|---:|
| Title | 0 | 0 | 4.614 | 4.557–5.041 | 216.71 | 30.00 |
| Intro 1: bridge | 1 | 5 | 21.507 | 21.435–21.979 | 46.50 | 30.00 |
| Intro 2: tower, before hookshot | 2 | 3 | 27.739 | 27.562–28.148 | 36.05 | 30.00 |
| Trailhead: first named level | 3 | 79 | 43.263 | 43.074–43.740 | 23.11 | 23.11 |

[Machine-readable FPS and provenance](CELESTE2-OS20.csv) retains the cycle means,
uncapped capacity, scanout timing, source and ELF hashes, and private case names.
Diagnostic scanout means are respectively 4.624, 21.560, 27.818 and 43.357 ms;
this small diagnostic traffic change does not explain Trailhead's slowdown.
The first timed frame has cold CPU caches and is included in every mean.

Scenes are recreated through the original cart's `goto_level` function, with
no buttons and `level_intro=0`; the title uses an ordinary fresh launch.
Measurements cover frames 100–111 after 100 warmup frames. The player remains
in normal state 0 at (52,104), (60,232) and (12,152) respectively throughout
the gameplay windows. Intro 2 has no hookshot yet; Trailhead has it through
the cart's normal level initialization. Screenshots were inspected and level,
intro-card, hookshot, object and player-state counters checked. These samples
do not describe traversal, grappling, deaths, transitions or a whole-level mean.

Separate diagnostic binaries attribute time as follows. Instrumentation and
code layout change timing: these columns describe the diagnostic executions
and must not be added to or subtracted directly from the clean frame times above.
GC is inclusive within the other phases, not an extra cost to add.

| Scene | Update, ms | Draw, ms | PCM, ms | GC mean / peak, ms |
|---|---:|---:|---:|---:|
| Title | 0.036 | 2.380 | 2.136 | 0 / 0 |
| Intro 1 | 2.686 | 17.158 | 2.211 | 0 / 0 |
| Intro 2 | 1.311 | 23.315 | 4.054 | 0 / 0 |
| Trailhead | 14.100 | 23.930 | 6.154 | 0.048 / 0.317 |

Trailhead exceeds 33.333 ms by 9.930 ms; reaching 30 complete frames per second
requires about a **23% reduction in total runtime cost**, before presentation
and OS overhead. The application's 32 ms scheduling budget is stricter still.
The samples are consistently expensive, rather than one exceptional GC frame.

An external QEMU instruction trace of the **unchanged clean Trailhead ELF**
checks all four update/draw boundary markers in all 12 frames and preserves its
pixel/palette/PCM/input/FPS output. It records 28,294,744 coroutine instructions:
38.25% in update and about 61.7% in draw. `luaV_execute` accounts for 52.30%
of physical-function self instructions. The lookup/cache helper union accounts
for 22.43%, including inline helpers; it overlaps the VM share and cannot be
added to it. These are instruction shares, **not cycle shares**, and use no
single-lane os25 pipeline observer on the dual-issue CPU.

The cart's object inheritance repeatedly invokes a Lua forwarding `__index`
function to read `self.base[key]`. Its update, draw and collision scans process
the global object list. The tile draw loop separately performs up to 17×17
Lua tile queries, `peek`, flag tests, sprite calls, and palette resets. The cart
stores level tiles behind `peek(0x4300+...)`; an `mget` optimization would miss
this workload. Trailhead records 432 memory API calls, 608 draw-state calls and
359 helper calls per frame in the diagnostic build.

The companion [Moss Moss os20 study](MOSS-OS20.md) records two gameplay windows
at about 20 FPS capacity, with heavy iterator/callback/environment work. Include
both carts in shared VM/API optimization checks; a Celeste gain alone does not
establish a safe shared-runtime improvement.

The next optimization experiments should prioritize:

1. **Reduce inherited-property and method-call overhead without displacing
   important BRAM code.** This has both current instruction evidence and an
   earlier A/B result: prototype `cfd8c33` reduced old os20 Trailhead frame time
   by 4.33%, but regressed Moss by 5.66%. That implementation remains unsuitable
   for deployment. Rework its compiler/layout boundary and retest other carts;
   preserve mutations, hooks, errors, yields and arbitrary metamethod side
   effects. Even its previous Celeste gain was insufficient to reach 30 FPS.
2. **Reduce repeated Lua/API overhead in tile rendering.** Current palette
   resets already return early when unchanged: their diagnostic bodies total
   only about 0.36 ms/frame in Trailhead despite hundreds of calls. Optimizing
   those reset bodies again offers little; investigate call dispatch, argument
   handling and common single-value memory reads. Generic offscreen-update
   culling is unsafe because cartridge callbacks can have side effects.
3. **Target the tower's remaining cloud/pattern/sprite work with compiler
   parity established.** Intro 2's diagnostic `circfill`, patterned `rectfill`
   and `spr` bodies cost 2.30, 1.81 and 1.83 ms/frame. They explain part of its
   heavier draw workload; much drawing time remains in Lua and other calls.
   Clipped circle spans, word fills and ordinary tile blits already exist.
   Earlier work showed that GCC13's out-of-line four-byte `memcpy` calls in
   these paths were absent from the production GCC16 ELF, so removing those
   simulator calls cannot be counted as a new Pocket optimization.
4. **Measure PCM output-pair batching.** `audio.c` already synthesizes at 24 kHz
   and interpolates to 48 kHz. Processing each pair together could remove
   per-output branch/state bookkeeping while preserving odd-length calls and
   interpolation state. Trailhead's 6.15 ms diagnostic audio scope makes audio
   worth investigating, but this is an unmeasured candidate, not a promised
   saving. Arpeggio-specific work is not supported as a cause by these initial
   Celeste music patterns.

A smaller title-only opportunity is an unscaled rectangular `sspr` path.
The title's 64×32 image still uses the general scaler and costs about 0.74 ms
in the diagnostic API scope. The title already has ample headroom; this does
not address Trailhead. Repeated `time()` evaluation is also a lower-priority
candidate; its software-double path has already been removed.

Source anchors in the sibling Pico8Pocket checkout are
`src/runtime/runtime.cpp` (`api_sspr`, `api_circfill`, `api_peek`, `api_fget`,
`api_pal`, `api_palt`, `api_time`), `patches/z8lua-index-chain.patch`,
`src/runtime/audio.c:p8p_audio_render` and `src/app/scheduler.c`.
These conclusions extend the earlier private
`scene-costs-20261012-r1/CELESTE-REPORT.md`,
`forward-index-20261012-r1/final-r2/REPORT.md` and
`os20-platform-20261012-r1/REPORT.md`; their old timings are not substituted for
the fresh measurements above. Existing architecture and replay constraints
are documented in Pico8Pocket's `docs/architecture.md` and this adapter's
[README](README.md).

All eight clean/diagnostic cases pass two 600-frame native runs, repeated
same-ELF QEMU checkpoints with native equality, quiet and scanout RTL
pixel/palette/PCM/input/FPS and memory checks, and corrupted-pixel negative
controls. Clean/diagnostic output hashes match over all 600 native frames and
the RV32 windows. Native raw indexed pixels, palette and PCM were independently
exported for every clean scene and their hashes checked against its original
runner. Cross-build raw-byte identity is not claimed. The instruction parser's
positive fixture passes and its missing-marker negative fixture is rejected.

Private evidence lives under
`experiments/pico8/celeste2-os20-{title,intro1,intro2,trailhead}-{clean,diagnostic}-20261016-r2/`.
Launchers, observer derivation, verified summaries, per-frame CSV, screenshots,
raw channels and the instruction profile are preserved in
`experiments/pico8-sources/celeste2-os20-20261016-r1/`. Its `study-r2.py`,
`summarize.py`, `collect-raw.py` and `profile-trailhead.py` record the procedure.
The first sandbox-denied build attempt remains preserved separately as r1.

Pico8Pocket source: `bc2e8b6f067ed7287bf0ddc85481c5fa5693e6c0`, clean checkout.
Harness tooling: `a1568ec`, with a pre-existing unrelated `.gitignore` edit.
Final Lua seed: `0x5eed1234`, checked through runtime readback.
Cart SHA-256: `15b1f2639c8dd237ddb1176b1d9f311bb960082b780668e14c0f1d0fd8f8d96d`.
CPU SHA-256: `6f56e1794a254286d93e97b907af0ccc1ceb5658820d7e01d858f3f39ffaa6f0`.
Simulator SHA-256: `d8e55c6d8369b3215280b3006562a2607d04d2c3804ac965ce559928aa7dc4ca`.
Compiler: RV32 GCC 13.2.0, normal harness flags and bounded allocator.
The production runtime pins `pocket-runtime-a58aacd`; documented CPU-source
agreement does not establish physical timing parity. No production runtime,
dependency pin, SD card or device installation was changed.
