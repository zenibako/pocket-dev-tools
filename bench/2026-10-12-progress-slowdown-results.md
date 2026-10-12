# Deltarune progress-scene replay, 2026-10-12

The recreated spade chase has substantial frame cost in both revisions with
Script times disabled. The battle-sampling candidate adds a smaller regression:
1.62% in the chase and 0.81% at Castle Front. Both scenes keep battle sharpening
inactive, and all compared pixels and audio are identical. This reproduces a
heavy spade workload, not the user's exact saved-game state or physical timing.

## Revisions and setup

- Base: `a3f0057ebe98cf8905736ea72971c08f4d4640ec`.
- Sharp: `aa0e12357e1692b09a1213e27dd4207799dc19c7`.
- GCC 16.2.0, production port flags, native scripts enabled, 64-byte function
  and loop alignment, BRAM interpreter, Speed, uncached framebuffer, 1,680-cycle
  clock charge, fixed audio, quiet traffic, pinned os25 CPU at 100 MHz.
- Independent revision snapshots and cases. Production sources and assets were
  read only; adapter changes are confined to the dedicated harness worktree.

`spades` recreates room 43 (`room_dark_chase2`) with Kris alone, globals set at
frame 29, a jump at frame 30, and confirmation input every 15 frames from 40
through 475. Frames 490–492 contain nine active spades, with 9/8/8 centers visible
in the camera. The normal game events run the chase; the adapter does not draw
synthetic hazards. `castle` recreates room 46 (`room_castle_front`) with Kris and
Susie, the same setup/jump frames, no input, and frames 150–152 measured.
Both use `darkzone=1`, `plot=60`, and `interact=0`.

Benchmark draw diagnostics are disabled, volatile saves retained, and frame
pacing disabled for the fixed capture clock. Checks after cycle sampling require
the intended room and Speed setting, no active battle controller, inactive
contrast sampling, no draw profiling, and a null script-profiler pointer.

## Timing results

These are means of three complete-frame timing samples, **simulated at 100 MHz**.
VM tracing and in-loop PCM hashing are removed from timing ELFs; separate traced
ELFs validate the output.

| Scene | Base ms/frame | Sharp ms/frame | Change |
| --- | ---: | ---: | ---: |
| Spade chase | 167.501323 | 170.222580 | +1.624618% |
| Castle Front | 23.548763 | 23.739670 | +0.810687% |

Spade timing cycles, base: 16,765,469 / 16,656,439 / 16,828,489;
sharp: 17,038,442 / 16,917,723 / 17,110,609.
Castle timing cycles, base: 2,370,445 / 2,347,791 / 2,346,393;
sharp: 2,391,148 / 2,366,148 / 2,364,605.

The spade scene is expensive before the appearance change. The candidate's
2.72 ms increase is measurable in this deterministic replay, but these results
do not attribute it to a particular function, cache effect, or allocation.
The custom battle sampler is inactive here; its selected-pixel work cannot
explain the measured overworld difference. Castle Front's small increase does
not reproduce a large sustained slowdown throughout later areas.

## Verification and evidence

All eight cases (two revisions × two scenes × traced/timing) pass repeated QEMU
captures and same-ELF RTL output/state checks. All eight deliberately corrupted
state oracles are rejected. Cross-revision and traced/timing comparisons pass
for both scenes: raw RGB555 pixels, raw stereo PCM, and pair counts agree.
An additional direct comparison verifies 48 raw pixel/PCM byte comparisons.
A separate RV32 capture expecting room 46 during the spade scene fails with
`FRAMEHARNESS FAIL scene room mismatch`.

Six adapter regression tests pass, including scene separation in comparison and
report pairing. The original 1,631 frozen files remain unchanged; each exported
revision verifies its 1,647-file manifest. No device build or SD copy was run.

Private evidence directory:
`build/progress-regression-20261012-182551/`. It contains:

- `story-results.json`: validated eight-case report, exact case paths, revisions,
  flags, provenance hashes, timing rows and negative results.
- `story-*-comparison.json`, `story-*-trace-timing.json`: output comparisons.
- `story-raw-byte-comparisons.json`: direct byte comparison results.
- `story-wrong-scene-negative.json` and build/capture logs: rejected wrong room.
- `story-spades-reference.png`, `story-castle-reference.png`: inspected reference
  scenes, alongside original PPMs in the independent cases.

Earlier offscreen-hazard, benchmark-diagnostic, pacing-failure and three-member
party cases are preserved separately and excluded from this report.

## Limits and next diagnosis

Only three frames per controlled scene are measured, with cold RTL caches at
the checkpoint. This is not an imported save, a complete route, or an exact
recreation of every supplied screenshot. The harness substitutes allocator,
kernel, file access, framebuffer service and audio scheduling, and uses frozen
128-pixel standalone texture packs rather than the device's embedded 64-pixel
pack. It cannot reproduce actual SD stalls or establish physical Pocket FPS.

The next CPU investigation should profile the exact successful spade timing
case and use a controlled candidate to isolate inactive battle-UI bookkeeping
from code/heap layout effects. A current progressed save or deterministic input
route would allow more exact coverage of the other slow areas.
