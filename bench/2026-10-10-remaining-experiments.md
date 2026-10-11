# Texture fast-hit and profiler control screening, 2026-10-10

This screen tests the remaining implemented independent experiments before another
device recommendation: cached item texture fast-hit (`tex`) and GML profiler
compile-out (`prof`). The user chose to screen existing experiments first;
VM superinstructions remain reconnaissance, with no candidate implemented here.

Keep both flags opt-in. Texture fast-hit saves only 0.285 simulated ms/frame
in Deltarune field, is nearly flat in the other Deltarune samples, and is slightly
slower in Undertale Flowey. The profiler control saves about 1.1 ms/frame in
Deltarune Speed but loses useful “Script times” diagnostics; it also provides no
gain in the Undertale timing sample. Neither is an established shared default
optimization.

The subsequent device bracket, after rebasing and rebuilding at `79ab365`,
records a small texture win: 146.3 → 145.7 → 146.3 seconds for the full route
(-0.41%), with field work 43.2 → 43.1 → 43.2 ms/frame. This supports retaining
tex as a candidate. It does not establish an Accuracy or shared-game default;
the harness matrix recorded here uses the earlier `bbea9be` source snapshot.

## Source and method

All harness entries use `bbea9be12477bc96d4ccbab906fbcce0e9f37bc7` from the dedicated
`perf/draw-cost-experiments` branch, based on Pocket main `e83f1c7`.
Its runner C/header sources match the previously measured bounds-reuse revision
`d78c9c2`; the intervening commit records verification. Independent snapshot
`remaining-main-e83` has SHA-256
`492de4cd3168dc5a2c76e769257dc8005c38a1399e1131fd3d4f09217ad06b17`.
Base, tex and prof use this same snapshot and differ only in the recorded switch:
none, `-DUT_TEXTURE_FAST_HIT`, or `-UENABLE_VM_GML_PROFILER`.

Tex returns an already cached item texture before pack metadata work, preserving
whole-page texture priority and the last-used-frame update. Prof removes GML
profiling, including the user's “Script times” diagnostic; renderer profiling
remains enabled. Prof is a cost control with a feature tradeoff, rather than a
feature-preserving replacement.

The comparison follows [ARCHITECTURE.md](../ARCHITECTURE.md),
[full-frame replay](../fullframe/README.md), [revision experiments](README.md),
and the [existing experiment plan](../../butterscotch-draw-experiments/src/openfpga/docs/2026-10-10-draw-cost-experiments.md).
Original frozen inputs, CPU RTL, dependency pins and older evidence are preserved.
No renderer/VM source change, device rebuild or SD-card write is part of this
screen. Fresh PC binaries were built separately from the existing card outputs.

The user subsequently requested the newly installed `os25-harness` skill.
Its shared-path guidance adds Undertale's Flowey window, with the same three
switches and paired trace/timing builds. `--kind both` denotes the two build
kinds; both games are selected explicitly. Frozen-input verification still
passes all 1,631 original files; independent revision cases verify 1,644 files.

Undertale and Deltarune Chapter 1, seed 7, fresh volatile saves, native scripts enabled,
GCC 16.2.0, port profile, `-O2`, 64-byte function/loop alignment, BRAM interpreter,
uncached framebuffer, fixed 800 stereo sample pairs/frame and the declared
1,680-cycle clock charge. Each window contains three replay frames with cold CPU
caches. Quiet traffic supplies the main comparison; diagnostic scanout adds
display contention. These are simulated timings, not physical Pocket frame times.

Separate timing builds omit harness opcode/event tracing and in-loop PCM hashing;
trace builds supply the paired correctness evidence. Use timing builds for speed
comparisons. Same-binary pointer-bearing state oracles stay enabled; cross-build
comparisons use raw RGB555 pixels, raw PCM and sample-pair counts. Traced opcode
and builtin counts are also checked across entries.

## Speed samples

Negative changes mean faster. These are matched timing builds from the same
snapshot; percentages do not predict physical Pocket section averages.

| Window | Base ms/frame | Tex ms/frame | Tex change | Prof ms/frame | Prof change |
| --- | ---: | ---: | ---: | ---: | ---: |
| Dodge, 3323–3325 | 87.253 | 87.274 | +0.02% | 86.162 | -1.25% |
| Field, 2800–2802 | 48.139 | 47.854 | -0.59% | 47.024 | -2.32% |
| Menu/attack, 3120–3122 | 65.582 | 65.473 | -0.17% | 64.508 | -1.64% |
| Undertale Flowey, 2400–2402 | 15.800 | 15.825 | +0.16% | 15.841 | +0.26% |

