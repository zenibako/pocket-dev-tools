# Separate draw-palette identity experiment

The source candidate is correct but fails the established no-regression gate.
Keep accepted audio/foreach source `9f4cd16f6d3d730b8edaab1102387c6958df5536`
and its package. The experiment is preserved in signed source commit
`3e4e15ddda2fc8b990399582a18ece3caf7f9e31`; it is not promoted or packaged.

This follows the [deeper palette investigation](TILE-DEEP-OS20.md), which found
that Moss's timed tiles have identity draw colors and a remapped screen palette.
The combined `palettes_default` predicate therefore unnecessarily selects the
existing general tile loop. The new experiment starts from the accepted
renderer, with none of the previously rejected tile kernels.

## Full-build results

Fixed seed `0x5eed1234`, simulated os20 at 90 MHz, twelve timed frames per
window. Negative changes mean less runtime time. Both source builds use the
same runtime compiler policy. Baselines are the retained accepted-source
`tile-full-os20-*-baseline-20261016-r1` cases, not older timings compiled with
a different runtime policy. [Validated data](DRAW-IDENTITY-OS20.csv) records
full precision, source/ELF identities, first-frame and warm-frame changes.

| Window | Accepted ms | Candidate ms | Quiet change | Scanout change |
|---|---:|---:|---:|---:|
| Celeste 2 tower, frames 100–111 | 25.87136 | 25.88509 | +0.0531% | −0.0171% |
| Celeste 2 Trailhead, frames 100–111 | 42.14437 | 42.82921 | +1.6250% | +1.6239% |
| Moss steady, frames 180–191 | 48.68967 | 48.88591 | +0.4031% | +0.3625% |
| Moss GC, frames 234–245 | 49.05153 | 48.75696 | −0.6005% | −0.5645% |

Trailhead's warm eleven frames also regress by 1.6250%; its difference is not
limited to the first cold-cache frame. Moss's two windows move in opposite
directions under both memory-traffic controls. The tower remains below the
30 FPS runtime budget. Trailhead's quiet simulated runtime capacity changes
from 23.728 to 23.349 FPS; these are not physical Pocket FPS measurements.

All four candidate cases pass native 600-frame repeats, repeat QEMU captures,
quiet RTL, scanout RTL and deliberate negative controls. Each candidate's
600-frame raw pixel, display-palette and PCM streams equal accepted output
byte for byte. The exporter revalidates eight complete cases and their
source/binary inventories before emitting comparisons. Only runtime.cpp
changes in the program inventory.

## Change and correctness

An exact count of nonidentity draw entries, 0..16, occupies the padding byte
after `screen_ram_dirty`. Changed scalar/table draw entries adjust the count;
screen-only changes leave it alone. RAM imports and state restoration rebuild
it. Create, cart load and palette reset initialize it. The tile guard uses
count zero plus default transparency to select the original default loop.

The existing combined `palettes_default` still controls argument-free `pal()`
resetting both palettes. The screen palette and saved-state format retain their
semantics. All 58 existing member offsets and runtime size are empirically
unchanged in native and RV32 DWARF. Production allocation size and field
instructions corroborate the RV32 layout.

The public runtime suite adds 22 literal palette-transition cases, each using
spr and map, checking pixels and screen-palette values, and checking a saved
state after deliberately changing draw colors. The original and candidate
pass these tests. The candidate also passes the full native core/runtime
suites and a separate 48-case pixel/RAM-checksum oracle, natively and with all
35 translation units built under ASan/UBSan.

A private lookup counter reproduces the original opportunity: the accepted
source fails exactly two screen-only cases requiring zero draw-palette reads;
the candidate passes all 48 cases. This instrumentation is absent from all
timed and production builds. Removing scalar count maintenance fails 18 pixel
oracle cases. Replacing the combined reset guard with draw-only identity fails
the public screen-only reset case both before and after state restoration.

## Why the saving does not establish a win

The branch opportunity is real: the candidate removes unnecessary draw-palette
lookups without changing pixels. Two additional costs are also real:
incremental/rebuilt count maintenance and different guard code generation.
The production tile grows from 522 to 526 bytes. Its new count address requires
an extra `lui/add` pair on the default path because count and transparency
are in different address regions. After guard selection, the original pixel
loop remainder is byte-identical, shifted four bytes.

Production BRAM remains 14,182 bytes with 154 bytes free; existing alignment
absorbs the growth. The dispatcher stays at 0x4ad8 with size 10,800 bytes.
Other BRAM function sizes and masked instruction sequences remain equal,
but their raw bytes and SDRAM code/data addresses change. SDRAM .text grows
by 512 bytes against the fresh accepted production build. Thus these are
complete source-build measurements, not an isolated measurement of palette
lookups or the two extra instructions. BRAM itself is uncached.

The earlier copied-host branch probe avoided these source-build costs; its
small Moss improvement did not predict the complete candidate. The current
measurements do not apportion the regressions between guard cost, mutation
bookkeeping and surrounding binary placement. No claim that any single one
explains the full Trailhead regression is supported. A useful follow-up would
first isolate the identity predicate's addressing cost while preserving the
accepted host binary, before trying another complete source layout.

## Evidence and limits

Private source, tests, production ELF, audit, launchers and validated captures
are under `experiments/pico8-sources/draw-identity-20261016-r1` and the four
`experiments/pico8/draw-identity-os20-*-candidate-20261016-r1` cases. The
production ELF SHA-256 is
`23a8b468ca177a3c545c9728b956b1ba86a7d126ef0f480623d4ba2c26db9d98`.
Its pre-commit build provenance maps to the exact signed runtime content;
the original provenance is retained.

Fresh frozen-input and os20-platform checks pass. The private manifest covers
2,803 files; SHA-256:
`be22fe8d7e90f6e804e4885d9547ce8c2e421102c535d9a23afdebad42a5069e`.
The active port and accepted source worktrees remain clean and unchanged.

These are selected deterministic runtime windows under simulated os20/90 MHz.
They do not establish physical Pocket speed, whole-game compatibility,
presentation/OS scheduling, or isolated kernel cycles. With the gate already
failed, no extra title/intro windows, package or PR are produced.

The [controlled follow-up](DRAW-IDENTITY-DEEP-OS20.md) finds that reverting
only this candidate's renderer makes it slower again. It also records a
count-free combined diagnostic that improves both games in copied accepted
images; a production source implementation remains untested.
