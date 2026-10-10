# Frozen f1d8542 pipeline and cache profile (2026-10-10)

Simulated 100 MHz os25; Speed, SDRAM, quiet; four three-frame windows, each traced and timing. The original baseline and the earlier [cache report](RESULTS.md) are preserved. No CPU parameter was changed.

The user reports that placing sixteen sprite-draw functions together (14.7 KB) on the Pocket changed the probe from 19.87 to 19.56 µs and changed no section frame time. That experiment does not support conflicts among those functions as the explanation. These full-frame counters investigate other causes; they do not isolate that same device probe.

## Reading the counters

Retired instructions use `PrivilegedPlugin_logic_harts_0_commitMask`, the ctrl5 CommitService event used by the optional hardware instruction counter. The older cache observer’s ctrl4 whitebox commit decision is preserved for compatibility and is not the retirement count used for CPI here. UOP IDs associate dispatched PCs and decompressed instructions with retirement. CPI is native RISC-V cycles per retired instruction, not cycles per VM instruction.

All cause counters overlap. A frontend or dispatch wait can coexist with an older retirement. The no-retirement subsets and full mask histograms in private `results.json` retain that distinction. A no-retirement cycle is a pipeline observation, not proof that removing one asserted signal saves that cycle. Refill bus latency sums and branch recovery lengths are not additive CPU stall totals.

## Undertale

| Window | Build | Frame | Cycles | Retired | CPI | I block cycles | D block cycles | I/D union | I refills | D refills |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| flowey | timing | 2400 | 1273699 | 645527 | 1.973 | 109864 | 108364 | 17.07% | 3375 | 4403 |
| flowey | timing | 2401 | 1261817 | 645681 | 1.954 | 104823 | 111820 | 17.09% | 3205 | 4134 |
| flowey | timing | 2402 | 1266096 | 648516 | 1.952 | 105361 | 112335 | 17.13% | 3229 | 4141 |
| flowey | trace | 2400 | 1491368 | 807705 | 1.846 | 115396 | 108180 | 14.89% | 3528 | 4403 |
| flowey | trace | 2401 | 1480170 | 808105 | 1.832 | 110606 | 111711 | 14.92% | 3363 | 4137 |
| flowey | trace | 2402 | 1486319 | 812785 | 1.829 | 111331 | 112350 | 14.95% | 3380 | 4144 |


Pooled refill latency in cycles, accepted AR through accepted RLAST inclusive. Full distributions are retained in the private results.

| Window | Build | Cache | Count | Mean | Min | p50 | p90 | p99 | Max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| flowey | timing | I | 9809 | 78.56 | 22 | 69 | 107 | 174 | 276 |
| flowey | timing | D | 12678 | 66.66 | 49 | 52 | 100 | 169 | 222 |
| flowey | trace | I | 10271 | 78.95 | 49 | 69 | 108 | 187 | 266 |
| flowey | trace | D | 12684 | 66.74 | 49 | 52 | 101 | 170 | 212 |


## Deltarune Chapter 1

| Window | Build | Frame | Cycles | Retired | CPI | I block cycles | D block cycles | I/D union | I refills | D refills |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dodge | timing | 3323 | 16253087 | 9012522 | 1.803 | 921864 | 690546 | 9.91% | 30459 | 17307 |
| dodge | timing | 3324 | 17345350 | 9612022 | 1.805 | 965914 | 774487 | 10.02% | 31811 | 19492 |
| dodge | timing | 3325 | 16161063 | 8947357 | 1.806 | 925536 | 762493 | 10.43% | 30584 | 18547 |
| dodge | trace | 3323 | 18598875 | 11259471 | 1.652 | 787283 | 652246 | 7.72% | 27460 | 16605 |
| dodge | trace | 3324 | 19749882 | 11886676 | 1.662 | 835870 | 735467 | 7.94% | 29007 | 18786 |
| dodge | trace | 3325 | 18494729 | 11173325 | 1.655 | 788501 | 721855 | 8.15% | 27522 | 17803 |
| field | timing | 2800 | 9972504 | 5555067 | 1.795 | 622926 | 372211 | 9.97% | 20824 | 9574 |
| field | timing | 2801 | 9945983 | 5547353 | 1.793 | 614772 | 371378 | 9.90% | 20571 | 9523 |
| field | timing | 2802 | 9932403 | 5544079 | 1.792 | 612057 | 371519 | 9.89% | 20523 | 9485 |
| field | trace | 2800 | 12104412 | 7558338 | 1.601 | 512053 | 335781 | 6.99% | 18421 | 8883 |
| field | trace | 2801 | 12067190 | 7550008 | 1.598 | 501830 | 334650 | 6.92% | 18146 | 8827 |
| field | trace | 2802 | 12057405 | 7546734 | 1.598 | 501831 | 335472 | 6.93% | 18140 | 8786 |
| bmenu | timing | 3120 | 13295652 | 7450850 | 1.784 | 882163 | 576800 | 10.96% | 29015 | 15239 |
| bmenu | timing | 3121 | 12800685 | 7151053 | 1.790 | 868116 | 533321 | 10.93% | 28547 | 14261 |
| bmenu | timing | 3122 | 12943150 | 7223046 | 1.792 | 865892 | 571816 | 11.09% | 28520 | 15102 |
| bmenu | trace | 3120 | 15646618 | 9690955 | 1.615 | 750515 | 540957 | 8.24% | 26230 | 14571 |
| bmenu | trace | 3121 | 15128364 | 9381192 | 1.613 | 731585 | 498304 | 8.12% | 25669 | 13587 |
| bmenu | trace | 3122 | 15266235 | 9444895 | 1.616 | 732170 | 534510 | 8.28% | 25668 | 14403 |


Pooled refill latency in cycles, accepted AR through accepted RLAST inclusive. Full distributions are retained in the private results.

| Window | Build | Cache | Count | Mean | Min | p50 | p90 | p99 | Max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dodge | timing | I | 92854 | 72.31 | 22 | 65 | 98 | 144 | 264 |
| dodge | timing | D | 55346 | 67.26 | 49 | 54 | 107 | 207 | 276 |
| dodge | trace | I | 83989 | 71.37 | 22 | 59 | 98 | 144 | 279 |
| dodge | trace | D | 53194 | 67.87 | 49 | 54 | 108 | 211 | 237 |
| field | timing | I | 61918 | 71.79 | 22 | 64 | 98 | 118 | 222 |
| field | timing | D | 28582 | 66.11 | 49 | 54 | 108 | 208 | 233 |
| field | trace | I | 54707 | 70.59 | 22 | 55 | 98 | 120 | 216 |
| field | trace | D | 26496 | 67.23 | 49 | 54 | 110 | 210 | 232 |
| bmenu | timing | I | 86082 | 72.17 | 22 | 65 | 98 | 143 | 272 |
| bmenu | timing | D | 44602 | 70.53 | 49 | 54 | 135 | 215 | 276 |
| bmenu | trace | I | 77567 | 71.26 | 22 | 58 | 98 | 142 | 281 |
| bmenu | trace | D | 42561 | 71.48 | 49 | 54 | 142 | 216 | 241 |


## Where cycles are observed

Each entry below is a percentage of the three-frame window. These rows overlap; do not sum them. `RAW` is an unavailable source operand while a valid candidate cannot issue. Load/multiply/FP rows identify the producer of that dependency. Late integer-register FP results can remain in other RAW; the FP row is a conservative subset. Integer multiply has no separate execute-freeze source in this netlist. Hardware single-precision FPU counters exclude software double helpers.

| Observed cause | undertale/flowey/timing | undertale/flowey/trace | deltarune/dodge/timing | deltarune/dodge/trace | deltarune/field/timing | deltarune/field/trace | deltarune/bmenu/timing | deltarune/bmenu/trace |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| execute_freeze | 1.94% | 1.66% | 2.13% | 1.85% | 0.87% | 0.69% | 0.92% | 0.76% |
| i_block | 8.42% | 7.57% | 5.65% | 4.24% | 6.20% | 4.18% | 6.70% | 4.81% |
| d_block | 8.75% | 7.45% | 4.48% | 3.71% | 3.74% | 2.78% | 4.31% | 3.42% |
| raw_dependency | 9.63% | 9.31% | 13.14% | 12.56% | 10.24% | 9.92% | 9.83% | 9.63% |
| load_dependency | 4.74% | 5.22% | 6.71% | 7.04% | 7.03% | 7.42% | 6.95% | 7.32% |
| multiply_dependency | 0.32% | 0.27% | 0.28% | 0.25% | 0.10% | 0.08% | 0.17% | 0.14% |
| fp_dependency | 1.94% | 1.66% | 3.09% | 2.69% | 0.47% | 0.38% | 0.43% | 0.35% |
| fp_reservation | 0.04% | 0.03% | 0.19% | 0.16% | 0.03% | 0.01% | 0.02% | 0.01% |
| flush_interlock | 0.02% | 0.02% | 0.01% | 0.01% | 0.00% | 0.00% | 0.00% | 0.00% |
| fence_interlock | 0.06% | 0.05% | 0.04% | 0.03% | 0.00% | 0.00% | 0.00% | 0.00% |
| store_buffer_wait | 4.78% | 4.07% | 0.48% | 0.42% | 0.38% | 0.32% | 0.63% | 0.53% |
| integer_divider | 0.52% | 0.44% | 0.50% | 0.44% | 0.45% | 0.37% | 0.53% | 0.45% |
| fp_divider | 0.77% | 0.66% | 0.41% | 0.36% | 0.08% | 0.06% | 0.06% | 0.05% |
| fp_sqrt | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| fp_to_int | 0.10% | 0.08% | 0.11% | 0.09% | 0.04% | 0.04% | 0.04% | 0.03% |
| int_to_fp | 0.50% | 0.44% | 0.70% | 0.59% | 0.30% | 0.22% | 0.28% | 0.22% |
| uncached_io | 0.00% | 0.00% | 0.39% | 0.34% | 0.00% | 0.00% | 0.00% | 0.00% |
| csr | 0.05% | 0.05% | 0.03% | 0.03% | 0.00% | 0.00% | 0.00% | 0.00% |
| atomic | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| branch_recovery | 10.48% | 10.19% | 11.72% | 9.70% | 14.85% | 11.59% | 13.93% | 11.09% |


The integer and FP divide units share a divider; `FpuDivPlugin_SEL` splits its freeze cycles. FPU reservations track shared add/pack resources, separately from sqrt and conversion freezes. Uncached-I/O freeze includes the LSU ordering/response wait and is not a D-cache refill. Store-buffer dispatch waits and flush/fence interlocks are also separate from D refills. Every sample checks that the reconstructed producer dependencies equal the RTL RAW hazard and that the seven execute-freeze sources account for the complete freeze signal.

