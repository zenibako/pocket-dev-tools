# Isolated sprite probe (perf/mirrored-blend)

Pinned revision `3c2d37a22a194d1745a72e0dd9b9677e4bd6f8fc`. Deltarune Chapter 1, Speed, 40x40 selection, BRAM interpreter, quiet traffic. Compiler: `riscv64-unknown-elf-gcc (13.2.0-11ubuntu1+12) 13.2.0`. Renderer/GML profiling and VM tracing are disabled; independent stop/path hooks remain. All timings below are simulated at 100 MHz.

The current staged `swrSpriteCostProbe` is copied from the snapshot. It warms a sprite, then calls `Renderer_drawSprite` 2,000 times per stage in order 6,5,4,3,2,1,0,outside. The suite runs three times consecutively. Outside uses `(viewX - 10000, viewY + 60)`; inside uses `(viewX + 60, viewY + 60)`, frame 0 of the sprite. Audio top-ups are suppressed as in the original probe. This bypasses VM/GML dispatch.

The adapter enables only the probe’s compile-time stop/path gates while removing `SW_DRAW_PROFILE` and `ENABLE_VM_GML_PROFILER`. It replaces the probe’s two `nowNanos` calls around each batch with exact MMIO-counter interval hooks. Setup, output formatting, game-state/pixel validation and logs are outside each interval. The loop, call/return path and small boundary overhead remain measured; boundary overhead is amortized over 2,000 calls. No kernel clock/ecall cost is charged.

State/pixel hashing and UART logs run between batches, unlike the original device probe. They can evict cache contents and change predictor history before the next batch. This is an additional comparability limit even though those clocks are excluded. The observed refill counts and three batch means retain its effect rather than assuming it is absent.

## Per-call cost

| Stage | Cycles/call | µs/call | Three batch means (cycles/call) | Retired/call | Native CPI | I block/call | D block/call | I/D refills (6,000 calls) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| whole inside draw | 5677.339 | 56.773 | 5677.355, 5677.328, 5677.333 | 4078.015 | 1.392 | 0.070 | 1.047 | 21/153 |
| renderer door | 76.253 | 0.763 | 76.281, 76.243, 76.235 | 60.014 | 1.271 | 0.008 | 0.163 | 1/18 |
| texture found | 243.479 | 2.435 | 243.511, 243.467, 243.460 | 192.014 | 1.268 | 0.009 | 0.331 | 2/42 |
| drawing entered | 449.562 | 4.496 | 437.593, 455.559, 455.534 | 321.014 | 1.400 | 0.045 | 0.399 | 12/48 |
| clipped | 594.237 | 5.942 | 593.557, 594.581, 594.573 | 410.014 | 1.449 | 0.048 | 0.397 | 12/48 |
| setup complete | 771.258 | 7.713 | 773.592, 765.595, 774.587 | 529.014 | 1.458 | 0.059 | 0.397 | 15/48 |
| held layers flushed | 1010.556 | 10.106 | 1013.385, 1005.163, 1013.121 | 611.015 | 1.654 | 0.057 | 0.009 | 10/1 |
| outside view | 498.607 | 4.986 | 486.700, 504.557, 504.564 | 365.019 | 1.366 | 0.084 | 0.407 | 24/48 |


The three values are consecutive batch averages in a deterministic model, not physical-device variance or a per-call latency distribution. The first suite follows restoration with cold CPU caches, but the original warm draw occurs before its first measured batch.

## Pipeline observations

Values are cycles per call, averaged over all three batches. Rows overlap and can coexist with retirement; they must not be summed as causal lost cycles. Canonical retirement uses the ctrl5 CommitService event. Source dependency categories identify the waiting operand’s producer.

