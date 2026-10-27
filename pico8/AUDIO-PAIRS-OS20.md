# PCM output-pair batching — 2026-10-16

Candidate **`9edffde`** passes all six sampled windows against the accepted
`foreach` optimization in PR #13 (`f5ab230`, runtime-equivalent to `3c726f8`).
Celeste's gameplay frame costs fall about 2.1–2.2%; Moss is effectively flat,
with small improvements in both measured windows. The title improves 7.69%.
These are **simulated os20/90 MHz runtime timings**, not physical Pocket FPS.

| Scene | Baseline, ms | Candidate, ms | Frame-cost change | Capped runtime capacity, FPS |
|---|---:|---:|---:|---:|
| Celeste title | 4.614362 | 4.259708 | -7.686% | 30.000 → 30.000 |
| Celeste intro 1 | 21.507412 | 21.046600 | -2.143% | 30.000 → 30.000 |
| Celeste intro 2 | 27.738885 | 27.160270 | -2.086% | 30.000 → 30.000 |
| Celeste Trailhead | 43.263101 | 42.322168 | -2.175% | 23.114 → 23.628 |
| Moss steady | 48.370594 | 48.287563 | -0.172% | 20.674 → 20.709 |
| Moss GC window | 48.693879 | 48.667403 | -0.054% | 20.536 → 20.548 |

The [validated CSV](AUDIO-PAIRS-OS20.csv) includes both attempts, exact quiet
and scanout changes, source/ELF hashes, BRAM sizes and private case identities.
All six final scanout means also improve. The samples, fixed PCM model, route,
seed and cold-cache timing boundaries match [the accepted foreach study](FOREACH-TABLE-OS20.md).
The simulation excludes presentation, adaptive skipping, OS/SD work and live
audio scheduling. Trailhead remains over the 33.333 ms budget; the intro/title
scenes remain capped at 30 FPS. Moss's small changes should not be described
as a substantial gameplay improvement or generalized beyond these windows.

## Implementation and compiler trade-off

The [Celeste](CELESTE2-OS20.md) and [Moss](MOSS-OS20.md) diagnostic profiles
identified PCM scopes around 6.15 ms in Trailhead and 1.08–1.30 ms in Moss.
The synthesizer already runs at 24 kHz and interpolates to 48 kHz. This change
emits the midpoint and held outputs together, removing per-output phase checks
and stores. Waveforms, filters, sequencing and synthesis rate are unchanged.
A leading pending held output and an odd final midpoint preserve continuity
across calls. Midpoints retain signed division truncation toward zero.

The first implementation (`4e043f8`) had a separate odd-tail synthesis call.
GCC 13.2 outlined the synthesizer: the Moss target ELF gained a standalone
`0x1240`-byte `synthesize` function, absent in the accepted baseline. The
production build showed the same inlining decision. That attempt regressed
Moss by 1.042% and Trailhead by 0.431% in quiet replay (and both under scanout),
so its gate stopped after those two scenes.

The final loop handles the odd tail at its single synthesis call site. GCC
again inlines synthesis, including in the production build. This removes the
first attempt's added call boundary while retaining pair batching. Both
versions pass output checks; source-level bookkeeping reductions alone did
not establish a speedup. LTO also changes code placement, so the complete gain
must not be attributed solely to pair arithmetic or the absence of calls.
The CSV records BRAM differences rather than claiming unchanged layout.

## Verification and production build

- A fresh accepted-foreach Trailhead rebuild reproduces its prior ELF and BRAM
  byte for byte. Candidate source inventories differ only in `audio.c`.
- Every final scene passes two native 600-frame runs, repeated RV32 captures
  with native equality, quiet/scanout RTL output and memory oracles, and a
  deliberately corrupted-pixel negative control.
- The existing reviewed collector exports raw pixels, palettes and PCM. All
  three channels are byte-identical across the 600 baseline/candidate frames
  in every scene; its output rows and PCM pair counts match the normal runner.
- Native core/runtime suites and Celeste's 600-frame/save-state replay pass.
  New boundary coverage compares single-frame output with irregular chunks
  across eight waveforms and four starting skip positions, including PCM,
  zero/null calls, two-byte-aligned output, sentinels and subsequent playback.
  A deliberate interpolation-phase-reset mutant fails those fixtures.
- The 32 boundary fixtures pass ASan/UBSan. Independent source reviews found
  no issues in either loop variant.
- Production GCC 13.2 build passes. BRAM stays at 14,182 of 14,336 bytes,
  leaving 154 bytes. APF and ZIP checks pass; all three runtime hashes match
  `pocket-runtime-a58aacd` pins. The public-format test zip contains no carts.

The production candidate has **not yet been tested on the Pocket**. Earlier
user observations concern the preceding foreach package and are not evidence
for this audio change. No active port checkout, SDK original, SD card, frozen
input or platform pin was changed. PR #13 remains unchanged.

## Reproduction and private evidence

`experiments/pico8-sources/audio-pairs-20261016-r1` preserves the source worktree,
first attempt, baseline reproduction, mutation test and production executable.
`audio-pairs-20261016-r2` contains the final six-scene `benchmark.py`, validating
`export.py`, raw channels, results, sanitizer evidence, production ELF and build
provenance. `export.py` checks eight complete results before writing the CSV;
the four unrun first-attempt cases are not counted as evidence.

The final source is GPG signed. The test package is
`audio-pairs-20261016-r1/candidate/releases/pico8pocket-v0.0.33-audio-pairs.zip`;
its adjacent `audio-pairs-build-info.json` records executable/package hashes.
Production ELF SHA-256:
`c4af75204fe7f59633fbefc63091cebf95732acbe6ee320482404b7ff3ec2dd6`.

## Rebased after PR #13 merged

The audio commits are now `793c98d` and `9f4cd16` on merged `main` (`1ef6525`).
Their final tree is byte-identical to `9edffde`, both new signatures verify,
and the core/runtime and Celeste save-state tests pass. The pre-rebase commits
remain on `archive/audio-output-pairs-pre-rebase-20261016`. The original
captures and package retain their historical provenance; a fresh rebased
Trailhead build reproduces the accepted ELF and BRAM exactly. The follow-up
[environment-lookup experiments](ENV-LOOKUP-OS20.md) were rejected.
