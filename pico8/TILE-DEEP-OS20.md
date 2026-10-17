# Tile investigation: draw identity versus screen remapping — 2026-10-16

We missed a useful distinction: **Moss's timed tile draws have an identity draw
palette and a remapped screen palette.** The shared `palettes_default` flag
covers both, so it correctly selects the general drawing path even though
those tiles need no draw-color lookup. Our earlier inference from that flag
to actual draw remapping was wrong for these windows.

A strictly fixed-host diagnostic confirms a measurable opportunity: selecting
the existing identity-draw loop in the verified Moss window saves **0.37%** in
quiet replay and **0.41%** under scanout. This is a diagnostic result, not an
implemented source optimization or a physical Pocket gain. The next source
experiment should track draw-palette identity separately while preserving the
combined flag's reset semantics.

This follows the [hybrid](TILE-HYBRID-OS20.md),
[palette/layout](TILE-PALETTE-LAYOUT-OS20.md),
[complete-tile](TILE-FULL-OS20.md) and
[rendering-cost](RENDER-COSTS-OS20.md) studies. Their frame measurements remain
valid. The interpretation of the original palette population needed correction.
No accepted runtime, prototype worktree, SDK pin, platform or SD card changes.

## The workload distinction

Fresh native counters inspect all 16 actual draw and screen palette entries,
derived flags and actual branch entries once per tile call. They do not infer
actual palette contents from a false optimization flag.

| Selected 12-frame window | Visible full tile calls | Draw identity | Screen identity | Existing color path |
|---|---:|---|---|---|
| Celeste tower | 2,436 | Yes | Yes | Default |
| Celeste Trailhead | 1,656 | Yes | Yes | Default |
| Moss steady | 540 | Yes | No | General / middle |
| Moss GC | 551 | Yes | No | General / middle |

The accepted renderer selects its general loop; the palette/hybrid prototypes
select their middle or remapped branch. The latter name describes code that
can remap colors, not proof that its current draw palette is nonidentity.
Moss's map contributes 540 calls in each window; the GC window also has 11
sprite tile calls. General/flipped sprite drawing is a separate path, outside
these tile counts.

Private cart inspection confirms the reason: its palette reset reapplies screen
mappings before the map draw, and the usual palette helper defaults to screen
mode. The selected false flag is accurate, not a stale conservative value.
No selected tile enters custom transparency or the clipped fallback. Indeed,
custom-transparency tile entries are zero over all 600 frames in these four
routes. The hybrid's selected trade-off therefore cannot come from executing
the custom-transparency body it moved into SDRAM.

There are real draw remaps elsewhere. Each 600-frame Moss route has 27,706
full tile calls: all 26,730 map tiles use identity draw colors, while 37 of 976
sprite tiles use nonidentity draw colors. Some occur at frames 91–93, before
the timed checkpoint. Forcing identity through the entire run would be wrong.
This also explains why a new predicate must track state, not assume Moss is
always identity or special-case a cart name.

Two census passes cover accepted audio and hybrid across four scenes, each
with enabled and disabled counters: 32 native runs. Four further runs cover
the exact two parent control cases used below. All 36 runs preserve their
original 600 PICOFRAME rows and fixed final seed `0x5eed1234`. The parent
Trailhead and Moss windows directly confirm the required identity-draw/default-
transparency precondition at all 1,656 and 540 visible full tile calls.
These are native counts and output-hash transcripts, not target cycle profiles,
raw-channel byte comparisons or unchanged observer layouts.

## Renderer-only timing with the host binary fixed

Both hosts are existing parent tile `03130b7` controls with a reserved 672-byte
tile slot at `0x4000`. Trailhead uses the renderer-prefix host; Moss uses its
dispatcher-last host. Comparisons within each host are matched; their absolute
times are not interchangeable with normal-build accepted baselines.

| Diagnostic | Window | Quiet baseline → diagnostic ms | Quiet change | Scanout change |
|---|---|---:|---:|---:|
| Audited unrolled palette kernel | Trailhead | 43.349 → 43.359 | +0.024% | +0.038% |
| Audited unrolled palette kernel | Moss steady | 50.131 → 49.982 | −0.297% | −0.287% |
| Identity-draw path, timed only | Trailhead | 43.349 → 43.358 | +0.020% | +0.037% |
| Identity-draw path, timed only | Moss steady | 50.131 → 49.947 | −0.366% | −0.406% |

[The validating CSV](TILE-DEEP-OS20.csv) records exact means, warm-11 deltas,
ELF hashes, original cases and diagnostic scope. All means cover 12 frames
on simulated os20/90 MHz, including the first frame with cold RTL caches.
Removing that frame preserves all signs. These are selected complete-runtime
frame costs; they exclude production OS, presentation and live audio scheduling.

