# Warm immediate-return Lua calls — 2026-10-16

Neither tested shortcut passes the two-game performance gate. Both preserve
sampled output but regress Moss Moss and Celeste 2 Trailhead. The accepted
rebased audio source at `9f4cd16` remains unchanged. These are simulated
os20/90 MHz runtime frame costs, not physical Pocket FPS.

| Timed variant | Moss steady cost | Trailhead cost | Decision |
|---|---:|---:|---|
| Shared RETURN, `0484d2b` | +0.2748% | +1.1644% | Reject |
| Discarded results first, `1064a35` | +2.6402% | +0.0752% | Reject |

Baseline costs are 48.287563 ms for Moss and 42.322168 ms for Trailhead.
Scanout also regresses: +0.1526% / +1.1243% for the first variant and
+2.4875% / +0.0540% for the retry, respectively. The [validated CSV](EMPTY-LUA-CALL-OS20.csv)
contains exact means, quiet/scanout changes, source/ELF hashes, BRAM sizes
and case identities. Each variant stopped after these two scenes. Moss GC,
intro 1, intro 2 and title cases were created but not run; there are no new
measurements for those windows.

## Opportunity and call census

The [Moss profile](MOSS-OS20.md) identified 550 actors with empty update
functions. The [existing call optimizations](ITERATOR-CAUSES.md) already
inline non-vararg Lua frame setup and return, so changing only generic
`luaD_precall` would miss the relevant inline calls. The new experiment
examines `OP_CALL` after its existing inline frame setup and collector check.

A private native census of the accepted audio cases counts eligible calls for
the first timed variant, without installing CALL hooks or changing target ELFs:

| Selected window | Eligible calls in 12 frames | Calls per frame |
|---|---:|---:|
| Moss 180–191 | 6,612 | 551 |
| Trailhead 100–111 | 648 | 54 |

All 600 pixel/palette/PCM/input/FPS rows remain identical in both diagnostic
runs. Before-dispatch and post-GC populations agree in the selected windows.
The census establishes coverage, not instruction cost, target-cycle savings,
or the identity of every actor callback. Native source instrumentation can
change layout. Three independently retained censuses characterize the guard as it evolves;
their selected hit counts agree. The final retry's discarded-result intersection
was not separately censused.

## Implementation and BRAM constraints

The final shortcut retains normal frame creation, stack-capacity checks,
argument completion, roots and `luaC_checkGC`. It requires an initialized
`Proto.icache`, so first-use cache allocation still follows the original path.
The first instruction must be exactly `RETURN A=0, B=1, C=0`: later bytecode
cannot execute. It rechecks CALL/RET/LINE hook masks after GC, then reloads
callee closure/base and enters the existing RETURN handler before its local
initializations. That handler retains result padding, upvalue closing and
parent-frame restoration. OP_CALL servicepoints remain; RETURN has no count
servicepoint. Varargs, tail calls and other calls retain their existing paths.
The final retry checks `nresults == 0` before inspecting the prototype.

Two earlier source shapes were rejected before timing. `fc6fb7f` duplicated
a narrow zero-result unwind and overflowed production BRAM by 206 bytes.
`eb4c8e1` reused RETURN but required exactly one bytecode instruction; it
overflowed by 6 bytes. Removing that unnecessary size restriction produced
`0484d2b`, which uses 14,326 of 14,336 bytes. The zero-result retry uses
14,334 bytes, leaving only 2 bytes. The BRAM limit was never increased.

The guard retry was evidence-driven: only 2,376 of Trailhead's 7,092 Lua calls
across the selected window discard results. Rejecting other calls before the
prototype checks reduces exposure to the new condition. It improves that
variant's Trailhead result relative to the first attempt, but worsens Moss
substantially and still fails the shared-runtime acceptance rule.

GCC code shape changes beyond the shortcut. In benchmark ELFs the VM shrinks
26 bytes in the first attempt and 30 in the retry; in production it grows
148 and 156 bytes, respectively. Recorded moved-symbol counts are 785 then
205 in Moss and 42 in Trailhead for both attempts. BRAM contents change.
Fewer symbols moving, smaller VM code, and a high hit count therefore do not
establish a whole-frame improvement. These experiments do not isolate exact
cycle shares for guard overhead, branch encodings, code placement or caches.
No new unchanged-ELF instruction or fixed-layout cycle attribution was made.
Further tuning of this shortcut is parked after the bounded retry.

## Verification and limitations

All four completed A/B results pass two native 600-frame runs, repeated RV32
captures with native equality, quiet and scanout replay, memory oracles and
corrupted-output negative controls. Raw pixels, palettes and PCM match baseline
byte for byte across 600 frames in both games for both variants. Compiler,
flags, link command, routes, carts, fixed seed and os20 platform match.
Snapshot inventories differ only in prepared `lvm.c` plus the new dependency
patch; platform and frozen input hashes remain intact.

New fixtures cover ignored arguments and parent locals, fixed/multiple
results, explicit returns, parameter/vararg fallbacks, nonempty functions,
stack growth, GC/upvalues, errors and resumed coroutines. Native C hooks check
CALL/RET, a separately warmed RET-only path, and count delivery. Fixtures pass
on unchanged baseline and candidate VMs; the final native suite and Celeste's
600-frame/save-state replay pass. Return-hook and invalid-return-guard mutants
fail their intended assertions. The first timed variant passes the complete
suite under ASan/UBSan; the final timed retry passes the focused fixtures under
both sanitizers. Independent source and evidence reviews found no semantic
blocker.

An exploratory Lua-written debug-hook fixture crashes the unchanged baseline;
ASan records a read before a bytecode allocation during `luaD_precall`. That
failure is retained and excluded from passing evidence. Full Lua debug-hook
and LINE-hook behavior is not claimed verified. No related runtime fix was
mixed into this optimization; its hook fallback checks remain intact.

The new patch applies after the existing 17 patches to pinned Z8Lua `e6928578`.
Fresh application reproduces all 62 prepared C/header files for the first
timed variant; the retry patch reproduces its prepared VM over the same prior
17 patches. Dependency pins, original SDK/OS, active port and SD card were not
changed. Both fitting production ELFs are retained. An independent private
rebuild reproduces the first timed production ELF byte for byte.

## Retained evidence

`experiments/pico8-sources/empty-lua-call-20261016-r1` contains the signed source
worktree, overflow attempts, tests/mutants, sanitizer logs, first timed cases,
production artifacts and patch validation. `empty-lua-call-20261016-r2` contains
the retry launcher/results and final validating `export.py`. The exporter
freshly checks case/binary inventories, prepared inputs, replay rows/cycles and
log hashes, negative-log hashes, raw channels, source scope and matched build
settings before writing four CSV rows.

`empty-call-census-20261016-r1` through `-r3` retain private probes and per-frame
population counts. Final source `0486362` adds only the passing discarded
explicit-return fixture over measured `1064a35`; runtime/build source is
unchanged. Commits are GPG signed. No optimization was promoted, no package
was made, and no remote was changed.

Final evidence manifest SHA-256:
`280276e11d8b5e10e4c6ad698ca56de47c8cda2038b32e1555477bc5d3a6c269`.
