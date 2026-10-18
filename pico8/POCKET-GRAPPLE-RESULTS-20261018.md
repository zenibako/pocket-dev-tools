# Pocket moving Trailhead and Moss captures — 2026-10-18

These physical reports use the [movement/grapple packages](POCKET-GRAPPLE-CONTROLLED.md). The baseline journal contains six complete records and the palette journal seven; each retains the two historical manual/stationary records. The new set contains two grapple runs per core, two baseline Moss runs and three palette Moss runs. All new runs use DETAIL ON. No OFF measurement is present, so physical instrumentation overhead remains unmeasured.

All nine new runs have 300 measured/drawn/presented frames, fixed draw divisor 1, the intended build IDs, matching requested/actual seed, expected input fingerprints and both expected semantic/framebuffer/palette endpoints. All 2700 detailed/audio samples are valid with no unbalanced scopes or truncation. These endpoint checks do not constitute full per-frame output equality on hardware. Volume, mute, display scale, controls and runtime identity match.

## Performance

FPS below pools frames over elapsed time within each game/core; frame means pool the equal-length runs. These are every-frame controlled workloads, not normal adaptive gameplay FPS. Captures have journal order but no cross-core timestamp or randomized ordering; run ranges are descriptive, not confidence intervals.

| Workload | Baseline FPS (range) | Palette FPS (range) | Palette change | Mean frame, baseline → palette |
| --- | ---: | ---: | ---: | ---: |
| Trailhead movement/grapple | 14.90 (14.89–14.92) | 15.14 (15.08–15.20) | +1.60% | 67.10 → 66.04 ms |
| Moss Moss | 16.39 (16.30–16.49) | 17.19 (17.15–17.22) | +4.89% | 61.00 → 58.16 ms |

The palette build improves average FPS in both controlled workloads in this sample. Worst-frame behavior is mixed: Trailhead baseline maxima are 120.989 and 120.834 ms; palette maxima are 128.311 and 117.069 ms. The first palette run therefore has a worse isolated maximum despite its better average. Moss maxima are 72.954/70.758 ms baseline and 67.220/71.202/67.236 ms palette. Small sample counts and the earlier stationary tradeoff do not establish a universal improvement or justify promotion on these records alone.

| Mean component (ms/frame) | Trailhead baseline | Trailhead palette | Moss baseline | Moss palette |
| --- | ---: | ---: | ---: | ---: |
| UPDATE excluding GC | 29.086 | 28.166 | 54.488 | 51.754 |
| DRAW excluding GC | 23.367 | 23.309 | 0.000 | 0.000 |
| GC | 0.042 | 0.042 | 0.206 | 0.214 |
| Audio pump | 11.232 | 11.068 | 2.871 | 2.753 |
| Presentation | 2.959 | 3.029 | 2.979 | 2.989 |

Moss renders inside UPDATE; its zero DRAW callback time does not mean rendering is free. The current timers cannot separate Moss rendering from other update work. Most of the measured palette gain occurs in UPDATE, but the exact fast-path versus compiler/layout contribution is not isolated by these recordings.

## Celeste stall attribution

Mapping zero-based recorded indices to the validated native route trace by adding the 100 warmup frames shows that **15 of each run's 16 slowest frames execute grapple throw state 10**. Fourteen repeated indices execute state 10 and remain in it: 16–19, 53–54, 105–106, 155–156, 205–206, 255–256. Index 55 executes the throw and attaches (10→11). The remaining retained frame belongs to attached/release work. This is correlation with the native route trace, not a per-frame Pocket game-state probe.

For the 14 full-throw rows, UPDATE excluding GC averages 64.523/64.422 ms in the baseline and 63.060/61.970 ms in the palette. DRAW stays around 23.8 ms and the audio pump around 24.5–24.7 ms. These are correlated rows, not separately selected component maxima. A representative baseline worst frame (record 2, index 205) is 120.989 ms: UPDATE 64.712 ms, DRAW 23.718 ms, audio 29.235 ms, presentation 2.906 ms, no GC. The first palette maximum at index 155 likewise has no GC: UPDATE 68.513 ms, DRAW 24.446 ms, audio 31.849 ms, total 128.311 ms.

Private cart source provides a concrete hotspot hypothesis. The throw state at `discovery/cart.lua:1575` advances the hook up to six times, making up to three `grapple_check` calls each time. The check at line 1255 scans `all(objects)` after a tile miss. For a full no-hit advancement through the 79-object scene, that implies 18 scans and 1422 object property probes, plus iterator/closure work. `o.grapple_mode` usually follows the cart's Lua `lookup.__index` inheritance callbacks (line 676) through instance, type and default object. These repeated inherited-property lookups and iterator calls are strong next targets. The counts are derived from source and the route trace; no per-function timing in these reports establishes their individual shares. This loop uses `all`, not `foreach`.

GC is a small contributor: approximately 0.042 ms/frame in Celeste (0.06% of elapsed time) and 0.206–0.214 ms/frame in Moss (0.34–0.37%). Maximum recorded per-frame incremental GC is 1.562 ms in Celeste and 3.259 ms in Moss; there are no full or emergency collections. GC-kind statistics are an alternative partition of the phase GC intervals and are not added to them.

Audio is substantial during Celeste's long frames. Both variants render approximately 48.08k stereo pairs per elapsed second at approximately 3.48 us per pair. Longer updates leave more audio work for the next outer pump, consistent with catch-up amplifying the stalls. The recorded worst-frame components support this interaction, but no audio-queue underrun counter exists. All new reports show rendered pairs equal written pairs, zero software-skipped pairs and zero synthesized silence; those facts alone do not rule out hardware underruns. Presentation remains around 3 ms. Region timings include interruptions and timer instrumentation.

The next diagnostic should isolate inherited-property/metamethod and `all` iterator costs during the known throw frames, initially with disposable native counters and then narrowly scoped timing if necessary. It should retain the same route, ordinary API profiler disabled, and matched enabled/disabled controls. These captures point away from prioritizing GC tuning for the observed long stalls.

## Evidence

Private original uploads, strict journal/metadata validation, parsed metrics, correlated worst rows, and reproducible analysis are preserved under `experiments/pico8-device/grapple-moss-20261018-r1/` (`analyze.py`, `analysis.json`, `grapple-state-correlation.json`). Source/trace provenance remains in the earlier movement package experiment. The attachments are source data and no attached text was executed.

- Baseline upload SHA-256: `8f0ff59569da350a1981339fe2b9a20e837603b2a1cd22e71b933d041d1c89ee`.
- Palette upload SHA-256: `c99a1919b9a15b79c05c6bf0d0ddb1e429416bdcc84254196f015b16bbd37b7e`.

No runtime implementation, package, SD or remote changes were made in this analysis.