| Observation | whole inside draw | renderer door | texture found | drawing entered | clipped | setup complete | held layers flushed | outside view |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| raw_dependency | 535.384 | 9.004 | 45.010 | 55.004 | 74.010 | 97.008 | 114.995 | 58.005 |
| load_dependency | 276.386 | 9.004 | 40.008 | 40.008 | 59.009 | 79.008 | 96.999 | 43.008 |
| multiply_dependency | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| fp_dependency | 8.998 | 0.000 | 0.000 | 8.995 | 8.998 | 8.998 | 8.995 | 8.995 |
| fp_reservation | 4.998 | 0.000 | 0.000 | 4.998 | 4.998 | 4.998 | 5.000 | 4.998 |
| execute_freeze | 61.007 | 6.006 | 6.006 | 61.007 | 61.007 | 61.007 | 61.005 | 64.010 |
| integer_divider | 6.000 | 0.000 | 0.000 | 6.000 | 6.000 | 6.000 | 6.000 | 6.000 |
| fp_divider | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| fp_sqrt | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| fp_to_int | 8.000 | 0.000 | 0.000 | 8.000 | 8.000 | 8.000 | 8.000 | 8.000 |
| int_to_fp | 48.002 | 6.002 | 6.002 | 48.002 | 48.002 | 48.002 | 48.000 | 51.005 |
| store_buffer_wait | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| uncached_io | 0.005 | 0.005 | 0.005 | 0.005 | 0.005 | 0.005 | 0.005 | 0.005 |
| csr | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| atomic | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| branch_recovery | 329.365 | 0.035 | 0.065 | 8.728 | 24.736 | 40.418 | 145.458 | 8.733 |


Disjoint no-retirement accounting follows the same explicit priority as the [full-frame pipeline report](../cacheprobe/PIPELINE-RESULTS.md): execute freeze, D wait, store-buffer wait, RAW, FP reservation, flush/fence interlocks, I block, branch recovery, then residual issue/candidate/frontend clocks. This assigns overlaps for presentation; it does not predict the saving from removing a source.

| Exclusive clock category | whole inside draw | renderer door | texture found | drawing entered | clipped | setup complete | held layers flushed | outside view |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| retirement | 4078.015 | 60.014 | 192.014 | 321.014 | 410.014 | 529.014 | 611.015 | 365.019 |
| execute_freeze | 61.007 | 6.006 | 6.006 | 61.007 | 61.007 | 61.007 | 61.005 | 64.010 |
| d_block | 1.047 | 0.163 | 0.331 | 0.399 | 0.397 | 0.397 | 0.009 | 0.404 |
| store_buffer_wait | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| raw_dependency | 145.142 | 2.002 | 12.012 | 12.011 | 22.011 | 30.012 | 39.342 | 13.009 |
| fp_reservation | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| flush_interlock | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| fence_interlock | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| i_block | 0.041 | 0.008 | 0.009 | 0.019 | 0.022 | 0.026 | 0.041 | 0.043 |
| branch_recovery | 223.581 | 0.023 | 0.046 | 6.043 | 17.716 | 30.062 | 103.092 | 6.046 |
| dispatch_without_retirement | 1079.493 | 8.032 | 33.053 | 48.395 | 72.730 | 100.398 | 168.045 | 49.399 |
| candidate_other | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| frontend_or_pipeline_empty | 89.014 | 0.003 | 0.008 | 0.674 | 10.341 | 20.340 | 28.008 | 0.676 |


## Refill and branch distributions

| Stage | Cache | Refills | Mean cycles | Min | p50 | p90 | p99 | Max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| whole inside draw | I | 21 | 85.43 | 49 | 69 | 151 | 158 | 158 |
| whole inside draw | D | 153 | 56.45 | 49 | 54 | 71 | 95 | 98 |
| renderer door | I | 1 | 54.00 | 54 | 54 | 54 | 54 | 54 |
| renderer door | D | 18 | 54.22 | 52 | 54 | 54 | 54 | 64 |
| texture found | I | 2 | 88.00 | 66 | 66 | 66 | 66 | 110 |
| texture found | D | 42 | 54.86 | 52 | 54 | 54 | 70 | 70 |
| drawing entered | I | 12 | 80.83 | 49 | 54 | 122 | 122 | 129 |
| drawing entered | D | 48 | 56.46 | 52 | 54 | 70 | 71 | 79 |
| clipped | I | 12 | 82.08 | 49 | 54 | 122 | 122 | 129 |
| clipped | D | 48 | 56.21 | 52 | 54 | 70 | 71 | 71 |
| setup complete | I | 15 | 82.47 | 54 | 69 | 122 | 122 | 129 |
| setup complete | D | 48 | 56.23 | 52 | 54 | 69 | 71 | 76 |
| held layers flushed | I | 10 | 79.90 | 52 | 54 | 112 | 112 | 155 |
| held layers flushed | D | 1 | 52.00 | 52 | 52 | 52 | 52 | 52 |
| outside view | I | 24 | 72.58 | 49 | 69 | 98 | 106 | 150 |
| outside view | D | 48 | 57.17 | 49 | 54 | 70 | 100 | 101 |


