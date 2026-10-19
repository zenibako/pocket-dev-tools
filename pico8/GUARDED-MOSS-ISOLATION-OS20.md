# Moss guarded-VM regression isolation — 2026-10-18

The regression has **two separable contributors**: changed machine code in
`luaV_gettable`, and changes elsewhere in the binary and its placement. Both
fixed-slot swap directions reproduce a cost increase. The separated-handler
candidate has identical measured instruction, entry and memory-operation totals
to baseline in both Moss windows, but generates substantially more instruction-
fetch traffic. The exact
local instruction/prediction/stall mechanism remains unresolved; this study does
not reduce the cause to a single bad instruction or a cache-miss percentage.

This follows [the guarded inheritance experiment](GUARDED-DELEGATE-OS20.md),
[the earlier fixed-layout diagnostic method](ENV-LAYOUT-CONTROL-OS20.md), and
[the compiler/placement findings](ITERATOR-CAUSES.md). All timings below are
simulated os20/90 MHz costs, not physical Pocket FPS. No source optimization was
accepted or packaged, and the active port and PR #14 were not changed.

## Fixed-slot causal controls

The baseline lookup body is 612 bytes; the separated-handler body is 600 bytes.
Both fit either existing 640-byte function slot. Transplants preserve every
other executable/checkpoint byte, address, original RTL stack and input. Eight
external call sites and two absolute string references are relocated explicitly;
internal branch offsets are preserved. Recipient helper implementations remain
in place, so this isolates the lookup body from its surrounding build rather
than replacing every table helper.

Quiet mean costs, with changes relative to the original baseline:

| Lookup body | Surrounding build | Moss steady, ms | Change | Moss GC window, ms | Change |
| --- | --- | ---: | ---: | ---: | ---: |
| Original | Original | 48.685559 | reference | 49.040888 | reference |
| Separated handler | New | 48.943138 | +0.5291% | 49.360624 | +0.6520% |
| Original | New | 48.816417 | +0.2688% | 49.222193 | +0.3697% |
| Separated handler | Original | 48.759269 | +0.1514% | 49.163578 | +0.2502% |

Replacing only the lookup body in the new binary recovers 0.126721 ms in steady
and 0.138431 ms in the GC window, while leaving a regression. Conversely, the
new lookup body regresses the original surrounding binary. Neither contributor
can be dismissed. Their costs depend on context and must not be added as fixed
independent percentages. Scanout agrees in direction: original-body/new-surrounds
is +0.4285%/+0.4256%, and new-body/original-surrounds is +0.1564%/+0.2395%.

The reverse transplant is explicitly **Moss-only**: the new callback handler does
not exist in the original binary, so its unreachable tail is replaced with
`EBREAK`. Any unexpected callback fails closed instead of invoking a wrong ABI.
Repeated full QEMU runs pass, and independent profiles record no such callbacks.
This diagnostic cannot be used as a general emulator build or Pocket package.
The forward transplant preserves the complete original callback behavior.

## Actual executed work

Unchanged-ELF QEMU traces cover runtime-step entry through return, excluding
standalone PCM generation, frame hashing and presentation. Positive and missing-
marker negative parser fixtures pass; all six profiles retain original output
and ELF hashes. Counts are architectural instructions, not cycle shares.

| Window | Baseline instructions | Initial candidate | Separated handler |
| --- | ---: | ---: | ---: |
| Steady, frames 180–191 | 31,299,864 | 31,311,036 | 31,299,864 |
| Allocation/GC, frames 234–245 | 31,886,090 | 31,897,237 | 31,886,090 |

The separated handler matches baseline instructions, entries and memory-operation
counts **for every profiled function in both windows**. This includes VM,
allocator and GC routines. There is no additional simulated game work to explain
its slower runtime. Allocator geometry also matches within both windows:
steady has 1,621 blocks (56 free), and the GC window has 1,455 blocks (62 free).
All corresponding header bytes, addresses, links and free flags agree.
All six source cases keep heap start `0x10459000`; the warm heap cursor
matches within each window: `0x106c3030` for steady and `0x106ef070` for the GC
window. Simple heap displacement between builds is ruled out. Relocated static/code
pointer values still differ between source builds.

The measured steady lookup path is more specific than the previous raw-hit
assembly example: 9,087 calls perform 16,904 raw reads, all missing; 7,817 follow
one table-valued inheritance hop. There are no string-index paths, function-valued
callbacks or new missing-metamethod cache writes in that measured window.
`luaV_gettable` executes 738,105 instructions in both original and separated
builds, with identical load/store counts. A real string out-of-range path differs
in assembly, but it does not execute here and cannot explain this window.