For the unrolled diagnostic, only the audited 658-byte kernel plus compressed
NOP padding replaces the reserved slot. Its sole fallback transfer is relocated
to the unchanged host helper. All ELF bytes outside the slot, all other BRAM
bytes, VM bodies and entries, callers, SDRAM code/data, original warm checkpoint,
stack, input and simulator remain identical. Repeated patched QEMU warmups
produce the **entire original SDRAM checkpoint and stack byte for byte**.

An independent control-flow/register audit covers every instruction in the
original, unrolled and hybrid kernels and their fallback. Donors add no clobbered
register beyond the actual original compiler contract, preserve tail arguments,
and fit the reserved slot. This matters because GCC's interprocedural register
analysis can make a transplant unsafe even when ordinary ABI rules look valid.
The hybrid was audited for feasibility but not timed in this diagnostic.

The identity-draw probe makes just one four-byte code change: replace the
combined-palette `beqz` at `0x4072` with a NOP. Its palette load and subsequent
transparency guard remain. The original ELF warms normally; only the RTL BRAM
image is changed for the census-verified timed replay. A corresponding patched
ELF is retained for byte/disassembly inspection, but is never used for warmup.
This probe is deliberately invalid outside its verified identity-draw windows.
It neither maintains a new predicate nor measures that maintenance cost.

Fresh unmodified identity-copy replays reproduce every original quiet frame
cycle count exactly in both hosts. All four changed diagnostics pass output
hash oracles, memory/read/write checks, deliberately corrupted-output rejection,
and scanout. Independent export checks prove the outside-slot and initial-state
identities; no immutable baseline inventory is rewritten.

The small positive Trailhead results show that even the kernel-only change is
not free in every workload. We have not measured its exact issue/scheduling
cause. The probe removes a branch rather than implementing the proposed state
predicate, so its cost is not a forecast of that source change. These results
must not be subtracted from different-host full-rebuild deltas to assign exact
cycle shares to compiler effects.

## Build fidelity: the kernel matches better than its surroundings

The audit compares five production builds with their ten Trailhead/Moss target
benchmark ELFs. Accepted tile bytes match production exactly. Each later tile
kernel differs only in three individual bytes inside the two-instruction
fallback-address transfer. Pixel loops and dispatch instructions otherwise
match exactly. The clipped helper's 634 bytes also match. A generally wrong
renderer compiler mode is not supported by this evidence.

Whole-program parity differs materially. Production puts tile and span code
before the VM; normal benchmarks put nine VM functions before the tile and
five afterward. Production uses SDK `SUBALIGN(8)`; the normal benchmark linker
does not. VM sizes, drawing wrappers, surrounding translation-unit compiler
policies, libc startup and allocator differ. Only runtime.cpp's builtin policy
had been matched. Those differences limit production extrapolation from the
full-frame source rebuilds, despite strong kernel parity. BRAM is uncached;
relocation alone is not evidence of BRAM instruction-cache conflicts.

## The next source opportunity

Use the accepted renderer's existing default-color loop with a separate exact
draw-identity predicate. Keep `palettes_default` combined: argument-free `pal()`
uses it to decide whether to reset **both** draw and screen palettes. Redefining
that flag would break screen-palette reset behavior.

An exact count of nonidentity draw entries, from 0 to 16, can fit in the existing
one-byte hole after `screen_ram_dirty`. Existing RV32 DWARF locates that padding
at `0x18311`, before `draw_target` at `0x18312`. It offers a way to avoid moving
later runtime fields; a real implementation must verify native/target offsets
and total size. Update the count only on changed draw entries, leave it alone
for screen-only changes, and rebuild it on RAM imports and state restoration.
Initialize/reset it on create, load and `pal()`. Transparency remains independent.

That is a narrower opportunity than adding another tile loop. It still needs
state-transition tests, a production fit check and fresh two-game source-build
benchmarks. No new source fix, package, PR or claim of passing the no-regression
gate is made by this investigation.

Private diagnostics are under `experiments/pico8-sources/tile-deep-20261016-r1`:
`path-census` and its separate `parents-only` evidence; `build-audit` for compiler,
placement and padding facts; `slot-audit` for actual register/control-flow safety;
and `slot-runs` for the copied hosts and all execution controls. Original
cases and their source/provenance remain unchanged.

Fresh checks pass for all 1,631 frozen inputs and the existing os20 platform.
Independent actual-image and final-report reviews find no blockers. The final
private evidence manifest covers 478 files. SHA-256:
`af955fcdb4de7296ad86bbbc2c175af4c0821caab93a551a1f4a742187d766e0`.
