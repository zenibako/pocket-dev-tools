---
name: os25-harness
description: Test Pico8Pocket on the isolated os20/90 MHz RTL adapter, or Butterscotch Undertale and Deltarune Chapter 1 on os25. Use for fixed-seed cart performance comparisons, baseline/candidate output replay, supported cache/pipeline analysis, sprite probes or hardware calibration evidence.
---

# openFPGA replay: Pico8Pocket os20 and Butterscotch os25

Use the standalone `openfpga-os25-harness` repository for functional RV32 replay
and simulated CPU/cache/memory measurements. Desktop captures check broader
scenes; the harness measures selected target workloads; a Pocket run checks
actual OS, SD, display/audio and board behavior. Select **os20 at 90 MHz for
Pico8Pocket performance** and os25 at 100 MHz for Butterscotch. Pico8Pocket's
separate adapter matches its documented CPU configuration; exact equivalence to
the shipped bitstream and complete hardware timing parity remain unproven.
Do not generalize the bounded cart/scene or game/chapter evidence.

## Locate and verify

Use the harness path supplied by the user, an `OS25_HARNESS_ROOT` environment
value, or a sibling `openfpga-os25-harness` checkout next to the Butterscotch
checkout. Verify `AGENTS.md`, `run.py`, `experiments.py` and `cpu-lock.json` are
present. If unavailable, locate the existing checkout or report what is missing;
do not silently substitute the old `undertale-vm-os25-harness` baseline directory.
Commands below run from the located harness root. Read its `AGENTS.md`,
`README.md`, and the workflow README selected below.

```sh
python3 run.py verify
```

A fresh clone needs private inputs; read `SETUP.md` and use `bootstrap.py` to
import compatible copies. Source dependencies alone do not provide game assets,
musl archives or process checkpoints. Frozen input hashes and `cpu-lock.json`
are intentional. A sibling port edit does not alter the frozen `f1d8542` runner.

## Choose the smallest relevant workload

| Need | Launcher | Read under the harness root |
| --- | --- | --- |
| Pico8Pocket runtime, fixed-seed cart/scene A/B | `pico8/cpu_platform.py`, `pico8/run.py` with explicit `--platform os20` | `pico8/README.md` |
| Butterscotch VM leaf events / synthetic interpreter checks | `run.py` | `README.md` |
| Original complete-frame matrix | `fullframe/run.py`, `fullframe/report.py` | `fullframe/README.md` |
| A current port revision or optimization | `experiments.py snapshot/run/compare/report` | `bench/README.md` |
| Cache refills, retirement/CPI, FPU or dependency waits | `cache_profile.py` on an exact successful case | `cacheprobe/README.md` |
| Direct sprite-culling call breakdown | `sprite_probe.py`, observer controls, `sprite_report.py` | `spriteprobe/README.md` |
| Same-ELF hardware/RTL calibration or saved device log | `calibration.py` | `calibration/README.md` |

Use [references/workflows.md](references/workflows.md) for detailed commands,
coverage, controls and timing limitations for the selected workflow. CLI `--help`
and the maintained README take precedence over remembered command syntax.

For a Butterscotch port change, snapshot explicit baseline and candidate Git revisions under
new names; never build a candidate by changing `inputs/`. Export reads Git objects,
so uncommitted work needs an explicitly recorded supported source patch or a
committed revision. Preserve the original baseline and failed cases. Compare
matching game/window, mode, compiler/alignment, native setting, placement,
framebuffer, audio, clock-cost and build kind. Use both games for shared VM or
renderer changes when the affected paths are covered.

Supported Butterscotch windows are Undertale `flowey` 2400–2402 and Deltarune Chapter 1
`field` 2800–2802, `bmenu` 3120–3122, `dodge` 3323–3325. These samples are not
whole-game coverage. `experiments.py run` defaults to **Deltarune/dodge only**;
`--kind both` means traced and timing ELFs, not both games. Specify
`--game undertale --window flowey` and `--game deltarune --window WINDOW`
individually for each baseline/candidate. Leaf-event cycles cannot substitute
for full-frame cycles.

## Pico8Pocket platform and seed selection

