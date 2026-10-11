# Rebased Script times disabled-path comparison, 2026-10-10

This repeats the [feature-preserving profiler test](2026-10-10-profiler-off-results.md)
after rebasing onto main 308c17c, then prepares a Pocket card for the MacBook pull.
Base is e484cccb124224e013f34c97900e997f842aeda9; candidate is
86140c1a5a0b869b4ccfd8af5791e73453536d58. The runtime source at device checkout
2de8dd6 is identical to the tested candidate; later notes commits are documentation only.

Both controls retain ENABLE_VM_GML_PROFILER, disabled by default. Candidate caches
the Pocket profiler pointer per interpreter invocation and guards script enter/exit
calls when it is null. Script times remains on the new Debug page.

## Configuration and validated timing

Twelve new cases use GCC 16.2.0, port profile, native scripts enabled, 64-byte
function/loop alignment, BRAM interpreter, uncached framebuffer, 1,680-cycle
clock-read charge, fixed 800 stereo pairs/frame and quiet memory traffic.
Each sample starts with cold caches and contains three consecutive frames:
Undertale Flowey 2400–2402 and Deltarune dodge 3323–3325. Traced builds retain
VM/PCM instrumentation; timing builds omit it. Both kinds retain script profiling.
The table uses timing builds and the pinned simulated 100 MHz os25 clock.

| Timing sample | Base ms/frame | Candidate ms/frame | Change |
| --- | ---: | ---: | ---: |
| Undertale Flowey Speed | 15.965970 | 15.884230 | -0.512% |
| Deltarune dodge Speed | 84.629807 | 84.373247 | -0.303% |
| Deltarune dodge Accuracy | 183.760053 | 183.610650 | -0.081% |

The Accuracy timing gain is only 0.081%, versus 0.794% before the rebase; that
larger effect did not persist. All nine timing frames improve individually.
Traced Accuracy changes from 195.058507 to 193.342620 ms (-0.880%), illustrating
the instrumentation/layout sensitivity; timing builds supply the speed estimate.
Whole-frame results include compiler/layout
interactions and do not isolate the cost of the removed load and calls.

All twelve cases pass repeated QEMU capture agreement, same-binary RTL output
and memory checks, and corrupted-state negative controls. Six base/candidate and
six trace/timing comparisons match raw RGB555 pixels, stereo PCM and sample
counts: 36 frame pairs. All nine paired traced opcode/builtin counts match.
The validating report rechecks source, ELF, input and capture hashes.

Both generated loops still remove the per-instruction profiler load, retain one
null check per instruction, and fit the 14 KB application BRAM region. Undertale
loop sizes are 10,246/10,226 bytes; Deltarune sizes are 9,004/9,016. Disassembly
and exact counter values are preserved with the new evidence.

Fresh desktop ASan/UBSan menu smoke tests enable Script times from the new Debug
submenu, emit a script report, and separately toggle it on/off. There are no
sanitizer diagnostics with alignment/function checks and leak detection excluded.
The rebased WAD16/17 profiler fixture and strict port lint for both games passed
immediately before this rerun.

These sampled whole-frame differences include compiler/layout effects. The
harness substitutes OS/storage/allocator services and fixed audio; physical
Pocket milliseconds saved remain unmeasured. Traced means are retained separately
in the machine-readable report.

## Pocket rebuild

The [2026-10-11 device follow-up](2026-10-11-profiler-device-results.md) records
the subsequently uploaded Speed pair: dodge work improves 0.89% and the complete
route saves 0.88%. One independent pair does not establish repeatable variance.

The old 79ab365 card tree and ordinary objects were preserved before rebuilding.
The ordinary entries use candidate source. The paired builds use independent
Git exports in equal-length base308/fast308 directories and fresh objects, with
matching GCC/SDK settings. Equal-length inert report flags -DUT_PROFILER_BASE308
and -DUT_PROFILER_FAST308 distinguish appended reports; those macros have no
source usages. Both controls keep Script times compiled in.

The card contains Speed, Accuracy and no-drawing base/profiler entries for both
games. Start with Deltarune Benchmark speed base, then Deltarune Benchmark speed
profiler, keeping Script times off. The older prof experiment compiles profiling
out and is a separate control. Existing SD entries can remain because the copy
command omits --delete.

All six card ELFs have entry 0x10400000 and retain Profiler_createReport. All
non-save data-slot references and the 23-character filename limit pass validation.
All six game-data/texture/music hashes match the preserved 79ab365 card manifest.
No SD copy was performed; the completed tree is left ready for the user's pull.

## Evidence

Private build/profiler-off-308/ contains validated results.json, summary.json,
twelve final comparisons, exact cases, disassembly and menu smoke logs. The card
manifest, build logs, frozen source exports, preserved old card and build script
are in the port's ignored src/openfpga/out/experiments/profiler308-device/.

Base snapshot manifest SHA-256: f9b7bf50685f34abb79c8144859ab9f50cb38d89b23b30130e0ac3773b6f0315.

Candidate snapshot manifest SHA-256: 6110c986c53ad8aa4101fbac0c4c07dc8cfe33ef18dc5d7ac003492456dfa688.

CPU lock SHA-256: f06eead7ccd9be1c9892fe18c9cfee61318307ccedbe38b5771054612587a94c.

| Snapshot | Game/window | Mode | Kind | Exact CASE under experiments/cases/ |
| --- | --- | --- | --- | --- |
| profiler-off-base308 | undertale/flowey | speed | trace | profiler-off-base308-undertale-flowey-speed-trace-18bd01b1962681f8 |
| profiler-off-base308 | undertale/flowey | speed | timing | profiler-off-base308-undertale-flowey-speed-timing-92dc78162ed5651d |
| profiler-off-base308 | deltarune/dodge | speed | trace | profiler-off-base308-deltarune-dodge-speed-trace-040e58f575fd4b2a |
| profiler-off-base308 | deltarune/dodge | speed | timing | profiler-off-base308-deltarune-dodge-speed-timing-523e5ed20e6803ff |
| profiler-off-base308 | deltarune/dodge | accuracy | trace | profiler-off-base308-deltarune-dodge-accuracy-trace-bbcea0369150cbfe |
| profiler-off-base308 | deltarune/dodge | accuracy | timing | profiler-off-base308-deltarune-dodge-accuracy-timing-8c78204beaa56ea8 |
| profiler-off-fast308 | undertale/flowey | speed | trace | profiler-off-fast308-undertale-flowey-speed-trace-9219e8d9dfa5c197 |
| profiler-off-fast308 | undertale/flowey | speed | timing | profiler-off-fast308-undertale-flowey-speed-timing-2fb344e7e6ef9e65 |
| profiler-off-fast308 | deltarune/dodge | speed | trace | profiler-off-fast308-deltarune-dodge-speed-trace-4f4f13a7932fa2e7 |
| profiler-off-fast308 | deltarune/dodge | speed | timing | profiler-off-fast308-deltarune-dodge-speed-timing-9412faa8f6582823 |
| profiler-off-fast308 | deltarune/dodge | accuracy | trace | profiler-off-fast308-deltarune-dodge-accuracy-trace-ced8db1d97307670 |
| profiler-off-fast308 | deltarune/dodge | accuracy | timing | profiler-off-fast308-deltarune-dodge-accuracy-timing-df1b740f243fcd7d |
