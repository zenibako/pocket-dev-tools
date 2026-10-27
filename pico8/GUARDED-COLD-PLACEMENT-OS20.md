# Guarded callback cold placement — os20, 2026-10-18

**Preserving the lookup body and moving the helper do not clear the Moss
no-regression gate.** Celeste grappling and Trailhead improve, but both helper
placements leave Moss about 2.5–3.1% slower. The exact baseline lookup instruction
sequence is preserved in the benchmark ELFs. Placement changes Moss by less than
0.04% between variants; the larger regression survives in the surrounding build.
Keep this experiment isolated.

This tests the bounded follow-up to
[the Moss regression isolation](GUARDED-MOSS-ISOLATION-OS20.md) and
[the guarded inheritance shortcut](GUARDED-DELEGATE-OS20.md), using the same
[controlled Celeste grapple route](POCKET-GRAPPLE-CONTROLLED.md). The accepted
PR #14 audio/palette source remains the baseline. Cart code and routes are
unchanged.

## Results

Mean simulated os20/90 MHz runtime cost in milliseconds, including fixed PCM;
lower is better. Changes are relative to the same baseline, not Pocket FPS.

| Scene and frames | Baseline | Early helper | Change | Late helper | Change |
| --- | ---: | ---: | ---: | ---: | ---: |
| Celeste full throw, 305–306 | 94.453 | 76.949 | -18.532% | 78.527 | -16.861% |
| Celeste whole grapple, 304–308 | 68.637 | 60.117 | -12.413% | 60.902 | -11.269% |
| Celeste Trailhead, 100–111 | 42.929 | 41.023 | -4.440% | 41.977 | -2.217% |
| Celeste intro 2, 100–111 | 25.740 | 25.570 | -0.660% | 25.601 | -0.540% |
| Moss steady, 180–191 | 48.686 | 50.172 | +3.053% | 50.191 | +3.092% |
| Moss GC window, 234–245 | 49.041 | 50.276 | +2.519% | 50.286 | +2.538% |

Diagnostic scanout changes relative to baseline:

| Scene | Early helper | Late helper |
| --- | ---: | ---: |
| Celeste full throw | -18.595% | -16.230% |
| Celeste whole grapple | -12.466% | -10.813% |
| Celeste Trailhead | -4.414% | -2.004% |
| Celeste intro 2 | -0.591% | -0.467% |
| Moss steady | +2.968% | +3.000% |
| Moss GC window | +2.421% | +2.448% |

The [validated CSV](GUARDED-COLD-PLACEMENT-OS20.csv) records all 24 scene/variant/
traffic rows, individual frame changes, exact case paths, source revisions and
ELF/result hashes. These deterministic samples do not establish whole-game
performance. Neither placement is accepted for shipping.

## What was controlled

The successful guard and ordinary callback fallback live in a separate
`src/runtime/vm_delegate.cpp`, compiled with `-fno-lto`. The cold callback accepts
the `Value` payload and tag separately, matching the original RV32 seven-word
`callTM` clone ABI. Only the function-valued `__index` call crosses this boundary;
the other four `callTM` uses remain original. All existing semantic guards remain.

An initial payload-copy implementation failed the assembly gate: byte-wise
copying grew the stack frame from 80 to 96 bytes, and an external `luaH_getstr`
reference prevented its original scalarized ABI. It was corrected before target
timing. Passing `Value` by value removes that copy. A private short-string bucket/
chain probe and metatable check preserve Lua semantics without exposing shared
lookup functions to the non-LTO unit.

In the actual harness ELFs, `luaV_gettable` is **612 bytes in the original
640-byte slot**, with the original 80-byte frame. Every opcode, register,
instruction width, internal branch and schedule matches baseline. Eight external
calls and two string-address references differ only through verified relocation
immediates; the former callback call targets the compatible cold thunk. A
baseline-body transplant reproduces the existing recipient function byte for
byte, so another such timing control would be a no-op. This is verified for both
Moss windows and the late-helper grapple ELF in the retained relocation manifest.

Early placement puts `.p8p_vm_cold` after normal text, before data. Late placement
puts it after frame metadata, inside the gap before the aligned heap. Both use
the byte-identical non-LTO input object (SHA-256
`adf1454f939fd7a0de2b89ed71bb6570257e38c3a7a41eeddd4898abfcd03859`).
The helper section spans 920 bytes. Ordinary text function addresses match between
placements, but linked address references change. Data/BSS move by 928 bytes
between variants, so this comparison includes data placement effects. All keep
heap start `0x10459000`. Relative to baseline, the surrounding compiler output
still differs; this is not an otherwise identical complete-image control.

The fresh empty-helper baseline ELF is byte-identical to the retained baseline
ELF, with exactly the same repeated RTL cycles. This checks that appending the
extra compilation job itself does not account for the regression.

## Why Moss still loses

