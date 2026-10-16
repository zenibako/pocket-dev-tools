# Why the iterator experiments trade performance — 2026-10-16

The iterator shortcuts reduce useful work, but recompiling them also changes
hot code placement, branch encodings and memory traffic. For direct `foreach`
and specialized callbacks, Moss executes enough of the optimized paths to
overcome those costs. Celeste's Trailhead sample gets much less benefit and
incurs a larger placement penalty. The smaller array-only saving is overwhelmed
in Moss too. The results do not establish incompatible iterator semantics.

This follows the [four rejected candidates](ITERATOR-OS20.md). The new evidence
uses their original ELFs and checkpoints, with the same seed, routes and
12-frame windows. Timings are simulated os20/90 MHz. [The CSV](ITERATOR-CAUSES.csv)
records exact counts, hashes and diagnostic paths.

## Direct `foreach`: useful work falls only in Moss

| Measured work across 12 frames | Moss | Celeste Trailhead |
|---|---:|---:|
| Baseline instructions in profiled runtime/coroutine | 31,708,640 | 28,294,744 |
| Direct `foreach` candidate | 31,308,842 | 28,294,744 |
| Instruction change | −1.261% | 0.000% |
| Full-frame cost change | −3.117% | +2.031% |

Moss's entire 399,798-instruction reduction comes from three functions:
`foreach` itself saves 188,970 instructions, generic equality saves 210,168,
and removing `lua_settop` saves 660. The generic equality function is entered
7,506 fewer times because the new path compares table identity directly.
Callback counts, table-length searches, `all` iteration and rendering work
remain unchanged. This optimization does not skip actor updates.

Trailhead never calls `foreach` in the measured coroutine. Every profiled
function's instruction count and entry count matches the baseline, as does
every dynamic RV32 instruction-mnemonic count. None of the ten functions
whose generated sizes changed appears in that coroutine profile. Its regression
therefore cannot be explained by executing a slower `foreach` or by doing
more measured Lua/rendering work.

The binary still changes around those functions. In this candidate, 666
same-size text-classified symbols move; this broad count includes some local
data symbols. For example, `spr` moves from `0x10427900` to `0x10427a80`, and
`all`'s iterator moves from `0x104384c0` to `0x10438600`. The BRAM VM retains
its address and size, but addresses referenced by it change. Global data also
moves; Trailhead's heap start remains `0x10459000`.

A passive bus observer confirms a changed memory workload in the full frame:

| Accepted read requests across 12 timer spans | Moss baseline → candidate | Trailhead baseline → candidate |
|---|---:|---:|
| Instruction fetch | 31,848 → 32,863 (+3.187%) | 7,106 → 7,849 (+10.456%) |
| Data-memory master | 154,287 → 151,186 (−2.010%) | 18,295 → 18,404 (+0.596%) |

Moss does fewer instructions and fewer data reads despite slightly more
instruction traffic. Trailhead gets no measured coroutine instruction saving,
and its relocated binary fetches more code. This is concrete evidence of a
collateral placement cost, beyond the earlier observation that addresses moved.

## Array-only shortcut: smaller instruction savings can disappear in timing

The third candidate isolates inline array reads in `all`. Its unchanged-ELF
profiles also show genuine work reduction: Moss executes 31,453,759 instructions
(−0.804%), and Trailhead executes 28,260,616 (−0.121%). Avoided `luaH_getint`
function calls outweigh the extra instructions in the inlined iterator.
Callback and rendering entry counts remain unchanged. Despite those savings,
Moss's frame cost rises 0.281%; Trailhead's falls only 0.030%. The residual
instruction effects in Moss include 3,403 extra VM instructions and 48 fewer
GC-wrapper instructions. No additional bus-traffic run was made for this
candidate. The combined second candidate was not separately traced in this
follow-up; its original controlled timings remain in the prior report.

## Specialized callbacks: the shortcut helps both games

Moss enters the C-closure iterator 29,467 times across the window; Trailhead
enters it 3,840 times. The specialized helper executes 77 instructions per
invocation, replacing 115 instructions in generic call/setup/return functions.
The VM adds eight dispatch/call-block instructions per invocation. Additional
compiler effects change the final totals:

| Measured work across 12 frames | Moss | Celeste Trailhead |
|---|---:|---:|
| Instructions with specialized callbacks | 30,789,564 | 28,073,764 |
| Change against baseline | −2.899% | −0.781% |
| Full-frame cost change | −2.436% | +1.150% |
| Instruction-fetch requests | 31,749 (−0.311%) | 12,057 (+69.674%) |
| Data-memory read requests | 150,484 (−2.465%) | 21,236 (+16.075%) |

The full-frame slowdown in Trailhead persists despite fewer instructions in
its coroutine. Simply calling the SDRAM helper slower than the original BRAM
machinery is not a sufficient explanation: the controlled comparison below
shows that specialization helps at the new layout too.

To separate call-path cost from recompilation, a diagnostic changes only two
BRAM instructions at `0x68ec`: the helper's `auipc`/`jalr` call becomes
`li a3,1; jal luaD_call`. Its return address remains `0x68f4`. Every function
address and all other code retain the candidate layout. The replay uses the
original candidate's prepared SDRAM image and stack byte-for-byte; only the
two BRAM words differ. This directly restores generic calls without rebuilding
or adding a wrapper's execution overhead. The comparison includes the complete
call path and the indirect-versus-direct call encoding, rather than isolating
helper-body cycles.

