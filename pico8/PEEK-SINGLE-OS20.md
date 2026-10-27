# Single-result peek experiment — 2026-10-16

The single-result `peek()` fast path is rejected: both Moss and Celeste
Trailhead regress against accepted audio. The rebased audio source at
`9f4cd16` remains the validated candidate. These are simulated os20/90 MHz
runtime frame costs, not physical Pocket FPS.

| Scene | Accepted audio, ms | Candidate, ms | Quiet cost change | Scanout cost change |
|---|---:|---:|---:|---:|
| Moss steady | 48.287563 | 48.534021 | +0.5104% | +0.4187% |
| Celeste Trailhead | 42.322168 | 42.430769 | +0.2566% | +0.2575% |

The [validated CSV](PEEK-SINGLE-OS20.csv) records exact values, source and ELF
hashes, BRAM sizes and case identities. The gate stopped after these two
scenes. Moss GC, intro 1, intro 2 and title cases were created but not run;
there is no new timing evidence for those windows.

## Implementation and trade-off

Signed candidate `3c91e2e` adds a return path for `count <= 1` after the existing
argument conversions. It retains the existing remap-aware framebuffer sync,
reads one masked RAM address, pushes one value and returns. The multi-result
loop, count limit, stack reservation and address wrapping remain in place.
No dependency, platform, source pin or runtime rate changes were made.

The opportunity came from the earlier [Celeste investigation](CELESTE2-OS20.md):
the cart reads its level tiles through `peek(0x4300+...)`, so avoiding generic
multi-result work could benefit gameplay. Previous profiles recorded 3,360
calls in the sampled Trailhead window; those historical counts are not a
current-build cycle attribution. They did not show this opportunity in Moss.

GCC produces a separate straight-line single-read path, but that alone does
not establish a frame improvement. In both benchmark ELFs, `api_peek` grows
from 412 to 462 bytes. The production ELF goes the other way, from 508 to 462
bytes. The different surrounding link contexts therefore produce different
baseline code-generation decisions. Both size directions must be reported;
the smaller production function is not evidence that the benchmark got faster.

LTO changes surrounding code/data placement: 549 recorded symbols move in the
Moss case and 431 in Trailhead; BRAM contents differ despite stable size. The
main VM and fast-call functions keep the same addresses and sizes, while the
Moss environment helper moves by 64 bytes. This is evidence of collateral
binary changes, not proof of a particular cache conflict or stall mechanism.
The measured regression cannot be assigned solely to the single-read body.
There was no fixed-layout `peek()` experiment. The independently bounded
[environment lookup diagnostic](ENV-LAYOUT-CONTROL-OS20.md) tests a different
helper and must not be used as a numerical attribution for this change.

## Verification and retained evidence

Characterization tests first passed against the accepted baseline. They cover
omitted, nil, one, zero, negative, string, fractional and boolean counts; the
single-result count; multi-result values; wrapped addresses; and dirty default
and remapped framebuffer reads. A deliberate private mutant skipping screen
synchronization fails the framebuffer checks. The implementation then passes
native core/runtime suites and the Celeste 600-frame/save-state replay.
Independent review found no blockers.

Both completed benchmark scenes pass two native 600-frame runs, repeated RV32
captures with native output equality, quiet and scanout replay, SDRAM/read/write
oracles and corrupted-output negative controls. Raw pixels, palettes and PCM
are byte-identical to baseline across 600 frames. Source inventories differ
only in `src/runtime/runtime.cpp`; compiler, flags, link command, routes, input
carts, seed and os20 CPU configuration match the accepted baseline.

The private production GCC 13.2 build succeeds. BRAM remains 14,182 of 14,336
bytes, leaving 154 bytes. No package was made from this rejected optimization,
and the accepted audio checkout was not modified. The active port checkout,
original SDK, SD card and frozen inputs were not edited.

Private `experiments/pico8-sources/peek-single-20261016-r1` retains the detached
signed source worktree, tests and mutation logs, production ELF, disassembly,
benchmark launcher, raw channels, derived layout reports and replay results.
`export.py` validates completed captures, exact raw channels, matching source
scope/build settings and replay log hashes before writing two CSV rows.
Source signature verification and clean working-tree checks pass.

Evidence manifest SHA-256:
`ffa145f81c252808dd34f7606c63b4a57c50c4553b61e1e6a6716949a6852d8d`.
