# Deltarune draw-cost experiment: harness and device, 2026-10-10

The cached held-row implementation loses time on both the Pocket and the RTL harness. The surrounding device base runs take 80.1 and 79.9 ms/frame in dodge; rows takes 84.4 ms (+5.5%). The matching harness timing cases take 87.853 and 91.323 simulated ms (+4.0%). Keep the current rows change experimental. Test the profiler control next, then early culling.

## Scope and provenance

Source snapshot: `0134a2f8c0a393895fe86fd2f15bf3738147852b`, exported as `draw-cost-device-0134` from the dedicated game experiment checkout. All seven variants use this same frozen revision; only the recorded preprocessor switches differ. Source snapshot SHA-256: `e0454f26a6ede1b771197aadf77a557d7f9d18dd5bc29e894ae223425d0a6712`.

This study follows [ARCHITECTURE.md](../ARCHITECTURE.md), [the frame replay workflow](../fullframe/README.md), and [the revision experiment guidance](README.md). Original input pins, CPU RTL and baseline evidence were preserved. The game checkout and SD card were not modified. Harness changes are on `perf/draw-cost-harness`.

Deltarune Chapter 1 Speed, seed 7, native scripts enabled, BRAM interpreter at 0x4000, dodge frames 3323–3325. Port profile; host GCC 16.2.0, -O2, 64-byte function/loop alignment; uncached framebuffer. Quiet memory traffic, fixed consumption of 800 stereo pairs/frame, and the existing optional 1,680-cycle clock charge. Base retains renderer and GML profiling; the prof entry removes only ENABLE_VM_GML_PROFILER. Timing builds omit harness VM/event tracing and in-loop PCM hashing; they retain renderer profiling.

GCC version and alignment match the recorded card build procedure. This is a harness rebuild with platform substitutions, not the card ELF. Kernel service ABI, allocator, storage and audio differ. The three replay frames begin with cold CPU caches; device figures average whole benchmark sections and consume audio according to real elapsed time. Neither absolute frame times nor small deltas establish whole-route performance. The clock/audio settings are declared assumptions; no settings were tuned to these results.

## Simulated frame timings

Changes are relative to base. Use timing results for speed comparisons; trace results provide stronger audio/event checks and alter code layout.

| Entry | Timing ms/frame | Change | Trace ms/frame |
| --- | ---: | ---: | ---: |
| base | 87.853 | +0.00% | 99.210 |
| flush | 87.689 | -0.19% | 99.289 |
| tex | 88.658 | +0.92% | 99.617 |
| cull | 87.347 | -0.58% | 98.135 |
| rows | 91.323 | +3.95% | 103.513 |
| prof | 86.343 | -1.72% | 99.476 |
| combo | 91.154 | +3.76% | 102.146 |

The profiler control and early-cull gains are small and confined to this sample. The profiler control is slightly slower in the traced build, so instrumentation/layout affects the comparison; its timing gain cannot be assigned entirely to active profiler work. Texture fast-hit and combo also lose time here. Flush changes cost attribution in the device report and remains within 0.2% of base in this timing sample.

| Entry | Frame 3323 ms | Frame 3324 ms | Frame 3325 ms |
| --- | ---: | ---: | ---: |
| base | 83.59558 | 98.34245 | 81.61977 |
| flush | 83.37786 | 98.24771 | 81.44188 |
| tex | 84.40234 | 99.16399 | 82.40794 |
| cull | 83.06708 | 97.82973 | 81.14434 |
| rows | 87.02628 | 101.89184 | 85.05012 |
| prof | 82.06766 | 96.77676 | 80.18372 |
| combo | 86.85537 | 101.70444 | 84.90349 |

A separate diagnostic scanout replay of the timing builds preserves the oracles: base 98.673 ms; rows 100.545 ms (+1.90%). This display traffic is a harness diagnostic, not a complete physical display model.

## Device base → rows → base

Attachment SHA-256: `cb4c21ccd70a0b2ac02dbfd8d2e2bae034fda2c89b5b69086695599cf0730bbf`. Report lines 191, 1037 and 1793 provide the surrounding controls and rows run. The rows summary also appears at line 281; that duplicate is one run, not a second trial. The older unlabelled 77.0 ms dodge report is excluded: the user identified it as an earlier build or unknown.