| Stage | Branches/call | Mispredicts/call | Recovery mean cycles | p50 | p90 | p99 | Max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| whole inside draw | 634.002 | 56.893 | 5.79 | 6 | 7 | 7 | 15 |
| renderer door | 9.002 | 0.006 | 5.92 | 6 | 6 | 6 | 6 |
| texture found | 36.002 | 0.011 | 5.78 | 6 | 6 | 7 | 7 |
| drawing entered | 41.002 | 1.344 | 6.49 | 6 | 7 | 7 | 7 |
| clipped | 67.002 | 4.012 | 6.17 | 6 | 7 | 7 | 7 |
| setup complete | 89.002 | 6.681 | 6.05 | 6 | 6 | 7 | 7 |
| held layers flushed | 114.002 | 23.687 | 6.14 | 6 | 7 | 7 | 9 |
| outside view | 48.002 | 1.345 | 6.50 | 6 | 7 | 7 | 8 |


Refill latency is accepted AR through RLAST, inclusive, including speculative prefetch. Branch recovery is a firing direction/target correction through dispatch of its corrected target and includes overlapping waits. Full histograms and raw event hashes remain in private results.

## Culling code

### renderer door

| Function | Retired/call | RAW/call | Load dependency/call | FP dependency/call | Multiply dependency/call | Dispatch blocked/call |
| --- | --- | --- | --- | --- | --- | --- |
| SWRenderer_drawSprite | 32.000 | 0.001 | 0.001 | 0.000 | 0.000 | 0.001 |
| swrSpriteCostProbe | 28.002 | 9.002 | 9.002 | 0.000 | 0.000 | 15.142 |
| sprite_probe_end | 0.007 | 0.000 | 0.000 | 0.000 | 0.000 | 0.003 |
| sprite_probe_begin | 0.006 | 0.000 | 0.000 | 0.000 | 0.000 | 0.003 |


### drawing entered

| Function | Retired/call | RAW/call | Load dependency/call | FP dependency/call | Multiply dependency/call | Dispatch blocked/call |
| --- | --- | --- | --- | --- | --- | --- |
| SWRenderer_drawSprite | 115.000 | 15.999 | 8.003 | 5.996 | 0.000 | 39.079 |
| swrDrawSprite | 71.000 | 3.998 | 0.000 | 2.998 | 0.000 | 35.023 |
| swrTextureForItem | 61.000 | 20.003 | 17.002 | 0.000 | 0.000 | 20.080 |
| swrTexturePackGetSize | 32.000 | 6.001 | 6.001 | 0.000 | 0.000 | 6.024 |
| swrSpriteCostProbe | 28.002 | 9.002 | 9.002 | 0.000 | 0.000 | 15.140 |
| swrDrawSpriteInternal | 14.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| sprite_probe_end | 0.007 | 0.000 | 0.000 | 0.000 | 0.000 | 0.003 |
| sprite_probe_begin | 0.006 | 0.000 | 0.000 | 0.000 | 0.000 | 0.003 |


### outside view

| Function | Retired/call | RAW/call | Load dependency/call | FP dependency/call | Multiply dependency/call | Dispatch blocked/call |
| --- | --- | --- | --- | --- | --- | --- |
| SWRenderer_drawSprite | 115.000 | 15.999 | 8.002 | 5.997 | 0.000 | 42.045 |
| swrDrawSprite | 71.000 | 3.998 | 0.000 | 2.998 | 0.000 | 34.995 |
| swrTextureForItem | 61.000 | 20.004 | 17.002 | 0.000 | 0.000 | 20.080 |
| swrDrawSpriteInternal | 56.000 | 4.000 | 4.000 | 0.000 | 0.000 | 4.000 |
| swrTexturePackGetSize | 32.000 | 6.001 | 6.001 | 0.000 | 0.000 | 6.024 |
| swrSpriteCostProbe | 30.006 | 8.002 | 8.002 | 0.000 | 0.000 | 14.202 |
| sprite_probe_end | 0.007 | 0.000 | 0.000 | 0.000 | 0.000 | 0.003 |
| sprite_probe_begin | 0.006 | 0.000 | 0.000 | 0.000 | 0.000 | 0.003 |


## Result and comparability

The outside-view call costs 498.607 cycles (4.986 µs), versus 76.253 cycles at the renderer door. The difference is 422.355 cycles. Outside native CPI is 1.366. Cache blocking occupies 0.097% of its clocks. See the counters above for the actual waits; broad full-frame shares were not used to infer them.

The door-to-outside difference contains 305.004 additional retired native instructions per call. Refills do not dominate this warmed repeated sprite path in this binary. The physical-device hypothesis remains undecided because the simulated timing is substantially smaller.