No-retirement subset, as a percentage of the full window (also overlapping):

| Observed cause | undertale/flowey/timing | undertale/flowey/trace | deltarune/dodge/timing | deltarune/dodge/trace | deltarune/field/timing | deltarune/field/trace | deltarune/bmenu/timing | deltarune/bmenu/trace |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| execute_freeze | 1.94% | 1.66% | 2.13% | 1.85% | 0.87% | 0.69% | 0.92% | 0.76% |
| i_block | 7.75% | 6.97% | 5.12% | 3.84% | 5.60% | 3.77% | 6.07% | 4.35% |
| d_block | 8.75% | 7.45% | 4.48% | 3.71% | 3.74% | 2.78% | 4.31% | 3.42% |
| raw_dependency | 4.18% | 3.55% | 5.20% | 4.49% | 3.83% | 3.09% | 3.59% | 2.97% |
| load_dependency | 1.83% | 1.63% | 1.85% | 1.66% | 2.24% | 1.91% | 2.24% | 1.95% |
| multiply_dependency | 0.10% | 0.09% | 0.11% | 0.10% | 0.03% | 0.03% | 0.04% | 0.03% |
| fp_dependency | 1.38% | 1.18% | 2.25% | 1.96% | 0.30% | 0.24% | 0.27% | 0.22% |
| fp_reservation | 0.03% | 0.03% | 0.16% | 0.14% | 0.01% | 0.01% | 0.01% | 0.01% |
| flush_interlock | 0.01% | 0.01% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| fence_interlock | 0.01% | 0.01% | 0.01% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| store_buffer_wait | 4.76% | 4.06% | 0.46% | 0.41% | 0.36% | 0.30% | 0.60% | 0.51% |
| integer_divider | 0.52% | 0.44% | 0.50% | 0.44% | 0.45% | 0.37% | 0.53% | 0.45% |
| fp_divider | 0.77% | 0.66% | 0.41% | 0.36% | 0.08% | 0.06% | 0.06% | 0.05% |
| fp_sqrt | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| fp_to_int | 0.10% | 0.08% | 0.11% | 0.09% | 0.04% | 0.04% | 0.04% | 0.03% |
| int_to_fp | 0.50% | 0.44% | 0.70% | 0.59% | 0.30% | 0.22% | 0.28% | 0.22% |
| uncached_io | 0.00% | 0.00% | 0.39% | 0.34% | 0.00% | 0.00% | 0.00% | 0.00% |
| csr | 0.05% | 0.05% | 0.03% | 0.03% | 0.00% | 0.00% | 0.00% | 0.00% |
| atomic | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| branch_recovery | 7.83% | 7.48% | 8.71% | 7.11% | 11.06% | 8.48% | 10.38% | 8.15% |


Disjoint accounting of all clocks follows this explicit priority: retirement; execution freeze; D wait; store-buffer wait; RAW; FP reservation; flush interlock; fence interlock; I block; branch recovery; residual dispatch without retirement; other waiting candidate; empty frontend/pipeline. This makes the table sum to 100%; its priority assigns overlaps for presentation, not causal blame. A dispatch without retirement may reflect pipeline latency, cancelled work or recovery.

| Exclusive observation | undertale/flowey/timing | undertale/flowey/trace | deltarune/dodge/timing | deltarune/dodge/trace | deltarune/field/timing | deltarune/field/trace | deltarune/bmenu/timing | deltarune/bmenu/trace |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| retirement | 51.02% | 54.48% | 55.41% | 60.38% | 55.77% | 62.53% | 55.90% | 61.94% |
| execute_freeze | 1.94% | 1.66% | 2.13% | 1.85% | 0.87% | 0.69% | 0.92% | 0.76% |
| d_block | 8.75% | 7.45% | 4.48% | 3.71% | 3.74% | 2.78% | 4.31% | 3.42% |
| store_buffer_wait | 4.76% | 4.06% | 0.46% | 0.41% | 0.36% | 0.30% | 0.60% | 0.51% |
| raw_dependency | 3.38% | 2.87% | 4.51% | 3.90% | 3.55% | 2.87% | 3.31% | 2.75% |
| fp_reservation | 0.00% | 0.00% | 0.02% | 0.02% | 0.00% | 0.00% | 0.00% | 0.00% |
| flush_interlock | 0.01% | 0.01% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| fence_interlock | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| i_block | 7.61% | 6.81% | 5.08% | 3.79% | 5.55% | 3.72% | 6.02% | 4.29% |
| branch_recovery | 6.85% | 6.58% | 8.10% | 6.70% | 10.43% | 8.13% | 9.68% | 7.70% |
| dispatch_without_retirement | 13.67% | 13.61% | 17.89% | 16.77% | 17.61% | 16.11% | 17.03% | 15.77% |
| candidate_other | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| frontend_or_pipeline_empty | 1.99% | 2.47% | 1.92% | 2.47% | 2.12% | 2.87% | 2.23% | 2.86% |


## Branches and instruction mix

A mispredict is a firing branch/jump learn event with `wasWrong`, including direction and target corrections for calls/returns. Recovery spans that event to dispatch of its corrected target. It includes overlapping cache and execution waits; it is not a pure mispredict penalty. BTB and decoder redirect pins are additionally retained as asserted-cycle counters, not assumed to be distinct retired branch events.

| Window/build | Retired | CPI | Branches/jumps | Mispredicts | Rate | Recovery mean | p50 | p90 | p99 | Max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| undertale/flowey/timing | 1939724 | 1.960 | 494466 | 59790 | 12.09% | 6.67 | 6 | 7 | 32 | 121 |
| undertale/flowey/trace | 2428595 | 1.836 | 554288 | 68995 | 12.45% | 6.58 | 6 | 7 | 31 | 125 |
| deltarune/dodge/timing | 27571901 | 1.805 | 6930033 | 915211 | 13.21% | 6.37 | 6 | 7 | 21 | 184 |
| deltarune/dodge/trace | 34319472 | 1.656 | 7700998 | 872365 | 11.33% | 6.32 | 6 | 7 | 17 | 127 |
| deltarune/field/timing | 16646499 | 1.793 | 4281868 | 702391 | 16.40% | 6.31 | 6 | 7 | 17 | 167 |
| deltarune/field/trace | 22655080 | 1.599 | 4968728 | 671862 | 13.52% | 6.25 | 6 | 7 | 17 | 167 |
| deltarune/bmenu/timing | 21824949 | 1.789 | 5774834 | 854247 | 14.79% | 6.37 | 6 | 7 | 21 | 200 |
| deltarune/bmenu/trace | 28517042 | 1.615 | 6539463 | 808123 | 12.36% | 6.32 | 6 | 7 | 17 | 174 |


| Retired instruction class | undertale/flowey/timing | undertale/flowey/trace | deltarune/dodge/timing | deltarune/dodge/trace | deltarune/field/timing | deltarune/field/trace | deltarune/bmenu/timing | deltarune/bmenu/trace |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| other_integer | 44.19% | 47.45% | 48.77% | 51.46% | 47.30% | 51.32% | 45.80% | 49.71% |
| load | 13.68% | 13.54% | 15.17% | 14.60% | 16.74% | 15.55% | 17.08% | 15.95% |
| store | 13.46% | 11.49% | 7.53% | 6.85% | 8.53% | 7.34% | 9.00% | 7.84% |
| branch_jump | 25.49% | 22.82% | 25.13% | 22.44% | 25.72% | 21.93% | 26.46% | 22.93% |
| fp_compute | 2.04% | 1.63% | 2.16% | 1.73% | 0.75% | 0.55% | 0.71% | 0.54% |
| integer_multiply | 0.99% | 2.95% | 1.10% | 2.82% | 0.87% | 3.25% | 0.84% | 2.95% |
| integer_divide_rem | 0.12% | 0.10% | 0.10% | 0.08% | 0.09% | 0.06% | 0.10% | 0.08% |
| system_csr | 0.03% | 0.02% | 0.02% | 0.01% | 0.00% | 0.00% | 0.00% | 0.00% |


The timing builds still enable `SW_DRAW_PROFILE` and `ENABLE_VM_GML_PROFILER`. In the frozen renderer, `swrDrawSprite` formats a note with `snprintf`, and `swrNote` hashes/searches descriptions and formats new descriptions. `printf_core` therefore includes renderer note formatting, not just UART output. These costs remain when VM tracing is disabled. They are measured work in this baseline; their cost in the card build has not been matched.

## Code attribution

Cache refills are attributed by line base; I block by initiating miss or held fetch PC. Sized ELF symbols keep padding explicit. These are different histograms. Pipeline dependency cycles below are charged to the waiting consumer’s dispatch PC. Retirement uses the actual retiring instruction PC. None of these function counts alone constitutes a function’s elapsed time.

### undertale/flowey/timing

Top 30 by refill count account for 57.38% of all I refills and 4.85% of the frame in attributed I block. Top 30 by I block account for 4.98% of the frame.

I refills:

| Function | I refills | I block cycles | Frame share |
| --- | --- | --- | --- |
| executeLoop | 1044 | 29577 | 0.778% |
| resolveVariableWrite | 506 | 16500 | 0.434% |
| swrDrawSpriteInternal | 449 | 18365 | 0.483% |
| handlePush | 255 | 6452 | 0.170% |
| printf_core | 249 | 7951 | 0.209% |
| Runner_step | 214 | 6896 | 0.181% |
| __subdf3 | 204 | 7643 | 0.201% |
| __adddf3 | 190 | 5808 | 0.153% |
| swrDrawText | 165 | 7401 | 0.195% |
| __divdf3 | 161 | 4805 | 0.126% |
| VM_callCodeIndex | 153 | 5302 | 0.139% |
| IntRValueHashMap_getOrInsertUndefined | 150 | 3488 | 0.092% |
| vfprintf | 136 | 3485 | 0.092% |
| Runner_getMouseRoomPosition | 132 | 3178 | 0.084% |
| loop | 131 | 5760 | 0.152% |
| __muldf3 | 130 | 4577 | 0.120% |
| malloc | 129 | 4755 | 0.125% |
| VM_executeCode | 122 | 3902 | 0.103% |
| resolveVariableRead | 121 | 3918 | 0.103% |
| handleCall | 105 | 2958 | 0.078% |
| VMBuiltins_getVariable | 100 | 3781 | 0.099% |
| swrNote | 100 | 2345 | 0.062% |
| memset | 96 | 5864 | 0.154% |
| SWRenderer_profDrawRectangle | 95 | 3733 | 0.098% |
| __truncdfsf2 | 94 | 4410 | 0.116% |
| swrOverlayFlushHeld | 87 | 1818 | 0.048% |
| __udivdi3 | 86 | 3569 | 0.094% |
| strcasecmp | 76 | 268 | 0.007% |
| Runner_draw | 75 | 3699 | 0.097% |
| platformHandleEvents | 73 | 2314 | 0.061% |