An unchanged-ELF instruction profile covers runtime-step entry through return in
Moss frames 180–191, excluding standalone PCM, hashing and presentation. It records
31,299,864 baseline instructions versus 31,239,876 for late placement: **59,988
fewer instructions (0.192%)**. Only `luaV_execute` changes, from 15,232,520 to
15,172,532 instructions, with 7,522 entries in both. Every other function's
instruction and entry counts match baseline, including lookup, allocation and GC.
All per-function load/store counts also match. The guard/thunk do not execute in
this measured Moss window. There is no additional measured game work or repeated
failed guard to explain its slower runtime.

The compiler still changes the interpreter outside lookup: its BRAM body shrinks
from `0x29e4` to `0x29b4` bytes, shifting later BRAM code. The complete BRAM image
changes from `0x375e` to `0x3732` bytes. Preserving one hot function does not
preserve all whole-program optimization decisions or surrounding placement.

The previously validated passive os20 bus observer reproduces each original
quiet frame cycle exactly and passes output/memory checks. Between matching
frame timer reads it counts:

| Build | Instruction requests | Data requests |
| --- | ---: | ---: |
| Baseline | 30,171 | 153,316 |
| Early helper | 34,531 | 150,872 |
| Late helper | 34,464 | 151,083 |

Late placement generates **14.23% more instruction requests** despite fewer
executed instructions and identical memory-operation counts. Examples include
`fastchain` (156 → 1,719), a `luaM_realloc_` clone (10 → 1,534), the interpreter
(4,725 → 5,703), and lookup itself (291 → 1,029). This implicates the surrounding
compiler/layout effects and supports investigating frontend behavior. The counts
include speculative/prefetch traffic: they are not demand miss rates, CPI or CPU
stall attribution. They do not quantitatively explain the entire timing loss or
identify one cache conflict or branch predictor effect.

The prior handler experiment regressed Moss by only 0.53–0.65%; this more isolated
source candidate is worse. Moving cold bytes alone is therefore insufficient,
and the amount of fetch traffic alone cannot be treated as a universal timing
predictor. The next meaningful control would preserve interpreter code generation
and surrounding layout as well as lookup, rather than add a Moss/game-specific
runtime switch for a guard Moss never calls.

## Verification and production check

Both placements pass repeated native and QEMU output, quiet and scanout RTL,
corrupted-pixel negative control, and memory oracles in all five scene windows.
Raw indexed pixels, palettes, PCM bytes and pair counts match baseline across
all 400 grapple frames and 600 frames in each other scene. All cases pin the
final Lua seed to `0x5eed1234` (`PICOSEED 1592594996`) and confirm
`PICOCPU 90000000`. Source snapshots and executable inventories validate.

Core/runtime/delegate tests pass, including Lua, light-C and C-closure payloads,
mutation, false/nil, ordinary no-result fallback, 1,024 populated and removed hash
keys, dummy tables and changed metatables after cached misses. The refined build
also preserves exact error text and supported hook counts, and six-way cross-
version synthetic save-state output. The existing baseline line-hook SIGBUS and
optional missing-local-cart acceptance-test skip remain the limitations described
in the prior report; real supplied-cart harness comparisons pass independently.
All 18 patches reapply to pinned z8lua, reproducing 62 prepared C/header files.

A clean signed-source offline production ELF builds and is byte-identical to the
reviewed pre-commit build. Its explicit SDRAM cold section follows BSS and precedes
BRAM load storage. Production BRAM is `0x37f2` of `0x3800` bytes (14 bytes free).
The linker emits forward-region/redeclaration warnings for the augmenting
fragment, but segment mapping is verified. Removing explicit `> SDRAM` wrongly
places cold code in BRAM and overflows it; that failed attempt is preserved.
Unlike the aligned harness build, the production lookup still has register/
scheduling differences from production baseline. No claim of identical device
machine code or physical Pocket performance is made.

## Reproduction and retained evidence

Private experiment root: `experiments/pico8-sources/guarded-cold-20261018-r1/`.
The isolated source worktree is
`experiments/pico8-sources/palette-leaf-20261017-r1/boundary`, signed revision
`f63234f618318acbb146f36399ce1ea551053fb2`; baseline is
`db6bced088a69c82c2be0256947e0a5d2794afd2`.

`benchmark.py` builds fresh explicit-os20 cases; the CSV names every completed
case. The first concurrent grapple launch had a local ZIP creation race before
creating a case; its log is retained, and the early case completed as `r2` using
the existing immutable archive. `report.py` revalidates all case inventories,
flags, seed/clock logs, raw comparisons and timing controls before generating the
CSV. `write-report.py` validates the production provenance and emits this report.

`harness-assembly-review/relocation-manifest.json` verifies the exact lookup
body; `assembly-review-refined/` separately records production differences.
`analysis.json`, `profile-steady-late-r1/`, `bus-{early,late}-enabled/`,
`refined-state/`, `fresh-patches-refined-result.json`, `native-refined-r2.log`
and `production-clean-boundary/` retain profiling, compatibility and build proof.
The passive observer uses the unchanged validated RTL model archive; no CPU or
frozen-input parameters changed.

The active port checkout and PR #14 were untouched. Source work and this report
are local signed commits only; no package, push or deployment was performed.