| Same candidate layout and captured state | Moss frame, ms | Trailhead frame, ms |
|---|---:|---:|
| Specialized iterator calls | 48.617020 | 43.760639 |
| Generic iterator calls restored | 50.150842 | 43.935764 |
| Cost of restoring generic calls | +3.155% | +0.400% |

Thus the specialized call path improves both sampled games when addresses and
warm state are held fixed. The candidate layout plus retained VM dispatch
changes are already expensive before that benefit: the direct-generic control
is 0.642% slower than the original Moss baseline and 1.555% slower than the
original Trailhead baseline. Specialization overcomes that cost in Moss, but
only partly offsets it in Trailhead. These percentages are empirical
comparisons, not an additive cycle decomposition. In fact, the Trailhead
generic-call control issues fewer instruction requests (11,649 versus 12,057)
while running slower. Request counts alone cannot predict frame time.

## Small VM edits change branches well beyond the iterator

The VM's added case grows its BRAM function by only 48 bytes, but GCC rearranges
blocks and the resulting branch distances change. RISC-V conditional branches
have roughly ±4 KiB reach. A destination outside that range needs an inverted
conditional branch plus an unconditional jump.

In `OP_EQ`, two branches that previously reached their destinations directly
now need that extra jump. Those added jumps execute 73,343 times in Moss and
22,560 times in Trailhead. Conversely, a cached `OP_GETTABUP` lookup's branch
moves within reach, eliminating a jump executed 23,397 times in Moss and
52,524 times in Trailhead. The generated code also executes fewer alignment
NOPs. The instruction trace accounts for the complete VM difference:

| VM instruction delta | Moss | Trailhead |
|---|---:|---:|
| Iterator dispatch/call-block changes | +235,736 | +30,720 |
| Other unconditional jumps | +2,569 | −56,628 |
| Alignment NOPs | −37,624 | −49,152 |
| Net VM change | +200,681 | −75,060 |

These are measured execution frequencies, not estimates from static code size.
They explain why even the instruction-count effect of one VM edit depends on
the cart's opcode mix. The changed fetch/data traffic is further evidence that execution timing can
change independently of instruction count. The configured instruction cache has 256 sets,
two ways and 64-byte lines; address-to-set identity repeats every 16 KiB.
Function alignment, code order and branch layout therefore matter alongside
instruction reduction.

## Verification and limits

The six new profiles execute unchanged baseline/candidate ELFs under external
QEMU tracing, validate frame/phase boundaries with positive and missing-marker
negative fixtures, check reference output, and verify immutable ELF/source
inventories. Moss's profile covers `runtime_step`; Trailhead's covers its frame
coroutine including `_update` and `_draw`. Both exclude standalone PCM, so
instruction percentages do not decompose full-frame cycle percentages.

The new observer counts accepted CPU-boundary AXI requests and response beats
using existing exported signals, sampled immediately before each rising edge.
It does not inspect issue lanes, retirement or pipeline hazards. All 70 copied
Verilated model source/header/object/archive files match the frozen originals;
only the separate host observer changes. Unit fixtures check timer pairing,
non-timer reads, wraparound, disabled mode and an unpaired-response failure.

Timer responses for `0x40000004` delimit each full runtime-plus-PCM span. Their
returned-value differences exactly match all original `PICOFRAME` elapsed
values. Traffic covers `(begin response edge, end response edge]`; that is a
precisely paired diagnostic window, rather than a claim of identical timing to
the downstream timer-latch edge. Requests and response beats crossing a span
boundary are counted independently. Counts include speculative/prefetch traffic,
so an instruction-fetch request is not necessarily a demand miss or CPU stall.

All six baseline/candidate observer runs preserve every original output row
and frame cycle exactly, and pass the existing memory checks. The disabled
observer also preserves output and cycles; the corrupted-pixel negative run
fails as expected. The two direct-call controls pass repeated QEMU output and
unchanged warm-heap checks, then quiet RTL output/timer/memory checks. Their
original prepared stack is retained even when fresh QEMU warmup writes different
stack bytes. These are causal diagnostics for the bounded windows, not new
production candidates or complete cart-conformance tests.

The exact cycle split among fetch waiting, data-cache conflicts, branch
prediction and issue scheduling is not measured here. Extra traffic and branch
expansion are established; their percentages must not be treated as CPU-stall
percentages. The existing single-lane os25 pipeline observer remains unused.
Physical Pocket timing and production compiler/layout still require separate
verification.

Reproducible private evidence is under
`experiments/pico8-sources/iterator-causes-20261016-r1`: `profile-moss` and
`profile-trailhead` contain the unchanged-ELF comparisons and exact VM-branch
accounting; `bus-observer` contains the source, fixtures, original-cycle
controls and direct-call controls. `export.py` validates these before generating
the CSV. Earlier failed preparation attempts and the less tightly controlled
helper-entry trampoline tests are retained but excluded from the main tables.

The next optimization should preserve hot VM/code placement while changing the
iterator body, then benchmark both carts. Treating the original A/B percentages
as the intrinsic cost of the iterator algorithm would send that work in the
wrong direction. No additional runtime change was promoted by this diagnosis.
