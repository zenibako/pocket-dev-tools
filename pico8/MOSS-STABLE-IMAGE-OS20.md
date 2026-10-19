# Moss stable-image controls — os20, 2026-10-19

Preserving the entire baseline image removes the measured Moss regression:
**both Moss windows reproduce every baseline frame cycle exactly**, with and
without scanout traffic. The same guarded callback makes Celeste's full grapple
throw 14.596% cheaper. This establishes that the guarded algorithm can coexist
with unchanged Moss performance. It does not yet provide a source build ready
to ship: the ordinary compiler builds still change surrounding VM code.

This follows the [cold-helper placement experiment](GUARDED-COLD-PLACEMENT-OS20.md)
and [Moss isolation](GUARDED-MOSS-ISOLATION-OS20.md). Baseline remains PR #14's
audio/palette source, revision `db6bced088a69c82c2be0256947e0a5d2794afd2`.
Cart bytes, input routes, fixed PCM and final seed `0x5eed1234` are unchanged.
All numbers are simulated os20 at 90 MHz, not physical Pocket FPS.

## Whole-image control

A derived ELF retains every original loaded code/data byte except one four-byte
callback call. The call targets the existing 920-byte non-LTO guarded thunk,
relocated into unused memory before the original aligned heap. Three nil-object
address pairs and two Lua-call pairs inside that thunk are relocated. Original
BRAM firmware, function addresses, data placement and heap start `0x10459000`
remain unchanged. The baseline ELF itself is never modified.

| Scene, frames | Baseline ms | Guard ms | Quiet change | Scanout change |
| --- | ---: | ---: | ---: | ---: |
| Celeste full throw, 305–306 | 94.453 | 80.666 | -14.596% | -14.286% |
| Celeste whole grapple, 304–308 | 68.637 | 62.074 | -9.562% | -9.335% |
| Celeste Trailhead, 100–111 | 42.929 | 41.792 | -2.648% | -2.479% |
| Celeste intro 2, 100–111 | 25.740 | 25.651 | -0.348% | -0.315% |
| Moss steady, 180–191 | 48.686 | 48.686 | 0.000% | 0.000% |
| Moss GC window, 234–245 | 49.041 | 49.041 | 0.000% | 0.000% |

Moss's warm SDRAM state and stack are byte-identical to baseline apart from the
declared code edits. This is stronger than matching output alone. It excludes
additional guard work as the explanation for the earlier Moss slowdown in these
windows. Together with the prior instruction and bus profiles, the evidence
points to surrounding compiler output and placement. It does not identify a
single cache conflict or attribute every stalled cycle to one hardware unit.

The ELF extension preserves the original page tail. An initial control exposed
a QEMU detail: its page-rounded file mapping also maps bytes following the
original load segment. Extending only through the helper changed those bytes
and failed the strict checkpoint comparison. The corrected control preserves
them and extends to the original heap boundary. The failed attempt is retained.

## Moss-specific experiments

The baseline short-string miss helper executes 24,507 times in the measured
steady window. Its unchanged-ELF profile shows 24,320 no-match returns (99.24%),
27,954 tag probes, 13,907 key probes, 187 matching keys and 149 non-nil values.
That makes its miss path a plausible target, but the measured variants fail the
no-regression gate:

| Exact-image change, Moss steady | Quiet cost change | Scanout cost change |
| --- | ---: | ---: |
| Move unchanged 62-byte helper into spare harness BRAM | +0.895% | +0.896% |
| Same helper at a 64-byte boundary, preserve padding | +0.670% | +0.790% |
| Check pointer identity before key tag | -0.054% | +0.040% |
| Skip bucket hash arithmetic for one-bucket tables | +0.171% | +0.238% |

BRAM placement is not automatically faster. The aligned zero-padding control
and the version preserving all unused BRAM NOPs produce identical cycles; padding
does not explain that result. The production baseline has only 14 spare BRAM
bytes, so the 62-byte relocation would also require eviction. No eviction was
implemented after this timing failure.

