# Detailed Pocket capture and controlled runs — 2026-10-18

The new baseline and palette packages extend the [working diagnostic capture](CAPTURE-PERSISTENCE.md) after the [first physical Trailhead comparison](POCKET-TRAILHEAD-20261018.md). They add correlated phase/GC/audio evidence and controlled-input routes. No new optimization is promoted.

The newer [movement and grapple package](POCKET-GRAPPLE-CONTROLLED.md) replaces the Celeste menu preset with scripted movement. This report preserves the earlier stationary package and its evidence.

## Package and use

Local combined ZIP: `experiments/pico8-sources/detailed-controlled-20261018-r1/pico8pocket-capture-controlled-ab.zip`.

SHA-256: `59d9d19294007459db5fb9ad01394fde09f19b5479de097cf0c9e6c2702c4198`.

Extract at the SD root, replacing the prior capture package files. Entries remain **PICO-8 capture baseline** and **PICO-8 capture palette**. Existing cartridges, settings, saves and reports are used; none are bundled. The ZIP contains `BENCHMARK.md` with full instructions.

Open the in-core menu with Select:

- **L AUTO:** run the known-cart preset. Celeste 2 recreates stationary Trailhead, warms 100 logical frames and measures 300; Moss Moss runs the retained seed-7 gameplay route, warms 180 and measures 300. Both draw every frame. Unsupported content, incorrect seeds and scene mismatches are refused.
- **R DETAIL:** toggle detailed timing/audio accounting in the same executable, default ON. Repeat the same AUTO route with OFF to measure enabled collection cost on Pocket.
- **Y MANUAL30S:** retain ordinary adaptive gameplay capture with two-second warmup and thirty-second recording.

AUTO uses a fresh VM with final Lua hash seed `0x5eed1234`. The original game remains paused and keeps its persistence hooks; the benchmark VM has none. Scripted gameplay buttons also replace mid-frame live inputs. Select and native Memory/sleep requests cancel and restore the original. The final-frame Select race found in review is reproduced and fixed for both games.

ARM/REC border indicators and the release-plus-fresh-Select result screen remain. AUTO measures fixed logical-frame counts rather than a fixed wall duration. For comparison, take three AUTO runs per game/core with DETAIL ON; use matching OFF repeats for overhead controls. Keep audio/display settings matched. Exit normally through the Analogue menu, then retrieve both `/Saves/pico8/common/p8pcapbase.bench` and `p8pcapleaf.bench`.

## Attribution and limits

Per-frame data separates update/draw callback execution, GC by callback phase and exclusive incremental/full/emergency kind, remaining runtime work, outer audio pumping and presentation. GC is removed from ordinary phase time and counted once. GC-kind columns are another view of those same intervals. Heap/debt values, entry counts, validity flags, rendered/skipped/written stereo pairs and queue observations accompany the timings. Post-pump queue occupancy is an estimate, not a second hardware snapshot.

The slowest 16 frames retain their own component values and flags; independent maxima are never paired. Disabled/invalid attribution is explicit and excluded from detailed aggregates. Callback phases persist across `flip()` yields, but elapsed segments close at every runtime return, excluding menu/pacing gaps. Production longjmp/error handling uses explicit cleanup, not C++ destructor assumptions.

**Moss draws inside update.** Its UPDATE includes rendering; zero DRAW is expected. Coarse timers cannot separate its Lua drawing algorithm from other update work. Region elapsed times include interrupts and instrumentation and do not establish pure CPU self time.

Collection adds no per-opcode/API/allocation timers or formatting, sorting, report I/O or collector allocations while recording. The fixed buffer holds 4096 samples (573480 native bytes); paused export uses a bounded 32768-byte report buffer. Existing complete `P8PBENCH1` journals remain append-compatible. Full, unknown or incomplete journals are refused.

The target clock callback is an 8-byte, three-instruction read of the pinned hardware cycle register, with no timer syscall. Raw unsigned deltas convert to microseconds once per step; main rejects spans reaching one counter wrap (about 47.7 seconds at 90 MHz). Integer partition rounding can lose a few microseconds.

Controlled inputs, seed, warmup and draw cadence do not fix allocator addresses, CPU caches, OS scheduling or live audio consumption. The public HAL has no portable queue-clear API. Boundary checks and audio counts provide evidence about drift; they do not prove identical live whole-system execution. Fixed-audio validation below is separate from normal hardware audio.

