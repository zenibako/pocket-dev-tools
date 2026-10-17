# Isolated palette leaves and Pocket A/B test — os20 / 90 MHz

The new source candidate isolates the `pal()` entry and draw-palette identity helper in a non-LTO object. It preserves the baseline GC inlining policies but still regresses Trailhead. A cartridge-free, side-by-side Pocket package is prepared for the requested physical test; this is an experimental candidate, not a promoted optimization.

This follows the [accepted-audio source matrix](ACCEPTED-COMBOS-OS20.md) and [successful fixed-image palette diagnostic](DRAW-IDENTITY-DEEP-OS20.md). All percentages below are simulated frame-time changes, with positive values slower.

| Window | Extraction-only vs accepted | Candidate vs accepted | Candidate vs extraction-only |
| --- | ---: | ---: | ---: |
| Celeste tower | +0.823538% | -0.378784% | -1.192501% |
| Celeste Trailhead | +1.727241% | +1.842537% | +0.113338% |
| Moss steady | -1.444310% | -1.913846% | -0.476417% |
| Moss GC | -1.291147% | -1.918466% | -0.635524% |

Scanout preserves every sign. The [CSV](PALETTE-LEAF-OS20.csv) contains exact milliseconds, FPS capacities/caps, scanout and warm-frame comparisons, source revisions and ELF hashes.

The extraction-only control already has a 1.727% Trailhead regression and improves both Moss windows before the new fast paths are used. Therefore the candidate's overall Moss gain cannot all be credited to its identity helper, and most of the observed Trailhead regression is already present in the extraction control. These are whole-build comparisons; percentages are not independent costs to add.

## Source and code-generation checks

Accepted source is `9f4cd16`. Benchmark baseline `2bda633` adds only an empty extra object so all new link commands match; every quiet and scanout cycle array reproduces the retained accepted-source cases exactly. The extraction control is `58756b3`; candidate is `2b24aa7`. All three commits are signed.

The runtime structure moves verbatim to a private header, retaining field order and save layout. The existing full `pal` body is unchanged and has a C-linkage entry. A narrow private pointer gives the new entry access to the active runtime. No dependency pin or GC source/header changes.

The new object is compiled with trailing `-fno-lto`; actual objects have no LTO sections. Its 52-byte `pal` entry has no stack allocation or calls: the default zero-argument case returns zero, and every other case tail-jumps to the full implementation. Profiling remains on that fallback. Its 46-byte identity leaf performs four aligned, alias-safe word comparisons using an explicit loop; there are no library calls or cached palette state.

Production candidate uses 14,322 of 14,336 BRAM bytes, leaving 14 bytes. Initial unrolled or compiler-unrolled attempts exceeded the unchanged budget; their build failures are retained. The accepted production image uses 14,182 bytes.

The baseline VM and ordinary call-helper policies now match the candidate: benchmark VM has three wrapper calls and one direct forced step, while production has one wrapper call and three direct forced steps. Ordinary benchmark C-call helpers retain 262/212 bytes, removing the prior automatic-inlining growth.

The renderer is still a confound. The new cold helper call makes the benchmark tile grow from 522 to 560 bytes; production grows to 562. Benchmark stack allocation grows from 16 to 48 bytes, saves the return address and additional registers, and moves before the clipping returns. Thus the existing default path is not preserved instruction for instruction. These static changes are demonstrated; their exact contribution to frame cycles is not isolated. The unused identity body is also retained in the extraction control because both leaves share an input section.

## Verification

Twelve new cases and four retained accepted-baseline cases validate. All new cases pass repeated native/QEMU output, native output equality, 600-frame raw pixel/palette/PCM comparisons, strict quiet/scanout RTL memory checks and intentional corrupted-output rejection. Native core/runtime suites pass for both source variants; the full candidate runtime suite also passes AddressSanitizer and UndefinedBehaviorSanitizer across all compiled sources.

Additional contracts exercise all sixteen individual draw-entry remaps, no-op calls, palette/transparency resets, profiling counters and argument-bearing fallback. Skipping the final identity word is rejected by sixteen helper/render assertions; removing the profile guard is rejected by the counter test. The original accepted entry fails the stack-free leaf contract; both new target leaves pass code-generation checks.

The production fit and fourteen-image code audit are separate from timing evidence. Measurements use fixed seed `0x5eed1234`, os20 at 90 MHz, twelve frames per window, production runtime builtin policy and a matched untimed terminal drain. Celeste windows are frames 100–111; Moss windows are 180–191 and 234–245. These are recreated scenes and simulated timings, not physical Pocket FPS.

## Pocket test package

The private bundle is `experiments/pico8-sources/palette-leaf-20261017-r1/pico8pocket-palette-leaf-ab.zip`. It contains two separately named cores:

- **PICO-8 accepted audio baseline** — `zenibako.pico8palettebase`, exact retained accepted production ELF.
- **PICO-8 isolated palette test** — `zenibako.pico8paletteleaf`, exact verified candidate production ELF.

Unzip the bundle at the SD root. Both cores use the existing PICO-8 cart directory and have separate settings/save filenames. Match settings and the same cart/scene when comparing tower, Trailhead and Moss. The ZIP contains no cartridges, settings or saved games. No SD deployment was performed.

**Compare normal gameplay with diagnostics hidden first.** Select plus physical X enables the profiler, which sets a profile hook and deliberately routes `pal()` through the full implementation to preserve counters. Profiler-visible results therefore exercise different behavior from the unprofiled no-op fast path.

Both packages pass APF validation before renaming. The repackaging checks exact ELF bytes, the pinned os20/OS/loader assets, distinct application/settings/save references, identical shared files and ZIP integrity. SDK/runtime originals, the accepted audio checkout, active source checkout and prior palette branch remain unchanged.

Private source worktrees, benchmark evidence, sanitizer/mutation logs, failed links, exact-object audits and packaging manifests remain under `experiments/pico8-sources/palette-leaf-20261017-r1`. The candidate remains experimental pending the Pocket comparison.
