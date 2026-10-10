# Passive os25 cache profiling

This extension follows [ARCHITECTURE.md](../ARCHITECTURE.md), the preserved
[full-frame workflow](../fullframe/README.md) and the independently captured
[revision cases](../bench/README.md). It observes the existing CPU without
changing its RTL parameters, firmware, checkpoints or baseline evidence.

The verified frozen-baseline study is in [RESULTS.md](RESULTS.md). Its private
machine-readable counterpart is `build/cache-profile/results.json`, with exact
distributions, function/address histograms, flags, hashes and evidence paths.
These are simulated pipeline and bus measurements, not physical Pocket timings.

## Run an existing case

First prepare and verify an experiment case using `experiments.py`. Use its
exact printed case path: several cases can have the same revision/window/build
kind but different compiler, placement or native-script settings.

```sh
python3 run.py verify
python3 cache_profile.py --case experiments/cases/EXACT_CASE_NAME --traffic quiet
python3 cache_profile.py --case experiments/cases/EXACT_CASE_NAME --disabled
python3 cache_profile.py --case experiments/cases/EXACT_CASE_NAME --negative
```

The source case must already have a successful replay for the selected traffic.
Each command creates a new independent copy under `experiments/cache-profiles/`.
Only that copy is mounted at `/work`; the active port checkout, SDK/OS originals
and SD card are neither mounted nor modified. The wrapper is compiled once per
observer-source hash, then copied into each measurement. Existing output names
are refused rather than overwritten. Frozen input hashes are checked before
and after replay.

The Verilog wrapper exposes read-only signals behind `HARNESS_CACHE_PROFILE`;
the C++ observer records only when `CACHE_PROFILE=1`. `--disabled` runs the same
observer-capable binary with recording switched off. CPU parameter changes are
recorded as `{}` in `rtl.json`, propagated into every result. A positive run
must reproduce the original frame cycles and all oracle values exactly before
its profile is accepted. The negative run must still reject a corrupted state
oracle.

Generate the named f1d8542/Speed/legacy/SDRAM/quiet study with exact result paths:

```sh
python3 cache_report.py --results PROFILE_RESULT_1 PROFILE_RESULT_2 \
    --checks DISABLED_RESULT NEGATIVE_RESULT SCANOUT_RESULT \
    --output build/cache-profile/results.json --markdown build/cache-profile/results.md
```

This report writer deliberately rejects a different revision, compiler or
service model under the baseline study’s label. It verifies ordinary capture,
checkpoint, simulator and log hashes, the copied observer/wrapper, raw event CSV,
ELF and original replay result, and reanalyses the CSV before producing tables.
Scanout/BRAM controls may be supplied through `--checks` and are labeled by their
own configuration. Per-case `quiet-results.json`/`scanout-results.json` also
contain the complete analysis under `cache_profile`.

## What the counters mean

Observer v3 also measures canonical architectural retirement, dispatch, source
operand dependencies, execution freezes and branch recovery. See
[PIPELINE-RESULTS.md](PIPELINE-RESULTS.md) for the frozen eight-case study;
[RESULTS.md](RESULTS.md) remains the original v2 cache study. The same
`--case`, `--disabled` and `--negative` commands apply. Write the new report to
separate destinations to preserve the earlier evidence:

```sh
python3 pipeline_report.py --results EIGHT_EXACT_POSITIVE_RESULTS \
    --checks DISABLED_RESULTS NEGATIVE_RESULTS SCANOUT_RESULTS \
    --output build/pipeline-profile/results.json \
    --markdown build/pipeline-profile/results.md
```

`pipeline_report.py` requires both builds of all four frozen Speed/legacy/SDRAM/
quiet windows. It rejects a missing/duplicate window or different revision,
compiler or service configuration. Both report writers verify artifacts and
freshly parse the raw events; v2 parsing retains its original schema.

All signals are sampled settled, immediately before a rising CPU clock edge.
The peripheral cycle counter supplies timestamps. Frames begin/end on the exact
MMIO latch edges used by the existing `frame_begin`/`frame_end` firmware reads,
identified from the ELF’s sized function symbols. No marker, UART delay or
additional firmware instruction is added. The sample count must equal the
firmware’s elapsed cycle count for each of the three frames.

