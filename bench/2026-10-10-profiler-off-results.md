# Script times disabled-state optimization, 2026-10-10

The candidate retains Script times in the debug menu and reduces its disabled-state work. All nine measured timing frames improve: 0.51% in Undertale Flowey Speed, 0.30% in Deltarune dodge Speed, and 0.79% in Deltarune dodge Accuracy. This supports a device comparison of the feature-preserving candidate. These are simulated results; the Pocket card tree remains at the earlier `79ab365` build.

## Source and implementation

Baseline is `79ab365e92fe957280e42d518e2a9fbb3f8796dd`, based on Pocket `fork/main` `05b0eef`. Candidate is `0f4afe154180a71a3695f7aae4730d949720e6e5` on the dedicated `perf/draw-cost-experiments` branch/worktree. The [earlier profiler compile-out screen](2026-10-10-remaining-experiments.md) uses older source and removes diagnostics; its timings are not this comparison's controls.

With `UT_FAST_LOOP`, the interpreter reads the profiler pointer once per invocation. Pocket applies menu toggles between frames, before `Runner_step`; nested scripts and audio service hooks cannot free it. Other platforms retain the per-instruction pointer read. Interpreted/native script and code boundaries now guard enter/exit calls when the pointer is null, as builtin boundaries already do. Allocation, enabled counting, exclusive accounting, reports/reset, and menu behavior remain available. Profiling is off by default.

The [source note](../../butterscotch-draw-experiments/src/openfpga/docs/2026-10-10-profiler-off-path.md) records the lifetime contract and fixture command. Generated RISC-V timing loops retain the pointer in a saved register. Undertale removes the context load at each loop iteration (10,246 → 10,226 bytes); Deltarune does likewise (9,004 → 9,016 bytes). Stack frames remain 112 and 400 bytes respectively. Both single-copy loops stay at `0x4000`, below the 14 KB application BRAM limit. The per-instruction null branch remains.

## Method and validation

The comparison follows [the architecture](../ARCHITECTURE.md), [full-frame replay](../fullframe/README.md), and [revision experiments](README.md). Independent immutable snapshots are `profiler-off-base05` and `profiler-off-fast05`; names have equal lengths to limit incidental source-path string/layout changes. Their manifest SHA-256 values are respectively `2e46f966149012cd3ba6b4ace438130fbe44f490c9cbc5d874f78c621467bb54` and `d2ec0032d70a348048f934f1d69bf47bae41b3000bbbf3127559557437783370`.

All twelve cases use GCC 16.2.0, port profile, `-O2`, 64-byte function/loop alignment, native scripts enabled, a BRAM interpreter, uncached framebuffer, quiet traffic, fixed 800 stereo sample pairs/frame, and the declared 1,680-cycle clock-read cost. They retain `ENABLE_VM_GML_PROFILER`, share adapter/launcher hashes, and retain the same CPU lock. Each replay starts with cold CPU caches at a restored checkpoint; later frames carry cache state forward. Windows are Undertale Flowey 2400–2402 and Deltarune Chapter 1 dodge 3323–3325, seed 7 with fresh volatile saves.

- All twelve ELFs have reproducible two-run QEMU captures and pass same-binary RTL frame/output and memory oracles.
- All twelve corrupted-state controls are rejected.
- Six base/candidate and six trace/timing comparisons match raw RGB555, raw PCM and sample counts: 36 frame pairs.
- All nine traced base/candidate frame opcode/builtin counts match. Both Deltarune modes execute 6,195/6,680/6,194 opcodes and 53/59/54 builtins in the sampled frames; Undertale executes 1,181/1,183/1,198 and 17/17/17.
- The asset-free profiler fixture passes under ASan/UBSan for baseline, candidate Pocket loop, and candidate generic loop. It checks WAD16/17 nested exclusive counts/calls, native success/fallback, reports/reset, repeated enable/disable, off/on/off between executions, and balanced frames. Alignment/function sanitizer checks and leak detection are disabled; no runtime sanitizer diagnostics occur.
- Strict port lint passes for both games. Original frozen-input verification remains green for all 1,631 files; revision cases verify 1,644 base and 1,645 candidate files.

## Timing results

Timing builds omit the harness VM tracing hooks and in-loop PCM hashing. Traced builds validate PCM/execution. Both retain the GML profiler feature. Negative deltas mean faster; means cover three frames at the pinned simulated 100 MHz clock.

| Window / mode | Base ms/frame | Candidate ms/frame | Change ms | Change |
| --- | ---: | ---: | ---: | ---: |
| Undertale Flowey / Speed | 15.806370 | 15.725053 | -0.081317 | -0.514% |
| Deltarune dodge / Speed | 84.564633 | 84.314053 | -0.250580 | -0.296% |
| Deltarune dodge / Accuracy | 184.272107 | 182.808207 | -1.463900 | -0.794% |