I block cycles:

| Function | I refills | I block cycles | Frame share |
| --- | --- | --- | --- |
| executeLoop | 1044 | 29577 | 0.778% |
| swrDrawSpriteInternal | 449 | 18365 | 0.483% |
| resolveVariableWrite | 506 | 16500 | 0.434% |
| printf_core | 249 | 7951 | 0.209% |
| __subdf3 | 204 | 7643 | 0.201% |
| swrDrawText | 165 | 7401 | 0.195% |
| Runner_step | 214 | 6896 | 0.181% |
| handlePush | 255 | 6452 | 0.170% |
| memset | 96 | 5864 | 0.154% |
| __adddf3 | 190 | 5808 | 0.153% |
| loop | 131 | 5760 | 0.152% |
| VM_callCodeIndex | 153 | 5302 | 0.139% |
| __divdf3 | 161 | 4805 | 0.126% |
| malloc | 129 | 4755 | 0.125% |
| __muldf3 | 130 | 4577 | 0.120% |
| __truncdfsf2 | 94 | 4410 | 0.116% |
| resolveVariableRead | 121 | 3918 | 0.103% |
| VM_executeCode | 122 | 3902 | 0.103% |
| VMBuiltins_getVariable | 100 | 3781 | 0.099% |
| SWRenderer_profDrawRectangle | 95 | 3733 | 0.098% |
| Runner_draw | 75 | 3699 | 0.097% |
| __udivdi3 | 86 | 3569 | 0.094% |
| IntRValueHashMap_getOrInsertUndefined | 150 | 3488 | 0.092% |
| vfprintf | 136 | 3485 | 0.092% |
| memcpy | 58 | 3416 | 0.090% |
| Runner_getMouseRoomPosition | 132 | 3178 | 0.084% |
| SWRenderer_drawSprite | 60 | 3066 | 0.081% |
| handleCall | 105 | 2958 | 0.078% |
| vsnprintf | 43 | 2583 | 0.068% |
| swrNote | 100 | 2345 | 0.062% |


Top retiring functions, with overlapping waits charged to their consumers:

| Function | Retired | RAW cycles | Load dependency | Multiply dependency | FP dependency | Store-buffer wait |
| --- | --- | --- | --- | --- | --- | --- |
| swrClearSettle.part.0.constprop.0 | 345789 | 3 | 0 | 0 | 0 | 127340 |
| mixAndWrite | 236908 | 54340 | 21630 | 4800 | 0 | 0 |
| executeLoop | 187312 | 49749 | 23865 | 0 | 5447 | 0 |
| memcpy | 166279 | 2031 | 0 | 0 | 0 | 63 |
| swrDrawSpriteInternal | 133212 | 37177 | 17859 | 4630 | 0 | 0 |
| swrDrawHLineInt.part.0 | 81633 | 1068 | 801 | 0 | 0 | 0 |
| Collision_pointInInstance | 80259 | 57697 | 13938 | 0 | 39424 | 0 |
| Runner_step | 68482 | 33121 | 26752 | 54 | 576 | 0 |
| printf_core | 64938 | 10758 | 8407 | 344 | 0 | 0 |
| Runner_executeEventForAll | 42429 | 19322 | 14831 | 0 | 0 | 0 |
| memset | 31780 | 0 | 0 | 0 | 0 | 4518 |
| __fwritex | 29406 | 3072 | 3072 | 0 | 0 | 0 |
| __muldf3 | 27802 | 2940 | 0 | 1210 | 0 | 0 |
| handleCall | 20624 | 2859 | 2425 | 0 | 0 | 0 |
| resolveVariableRead | 20585 | 1823 | 1077 | 0 | 0 | 0 |
| malloc | 18051 | 630 | 477 | 0 | 0 | 0 |
| Collision_instancesOverlapPrecise.isra.0 | 16326 | 7869 | 45 | 0 | 7815 | 0 |
| resolveVariableWrite | 15297 | 769 | 205 | 0 | 0 | 0 |
| dispatchCollisionEvents | 12219 | 5272 | 4108 | 0 | 42 | 0 |
| handlePush | 12128 | 671 | 444 | 0 | 0 | 0 |


Top branch recovery sites, grouped by function:

| Function | Mispredicts | Recovery envelope cycles |
| --- | --- | --- |
| executeLoop | 10764 | 72038 |
| memcpy | 5519 | 32537 |
| swrDrawSpriteInternal | 4864 | 30793 |
| printf_core | 4676 | 30181 |
| mixAndWrite | 4464 | 24822 |
| handleCall | 1436 | 9289 |
| Runner_step | 1054 | 6556 |
| malloc | 1061 | 6133 |
| __fwritex | 949 | 5880 |
| handlePush | 852 | 5590 |
| swrOverlayFlush | 698 | 5497 |
| __muldf3 | 845 | 5411 |
| memset | 771 | 5263 |
| VM_callCodeIndex | 753 | 4707 |
| resolveVariableWrite | 607 | 4608 |
| __strchrnul / strchrnul | 605 | 3785 |
| resolveVariableRead | 511 | 3701 |
| VM_executeCode | 483 | 3517 |
| __adddf3 | 402 | 3409 |
| __subdf3 | 400 | 3253 |


### undertale/flowey/trace

Top 30 by refill count account for 56.91% of all I refills and 4.38% of the frame in attributed I block. Top 30 by I block account for 4.48% of the frame.

I refills:

| Function | I refills | I block cycles | Frame share |
| --- | --- | --- | --- |
| executeLoop | 944 | 28962 | 0.650% |
| resolveVariableWrite | 432 | 15755 | 0.353% |
| swrDrawSpriteInternal | 431 | 16824 | 0.377% |
| printf_core | 392 | 13010 | 0.292% |
| handlePush | 323 | 7998 | 0.179% |
| __subdf3 | 237 | 8982 | 0.201% |
| Runner_step | 222 | 7730 | 0.173% |
| malloc | 219 | 7849 | 0.176% |
| __adddf3 | 185 | 6283 | 0.141% |
| swrDrawText | 181 | 7642 | 0.171% |
| VM_callCodeIndex | 175 | 5752 | 0.129% |
| Runner_draw | 168 | 7612 | 0.171% |
| __muldf3 | 158 | 4325 | 0.097% |
| Runner_getMouseRoomPosition | 132 | 3451 | 0.077% |
| loop | 132 | 4940 | 0.111% |
| IntRValueHashMap_getOrInsertUndefined | 130 | 2960 | 0.066% |
| free | 127 | 5581 | 0.125% |
| __divdf3 | 126 | 3676 | 0.082% |
| memcpy | 123 | 4307 | 0.097% |
| VM_executeCode | 117 | 3203 | 0.072% |
| resolveVariableRead | 107 | 3357 | 0.075% |
| SWRenderer_drawSprite | 99 | 3464 | 0.078% |
| handleCall | 97 | 2745 | 0.062% |
| strcasecmp | 97 | 945 | 0.021% |
| VMBuiltins_getVariable | 90 | 3267 | 0.073% |
| __truncdfsf2 | 90 | 4249 | 0.095% |
| vfprintf | 82 | 3792 | 0.085% |
| handlePop | 81 | 2270 | 0.051% |
| swrNote | 76 | 1543 | 0.035% |
| __udivdi3 | 72 | 2737 | 0.061% |


I block cycles:

| Function | I refills | I block cycles | Frame share |
| --- | --- | --- | --- |
| executeLoop | 944 | 28962 | 0.650% |
| swrDrawSpriteInternal | 431 | 16824 | 0.377% |
| resolveVariableWrite | 432 | 15755 | 0.353% |
| printf_core | 392 | 13010 | 0.292% |
| __subdf3 | 237 | 8982 | 0.201% |
| handlePush | 323 | 7998 | 0.179% |
| malloc | 219 | 7849 | 0.176% |
| Runner_step | 222 | 7730 | 0.173% |
| swrDrawText | 181 | 7642 | 0.171% |
| Runner_draw | 168 | 7612 | 0.171% |
| __adddf3 | 185 | 6283 | 0.141% |
| VM_callCodeIndex | 175 | 5752 | 0.129% |
| free | 127 | 5581 | 0.125% |
| loop | 132 | 4940 | 0.111% |
| __muldf3 | 158 | 4325 | 0.097% |
| memcpy | 123 | 4307 | 0.097% |
| __truncdfsf2 | 90 | 4249 | 0.095% |
| vfprintf | 82 | 3792 | 0.085% |
| memset | 55 | 3748 | 0.084% |
| __divdf3 | 126 | 3676 | 0.082% |
| SWRenderer_drawSprite | 99 | 3464 | 0.078% |
| Runner_getMouseRoomPosition | 132 | 3451 | 0.077% |
| resolveVariableRead | 107 | 3357 | 0.075% |
| VMBuiltins_getVariable | 90 | 3267 | 0.073% |
| VM_executeCode | 117 | 3203 | 0.072% |
| IntRValueHashMap_getOrInsertUndefined | 130 | 2960 | 0.066% |
| fabsf | 0 | 2850 | 0.064% |
| handleCall | 97 | 2745 | 0.062% |
| __udivdi3 | 72 | 2737 | 0.061% |
| SWRenderer_profDrawRectangle | 66 | 2457 | 0.055% |


Top retiring functions, with overlapping waits charged to their consumers:

| Function | Retired | RAW cycles | Load dependency | Multiply dependency | FP dependency | Store-buffer wait |
| --- | --- | --- | --- | --- | --- | --- |
| frame_tick | 423878 | 42744 | 42744 | 0 | 0 | 0 |
| swrClearSettle.part.0.constprop.0 | 345789 | 3 | 0 | 0 | 0 | 126663 |
| mixAndWrite | 236908 | 54335 | 21612 | 4800 | 0 | 0 |
| executeLoop | 201560 | 45136 | 23811 | 0 | 5582 | 0 |
| memcpy | 166279 | 3221 | 0 | 0 | 0 | 44 |
| swrDrawSpriteInternal | 133212 | 37117 | 17814 | 4626 | 0 | 0 |
| swrDrawHLineInt.part.0 | 81633 | 1068 | 801 | 0 | 0 | 0 |
| Collision_pointInInstance | 80259 | 57690 | 13938 | 0 | 39417 | 0 |
| Runner_step | 68482 | 33135 | 26764 | 54 | 575 | 0 |
| printf_core | 64938 | 10719 | 8368 | 344 | 0 | 0 |
| frame_hash | 48228 | 9600 | 9600 | 0 | 0 | 0 |
| Runner_executeEventForAll | 42429 | 19316 | 14825 | 0 | 0 | 0 |
| memset | 31780 | 0 | 0 | 0 | 0 | 4864 |
| __fwritex | 29406 | 3066 | 3066 | 0 | 0 | 0 |
| __muldf3 | 27802 | 2948 | 0 | 1208 | 0 | 0 |
| handleCall | 20624 | 2918 | 2484 | 0 | 0 | 0 |
| resolveVariableRead | 20585 | 1725 | 1064 | 0 | 0 | 0 |
| malloc | 18051 | 610 | 448 | 0 | 0 | 0 |
| Collision_instancesOverlapPrecise.isra.0 | 16326 | 7869 | 45 | 0 | 7815 | 0 |
| resolveVariableWrite | 15297 | 815 | 234 | 0 | 0 | 0 |


