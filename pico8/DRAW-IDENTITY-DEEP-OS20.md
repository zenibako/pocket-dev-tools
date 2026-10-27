# Palette trade-off investigation and combined BRAM diagnostic

We found a combination that improves both games in controlled copies of the
accepted binary. It combines a small no-op `pal()` path with an on-demand check
of the actual draw palette, avoiding the rejected count-maintenance source
rebuild. All four tested windows improve under quiet and scanout traffic.
This is a diagnostic result, not a promoted source change or installable build.

## The earlier guard explanation was incomplete

The [draw-count source experiment](DRAW-IDENTITY-OS20.md) added two address
instructions to its tile guard and regressed overall. Replacing its renderer
with the accepted renderer makes that candidate slower again. The original
522-byte renderer fits in the candidate's 526-byte function slot; its internal
branches need no relocation, and four compressed-NOP bytes fill the remainder.
All other ELF/BRAM bytes, SDRAM inputs, stack and simulator stay fixed.

| Quiet runtime, ms/frame | Accepted source | Failed count source | Count-source host with accepted renderer |
|---|---:|---:|---:|
| Trailhead | 42.14437 | 42.82921 | 42.92057 |
| Moss steady | 48.68967 | 48.88591 | 49.11306 |

Reverting only the renderer increases candidate time by **0.2133% / 0.2466%**
in Trailhead and **0.4646% / 0.5070%** in Moss steady, quiet/scanout respectively.
The residual against accepted source is 1.8418% / 1.8745% for Trailhead and
0.8696% / 0.8714% for Moss. Thus the new renderer is a net benefit within that
candidate image; its guard cannot explain the overall source-build regression.
[Complete comparison data](DRAW-IDENTITY-DEEP-OS20.csv) preserves precision,
warm-frame changes and image identities.

Both copied-host identity controls reproduce every quiet cycle exactly. The
substitutions pass repeat QEMU with byte-identical full warm checkpoints and
stacks, quiet/scanout output and memory checks, and rejected negative oracles.
An all-path register audit verifies the same caller-clobber set, preserved
callee registers/stack, and no external references. Actual-image review verifies
all four ELF/MIF/input copies against the intended edits.

A separate native census, enabled and disabled over 600 frames for each scene,
locates the bookkeeping work. Both modes retain every original frame/hash
transcript, including pixel, display-palette, PCM, input, FPS and pair counts.
Counts below sum the twelve selected frames; they are frequencies, not cycles.

| Window | `pal()` calls | Palette-reset writes | Changed scalar draw entries | Changed scalar screen entries | Flag recomputations |
|---|---:|---:|---:|---:|---:|
| Celeste tower | 3480 | 0 | 0 | 0 | 0 |
| Trailhead | 3480 | 0 | 0 | 0 | 0 |
| Moss steady | 184 | 24 | 60 | 96 | 0 |
| Moss GC | 120 | 24 | 0 | 96 | 0 |

Celeste makes 290 no-op `pal()` calls per frame. Its transparency-reset helper
is called 579 times per frame, with no writes; the other 289 calls come from
`palt()`. None of the newly added draw-count maintenance executes in these
selected Celeste frames. The actual no-op `pal()` path also retains the same
30 instructions, register operations and widths in accepted and count-source
ELFs. Profiling is disabled in these runs. Its code addresses, branch targets
and the addresses of its four instruction-cache lines move.

This localizes a substantial effect outside the renderer and rules out added
count updates or extra no-op-path instructions as its direct cause. It does
not isolate cache conflicts, branch prediction, data placement or all other
LTO/code-generation effects. BRAM itself is uncached. Calling the entire
regression a two-instruction cost would be wrong.

## A smaller combination

The new probes start from accepted source `9f4cd16`, preserving its renderer,
VM, palette mutations, object layout and warm process state. The first probe
redirects the eight-byte `pal()` entry through a 76-byte unused-BRAM stub.
It returns zero only for zero arguments, existing default palettes/default
transparency, and a null profile hook. Every other case executes the stolen
original prologue and resumes the original implementation.

This alone helps Celeste but fails the strict gate: Moss steady changes by
−0.0006% quiet and +0.0676% scanout; Moss GC changes by +0.0012% / +0.0157%.
A second 102-byte probe moves the original prefix, retaining profiling and
resuming original argument/reset blocks. It also helps Celeste but regresses
both Moss windows slightly. Both rejected probes remain preserved.

