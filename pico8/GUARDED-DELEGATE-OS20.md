# Guarded inheritance shortcut — os20, 2026-10-18

The guarded VM shortcut materially reduces Celeste 2 grapple work, but **neither
candidate passes the no-regression gate**. The initial candidate reduces sampled
full-throw cost by 20.23%, while increasing Moss Moss scene means by 0.15–0.35%
and Celeste's second intro scene by 0.53–0.74%. A callback-isolation mitigation
removes a confirmed register spill, preserves an 18.7–18.8% grapple reduction and
fixes the intro mean, but leaves Moss 0.53–0.68% slower. Both remain isolated
experiments; this report does not recommend shipping either unchanged.

This implements the bounded experiment proposed in
[the grapple cost investigation](GRAPPLE-COSTS-OS20.md), following the
[physical stall attribution](POCKET-GRAPPLE-RESULTS-20261018.md) and
[controlled grapple route](POCKET-GRAPPLE-CONTROLLED.md). It uses PR #14's
accepted audio/palette source as its baseline. Cart algorithms are unchanged.

## Measured results

Mean runtime cost in milliseconds at simulated os20/90 MHz; lower is better.
All cases include fixed PCM generation. The percentages describe runtime cost,
not physical Pocket FPS. The final two columns compare the isolated-handler
candidate to the same baseline under quiet and diagnostic scanout traffic.

| Scene | Baseline quiet | Initial shortcut quiet | Isolated handler quiet | Isolated change, quiet | Isolated change, scanout |
| --- | ---: | ---: | ---: | ---: | ---: |
| Celeste full grapple throw, frames 305–306 | 94.453 | 75.341 | 76.682 | −18.815% | −18.703% |
| Celeste whole grapple window, 304–308 | 68.637 | 59.449 | 60.115 | −12.416% | −12.320% |
| Celeste Trailhead, 100–111 | 42.929 | 41.679 | 41.661 | −2.953% | −2.874% |
| Celeste second intro scene, 100–111 | 25.740 | 25.876 | 25.713 | −0.106% | −0.001% |
| Moss steady, 180–191 | 48.686 | 48.851 | 48.943 | +0.529% | +0.629% |
| Moss allocation/GC window, 234–245 | 49.041 | 49.133 | 49.361 | +0.652% | +0.683% |

The [validated CSV](GUARDED-DELEGATE-OS20.csv) contains both candidates, both
traffic modes, exact source revisions, executable hashes and private case paths.
These are selected deterministic windows, not a guarantee about every frame or
all gameplay. Even the improved grapple window contains individual non-throw
frames whose cost increases slightly. No statistical-noise allowance was used to
hide the small regressions: the simulator measures deterministic cycle counts.

## Shortcut and compatibility guards

The VM recognizes exactly the warmed Lua delegate
`function(self,key) return self.<constant field>[key] end`: two parameters,
zero upvalues, three stack slots and the precise four-instruction body.
It reads the current forwarding table and requested value on every access;
there is no cached final property value or new Proto/serialization field.

Only successful short-string reads through up to four exact delegate hops can
skip Lua setup, dispatch and return. False is a successful result. Missing
values, non-table forwarding fields, arbitrary callbacks, cold prototypes,
uncertain chains and hooks other than count hooks use the ordinary interpreter.
GC debt, possible stack growth, recursion-limit proximity or missing CallInfo
records also force fallback. The accepted body has no count-hook servicepoints.

Independent review caught the CallInfo allocation condition during development:
value-stack capacity alone does not prevent a new call-frame allocation. A fresh
coroutine with a warmed delegate and no next CallInfo reproduced the unsafe
acceptance; the added guard makes that case fall back and preserves allocator
failure behavior. This was fixed before target benchmarking.

Focused contracts exercise live value/base mutation, false/nil, own-property
shadowing, two/four/five-hop chains, missing CallInfo, stack/GC/recursion limits,
hooks, unsupported bodies, non-table bases, observable and yielding callbacks,
and cycles. Core, runtime and delegate tests pass for both timed candidates.
A separate fixture preserves exact error text/lines and call/return/count hook
counts. Synthetic runtime save states load in both directions between baseline
and each candidate with identical subsequent pixels, palette and PCM.

End-to-end line-hook equality is not claimed: the baseline fixture crashes with
SIGBUS when enabling line hooks. Its reproduction is retained separately; the
new helper's line-hook rejection is covered by the focused contract tests. The
runtime test suite's optional local-cart Celeste acceptance test is skipped
because that assets directory is empty; the supplied real-cart comparisons below
run independently and pass.

