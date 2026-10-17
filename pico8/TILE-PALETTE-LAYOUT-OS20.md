# Remapped-palette tiles and placement controls — 2026-10-16

Follow-up: [the two-path tile hybrid](TILE-HYBRID-OS20.md) removes the third
BRAM loop and leaves 250 bytes free, but does not improve the performance gate.

Keep the accepted audio build. A dedicated remapped-palette tile path makes
both Moss windows faster, but both source variants slightly slow Celeste's
Trailhead window. The smaller variant reduces that cost to **0.07%**, without
eliminating it. Neither passes the shared no-regression gate, so no package or
PR is prepared. The active port and accepted audio worktree remain unchanged.

This follows the [complete-tile experiments](TILE-FULL-OS20.md) and
[rendering-cost study](RENDER-COSTS-OS20.md). All timings are **simulated
os20/90 MHz complete runtime frames**, not physical Pocket FPS or isolated
tile-kernel savings. Address controls show substantial compiler/layout
sensitivity, but do not completely isolate the tile algorithm.

## Normal-build results

Each mean covers 12 frames, including the first frame with cold RTL caches.
Lower is better; percentages are `(candidate / accepted - 1) × 100`.

| Window | Accepted ms | Unrolled ms | Change | Compact ms | Change |
|---|---:|---:|---:|---:|---:|
| Celeste tower | 25.871 | 25.212 | −2.55% | 25.166 | −2.73% |
| Celeste Trailhead | 42.144 | 42.210 | +0.16% | 42.174 | +0.07% |
| Moss steady | 48.690 | 48.409 | −0.58% | 48.579 | −0.23% |
| Moss GC window | 49.052 | 48.718 | −0.68% | 48.909 | −0.29% |

Scanout preserves every sign: unrolled changes are −2.61%, +0.15%, −0.45%
and −0.54%; compact changes are −2.73%, +0.07%, −0.17% and −0.21%.
Removing the first frame also preserves all normal-build signs. In particular,
Trailhead's remaining 11 quiet frames cost +0.17%/+0.08%. The small regression
is not confined to the first cold-cache frame. These are deterministic selected
windows, not statistical estimates of whole-game behavior.

Against parent tile source `03130b7`, rather than accepted source `9f4cd16`,
unrolled changes are +0.48%, +0.83%, −0.67%, −0.85%; compact changes are
+0.30%, +0.74%, −0.32%, −0.46% in quiet replay. The specialization therefore
recovers the preceding experiment's Moss losses while giving back some of its
Celeste gains. The Trailhead cost against accepted is about 0.065/0.029 ms.

[The CSV](TILE-PALETTE-LAYOUT-OS20.csv) contains all 21 comparisons, exact
quiet/scanout means, first-frame and warm-11 deltas, runtime capacity and capped
FPS estimates, source/harness revisions, case names and ELF identities. Capacity
estimates exclude presentation, OS scheduling, adaptive draw skipping and live
hardware audio. Celeste uses stationary recreated scenes, not traversal tests;
Moss uses scripted input windows.

## Algorithm and generated code

Unrolled source `6eef559` adds a middle branch for a fully visible 8×8 tile
whose transparency is default but whose palettes are not both identity.
`transparency_default` guarantees that source zero is transparent and colors
1–15 are opaque. The new branch tests the source nibble before mapping through
the draw palette, replacing each transparency-table lookup with a zero test.
Opaque source colors mapped to destination zero still write zero. Custom
transparency, including opaque source zero, retains the general path.

The palette flag also includes the screen palette: a false value need not mean
the draw palette is remapped. The branch always reads the draw palette and
masks to four bits. Reset, direct RAM mutation and restoration paths maintain
the flags; false can conservatively select the general path. Unchanged
per-color `palt` requests return early and preserve the true flag.

Production disassembly confirms four packed pairs unrolled per row, eight rows,
and no transparency-array reads in the middle branch: 64 reads avoided per
complete tile. Palette reads and writes remain conditional on source opacity.
This is an instruction-path observation, not an isolated cycle measurement.

Compact source `3cc5b18` adds only `#pragma GCC unroll 1` to that middle
four-pair loop. It saves 88 bytes, at the cost of pointer updates and an inner
backedge per pair. The compact variant improves the overall Celeste results, but
gives back part of Moss's gain. The exact contribution of loop work versus
surrounding code generation is not isolated.

| Production build | Tile kernel bytes | App BRAM bytes | Free bytes |
|---|---:|---:|---:|
| Parent tile `03130b7` | 466 | 14,126 | 210 |
| Unrolled `6eef559` | 658 | 14,318 | 18 |
| Compact `3cc5b18` | 570 | 14,230 | 106 |

All fit the 14,336-byte app BRAM budget. A fresh parent production rebuild is
byte-identical to the preceding experiment's `7d807a89…` ELF. The new ELFs are
`c96f91e9…` and `8997a337…`; full hashes and build logs remain in private
evidence. Production builds preceded source commits, so their original origin
records retain the dirty parent revision; recorded runtime content hashes
match the subsequently signed commits exactly.

Celeste's default-color row loop has the same 31 static instructions and
addresses (`0x4080..0x40e4`), up to register renaming, across parent/unrolled;
compact's row instructions are identical to unrolled. There is no added default
pixel-loop work to explain Trailhead's regression. Fully visible default entry
has 40 instructions in parent/compact and 39 in unrolled; register allocation,
load scheduling and surrounding addresses still change. All 15 other production
BRAM function sizes stay equal, but their entries relocate. BRAM is uncached;
these observations do not support a BRAM instruction-cache-conflict explanation.