The initial candidate has extra generated work: steady lookup adds 16,904 loads,
9,087 stores and 7,817 instructions. The key is spilled/reloaded, and an extra
move retains the metamethod pointer even for table-valued inheritance. The GC
window similarly adds 16,842 loads, 8,948 stores and 7,894 lookup instructions.
The initial VM/GC-check code generation also changes; the separated-handler
version restores all per-function totals. Counts of a GC entry are not a measure
of time spent collecting.

## Surrounding fetch traffic

A previously validated passive host-side AXI observer uses the byte-identical
compiled os20 RTL archive. Its disabled and enabled runs reproduce the original
frame cycles exactly, and its corrupted-output negative control fails as
expected. It observes accepted CPU-boundary requests/responses between the same
paired frame timer reads. It includes speculation/prefetch; these counts are not
retired instructions, demand miss rates, CPI or stall cycles.

Steady-window accepted request totals:

| Build/control | Instruction requests | Data requests |
| --- | ---: | ---: |
| Original | 30,171 | 153,316 |
| Separated handler | 35,528 | 150,508 |
| Original lookup in new surroundings | 35,688 | 150,508 |
| New lookup in original surroundings | 30,192 | 153,316 |

Holding the lookup body constant, the new surroundings generate **17.7–18.3%
more instruction requests** and 1.83% fewer data requests.
That strongly supports a surrounding instruction-placement/front-end traffic
component; it does not assign the elapsed-cycle difference to those requests.
The old lookup body is faster even though it slightly increases instruction
requests in the new surroundings, so fetch counts alone cannot explain the local
lookup-body effect.

Grouping accepted instruction addresses by the symbol containing the request's
starting address gives these larger changes between the two source builds:

| Routine | Original requests | Separated-handler requests |
| --- | ---: | ---: |
| Short-string interning | 63 | 1,567 |
| Iterator next | 572 | 1,496 |
| VM dispatch | 4,725 | 5,540 |
| Pool allocator | 1,350 | 271 |

Function execution counts are unchanged. These are changes in code residency /
fetch behavior, with gains as well as losses; they are not evidence that string
interning or iteration algorithms execute more work. Boundary/padding attribution
and speculative fetches limit the interpretation of symbol-level request counts.

## One narrower scheduling hypothesis rejected

A six-byte diagnostic swaps the order of `s0` and `s2` restore loads. Three
same-width compressed instructions change, including the valid-string path's
restore to keep the shared epilogue correct. All PCs, widths, branch targets and
caller values remain valid; independent review found no control-flow issue.

Both Moss windows produce **exactly the original separated-handler cycle counts
on every quiet and scanout frame**. The tested restore ordering is therefore not
the local cause. Other register choices, branch encodings, internal alignment and
prediction/issue effects remain possible; no random source alignment fix is
justified by this negative control.

## Verification and retained evidence

The [validated CSV](GUARDED-MOSS-ISOLATION-OS20.csv) contains 24 rows for both
windows/traffic modes, original candidates, both swap directions and the restore
control, with exact source revision, ELF and log identities. Baseline is
`db6bced`, initial is `1466107`, separated handler is `ea36491`.

Each of the six derived images passes two QEMU runs with matching frame oracles
and byte-identical warm checkpoint outside its fixed code slot. Regenerated
scratch stacks differ; RTL deliberately uses the original receiver stack. The
checkpoint is taken in the outer runner before the next runtime step, after the
previous step returned; no gettable native frame is suspended. Each image passes
an exact-cycle identity replay, quiet and scanout output/memory oracles, and an
intentional negative output oracle. Encoding, external-helper ABI, outside-slot
bytes and the restore control were independently reviewed.

The four passive bus runs preserve exact validated cycles/output; disabled and
negative controls pass. The observer's compiled RTL archive equals the pinned
os20 archive byte-for-byte, and CPU parameters are unchanged. Private profiles,
relocation/ABI manifests, original/draft artifacts, captures, controls and the
independent exporter remain under
`experiments/pico8-sources/guarded-moss-isolation-20261018-r1/`.
Frozen inputs and os20 platform hashes are checked separately. Derived-image
outputs are hash-oracle comparisons, not newly exported raw rendered channels;
the original source-case raw equality remains covered by the preceding report.

The next source experiment should preserve the original hot table-miss path and
its calling convention, then isolate placement of the new cold delegate code.
That targets both demonstrated contributors. The branch/pipeline mechanism and
physical Pocket effect remain open; these diagnostics are not a shipping fix.