Top branch recovery sites, grouped by function:

| Function | Mispredicts | Recovery envelope cycles |
| --- | --- | --- |
| executeLoop | 11643 | 76306 |
| memcpy | 7965 | 45963 |
| printf_core | 4871 | 32063 |
| frame_tick | 4698 | 28882 |
| swrDrawSpriteInternal | 4577 | 28642 |
| mixAndWrite | 4443 | 24615 |
| handleCall | 1480 | 9236 |
| Runner_step | 1088 | 6892 |
| malloc | 985 | 6380 |
| memset | 780 | 6143 |
| __fwritex | 947 | 5871 |
| handlePush | 879 | 5712 |
| __muldf3 | 863 | 5530 |
| resolveVariableWrite | 733 | 5045 |
| VM_callCodeIndex | 689 | 4659 |
| resolveVariableRead | 713 | 4522 |
| swrOverlayFlush | 715 | 4492 |
| __strchrnul / strchrnul | 691 | 4339 |
| VM_executeCode | 543 | 4161 |
| __subdf3 | 432 | 4032 |


### deltarune/dodge/timing

Top 30 by refill count account for 81.37% of all I refills and 4.61% of the frame in attributed I block. Top 30 by I block account for 4.67% of the frame.

I refills:

| Function | I refills | I block cycles | Frame share |
| --- | --- | --- | --- |
| executeLoop | 18491 | 557773 | 1.121% |
| printf_core | 9933 | 262067 | 0.527% |
| builtin_draw_sprite | 5272 | 180663 | 0.363% |
| Instance_setSelfVar | 4032 | 176243 | 0.354% |
| resolveVariableRead | 3809 | 118068 | 0.237% |
| resolveVariableWrite | 3740 | 69042 | 0.139% |
| vfprintf | 3069 | 42412 | 0.085% |
| handlePush | 2940 | 125559 | 0.252% |
| swrDrawSpriteInternal | 2620 | 89311 | 0.179% |
| __udivdi3 | 2379 | 98592 | 0.198% |
| memset | 2254 | 82621 | 0.166% |
| swrNote | 2109 | 45861 | 0.092% |
| sn_write | 1994 | 47064 | 0.095% |
| vsnprintf | 1597 | 69011 | 0.139% |
| Runner_draw | 1089 | 36948 | 0.074% |
| free | 1015 | 32390 | 0.065% |
| stackPopInt32 | 933 | 31593 | 0.063% |
| handleConv | 830 | 24521 | 0.049% |
| __moddi3 | 828 | 0 | 0.000% |
| swrMirrorFlush | 797 | 23693 | 0.048% |
| memcpy | 787 | 32092 | 0.064% |
| swrDrawText | 752 | 28090 | 0.056% |
| malloc | 749 | 23093 | 0.046% |
| strcasecmp | 705 | 3250 | 0.007% |
| VM_callCodeIndex | 599 | 17501 | 0.035% |
| __subdf3 | 465 | 17808 | 0.036% |
| VMBuiltins_getVariable | 452 | 14758 | 0.030% |
| Profiler_exit | 449 | 17744 | 0.036% |
| __adddf3 | 444 | 14749 | 0.030% |
| handleCall | 419 | 11394 | 0.023% |


I block cycles:

| Function | I refills | I block cycles | Frame share |
| --- | --- | --- | --- |
| executeLoop | 18491 | 557773 | 1.121% |
| printf_core | 9933 | 262067 | 0.527% |
| builtin_draw_sprite | 5272 | 180663 | 0.363% |
| Instance_setSelfVar | 4032 | 176243 | 0.354% |
| handlePush | 2940 | 125559 | 0.252% |
| resolveVariableRead | 3809 | 118068 | 0.237% |
| __udivdi3 | 2379 | 98592 | 0.198% |
| swrDrawSpriteInternal | 2620 | 89311 | 0.179% |
| memset | 2254 | 82621 | 0.166% |
| resolveVariableWrite | 3740 | 69042 | 0.139% |
| vsnprintf | 1597 | 69011 | 0.139% |
| sn_write | 1994 | 47064 | 0.095% |
| swrNote | 2109 | 45861 | 0.092% |
| vfprintf | 3069 | 42412 | 0.085% |
| Runner_draw | 1089 | 36948 | 0.074% |
| free | 1015 | 32390 | 0.065% |
| memcpy | 787 | 32092 | 0.064% |
| stackPopInt32 | 933 | 31593 | 0.063% |
| swrDrawText | 752 | 28090 | 0.056% |
| handleConv | 830 | 24521 | 0.049% |
| swrMirrorFlush | 797 | 23693 | 0.048% |
| malloc | 749 | 23093 | 0.046% |
| __subdf3 | 465 | 17808 | 0.036% |
| Profiler_exit | 449 | 17744 | 0.036% |
| VM_callCodeIndex | 599 | 17501 | 0.035% |
| __truncdfsf2 | 357 | 15817 | 0.032% |
| VMBuiltins_getVariable | 452 | 14758 | 0.030% |
| __adddf3 | 444 | 14749 | 0.030% |
| executeCode | 336 | 13951 | 0.028% |
| stbds_hm_find_slot | 371 | 12274 | 0.025% |


Top retiring functions, with overlapping waits charged to their consumers:

| Function | Retired | RAW cycles | Load dependency | Multiply dependency | FP dependency | Store-buffer wait |
| --- | --- | --- | --- | --- | --- | --- |
| swrDrawHLineInt.part.0 | 3841285 | 887715 | 471225 | 38397 | 0 | 0 |
| swrDrawSpriteInternal | 3531390 | 1002348 | 719035 | 18071 | 0 | 0 |
| executeLoop | 3175118 | 915850 | 529277 | 0 | 103231 | 315 |
| memcpy | 2878038 | 12200 | 0 | 0 | 0 | 5704 |
| swrTiledHeldWrite | 2027407 | 354438 | 305854 | 17387 | 0 | 96451 |
| printf_core | 1500908 | 245893 | 194181 | 7236 | 0 | 435 |
| swrRunsDrawOnto | 1241842 | 224376 | 79220 | 0 | 0 | 92641 |
| swrDrawSpriteRotated | 786912 | 1148526 | 22886 | 20639 | 1072341 | 0 |
| __fwritex | 699741 | 73114 | 73114 | 0 | 0 | 0 |
| Collision_pointInInstance | 533611 | 381999 | 92565 | 0 | 260584 | 0 |
| mixAndWrite | 467223 | 106042 | 49768 | 4800 | 0 | 0 |
| handlePush | 336880 | 24222 | 17828 | 0 | 0 | 0 |
| swrNote | 331870 | 59391 | 52285 | 0 | 0 | 0 |
| resolveVariableRead | 325791 | 33005 | 21383 | 0 | 0 | 0 |
| handleCall | 262557 | 40680 | 34085 | 0 | 0 | 0 |
| memset | 258452 | 0 | 0 | 0 | 0 | 7234 |
| __muldf3 | 257346 | 28105 | 0 | 12045 | 0 | 0 |
| IntRValueHashMap_findSlot | 225374 | 77837 | 59628 | 0 | 0 | 0 |
| strncmp | 223139 | 60889 | 60889 | 0 | 0 | 0 |
| Runner_draw | 213986 | 77891 | 73926 | 2100 | 1050 | 105 |


Top branch recovery sites, grouped by function:

| Function | Mispredicts | Recovery envelope cycles |
| --- | --- | --- |
| executeLoop | 207489 | 1287140 |
| memcpy | 116220 | 678120 |
| printf_core | 98576 | 650921 |
| swrDrawSpriteInternal | 85532 | 508672 |
| __fwritex | 22002 | 165424 |
| swrDrawHLineInt.part.0 | 23078 | 137706 |
| IntRValueHashMap_findSlot | 19543 | 123929 |
| handleCall | 19494 | 122778 |
| RValue_free | 13831 | 87318 |
| resolveVariableWrite | 10840 | 86816 |
| stackPopInt32 | 6843 | 68709 |
| resolveVariableRead | 9770 | 64365 |
| mixAndWrite | 11587 | 63496 |
| swrRunsDrawOnto | 11801 | 61564 |
| handlePush | 7097 | 58888 |
| swrNote | 7781 | 58184 |
| memset | 8012 | 58149 |
| SWRenderer_profDrawSprite | 8406 | 52301 |
| builtin_draw_sprite | 7203 | 50832 |
| pop_arg | 8103 | 48725 |


### deltarune/dodge/trace

Top 30 by refill count account for 79.75% of all I refills and 3.34% of the frame in attributed I block. Top 30 by I block account for 3.40% of the frame.

I refills:

| Function | I refills | I block cycles | Frame share |
| --- | --- | --- | --- |
| executeLoop | 18825 | 422031 | 0.742% |
| printf_core | 5529 | 128994 | 0.227% |
| builtin_draw_sprite | 5366 | 210840 | 0.371% |
| resolveVariableWrite | 4918 | 146861 | 0.258% |
| swrDrawSpriteInternal | 3850 | 133749 | 0.235% |
| vfprintf | 3729 | 144834 | 0.255% |
| Instance_setSelfVar | 3691 | 129257 | 0.227% |
| frame_tick | 2567 | 33178 | 0.058% |
| __udivdi3 | 1800 | 84734 | 0.149% |
| handleCall | 1746 | 50229 | 0.088% |
| stackPopInt32 | 1672 | 40334 | 0.071% |
| Runner_draw | 1309 | 44533 | 0.078% |
| swrNote | 1155 | 30500 | 0.054% |
| handlePush | 1077 | 28497 | 0.050% |
| resolveVariableRead | 1048 | 36818 | 0.065% |
| swrMirrorFlush | 942 | 18720 | 0.033% |
| swrDrawText | 811 | 27308 | 0.048% |
| tryReadStaticFallback.isra.0 | 807 | 0 | 0.000% |
| __moddi3 | 778 | 0 | 0.000% |
| VM_callCodeIndex | 747 | 22162 | 0.039% |
| malloc | 599 | 19978 | 0.035% |
| free | 574 | 20392 | 0.036% |
| handleConv | 574 | 17782 | 0.031% |
| __adddf3 | 474 | 16367 | 0.029% |
| __subdf3 | 459 | 17115 | 0.030% |
| memcpy | 458 | 29552 | 0.052% |
| __muldf3 | 379 | 12960 | 0.023% |
| SWRenderer_profDrawRectangle | 374 | 11628 | 0.020% |
| VMBuiltins_getVariable | 373 | 12282 | 0.022% |
| __divdf3 | 354 | 8796 | 0.015% |