| Section, work ms/frame | Base before | Rows | Base after | Change vs mean base |
| --- | ---: | ---: | ---: | ---: |
| field (640x480) | 44.4 | 45.1 | 44.2 | +1.81% |
| battle: menu, attack | 67.4 | 72.8 | 67.5 | +7.93% |
| battle: dodging | 80.1 | 84.4 | 79.9 | +5.50% |
| battle: next turn | 62.8 | 67.1 | 62.8 | +6.85% |

Full route: 147.7 s → 150.4 s → 147.6 s, +1.86% against the mean control. In dodge, draw rises from 57.6 to 62.1 ms/frame. The sampled held clear/tile operation rises from 12.1 to 16.4 ms, accounting for almost all of that draw increase. Step time remains 17.2–17.3 ms. This supports rejecting the current scratch-row implementation; it does not isolate cache or memcpy as the cause.

The rows device microprobe reports whole draw 63.78 µs and out-of-view 6.50 µs, versus 59.16 and 5.08 µs in the final base run. These end-of-route microprobes were not replayed by the frame cases in this study. Their slowdown does not identify an instruction-cache cause.

Run base → prof → base next, then base → cull → base if useful. The current prof card entry has an unlabelled base-like report header, so retain the run order. Neither tiny simulated gain is sufficient to adopt an optimization.

## Verification and local evidence

All 14 executables reproduce two QEMU captures and pass same-binary RTL replay. Each variant matches base raw RGB555 pixels, raw PCM and PCM pair counts for all three frames, separately for trace and timing. Every trace/timing pair also matches those outputs. Cross-build pointer-bearing state hashes are excluded; same-binary RTL checks retain them. All 14 corrupted-state oracle controls are rejected. Base/rows timing scanout replays also pass.

`python3 -m unittest test_experiments test_cache_profile test_bootstrap`: 28 tests passed. `python3 run.py verify`: all 1,631 original frozen input files match; each candidate case verifies 1,640 snapshot files. The launcher accepts only ordered -D/-U tokens and records them in case identity and build metadata. Trace/timing report pairs require matching switches; all seven pairs were checked against the actual case flags.

Generated private evidence stays ignored under `build/draw-cost-0134/`: `results.json`, `base-rows-scanout-results.json`, `device-base-rows-base.json`, twelve base/candidate comparison reports and seven trace/timing comparisons. Each case retains compile command, source/ELF/checkpoint hashes, raw captures, RTL logs and negative-oracle evidence. The shared simulator SHA-256 is `0b7a83995669152117afa4b1ac43c968cdffd274a01dccf1b46a8c90a89c4501`.

Case paths share prefix `experiments/cases/draw-cost-device-0134-deltarune-dodge-speed-`; the table retains kind and full identity suffix.

| Entry | Switches | Trace identity | Timing identity |
| --- | --- | --- | --- |
| base | `(none)` | `trace-befff113fa17721d` | `timing-c5a06056d0beeeb7` |
| flush | `-DUT_FLUSH_PROFILE` | `trace-2554ded200740c7b` | `timing-ef64ddb7e9019170` |
| tex | `-DUT_TEXTURE_FAST_HIT` | `trace-5e2eab7c6f6c790f` | `timing-09d960a79f76694e` |
| cull | `-DUT_SPRITE_EARLY_CULL` | `trace-494a1e1f02f55ed7` | `timing-223b4cfe11b30874` |
| rows | `-DUT_CACHED_HELD_ROWS` | `trace-ad8b4ab9b1c7cfe2` | `timing-c2791fedb814dfeb` |
| prof | `-UENABLE_VM_GML_PROFILER` | `trace-20d33aba074c1709` | `timing-d7716774902745de` |
| combo | `-DUT_TEXTURE_FAST_HIT -DUT_SPRITE_EARLY_CULL -DUT_CACHED_HELD_ROWS` | `trace-3be35df0b9d1b3bc` | `timing-8a1769fe3ae61a2f` |

Verified quiet report SHA-256: `3a74e4433de76740d7b00d2167063ade103f0a70b98ebc1762d0ace9a0df61db`.