The successful diagnostic pairs the first stub with a **74-byte on-demand draw
identity helper**. It changes only the renderer's existing false-palette branch:
when the combined flag is false, the helper compares all sixteen draw entries
as four aligned little-endian words. Actual draw identity returns to the
original transparency check; any remap returns to the original general loop.
The default combined-palette path executes no extra test. No palette mutation,
initialization, import, reset, saved-state code or derived-state cache changes.

Unlike the earlier timed-only forced-identity probe, this helper checks actual
contents every time it is needed. It handles real draw remaps during Moss's
warm-up and keeps custom transparency on the existing general path.

| Window | Accepted quiet ms | Combined quiet ms | Quiet change | Scanout change |
|---|---:|---:|---:|---:|
| Celeste tower, frames 100–111 | 25.87136 | 25.65866 | −0.8221% | −0.8699% |
| Trailhead, frames 100–111 | 42.14437 | 41.93367 | −0.5000% | −0.5000% |
| Moss steady, frames 180–191 | 48.68967 | 48.43317 | −0.5268% | −0.4625% |
| Moss GC, frames 234–245 | 49.05153 | 48.78847 | −0.5363% | −0.4164% |

All eight quiet/scanout comparisons improve. Warm-eleven-frame comparisons
also improve, so this is not limited to the first cold-cache frame. The combined
Celeste cycle arrays equal the first reset-only probe: the palette helper adds
no measured cost on its existing default path. [Full data for all three probes](PAL-NOOP-BRAM-OS20.csv)
includes rejected variants, exact timings and image hashes.

## Validation and remaining work

Across the three probes, all twelve scene diagnostics pass repeated QEMU,
quiet RTL, scanout RTL, output/memory oracles and deliberate negative controls.
Four additional unmodified accepted copies reproduce their quiet cycles exactly.
For each patched image, the complete warm SDRAM checkpoint equals accepted
except for its explicit eight-byte function-entry patch; the stack is identical.
The combined probe additionally changes one four-byte BRAM branch and installs
154 bytes in unused BRAM: 76 reset bytes, four padding bytes and 74 identity bytes.
The ELF load/section sizes are extended only to cover those new bytes.
Independent reconstruction checks preserve every other code/data/input byte.

RV32 synthetic tests cover all six first-stub guard/fallback cases; the second
stub checks five cases including profiling-counter behavior. The identity helper
passes eighteen cases: default/custom transparency flags and a remap at each
of sixteen individual palette entries. Pointer/stack or saved-register checks
cover the relevant stub contracts. Guard-removal mutants fail for both reset
probes and for the final identity word. The tested helper machine bytes match
the installed diagnostic bytes, including the real return targets.

These game probes establish the selected QEMU/RTL output oracles, not a new
600-frame raw-byte export for each patched image. The native census preserves
600 frame/hash transcripts; accepted source cases retain their earlier raw
collectors. Those are separate kinds of evidence.

The measured environment is fixed seed `0x5eed1234`, simulated os20 at 90 MHz,
twelve frames per window, fixed PCM and matching routes/compiler policy.
The tower and Trailhead scenes are recreated through setup expressions; Moss
uses the recorded seed-7 input route. No physical Pocket FPS, whole-game
compatibility, presentation/OS scheduling or production timing claim follows.

The remaining step is a portable source implementation and actual production
link/fit, followed by fresh whole-source benchmarks. Production's accepted
image has only 154 BRAM bytes free. The two payloads total 150 bytes before
placement padding, so the budget is tight; this diagnostic's fit does not prove
that a compiler-generated source version will fit or retain its gains. The
frequent no-op `palt()` path is another measured opportunity, but is not changed
here. No new package, PR or source promotion was made.

Private evidence lives in `experiments/pico8-sources/draw-identity-deep-20261016-r1`,
`pal-noop-bram-20261016-r1`, `pal-noop-bram-20261016-r2` and
`pal-draw-combo-20261016-r1`. Fresh frozen-input and os20-platform checks pass;
accepted `9f4cd16`, rejected count source `3e4e15d` and active port `bc2e8b6`
remain clean and unchanged. The combined private manifest covers 851 files;
SHA-256:
`581bbccf7d69bbb5602fe907d792a903665ddf83ff3eb82ea689f76abb975dd9`.
