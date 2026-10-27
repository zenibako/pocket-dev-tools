# Celeste 2 grapple inherited-field diagnostics — 2026-10-18

Repeated inherited-property reads are a major cause of the grapple throw cost.
A matched-code diagnostic that resolves just `grapple_mode` onto the scene's
objects before execution reduces the two sampled full-throw frames from
**91.42 to 70.36 ms (23.03%)** in quiet os20 replay. Scanout gives the same
23.03% reduction. These are simulated runtime costs at 90 MHz, including fixed
PCM output; they are not physical Pocket FPS or a shippable optimization.

This follows the [Pocket stall attribution](POCKET-GRAPPLE-RESULTS-20261018.md)
and uses the exact [moving grapple route](POCKET-GRAPPLE-CONTROLLED.md).
The earlier [environment lookup experiments](ENV-LOOKUP-OS20.md) optimized
table-valued `_ENV` inheritance. Celeste's object properties use a Lua
function-valued `__index`, so those shortcuts do not cover this hotspot.

## What executes during a throw

Disposable native counters run the original 100-warmup/300-measured route with
ordinary API profiling and detailed timers disabled. Counters cover iterator
creation/advancement, function-valued index dispatch, Lua function calls and
VM dispatches by function. They do not time each lookup. Call counts cover
both ordinary `luaD_precall` and the VM's inline Lua-call path.

All fourteen full-throw frames make eighteen `grapple_check` calls and eighteen
complete scans of the 79-object scene: **1,422 objects inspected and 1,440
iterator calls**, including loop termination. Those are route frames
116–119, 153–154, 205–206, 255–256, 305–306 and 355–356, matching the fourteen
full-throw rows retained in each physical report after its 100-frame offset.

The scans cause 3,942–3,978 Lua inheritance callbacks per full-throw frame.
For representative route frame 305 (Pocket capture index 205), the 3,978
callbacks inside `grapple_check` break down as follows:

| Inherited property | Lua callbacks |
| --- | ---: |
| `grapple_mode` | 2,466 |
| `contains` method | 756 |
| `hit_x` | 738 |
| `hit_w` | 18 |

The cart's tiny delegation function runs three VM dispatches per call.
`grapple_check` and its descendants account for 21,366 of the frame's 47,788
dispatches (44.71%); inherited lookup bodies account for 11,934 of those
21,366 (55.86%). Function setup/return, table helpers, C iterators and native
execution costs are additional work. These proportions are **not cycle shares**.
Fused companion jumps and the `TFORLOOP` consumed by `TFORCALL` are not counted
as separate dispatches, so these counters are not a complete bytecode-instruction
count either. Instrumented native elapsed times are excluded from conclusions.

The counts refine the original hypothesis: the repeated mode test is expensive,
and eligible objects also repeatedly inherit their containment method and bounds.
The scene has 21 eligible objects, producing 378 `contains` calls in frame 305.

## Causal diagnostics and their tradeoffs

All target cases start from PR #14's optimization-only source `db6bced`, with
final hash seed `0x5eed1234`, the independent 400-mask route, production runtime
builtin policy and non-LTO palette object. The replay window is absolute frames
304–308: enter throw, two full throws, attachment and attached movement. Timed
replay contains no new counters, Lua hooks or per-lookup timers.

The first comparison uses separately rebuilt diagnostic executables:

| Diagnostic substitution | Full-throw cost, quiet | Change | Change with scanout |
| --- | ---: | ---: | ---: |
| Original cart | 94.453 ms | reference | reference |
| Numeric iteration in `grapple_check` | 90.776 ms | −3.89% | −4.50% |
| Equivalent C callback for the inheritance function | 95.440 ms | +1.04% | +0.98% |
| Resolve `grapple_mode` onto each object before the route | 71.265 ms | −24.55% | −24.60% |

Numeric iteration removes the grapple's 1,440 C iterator calls, but it leaves
all inherited reads intact and increases VM dispatches in frame 305 from
47,788 to 50,650. Its target result is better despite doing more Lua work.
The rewrite is valid for this non-mutating loop; it does not replace `all`'s
general deletion/iteration semantics. Neither these rebuilds nor a generic
`all` replacement establish an acceptable emulator optimization.

The C callback preserves live `self.base[key]` evaluation but still performs
the table operations through public Lua APIs and enters a callback for every
miss. It removes the inheritance function's Lua execution, reducing frame 305
to 31,045 dispatches, yet target time is slightly worse. Removing Lua
instructions alone is insufficient. This experiment does not independently
separate C API overhead, callback machinery and changed code placement; it is
not evidence that a lower-level guarded lookup shortcut would be unhelpful.

