# Revision experiments

This extension follows [ARCHITECTURE.md](../ARCHITECTURE.md) and the checkpoint
workflow in [fullframe/README.md](../fullframe/README.md). The original tooling,
frozen inputs and baseline evidence remain unchanged. These experiments use the
same pinned os25 CPU and memory RTL with independent source snapshots.

For cache diagnostics on an already verified case, use the separate
[passive observer](../cacheprobe/README.md). Its independent copies preserve
the case’s firmware, checkpoints, frame cycles and output oracles; see the
[f1d8542 Speed results](../cacheprobe/RESULTS.md) for measured refill tails and
both function rankings.

The [draw-cost comparison](2026-10-10-draw-cost-results.md) records all seven
experiment switches at revision 0134a2f, verified frame replays, and the device
rows, profiler and early-culling controls. These are three-frame simulated samples;
the device measurements cover complete benchmark sections.

The [transformed-bounds cull follow-up](2026-10-10-cull-reuse-results.md) compares
base and revised cull after rebasing onto main `e83f1c7`, with fresh dodge/field
cases. Outputs match; cull is slightly slower in both timing samples.

The [remaining experiment screen](2026-10-10-remaining-experiments.md) uses fresh
same-source controls at `bbea9be`, after rebasing onto main `e83f1c7`. Texture
fast-hit and profiler compile-out pass both games' sampled output checks. Texture
helps only the field sample modestly; profiler removal saves Deltarune time but
loses script diagnostics. Neither is established as a shared default improvement.
The subsequent `79ab365` device base/tex/base bracket records a small texture
gain: 0.41% for the Speed route, with matching surrounding base route times.
The device source includes newer main optimizations than the harness snapshot.

The [feature-preserving profiler follow-up](2026-10-10-profiler-off-results.md)
compares `79ab365` and `0f4afe1`, based on main `05b0eef`. Script times stays in
the debug menu. Timing builds improve 0.51% in Undertale Speed, 0.30% in
Deltarune Speed, and 0.79% in Deltarune Accuracy; all twelve positive and
negative RTL controls and output comparisons pass. Device testing remains.

The [rebased profiler comparison](2026-10-10-profiler-rebase-results.md) repeats
that matrix on main 308c17c using fresh e484ccc/86140c1 snapshots, and prepares
separate feature-preserving base/profiler Pocket entries.

The [Pocket profiler result](2026-10-11-profiler-device-results.md) measures the
rebased pair: all seven Deltarune Speed scene means improve and the route saves
0.88%. Accuracy also improves in all seven scenes, saving 0.45% over its route.
There is one independent pair per mode; repeatable variance remains unmeasured.

The [combined main comparison](2026-10-11-combined-main-results.md) tests merged
profiler and texture-I/O changes at dd28a6e against 6100fcc. All sampled output
and negative checks pass; Deltarune timing means improve 2.01% in Speed and 1.09%
in Accuracy. The adapter uses modeled file reads and the frozen standalone
128-pixel texture packs; physical DMA and the new embedded pack layout remain
separate validation work.

The [rebased device reports](2026-10-11-rebased-device-results.md) confirm
the embedded 64-pixel pack runs on the Pocket. The latest route is 1.46% quicker
than the preceding unlabelled report, but battle draw counts differ; it does not
isolate optimization gains. Accuracy saves 5.39% over its route against the
older FAST308 profiler build, with matching rounded draw counts; dodge saves
17.05%. That historical comparison includes all intervening merged changes.

## Export and run revisions

Import the original frozen inputs using [SETUP.md](../SETUP.md), and prepare the
full-frame toolchain and RTL using the original workflow first. Revision export
reads Git objects only; it does not build from or modify the supplied checkout.
The repository must contain the original frozen revision as well as the requested
revision. Private assets are copied from the verified original inputs.

```sh
python3 experiments.py snapshot --name baseline-f1 --revision f1d8542 --repo /path/to/port
python3 experiments.py snapshot --name candidate-1ae --revision 1ae1496 --repo /path/to/port
python3 experiments.py run --snapshot baseline-f1 --kind both --compiler /absolute/path/to/riscv64-elf-gcc
python3 experiments.py run --snapshot candidate-1ae --kind both --compiler /absolute/path/to/riscv64-elf-gcc
```

Each command prints its `CASE` path. Use those exact paths in subsequent commands:

```sh
python3 experiments.py compare --baseline BASELINE_CASE --candidate CANDIDATE_CASE --output build/review/comparison.json
python3 experiments.py report --cases BASELINE_CASE CANDIDATE_CASE --output build/review/results.json
python3 experiments.py replay --case CANDIDATE_CASE --traffic scanout
python3 experiments.py replay --case CANDIDATE_CASE --negative
```

