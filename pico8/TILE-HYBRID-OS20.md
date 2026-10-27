# Two-path tile hybrid — 2026-10-16

Follow-up: [the deeper palette investigation](TILE-DEEP-OS20.md) separates
Moss's identity draw palette at sampled tile calls from its remapped screen
palette and measures tile-kernel changes with the surrounding binary held fixed.

The hybrid does not pass the shared no-regression gate. It improves Celeste's
tower and both Moss windows against accepted audio, but slows Trailhead by
**0.18%** in quiet replay. Its quiet results are worse than the preceding
compact variant in all four windows. Keep the accepted audio build; no package
or PR is prepared from this experiment.

This is the combination proposed after the
[palette/placement experiments](TILE-PALETTE-LAYOUT-OS20.md): keep default and
remapped/default-transparency fast loops, and use the existing general fallback
for custom transparency. It follows the
[complete-tile study](TILE-FULL-OS20.md) and
[rendering-cost measurements](RENDER-COSTS-OS20.md). All performance figures are
**simulated os20/90 MHz runtime frame times**, not physical Pocket FPS,
whole-game averages or isolated tile-kernel timings.

## Measured frame costs

Each mean includes 12 frames, including the first frame with cold RTL caches.
Negative changes mean faster. Accepted source `9f4cd16` already includes the
accepted table-identity foreach change and audio pair batching; these gains
must not be added again. Both the preceding compact build and this hybrid
also include the complete-tile kernel and early offscreen rejection.

| Window | Accepted ms | Compact ms | Hybrid ms | Hybrid vs accepted |
|---|---:|---:|---:|---:|
| Celeste tower | 25.871 | 25.166 | 25.267 | −2.34% |
| Celeste Trailhead | 42.144 | 42.174 | 42.220 | +0.18% |
| Moss steady | 48.690 | 48.579 | 48.610 | −0.16% |
| Moss GC window | 49.052 | 48.909 | 48.966 | −0.18% |

Scanout changes against accepted are −2.39%, +0.18%, −0.015% and −0.040%,
respectively. Moss is almost flat under scanout. Excluding the first timed
frame leaves Trailhead +0.19% slower in quiet replay and +0.20% under scanout;
its regression is not a first-frame cold-cache effect. Moss steady's remaining
11 scanout frames are +0.008% slower, also effectively flat. The compact build
has lower quiet and scanout means than the hybrid in all four windows.

[The validating CSV](TILE-HYBRID-OS20.csv) contains comparisons against accepted
audio, parent tile `03130b7`, unrolled palette `6eef559` and compact palette
`3cc5b18`: 16 rows across 20 unique cases. It records exact quiet and scanout
means, first-frame and warm-11 changes, runtime capacity/capped FPS estimates,
revisions, ELF identities and case names. Runtime capacity excludes presentation,
OS scheduling, adaptive draw skipping and live audio work. These are recreated
stationary Celeste scenes and scripted Moss windows, not traversal coverage.

## Implementation and compiler observations

Signed hybrid source `604e3a5` starts from unrolled `6eef559`. Fully offscreen
tiles retain the existing early rejection. A partial tile or false
`transparency_default` flag now dispatches to `blit_clipped_tile` in SDRAM.
The remaining BRAM kernel chooses between identity draw colors and remapping
using `palettes_default`; both paths skip source nibble zero. The third,
custom-transparency BRAM pixel loop is deleted. No game-specific selection,
VM patch, dependency pin or runtime rate is changed.

The existing fallback supports fully visible tiles too: clipped bounds become
`[0,8)` in each dimension. Its per-source transparency tests preserve custom
opaque zero, transparent nonzero colors and opaque colors mapped to destination
zero. Dirty marking remains correct in both fallback and hot paths. A
conservatively false flag safely selects the general fallback. Screen-only
palette changes can select the remapped branch, which still uses draw_palette.

| Production build | Tile kernel bytes | App BRAM bytes | Free bytes |
|---|---:|---:|---:|
| Parent tile `03130b7` | 466 | 14,126 | 210 |
| Unrolled palette `6eef559` | 658 | 14,318 | 18 |
| Compact palette `3cc5b18` | 570 | 14,230 | 106 |
| Hybrid `604e3a5` | 430 | 14,086 | 250 |

Production GCC 13.2 really unrolls four packed pairs per row in both hot loops.
The remapped row has eight conditional palette-load sites and no transparency
array loads. The default row retains its prior 31-instruction mnemonic/register
sequence after masking numeric operands, but moves four bytes. This masked
comparison is not byte identity or proof of equal scheduling costs.