| Quantity | Pinned RTL / observer definition |
| --- | --- |
| I refill | CPU-side `i_arvalid_cpu && i_arready_cpu`, completed by accepted `i_rlast_cpu` with its ID |
| D refill | CPU-side `mem_arvalid_cpu && mem_arready_cpu`, completed by accepted `mem_rlast_cpu` with its ID |
| Full refill latency | Accepted AR through accepted RLAST, inclusive; a 64-byte, 16-beat read |
| First-beat latency | Accepted AR through first accepted R beat, inclusive |
| AR backpressure | First AR offer through acceptance, exclusive of the acceptance edge |
| I fetch hold | `FetchL1Plugin_logic_refill_onRsp_holdHarts` while stage-1 fetch is valid; includes refill tag writes |
| I miss recovery | Passive shadow of `FetchL1Plugin.scala`’s optional `onEvents.waiting`: set by stage-3 `up.isMoving && allowRefill`, cleared by stage-3 `isValid && !TRAP`; set wins |
| I block | Union of I fetch hold and I miss recovery, counted once per clock |
| D block | `LsuPlugin_logic_onCtrl_hartRegulation_valid`, the refill waiter halting dispatch |
| I/D union | I block + D block − simultaneous block |
| No-commit subset | Above cycles with no `WhiteboxerPlugin_logic_commits_ports_0_valid` architectural commit-decision pulse |

### Additional v3 observations

| Quantity | Definition |
| --- | --- |
| Retired instruction | `PrivilegedPlugin_logic_harts_0_commitMask`, ctrl5 CommitService; the optional hardware instruction counter uses this event |
| CPI | Exact frame cycles divided by canonical retired native RISC-V instructions; pooled CPI divides pooled cycles by pooled instructions |
| Retiring function/instruction mix | Dispatch PC and decompressed instruction tracked by the 16-bit UOP ID until retirement; cancelled work never retires |
| RAW dependency | Valid, uncancelled candidate cannot dispatch while `rsHazards[0]` is asserted |
| Load/multiply/FP dependency | Exact producer-stage register/enable/file/bypass matches, classified by producer instruction; counts overlap across operands |
| FP reservation | Candidate blocked by the shared FP add/pack resource reservation checker |
| Execute freeze | Union of divider, sqrt, float-to-int, int-to-float, uncached LSU I/O, CSR injection and atomic delay freezes |
| Integer/FP divider | Shared divider freeze split by the ctrl2 FP-divide select |
| Store-buffer wait | `LsuPlugin_logic_storeBuffer_holdHart_waitIt`, separately from the refill waiter |
| Flush/fence interlocks | Candidate blocked by dispatch flush/fence hazard flags; these are not branch-mispredict counts |
| Branch/jump mispredict | Firing branch learn event with `wasWrong`; includes direction/target corrections, calls and returns |
| Branch recovery envelope | That event through dispatch of the corrected target, exclusive of the redirect edge; overlaps cache and execution waits |

The observer checks every sample that its reconstructed producer hazards match
the RTL RAW signal and that its freeze sources equal the global freeze signal.
Load and integer multiply producers occur in stages 1–4 in this netlist. FP
classification includes FP instructions there and later floating-register
producers. Late FP results to integer registers can remain in other RAW; the FP
subset is conservative. There is no dedicated integer multiply freeze pin.

`P` records retain the complete per-cycle bitmask histogram; `S` records retain
blocked consumer PCs; `T` records retain retired PCs/instructions; `B` records
retain completed branch recovery episodes (`V` marks an unfinished episode).
The analyzer requires complete frame/PC histograms and branch recoveries.
Existing cache `F/H/R/M/W/U` records remain unchanged. The mask bit names are in
[pipeline_analysis.py](../pipeline_analysis.py); the read-only pins and runtime
checks are in [signals.vh](signals.vh) and [pipeline.hpp](pipeline.hpp).

No-retirement subsets use the canonical ctrl5 event; old no-commit subsets keep
the ctrl4 definition. Overlapping signals are observations, not additive lost
cycles. The report's disjoint partition states its assignment priority and
preserves the raw masks so another priority can be computed. Branch recovery
also includes I-cache misses and other waits. Removing one observed source
requires a separate counterfactual before claiming a speedup.

