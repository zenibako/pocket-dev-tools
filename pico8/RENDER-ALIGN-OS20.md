# Renderer bulk-pointer alignment — 2026-10-20

The #19 experiment removes avoidable byte operations from real renderer bulk
loops. It improves every maintained window's average and peak simulated cost,
with a small matched-frame Moss caveat. Retain it as a local candidate for Pocket
testing. [Tracking issue](https://github.com/zenibako/pico8pocket/issues/19).

This follows the [rendering cost study](RENDER-COSTS-OS20.md) and
[draw-state investigation](DRAW-IDENTITY-DEEP-OS20.md). It is independent of the
[unmerged palt shortcut](PALT-NOOP-OS20.md); their combination is untested.

## What was missed

Current production already lowers four-byte `memcpy` calls inline. However,
`fill_pattern_span` and `fill_solid_span` tell GCC that the row base is aligned,
then add a variable pixel offset. GCC does not carry the prefix loop's resulting
alignment into that copy address: bulk paths use four byte loads/stores, with
additional stack unpack/repack in the mixed-pattern path.

Candidate `a1e82d17cf51e97111b7455d18875081aa795d15` on local `perf/render-span-alignment` describes the actual
`row_pixels + x` address as aligned **inside each existing bulk iteration**.
The prefix may exhaust a short span while `x` remains unaligned, so applying
that assumption unconditionally after the prefix would be unsound. Bounds,
byte edges, mask handling and alias-safe `memcpy` remain unchanged. No VM,
audio, GC, API binding, dependency, compiler flag or linker policy changes.
Baseline is clean main `726a2353343ebe7ea449c9e0f16b457bee2d5aaf`.

## Reached work, measured before the optimization

A native same-binary observer-on/off census partitions the helper callers.
Complete pixel, display-palette and PCM bytes, frame/input/FPS rows and audio
pair counts match the original current-main references in both observer modes.
All counted nonempty bulk pointers are aligned. Counts describe geometry and
copy-loop iterations, not CPU cycles, actual store counts or recoverable time.

| Scene | Pattern rectangle words/frame | Pattern circle words/frame | Solid rectangle words/frame | Solid circle words/frame |
| --- | ---: | ---: | ---: | ---: |
| intro2 | 2816.000 | 699.333 | 0.000 | 581.500 |
| trailhead | 0.000 | 0.000 | 0.000 | 711.167 |
| grapple | 0.000 | 0.000 | 0.000 | 711.000 |
| moss-steady | 0.000 | 0.000 | 24.000 | 3.583 |
| moss-gc | 0.000 | 0.000 | 22.000 | 1.833 |

The sampled patterned hspan caller is unused. Intro totals reproduce the prior
15,063 patterned rows and 42,184 patterned bulk words across 12 frames. Zero
keep mask means opaque writes; no fully retained pattern rows occur here.
Pattern rectangles already prepare four pattern rows per call; the compiler
already hoists some geometry, so neither is claimed as new work savings.
[Full caller/edge/preparation counts](RENDER-ALIGN-CENSUS-OS20.csv).

## Production code generation

Both builds use the same offline production build policy. Disassembly confirms
`lw`/`sw` in the candidate's mixed-pattern loops and `sw` in opaque/solid loops;
the prior bulk byte unpacking/repacking is gone. Partial edges retain byte I/O.

| Function | Baseline bytes | Candidate bytes |
| --- | ---: | ---: |
| `draw_rect_pattern` | 1690 | 1680 |
| `draw_hspan_pattern` | 714 | 686 |
| `api_circfill` | 1648 | 1600 |
| `api_rectfill` | 810 | 804 |

Those four bodies shrink by 92 bytes. Total `.text` shrinks by 192 bytes;
the remainder includes other code/alignment effects, and function order changes.
Do not attribute the full image change or full frame gains solely to these loops.
Both ELFs retain SDK entry `0x10400000`, nonoverlapping load ranges and BRAM
usage `0x375a` of `0x3800` (14,170 bytes, 166 free). No BRAM duplication or
arbitrary padding/address pinning is introduced.

## Fresh uninstrumented simulated performance

All comparisons use os20 at 90 MHz, fixed hash seed `0x5eed1234`, original carts,
scripted inputs, audio model, real delegate/dense iterator and matched compiler/
link policy. Native counters are absent from these timing builds. Every fresh
baseline reproduces its previous accepted quiet and scanout frame cycles.
These are bounded simulated runtime costs, not physical Pocket FPS.

| Window | Baseline quiet ms | Candidate quiet ms | Change | Baseline scanout ms | Candidate scanout ms | Change |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| intro2 | 25.890126 | 25.024760 | -3.342% | 25.983240 | 25.088046 | -3.445% |
| trailhead | 41.066409 | 40.864516 | -0.492% | 41.193099 | 40.969738 | -0.542% |
| Celeste whole grapple | 58.972933 | 58.411527 | -0.952% | 59.100924 | 58.540687 | -0.948% |
| Celeste full throw | 74.857006 | 73.990056 | -1.158% | 75.000456 | 74.131333 | -1.159% |
| Moss steady | 48.042425 | 47.951247 | -0.190% | 48.740644 | 48.674542 | -0.136% |
| moss-gc | 48.330589 | 48.266955 | -0.132% | 49.056132 | 48.988768 | -0.137% |

Windows: intro/Trailhead 100–111, whole grapple 304–308, full throws 305–306,
Moss steady 180–191 and Moss GC 234–245. All measured Celeste frames improve.
Six matched Moss frames across the traffic/window combinations are slower by
at most 0.037823 ms; every Moss window's mean and worst frame improve. This is
a window mean/peak pass, not a claim that every individual frame improves.
[Full per-frame change and provenance CSV](RENDER-ALIGN-OS20.csv).

Moss reaches very few bulk iterations. Treat its small gains as a regression
check, not evidence that direct bulk work accounts for all its timing change.
Whole-image layout and execution context also change; this study does not
identify a specific cache-conflict, prediction or pipeline mechanism.

## Verification and remaining limits

Core/runtime/delegate host suites pass before and after the source change.
A new 7,680-case independent per-pixel rectangle/disk model covers all 16 pattern
phases, short/word-boundary widths, solid/mixed/retained patterns, remapped
colors, camera/clipping/empty clips, negative/zero/larger radii, neighboring
pixels and packed screen RAM. A private missing-final-pixel mutant fails that
characterization. The optional checkout-local Celeste cart test is skipped;
separate actual-cart cases supply the game evidence.

All ten fresh cases pass repeated native and QEMU output, quiet/scanout RTL,
memory oracles and corrupted-pixel negative controls. Native raw comparisons
cover all 600 frames per case (400 for the grapple route). RV32 checks compare
measured-window channel hashes and pair counts; complete raw target channel
bytes are not claimed. Heap start remains `0x10459000` in all cases.
Frozen input/platform hashes and the validated replay toolchain image are
unchanged. The actual Pocket allocator, libc, OS/audio/display scheduling and
fitted hardware timing remain separate checks. Test both games on Pocket before
shipping, and benchmark any combination with the palt candidate separately.

Private evidence: `experiments/pico8-sources/render-align-20261020-r1/`.
`census.py`/`census-report.py` validate the same-binary r3 native census;
`benchmark.py`/`report.py` freeze and validate the five-scene r1 timing matrix;
`validate-production.py` checks production inventories/placement and preserves
disassembly. Early census setup failures and all original evidence are retained.
Source, reports and private files do not modify the active checkout, SDK/OS roots,
SD card, release branch or existing test ZIP. No new package or PR was published.

Production baseline SHA-256:
`578fa706c75b79f22fc8f9c5a6090fb464c6f11da9886024315308b9cddb5404`.
Candidate SHA-256:
`7a0770fbb40ca39b5e828145a8630848aed94418ff5d5803dd11dc755470a58f`.
