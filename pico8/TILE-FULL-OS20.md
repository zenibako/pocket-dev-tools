# Complete-tile experiments — 2026-10-16

Follow-up: [remapped-palette tiles and placement controls](TILE-PALETTE-LAYOUT-OS20.md)
recover the Moss losses, but retain a small Trailhead regression. Neither new
variant is promoted; that report records the compiler/layout controls and limits.

Keep the accepted audio build. The best tile variant improves Celeste's tower
by **3.02%** and Trailhead by **0.67%**, but slows the two Moss windows by
**0.09%/0.17%** in quiet replay. Those Moss costs are small (0.044/0.084 ms per
frame), but they do not meet the shared no-regression gate. Neither variant is
promoted or packaged. The active port and accepted audio worktree are unchanged.

This follows [the rendering-cost study](RENDER-COSTS-OS20.md): both games use
fully visible 8×8 tiles. A [later census](TILE-DEEP-OS20.md) clarifies that both
games' selected tile draws use identity draw palettes; Moss remaps its screen
palette, which clears the combined palette flag. The study measured API bodies;
this experiment measures complete,
uninstrumented runtime frames. All timings here are **simulated os20/90 MHz**,
not measured Pocket FPS or isolated tile-kernel savings.

## Matched frame results

Lower frame time is better. Changes are `(candidate / baseline - 1) × 100`;
negative percentages mean faster. Each mean includes 12 frames, including the
first frame with cold RTL caches.

| Window | Baseline ms | Full tile r2 ms | Change | Early rejection r3 ms | Change |
|---|---:|---:|---:|---:|---:|
| Celeste tower | 25.871 | 25.374 | −1.92% | 25.090 | −3.02% |
| Celeste Trailhead | 42.144 | 42.353 | +0.49% | 41.863 | −0.67% |
| Moss steady | 48.690 | 49.167 | +0.98% | 48.734 | +0.09% |
| Moss GC window | 49.052 | 49.572 | +1.06% | 49.136 | +0.17% |

Scanout changes have the same signs: r2 is −1.93%, +0.50%, +1.09% and +1.12%;
r3 is −3.04%, −0.69%, +0.14% and +0.21%, respectively. Omitting the first
timed frame also preserves r3's result: tower −3.00%, Trailhead −0.67%, Moss
steady +0.11% and Moss GC +0.15% in the remaining 11 quiet frames. The small
Moss regression is therefore not just a first-frame cold-cache effect.

[The CSV](TILE-FULL-OS20.csv) records both variants, exact frame means, quiet
and scanout changes, first-frame and warm-11 changes, runtime capacity/capped
FPS estimates, revisions and case/ELF identities. These estimates exclude video
presentation, OS scheduling, adaptive draw skipping and live hardware audio.
These are stationary recreated Celeste scenes and scripted Moss windows, not
whole-game averages or traversal tests.

Baseline is accepted source `9f4cd16f6d3d730b8edaab1102387c6958df5536` in fresh
cases. Both sides compile runtime.cpp without `-ffreestanding`, matching current
production's builtin policy; VM/other translation units and linking retain
their original flags. There are no API timers, path counters or GC observers.
Older freestanding-harness timings are not the baseline for these percentages.
The complete snapshot inventories, platform/CPU/simulator identities, routes,
seeds and build settings match except for runtime.cpp and source revision.

## What changed and why the trade-offs remain

Corrected full-tile variant **r2**, signed `3c2995c`, keeps a compact complete
8×8 kernel in BRAM and moves the original generic clipped body into a noinline
SDRAM helper. It selects default versus general palette/transparency behavior
once per tile and uses constant four-byte source rows. It tests transparency
on the source nibble before mapping, preserves opaque colors mapped to zero,
supports custom opaque source-zero, and keeps screen-RAM dirty marking.
Row pointers are formed only for the eight rows actually accessed.

GCC already split the old palette-mode pair loops once per row and advanced row
pointers by fixed strides. Thus there was no per-pair mode branch or repeated
row multiplication to claim eliminated from the old machine code. The new full
path removes generic odd-edge/tail/variable-bound handling and makes the mode
choice once per tile. GCC unrolls all four packed-byte pairs despite the rolled
source; the eight-row loops remain.

R2 sends partial and fully offscreen tiles to SDRAM. The prior census counts
15 rejected tile calls/frame in the tower and 61 in Trailhead, versus none in
these Moss windows. Retry **r3**, signed `03130b7`, adds a BRAM early return for
fully offscreen tiles before the partial-tile dispatch. Disassembly confirms
right-of-clip rejection stays entirely in BRAM; visible tiles execute four
additional clip branches, reusing the existing clip loads. Partial tiles still
use the unchanged generic source body in SDRAM. Their correctness is covered,
but their performance is not characterized by these four windows, which have
no visible partial tiles.

