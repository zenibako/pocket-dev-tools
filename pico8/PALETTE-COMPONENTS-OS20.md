# Palette source tradeoffs: compiler budget and renderer isolation

The renderer is helping inside the combined candidate, yet the whole source
build regresses. We also found a concrete compiler effect that earlier kernel
experiments missed: changing palette code changes GCC's global inlining budget
and its GC-wrapper decisions inside otherwise unchanged VM source.

This extends the [source PR matrix](PALETTE-SOURCE-OS20.md) and
[earlier fixed-image investigation](DRAW-IDENTITY-DEEP-OS20.md). It does not
establish how many frame cycles come from each changed compiler decision.

## Separate source components still regress

The baseline remains main `1ef6525b9bd875ee7bb3ea81162637b53f12aa7b`.
Two explicit, private source transformations isolate the argument-free `pal()`
BRAM wrapper from the on-demand draw-palette identity check. Their composition
is byte-for-byte the runtime source in combined commit `faa9b61`. Neither the
active source checkout nor the signed palette branch was modified.

Quiet simulated frame-time changes against main, with positive values slower:

| Window | Reset wrapper only | Draw identity only | Combined |
| --- | ---: | ---: | ---: |
| Celeste tower, frames 100–111 | -1.006152% | -1.126153% | -1.489439% |
| Celeste Trailhead, frames 100–111 | +0.389818% | +0.425272% | +0.718773% |
| Moss steady, frames 180–191 | +1.080091% | +0.722059% | +0.136343% |
| Moss GC, frames 234–245 | +1.000052% | +0.823955% | +0.002292% |

All three variants fail the no-regression gate. Scanout preserves these signs;
[the full CSV](PALETTE-COMPONENTS-OS20.csv) records quiet/scanout means, warm-frame
comparisons, capacities, exact images and source-patch hashes. Source components
are recorded as main plus an explicit pre-inventory patch, not as new commits.

These are whole-source comparisons: their percentages cannot be added together
as independent kernel savings. Both separate components improve the tower and
regress Trailhead, even though reset-only retains the original tile source.

## The actual renderer helps within the combined image

The combined Celeste tile's default palette guard executes six instructions
where main executes four, even when the identity helper is skipped. The compiler
reconstructs a runtime-field address and branches back to the common path.
The function also grows from 522 to 596 bytes and changes register allocation.
That observation alone is not an explanation of its net cost.

We copied main's complete 522-byte renderer into the combined candidate's
596-byte slot and filled the remaining 74 bytes with compressed NOPs. Internal
branches move with the function; there are no external references to relocate.
An all-path register/stack audit confirms the donor respects the host's actual
compiler clobber contract. Every other ELF and BRAM byte stays fixed.

| Quiet ms/frame | Main | Combined | Combined with main renderer |
| --- | ---: | ---: | ---: |
| Trailhead | 43.293020 | 43.604199 | 43.720819 |
| Moss steady | 49.397436 | 49.464786 | 49.706198 |

Reverting only the renderer makes the candidate **0.267450% slower in Trailhead
and 0.488048% slower in Moss steady**. Scanout agrees: +0.267047% and +0.398325%.
The residual against main becomes +0.988146% and +0.625057% quiet. Thus the
renderer is a net benefit in this host; the full-build regression has effects
outside that renderer. This test does not identify those effects individually.
[Fixed-image CSV](PALETTE-FIXEDIMAGE-OS20.csv) preserves exact data and hashes.

## GCC's global inline budget changes unchanged VM code

Moss's `lvm.c` and `lgc.c` are byte-identical across source variants, but the
actual `luaV_execute` machine code differs:

| Variant | VM bytes | Instructions | Changed wrapper sites relative to main |
| --- | ---: | ---: | ---: |
| Main | 10,724 | 3,479 | — |
| Reset only | 10,766 | 3,490 | One additional GC-wrapper inline |
| Draw identity only | 10,766 | 3,490 | One additional GC-wrapper inline |
| Combined | 10,782 | 3,497 | Two additional GC-wrapper inlines |

The VM starts at `0x47ec` in all four. Combined replaces two `luaC_step` calls
with direct `global_State::gcrunning` tests, `luaC_forcestep` calls and stopped-GC
debt updates. The guards add 16 bytes/four instructions; the two debt blocks add
42 bytes/fourteen instructions, matching the 58-byte/eighteen-instruction net
growth. Block ordering and branches also change. This is compiler code generation,
not just linker relaxation. BRAM is uncached, so moving BRAM addresses alone is
not evidence of instruction-cache conflicts.

Independent relinks with `-fdump-ipa-inline-details` reproduce **both original
measured ELFs byte for byte**. Their IPA dumps explicitly explain the decision:
main rejects the two estimated-frequency-16.501166 edges with
`--param inline-unit-growth limit reached`; combined accepts them with the same
cost estimates and hints. The hotter edge is accepted in both; the cold edge is
rejected in both. The global small-function-inlining summary changes from
45,078 → 60,818 to 45,112 → 60,866 compiler size units. Those units are not bytes.

This establishes why unrelated VM instructions changed. It does not prove that
GC inlining alone causes the measured slowdown. Other inlining, SDRAM placement,
callee behavior, branch scheduling and memory effects remain possible.

## Verification and next control

The 16 source cases include eight new component cases and the eight retained
main/combined cases. Every case passes repeated native/QEMU output, strict quiet
and scanout RTL memory checks, and deliberately failing negative controls. All
component routes preserve 600 frames of raw indexed pixels, palettes and audio.
The recreated ZIP containers have different metadata; the exporter independently
verifies both archive hashes and byte-identical ordered uncompressed entries,
then permits only that container-hash difference in configuration comparison.
Cart identities, routes and all program-file checks remain strict.

Both fixed-image unmodified copies reproduce every original quiet cycle exactly.
The two renderer substitutions pass repeated QEMU with byte-identical complete
warm SDRAM and stack, quiet/scanout output and memory checks, and negative controls.
Independent export reconstructs every edited ELF/MIF byte and verifies that the
surrounding code, checkpoint, input and simulator remain unchanged.

The next useful experiment is to hold the GC-wrapper inline policy equal in
main and candidate, then repeat matched builds. This targets a demonstrated
compiler discontinuity without assuming a larger global inline budget improves
performance. No new source optimization passed the gate or was promoted here.

All timings use fixed seed `0x5eed1234`, simulated os20 at 90 MHz, twelve measured
frames and the same runtime builtin policy and untimed terminal drain as the
source PR matrix. These are selected recreated cart windows, not full-game or
physical Pocket FPS measurements. No package or deployment was made.

Private evidence: `experiments/pico8-sources/palette-components-20261017-r1`
(`run.py`, `variants.json`, `export.py`, raw outputs and exact-ELF compiler dumps),
and `palette-fixedimage-20261017-r1` (static audit, copied hosts, controls and
validating exporter). The main dump's decisive lines are 186923–186939; the
combined dump's are 186952–186989, under
`inline-dumps/{baseline,candidate}/build/pico8/program.elf.wpa.085i.inline`.