Comparison prints `identical` or the first differing frame and field, exits 2 for
a difference, and retains both PPMs for every differing pixel frame. It compares
SHA-256 of raw RGB555 pixels, SHA-256 of raw interleaved stereo PCM and sample-pair
count. Pointer-bearing state hashes are excluded across builds. Input, source,
ELF and capture hashes must still match before comparison/reporting.

Snapshots and case directories live under ignored `experiments/`. Existing
snapshot names cannot be overwritten. Every snapshot records the exact revision,
parent manifest, exported source hashes, optional patch hash and new manifest.
Every case copies tooling and inputs independently; on macOS APFS clones share
storage blocks until written. Docker mounts only that case at `/work`; source
roots, active worktrees and SD cards are never mounted. Case identity includes
configuration and adapter/launcher hashes, so changed tooling gets a new case
while old evidence remains available through `replay`, `compare` and `report`.
An interrupted incomplete case is retained rather than silently reused.

For a renderer regression probe, export another name with `snapshot --patch
/path/to/change.patch`. Patches are restricted to runner C/header sources and
applied only inside the new private snapshot.

## Windows and switches

| Game | `--window` | Frames | Captured scene |
| --- | --- | --- | --- |
| Undertale | `flowey` | 2400–2402 | Flowey battle |
| Deltarune Chapter 1 | `field` | 2800–2802 | Party walking in the field |
| Deltarune Chapter 1 | `bmenu` | 3120–3122 | Benchmark menu/attack section, attack meters |
| Deltarune Chapter 1 | `dodge` | 3323–3325 | Enemy turn / dodging |
| Deltarune Chapter 1 | `spades` | 490–492 | Recreated Dark World spade chase, Kris alone |
| Deltarune Chapter 1 | `castle` | 150–152 | Recreated Castle Front, Kris and Susie |

The original four windows are three-frame samples of `platform/ut_bench.c`'s
route with seed 7 and fresh volatile saves. Field and menu/attack reference images
were inspected. The later windows use the controlled setup described below.
They do not cover every frame in those sections or every battle.

- `--mode accuracy` uses `--bench`; `--mode speed` uses `--bench-smooth`.
- `--kind trace|timing|both` creates separate executables. Traced builds retain
  per-opcode/event hooks and PCM checks. Timing builds contain neither
  `frame_tick` nor `frame_event` (ELF symbols checked), and omit in-loop PCM
  hashing. They still check same-binary state, pixels, VM cleanup and memory
  delivery. Capture/report metadata labels every cycle count by build kind.
- `--variant bram|sdram` selects interpreter placement. `--traffic quiet|scanout`
  selects diagnostic display contention. Validation/output are outside timing;
  replay starts with cold CPU caches at the restored process checkpoint.
- `--profile port` reads the copied port Makefile's declarative CFLAGS/BS_DEFS
  prefix. It has no global `OF_PC` or additional alignment flags. A local SDK
  declaration shim includes SDK types in host-declaration mode, then undefines
  `OF_PC`, so game/port device branches compile. Kernel service-table/ecall ABI
  is **not reproduced**. Async storage is disabled through explicit stubs.
- `--profile legacy` uses global `OF_PC`, 64-byte function/loop alignment and
  disabled native replacements. The untouched original fullframe workflow is
  the authoritative reproduction of the original numerical baseline.
- Native script replacements default on for `port`, off for `legacy`;
  `--native enabled|disabled` overrides this explicitly. Removing `OF_PC`
  otherwise changes this behavior because the port's `UT_NO_NATIVE` environment
  gate is a PC-only branch. Compare matching native settings.
- `--compiler container` uses the existing Ubuntu GCC 13.2.0 image; an absolute
  GCC path uses the host toolchain. Tested Homebrew GCC is **16.2.0**. The measured
  card compiler version was not supplied or verified and is recorded as null.
- `--alignment` explicitly adds 64-byte function/loop alignment. The copied SDK
  `sdk.mk` also adds these flags in ordinary device builds, contrary to the
  review's description of the measured card. This extension's `port` default
  intentionally follows the request for no extra alignment. Exact card flag
  parity remains unverified.
- `--extra-cflags='-DUT_CACHED_HELD_ROWS'` applies ordered experiment defines
  and undefines after the port defaults. Only single `-DNAME[=VALUE]` and
  `-UNAME` tokens are accepted; include, output, plugin and linker options
  are rejected. The exact tokens participate in case identity and appear in
  build metadata. For the profiler control use
  `--extra-cflags='-UENABLE_VM_GML_PROFILER'`. These switches create independent
  builds from the same frozen revision; they do not change source snapshots.