Key-first comparison retains both checks and is only a machine-code diagnostic.
A portable source rewrite must account for empty table nodes whose payload is
uninitialized and for inactive union members. The pinned compiler also lowers
unqualified byte comparisons poorly; assuming alignment is not a correctness
solution. This tiny quiet improvement reverses with scanout, so it is rejected.
The bucket shortcut retains tag-first behavior; its reassembled helper also
merges return paths, so its result cannot isolate hash arithmetic alone. It too
is rejected.

## Source refinements

The first normal source trial preserves the original gettable-to-callTM edge
and moves the guard inside callTM. It reduces the earlier roughly 3.1% Moss
loss, but leaves Moss steady **1.835% slower quiet / 1.731% slower scanout**.
Celeste's full throw improves 10.933% / 10.278%. Its signed isolated source is
`1cfdc60c703dfd8c0b90485673103d317ddc589c`.

Assembly reveals a concrete complication: GCC retains the original callback
pointer across the opaque guard, then reloads both callback fields. Baseline
instead uses a scalarized callback ABI. A second trial copies the callback
before the guard and uses a typed Lua-closure entry after an explicit tag check.
This removes the post-guard reads of the caller's callback, verified in assembly.
The allocation-free guard preserves the snapshot; ordinary fallback roots it on
the Lua stack before allocation or callbacks. Independent semantic review found
no rooting, aliasing or allocation blockers.

The snapshot trial, signed source `0087abd`, regresses Moss steady by **2.247%
quiet / 2.130% scanout**. Celeste full throw improves **13.505% / 12.961%**.
Its callback-copy change therefore fails the performance gate despite removing
the specific reload problem. Neither source trial was extended to additional
scenes after the Moss gate failed.

The callback still has the six-argument pointer-based ABI rather than baseline's seven-word
scalar clone. Its stack frame is 32 rather than 16 bytes; gettable is 602 rather
than 612 bytes; the BRAM interpreter is `0x295a` rather than `0x29e4` bytes.
Removing the reload was insufficient to restore baseline compilation. A narrow
pinned-GCC diagnostic build confirms why scalar splitting is lost: baseline
classifies callback parameter `f` as a candidate, while snapshot compilation
rejects it with "reference has nonarg uses" before LTO. The link-time pass inherits
that rejection. This identifies the compiler decision, rather than merely
inferring it from assembly; it does not by itself attribute the Moss timing loss
to one instruction. These source variants remain isolated.

## Verification and retained evidence

The [validated CSV](MOSS-STABLE-IMAGE-OS20.csv) includes per-frame changes, result
paths/hashes, source revisions and ELF hashes for all completed comparisons.
Every exact-image variant passes repeated QEMU captures, full target output
hashes over 400 grapple or 600 other frames, quiet/scanout RTL, corrupted-pixel
negative control and memory oracles. Target raw channel bytes were not collected
for derived ELFs; those checks compare per-frame pixel/palette/PCM hashes and
pair counts against the baseline native trace. They are not raw-byte proof.

Both normal source trials additionally match baseline native raw indexed pixels,
palettes, PCM bytes and pair counts over the full routes. Native core, runtime
and delegate contracts pass. All 18 dependency patches reapply to pristine
pinned z8lua and reproduce all 62 prepared C/header files. The first source
trial also passes error/hook text and six-way cross-version synthetic state
output; that compatibility fixture was not rerun for the snapshot refinement.
The optional native local-cart test skips because its cart is absent; supplied
cart harness checks pass separately. The inherited baseline line-hook SIGBUS
limitation remains unchanged.

Both source trials build an offline production ELF with prepared dependencies.
The snapshot production ELF has `.app_fasttext` size `0x376a` (150 bytes free)
and `.p8p_vm_cold` size `0x432`. This is a build check, not a physical Pocket
performance result. No package, PR update, push or deployment was performed.

Private evidence root: `experiments/pico8-sources/moss-stable-image-20261019-r1/`.
`image.py`, `run-image.py` and `bucket.py` retain exact-image transformations and
controls. `benchmark.py` and `benchmark-snapshot.py` retain source trials.
`report.py` revalidates inventories, replay results, hashes and native raw
comparisons before generating the CSV. `discovery/` contains call-site evidence,
compiler probes and the unchanged-helper profile analysis. Failed setup and
page-tail controls are retained under explicitly named failure directories.
Source work is confined to the existing private boundary worktree; the active
port checkout and baseline source remain untouched.
