# Explicit callback payload/tag — os20, 2026-10-19

**The explicit callback ABI avoids the identified compiler obstacle, but still
fails the Moss no-regression gate.** Celeste's full grapple throw is 14.985%
cheaper quiet and 14.411% cheaper with scanout. Moss steady remains 1.063% /
1.058% more expensive than the accepted audio/palette baseline. Keep this source
isolated; no Pocket package was made.

This implements the next experiment identified by the
[stable-image controls and compiler diagnostics](MOSS-STABLE-IMAGE-OS20.md).
Those controls already proved that the guard can improve Celeste without
changing Moss cycles when the complete original image is preserved. The source
baseline remains `db6bced088a69c82c2be0256947e0a5d2794afd2`; this candidate is
signed revision `1e459bf`. Cart bytes, routes, fixed PCM and final Lua seed
`0x5eed1234` are unchanged. All timings below are simulated os20 at 90 MHz,
not physical Pocket FPS.

## Results

Mean runtime cost in milliseconds, including fixed PCM; lower is better.

| Scene and frames | Baseline quiet | Scalar quiet | Change | Scanout change |
| --- | ---: | ---: | ---: | ---: |
| Moss steady, 180–191 | 48.686 | 49.203 | +1.063% | +1.058% |
| Celeste full throw, 305–306 | 94.453 | 80.299 | -14.985% | -14.411% |
| Celeste whole grapple, 304–308 | 68.637 | 62.279 | -9.263% | -8.790% |

The prior callback-copy source trial regressed Moss by 2.247% / 2.130% and
improved Celeste's full throw by 13.505% / 12.961%. Explicit parameters reduce
that Moss loss while improving Celeste further. They do not eliminate the
remaining loss. The [validated CSV](SCALAR-CALLBACK-OS20.csv) records all six
scene/traffic comparisons, individual frame changes and maximum frame costs.
Additional scene runs were not started after the Moss steady gate failed.
These windows do not establish whole-game performance.

## Source change and generated code

The original internal `callTM` took a pointer to a callback `TValue`. GCC
scalarized it in baseline, but the guarded version lost that optimization.
Copying the callback before the guard removed actual reloads but made early
scalar replacement emit a memory view that IPA-SRA rejected.

The new static signature takes the whole `Value` payload and integer tag
explicitly. All five callers change together: table lookup, table assignment,
binary metamethods, equality and length. The callee reconstructs a local
`TValue`, checks liveness, and retains the existing tag-checked guard and normal
fallback. No pointer/integer cast or unconditional inactive union-field read is
introduced. The guard remains in the existing non-LTO helper; fallback roots
the callback and arguments on the Lua stack before calling Lua.

Independent RV32 assembly review verifies `a1=payload`, `a2=tag`, `a3=p1`,
`a4=p2`, `a5=p3`, `a6=hasres`: the original seven-word convention including `L`.
This no longer relies on GCC rediscovering how to split a callback pointer.

The complete `luaV_gettable` instruction sequence matches baseline after masking
only ten verified relocation immediates. Registers, instruction widths, order,
internal branches and scheduling match: 612 bytes, 218 static instructions,
80-byte frame, 68 loads and 23 stores. Restoring size alone was not the check.

The rest of the image is still different. `callTM` grows from 168 to 238 bytes,
its frame grows from 16 to 48 bytes, it saves two additional registers, and it
spills `p2` around the guard. `luaV_execute` shrinks from 10,724 to 10,528 bytes
and 3,479 to 3,417 static instructions; its frame remains 112 bytes, but the base
register changes from `s10` to `s11`, and its body differs beyond relocation.
Static instruction counts do not measure dynamic work or stalled cycles.

This separates two conclusions: the parameter handling problem is avoided, while
baseline interpreter code and placement are not restored. The smaller
Moss regression is evidence that this build is closer to the goal; it does not
prove that one register assignment or cache conflict explains the remainder.
The next useful isolation target is the interpreter's changed code generation,
rather than more changes to the now-matching lookup body.

## Verification

Core, runtime and delegate tests pass. New real-Lua tests exercise all five
internal callback callers with both light-C functions and captured C closures,
including no-result assignment. Callable-table `__add`, `__eq` and `__len`
metamethods and invalid numeric-callback errors are covered. Existing Lua,
mutation, false, aliasing, GC guard, hook rejection and yielding fallback
contracts also pass.

Review caught an assertion-only liveness-check argument error before target
builds. Assertion-enabled compilation reproduces that failure and passes after
using `G(L)`. A numeric-error canary initially used an unavailable string method;
it was corrected to inspect the actual error through the C API. Both failures
and subsequent passing logs are retained.

All 18 dependency patches reapply to pristine pinned z8lua and reproduce all
62 prepared C/header files. Final-source error text and supported hook counts
match baseline. Six cross-version synthetic save/load outputs are byte-identical
for pixels, palettes and PCM. The inherited baseline line-hook SIGBUS is
excluded from that hook matrix; line-hook shortcut rejection is unit-tested.
The optional native local-cart acceptance test skips for an absent cart;
supplied-cart checks below run separately.

Both benchmark cases pass repeated native and QEMU output, quiet and scanout
RTL, corrupted-pixel negative controls and memory oracles. Native raw indexed
pixels, palettes, PCM bytes and pair counts match baseline over all 400 grapple
and 600 Moss frames. Target QEMU/RTL checks compare channel hashes and pair
counts in the measured windows; they are not target raw-channel byte proof.
Seed and `PICOCPU 90000000` are checked explicitly. The performance acceptance
script fails on Moss both before and after this implementation, as intended;
correctness passing is not performance acceptance.

A clean signed-source offline production ELF builds with prepared dependencies.
Its `.app_fasttext` occupies `0x375a` bytes, leaving 166 bytes of the 14 KiB BRAM
region; `.p8p_vm_cold` is `0x432` bytes. The augmenting linker fragment retains
its previously documented region warnings. This build check does not establish
device performance or production/harness machine-code equivalence.

Private evidence root: `experiments/pico8-sources/moss-scalar-abi-20261019-r1/`.
`benchmark.py`, `codegen.py`, `accept.py`, `report.py`, `discovery/audit.json`,
`compatibility/`, `production-scalar-boundary/` and the native/negative logs
retain reproduction and provenance. `report.py` revalidates case inventories,
UART cycles, raw comparisons, seed/clock, assembly evidence and build/state hashes
before generating the CSV. The source worktree is the existing private
`palette-leaf-20261017-r1/boundary` checkout. The active port, original SDK/OS,
SD card and previous cases were untouched. No push, PR update or deployment was
performed.
