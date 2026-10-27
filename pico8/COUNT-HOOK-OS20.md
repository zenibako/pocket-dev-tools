# Guarded delegates and count-hook servicepoints

The count-hook review concern does not reproduce in Pico8Pocket's patched VM.
The accepted delegate body skips zero count-hook servicepoints. Added regression
coverage and an explicit explanation; no production behavior change is needed.

## Root cause of the review discrepancy

Stock Lua count hooks count instructions. Pico8Pocket's existing
`z8lua-servicepoints.patch` and `z8lua-pc-register.patch` instead count calls,
jumps and loop boundaries. The final VM dispatch does not decrement the count
on every instruction. The exact admitted delegate has GETTABLE, GETTABLE,
RETURN and an unreachable RETURN: none is a servicepoint. Ordinary C entry
through `luaD_call` does not add one, and admitted nested delegates have the
same shape. Call/return/line hooks already require the fallback.

Rejecting every count hook would disable Celeste's shortcut during normal
frames: the runtime installs a count hook for cooperative audio/input service
and runaway-loop protection. There is no need to distinguish trusted from
arbitrary count callbacks when the accepted body skips no events.

## Empirical checks

A C count hook mutates the terminal table from 7 to 99 when fired. Periods 1
and 2, at one and four delegation levels, produce 7 with zero hook calls and
an unchanged remaining count in both the guarded lookup and an ordinary Lua
body invoked from C. An unsupported delegate containing a loop fires the hook
and returns 99. A separate private probe forced the ordinary callback through
positive GC debt and obtained the same zero-event result.

A private negative VM variant restores per-instruction decrements. The new
regression test then fails on the ordinary result assertion, reproducing the
reviewer's assumed mismatch and proving that the test detects a future change
to the servicepoint policy. The mutant is not in the PR or any performance case.

Core, runtime and delegate suites pass, including the new count-hook contracts.
The optional local Celeste cart acceptance test is skipped because that checkout
has no cart assets; the separate benchmark cases below use preserved private carts.
All 18 dependency patches reapply and reproduce 62 prepared source/header files;
assertion-enabled VM compilation passes. Independent review found no blocker.

## Fresh simulated performance

Baseline is the prior PR #15 executable, corresponding to reauthored tip
`771c5b2`; preserved cases use implementation-equivalent `55d9e35`/`c400307`.
Candidate is signed `f17ad1872c49238b83c95ff9c44c11e0c8067858`.
Both use the fixed seed `0x5eed1234`, original input/cart/audio and os20 at 90 MHz.
Every measured frame cycle count is identical, under quiet and scanout traffic.

| Scene | Candidate quiet ms | Change | Candidate scanout ms | Change |
| --- | ---: | ---: | ---: | ---: |
| Moss steady | 48.042425 | +0.00% | 48.740644 | +0.00% |
| moss-gc | 48.330589 | +0.00% | 49.056132 | +0.00% |
| Celeste full throw | 74.857006 | +0.00% | 75.000456 | +0.00% |
| Celeste whole grapple | 58.972933 | +0.00% | 59.100924 | +0.00% |
| trailhead | 41.066409 | +0.00% | 41.193099 | +0.00% |
| intro2 | 25.890126 | +0.00% | 25.983240 | +0.00% |

This is a comparison to the previous PR build, not main. The earlier intro
trade-off relative to main is unchanged. These are simulated runtime costs;
physical Pocket FPS and OS/audio/display scheduling are not measured here.
Windows are Moss steady 180–191, Moss GC 234–245, whole grapple 304–308/full
throw 305–306, and Trailhead/intro 100–111.

All five fresh cases pass full native pixel/palette/PCM byte and pair-count
comparisons, repeated QEMU captures, quiet/scanout RTL, corrupted-pixel negative
controls and memory oracles. Target comparisons cover measured-window hashes
and pair counts, not full raw target channels. No production behavior, service
hook policy, compiler flags or linker placement changed. The offline production
ELF is byte-identical to the previous PR build, including its 166 free BRAM bytes
and entry at `0x10400000`.

Production SHA-256:
`578fa706c75b79f22fc8f9c5a6090fb464c6f11da9886024315308b9cddb5404`.

Private evidence is under `experiments/pico8-sources/count-hook-20261019-r1/`.
`report.py` validates source identity, original launcher hashes, complete raw
channels, baseline/candidate cycle logs, repeat captures, seed/clock, negative
controls and memory oracles before generating [COUNT-HOOK-OS20.csv](COUNT-HOOK-OS20.csv).
Original fresh-case launch records remain under `moss-link-order-20261019-r1/`
with suffix `count-hook-r1`. No SDK/OS source, active checkout or SD card changed.