All 15 other production BRAM functions retain their sizes; every entry moves,
and only one retains exact bytes. The production dispatcher remains 10,800
bytes, now at `0x4a78`. BRAM is uncached, so these facts do not establish BRAM
instruction-cache conflicts. SDRAM code/data and numeric operands are not held
fixed. The earlier fixed-slot diagnostics test different binary/layout policies
and cannot be added to these normal-build results.

The production clipped helper is unchanged in source, address (`0x1040d640`),
size (634 bytes) and bytes across all four audited tile builds. Fully visible
custom-transparency tiles now incur that helper's existing 16-byte stack frame
and SDRAM execution. Correctness is verified, but performance on other carts
or custom-transparency workloads is not established by these four windows.

In the actual game benchmark ELFs, hybrid BRAM is 13,948 bytes in all four
scenes. Its dispatcher is 10,724 bytes at `0x47ec`, matching the accepted
benchmark's entry and size. The preceding palette variants' Moss dispatchers
grew 42 bytes; that growth is absent here. Equal entry/size is not a body-byte
identity claim. Production and benchmark layouts are distinct and are recorded
separately.

The experiment achieves its code-size goal but not its frame-time goal.
Removing a loop frees BRAM without ensuring a faster complete runtime. These
results neither isolate individual guard costs nor identify an exact compiler,
cache or instruction-level cause for every frame delta. No new unchanged-ELF
control or dual-issue instruction observer was run.

## Correctness and provenance

Before implementation, the unchanged 46-case spr/map oracle passes on unrolled
parent source. Two new independent cases draw custom-transparency tiles exactly
at `(120,120)`, for spr and map. The expanded 48-case oracle passes on the
parent before the dispatch change, then on the hybrid natively and with all 35
translation units consistently rebuilt under ASan and UBSan. Removing only the
new transparency guard makes 19 cases fail with pixel/RAM mismatches, including
both new edge cases; it is an assertion failure, not a build failure or crash.

Coverage retains custom opaque zero, opaque mapped zero, arbitrary transparency,
pal/palt resets, screen-only and direct-RAM palette changes, clips/offscreen
tiles, source bases, multi-tile calls, flips, camera offsets, redirected targets,
aliasing and dirty marking. The fixture compares every displayed pixel and a
weighted checksum over packed target RAM. That checksum is not a byte-identity
claim. Existing native unit/runtime suites also pass; their optional local-cart
Celeste acceptance test is skipped because no carts are installed there.

All four game cases run native 600-frame repeats and repeated QEMU captures
with native agreement. The independently collected 600 frames of raw pixels,
palettes and PCM match the accepted output byte for byte. Collector transcripts
match the validated normal runner. Quiet and scanout RTL replay, memory checks
and deliberate output-oracle rejection are required before export. Pointer-bearing
checkpoints are compared only within the same ELF.

The exporter freshly validates all 20 cases used by the 16 comparisons, along
with input/binary inventories, routes, compiler settings, raw channel hashes,
repeat checkpoints, prepared inputs and replay logs. Program inventories match
apart from runtime.cpp. Harness revision differences are allowed only for report
Markdown/CSV files. Runtime.cpp retains the production builtin policy; other
translation units and linking retain the original freestanding flags. Final
Lua seed is `0x5eed1234`, platform is explicit os20/90 MHz, and no API timers
or path counters enter the timing builds.

Celeste uses frames 100–111 with no buttons; Moss uses the retained seed-7 input
route at frames 180–191 and 234–245. These are the same routes as the preceding
tile studies. The production ELF is
`28409c7150bf65975c850d4515de287e00665e3d752637dbaff901bbc1d4833e`.
Its original build record retains the dirty parent revision because compilation
preceded committing; the recorded runtime content hash matches signed `604e3a5`.

Private source, fixtures, mutation failure, production build/audit, comparison
exports and raw channels are retained under
`experiments/pico8-sources/tile-hybrid-20261016-r1`. New cases are
`experiments/pico8/tile-hybrid-os20-{intro2,trailhead,moss-steady,moss-gc}-candidate-20261016-r1`.
Existing baselines and prior prototypes remain untouched. No active port,
accepted audio worktree, original SDK, SD card, dependency pin or remote is changed.

Fresh checks pass for all 1,631 frozen inputs and the existing os20 platform.
The final private evidence manifest covers 2,759 files. SHA-256:
`afcbb077c1cdf3fd90a6a9447a35bd5337beb4bd98eff5b2579aa85359b4dcec`.
