# Iterator and callback experiments — 2026-10-16

None of four runtime/VM candidates satisfies the requirement that neither
Celeste 2 nor Moss Moss regress. Keep the production baseline at `bc2e8b6`.
The candidates remain isolated, signed experiment commits; no runtime change
was promoted to the active game checkout.

The [follow-up cause analysis](ITERATOR-CAUSES.md) separates instruction savings
from placement, branch-range and memory-traffic effects using unchanged ELFs
and controls that retain the candidate layout.

This follows the diagnoses in [Celeste 2](CELESTE2-OS20.md) and
[Moss Moss](MOSS-OS20.md). The measurements below are **simulated os20/90 MHz
runtime costs**, not measured Pocket FPS. A negative cost change is faster.

| Candidate | Source commit | Moss frames 180–191 | Celeste Trailhead frames 100–111 | Decision |
|---|---|---:|---:|---|
| Direct-table `foreach` traversal | `444be87` | −3.117% | +2.031% | Reject |
| Direct-table `foreach` plus inline array reads in `all`/`foreach` | `b93c2c9` | −2.995% | +0.952% | Reject |
| Inline array reads in `all` only | `b7f4819` | +0.281% | −0.030% | Reject |
| Separate C-closure iterator call path | `c3c2761` | −2.436% | +1.150% | Reject |

The baseline costs are 49.831 ms / 20.07 FPS capacity for Moss and
43.263 ms / 23.11 FPS capacity for Trailhead. The direct `foreach` candidate
reaches 48.278 ms / 20.71 FPS in Moss, but takes 44.142 ms / 22.65 FPS in
Trailhead. The separate iterator-call candidate takes 48.617 ms / 20.57 FPS
and 43.761 ms / 22.85 FPS respectively. These improvements are too small to
bring Moss to its 30 FPS target and do not justify the Celeste regression.

The original Celeste samples remain 30 FPS at the target cap for title,
intro 1 and intro 2 (4.614, 21.507 and 27.739 ms respectively). Earlier
rejected candidates also ran extra intro/GC windows before stopping;
[the validated CSV](ITERATOR-OS20.csv) records every fully controlled result.
Unfinished cases are preserved and are not counted as passing evidence.

## What was changed

The first candidate avoids repeated Lua API table accesses in `foreach`,
while retaining its mutation behavior: deletion of the current value retries
that index; other changes, appends, sparse boundaries and raw length follow
the existing semantics. The second candidate also bypasses `luaH_getint` for
array slots, keeping the integer-key hash fallback. The third restores the
baseline `foreach` and isolates only `all`'s array reads. These did not produce
a shared win.

The fourth candidate restores `runtime.cpp` byte-for-byte to the baseline
and adds a separate `luaD_callciterfast` helper only for C-closure iterators
at `OP_TFORCALL`. Ordinary light-C API calls keep their existing fast path.
The helper preserves a real C call frame, depth overflow checks, stack growth,
GC, upvalues, callback errors/yields, result padding, and hooks enabled during
setup GC or by the callback. It is `noinline` in SDRAM at `0x104113c0`, size
366 bytes. BRAM grows from 14,040 to 14,088 bytes, below the 14,336-byte limit.

The shared VM/layout tradeoff matters. In the first candidate, the BRAM size
and `luaV_execute` address remained unchanged, while several SDRAM helper
addresses and unrelated generated function sizes changed. This is evidence
of compiler/layout sensitivity, not proof of a particular cache stall cause.
A source-level reduction in API work does not imply a whole-cart speedup.
The iterator-specific fourth candidate also regresses Trailhead, despite
leaving the ordinary light-C helper unchanged. No unvalidated os25 pipeline
observer was used to claim an exact os20 stall attribution.

## Verification and reproducibility

Each result admitted to the CSV requires matching cart, route, fixed final
Lua seed `0x5eed1234`, source inventory, 12-frame window, clock and fixed PCM
model. The frozen 1,631-file input inventory and os20 platform hashes pass.
Native/readback confirms the seed; RTL confirms the 90 MHz MMIO clock.
Baseline cases are from the two linked reports and were not overwritten.

Completed results pass two native 600-frame runs, baseline/candidate raw pixel,
palette and PCM byte comparisons over all 600 frames, repeated QEMU capture
with `native_output_equal=true`, quiet and scanout RTL output and memory
oracles, and deliberate corrupted-pixel negative controls. The native collector
also checks every frame's output row and PCM pair count against the normal
runner. The CSV retains source/ELF hashes and exact private case identities.

The runtime suite passes 16 added `foreach` mutation/callback cases and seven
`all` cases. Celeste's local acceptance cart passes 600 frames plus a 90-frame
save-state replay with zero mismatches. The first direct-table fixture detects
a deliberately broken index-advance rule; the array fixture detects removal
of the integer-key hash fallback. The fourth candidate passes 12 focused
C-closure iterator cases; hook counts exactly match the generic baseline.
Its fixture rejects a deliberately omitted post-GC call hook. Runtime and
iterator suites also pass ASan/UBSan, with leak detection disabled on macOS.
Independent code review found no actionable semantic issue. The dependency
patch reapplies to the prior patched sources byte-for-byte.

Private experiment roots are `experiments/pico8-sources/iterators-20261016-r1`
through `-r4`. Each contains its launcher, logs and per-scene result JSON;
`-r4/report.py` validates complete results before generating this CSV.
The source worktree is under `-r1/candidate`; all four source commits are
GPG signed. Game assets, source snapshots, raw streams and binaries remain
ignored. No device build, deployment, push or external publication occurred.

These stationary/reconstructed Celeste scenes and bounded Moss routes are
regression samples, not whole-game coverage. The harness substitutes allocator
and OS services, uses GCC 13.2, starts RTL caches cold and excludes presentation,
OS scheduling, SD and live audio delivery. Production compiler/layout and
physical Pocket FPS need separate evidence. Do not generalize these simulated
percentages to the device.