## Address controls and their limits

The benchmark-only linker reserves a 672-byte tile slot at `0x4000`, keeps
`draw_hspan` at `0x42a0`, and starts VM input at `0x4368`. Both sides use the
same section transformation, linker policy and build flags within each pair.
These controls compare against parent `03130b7` under that control's layout,
not against the normal-build accepted baseline. Absolute times across different
layout policies must not be treated as a single matched comparison.

| Control | Window / variant | Quiet change | Scanout change |
|---|---|---:|---:|
| Renderer slots | Trailhead / unrolled | −0.30% | −0.27% |
| Renderer slots | Trailhead / compact | −0.27% | −0.25% |
| Renderer slots | Moss steady / unrolled | −0.05% | +0.10% |
| Dispatcher last | Moss steady / unrolled | −0.14% | −0.09% |
| Dispatcher last | Moss steady / compact | +0.07% | +0.16% |

Trailhead holds all 15 non-tile BRAM entry addresses and sizes. Its normal-build
regression reverses under the control, demonstrating that the overall trade-off
depends on the build/layout policy. Only three of those functions retain exact
bytes; twelve contain changed numeric operands. Matching masked instruction
sequences is not byte identity, nor does it freeze SDRAM code or data.

The first Moss renderer-slot control **fails the intended all-entry premise**:
`luaV_execute` grows 10,720→10,762 bytes, moving five subsequent helpers by
44 bytes. It remains a valid renderer-prefix comparison, not a fixed-VM control.
Fresh repaired controls put the dispatcher after the other VM functions.
All 15 non-tile entries then match, and 14 functions retain identical bytes.
The dispatcher itself still grows by 42 bytes at fixed entry `0x4d88`, with
instruction/block changes beyond relocations. Thus even this stronger control
cannot attribute the remaining delta solely to palette handling.

The controls establish compiler/layout sensitivity and narrow the confound.
They do not identify the exact scheduling, SDRAM/cache or dispatcher instruction
responsible for every cycle. A strict unchanged-binary slot experiment would
be a separate diagnostic requiring relocation and interprocedural register-use
audits; it was not performed here. The single-lane os25 pipeline observer is
not valid evidence for these dual-issue os20 cases.

## Correctness and retained evidence

Both variants pass the independent public `spr`/`map` oracle's 46 cases,
natively and with all 35 translation units consistently rebuilt under ASan and
UBSan. Coverage includes default/remapped/screen-only palettes, source zero,
opaque colors mapped to zero, custom transparency, direct RAM changes, exact
and partial clips, offscreen rejection, camera offsets, flipping, sprite bases,
multi-tile draws, redirected targets and dirty marking. Six added cases cover
both APIs after `palt(0x8000)`, after `palt()`, and with a screen-only remap.
Checks compare all displayed pixels and a weighted checksum of all packed
target RAM bytes; that checksum is not a byte-identity claim.

Two middle-branch mutants fail with assertion mismatches: suppressing opaque
mapped-zero writes fails 12 cases; bypassing the transparency guard fails 17.
Both variants also pass the existing native unit/runtime suites. Their optional
local-cart Celeste acceptance check is skipped; the separate game cases below
provide this experiment's Celeste coverage.

There are **16 new completed cases**, plus eight retained baseline/parent
cases, all freshly validated for this report. Each completed case has native
600-frame repeats, repeat QEMU checkpoints and native agreement, quiet/scanout
RTL replay, memory checks and deliberate output-oracle rejection. Independent
600-frame raw pixel/palette/PCM collectors match the validated runner transcripts
and their bytes match across every compared pair. Pointer-bearing checkpoints
are compared only within the same ELF. The final exporter checks source/binary
inventories, compiler settings, routes and provenance before calculating deltas.
Harness revision differences are permitted only for report Markdown/CSV files;
program inventories match apart from runtime.cpp within each comparison.

Private sources and evidence are under
`experiments/pico8-sources/tile-palette-layout-20261016-{r1,r2}` and
`tile-palette-address-20261016-r1`. Regular cases use
`tile-palette-os20-{scene}-candidate-20261016-{r1,r2}`; prefix controls use
`tile-palette-control-os20-{scene}-{before,after}-20261016-r2`; final controls
use `tile-palette-address-os20-{scene}-{before,after,compact}-20261016-r1`.
Not every scene/variant combination exists; the CSV names all actual cases.
The initial prefix preparation failed before inventory/build because the
platform linker was copied after the source-preparation hook. That failed
snapshot is preserved and excluded; corrected launchers derive files before
immutable inventory creation.

All cases retain final Lua seed `0x5eed1234`, explicit os20/90 MHz, and the
preceding study's routes: Celeste frames 100–111 with no buttons, Moss seed-7
input at frames 180–191/234–245. Runtime.cpp uses production builtin handling;
VM/other translation units and linking retain the original freestanding flags.
There are no API timers or path counters. Fresh checks pass for all 1,631 frozen
inputs and the existing os20 platform. Source, fixture, actual-ELF and evidence
audits accompany the private artifacts. No frozen input, original SDK, active
port, accepted audio worktree, remote or SD card is changed.

Final private evidence manifest covers 15,424 files. SHA-256:
`713175e68f4f78b21f57de6ba7f373976ed069dce1b946cbc1377d18575c9c73`.