R3 improves both Celeste windows relative to r2 and nearly removes the Moss
regressions. This does **not** isolate the early-return branch's benefit:
Moss executes no rejected tiles, yet its timing changes substantially too.
The compiler changes kernel register allocation and block ordering, relocates
all other BRAM helpers, and changes some unrelated functions through LTO.
For example, `luaV_execute` remains 10,800 bytes but moves from `0x4ad8` in the
baseline to `0x4a90` in r2 and `0x4aa0` in r3. Production r2/r3 also differ in
`unpersist`, `db_traceback` and `api_camera` sizes. These are direct codegen
observations, not proof of which cache or instruction change causes each frame
delta. The single-lane os25 pipeline observer is not valid evidence for this
dual-issue os20 workload.

| Production build | Full kernel bytes | App BRAM bytes | Free BRAM bytes |
|---|---:|---:|---:|
| Fresh accepted baseline | 522 | 14,182 | 154 |
| Corrected full tile r2 | 450 | 14,110 | 226 |
| Early rejection r3 | 466 | 14,126 | 210 |

The SDRAM clipped helper is 634 bytes, including default 64-byte loop-alignment
padding that the former BRAM helper avoided. Both candidates fit production,
but the full-build timing gate still matters. The measured renderer bodies are
only a small part of the complete frame, so a kernel simplification alone is
not evidence for a broad runtime win.

## Correctness and provenance

An independent public `spr`/`map` fixture passes 40 cases on the accepted and
corrected candidates: default/remapped palettes, direct palette-RAM writes,
custom transparency, opaque zero, colors mapped to zero, exact-edge/full/partial
and fully offscreen tiles, camera offsets, multi-tile calls, flips, sprite
indices/bases and redirected drawing. It compares all 16,384 displayed pixels
per case and a weighted checksum covering all 8,192 bytes of active packed
target RAM. The latter is a checksum check, not a byte-identity claim.

Both r2 and r3 pass consistent ASan/UBSan builds of all 35 fixture/runtime/
dependency translation units, plus the existing native runtime suite. R2's four
new-fast-path mutants fail for default transparency, opaque-zero remapping,
custom opaque source-zero and dirty marking; original-path transparency and
right-clip mutants also fail. R3's new rejection is covered by both spr/map
offscreen cases and independent half-open clip-boundary reasoning.
The native suite's optional local-cart Celeste acceptance check was skipped;
the separate 600-frame cases provide this experiment's game coverage.

Two development corrections are retained explicitly. The fixture initially
mistook redirected target RAM for the public displayed framebuffer; the accepted
runtime returns the real screen for that accessor. Its failed attempt is retained
and the display/target-RAM expectations were separated. Initial prototype
`093d8e5` advanced row pointers beyond one-past after the final row. Review
caught that C++ pointer-formation issue even though tests passed; r2 uses valid
row-local pointers. Initial candidate timing was stopped and preserved as
superseded, and is excluded from the result tables.

The fresh production baseline ELF differs from archived accepted ELF `c4af752…`
because miniz's embedded source-path string shrinks from 159 to 39 bytes under
the consistent `/work` build mount. Independent comparison finds the same name,
address and size for all 771 functions and exact renderer bytes/addresses;
downstream data moves by 120 bytes. Both candidate builds use the same new
mount/path policy. Their runtime content hashes match the signed source commits,
even where compilation preceded the commit; original build logs remain intact.

Private evidence is under `experiments/pico8-sources/tile-full-20261016-r1`
(source worktree, baseline, original attempt, fixtures), `-r2` (corrected full
tile) and `-r3` (early rejection, final exports). Cases are
`experiments/pico8/tile-full-os20-{scene}-baseline-20261016-r1` and
`tile-full-os20-{scene}-candidate-20261016-{r2,r3}`. Scenes are `intro2`,
`trailhead`, `moss-steady` and `moss-gc`. Routes retain final Lua seed
`0x5eed1234`, Celeste frames 100–111 with no buttons, and Moss's seed-7 input
over frames 180–191/234–245. Production seeding is untouched.

The validating exporters check immutable inputs/binaries, native repeats and
600-frame raw pixel/palette/PCM identity, raw-collector/runner frame equality,
repeat QEMU checkpoints/stacks/output, prepared inputs, quiet/scanout RTL replay,
memory checks and deliberate output-oracle rejection. They verify full cross-case
inventories/settings before calculating comparisons. `-r3/finish.py` reruns both
exporters and combines their eight rows. Assets, checkpoints, binaries and failed
attempts remain private and ignored. No frozen input, SDK pin, active port,
accepted audio worktree or SD card is changed.

All 12 completed cases (four baselines and both four-scene candidates) pass
those controls. Fresh frozen-input and os20-platform verification also pass.
Independent source/codegen, fixture and final evidence/report reviews accompany
the retained private artifacts.

Final private evidence manifest covers 928 files. SHA-256:
`d22713c0ac0ca31f30e353afc029a7ca6679647eda40e7c9f43b1c6d11f1e1e4`.
