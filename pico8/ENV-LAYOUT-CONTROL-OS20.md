# Fixed-layout environment lookup diagnostic — 2026-10-16

The leaf lookup algorithm helps Moss when the accepted surrounding binary is
held fixed. It is effectively flat in Trailhead. The previous full source
rebuilds remain rejected; this diagnostic is not a production optimization.
These are simulated os20/90 MHz runtime frame costs, not physical Pocket FPS.

| Scene | Accepted audio, ms | Diagnostic, ms | Quiet cost change | Scanout cost change |
|---|---:|---:|---:|---:|
| Moss steady | 48.287563 | 47.943131 | -0.7133% | -0.7851% |
| Celeste Trailhead | 42.322168 | 42.325204 | +0.0072% | -0.0210% |

The [validated CSV](ENV-LAYOUT-CONTROL-OS20.csv) records exact means, hashes
and input identities. Baselines are the accepted [audio cases](AUDIO-PAIRS-OS20.md),
whose source tree is identical to rebased audio commit `9f4cd16` on merged main.
The [full lookup experiments](ENV-LOOKUP-OS20.md) include the rejected R3
rebuild at `4be2dd9`: +3.670% Moss and +3.170% Trailhead in quiet replay.

## What was isolated

Each accepted ELF and prepared replay checkpoint was copied to a new private
folder. Only the original 366-byte `fastchain` slot was replaced: Moss at
`0x1041f200`, Trailhead at `0x1041f0c0`. All bytes outside that slot, ELF headers,
other code/data addresses, original stack, BRAM firmware, simulator, cart,
prepared output oracles and warm heap were preserved. The unused tail contains
compressed NOPs. No frozen case or hash inventory was changed.

A raw transplant of R3's 198-byte leaf would be unsafe. GCC's interprocedural
register analysis lets the accepted callers rely on more preserved registers
than the standard ABI alone requires. The R3 leaf clobbers additional registers.
Instead, the exact R3 lookup algorithm was recompiled with GCC 13.2, reserving
`a3,a6,a7,t0–t6`. Its 242-byte result writes only permitted caller registers
and saves/restores `s0–s6` and its 32-byte stack frame. Every branch is internal;
there are no external references, calls or floating-point register writes.
Independent source/disassembly review found no blockers.

This is the **R3 algorithm under the accepted register contract**, not the exact
rejected 198-byte donor. Its register allocation, prologue and internal branches
therefore differ from R3. The experiment isolates surrounding layout, but does
not isolate an exact instruction, cache-conflict or stall-cycle attribution.

## Interpretation

Earlier unchanged-ELF profiles showed Moss frequently reaching a successful
inherited-field lookup, while Trailhead exited before that lookup. The isolated
result agrees with this workload difference: Moss benefits; Trailhead changes
very little. Those historical counts are not cycle shares for this build.

The full R3 rebuild's multi-percent regressions are not reproduced by changing
only the helper under the accepted caller contract. This supports collateral
compiler/code-generation/layout changes as a substantial contributor to the
trade-off. It does not prove that cache conflicts alone caused the regressions,
or assign a numerical share to layout versus register allocation. The paired
results cannot simply be subtracted to obtain that attribution.

A source build still needs to deliver the improvement without regressing either
game. The fixed-layout image is diagnostic only; no package was built from it.
With only a sub-percent isolated opportunity and prior source variants failing
the two-game gate, further lookup tuning is parked.

## Verification and retained evidence

Both scenes pass two QEMU runs with baseline output rows and byte-identical
warm checkpoints outside the replacement slot. Both warmup stacks also match;
RTL nevertheless uses the original accepted stack. Fresh identity-copy RTL
controls reproduce every baseline frame's cycle count exactly. Patched quiet
and scanout replay pass output and SDRAM/read/write oracles. Deliberately bad
output oracles fail as expected in both scenes.

Private `experiments/pico8-sources/env-layout-control-20261016-r1` retains the
minimal helper, compiler command/log, audited disassembly, independent derived
images with parent provenance, repeated captures, all controls and results.
`run-diagnostic.py` constructs the copies; `export.py` independently revalidates
outside-slot equality, parent hashes, unchanged input files, QEMU checkpoints,
identity cycles and output/log hashes before exporting two CSV rows.

The evidence manifest SHA-256 is
`88c0600ec416eff79e3e76b69a1d2492be4917d9813524ece4333c7ab6854e58`.
The frozen 1,631-input inventory and os20 platform hashes pass verification.