Read `pico8/README.md` and [the Pico8 workflow](references/workflows.md#pico8pocket-os20-performance).
Verify the existing platform with `python3 pico8/cpu_platform.py verify`; build
once if `build/platforms/os20` is absent. Preserve incomplete builds and inspect
logs before the documented wrapper-only `rtl` resume. Never overwrite completed
platform evidence or frozen inputs.

Create fresh baseline/candidate cases with explicit
`--platform os20 --hash-seed 0x5eed1234 --measure-frames 12`. Both CLI and Python
API defaults remain os25, so omitting the platform repeats the old mismatch.
Require `case.json` to record `platform_name=os20`, `clock_hz=90000000` and CPU/
simulator provenance; native/QEMU must confirm `PICOSEED 1592594996`, and RTL
must confirm `PICOCPU 90000000` from MMIO. `luai_makeseed()` alone does not fix
the final address-mixed Lua seed. Production seeding remains unchanged.

Use matching setup/input, frame window, audio model, compiler/alignment and BRAM
placement. Record recreated scenes separately from actual save imports. Require
repeated native/QEMU output, quiet/scanout RTL output and memory oracles, and a
corrupted-pixel negative control. Compare raw pixels, palettes, PCM and pair
counts independently before claiming byte identity. Pointer-bearing state hashes
only compare the same ELF/checkpoint.
Require `capture.json`'s `native_output_equal=true` as well as `passed=true`.
Standard runner commands export channel hashes, not raw channels or a cross-case
comparison. Use a separately reviewed collector for byte comparisons, or report
hash agreement with byte identity unverified.

os20 timing uses the recorded 90 MHz clock. Preserve historical os25 cases at
their original 100 MHz; clock rescaling cannot reproduce the different CPU and
cache configuration. Existing single-lane os25 cache/pipeline observers are not
validated for dual-issue os20. The shipped bitstream source, device compiler/libc/
layout, production allocator, presentation, adaptive skipping and OS/SD/live
audio scheduling still require separate evidence. Butterscotch's os25 calibration
does not calibrate Pico8Pocket os20 or establish physical Pocket FPS.

## Accept evidence before interpreting performance

- Require repeat QEMU captures, same-binary RTL output/memory oracles and the
  workflow's negative controls. For an observer, require disabled-observer
  equality; preserve CPU parameters and exact original frame/batch cycles.
- For behavior-preserving changes, compare baseline/candidate raw pixels, PCM
  and pair counts independently. Same-build QEMU/RTL agreement alone cannot
  detect a regression copied into a new reference. Pointer-bearing state hashes
  are only comparable for the same ELF/checkpoint. Use fixed audio for regression
  checks; realtime audio has documented oracle exclusions.
- Pair traced correctness evidence with timing builds. Full-frame timing removes
  VM hooks but can retain renderer/GML profiling; the sprite/calibration adapters
  disable it. Record the actual flags rather than calling every timing ELF
  profiler-free.
- Regenerate reports with their validating launchers. Retain exact CASE paths,
  revision, ELF/source hashes, configuration, counter definitions and failures.
  A hash mismatch or changed oracle requires investigation, not a rewritten pin.

## Calibration saves and timing claims

Prepare the Butterscotch calibration hardware bundle only after reference, negative, observer on/off and
scanout controls pass. Keep the exact ELF for the device run. Calibration saves
use the game's NUL-terminated save-slot method with a separate slot-11 filename,
`calibration_log.sav`. The user waits for `CALSAVE saved` and `CALIBRATION PASS`,
then exits through the Analogue menu to flush the save to SD. Compare the raw
`.sav` locally with `calibration.py compare`; record the actual core/OS identity.
A matching embedded build ID is not an independent hash of the loaded bitstream.

`calibration/DEVICE-RESULTS.md` records the verified 2026-10-10 v0.9 calibration:
all 72 intervals/pixels passed and workload means agreed within 3.15% of quiet
RTL. The outside-view call agreed within 0.13%. This controlled generated-sprite
run does not explain the older ~19.9 microsecond v0.7 game probe or establish
full-frame parity. Do not apply a universal calibration multiplier.

Call RTL timings **simulated**, using each case's recorded clock: 90 MHz for
Pico8Pocket os20, 100 MHz for Butterscotch os25. Refill latency is not CPU stall,
overlapping masks cannot be summed, and a disjoint presentation priority is not
recoverable speedup. Supported os25 architectural retirement/CPI uses observer
v3 CommitService; do not substitute the older commit-decision count or apply
single-lane counters to dual-issue os20.

Account for the chosen service model: cached versus uncached framebuffer,
fixed audio-pair counts versus modeled realtime consumption, substituted allocator
and OS services, cold caches, instrumentation and diagnostic scanout. Actual
SD latency, kernel interrupts, audio/display scheduling, GPU execution, synthesis
fit and board behavior need separate tests. Compiler/layout parity with a device
build must be established for that exact build, not inferred from the core name.

## Isolation and delivery

Use Python launchers; Docker mounts only the harness or its independently copied
case. Keep the game checkout, SDK, OS sources and SD card out of those mounts.
Harness runs never invoke the port's device-build, copy or deployment targets.
An authorized port implementation happens separately; harness testing reads its
revision and writes only to private harness cases.

Keep game assets, bytecode, captures, `inputs/`, `build/` and `experiments/`
private and ignored. Preserve baselines and old reports. Report the verified
scope, cycle differences, output comparisons and remaining device questions.
Preparing an ELF/overlay is separate from installation; a harness task does not
itself authorize copying to SD or deploying a core.