## Optional cost assumptions

The default is cached framebuffers, zero charged clock cost and fixed 800-pair
consumption. Optional costs do not change the original fullframe evidence:

```sh
python3 experiments.py run --snapshot device-871 --kind timing --compiler /absolute/path/to/riscv64-elf-gcc --framebuffer uncached --clock-cost 1680 --audio realtime
```

`--framebuffer uncached` places both buffers at `0x53a00000` onward, sharing SDRAM
physical storage at `0x13a00000` outside the harness heap. The copied fabric routes
both `0x10xxxxxx` and `0x50xxxxxx` to SDRAM; the CPU's PMA marks the latter uncached.
QEMU maps the alias and captures a separate framebuffer checkpoint; RTL restores
that physical checkpoint. The uncached option passed replay for both supplied
device revisions. This verifies the copied RTL alias, **not** the framebuffer
mapping of the measured v0.7 card or its measured pixel access latency.

Every build counts clock reads. `--clock-cost 1680` busy-waits at least 1,680
100 MHz cycles per RTL read (16.8 microseconds), including poll overhead. This
charges the supplied cost without implementing a kernel trap. Returned game time
remains the deterministic 16,666,667 ns-per-frame clock; game time does not follow
simulated slow-frame wall time.

`--audio realtime` polls elapsed RTL cycles and consumes at 48,000 stereo sample
pairs/second, retaining fractional consumption. It reports submitted, consumed
and underrun pair counts. Consumption excludes validation time between frames;
there is no hardware audio engine, interrupt or DMA traffic. QEMU capture retains
fixed consumption because it has no matching RTL-cycle clock. Its PCM hash/count
are therefore **explicitly excluded** from realtime RTL oracles. Cross-build PCM
comparison refuses realtime cases; use fixed audio for regression checks.
Underrun counts are model observations, not physical Pocket measurements.

## Controlled later Deltarune scenes

The [translated-picture follow-up](2026-10-14-tile-motion-results.md) keeps tile
contents cached as their placement changes, with fresh Speed/Accuracy spade,
Castle Front and Undertale controls plus pixel/audio and eviction regressions.

The [spade tile profile](2026-10-14-spade-tile-profile.md) records the subsequent
Pocket comparison, passive CPU observations and two rejected classifier trials.
Production classification was restored after both simulated regressions.

The [main 8d3cb19 rebase results](main-8d3cb19-spades-results.md) repeat the
base/sharp comparison after the shared-port rename and save-state changes.
The adapter detects `of_bench.h`, retains the real game/state modules with
native save states disabled, and supports both old and new port names. It
does not rewrite frozen inputs or earlier cases. New cases also compile the
snapshot codec's zstd dependency and record an explicit game-file fingerprint.

The [progress-scene results](2026-10-12-progress-slowdown-results.md) compare
base and battle sharpening with diagnostics off. The recreated spade chase is
expensive in both; the candidate adds 1.62% in that window and 0.81% at Castle
Front. All eight positive/negative cases and output comparisons pass.

Two additional Speed windows recreate later Chapter 1 scenes independently of
a player save: `spades` samples frames 490–492 in room 43 (`room_dark_chase2`),
and `castle` samples frames 150–152 in room 46 (`room_castle_front`). They use
the normal game objects and events, with globals set at frame 29 and a room jump
at frame 30. Spades uses Kris alone and confirmation input every 15 frames from
40 through 475 to pass the scene's opening dialogue. Castle uses Kris and Susie
with no input. Both set `darkzone=1`, `plot=60`, and `interact=0`; these are
controlled recreations, not exact imported story progress.

The setup retains benchmark seed/mode selection and volatile saves, replaces
benchmark startup to leave draw diagnostics off, and explicitly disables frame
pacing for the fixed capture clock. `FRAMESCENE` checks the room, Speed setting,
absence of Script times and draw profiling, and absence of battle-controller
sampling. The spades window also requires active, visible spades. These checks
run after frame-cycle sampling. The optional `ut_battle_ui.c` module is included
when the snapshot contains it. Scene setup participates in case identity,
cross-case comparisons, and traced/timing report pairing.