All nine timing frames improve individually. Saved cycles are 9,775/6,969/7,651 for Undertale Speed, 27,290/24,384/23,500 for Deltarune Speed, and 144,769/151,032/143,369 for Deltarune Accuracy.

Tracing changes register allocation, cache use and layout. Its means are 17.831113 → 17.824720 ms for Undertale, 94.331117 → 94.384270 ms for Deltarune Speed, and 193.886507 → 194.528273 ms for Deltarune Accuracy. Deltarune's traced direction reverses the timing result. Use timing builds for the performance estimate; the whole-frame deltas include compiler/layout effects and do not isolate the exact cost of the removed load or calls.

## Harness completion correction

The initial unchanged Undertale trace control completed every frame check but stopped at the success text with eight accepted SDRAM writes pending (`WCONF exp_fifo=8`). Its original case/log is preserved as `profiler-off-base05-undertale-flowey-speed-trace-0b47adf161ba9d52`.

Signed harness commit `11c16f3` waits for the complete success line and drains accepted write queues before the verdict. All memory checks stay enabled. A fresh unchanged trace control produces exactly the same frame cycles (1,822,306 / 1,760,904 / 1,766,124), passes with empty queues, and rejects corrupted state. Its control evidence is `build/profiler-off-05/write-drain-control.json`. The superseded original Deltarune replay was stopped and retained. Duplicate simulator-cache builders failed during regeneration; the final simulator was rebuilt once with two workers and its hashes are validated in every final case.

## Evidence and reproduction

Private evidence is under `build/profiler-off-05/`: validating `results.json`, `summary.json`, twelve output comparisons, `cases.json`, loop disassemblies/codegen notes, and three preserved desktop fixture binaries/logs. Each CASE retains revision/source/ELF hashes, flags, repeat captures, prepared images, RTL logs/metadata and negative controls.

Export new equal-length snapshot names when repeating this screen. The run configuration is:

```sh
python3 experiments.py run --snapshot SNAPSHOT --game GAME --window WINDOW \
  --mode MODE --kind both --profile port --native enabled \
  --compiler /opt/homebrew/bin/riscv64-elf-gcc --alignment --variant bram \
  --framebuffer uncached --clock-cost 1680 --audio fixed --traffic quiet
python3 experiments.py replay --case CASE --negative
python3 experiments.py compare --baseline BASE_CASE --candidate FAST_CASE --output COMPARISON.json
python3 experiments.py report --cases CASES --output RESULTS.json
```

Exact CASE names follow; their absolute paths are retained in the private `cases.json`.

| Source | Game / mode | Kind | CASE |
| --- | --- | --- | --- |
| base | undertale / speed | trace | `profiler-off-base05-undertale-flowey-speed-trace-c6c5f702a4cb0199` |
| base | undertale / speed | timing | `profiler-off-base05-undertale-flowey-speed-timing-1065b5953fc63bea` |
| base | deltarune / speed | trace | `profiler-off-base05-deltarune-dodge-speed-trace-6dc2dee967ec63b6` |
| base | deltarune / speed | timing | `profiler-off-base05-deltarune-dodge-speed-timing-8982550d8c027ac5` |
| base | deltarune / accuracy | trace | `profiler-off-base05-deltarune-dodge-accuracy-trace-433abad2b4954fc6` |
| base | deltarune / accuracy | timing | `profiler-off-base05-deltarune-dodge-accuracy-timing-6c6ac0b0cac63ba6` |
| candidate | undertale / speed | trace | `profiler-off-fast05-undertale-flowey-speed-trace-ca9a3a3f6cbfa4d1` |
| candidate | undertale / speed | timing | `profiler-off-fast05-undertale-flowey-speed-timing-7b04c53fc814b9be` |
| candidate | deltarune / speed | trace | `profiler-off-fast05-deltarune-dodge-speed-trace-cc66dc19abd0d9d5` |
| candidate | deltarune / speed | timing | `profiler-off-fast05-deltarune-dodge-speed-timing-37a68000cced2462` |
| candidate | deltarune / accuracy | trace | `profiler-off-fast05-deltarune-dodge-accuracy-trace-a95b2c3101d4d92b` |
| candidate | deltarune / accuracy | timing | `profiler-off-fast05-deltarune-dodge-accuracy-timing-463fa9f10295a1be` |

No device build, SD write or physical performance result is part of this pass. The harness substitutes allocator, storage/platform services and hardware audio; fixed audio and declared clock cost are assumptions. Coverage consists of two game windows and three game/mode combinations. The next device build should preserve the previous base as a control before replacing card entries.