Resolving `grapple_mode` ahead of time removes all 2,472 mode-related callbacks
in frame 305 (2,466 inside collision checks, six elsewhere), reducing total
dispatches to 40,372. It is a useful diagnostic, but changes inheritance
semantics: a later class/base change would no longer update that object's
resolved value. No cartridge rewrite or persistent property cache is proposed.

## Code placement control

Because earlier iterator/lookup experiments showed substantial compiler effects,
two further builds retain both paths behind a volatile setup selector.
Every symbol address and every loadable section's address/size match. All code,
BRAM and read-only data are byte-identical. The **only different initialized
loadable byte** is the selector at `0x10456b88`, choosing whether the field
resolution happens before warmup. Debug information is not part of this claim.

| Matched-code setup | Full-throw cost, quiet | Full-throw cost, scanout |
| --- | ---: | ---: |
| Normal inheritance | 91.423 ms | 91.595 ms |
| Resolved `grapple_mode` | 70.364 ms | 70.499 ms |
| Cost reduction | **23.035%** | **23.032%** |

The five-frame mean falls 14.81% quiet and 14.79% with scanout. The neighboring
non-throw frames 304/308 change by −0.006%/+0.060% quiet and +0.005%/+0.101%
with scanout. This confines the substantial gain to the throw work while
controlling program code/layout. Lua table/heap state changes are intentional
and remain part of the diagnostic; this is not a pure timing measurement of
one helper. Absolute times differ from the first table because the common
selector executable has a different layout; compare within each study.

The [validated CSV](GRAPPLE-COSTS-OS20.csv) retains both studies, exact case and
ELF identities, quiet/scanout full-throw means and five-frame means.

## Practical next experiment

Test a **guarded shortcut for simple Lua inheritance forwarding**, rather than
replacing callbacks with another general API wrapper or caching final property
values onto instances. It would recognize the exact pure delegate bytecode,
read current `base`/key/table values on every access, and fall back to normal Lua
execution for unsupported shapes, hooks, side effects, errors or uncertain
chains. Mutation, false/nil values, metatable replacement and error lines need
explicit compatibility checks. No such runtime implementation was made here.

The repeated scans remain substantial work even if inheritance gets cheaper.
Spatial filtering or an eligible-object list would reduce the cart's algorithmic
work, but those are cart changes with mutation/order/compatibility concerns.
They are not general emulator fixes. Any shared VM change must still pass Moss
Moss and Celeste tests, production BRAM fit and matched output comparisons.
Only fourteen bytes remain in the current production BRAM budget.

The [physical captures](POCKET-GRAPPLE-RESULTS-20261018.md) also show audio
catch-up amplifying long frames, while GC is tiny. These experiments use 1,600
fixed stereo pairs per frame and exclude live audio scheduling, presentation,
OS/SD and adaptive drawing. They cannot quantify a Pocket FPS improvement or
fully eliminate grappling stalls. No additional audio/GC change is justified
by this study.

## Verification and retained evidence

Six complete os20 cases pass repeated 400-frame native output, repeated RV32
checkpoints with native equality, five-frame quiet/scanout output and memory
oracles, and deliberately corrupted-pixel rejection. All six have identical
per-frame native pixels/palette/PCM hashes over the entire 400-frame route.
The original route's final scene and aggregate channel hashes are retained.

Twenty native counter/control/diagnostic runs independently compare all 300
measured frames byte-for-byte for pixels, palettes and fixed PCM. Their raw
channels also reproduce the target runner's per-frame protocol. Deliberate
pixel, palette and PCM corruption is rejected. Repeated counter runs agree
exactly after excluding instrumented elapsed times. A preliminary partial
table-metatable substitution is retained among those output controls but is
excluded from timing conclusions.

The exporter verifies case/binary inventories, original source hashes, actual
seed and MMIO clock, emitted output, all six result matrices, the matched-code
section/symbol comparison and independent raw channels before writing the CSV.
The frozen 1,631 input files and os20 platform remain unchanged. An initial
Docker socket denial is preserved in the first baseline case; it is excluded.

Private scripts, generated probes, versioned probe sources, raw output,
all original failures and `verification.json` live under
`experiments/pico8-sources/grapple-costs-20261018-r1/`. The verification manifest
SHA-256 is `1fbd0d02d17d4e7d9c53e75166263691c9c84664a4d6bd2d32fa446b1374ac0d`.
Completed replay cases remain under `experiments/pico8/grapple-costs-*`.
No production source, current PR, original SDK/OS, SD card or remote was changed.