I block cycles:

| Function | I refills | I block cycles | Frame share |
| --- | --- | --- | --- |
| executeLoop | 18825 | 422031 | 0.742% |
| builtin_draw_sprite | 5366 | 210840 | 0.371% |
| resolveVariableWrite | 4918 | 146861 | 0.258% |
| vfprintf | 3729 | 144834 | 0.255% |
| swrDrawSpriteInternal | 3850 | 133749 | 0.235% |
| Instance_setSelfVar | 3691 | 129257 | 0.227% |
| printf_core | 5529 | 128994 | 0.227% |
| __udivdi3 | 1800 | 84734 | 0.149% |
| handleCall | 1746 | 50229 | 0.088% |
| Runner_draw | 1309 | 44533 | 0.078% |
| stackPopInt32 | 1672 | 40334 | 0.071% |
| resolveVariableRead | 1048 | 36818 | 0.065% |
| frame_tick | 2567 | 33178 | 0.058% |
| swrNote | 1155 | 30500 | 0.054% |
| memcpy | 458 | 29552 | 0.052% |
| handlePush | 1077 | 28497 | 0.050% |
| swrDrawText | 811 | 27308 | 0.048% |
| VM_callCodeIndex | 747 | 22162 | 0.039% |
| free | 574 | 20392 | 0.036% |
| malloc | 599 | 19978 | 0.035% |
| swrMirrorFlush | 942 | 18720 | 0.033% |
| handleConv | 574 | 17782 | 0.031% |
| __subdf3 | 459 | 17115 | 0.030% |
| __adddf3 | 474 | 16367 | 0.029% |
| __truncdfsf2 | 309 | 14856 | 0.026% |
| Profiler_exit | 293 | 13023 | 0.023% |
| __muldf3 | 379 | 12960 | 0.023% |
| VMBuiltins_getVariable | 373 | 12282 | 0.022% |
| SWRenderer_profDrawRectangle | 374 | 11628 | 0.020% |
| stbds_hm_find_slot | 330 | 11397 | 0.020% |


Top retiring functions, with overlapping waits charged to their consumers:

| Function | Retired | RAW cycles | Load dependency | Multiply dependency | FP dependency | Store-buffer wait |
| --- | --- | --- | --- | --- | --- | --- |
| frame_tick | 6475028 | 652947 | 652947 | 0 | 0 | 0 |
| swrDrawHLineInt.part.0 | 3841285 | 887703 | 471213 | 38397 | 0 | 0 |
| swrDrawSpriteInternal | 3531390 | 1002586 | 719280 | 18047 | 0 | 30 |
| executeLoop | 3404133 | 857965 | 535189 | 0 | 95261 | 365 |
| memcpy | 2878038 | 12660 | 0 | 0 | 0 | 5852 |
| swrTiledHeldWrite | 2027407 | 354490 | 305915 | 17387 | 0 | 97979 |
| printf_core | 1500908 | 245076 | 193358 | 7236 | 0 | 543 |
| swrRunsDrawOnto | 1241842 | 224387 | 79231 | 0 | 0 | 92890 |
| swrDrawSpriteRotated | 786912 | 1148446 | 22886 | 20639 | 1072261 | 0 |
| __fwritex | 699741 | 73487 | 73487 | 0 | 0 | 0 |
| Collision_pointInInstance | 533611 | 381996 | 92538 | 0 | 260608 | 0 |
| mixAndWrite | 467223 | 106172 | 49787 | 4800 | 0 | 0 |
| handlePush | 336880 | 24197 | 17845 | 0 | 0 | 0 |
| swrNote | 331870 | 59362 | 52256 | 0 | 0 | 0 |
| resolveVariableRead | 325791 | 33875 | 22018 | 0 | 0 | 0 |
| handleCall | 262557 | 40501 | 33907 | 0 | 0 | 0 |
| memset | 258452 | 0 | 0 | 0 | 0 | 7426 |
| __muldf3 | 257346 | 28167 | 0 | 12081 | 0 | 0 |
| IntRValueHashMap_findSlot | 225374 | 77802 | 59593 | 0 | 0 | 0 |
| strncmp | 223139 | 60745 | 60745 | 0 | 0 | 0 |


Top branch recovery sites, grouped by function:

| Function | Mispredicts | Recovery envelope cycles |
| --- | --- | --- |
| executeLoop | 196540 | 1252692 |
| printf_core | 96024 | 624484 |
| memcpy | 88981 | 531210 |
| swrDrawSpriteInternal | 85596 | 507004 |
| frame_tick | 26197 | 168349 |
| swrDrawHLineInt.part.0 | 22711 | 135494 |
| __fwritex | 21132 | 127787 |
| handleCall | 17431 | 110925 |
| IntRValueHashMap_findSlot | 12399 | 74502 |
| resolveVariableWrite | 9607 | 64988 |
| mixAndWrite | 11816 | 64581 |
| VMBuiltins_getVariable | 10441 | 63104 |
| builtin_draw_sprite | 7626 | 63065 |
| swrRunsDrawOnto | 11736 | 61270 |
| vfprintf | 6968 | 59421 |
| SWRenderer_profDrawSprite | 9088 | 56412 |
| RValue_free | 7786 | 50893 |
| pop_arg | 8109 | 48687 |
| memset | 6772 | 43285 |
| swrNote | 6659 | 41573 |


### deltarune/field/timing

Top 30 by refill count account for 90.16% of all I refills and 5.53% of the frame in attributed I block. Top 30 by I block account for 5.58% of the frame.

I refills:

| Function | I refills | I block cycles | Frame share |
| --- | --- | --- | --- |
| executeLoop | 14186 | 417412 | 1.398% |
| printf_core | 7232 | 191441 | 0.641% |
| builtin_draw_sprite | 4818 | 164524 | 0.551% |
| Instance_setSelfVar | 3565 | 154708 | 0.518% |
| resolveVariableWrite | 2951 | 47501 | 0.159% |
| vfprintf | 2776 | 33788 | 0.113% |
| resolveVariableRead | 2617 | 78998 | 0.265% |
| handlePush | 2204 | 99390 | 0.333% |
| memset | 1842 | 65172 | 0.218% |
| __udivdi3 | 1769 | 78151 | 0.262% |
| sn_write | 1633 | 38730 | 0.130% |
| swrDrawSpriteInternal | 1602 | 52721 | 0.177% |
| swrNote | 1526 | 35218 | 0.118% |
| vsnprintf | 1393 | 55360 | 0.185% |
| stackPopInt32 | 773 | 25924 | 0.087% |
| __moddi3 | 718 | 0 | 0.000% |
| swrMirrorFlush | 564 | 11571 | 0.039% |
| free | 518 | 13969 | 0.047% |
| strcasecmp | 493 | 2613 | 0.009% |
| Runner_draw | 458 | 14814 | 0.050% |
| handleConv | 334 | 11223 | 0.038% |
| resolveLocalSlot | 246 | 4256 | 0.014% |
| Runner_step | 231 | 7250 | 0.024% |
| tryReadStaticFallback.isra.0 | 223 | 0 | 0.000% |
| memcpy | 219 | 11049 | 0.037% |
| VMBuiltins_getVariable | 218 | 7658 | 0.026% |
| executeCode | 199 | 8087 | 0.027% |
| VMBuiltins_setVariable | 182 | 6285 | 0.021% |
| VM_callCodeIndex | 169 | 6183 | 0.021% |
| malloc | 168 | 5813 | 0.019% |


I block cycles:

| Function | I refills | I block cycles | Frame share |
| --- | --- | --- | --- |
| executeLoop | 14186 | 417412 | 1.398% |
| printf_core | 7232 | 191441 | 0.641% |
| builtin_draw_sprite | 4818 | 164524 | 0.551% |
| Instance_setSelfVar | 3565 | 154708 | 0.518% |
| handlePush | 2204 | 99390 | 0.333% |
| resolveVariableRead | 2617 | 78998 | 0.265% |
| __udivdi3 | 1769 | 78151 | 0.262% |
| memset | 1842 | 65172 | 0.218% |
| vsnprintf | 1393 | 55360 | 0.185% |
| swrDrawSpriteInternal | 1602 | 52721 | 0.177% |
| resolveVariableWrite | 2951 | 47501 | 0.159% |
| sn_write | 1633 | 38730 | 0.130% |
| swrNote | 1526 | 35218 | 0.118% |
| vfprintf | 2776 | 33788 | 0.113% |
| stackPopInt32 | 773 | 25924 | 0.087% |
| Runner_draw | 458 | 14814 | 0.050% |
| free | 518 | 13969 | 0.047% |
| swrMirrorFlush | 564 | 11571 | 0.039% |
| handleConv | 334 | 11223 | 0.038% |
| memcpy | 219 | 11049 | 0.037% |
| executeCode | 199 | 8087 | 0.027% |
| VMBuiltins_getVariable | 218 | 7658 | 0.026% |
| Runner_step | 231 | 7250 | 0.024% |
| Profiler_exit | 152 | 6298 | 0.021% |
| VMBuiltins_setVariable | 182 | 6285 | 0.021% |
| VM_callCodeIndex | 169 | 6183 | 0.021% |
| handlePop | 166 | 5855 | 0.020% |
| malloc | 168 | 5813 | 0.019% |
| __truncdfsf2 | 123 | 5731 | 0.019% |
| loop | 130 | 5565 | 0.019% |


Top retiring functions, with overlapping waits charged to their consumers:

| Function | Retired | RAW cycles | Load dependency | Multiply dependency | FP dependency | Store-buffer wait |
| --- | --- | --- | --- | --- | --- | --- |
| executeLoop | 2846972 | 815068 | 470709 | 0 | 87864 | 305 |
| memcpy | 2449694 | 8767 | 0 | 0 | 0 | 8126 |
| swrDrawSpriteInternal | 2172535 | 621593 | 599930 | 1532 | 0 | 0 |
| swrRunsDrawOnto | 1331052 | 252732 | 88743 | 0 | 0 | 80503 |
| mixAndWrite | 1291057 | 289909 | 147895 | 4800 | 0 | 0 |
| printf_core | 1187826 | 194777 | 154775 | 5718 | 0 | 0 |
| __fwritex | 559758 | 58602 | 58602 | 0 | 0 | 0 |
| handlePush | 320742 | 22689 | 16753 | 0 | 0 | 0 |
| resolveVariableRead | 299838 | 30009 | 19312 | 0 | 0 | 0 |
| SWRenderer_profDrawTileRun | 213432 | 72720 | 23355 | 11553 | 26256 | 0 |
| IntRValueHashMap_findSlot | 195517 | 66454 | 51006 | 0 | 0 | 0 |
| strncmp | 178068 | 48608 | 48608 | 0 | 0 | 0 |
| Runner_draw | 175803 | 63424 | 59719 | 2100 | 1050 | 183 |
| handleCall | 170709 | 26789 | 22376 | 0 | 0 | 0 |
| memset | 170305 | 0 | 0 | 0 | 0 | 4629 |
| stackPush | 155089 | 14096 | 14096 | 0 | 0 | 0 |
| swrNote | 150699 | 6546 | 5121 | 0 | 0 | 0 |
| popArrayAccess | 145052 | 6004 | 4733 | 0 | 18 | 0 |
| VMBuiltins_getVariable | 141042 | 20265 | 12447 | 0 | 4074 | 0 |
| Instance_setSelfVar | 130001 | 830 | 830 | 0 | 0 | 0 |


Top branch recovery sites, grouped by function:

| Function | Mispredicts | Recovery envelope cycles |
| --- | --- | --- |
| executeLoop | 183402 | 1134512 |
| memcpy | 91702 | 536795 |
| printf_core | 74296 | 489936 |
| swrDrawSpriteInternal | 68304 | 403647 |
| mixAndWrite | 30202 | 164169 |
| __fwritex | 17486 | 135800 |
| IntRValueHashMap_findSlot | 16289 | 99950 |
| handleCall | 12434 | 78450 |
| resolveVariableWrite | 9468 | 76314 |
| RValue_free | 12131 | 73130 |
| swrRunsDrawOnto | 12686 | 65801 |
| handlePush | 7518 | 60086 |
| resolveVariableRead | 8878 | 54693 |
| stackPopInt32 | 4837 | 53229 |
| builtin_draw_sprite | 6465 | 45190 |
| swrNote | 5855 | 45172 |
| SWRenderer_profDrawSprite | 7131 | 44343 |
| memset | 5792 | 43316 |
| VMBuiltins_getVariable | 7064 | 42721 |
| pop_arg | 6441 | 38757 |


### deltarune/field/trace

Top 30 by refill count account for 88.59% of all I refills and 3.66% of the frame in attributed I block. Top 30 by I block account for 3.72% of the frame.

I refills:

| Function | I refills | I block cycles | Frame share |
| --- | --- | --- | --- |
| executeLoop | 14836 | 307112 | 0.848% |
| builtin_draw_sprite | 4848 | 188770 | 0.521% |
| resolveVariableWrite | 4212 | 119452 | 0.330% |
| printf_core | 3480 | 76802 | 0.212% |
| Instance_setSelfVar | 3156 | 104838 | 0.289% |
| vfprintf | 2901 | 120332 | 0.332% |
| swrDrawSpriteInternal | 2318 | 83246 | 0.230% |
| frame_tick | 2035 | 26508 | 0.073% |
| __udivdi3 | 1530 | 74965 | 0.207% |
| stackPopInt32 | 1464 | 35098 | 0.097% |
| handleCall | 1148 | 32908 | 0.091% |
| swrNote | 809 | 25134 | 0.069% |
| tryReadStaticFallback.isra.0 | 711 | 0 | 0.000% |
| __moddi3 | 707 | 0 | 0.000% |
| swrMirrorFlush | 606 | 11602 | 0.032% |
| Runner_draw | 576 | 19616 | 0.054% |
| resolveVariableRead | 518 | 17350 | 0.048% |
| handleConv | 278 | 9282 | 0.026% |
| resolveLocalSlot | 277 | 5829 | 0.016% |
| malloc | 268 | 9506 | 0.026% |
| free | 245 | 8377 | 0.023% |
| Runner_step | 229 | 6820 | 0.019% |
| VM_callCodeIndex | 217 | 7658 | 0.021% |
| VMBuiltins_getVariable | 175 | 5206 | 0.014% |
| VMBuiltins_setVariable | 175 | 6174 | 0.017% |
| handlePush | 170 | 4045 | 0.011% |
| handlePop | 157 | 5460 | 0.015% |
| executeCode | 150 | 6039 | 0.017% |
| Runner_getMouseRoomPosition | 138 | 3804 | 0.010% |
| __divdf3 | 132 | 4325 | 0.012% |


I block cycles:

| Function | I refills | I block cycles | Frame share |
| --- | --- | --- | --- |
| executeLoop | 14836 | 307112 | 0.848% |
| builtin_draw_sprite | 4848 | 188770 | 0.521% |
| vfprintf | 2901 | 120332 | 0.332% |
| resolveVariableWrite | 4212 | 119452 | 0.330% |
| Instance_setSelfVar | 3156 | 104838 | 0.289% |
| swrDrawSpriteInternal | 2318 | 83246 | 0.230% |
| printf_core | 3480 | 76802 | 0.212% |
| __udivdi3 | 1530 | 74965 | 0.207% |
| stackPopInt32 | 1464 | 35098 | 0.097% |
| handleCall | 1148 | 32908 | 0.091% |
| frame_tick | 2035 | 26508 | 0.073% |
| swrNote | 809 | 25134 | 0.069% |
| Runner_draw | 576 | 19616 | 0.054% |
| resolveVariableRead | 518 | 17350 | 0.048% |
| memcpy | 112 | 12685 | 0.035% |
| swrMirrorFlush | 606 | 11602 | 0.032% |
| malloc | 268 | 9506 | 0.026% |
| handleConv | 278 | 9282 | 0.026% |
| free | 245 | 8377 | 0.023% |
| VM_callCodeIndex | 217 | 7658 | 0.021% |
| Runner_step | 229 | 6820 | 0.019% |
| loop | 130 | 6235 | 0.017% |
| VMBuiltins_setVariable | 175 | 6174 | 0.017% |
| executeCode | 150 | 6039 | 0.017% |
| resolveLocalSlot | 277 | 5829 | 0.016% |
| handlePop | 157 | 5460 | 0.015% |
| VMBuiltins_getVariable | 175 | 5206 | 0.014% |
| __truncdfsf2 | 103 | 4866 | 0.013% |
| __divdf3 | 132 | 4325 | 0.012% |
| __umoddi3 | 83 | 4226 | 0.012% |


Top retiring functions, with overlapping waits charged to their consumers:

| Function | Retired | RAW cycles | Load dependency | Multiply dependency | FP dependency | Store-buffer wait |
| --- | --- | --- | --- | --- | --- | --- |
| frame_tick | 5763289 | 581171 | 581171 | 0 | 0 | 0 |
| executeLoop | 3052414 | 768642 | 476960 | 0 | 84260 | 341 |
| memcpy | 2449694 | 9036 | 0 | 0 | 0 | 7942 |
| swrDrawSpriteInternal | 2172535 | 622483 | 600805 | 1530 | 0 | 0 |
| swrRunsDrawOnto | 1331052 | 252743 | 88754 | 0 | 0 | 80728 |
| mixAndWrite | 1291057 | 289966 | 147715 | 4800 | 0 | 0 |
| printf_core | 1187826 | 193754 | 153752 | 5718 | 0 | 0 |
| __fwritex | 559758 | 58635 | 58635 | 0 | 0 | 0 |
| handlePush | 320742 | 22682 | 16756 | 0 | 0 | 0 |
| resolveVariableRead | 299838 | 30349 | 19651 | 0 | 0 | 0 |
| SWRenderer_profDrawTileRun | 213432 | 72711 | 23346 | 11553 | 26256 | 0 |
| IntRValueHashMap_findSlot | 195517 | 66446 | 50998 | 0 | 0 | 0 |
| strncmp | 178068 | 48428 | 48428 | 0 | 0 | 0 |
| Runner_draw | 175803 | 63368 | 59657 | 2100 | 1050 | 105 |
| handleCall | 170709 | 26793 | 22380 | 0 | 0 | 0 |
| memset | 170305 | 0 | 0 | 0 | 0 | 4786 |
| stackPush | 155089 | 14094 | 14094 | 0 | 0 | 0 |
| swrNote | 150699 | 6552 | 5127 | 0 | 0 | 0 |
| popArrayAccess | 145052 | 6076 | 4799 | 0 | 24 | 0 |
| VMBuiltins_getVariable | 141042 | 20259 | 12450 | 0 | 4059 | 0 |


Top branch recovery sites, grouped by function:

| Function | Mispredicts | Recovery envelope cycles |
| --- | --- | --- |
| executeLoop | 174135 | 1109508 |
| printf_core | 74186 | 478525 |
| swrDrawSpriteInternal | 68876 | 407625 |
| memcpy | 65487 | 387532 |
| frame_tick | 28190 | 182374 |
| mixAndWrite | 29687 | 160981 |
| __fwritex | 16547 | 99627 |
| handleCall | 10852 | 68129 |
| swrRunsDrawOnto | 12643 | 65704 |
| VMBuiltins_getVariable | 9914 | 59876 |
| builtin_draw_sprite | 6876 | 57083 |
| resolveVariableWrite | 8462 | 55869 |
| IntRValueHashMap_findSlot | 9365 | 55575 |
| SWRenderer_profDrawSprite | 7779 | 48259 |
| vfprintf | 5319 | 43694 |
| RValue_free | 6605 | 40006 |
| pop_arg | 6441 | 38646 |
| handlePush | 6136 | 37398 |
| Instance_setSelfVar | 5072 | 33134 |
| resolveVariableRead | 5269 | 33037 |


### deltarune/bmenu/timing

Top 30 by refill count account for 84.86% of all I refills and 5.68% of the frame in attributed I block. Top 30 by I block account for 5.73% of the frame.

I refills:

