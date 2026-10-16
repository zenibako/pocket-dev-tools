# Environment fallback lookup experiments — 2026-10-16

No environment-lookup candidate was accepted. The rebased audio optimization
on **`perf/audio-output-pairs` at `9f4cd16`** remains the current validated change.
The best new lookup variant improved Moss slightly but regressed Trailhead.
These are **simulated os20/90 MHz runtime frame costs**, not physical Pocket FPS.

| Variant | Moss steady cost | Trailhead cost | Decision |
|---|---:|---:|---|
| Field lookup inline | +0.441% | +1.228% | Reject |
| Both lookups inline / leaf | -0.881% | +1.665% | Reject |
| Leaf plus target noipa | +3.670% | +3.170% | Reject |

Baseline frame costs are 48.287563 ms for Moss and 42.322168 ms for Trailhead,
from the [accepted audio study](AUDIO-PAIRS-OS20.md). Scanout follows the same
accept/reject outcome. The [validated CSV](ENV-LOOKUP-OS20.csv) records exact
quiet/scanout means, source and ELF hashes, BRAM sizes and case identities.
Each attempt stopped after this two-game gate; the other four scenes were
created but not run and are not counted as evidence.

## Rebase completed first

PR #13 merged as `1ef6525`. The two local audio commits were GPG-signed again
on top of that merge: `793c98d` and `9f4cd16`. A backup branch,
`archive/audio-output-pairs-pre-rebase-20261016`, preserves `9edffde` and its
parent. The old and rebased trees are byte-identical; native core/runtime and
Celeste save-state replay tests pass after rebase. The existing audio package
therefore still contains the same runtime code.

A fresh simulator build from the rebased audio source reproduces the prior
accepted Trailhead ELF and BRAM byte for byte. Historical evidence retains its
original source revisions. `audio-pairs-20261016-r2/rebase-provenance.json`
records the mapping and tree identity. No force-push or PR update occurred.

## Opportunity and implementation

The earlier unchanged-ELF profiles show `fastchain` entered 16,043 times per
12-frame Moss window, with 15,684 first inherited-field lookups and 15,412
successful returns. Trailhead enters it 3,456 times, but performs no inherited
field lookup: its sampled path exits at the metamethod/type guard. These old
instruction counts establish a target, not cycle shares for the audio build.

The first candidate (`20eaad4`) copied `luaH_getstr`'s short-string hash-node
walk into `fastchain`'s inherited-field read. It preserved live table reads,
false values, collision traversal, four-hop limits and all fallback paths.
The intended saving was the helper's real SDRAM-to-BRAM call. The compiler
instead emitted a smaller non-unrolled helper (366 to 212 bytes) and changed
surrounding layout. Both games regressed, including Trailhead's zero-hit path.

The second candidate (`8419522`) used the local raw lookup for the `__index`
metamethod as well. It preserved null-metatable and cached-absence checks;
only nil sets the absence flag, while false/functions/other types fall back.
The helper becomes a 192-byte leaf with no call instructions in either cart's
ELF. Moss improves 0.881%, but Trailhead regresses 1.665%. GCC specializes the
helper's arguments, relocates its clone, and changes VM call sites. Production
BRAM grows from 14,182 to 14,198 bytes, still within 14,336.

The last candidate (`4be2dd9`) retains the leaf algorithm but uses target GCC
`noipa` to prevent caller argument specialization. It is still a leaf, now
198 bytes, yet VM code/layout do not return to baseline and both games worsen.
`noipa` is therefore not a general cure for collateral performance changes.

These are observed compiler consequences and whole-window timings. We did not
isolate their exact cycle split among helper instructions, cache conflicts,
branch behavior and other layout effects. Neither fewer calls nor smaller
code establishes a whole-frame improvement; the paired-cart measurements are
the acceptance criteria. The lookup patch is archived and kept out of the
validated audio branch.

## Verification and retained evidence

All six completed A/B results pass two native 600-frame runs, repeated RV32
captures with native equality, quiet/scanout RTL output and memory oracles,
and corrupted-pixel negative controls. Baseline/candidate raw pixels, palettes
and PCM are byte-identical for 600 frames in both games for all three attempts;
the reviewed collector's rows and pair counts match the normal runner.

The native suites and Celeste 600-frame/save-state tests pass. Focused `_ENV`
fixtures cover local/upvalue environments, false/zero/nil, mutation and rehash,
metatable replacement, deep/function/cyclic/invalid chains and long keys.
Additional fixtures cover missing `__index` followed by insertion and a false
`__index` followed by replacement. Deliberate false-value and false-metamethod
negative-cache mutants are rejected. Field and leaf implementations pass
ASan/UBSan; the final added attribute affects RISC-V GCC only.

The appended dependency patch applies after the existing 17 patches to pinned
Z8Lua `e6928578`. Freshly patched C/header files match the prepared dependency.
All production builds pass the BRAM limit; no runtime or dependency revision,
CPU/platform pin, frozen input, original SDK or SD card was changed.

Private `env-lookup-20261016-r1` through `-r3` retain signed source commits,
launchers, build logs, raw comparisons, baseline reproduction, patch validation,
mutants, sanitizer evidence and code-generation audits. The source worktree is
in `-r1/candidate`; `archive/env-lookup-experiments-20261016` preserves the final
rejected chain. `-r3/export.py` validates six complete results before exporting
the CSV. There is no accepted lookup package or device performance claim.