The device’s reported 19.87/19.56 µs results were from f42a23c with profiling compiled but per-draw timing/notes disabled at runtime. This requested build removes that profiling code entirely and uses a newer pinned branch revision. The same call geometry and 40×40 fallback are recorded, but exact device compiler/link layout and v0.7 CPU/runtime parity are unverified. The simulated numbers therefore reproduce the workload under these stated conditions, not a proven match to the physical 19.9 µs result.

The checkpoint is taken immediately before benchmark frame 3323, not after the entire 3,600-frame device benchmark. Selection `40x40` explicitly bypasses the newer last-grid-sprite preference to use the old probe’s fallback search. Renderer geometry is recorded below. The SDK’s 64-byte function/loop alignment is applied; native scripts follow the port build. Firmware services, allocator, virtual file access and deterministic game clock are harness substitutions. The cached framebuffer matters for drawn stages; culling writes no pixels. Audio mixing and physical SD/display scheduling are outside the probe. The CPU/cache RTL and parameters are unchanged.

## Verification and source references

Two captures have identical RAM/stack checkpoints, all 24 oracles and raw pixel/PCM artifacts. The regular replay and passive-observer replay must agree exactly on cycles and oracles; disabled and corrupted-oracle controls are hash-verified below. Producer hazard and complete freeze-source checks run on every observer sample. Frozen baseline inputs and earlier reports are retained. Only independently copied harness directories are mounted in Docker.

The active performance checkout advanced independently during this experiment; this task read Git objects for the pinned snapshot and issued no write or deployment command there.

Source revision: `3c2d37a22a194d1745a72e0dd9b9677e4bd6f8fc`; source files `src/sw/sw_renderer.c:swrSpriteCostProbe`, `src/sw/sw_call_notes.h:SWR_PROBE_STOP`, `src/sw/sw_drawing.c:swrDrawSpriteInternal`. Generated adaptations are recorded in `build.json`; their tooling is [build.py](build.py), [runtime.c](runtime.c) and [sprite_probe.py](../sprite_probe.py). Counter definitions and pinned RTL source references are in [cacheprobe/README.md](../cacheprobe/README.md).

Observer `0711991b745113db`; ELF SHA-256 `947fa76e3eda276e09e8c7dd00e52f15cc3ca66b5ea70a7364059659e0c4644b`; profile result SHA-256 `016ac606ff14eff5bf19a0463e1d55e59f98206b6ed2ae583820d04298249943`.

| Control | Result SHA-256 |
| --- | --- |
| observer disabled, identical | b1d3369aacf2fba4258c2062158ded5468556d1a48b3ae9d9053d13dcf7f9d33 |
| corrupted oracle rejected | cb1d594a1a679a977d57f6e643eacd311cf908b1fc27571d7f99498408cbc947 |


Outside-view instruction mix (retired instructions per call):

| Instruction class | Retired/call |
| --- | --- |
| branch_jump | 48.002 |
| fp_compute | 53.000 |
| integer_divide_rem | 1.000 |
| load | 105.005 |
| other_integer | 106.007 |
| store | 52.005 |


The outside interval has 133.589 clocks per call without retirement. Its largest exclusive non-retirement categories are execute_freeze: 64.010 cycles/call, dispatch_without_retirement: 49.399 cycles/call, raw_dependency: 13.009 cycles/call, branch_recovery: 6.046 cycles/call. These are observations of this binary; they do not explain the remaining device/simulation timing gap.

Geometry fields: sample, stage, sprite, width, height, viewX/Y/W/H, portW/H, scaleX/Y IEEE-754 bits.

```text
SPRITECONFIG 0 6 42 40 40 0 0 320 240 320 240 3f000000 3f000000
SPRITECONFIG 1 5 42 40 40 0 0 320 240 320 240 3f000000 3f000000
SPRITECONFIG 2 4 42 40 40 0 0 320 240 320 240 3f000000 3f000000
SPRITECONFIG 3 3 42 40 40 0 0 320 240 320 240 3f000000 3f000000
SPRITECONFIG 4 2 42 40 40 0 0 320 240 320 240 3f000000 3f000000
SPRITECONFIG 5 1 42 40 40 0 0 320 240 320 240 3f000000 3f000000
SPRITECONFIG 6 0 42 40 40 0 0 320 240 320 240 3f000000 3f000000
SPRITECONFIG 7 7 42 40 40 0 0 320 240 320 240 3f000000 3f000000
```
