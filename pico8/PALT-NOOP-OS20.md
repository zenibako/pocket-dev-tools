# Guarded no-op palt experiment (2026-10-19)

The guarded `palt()` entry reduces Celeste 2's measured runtime cost without
increasing either Moss Moss window's average or peak frame cost. Keep it as a
local candidate for Pocket testing; this is not a measured device FPS gain.
Tracked exploration: [pico8pocket #18](https://github.com/zenibako/pico8pocket/issues/18).

This follows [draw-state identity diagnostics](DRAW-IDENTITY-DEEP-OS20.md),
[rendering cost measurements](RENDER-COSTS-OS20.md) and the established
[count-hook regression matrix](COUNT-HOOK-OS20.md). The other remaining topics
are [pattern/circle costs](https://github.com/zenibako/pico8pocket/issues/19),
[audio catch-up](https://github.com/zenibako/pico8pocket/issues/20) and
[intro/codegen parity](https://github.com/zenibako/pico8pocket/issues/21).

## Source change

Baseline is clean main `726a2353343ebe7ea449c9e0f16b457bee2d5aaf`.
Candidate is signed `5a1ef230748182b39ca109030641cd73b04543ff`, on local `perf/palt-noop`.
The new non-LTO SDRAM entry returns zero values only when Lua has exactly zero
arguments, the runtime exists, profiling is off and transparency is already at
its default. All other calls enter the original general body. No VM, GC, audio,
renderer pixel work, dependency pin or runtime bitstream changed.

Characterization covers no arguments versus explicit nil, bitfield and per-color
transparency, RAM writes, preservation of draw palette remaps, return counts and
profiling counters. Core, runtime and delegate host suites pass before and after
the optimization. The optional checkout-local Celeste acceptance cart is absent;
the separate private benchmark cases below cover the actual carts. Independent
source review found no blocker.

## Fresh simulated results

These are os20/90 MHz costs for matched deterministic routes, not Pocket FPS.
Both variants retain the real delegate, dense iterator, fixed seed `0x5eed1234`,
original carts/input/audio and the same production-builtin/linker policy.
Each fresh baseline reproduces its prior accepted quiet/scanout frame cycles.
Lower time is better; changes below are candidate versus current main.

| Window | Baseline quiet ms | Candidate quiet ms | Change | Baseline scanout ms | Candidate scanout ms | Change |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| intro2 | 25.890126 | 25.633156 | -0.993% | 25.983240 | 25.683271 | -1.154% |
| trailhead | 41.066409 | 40.928089 | -0.337% | 41.193099 | 41.048044 | -0.352% |
| Celeste whole grapple | 58.972933 | 58.436096 | -0.910% | 59.100924 | 58.556622 | -0.921% |
| Celeste full throw | 74.857006 | 74.095683 | -1.017% | 75.000456 | 74.206933 | -1.058% |
| Moss steady | 48.042425 | 48.002316 | -0.083% | 48.740644 | 48.727956 | -0.026% |
| moss-gc | 48.330589 | 48.288275 | -0.088% | 49.056132 | 49.015473 | -0.083% |

Windows are intro/Trailhead 100–111, whole grapple 304–308, full throws 305–306,
Moss steady 180–191 and Moss GC 234–245. All measured Celeste frames improve.
Some matched Moss frames are slower, by at most 0.0805 ms; both Moss windows'
mean and worst-frame costs improve in both traffic modes. This satisfies the
window-average and peak gates, not a claim that every individual frame improves.
See [the full per-frame and provenance CSV](PALT-NOOP-OS20.csv).

The shortcut avoids the general API entry and argument helper for redundant
resets. Timing also includes the changed whole-image code layout. Historical
Moss diagnostics found no reached `palt()` calls in these windows, so its tiny
changes should be treated as layout sensitivity, not direct work savings.
This experiment does not isolate a particular cache or pipeline mechanism.

## Verification and build limits

All ten fresh cases pass repeated native/QEMU output checks, quiet/scanout RTL,
corrupted-pixel negative controls and memory oracles. The native collector
compares complete pixel, palette and PCM bytes, plus pair counts, over 600 frames
per case (400 for the scripted grapple route). RV32 comparisons cover measured
window channel hashes/pair counts, not complete raw target channel bytes.

Both offline production ELFs link at SDK entry `0x10400000`, use 14,170 bytes
of BRAM (`0x375a` of `0x3800`, 166 bytes free) and retain startup/hot/cold sections.
The wrapper is in SDRAM; production text grows by 80 bytes. Baseline production
SHA-256 is `578fa706c75b79f22fc8f9c5a6090fb464c6f11da9886024315308b9cddb5404`;
candidate is `c7199c8ae10e4e68a15287fc018da1ff9776195fe610fbe10384f6ad21100e11`.
These are local production builds, not new release packages or Pocket captures.

The missing replay image was restored from the existing production image using
the same Ubuntu GCC 13.2.0 package, QEMU 8.2.2 and pyelftools. The frozen CPU,
simulator and inputs were verified and reused; no RTL was regenerated. The
larger Java/RTL toolchain bootstrap was stopped after the replay image succeeded.
Image IDs and bootstrap logs are preserved privately. Baseline repeatability
checks confirm that this restoration did not change the recorded frame cycles.
Exact production allocator, libc, OS/audio/display scheduling and physical
Pocket timing parity remain unproven; test both games on Pocket before shipping.

Private reproducible evidence is under
`experiments/pico8-sources/palt-noop-20261019-r1/`: `benchmark.py` freezes/runs
r2 cases, `report.py` validates the complete matrix and generates the CSV,
`production-validation.json` records production placement and hashes, and
`replay-toolchain/` records the tool restoration. Missing-image r1 failures,
source snapshots, launchers, raw channels, captures and RTL logs are preserved.
No active game checkout, original SDK/OS tree, SD card or v0.0.35 ZIP was modified.
