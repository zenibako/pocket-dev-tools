# Transformed sprite bounds reuse versus base, 2026-10-10

Reusing cull's transformed bounds preserves the checked rendering and audio, but
does not beat base in either sampled window. Deltarune Speed takes 87.157 versus
87.340 simulated ms/frame in dodge (+0.21%), and 47.907 versus 48.146 in field
(+0.50%). Keep cull opt-in; these results do not support promoting it to default.

## Source and change

The dedicated game branch `perf/draw-cost-experiments` was rebased onto the newly
merged Pocket `fork/main`, `e83f1c7`. Git omitted fourteen equivalent commits
already on main; the eleven rebased commits through the measured revision have verified GPG
signatures. Measured source: `d78c9c2a3c22eee7654b08a97645c32920b22dc9`, exported
independently as `cull-reuse-main-e83`. Base and candidate use this exact snapshot;
candidate alone adds `-DUT_SPRITE_EARLY_CULL`.
Snapshot SHA-256: `db85ccb966d2ac537ad7ad59be2e46428d84f849ef47b88a40071544b9298df6`.

The cull entry retains the transformed, rounded destination used for early
rejection and passes it directly to the existing integer rasterizer for visible
sprites. Width/height truncation before view scaling, floor/ceil rounding and
strict zero-rotation/positive-scale eligibility remain unchanged. Flipped,
rotated and ineligible draws retain the ordinary wrapper. Source clipping,
blend ordering, held layers, mirrors and half-size rendering remain in the
existing rasterizer. The integer-coordinate entry point is absent from base.

This is revised cull versus base, rather than a controlled old-cull versus
revised-cull comparison. The results include early rejection, texture residency
changes and compiled code layout; they do not isolate the saved transformations.
See the [game experiment plan](../../butterscotch-draw-experiments/src/openfpga/docs/2026-10-10-draw-cost-experiments.md)
and the [earlier device/harness controls](2026-10-10-draw-cost-results.md).

The harness adapter now includes `ut_menu.c` and `ut_font.c` when present, as
required by the newly merged main. Older snapshots lacking those files retain
their previous source list. Original frozen inputs, RTL and dependency pins are
unchanged. The comparison follows [ARCHITECTURE.md](../ARCHITECTURE.md),
[the replay workflow](../fullframe/README.md), and [revision experiments](README.md).

## Simulated timings

GCC 16.2.0, port profile, native scripts enabled, -O2, 64-byte function/loop
alignment, BRAM interpreter, uncached framebuffer, quiet memory traffic, fixed
800 stereo sample pairs/frame and the declared 1,680-cycle clock charge. Seed 7,
fresh volatile saves, three cold-cache frames per window. Timing builds omit
harness VM/event tracing and in-loop PCM hashing; renderer/GML profiling remains
compiled in. Trace builds supply the paired correctness evidence.

| Window | Base timing ms/frame | Cull timing ms/frame | Change | Base trace ms/frame | Cull trace ms/frame |
| --- | ---: | ---: | ---: | ---: | ---: |
| Dodge, 3323–3325 | 87.157 | 87.340 | +0.21% | 98.495 | 98.634 |
| Field, 2800–2802 | 47.907 | 48.146 | +0.50% | 56.031 | 57.083 |

| Window / entry | First frame ms | Second frame ms | Third frame ms |
| --- | ---: | ---: | ---: |
| Dodge / base | 82.81221 | 97.71093 | 80.94790 |
| Dodge / cull | 82.92673 | 98.08358 | 81.00966 |
| Field / base | 48.20269 | 47.79427 | 47.72437 |
| Field / cull | 48.44751 | 48.03270 | 47.95920 |

The first rebase also completed this matrix at source `54ab600`, based on main
`c4bcfea`: dodge 87.253 → 87.510 ms (+0.29%), field 48.139 → 48.307 (+0.35%).
Its evidence remains independently preserved under `build/cull-reuse-rebased/`
and snapshot `cull-reuse-rebased`. The second rebase changes only save-archive
integer casts in the resulting source tree; fresh executables, captures and
checkpoints were nevertheless created and replayed for the final revision.
Neither study demonstrates a gain. Small deltas from these rebuilds cannot be
assigned uniquely to arithmetic, call overhead or cache/layout effects.

## Verification and limits

All eight final executables reproduce their two QEMU captures and pass full-frame
RTL replay. Base/cull raw RGB555, raw PCM and sample-pair counts match for every
frame, separately in trace and timing builds. Each trace/timing pair also matches
those outputs: eight comparisons total. All eight corrupted-state controls are
rejected. Same-binary state oracles remain checked; pointer-bearing state hashes
are excluded from cross-build comparisons.

Fresh ASan/UBSan desktop builds on the final revision match base/cull and the
previously saved reference across all 120 gameplay images, both games and modes.
Cull also matches 88 captures with every other frame skipped. The 1,452-sprite,
30-held-group fixture outputs match byte for byte with no sanitizer findings.
Gameplay reports only the documented vendored `stb_ds.h:1132` signed-left-shift
warning. Default/cull strict lint passes. The 35 harness unit tests pass, all
1,631 original frozen inputs match, and cases verify 1,644 snapshot source files.

These are simulated three-frame samples, not physical Pocket section means.
Kernel services/ABI, allocator, storage and audio remain substitutes. Neither
the end-of-route sprite microprobe nor the whole route was replayed here.
There is no measured Pocket result for this revision. No device ELF or card tree
was rebuilt or copied during this task. A later device comparison should use
newly built base → cull → base entries and compare full section times as well as
the inside/outside probe.

## Local evidence

Hash-verified report: `build/cull-reuse-main-e83/results.json`, SHA-256
`17fe02128e312b287600252dc43caedaad28baab59769c5f3195e44cfeb0aaae`. Eight output
comparison JSON files are beside it. Each ignored case retains its exact source,
flags, compiler command, ELF/checkpoint hashes, both raw captures, RTL logs and
negative-oracle evidence. Case names share prefix
`experiments/cases/cull-reuse-main-e83-deltarune-`:

| Window / entry | Trace identity | Timing identity |
| --- | --- | --- |
| dodge / base | `dodge-speed-trace-08763c33c8878e9f` | `dodge-speed-timing-8b25d54f845444cf` |
| dodge / cull | `dodge-speed-trace-bf9e16180d28c39b` | `dodge-speed-timing-02b3bb260aa60f9a` |
| field / base | `field-speed-trace-aeed8172a31e7158` | `field-speed-timing-fe2354d1ff1d7731` |
| field / cull | `field-speed-trace-ef8a3aeae4dd976a` | `field-speed-timing-8cc9f1fbf4d87318` |

The CPU simulator SHA-256 remains
`0b7a83995669152117afa4b1ac43c968cdffd274a01dccf1b46a8c90a89c4501`.
No private game assets or captures are committed.