## Validation

Baseline passes ten native suites, the eighteen original/manual/controlled/failure app modes and targeted post-fix completion/cancellation coverage, including new final-boundary Celeste/Moss modes 18/19. Candidate passes the same ten suites and modes 0–17, then post-port normal completion, detail-off, Select/native cancellation and both final-boundary cases. Actual-cart app tests assert exactly 300 samples/draws/presents, divisor 1, correct seeds and indices, stable scripted inputs at service polls, and the original game's unchanged framebuffer at benchmark discard. Synthetic cartdata tests verify controlled dirty data cannot reach the original persistence hooks.

Focused timing/export/runtime/audio and controlled app tests pass ASan/UBSan with production `LUA_USE_LONGJMP`. Existing signed fixed-point shift behavior and process-lifetime VM pools are excluded as recorded in the private reports. Compile-disabled timing tests pass. Mutations removing phase hooks, leaking mid-frame physical buttons, shifting the Moss RNG or corrupting input fingerprints are rejected. Independent source review approves the timing, controlled lifecycle and palette transposition after the cancellation fix.

Forty alternating OFF/ON pairs per cart in the baseline (80 runs/cart) agree on pixel/palette/fixed-PCM/input checksums and world fields. Ten OFF/ON pairs per cart in the candidate (20 runs/cart) match the baseline references. Separate raw-channel comparisons retain all 300 measured frames for each game, variant and detail mode; their outcome is recorded in `raw-validation.json`.

Native collector controls show the following differences of medians over 300 runtime steps:

| Cart | OFF runtime | ON runtime | Change |
| --- | ---: | ---: | ---: |
| Trailhead | 29.8705 ms | 29.885 ms | +0.049% |
| Moss Moss | 40.571 ms | 40.692 ms | +0.298% |

Run ranges overlap; these are small host-native observations, not a robust overhead bound or Pocket estimate. They measure enabled runtime collection in one binary with direct fixed synthesis, excluding frontend buffering/platform audio counters/display. OFF does not remove compiled hook/layout effects relative to older images. Full physical overhead remains for the supplied ON/OFF control.

## Production provenance

| Variant | Signed source | Production ELF SHA-256 | BRAM bytes / 14336 |
| --- | --- | --- | ---: |
| Baseline | `deae07a95d3e1d66b476c2dda9bc2eef5a2febb5` | `9e0add9a2313429359237dcdb0e698767f24b985a2e8cc354dfd20f0e8f15cd7` | 14182 |
| Palette | `a26577f8b0a5aab56eac3f89002d7c17bbdb9f20` | `1a3534a5cb040711259216e80f2938c62632920ba955a939a5dd21f39a53db2b` | 14322 |

Both final production links and APF/package checks pass. Existing VM GC call policy remains three direct forced-step calls and one wrapper call; ordinary C-call helper sizes remain unchanged. VM size increases by two bytes and GC bodies include diagnostic guards, so the older image's timing/layout is not reused. The final instructions-only relink preserves both pre-correction BRAM byte streams exactly.

All 531 copied dependency files are inventoried. Only `lgc.c`, `lstate.c`, `lstate.h` differ, reproduced independently by the two new tracked patches. Shared diagnostic files match between variants; runtime structure fields match despite the candidate's existing private-header location. Serialized fixed state, original audio algorithm and original palette leaf remain unchanged. Every new source commit has a verified GPG signature. The active source remains clean at its original revision.

The final ZIP has exact source-identified ELF bytes, short runtime-bound filenames, distinct report names, slot8's original position/address/capacity and explicit initialization flags. It contains no carts/settings/save/report payloads. OS/FPGA/loader hashes match the pinned a58aacd release. A host test using the exact pinned kernel filename-resolution code rejects the retained old long-name package and accepts both new cores. This checks bindings, not physical boot or SD flush.

Private source worktrees, reports, raw channels, source/target audits and manifests are preserved under `experiments/pico8-sources/detailed-controlled-20261018-r1/`. No SD deployment, remote push or PR was performed. Physical Pocket capture timing, live audio behavior and new-package persistence still require the user's run.