The timing firmware omits per-VM-instruction tracing and in-loop PCM hashing,
but still enables `SW_DRAW_PROFILE` and `ENABLE_VM_GML_PROFILER`. Renderer note
formatting/searching remains measured work. Hardware FPU counters also exclude
software double-precision helpers. Do not equate full-frame CPI with the cost
of an isolated sprite probe or describe this timing binary as profiler-free.

The production netlist omits the optional I-cache waiting event register. The
observer shadows its documented source logic without instantiating or driving
a register in the CPU. SpinalHDL `Node.isMoving` is `valid && (ready || cancel)`
for this cancellable node. The shadow is updated after counting its old value,
matching sequential RTL. It remains active across fetch REDO/flush/retry until
any valid non-trapped fetch reaches the cache-control stage. This includes
recovery overhead and possibly speculative cancelled demand fetches; it is not
just time spent awaiting an SDRAM response. Recovery episode lengths are also
recorded. An already active episode retains its initiating miss PC.

The relevant private, pinned sources are:

- `inputs/os/src/fpga/vendor/vexriscv/VexiiRiscv/src/main/scala/vexiiriscv/fetch/FetchL1Plugin.scala`, `onEvents` and `refill.onRsp`.
- The corresponding `execute/lsu/LsuPlugin.scala`, `L1Waiter`/`hartRegulation`.
- `ext/SpinalHDL/lib/src/main/scala/spinal/lib/misc/pipeline/Node.scala`, `isMoving`.
- `inputs/os/src/fpga/vendor/vexriscv/VexiiRiscv/VexiiRiscv_os25.v`, generated signals named in [signals.vh](signals.vh).

Additional pipeline references under the same pinned `src/main/scala/vexiiriscv/`
root are `misc/TrapPlugin.scala` (CommitService mask),
`misc/PerformanceCounterPlugin.scala` (instruction-counter event),
`schedule/DispatchPlugin.scala` (source-register bypass and reservations),
`execute/BranchPlugin.scala` (firing prediction learn event/redirect),
`execute/DivPlugin.scala` and `execute/fpu/FpuDivPlugin.scala` (shared divider),
and `execute/ExecutePipelinePlugin.scala` (global freeze).

## Interpretation and attribution

I-cache traffic includes next-line prefetch and speculative fetch. Refills can
overlap each other, execute useful instructions, and continue after a critical
word has satisfied a demand miss. Consequently full transaction latency sums
are not frame stall time. The report retains both summed latency and the union
of outstanding bus intervals, separately from pipeline blocking.

Counts/distributions include transactions accepted within `[frame_begin,
frame_end)`, even when they finish after the frame. Blocking is clipped to the
frame. Left/right boundary transfers are reported; incomplete accepted frame
transfers are rejected. Exact histograms preserve tails, and pooled quantiles
weight individual refills rather than averaging per-frame quantiles.

The I address histogram uses refill line bases. Sized ELF `STT_FUNC` ranges
provide function attribution, preserving same-address aliases. Padding and
unknown addresses remain explicitly unattributed; a line base is never assigned
to the nearest preceding function outside its size. A line can contain another
function or speculated code, so refill attribution does not identify the exact
instruction that demanded it. Blocking cycles use the initiating miss PC while
recovery is active, otherwise the held stage-1 fetch PC. These are different
histograms and produce separate top-30 rankings and frame shares.

Frontend/dispatch blocks can coexist with older instructions committing. The
no-commit subset is an observation, not proof of uniquely lost execution cycles.
D-cache blocking excludes other store-buffer/writeback backpressure. Exact
speedup from removing a cache limit needs a separately recorded counterfactual;
this study changes no cache size or refill latency parameter. Do not conclude
that an isolated renderer path is dominated by misses from frame-wide counts,
or infer a layout speedup from speculative refill service sums.

Validation includes the real C++ observer driven with synthetic pin sequences
for backpressure, out-of-order IDs, cross-frame completions, recovery intervals,
I/D overlap and continued commits, plus rejected shifted timing/PC histograms.
Actual replay, switch-off equality, bad-state rejection and original aggregate
verification accompany the frozen study. Hardware fidelity limitations remain
those in the bench/full-frame READMEs.