The Undertale trace control goes in the opposite direction for prof:
17.757 → 17.710 ms (-0.27%), whereas timing is 15.800 → 15.841 ms (+0.26%).
This is another reason to pair builds and avoid assigning the complete change
to the removed checks. None of the tiny Undertale differences establishes a
repeatable whole-game gain or loss. Deltarune's field texture gain retains its
direction under diagnostic scanout; the other quiet samples are close to flat.

Texture's field saving is 0.285 simulated ms/frame in quiet traffic. Its
diagnostic scanout replay also passes the output/memory oracles, with a
0.403 ms/frame saving. This is a modest result in one window, not whole-route
proof. The profiler saving also retains its direction in both dodge scanout
modes; neither result restores the removed diagnostic feature.

| Window / mode / traffic | Candidate | Base ms/frame | Candidate ms/frame | Change |
| --- | --- | ---: | ---: | ---: |
| Field / Speed / diagnostic scanout | tex | 54.526 | 54.124 | -0.74% |
| Dodge / Accuracy / quiet | prof | 186.074 | 185.149 | -0.50% |
| Dodge / Speed / diagnostic scanout | prof | 97.745 | 96.719 | -1.05% |
| Dodge / Accuracy / diagnostic scanout | prof | 212.048 | 211.002 | -0.49% |

## Correctness coverage

All 28 executables reproduce two QEMU captures and pass complete-frame RTL
replay with same-binary output and memory oracles. The 32 output comparisons
pass: 14 trace/timing pairs and 18 base/candidate comparisons, independently
matching raw pixels, PCM and sample-pair counts. Nine traced base/candidate
VM/builtin-count comparisons also match. All 28 corrupted-state controls are
rejected. Six supplemental diagnostic scanout replays pass their output/memory
oracles. Together the quiet and scanout runs cover 34 configurations and 102
positive frame rows; scanout reuses the already checked exact executables.

Fresh ASan/UBSan desktop tex and prof builds each match all 120 saved gameplay
images against base across Undertale and Deltarune, Accuracy and Speed. Tex also
matches 88 actually drawn captures with every other frame skipped. The texture
priority/invalid-index, 1,452-sprite and 30-held-group fixture matches base byte
for byte (3,123,072 bytes, SHA-256
`975331bf6f8cb79322ebd4097d34280961080688ff94d46d40bf67d1592e2168`).
Strict lint passes for both switches. Gameplay retains the documented vendored
`stb_ds.h:1132` signed-left-shift UBSan warning; the fixture has no sanitizer
findings. These desktop checks extend rendering coverage, not simulated timing.

## Device base → tex → base after rebasing

Attachment SHA-256:
`21e0234c21636daf97ba3eddea5ad951fb23ce2aaa91f8200e9345a0d77846a8`
(118,316 bytes). Selected report headers are at lines 273, 1127 and 1872 in
the NUL-stripped log. The texture report at line 365 is byte-identical to line
1127; it is one run, not a repeat. Older report headers at lines 3, 93 and 183
belong to the preceding base/cull study and are excluded.

All three selected reports identify Deltarune Chapter 1 Speed, OS 0.7.0, core
variant 0, 100 MHz and 3,600 benchmark frames. The middle header explicitly
records `-DUT_TEXTURE_FAST_HIT`; both surrounding headers have no experiment
flags. Their association with `79ab365e92fe957280e42d518e2a9fbb3f8796dd` follows
the session's rebuild/copy/run sequence and retained card manifest, rather than
an independently recorded hash of the loaded ELF. The reports contain no source
revision hash.

Changes use the mean of the surrounding bases and the printed work values.

| Section, work ms/frame | Base before | Tex | Base after | Change |
| --- | ---: | ---: | ---: | ---: |
| Opening text | 27.2 | 27.1 | 27.2 | -0.37% |
| Creation screens | 66.8 | 66.5 | 66.8 | -0.45% |
| Town yard | 27.4 | 27.4 | 27.4 | 0.00% |
| Field | 43.2 | 43.1 | 43.2 | -0.23% |
| Menu/attack | 65.6 | 65.3 | 65.6 | -0.46% |
| Dodging | 77.3 | 77.2 | 77.4 | -0.19% |
| Next turn | 61.4 | 61.4 | 61.4 | 0.00% |
| Full route, seconds | 146.3 | 145.7 | 146.3 | -0.41% |

