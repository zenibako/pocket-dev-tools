# GC-wrapper policy controls — os20 / 90 MHz

Holding GC-wrapper inlining consistent does not remove the palette candidate's
tradeoffs. A shared `noinline` policy still regresses Trailhead and Moss steady
against original main. The opposite, forced-inline policy helps three windows
on main but regresses Trailhead; the palette candidate cannot link within the
existing benchmark BRAM budget. Neither policy is promoted.

This follows the [compiler-budget and renderer investigation](PALETTE-COMPONENTS-OS20.md).
That investigation proved that palette edits change GCC's global inline-budget
decisions, but did not attribute frame cycles to individual choices. These new
controls test one demonstrated discontinuity without increasing the global
inline budget or changing memory limits.

## Matched noinline controls

Both main `1ef6525b9bd875ee7bb3ea81162637b53f12aa7b` and the palette branch at
`f60fd0f` receive the same private pre-inventory change: add `noinline` to the
definition of `luaC_step`. Its body remains unchanged. The latter branch's
runtime is the implementation from `faa9b61`; its later commit adds documentation.

Quiet frame-time changes, with positive values slower:

| Window | Main noinline vs original main | Palette noinline vs original main | Palette vs main, both noinline |
| --- | ---: | ---: | ---: |
| Celeste tower | +1.464526% | -0.443335% | -1.880323% |
| Celeste Trailhead | +1.295252% | +2.266718% | +0.959044% |
| Moss steady | +2.084680% | +0.622644% | -1.432180% |
| Moss GC | +1.482548% | -0.155071% | -1.613695% |

Scanout preserves every sign in this table. The palette candidate can beat the
slower noinline main control while still losing against original main. The
[complete CSV](GC-POLICY-OS20.csv) includes all five comparison groups, exact
timings, warm-frame changes, output identities, images and changed-source lists.

Actual disassembly confirms the intended policy in all eight new targets:
each VM has exactly four calls to `luaC_step`, no direct `luaC_forcestep` call,
no inlined `gcrunning` guard/debt blocks and no specialized wrapper clone.
All eight VMs are 10,650 bytes / 3,454 instructions at `0x47ec`. Each wrapper is
32 bytes / 12 instructions. The VM shrinks by 74 bytes from ordinary main;
main's total application BRAM shrinks by 72 bytes because of alignment.

Independent Moss inspection further finds that main/candidate VM code differs
only at 17 same-width `jal` instructions targeting five BRAM helpers relocated
by 124 bytes. Their GC-wrapper and forced-step bodies have identical bytes at
identical addresses. This is a strong control for the targeted wrapper policy,
while retaining differences in renderer/palette code and broader placement.

Trailhead still regresses in the matched pair. Therefore differing wrapper
inlining is not necessary for a palette regression under this policy, and
equalizing that choice is not a complete remedy. It does not prove that the
original inline mismatch contributes zero cost. Policy changes affect all
callers and can perturb other compiler decisions; these are whole-build
comparisons rather than fixed-image cycle attribution.

## Opposite control: forced inlining

We also add `always_inline` to the same definition in separate main/candidate
snapshots. This verifies the other uniform policy without combining it with
additional runtime changes.

The four main targets fit and pass all controls. Their VMs contain four direct
`luaC_forcestep` calls and four `gcrunning` tests; no `luaC_step` symbol or call
remains. The VM is 10,810 bytes / 3,506 instructions at `0x4838`.

| Window | Main forced-inline vs original main, quiet |
| --- | ---: |
| Celeste tower | -0.526864% |
| Celeste Trailhead | +2.253177% |
| Moss steady | -0.580694% |
| Moss GC | -1.380478% |

Scanout retains these signs. [Forced-inline main CSV](GC-INLINE-OS20.csv)
preserves exact data. These are main-only comparisons, not evidence of a matched
palette improvement.

Forced inlining grows more than the VM: versus ordinary main, VM code adds
86 bytes, `luaD_precall` adds 50, `luaD_callcfast` and its constant-propagated
clone add 24 each, and alignment adds six. Total BRAM growth is 190 bytes.
The definition attribute affects every caller, which is why a small GC wrapper
can consume significantly more space than one new copy.

Main uses 14,230 of 14,336 benchmark BRAM bytes. **All four palette builds require
14,354 bytes and fail the unchanged linker assertion by 18 bytes.** No candidate
ELF, QEMU checkpoint or RTL performance result exists for this policy. Failed
maps and logs are preserved; neither the linker region nor frozen platform was
expanded. No new production-build or package-fit claim follows from these
benchmark-only links.

## Verification and disposition

The evidence covers 20 unique complete cases: eight retained original
main/palette cases, eight new noinline cases, and four new forced-inline main
cases, plus four rejected forced-inline palette links. All successful new cases
pass repeated native/QEMU checks, native output equality, strict quiet/scanout
RTL memory checks and rejected negative controls. Their 600-frame raw indexed
pixels, palettes and PCM match original main byte for byte.

Source/configuration comparisons remain strict: matched noinline pairs change
only `runtime.cpp`; policy-only comparisons change only `lgc.c`; combined
comparisons require exactly those two files. Archives are copied byte for byte
from the retained baseline, so no container-hash exception is needed. The source
checkouts, dependency pins, frozen inputs, platform and signed palette branch
remain unchanged. No experimental attribute is included in shipped source.

These results reject both global wrapper policies as a solution to the
no-regression requirement. Further work should target a specific placement or
call-site choice and verify the resulting whole build, rather than treating
GC-wrapper inlining as the sole cause or assuming smaller VM code is faster.

Private evidence is in `experiments/pico8-sources/gc-policy-20261017-r1` and
`gc-inline-20261017-r1`: explicit policy/source hashes, launchers, immutable
cases, raw collectors, disassembly audits, validating exporters and failed link
records. All timings are simulated os20 at 90 MHz, fixed seed `0x5eed1234`,
twelve measured frames, and the same compiler policy, terminal drain, routes and
audio model as the original source matrix. Windows are tower/Trailhead 100–111,
Moss steady 180–191 and Moss GC 234–245. These are selected recreated scenes,
not full-game or physical Pocket FPS measurements.
