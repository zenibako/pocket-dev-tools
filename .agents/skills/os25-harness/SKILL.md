---
name: os25-harness
description: Test Butterscotch openFPGA changes for Undertale and Deltarune Chapter 1 in the isolated os25 RTL harness. Use for baseline/candidate frame replay, cache and pipeline cycle analysis, sprite probes, or matching Pocket calibration saves before device testing.
---

# Butterscotch openFPGA testing with os25 RTL

Use the standalone `openfpga-os25-harness` repository for functional RV32 replay
and simulated CPU/cache/memory measurements. Desktop captures check broader
scenes; the harness measures selected target workloads; a Pocket run checks
actual OS, SD, display/audio and board behavior. Only os25 with the current
Butterscotch adapters is validated. Do not generalize to other cores or chapters.

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
| VM leaf events / synthetic interpreter checks | `run.py` | `README.md` |
| Original complete-frame matrix | `fullframe/run.py`, `fullframe/report.py` | `fullframe/README.md` |
| A current port revision or optimization | `experiments.py snapshot/run/compare/report` | `bench/README.md` |
| Cache refills, retirement/CPI, FPU or dependency waits | `cache_profile.py` on an exact successful case | `cacheprobe/README.md` |
| Direct sprite-culling call breakdown | `sprite_probe.py`, observer controls, `sprite_report.py` | `spriteprobe/README.md` |
| Same-ELF hardware/RTL calibration or saved device log | `calibration.py` | `calibration/README.md` |

Use [references/workflows.md](references/workflows.md) for detailed commands,
coverage, controls and timing limitations for the selected workflow. CLI `--help`
and the maintained README take precedence over remembered command syntax.

For a port change, snapshot explicit baseline and candidate Git revisions under
new names; never build a candidate by changing `inputs/`. Export reads Git objects,
so uncommitted work needs an explicitly recorded supported source patch or a
committed revision. Preserve the original baseline and failed cases. Compare
matching game/window, mode, compiler/alignment, native setting, placement,
framebuffer, audio, clock-cost and build kind. Use both games for shared VM or
renderer changes when the affected paths are covered.

Supported windows are Undertale `flowey` 2400–2402 and Deltarune Chapter 1
`field` 2800–2802, `bmenu` 3120–3122, `dodge` 3323–3325. These samples are not
whole-game coverage. `experiments.py run` defaults to **Deltarune/dodge only**;
`--kind both` means traced and timing ELFs, not both games. Specify
`--game undertale --window flowey` and `--game deltarune --window WINDOW`
individually for each baseline/candidate. Leaf-event cycles cannot substitute
for full-frame cycles.

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

Prepare the hardware bundle only after reference, negative, observer on/off and
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

Call RTL timings **simulated**, at the pinned 100 MHz os25 clock. Refill latency
is not CPU stall, overlapping masks cannot be summed, and a disjoint presentation
priority is not recoverable speedup. Architectural retirement/CPI uses observer
v3 CommitService; do not substitute the older commit-decision count.

Account for the chosen service model: cached versus uncached framebuffer,
fixed 800 audio pairs versus modeled realtime consumption, substituted allocator
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