The base section values agree at printed precision everywhere except dodge
(0.1 ms apart). Texture has no section regression at that precision. Field draw
is 30.4 → 30.2 → 30.4 ms/frame and step is 10.4 in all three; menu/attack draw
is 54.1 → 53.9 → 54.1. The route saving is 0.6 seconds, so this is a small
positive bracketed result rather than a large frame-rate change. A single
bracket does not estimate repeatability, and 0.1-ms section rounding limits the
precision of the percentages.

| Sprite 40×40 probe, µs/call, path 1 | Base before | Tex | Base after |
| --- | ---: | ---: | ---: |
| Door stop | 1.03 | 1.03 | 1.03 |
| Cumulative texture-found stop | 2.66 | 2.11 | 2.66 |
| Whole inside-view draw | 60.48 | 58.70 | 59.24 |
| Outside-view draw | 5.10 | 4.55 | 5.10 |

The stable door and texture-found base controls place a 0.55-µs saving before
the texture-found stop. That cumulative stop includes the entry work; it is not
a texture-lookup-only timer. Outside-view cost falls by 10.78%. Whole inside-view
cost falls by 1.94% against the mean control, but the controls themselves differ
by 1.24 µs, so that whole-draw percentage is less stable. The fast-hit path and
compiled layout both differ; the probe does not isolate their contributions.

Actual audio work also illustrates why timings need controls: field output is
2,108 → 2,099 → 2,105 sample pairs/frame; dodge is 3,736 → 3,730 → 3,741.
The harness instead fixes 800 pairs/frame. The device difference is consistent
with a queue fed according to elapsed time; it does not prove audio caused the
measured renderer saving. Draw-call counts agree across all three runs.

Private extraction and checked calculations are retained in
`build/texture-device-79ab365/device-base-tex-base.json` and `reports.txt`.
No game source change, device rebuild or SD-card write is part of this analysis.

## Decision boundaries

The [revised cull study](2026-10-10-cull-reuse-results.md) already rejects promoting
cull: slightly slower harness samples and no clear device route gain, despite a
much faster isolated out-of-view probe. The
[earlier rows study](2026-10-10-draw-cost-results.md) rejects cached held rows on
both device and harness. Combo contains the losing rows component. Flush changes
measurement attribution and is not a proposed speed improvement. The compact
function-layout experiment did not establish a device gain.

Source/disassembly inspection found that the current interpreter reloads the
profiler pointer per opcode. A Pocket-specific pointer cache or caller-side null
guards could preserve diagnostics, but neither is implemented or measured in
this screen. Such a follow-up must exercise profiling enabled, nested calls,
exact instruction/call counts, balanced depth and off/on frame-boundary toggles.
The compile-out results cannot prove that a feature-preserving change would save
the same time. The generic VM profiler API does not promise a stable pointer.

No remaining screened flag is ready to become a shared default. The recommended
**Deltarune Benchmark speed base → tex → base** bracket, comparing field first
and retaining other sections/route as regression checks, is now complete above and
shows a small physical gain. Keep tex available as a candidate; promotion still
needs evidence for the target Accuracy mode and affected shared-game paths.
Prof remains an optional diagnostic control. A feature-preserving reduction of
dormant profiler overhead is the next implementation question to screen in the
harness, with the diagnostic feature retained; it has not been implemented here.

## Evidence and limits

Validated private aggregate reports under `build/remaining-main-e83/`:

| Report | Coverage | SHA-256 |
| --- | --- | --- |
| `results.json` | 24 Speed cases, 12 trace/timing pairs | `772afb381942c75101656affacdcf048db48e1db55e807bcdb4d50ebac4abd65` |
| `accuracy-results.json` | 4 Accuracy cases, 2 trace/timing pairs | `5633c5aaae0b96343234a7d8c3916126ac5b1e9538eb94dfed08d17ed33d8eaa` |
| `scanout-results.json` | 6 supplemental timing replays | `69ff3d99f11696d812b059ac4a35fc94fecb51c6a4e5e86230811701cbf9a306` |

Each case retains its compile command, snapshot/ELF/checkpoint hashes, repeated
captures, RTL logs and rejected negative oracle. Private game assets, captures
and generated results remain ignored. Source switches are recorded in
`experiment.json` and validated against the expected base/tex/prof flags before
reporting. Reports are regenerated by `experiments.report_cases`, which validates
the retained evidence; timings are not transcribed from an unchecked log.

The reproduction command shape is:

