# Spade benchmark after rebasing onto main 8d3cb19

Both experiment branches now descend from fork main
`8d3cb19662e83088b01df4ccacae781582a9d180`. The shared font, audio-group and
Undertale appearance foundation remains in both. Their only source difference
is Deltarune battle sampling plus its fixture and documentation; the benchmark
implementation is identical.

- Base: `34a8b36c4a3b94f934e3ec97077b7488fbe108d1`.
- Sharp: `3d0752315a49dc0b44840de3ea07f39ef3f9729e`.

The old heads (`bc9f304` and `bb17515`) are retained under local
`refs/codex-backup/spades-{base,sharp}-before-main-8d3cb19` refs. Nothing was
pushed. The rebase preserves main's snapshot startup, initialization and frame
boundary hooks, plus audio snapshot-buffer cleanup. Native save states remain
disabled for Deltarune. The device benchmark route now lives with the game's
metadata; shared reporting remains in `of_bench.c`.

## Simulated results

Same controlled scenes as the [preceding run](2026-10-12-progress-slowdown-results.md):
solo Kris in room 43, frames 490–492 with nine active spades (9/8/8 visible),
and Kris/Susie at Castle Front, room 46, frames 150–152. Both use seed 7,
setup at frame 29 and a room jump at frame 30. These are recreations, not an
imported player save.

GCC 16.2.0, production port flags, native scripts enabled, BRAM interpreter,
64-byte function/loop alignment, Speed, uncached framebuffer, 1,680-cycle clock
charge, fixed audio and quiet traffic. Values below are complete-frame means
from three timing samples, **simulated at 100 MHz**.

| Scene | Base ms/frame | Sharp ms/frame | Sharp versus base |
| --- | ---: | ---: | ---: |
| Spade chase | 173.825600 | 168.719947 | -2.937228% |
| Castle Front | 24.981590 | 24.746067 | -0.942788% |

Spade timing cycles, base: 17,396,023 / 17,287,079 / 17,464,578;
sharp: 16,885,973 / 16,768,322 / 16,961,689.
Castle timing cycles, base: 2,514,287 / 2,490,818 / 2,489,372;
sharp: 2,491,633 / 2,467,213 / 2,464,974.

The earlier comparison was 167.501 → 170.223 ms (+1.62%) for spades and
23.549 → 23.740 ms (+0.81%) at Castle Front. That small regression does not
persist after this rebase. The direction changes between code bases, and
battle sharpening is inactive in every measured overworld frame. These
measurements therefore do not establish a speed benefit from sharpening or
identify a particular cache/layout effect. Both spade builds still have
substantial simulated CPU cost.

## Verification

All eight cases (two revisions × two scenes × traced/timing) pass repeated
QEMU captures and positive same-ELF RTL output/state checks. All eight
corrupted-state oracles are rejected. Cross-revision and traced/timing
comparisons pass for pixels, PCM and pair counts; 48 direct raw RGB555/PCM
byte comparisons also agree. Pointer-bearing state is compared only within
the same ELF. All measured frames check the room, visible spades where
required, Speed, inactive battle sampling, disabled draw diagnostics and a
null script-profiler pointer.
An additional rebased RV32 capture expecting room 46 during the spade chase
is rejected with `FRAMEHARNESS FAIL scene room mismatch`; its separate case
and `wrong-scene-negative.json` are retained outside the eight positive cases.

The adapter's eight old/new-layout unit tests pass. The original 1,631 frozen
files remain unchanged; each new revision snapshot verifies 1,679 files.
The new adapter uses the real state-request module with `SAVESTATES=0`,
explicit game SHA, renamed native/benchmark modules and zstd. It supports
both `UT_*` and `BS_*` harness environment queries without enabling additional
settings. Earlier cases remain independent and unchanged.

Port checks pass: strict lint for both games, the spade benchmark fixture
under ASan/UBSan (including wrong-room rejection), both games' font, audio-group
and battle-contrast sanitizer fixtures, and main's snapshot regression suite.
Each device benchmark completes twice on desktop, retains prior reports and
leaves a normal-save sentinel unchanged; the captured base/sharp pixels agree.
Both device ELFs build at entry point `0x10400000`. Static review found no
actionable issues in the rebase or adapter.

## Evidence and delivery

Private harness evidence: `build/spades-rebase-main-8d3cb19-r1/` contains
`results.json` (exact case paths, hashes, flags and per-frame rows), eight output
comparison JSON files, `raw-byte-comparisons.json`, build/replay logs and
inspected scene PNGs. `build/spades-rebase-active.json` records the revision
and snapshot identities.

The dedicated Pocket overlay is at the sharp worktree's
`src/openfpga/out/device-spades-main-8d3cb19/benchmark-overlay/`. Its six files
add `Deltarune Spades base` and `Deltarune Spades sharp`, their INIs and ELFs.
The existing ordinary programs, runtime and saves are outside this overlay.
Both entries run automatically in Speed without Script times, measure the
harness frames followed by frames 493–519, append a labelled report to
`deltarune_1.sav`, and stop. Exit through the Analogue menu to flush the log.

The unchanged limitations apply: only three frames per RTL window, cold RTL
caches at the checkpoint, a substituted allocator and OS/file/audio services,
and frozen 128-pixel standalone texture packs versus the device's embedded
64-pixel packs. No physical Pocket timing or SD latency is measured here.
