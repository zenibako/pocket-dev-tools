# Table-identity `foreach` optimization — 2026-10-16

The final candidate, **`3c726f8`**, improves both measured Moss Moss windows
without a measured regression in any of the four Celeste 2 scenes. All six
quiet and scanout comparisons pass. This follows the
[iterator experiments](ITERATOR-OS20.md) and their
[cause analysis](ITERATOR-CAUSES.md).

These are **simulated os20/90 MHz runtime measurements**, including fixed PCM
rendering. Capacity FPS excludes presentation, OS scheduling and live audio.
It is not a physical Pocket measurement or whole-game coverage.

| Sample | Baseline, ms | Candidate, ms | Frame-cost change | Runtime FPS, before → after (30 FPS cap) |
|---|---:|---:|---:|---:|
| Moss, frames 180–191 | 49.830953 | 48.370594 | −2.931% | 20.07 → 20.67 |
| Moss, frames 234–245, GC window | 50.579213 | 48.693879 | −3.727% | 19.77 → 20.54 |
| Celeste title, frames 100–111 | 4.614362 | 4.614362 | 0% | 30 → 30, capped |
| Celeste intro 1, frames 100–111 | 21.507412 | 21.507412 | 0% | 30 → 30, capped |
| Celeste intro 2, frames 100–111 | 27.738885 | 27.738885 | 0% | 30 → 30, capped |
| Celeste Trailhead, frames 100–111 | 43.263101 | 43.263101 | 0% | 23.11 → 23.11 |

Every individual Celeste frame cycle count matches its baseline, in both quiet
and diagnostic scanout modes. Moss's scanout mean costs fall 2.923% and 3.760%
respectively. The [validated CSV](FOREACH-TABLE-OS20.csv) retains exact values,
source and ELF hashes, BRAM sizes and private case identities.

## Implementation

Only the post-callback equality check in `api_foreach` changes. When both the
current and previous values are tables, raw equality compares their identities
directly. Other types retain `lua_rawequal`. Length checks, table accesses,
callback setup, result handling and mutation-aware traversal remain unchanged.
The previous value stays rooted on the Lua stack, and pointers are acquired
after the callback, which may relocate the stack or collect garbage.

For the RISC-V GCC target, this helper also uses `align-loops=4` to limit loop
padding and `noipa` to prevent caller interprocedural optimization of the
indirect callback function. The baseline VM implementation and dependency
patch set remain unchanged. The final diff against production baseline
`bc2e8b6` contains only `src/runtime/runtime.cpp` and
`tests/runtime_test.cpp`.

This is a measured combination of source and compiler attributes, not a claim
that table identity alone explains the full gain. `noipa` is a local compiler
boundary; it does not freeze the whole program's code generation.

## Why this variant passes

The narrower identity change initially still regressed Trailhead. Three
immutable candidates were tested:

| Candidate | Source | Moss steady cost | Trailhead cost | Verdict |
|---|---|---:|---:|---|
| Table identity only | `ba1c955` | −1.462% | +0.173% | Reject |
| Identity plus compact loop alignment | `4044c89` | −0.414% | +0.414% | Reject |
| Identity, compact alignment and `noipa` | `3c726f8` | −2.931% | 0% | Pass all six windows |

Compact alignment restores the helper's body to 512 bytes in its original
576-byte padded slot. The final candidate restores all four Celeste scenes'
BRAM bytes to their respective baselines. In the audited Trailhead ELF,
no actual named text/data symbols move. Debug metadata is excluded from that
address comparison. This removes the earlier collateral change from a cart
that does not execute the optimized helper in the measured coroutine.

Moss still has broader compiler effects: its VM grows 42 bytes and seven
following BRAM functions move 44 bytes; its total BRAM grows from 14,040 to
14,084 bytes, below the 14,336-byte limit. Its SDRAM code/data also relocate.
The measured gain therefore includes these compiler/layout effects. A full
normalized audit is retained rather than asserting globally unchanged layout.

A fresh baseline rebuild with byte-identical source inventories reproduces
the entire original Trailhead ELF and BRAM byte-for-byte, with zero moved
symbols. The observed differences are repeatable compiler consequences of
the candidate, rather than an unexplained baseline rebuild difference.

## Verification

All six final cases pass two native 600-frame runs, repeated RV32 QEMU
captures with `native_output_equal=true`, quiet and scanout RTL output/memory
oracles, and deliberate corrupted-pixel negative controls. Baseline/candidate
native raw pixels, palettes and PCM are byte-identical over all 600 frames;
the collector also verifies output rows and PCM pair counts against the normal
runner. RV32 output checks cover each selected 12-frame window.

Cart, route, final hash seed `0x5eed1234`, measured window, compiler flags,
link command, PCM model and CPU configuration match each baseline. Native/QEMU
readback validates the seed; RTL validates the 90 MHz MMIO clock. The frozen
1,631-file input inventory and os20 platform remain unchanged. Source inventories
differ only in `runtime.cpp`; no harness timing or CPU parameters were changed.

The native core and runtime suites pass. Regression coverage includes 17
`foreach` cases, including table identity, raw metamethod behavior, mixed-type
replacement, deletion/appending, sparse boundaries, recursion, callback errors,
yield rejection, stack/table growth and garbage collection, plus seven `all`
cases. Celeste's local acceptance run completes 600 frames and a 90-frame
save-state replay with zero mismatches. ASan/UBSan passes for the comparison
change; a deliberately broken table-equality shortcut is rejected by the
fixtures. The later attributes affect target code generation only and pass
the target output controls above.

The compiler remains harness GCC 13.2; production compiler/layout, allocator,
presentation, OS scheduling and physical-device timing require separate
verification. This evidence covers reconstructed stationary Celeste scenes and
the existing Moss seed-7 gameplay route. Moss remains below its 30 FPS target.

## Delivery and private evidence

Source commit `3c726f8` and its parent experiments are GPG signed. The isolated
source checkout is
`experiments/pico8-sources/iterators-20261016-r1/candidate`.
Review the complete accepted change with `git diff bc2e8b6 3c726f8` there.
The equivalent source-only patch is
`experiments/pico8-sources/table-identity-20261016-r3/foreach-table.patch`.

Private `table-identity-20261016-r1` through `-r3` contain source snapshots,
launchers, logs, raw comparisons and layout audits. `-r3/export.py` validates
all ten complete A/B scene results before generating the CSV. The first two
candidates stopped after their initial two-game gate failed; remaining cases
are preserved but not counted as completed evidence. No old experiments were
deleted, no game-port active checkout was modified, and no device deployment,
push or external publication occurred.