Use the normal snapshot/run workflow with `--game deltarune --window spades`
or `--window castle`, `--mode speed --kind both --profile port`. Require repeat
captures, positive RTL replay, `replay --negative` for every case, cross-revision
raw output comparisons, and traced/timing comparisons. A wrong-room expectation
can additionally test scene validation using
`--extra-cflags=-DFRAME_SCENE_EXPECT_ROOM=46` for a spades case; capture must fail
with `scene room mismatch`. Preserve this separate failed case.

Run adapter regression tests with `python3 -m unittest bench.test_progress`.
The frozen texture packs, allocator, storage and audio service models still
differ from the Pocket; these windows establish bounded simulated CPU cost.

## Verified observations (2026-10-10)

`f1d8542` versus `1ae1496` Deltarune dodging: all three Accuracy frames have
identical raw pixels, PCM and pair counts; the same comparison passes in Speed.
A private candidate renderer patch (`swr->fb[0] ^= 1` before presentation) still
passes its same-build QEMU/RTL oracle, but cross-build comparison rejects frame
3323's pixels and reports exactly one changed pixel in each frame, retaining both
PPMs. This demonstrates why same-build replay alone misses renderer regressions.

Traced versus timing outputs match in both modes for Deltarune dodge, field and
menu/attack, and Undertale Flowey, with fixed audio. Both games have
repeat captures and complete RTL replay. Traced and timing corrupted state
oracles are rejected. The legacy/container profile also passed Undertale replay.
The preserved original aggregate still passes all eight configurations, 24 frame
rows and four negative oracles, with all 1,631 frozen inputs unchanged.
The new candidate Accuracy cases also pass both games × SDRAM/BRAM ×
quiet/scanout for both traced and timing builds: 16 configurations, 48 frame rows
and eight rejected bad state oracles. Placement and traced/timing output
comparisons are identical for both games. This matrix uses fixed audio;
optional-cost cases were separately verified with BRAM/quiet.

Deltarune BRAM/quiet, port profile, Homebrew GCC 16.2.0, native scripts enabled,
Accuracy, cached framebuffer, free clock and fixed audio:

| Revision | Traced mean simulated ms | Timing mean simulated ms | Removed instrumentation ms |
| --- | ---: | ---: | ---: |
| `f1d8542` | 216.869 | 205.943 | 10.926 |
| `1ae1496` | 153.633 | 144.068 | 9.565 |

These differ from the original 318–355 ms traced baseline because the compiler,
build profile and native script acceleration also changed. Removing hooks alone
accounts only for the within-row traced/timing difference.

Timing builds with uncached framebuffer, 1,680-cycle clock charge, proportional
audio, native replacements enabled, GCC 16.2.0, BRAM/quiet:

| Revision | Mean simulated ms | Supplied device ms | Difference |
| --- | ---: | ---: | ---: |
| `871c651` | 243.310 | 220.4 | +22.910 ms (+10.39%) |
| `72eed8e` | 319.901 | 247.3 | +72.601 ms (+29.36%) |

No cost was tuned to approach these numbers. Three cold-cache frames are being
compared with a longer device benchmark section mean. The direction of the
revision change agrees, but the magnitude does not establish predictive accuracy.

The remaining difference cannot be assigned quantitatively to review items a–e
without controlled device artifacts and measurements. (a) Clock cost is a busy
wait around a virtual clock, not the real kernel. (b) The measured card alias and
pixel latencies are unconfirmed. (c) Audio submission counts disagree with device
observations: `871c651` submits 7,874–12,030 pairs/frame, exceeding the supplied
3,500–4,900 range; `72eed8e` submits 832–10,162, with 7,989–9,295 simulated
underrun pairs/frame. (d) Card compiler version and effective alignment flags are
unknown. (e) Allocator, storage/OS services and ABI remain substitutes. The sample
window, cold caches and native setting add comparison constraints. These limits
are visible in machine-readable reports; this harness does not yet answer exact
milliseconds saved on the physical Pocket.

Earlier realtime cases `481ad5453d4ba50f` and `0d1e9f41a09f81d0` dropped
consumption after the final game queue poll. They remain saved for diagnosis and
are excluded from the final report. Corrected cases are `a45eb6e5681bef97` and
`8056356773aff18f`. The launcher now rejects any realtime result whose consumed
pair count fails to cover the complete timed frame (with a small boundary margin).

Local private evidence: `build/review/results.json`, `accuracy-comparison.json`,
`speed-comparison.json`, `pixel-probe-comparison.json`, comparison PPM pairs,
case-specific ELF/maps, source/config hashes, captures, RTL results and logs.
Run the report command again after selecting cases or adding scanout results;
it verifies evidence hashes before calculating means. No assets or captured game
data belong in commits.