## Why Moss loses despite no inheritance callbacks

A separate native counter diagnostic records **zero function-valued `__index`
dispatches in Moss across all 600 frames**. The helper therefore cannot be costing
Moss through repeated failed speculation. A callsite prototype prefilter was
considered and discarded when this evidence arrived.

RV32 disassembly exposes a concrete compiler effect in the initial candidate's
ordinary table-hit path. The key changes from a callee-saved register to a stack
slot, replacing two register moves with an extra store and reload on every such
lookup, including reads that never use metamethods:

| Ordinary table-hit path | Baseline | Initial | Isolated handler |
| --- | ---: | ---: | ---: |
| Instructions | 56 | 56 | 56 |
| Loads | 19 | 20 | 19 |
| Stores | 16 | 17 | 16 |
| Register moves | 6 | 4 | 6 |
| Stack frame, bytes | 80 | 80 | 80 |

The mitigation moves speculation and callback handling into a separate noinline
function, restoring the register-held key. It also adds another call boundary
on Celeste's callback path, consistent with the smaller grapple benefit.
Restoring these counts does not restore the old executable layout: instruction
addresses and surrounding placement change. The remaining Moss cost is
consistent with layout/cache effects, but this experiment does not isolate the
precise residual cause. Equal instruction counts alone do not prove equal cycles.

The Celeste diagnostic confirms that the shortcut targets real work: frames
304–308 make 10,943 helper attempts and 7,847 successful shortcuts. All of those
callbacks have the exact delegate shape from cart line 676. Per-frame attempts /
successes are 1198/542, 3431/2779, 3431/2779, 2050/1398 and 833/349. Diagnostic
counters are absent from every timed executable. Their outputs independently
match the uninstrumented game output.

## Verification, provenance and limits

- Baseline source: `db6bced088a69c82c2be0256947e0a5d2794afd2`.
  Initial signed candidate: `1466107`; isolated-handler signed candidate:
  `ea36491`. Active port checkout and PR #14 remain unchanged.
- Five fresh baseline cases, five initial cases and five isolated-handler cases
  use the original carts, production builtin policy, non-LTO palette object and
  final hash seed `0x5eed1234`. Moving grapple uses the independent 400-mask
  route. Other scenes run 600 native frames with their existing setup/input.
- Each case passes two native runs, two RV32 QEMU captures, exact native/capture
  frame agreement, quiet RTL, diagnostic scanout RTL and the intentional negative
  memory oracle. Checkpoint/stack hashes compare repetitions of the same binary;
  they are not used as cross-build equality tests.
- Independent raw collectors compare every pixel, palette byte and PCM byte
  across baseline/candidate, with frame counts and audio-pair counts equal.
  Altered-byte controls are rejected. All five scenes pass for both candidates.
- Fresh application of all eighteen registered patches to pinned z8lua
  `e6928578d46b61fd5ea30cfcf547e855a30a0553` reproduces all 62 prepared C/header
  files for each candidate. Frozen input and os20 platform hash checks pass.
- Offline production ELF builds pass. Both retain `.app_fasttext` at
  14,322 / 14,336 bytes, leaving 14 bytes; the new handlers reside in SDRAM.
  Initial ELF SHA-256:
  `50b98747e0a502f2325c8ff15fcf24b5d06d89222512e986c28a2427f3180db0`.
  Isolated-handler ELF SHA-256:
  `a7d126784c80650e0b33172a3c4bab721bcb19e8b5de091a726c7b3480ba7324`.

Private scripts, raw channels, review canary, disassembly, source origins and
complete replay controls remain under
`experiments/pico8-sources/guarded-delegate-20261018-r1/`; timing cases use
`experiments/pico8/guarded-delegate-{scene}-{variant}-20261018-{r1,r2}/`.
The initial collector/parser mismatch was corrected before target replay;
original failure logs are retained. No failed performance case was overwritten.

The os20 model is pinned to OS `8318f25`; exact shipped-bitstream source
equivalence remains unproven. Fixed audio output excludes live catch-up,
presentation, SD/OS scheduling and adaptive drawing, so physical FPS or the
remaining Pocket stall duration cannot be inferred from these timings.

The useful next experiment is a matched-placement control that separates
lookup code generation from executable layout, followed by another Moss gate.
The large Celeste win justifies continuing that investigation; the current
results do not justify declaring either candidate regression-free or packaging
one as an accepted optimization.