| Function | I refills | I block cycles | Frame share |
| --- | --- | --- | --- |
| executeLoop | 18056 | 541034 | 1.386% |
| printf_core | 9796 | 259120 | 0.664% |
| builtin_draw_sprite | 5345 | 182857 | 0.468% |
| Instance_setSelfVar | 3971 | 172689 | 0.442% |
| resolveVariableRead | 3678 | 113372 | 0.290% |
| resolveVariableWrite | 3428 | 62142 | 0.159% |
| vfprintf | 3040 | 40048 | 0.103% |
| handlePush | 2935 | 126546 | 0.324% |
| swrDrawSpriteInternal | 2571 | 88840 | 0.228% |
| __udivdi3 | 2399 | 100081 | 0.256% |
| memset | 2095 | 75564 | 0.194% |
| swrNote | 2024 | 47452 | 0.122% |
| sn_write | 1829 | 45169 | 0.116% |
| vsnprintf | 1594 | 69880 | 0.179% |
| Runner_draw | 931 | 31163 | 0.080% |
| stackPopInt32 | 908 | 31322 | 0.080% |
| free | 870 | 33155 | 0.085% |
| __moddi3 | 838 | 0 | 0.000% |
| swrMirrorFlush | 811 | 23534 | 0.060% |
| strcasecmp | 805 | 3186 | 0.008% |
| handleConv | 773 | 22534 | 0.058% |
| memcpy | 724 | 30394 | 0.078% |
| swrDrawText | 722 | 26133 | 0.067% |
| malloc | 665 | 21659 | 0.055% |
| VM_callCodeIndex | 474 | 13665 | 0.035% |
| Profiler_exit | 415 | 15436 | 0.040% |
| SWRenderer_profDrawRectangle | 389 | 12148 | 0.031% |
| VMBuiltins_getVariable | 342 | 11405 | 0.029% |
| stbds_hm_find_slot | 321 | 10439 | 0.027% |
| swrOverlayFlushHeld | 303 | 7180 | 0.018% |


I block cycles:

| Function | I refills | I block cycles | Frame share |
| --- | --- | --- | --- |
| executeLoop | 18056 | 541034 | 1.386% |
| printf_core | 9796 | 259120 | 0.664% |
| builtin_draw_sprite | 5345 | 182857 | 0.468% |
| Instance_setSelfVar | 3971 | 172689 | 0.442% |
| handlePush | 2935 | 126546 | 0.324% |
| resolveVariableRead | 3678 | 113372 | 0.290% |
| __udivdi3 | 2399 | 100081 | 0.256% |
| swrDrawSpriteInternal | 2571 | 88840 | 0.228% |
| memset | 2095 | 75564 | 0.194% |
| vsnprintf | 1594 | 69880 | 0.179% |
| resolveVariableWrite | 3428 | 62142 | 0.159% |
| swrNote | 2024 | 47452 | 0.122% |
| sn_write | 1829 | 45169 | 0.116% |
| vfprintf | 3040 | 40048 | 0.103% |
| free | 870 | 33155 | 0.085% |
| stackPopInt32 | 908 | 31322 | 0.080% |
| Runner_draw | 931 | 31163 | 0.080% |
| memcpy | 724 | 30394 | 0.078% |
| swrDrawText | 722 | 26133 | 0.067% |
| swrMirrorFlush | 811 | 23534 | 0.060% |
| handleConv | 773 | 22534 | 0.058% |
| malloc | 665 | 21659 | 0.055% |
| Profiler_exit | 415 | 15436 | 0.040% |
| VM_callCodeIndex | 474 | 13665 | 0.035% |
| SWRenderer_profDrawRectangle | 389 | 12148 | 0.031% |
| VMBuiltins_getVariable | 342 | 11405 | 0.029% |
| executeCode | 256 | 10986 | 0.028% |
| __truncdfsf2 | 243 | 10763 | 0.028% |
| stbds_hm_find_slot | 321 | 10439 | 0.027% |
| handleCall | 291 | 9002 | 0.023% |


Top retiring functions, with overlapping waits charged to their consumers:

| Function | Retired | RAW cycles | Load dependency | Multiply dependency | FP dependency | Store-buffer wait |
| --- | --- | --- | --- | --- | --- | --- |
| executeLoop | 3141848 | 908533 | 524946 | 0 | 102985 | 311 |
| swrDrawSpriteInternal | 3014725 | 806064 | 708216 | 14841 | 0 | 50 |
| memcpy | 2874638 | 12591 | 0 | 0 | 0 | 5792 |
| swrTiledHeldWrite | 2012937 | 352066 | 304073 | 17187 | 0 | 102686 |
| printf_core | 1531886 | 251268 | 198045 | 7342 | 0 | 545 |
| swrRunsDrawOnto | 1241751 | 224476 | 79240 | 0 | 0 | 95106 |
| mixAndWrite | 891753 | 197642 | 101022 | 4800 | 0 | 0 |
| __fwritex | 714763 | 74855 | 74855 | 0 | 0 | 0 |
| swrDrawHLineInt.part.0 | 450504 | 2304 | 1728 | 0 | 0 | 0 |
| handlePush | 334874 | 24235 | 17816 | 0 | 0 | 0 |
| resolveVariableRead | 328696 | 33569 | 21849 | 0 | 0 | 0 |
| swrNote | 252999 | 24288 | 22460 | 0 | 0 | 0 |
| handleCall | 248637 | 38745 | 32434 | 0 | 0 | 0 |
| memset | 248237 | 0 | 0 | 0 | 0 | 5210 |
| strncmp | 237192 | 64891 | 64891 | 0 | 0 | 0 |
| IntRValueHashMap_findSlot | 235686 | 81894 | 62406 | 0 | 0 | 0 |
| SWRenderer_profDrawTileRun | 213345 | 72665 | 23300 | 11553 | 26256 | 0 |
| Runner_draw | 201595 | 72915 | 69003 | 2100 | 1050 | 183 |
| stackPush | 172271 | 15639 | 15639 | 0 | 0 | 0 |
| popArrayAccess | 161975 | 7773 | 6014 | 0 | 206 | 63 |


Top branch recovery sites, grouped by function:

| Function | Mispredicts | Recovery envelope cycles |
| --- | --- | --- |
| executeLoop | 205348 | 1271711 |
| printf_core | 100714 | 664017 |
| memcpy | 113076 | 656333 |
| swrDrawSpriteInternal | 85198 | 508675 |
| __fwritex | 22450 | 171010 |
| IntRValueHashMap_findSlot | 20373 | 125504 |
| handleCall | 18200 | 114327 |
| RValue_free | 13571 | 85663 |
| resolveVariableWrite | 10082 | 81220 |
| mixAndWrite | 14143 | 76964 |
| resolveVariableRead | 10325 | 66706 |
| stackPopInt32 | 6649 | 66555 |
| swrRunsDrawOnto | 11775 | 61445 |
| swrNote | 7752 | 58165 |
| memset | 7821 | 57762 |
| handlePush | 6883 | 57334 |
| SWRenderer_profDrawSprite | 8447 | 52525 |
| builtin_draw_sprite | 7338 | 51764 |
| pop_arg | 8292 | 49857 |
| sn_write | 5112 | 47621 |


### deltarune/bmenu/trace

Top 30 by refill count account for 83.01% of all I refills and 3.96% of the frame in attributed I block. Top 30 by I block account for 4.00% of the frame.

I refills:

| Function | I refills | I block cycles | Frame share |
| --- | --- | --- | --- |
| executeLoop | 18391 | 411174 | 0.893% |
| builtin_draw_sprite | 5475 | 215254 | 0.468% |
| printf_core | 5387 | 123153 | 0.267% |
| resolveVariableWrite | 4675 | 139122 | 0.302% |
| swrDrawSpriteInternal | 3828 | 133311 | 0.290% |
| vfprintf | 3775 | 146822 | 0.319% |
| Instance_setSelfVar | 3675 | 128330 | 0.279% |
| frame_tick | 2587 | 33606 | 0.073% |
| __udivdi3 | 1813 | 85328 | 0.185% |
| stackPopInt32 | 1677 | 39989 | 0.087% |
| handleCall | 1609 | 46072 | 0.100% |
| Runner_draw | 1099 | 37092 | 0.081% |
| handlePush | 1093 | 28891 | 0.063% |
| swrNote | 1038 | 30519 | 0.066% |
| swrMirrorFlush | 968 | 19014 | 0.041% |
| resolveVariableRead | 841 | 29671 | 0.064% |
| swrDrawText | 794 | 27307 | 0.059% |
| tryReadStaticFallback.isra.0 | 789 | 0 | 0.000% |
| __moddi3 | 768 | 0 | 0.000% |
| VM_callCodeIndex | 628 | 18610 | 0.040% |
| malloc | 536 | 18282 | 0.040% |
| free | 488 | 16954 | 0.037% |
| handleConv | 469 | 15623 | 0.034% |
| SWRenderer_profDrawRectangle | 407 | 11332 | 0.025% |
| memcpy | 350 | 24082 | 0.052% |
| __muldf3 | 250 | 8445 | 0.018% |
| stbds_hm_find_slot | 248 | 8399 | 0.018% |
| Profiler_exit | 247 | 11393 | 0.025% |
| VMBuiltins_getVariable | 242 | 7641 | 0.017% |
| Profiler_enter | 239 | 7110 | 0.015% |


I block cycles:

| Function | I refills | I block cycles | Frame share |
| --- | --- | --- | --- |
| executeLoop | 18391 | 411174 | 0.893% |
| builtin_draw_sprite | 5475 | 215254 | 0.468% |
| vfprintf | 3775 | 146822 | 0.319% |
| resolveVariableWrite | 4675 | 139122 | 0.302% |
| swrDrawSpriteInternal | 3828 | 133311 | 0.290% |
| Instance_setSelfVar | 3675 | 128330 | 0.279% |
| printf_core | 5387 | 123153 | 0.267% |
| __udivdi3 | 1813 | 85328 | 0.185% |
| handleCall | 1609 | 46072 | 0.100% |
| stackPopInt32 | 1677 | 39989 | 0.087% |
| Runner_draw | 1099 | 37092 | 0.081% |
| frame_tick | 2587 | 33606 | 0.073% |
| swrNote | 1038 | 30519 | 0.066% |
| resolveVariableRead | 841 | 29671 | 0.064% |
| handlePush | 1093 | 28891 | 0.063% |
| swrDrawText | 794 | 27307 | 0.059% |
| memcpy | 350 | 24082 | 0.052% |
| swrMirrorFlush | 968 | 19014 | 0.041% |
| VM_callCodeIndex | 628 | 18610 | 0.040% |
| malloc | 536 | 18282 | 0.040% |
| free | 488 | 16954 | 0.037% |
| handleConv | 469 | 15623 | 0.034% |
| Profiler_exit | 247 | 11393 | 0.025% |
| SWRenderer_profDrawRectangle | 407 | 11332 | 0.025% |
| __truncdfsf2 | 210 | 9682 | 0.021% |
| executeCode | 207 | 9414 | 0.020% |
| RValue_toString.isra.0 | 219 | 8582 | 0.019% |
| __muldf3 | 250 | 8445 | 0.018% |
| stbds_hm_find_slot | 248 | 8399 | 0.018% |
| VMBuiltins_setVariable | 235 | 8281 | 0.018% |


Top retiring functions, with overlapping waits charged to their consumers:

| Function | Retired | RAW cycles | Load dependency | Multiply dependency | FP dependency | Store-buffer wait |
| --- | --- | --- | --- | --- | --- | --- |
| frame_tick | 6422311 | 647624 | 647624 | 0 | 0 | 0 |
| executeLoop | 3369440 | 851262 | 531208 | 0 | 95128 | 383 |
| swrDrawSpriteInternal | 3014725 | 806788 | 708947 | 14834 | 0 | 50 |
| memcpy | 2874638 | 13060 | 0 | 0 | 0 | 5934 |
| swrTiledHeldWrite | 2012937 | 352024 | 304039 | 17187 | 0 | 103311 |
| printf_core | 1531886 | 250405 | 197179 | 7342 | 0 | 533 |
| swrRunsDrawOnto | 1241751 | 224482 | 79246 | 0 | 0 | 95303 |
| mixAndWrite | 891753 | 197747 | 101007 | 4800 | 0 | 0 |
| __fwritex | 714763 | 75060 | 75060 | 0 | 0 | 0 |
| swrDrawHLineInt.part.0 | 450504 | 2304 | 1728 | 0 | 0 | 0 |
| handlePush | 334874 | 24194 | 17850 | 0 | 0 | 0 |
| resolveVariableRead | 328696 | 34414 | 22439 | 0 | 0 | 0 |
| swrNote | 252999 | 24282 | 22454 | 0 | 0 | 0 |
| handleCall | 248637 | 38482 | 32174 | 0 | 0 | 0 |
| memset | 248237 | 0 | 0 | 0 | 0 | 5309 |
| strncmp | 237192 | 64638 | 64638 | 0 | 0 | 0 |
| IntRValueHashMap_findSlot | 235686 | 81865 | 62377 | 0 | 0 | 0 |
| SWRenderer_profDrawTileRun | 213345 | 72651 | 23286 | 11553 | 26256 | 0 |
| Runner_draw | 201595 | 72785 | 68871 | 2100 | 1050 | 183 |
| stackPush | 172271 | 15650 | 15650 | 0 | 0 | 0 |


Top branch recovery sites, grouped by function:

| Function | Mispredicts | Recovery envelope cycles |
| --- | --- | --- |
| executeLoop | 194295 | 1237654 |
| printf_core | 97310 | 632342 |
| memcpy | 87342 | 521476 |
| swrDrawSpriteInternal | 85918 | 511207 |
| __fwritex | 21548 | 129819 |
| frame_tick | 19453 | 125952 |
| handleCall | 16597 | 104631 |
| mixAndWrite | 14307 | 77618 |
| IntRValueHashMap_findSlot | 12929 | 77337 |
| builtin_draw_sprite | 7757 | 63647 |
| VMBuiltins_getVariable | 10371 | 62775 |
| swrRunsDrawOnto | 11624 | 60701 |
| resolveVariableWrite | 8852 | 59895 |
| vfprintf | 6978 | 59732 |
| SWRenderer_profDrawSprite | 9115 | 56569 |
| pop_arg | 8298 | 49821 |
| RValue_free | 7522 | 48982 |
| memset | 6474 | 42166 |
| swrNote | 6651 | 41560 |
| resolveVariableRead | 6315 | 40081 |


## Interpretation and Pocket comparability

Timing CPI ranges from 1.789 to 1.805 across the Deltarune windows and is 1.960 in Undertale. Execution freezes occupy 0.87–2.13% of timing frames, while branch-recovery envelopes occupy 10.48–14.85% and RAW dependencies 9.63–13.14%. Hardware FPU/divider freezes are not dominant; branches, dependencies, cache waits and executed work all matter. These overlapping observations do not identify a single bottleneck for the device probe.

undertale/flowey/timing: CPI 1.960; I block 8.42%, D block 8.75%, cache union 17.10%. No retirement on 48.98% of clocks.

undertale/flowey/trace: CPI 1.836; I block 7.57%, D block 7.45%, cache union 14.92%. No retirement on 45.52% of clocks.

deltarune/dodge/timing: CPI 1.805; I block 5.65%, D block 4.48%, cache union 10.11%. No retirement on 44.59% of clocks.

deltarune/dodge/trace: CPI 1.656; I block 4.24%, D block 3.71%, cache union 7.93%. No retirement on 39.62% of clocks.

deltarune/field/timing: CPI 1.793; I block 6.20%, D block 3.74%, cache union 9.92%. No retirement on 44.23% of clocks.

deltarune/field/trace: CPI 1.599; I block 4.18%, D block 2.78%, cache union 6.95%. No retirement on 37.47% of clocks.

deltarune/bmenu/timing: CPI 1.789; I block 6.70%, D block 4.31%, cache union 11.00%. No retirement on 44.10% of clocks.

deltarune/bmenu/trace: CPI 1.615; I block 4.81%, D block 3.42%, cache union 8.21%. No retirement on 38.06% of clocks.

I-cache refill blocking does not dominate these complete frames. The recorded alternatives show where pipeline waits occur, including overlaps, but no single signal proves the cause of the device’s isolated sprite probe. The measured full-frame CPI should not be substituted for its reported roughly 10 cycles/instruction. Isolating the same probe in a matching binary would still be required to decide that path’s dominant cost. No free-refill/unlimited-cache or other hardware counterfactual was run.

Frozen runner `f1d8542`; OS `8318f25`; SDK `7882a0d`; container GCC 13.2.0. Builds use `-O2 -ffunction-sections -fdata-sections -falign-functions=64 -falign-loops=64`, matching those SDK alignment flags. The device’s v0.7/perf build has different source/compiler/link context, so its layout is not established comparable. No `hot-sprites.ld` ordering was applied. Global OF_PC, legacy services, native scripts disabled, harness-allocated cached framebuffer, fixed 800 audio pairs, deterministic free clock. Timing omits per-VM-instruction `frame_tick`/`frame_event` and in-loop PCM hashing; trace changes instructions and cache contents.

The timed loop reaches game, rendering and mixing code, but allocator/kernel/storage/audio services are substituted. No physical SD latency, interrupts, GPU/display scheduling or full production ABI is modeled. Quiet excludes diagnostic scanout traffic; board contention may change refill tails. Flowey/dodge are battle windows; field is walking; bmenu samples attack meters. Each window begins with cold CPU caches, then runs three consecutive frames.

## Verification and evidence

Each measured replay matches all original cycles and oracles. Raw CSV, ELF, simulator, copied observer/wrapper, CPU, captures and source results are hash-verified and freshly reanalyzed. CPU parameter changes are `{}`. Additional disabled, corrupted-oracle and scanout controls are recorded below. Docker mounts only an independent harness case; no game worktree, original SDK/OS or SD card is changed.

| Window/build | Observer version | ELF SHA-256 | Result SHA-256 |
| --- | --- | --- | --- |
| undertale/flowey/timing | 0711991b745113db | 534dd0ff1368aa6da9b2dec1a65207fb67f83cc5023ca47aa9e512a091d74db9 | 3ede3acfbcc9e3eb680791aea74f2cff961bbe2e1dd6d4b6f95248b8e2ce996c |
| undertale/flowey/trace | 0711991b745113db | ad2c916e08d1ea55abe68d1cd67e0417d080e79a13dc0fb2f001d4621aaee8c2 | 8a8bb130b931dedcdb400c0eca0d513ca65d199a631544fea6030353c9251e64 |
| deltarune/dodge/timing | 0711991b745113db | ef3e9d9101d9a88fbacd46501700068ddd0d1b2677db1f4ce19638800d36cdb0 | b73c46e0d6d896fee5612c547704808101c790492d7bdd53d77257d5da027dce |
| deltarune/dodge/trace | 0711991b745113db | 0996687e17af0c9dcbc6aa079c603ca6a52bb9c01b327aafcc812d7e147e2c26 | 9cabacad27758e641be1429ad1b61356f1c030c7380bd3e8e009ae27206a2a5e |
| deltarune/field/timing | 0711991b745113db | d63cc5086538e2d71f2b7c825cb119cf49c1aef32b9ad70653c4eeae9213c8fd | 2c7b9f59fb10d981c0e80109fdb567a8a625361881a52d88589ee5d996f4449f |
| deltarune/field/trace | 0711991b745113db | 04f278c31d45f63b2cf04a764920c2155ca1508926312e36f3b802192f7267a9 | e29baec7b4657980e5983b89accb124420e37c162b3010721ed8f6c2fbfc9a38 |
| deltarune/bmenu/timing | 0711991b745113db | 688d0fd8881075b4633d0c4dda82bb4358febc6460c293af0c0d5386eaa1c9d6 | 9a61c60f53815dc21e06b7291f86ccb75be19ccde5799e32a937efdd5e949bce |
| deltarune/bmenu/trace | 0711991b745113db | 6f990ede2e36391ccc5ee9cf98a990454a60e5e09f7f8f7e3405beb0bdd7ec17 | 81b43133e2dc59f77e16a4a4a6a07ad3d8f4c8cba22ac2e9994e056c2e4b9f39 |


| Window | Placement | Mode | Control | Result SHA-256 |
| --- | --- | --- | --- | --- |
| deltarune/dodge | sdram | speed | corrupted oracle rejected | c1335ac5f7d42b1321dad914e5d8adb90cc4f41d078d9282299fb06ac95a16bf |
| deltarune/dodge | sdram | speed | disabled, identical | 4731869d325d31d70d444046698d7eee7bf47dca5062e75c87174008c4a38c6b |
| deltarune/dodge | sdram | speed | corrupted oracle rejected | 6511f6bba880ff8191a73fa44598bb16021700de63228fb77cd255bccfda8978 |
| undertale/flowey | sdram | speed | corrupted oracle rejected | 0dab81d6d9f44fd27af82222eb0a5c86e39301ce2e2b74083e088ef85f2b4e2c |
| undertale/flowey | sdram | speed | disabled, identical | ea430e0f3f147ac8082b19a09eebae30b07e95e12f1a364c12884f2e7acf1a59 |
| undertale/flowey | sdram | speed | corrupted oracle rejected | 410271ab2ea6261ae1568ad8c3f53933c4921e05a9cfef0f0c12f58bd6435fdb |
| deltarune/dodge | sdram | accuracy | scanout, identical | 051df20458443f6f92f18b41bb598f8e821cc501ba00b766f28deda6754b5b1e |
| deltarune/dodge | bram | accuracy | scanout, identical | b787c9f218ddfd20e3bcd50e3e578204caffc02fc6661bd04c1f225759a7bd1c |
| undertale/flowey | sdram | accuracy | scanout, identical | d59afe463ee395f5234b893be31ef0036735ff69941f0b58df0509ea48bb7019 |
| undertale/flowey | bram | accuracy | scanout, identical | 5113f312d1f644ab58c09e621fd7b376b985eeeef392d112672b8b9b17aafbed |
| deltarune/field | sdram | speed | disabled, identical | 95780814924ce64f6f75796080ef5c526840f32f3f99967adbfd763317729f85 |