```sh
python3 experiments.py run --snapshot remaining-main-e83 --game GAME --window WINDOW --mode speed --kind both --profile port --native enabled --compiler /opt/homebrew/bin/riscv64-elf-gcc --alignment --variant bram --framebuffer uncached --clock-cost 1680 --audio fixed --traffic quiet
```

Select `deltarune` with `dodge`, `field`, or `bmenu`, and `undertale` with
`flowey`. Base has no extra flags. Add
`--extra-cflags='-DUT_TEXTURE_FAST_HIT'` for tex or
`--extra-cflags='-UENABLE_VM_GML_PROFILER'` for prof. The supplemental Accuracy
comparison uses Deltarune/dodge, `--mode accuracy`, base and prof only. Existing
verified CASE directories retain the evidence; do not rebuild them in place.
Use the printed CASE paths for `compare`, `report` and supplemental `replay`:

```sh
python3 experiments.py compare --baseline BASE_CASE --candidate CANDIDATE_CASE --output build/review/comparison.json
python3 experiments.py replay --case CASE --negative
python3 experiments.py replay --case TIMING_CASE --traffic scanout
python3 experiments.py report --cases CASES --traffic quiet --output build/review/results.json
```

Case paths use
`experiments/cases/remaining-main-e83-GAME-WINDOW-MODE-KIND-SUFFIX`.
Mode and kind in paths are lowercase. Scanout replays reuse the table's timing
cases: field Speed base/tex and dodge Speed/Accuracy base/prof.

| Game / window / mode | Entry | Trace case suffix | Timing case suffix |
| --- | --- | --- | --- |
| Deltarune / dodge / Speed | base | `9b410c7f63d97328` | `e6bf9ab272941d59` |
| Deltarune / dodge / Speed | tex | `f727d57282a41250` | `c17114c7755122ff` |
| Deltarune / dodge / Speed | prof | `264f1356b90266b0` | `ec6295164e215ab9` |
| Deltarune / field / Speed | base | `e4904d716ed8a35b` | `b006b8dd17bacf3e` |
| Deltarune / field / Speed | tex | `15b92a9d2fd22de0` | `eda0ff4b304b52a3` |
| Deltarune / field / Speed | prof | `a5847149d177bcb1` | `be728b5534a89f89` |
| Deltarune / bmenu / Speed | base | `3180e1daf5c84193` | `e26e1d59fae6fdb4` |
| Deltarune / bmenu / Speed | tex | `ee09b7583f74173b` | `7ae3feba2dca896c` |
| Deltarune / bmenu / Speed | prof | `62c262d9f4606bb1` | `90a9b98ba3b0ed47` |
| Undertale / flowey / Speed | base | `103d353d05ecee42` | `074e44115dbe9f06` |
| Undertale / flowey / Speed | tex | `8e4fc66cb4741141` | `87095538cbfe9d08` |
| Undertale / flowey / Speed | prof | `b07d5162e44ba3fb` | `8d0e5335fe0477ee` |
| Deltarune / dodge / Accuracy | base | `09e98100ef59d626` | `1dc2dae3243dee5f` |
| Deltarune / dodge / Accuracy | prof | `9a66627cccfde857` | `c3d92a1d6d5863eb` |

Three cold-cache frames cannot establish whole-section or whole-route speed.
Kernel service ABI, allocator, storage latency and hardware audio remain harness
substitutions; diagnostic scanout is not a complete physical display model.
Exact game output does not establish device performance. Small changes may
include compiled layout/cache effects and are not assigned solely to the edited
operation. Earlier device profiler measurements showed a smaller saving than
the old harness dodge sample, so simulated percentages are screening evidence,
not physical predictions.

Fresh controls matter even when runner C sources match an older snapshot.
The compiler embeds absolute case paths through `__FILE__` in assertion and
allocation error strings, without prefix mapping. The old and new base commands
and flags match after path normalization, but their allocated ELF data differs.
Older base timings are not reused as controls for the new candidates.
For example, `utLogLoadSummary` grows from 6 to 10 bytes through linker relaxation,
and `SWRenderer_drawSprite` and `swrTextureForItem` move by 64 bytes. The BRAM
interpreter remains at `0x4000` with the same size but different relocated bytes.
Current base/tex/prof case paths have equal lengths within each window/build kind.
This establishes layout sensitivity, not a measured cause of a particular delta.

The separate [identical-ELF calibration](../calibration/DEVICE-RESULTS.md) supports
the CPU/memory timing model for its controlled arithmetic, memory and sprite
workloads. It uses a different renderer snapshot, compiler, cached framebuffer
and device OS; that agreement does not remove the full-game comparison limits.
