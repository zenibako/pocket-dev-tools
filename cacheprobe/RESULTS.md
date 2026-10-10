# Frozen f1d8542 cache profile (2026-10-10)

Simulated 100 MHz os25, Speed mode, SDRAM, quiet traffic. Each window has three consecutive frames; the first starts with cold CPU caches. Traced and timing are separate ELFs. Timing omits `frame_tick`, `frame_event` and in-loop PCM hashing.

I block is the union of the fetch refill hold and the pinned CPU’s miss-to-fetch-recovery waiting event. D block is the LSU refill waiter halting dispatch. These are cycles of cache-related pipeline blocking, not uniquely attributable lost execution cycles: older instructions can still commit. The union removes I/D overlap; its no-commit subset is reported separately. A refill’s full bus latency is not a CPU stall; speculative next-line I-cache prefetches are included.

## Undertale

| Window | Build | Frame | Frame cycles | I block | D block | Overlap | I refills | D refills | I cycles/refill | D cycles/refill |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| flowey | timing | 2400 | 1273699 | 109864 | 108364 | 832 | 3375 | 4403 | 78.08 | 64.21 |
| flowey | timing | 2401 | 1261817 | 104823 | 111820 | 990 | 3205 | 4134 | 78.80 | 67.94 |
| flowey | timing | 2402 | 1266096 | 105361 | 112335 | 752 | 3229 | 4141 | 78.82 | 67.99 |
| flowey | trace | 2400 | 1491368 | 115396 | 108180 | 1522 | 3528 | 4403 | 78.32 | 64.39 |
| flowey | trace | 2401 | 1480170 | 110606 | 111711 | 1500 | 3363 | 4137 | 79.31 | 67.95 |
| flowey | trace | 2402 | 1486319 | 111331 | 112350 | 1539 | 3380 | 4144 | 79.25 | 68.01 |


## Deltarune Chapter 1

| Window | Build | Frame | Frame cycles | I block | D block | Overlap | I refills | D refills | I cycles/refill | D cycles/refill |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dodge | timing | 3323 | 16253087 | 921864 | 690546 | 2531 | 30459 | 17307 | 72.26 | 67.71 |
| dodge | timing | 3324 | 17345350 | 965914 | 774487 | 2908 | 31811 | 19492 | 72.45 | 66.96 |
| dodge | timing | 3325 | 16161063 | 925536 | 762493 | 2254 | 30584 | 18547 | 72.23 | 67.14 |
| dodge | trace | 3323 | 18598875 | 787283 | 652246 | 3565 | 27460 | 16605 | 71.27 | 68.46 |
| dodge | trace | 3324 | 19749882 | 835870 | 735467 | 4017 | 29007 | 18786 | 71.49 | 67.52 |
| dodge | trace | 3325 | 18494729 | 788501 | 721855 | 3570 | 27522 | 17803 | 71.33 | 67.69 |
| field | timing | 2800 | 9972504 | 622926 | 372211 | 1300 | 20824 | 9574 | 71.88 | 66.54 |
| field | timing | 2801 | 9945983 | 614772 | 371378 | 1193 | 20571 | 9523 | 71.74 | 65.88 |
| field | timing | 2802 | 9932403 | 612057 | 371519 | 1359 | 20523 | 9485 | 71.75 | 65.89 |
| field | trace | 2800 | 12104412 | 512053 | 335781 | 1557 | 18421 | 8883 | 70.67 | 67.76 |
| field | trace | 2801 | 12067190 | 501830 | 334650 | 1481 | 18146 | 8827 | 70.56 | 66.88 |
| field | trace | 2802 | 12057405 | 501831 | 335472 | 1457 | 18140 | 8786 | 70.54 | 67.06 |
| bmenu | timing | 3120 | 13295652 | 882163 | 576800 | 1728 | 29015 | 15239 | 72.20 | 70.12 |
| bmenu | timing | 3121 | 12800685 | 868116 | 533321 | 1699 | 28547 | 14261 | 72.12 | 71.31 |
| bmenu | timing | 3122 | 12943150 | 865892 | 571816 | 1905 | 28520 | 15102 | 72.19 | 70.21 |
| bmenu | trace | 3120 | 15646618 | 750515 | 540957 | 2297 | 26230 | 14571 | 71.33 | 71.14 |
| bmenu | trace | 3121 | 15128364 | 731585 | 498304 | 2204 | 25669 | 13587 | 71.14 | 72.21 |
| bmenu | trace | 3122 | 15266235 | 732170 | 534510 | 2576 | 25668 | 14403 | 71.30 | 71.14 |


## Frame shares and measured distributions

Shares are weighted by the three frames’ cycles. Distribution quantiles are pooled over accepted refills in the window, using order statistic floor((N−1)×p/100). Latency includes both handshake edges. The machine-readable report retains exact histograms, per-frame distributions, first-beat latency, AR backpressure, boundary-crossing transfers and outstanding-transaction unions.

| Game | Window | Build | I block | D block | Union | Union without commit | Fetch hold cycles | Miss recovery cycles | Miss events |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| undertale | flowey | timing | 8.42% | 8.75% | 17.10% | 16.52% | 42768 | 281826 | 11807 |
| undertale | flowey | trace | 7.57% | 7.45% | 14.92% | 14.40% | 41631 | 299756 | 12530 |
| deltarune | dodge | timing | 5.65% | 4.48% | 10.11% | 9.66% | 380714 | 2458942 | 108179 |
| deltarune | dodge | trace | 4.24% | 3.71% | 7.93% | 7.58% | 309924 | 2131338 | 99427 |
| deltarune | field | timing | 6.20% | 3.74% | 9.92% | 9.40% | 242331 | 1622342 | 70795 |
| deltarune | field | trace | 4.18% | 2.78% | 6.95% | 6.58% | 184544 | 1348339 | 64062 |
| deltarune | bmenu | timing | 6.70% | 4.31% | 11.00% | 10.45% | 348767 | 2291460 | 100257 |
| deltarune | bmenu | trace | 4.81% | 3.42% | 8.21% | 7.80% | 280060 | 1960649 | 92034 |


| Game | Window | Build | Cache | Refills | Min | Mean | p50 | p90 | p99 | Max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| undertale | flowey | timing | I | 9809 | 22 | 78.56 | 69 | 107 | 174 | 276 |
| undertale | flowey | timing | D | 12678 | 49 | 66.66 | 52 | 100 | 169 | 222 |
| undertale | flowey | trace | I | 10271 | 49 | 78.95 | 69 | 108 | 187 | 266 |
| undertale | flowey | trace | D | 12684 | 49 | 66.74 | 52 | 101 | 170 | 212 |
| deltarune | dodge | timing | I | 92854 | 22 | 72.31 | 65 | 98 | 144 | 264 |
| deltarune | dodge | timing | D | 55346 | 49 | 67.26 | 54 | 107 | 207 | 276 |
| deltarune | dodge | trace | I | 83989 | 22 | 71.37 | 59 | 98 | 144 | 279 |
| deltarune | dodge | trace | D | 53194 | 49 | 67.87 | 54 | 108 | 211 | 237 |
| deltarune | field | timing | I | 61918 | 22 | 71.79 | 64 | 98 | 118 | 222 |
| deltarune | field | timing | D | 28582 | 49 | 66.11 | 54 | 108 | 208 | 233 |
| deltarune | field | trace | I | 54707 | 22 | 70.59 | 55 | 98 | 120 | 216 |
| deltarune | field | trace | D | 26496 | 49 | 67.23 | 54 | 110 | 210 | 232 |
| deltarune | bmenu | timing | I | 86082 | 22 | 72.17 | 65 | 98 | 143 | 272 |
| deltarune | bmenu | timing | D | 44602 | 49 | 70.53 | 54 | 135 | 215 | 276 |
| deltarune | bmenu | trace | I | 77567 | 22 | 71.26 | 58 | 98 | 142 | 281 |
| deltarune | bmenu | trace | D | 42561 | 49 | 71.48 | 54 | 142 | 216 | 241 |


The 22/39-cycle I-cache observations are rare refills at boot-BRAM addresses `0x0`/`0x40`, outside the application ELF’s function ranges. They remain in the unattributed bucket. The distribution covers the actual I-cache bus, including those non-SDRAM addresses, rather than filtering to SDRAM code alone.

## Top 30 functions in each window and build

Counts use the 64-byte refill line base. Blocking cycles use the initiating miss PC while the miss-recovery event is active, otherwise the held fetch PC. Consequently a function with many prefetched lines need not have many blocked cycles. ELF padding and absent symbols stay explicitly unattributed and are reported separately from the 30 named functions. Per-function “bus service” sums overlapping refill latencies; never interpret it as frame time. `executeLoop` is in SDRAM in all these cases.

### undertale flowey — timing

Top 30 by count cover 57.38% of I refills and 4.85% of frame cycles in I blocking. Top 30 by blocking cover 4.98% of frame cycles.

Unattributed: 157 refills, 360 I-block cycles (0.009% of the frame cycles).

By refill count

| Rank | ELF function | I refills | I bus service cycles | I block cycles | Frame share |
| --- | --- | --- | --- | --- | --- |
| 1 | `executeLoop` | 1044 | 76298 | 29577 | 0.778% |
| 2 | `resolveVariableWrite` | 506 | 38750 | 16500 | 0.434% |
| 3 | `swrDrawSpriteInternal` | 449 | 38327 | 18365 | 0.483% |
| 4 | `handlePush` | 255 | 19906 | 6452 | 0.170% |
| 5 | `printf_core` | 249 | 17815 | 7951 | 0.209% |
| 6 | `Runner_step` | 214 | 18286 | 6896 | 0.181% |
| 7 | `__subdf3` | 204 | 14383 | 7643 | 0.201% |
| 8 | `__adddf3` | 190 | 13223 | 5808 | 0.153% |
| 9 | `swrDrawText` | 165 | 13399 | 7401 | 0.195% |
| 10 | `__divdf3` | 161 | 11125 | 4805 | 0.126% |
| 11 | `VM_callCodeIndex` | 153 | 12582 | 5302 | 0.139% |
| 12 | `IntRValueHashMap_getOrInsertUndefined` | 150 | 12387 | 3488 | 0.092% |
| 13 | `vfprintf` | 136 | 9447 | 3485 | 0.092% |
| 14 | `Runner_getMouseRoomPosition` | 132 | 9239 | 3178 | 0.084% |
| 15 | `loop` | 131 | 11389 | 5760 | 0.152% |
| 16 | `__muldf3` | 130 | 8601 | 4577 | 0.120% |
| 17 | `malloc` | 129 | 8804 | 4755 | 0.125% |
| 18 | `VM_executeCode` | 122 | 9929 | 3902 | 0.103% |
| 19 | `resolveVariableRead` | 121 | 9993 | 3918 | 0.103% |
| 20 | `handleCall` | 105 | 7975 | 2958 | 0.078% |
| 21 | `VMBuiltins_getVariable` | 100 | 7935 | 3781 | 0.099% |
| 22 | `swrNote` | 100 | 8409 | 2345 | 0.062% |
| 23 | `memset` | 96 | 7716 | 5864 | 0.154% |
| 24 | `SWRenderer_profDrawRectangle` | 95 | 7421 | 3733 | 0.098% |
| 25 | `__truncdfsf2` | 94 | 7051 | 4410 | 0.116% |
| 26 | `swrOverlayFlushHeld` | 87 | 6713 | 1818 | 0.048% |
| 27 | `__udivdi3` | 86 | 5704 | 3569 | 0.094% |
| 28 | `strcasecmp` | 76 | 6217 | 268 | 0.007% |
| 29 | `Runner_draw` | 75 | 6073 | 3699 | 0.097% |
| 30 | `platformHandleEvents` | 73 | 5949 | 2314 | 0.061% |


By I-cache blocking cycles

| Rank | ELF function | I refills | I bus service cycles | I block cycles | Frame share |
| --- | --- | --- | --- | --- | --- |
| 1 | `executeLoop` | 1044 | 76298 | 29577 | 0.778% |
| 2 | `swrDrawSpriteInternal` | 449 | 38327 | 18365 | 0.483% |
| 3 | `resolveVariableWrite` | 506 | 38750 | 16500 | 0.434% |
| 4 | `printf_core` | 249 | 17815 | 7951 | 0.209% |
| 5 | `__subdf3` | 204 | 14383 | 7643 | 0.201% |
| 6 | `swrDrawText` | 165 | 13399 | 7401 | 0.195% |
| 7 | `Runner_step` | 214 | 18286 | 6896 | 0.181% |
| 8 | `handlePush` | 255 | 19906 | 6452 | 0.170% |
| 9 | `memset` | 96 | 7716 | 5864 | 0.154% |
| 10 | `__adddf3` | 190 | 13223 | 5808 | 0.153% |
| 11 | `loop` | 131 | 11389 | 5760 | 0.152% |
| 12 | `VM_callCodeIndex` | 153 | 12582 | 5302 | 0.139% |
| 13 | `__divdf3` | 161 | 11125 | 4805 | 0.126% |
| 14 | `malloc` | 129 | 8804 | 4755 | 0.125% |
| 15 | `__muldf3` | 130 | 8601 | 4577 | 0.120% |
| 16 | `__truncdfsf2` | 94 | 7051 | 4410 | 0.116% |
| 17 | `resolveVariableRead` | 121 | 9993 | 3918 | 0.103% |
| 18 | `VM_executeCode` | 122 | 9929 | 3902 | 0.103% |
| 19 | `VMBuiltins_getVariable` | 100 | 7935 | 3781 | 0.099% |
| 20 | `SWRenderer_profDrawRectangle` | 95 | 7421 | 3733 | 0.098% |
| 21 | `Runner_draw` | 75 | 6073 | 3699 | 0.097% |
| 22 | `__udivdi3` | 86 | 5704 | 3569 | 0.094% |
| 23 | `IntRValueHashMap_getOrInsertUndefined` | 150 | 12387 | 3488 | 0.092% |
| 24 | `vfprintf` | 136 | 9447 | 3485 | 0.092% |
| 25 | `memcpy` | 58 | 4797 | 3416 | 0.090% |
| 26 | `Runner_getMouseRoomPosition` | 132 | 9239 | 3178 | 0.084% |
| 27 | `SWRenderer_drawSprite` | 60 | 5947 | 3066 | 0.081% |
| 28 | `handleCall` | 105 | 7975 | 2958 | 0.078% |
| 29 | `vsnprintf` | 43 | 3457 | 2583 | 0.068% |
| 30 | `swrNote` | 100 | 8409 | 2345 | 0.062% |


### undertale flowey — trace

Top 30 by count cover 56.91% of I refills and 4.38% of frame cycles in I blocking. Top 30 by blocking cover 4.48% of frame cycles.

Unattributed: 159 refills, 1785 I-block cycles (0.040% of the frame cycles).

By refill count

| Rank | ELF function | I refills | I bus service cycles | I block cycles | Frame share |
| --- | --- | --- | --- | --- | --- |
| 1 | `executeLoop` | 944 | 69663 | 28962 | 0.650% |
| 2 | `resolveVariableWrite` | 432 | 33791 | 15755 | 0.353% |
| 3 | `swrDrawSpriteInternal` | 431 | 38086 | 16824 | 0.377% |
| 4 | `printf_core` | 392 | 27769 | 13010 | 0.292% |
| 5 | `handlePush` | 323 | 25055 | 7998 | 0.179% |
| 6 | `__subdf3` | 237 | 17676 | 8982 | 0.201% |
| 7 | `Runner_step` | 222 | 19034 | 7730 | 0.173% |
| 8 | `malloc` | 219 | 16093 | 7849 | 0.176% |
| 9 | `__adddf3` | 185 | 12976 | 6283 | 0.141% |
| 10 | `swrDrawText` | 181 | 15403 | 7642 | 0.171% |
| 11 | `VM_callCodeIndex` | 175 | 14657 | 5752 | 0.129% |
| 12 | `Runner_draw` | 168 | 13257 | 7612 | 0.171% |
| 13 | `__muldf3` | 158 | 11031 | 4325 | 0.097% |
| 14 | `Runner_getMouseRoomPosition` | 132 | 9498 | 3451 | 0.077% |
| 15 | `loop` | 132 | 11354 | 4940 | 0.111% |
| 16 | `IntRValueHashMap_getOrInsertUndefined` | 130 | 12054 | 2960 | 0.066% |
| 17 | `free` | 127 | 10016 | 5581 | 0.125% |
| 18 | `__divdf3` | 126 | 8726 | 3676 | 0.082% |
| 19 | `memcpy` | 123 | 8615 | 4307 | 0.097% |
| 20 | `VM_executeCode` | 117 | 9371 | 3203 | 0.072% |
| 21 | `resolveVariableRead` | 107 | 8157 | 3357 | 0.075% |
| 22 | `SWRenderer_drawSprite` | 99 | 10005 | 3464 | 0.078% |
| 23 | `handleCall` | 97 | 7059 | 2745 | 0.062% |
| 24 | `strcasecmp` | 97 | 7227 | 945 | 0.021% |
| 25 | `VMBuiltins_getVariable` | 90 | 7107 | 3267 | 0.073% |
| 26 | `__truncdfsf2` | 90 | 6416 | 4249 | 0.095% |
| 27 | `vfprintf` | 82 | 5643 | 3792 | 0.085% |
| 28 | `handlePop` | 81 | 5888 | 2270 | 0.051% |
| 29 | `swrNote` | 76 | 6389 | 1543 | 0.035% |
| 30 | `__udivdi3` | 72 | 4752 | 2737 | 0.061% |


By I-cache blocking cycles

| Rank | ELF function | I refills | I bus service cycles | I block cycles | Frame share |
| --- | --- | --- | --- | --- | --- |
| 1 | `executeLoop` | 944 | 69663 | 28962 | 0.650% |
| 2 | `swrDrawSpriteInternal` | 431 | 38086 | 16824 | 0.377% |
| 3 | `resolveVariableWrite` | 432 | 33791 | 15755 | 0.353% |
| 4 | `printf_core` | 392 | 27769 | 13010 | 0.292% |
| 5 | `__subdf3` | 237 | 17676 | 8982 | 0.201% |
| 6 | `handlePush` | 323 | 25055 | 7998 | 0.179% |
| 7 | `malloc` | 219 | 16093 | 7849 | 0.176% |
| 8 | `Runner_step` | 222 | 19034 | 7730 | 0.173% |
| 9 | `swrDrawText` | 181 | 15403 | 7642 | 0.171% |
| 10 | `Runner_draw` | 168 | 13257 | 7612 | 0.171% |
| 11 | `__adddf3` | 185 | 12976 | 6283 | 0.141% |
| 12 | `VM_callCodeIndex` | 175 | 14657 | 5752 | 0.129% |
| 13 | `free` | 127 | 10016 | 5581 | 0.125% |
| 14 | `loop` | 132 | 11354 | 4940 | 0.111% |
| 15 | `__muldf3` | 158 | 11031 | 4325 | 0.097% |
| 16 | `memcpy` | 123 | 8615 | 4307 | 0.097% |
| 17 | `__truncdfsf2` | 90 | 6416 | 4249 | 0.095% |
| 18 | `vfprintf` | 82 | 5643 | 3792 | 0.085% |
| 19 | `memset` | 55 | 4148 | 3748 | 0.084% |
| 20 | `__divdf3` | 126 | 8726 | 3676 | 0.082% |
| 21 | `SWRenderer_drawSprite` | 99 | 10005 | 3464 | 0.078% |
| 22 | `Runner_getMouseRoomPosition` | 132 | 9498 | 3451 | 0.077% |
| 23 | `resolveVariableRead` | 107 | 8157 | 3357 | 0.075% |
| 24 | `VMBuiltins_getVariable` | 90 | 7107 | 3267 | 0.073% |
| 25 | `VM_executeCode` | 117 | 9371 | 3203 | 0.072% |
| 26 | `IntRValueHashMap_getOrInsertUndefined` | 130 | 12054 | 2960 | 0.066% |
| 27 | `fabsf` | 0 | 0 | 2850 | 0.064% |
| 28 | `handleCall` | 97 | 7059 | 2745 | 0.062% |
| 29 | `__udivdi3` | 72 | 4752 | 2737 | 0.061% |
| 30 | `SWRenderer_profDrawRectangle` | 66 | 5034 | 2457 | 0.055% |


### deltarune dodge — timing

Top 30 by count cover 81.37% of I refills and 4.61% of frame cycles in I blocking. Top 30 by blocking cover 4.67% of frame cycles.

Unattributed: 663 refills, 3706 I-block cycles (0.007% of the frame cycles).

By refill count

| Rank | ELF function | I refills | I bus service cycles | I block cycles | Frame share |
| --- | --- | --- | --- | --- | --- |
| 1 | `executeLoop` | 18491 | 1249615 | 557773 | 1.121% |
| 2 | `printf_core` | 9933 | 691990 | 262067 | 0.527% |
| 3 | `builtin_draw_sprite` | 5272 | 377344 | 180663 | 0.363% |
| 4 | `Instance_setSelfVar` | 4032 | 309388 | 176243 | 0.354% |
| 5 | `resolveVariableRead` | 3809 | 276949 | 118068 | 0.237% |
| 6 | `resolveVariableWrite` | 3740 | 273093 | 69042 | 0.139% |
| 7 | `vfprintf` | 3069 | 204129 | 42412 | 0.085% |
| 8 | `handlePush` | 2940 | 227820 | 125559 | 0.252% |
| 9 | `swrDrawSpriteInternal` | 2620 | 208483 | 89311 | 0.179% |
| 10 | `__udivdi3` | 2379 | 184738 | 98592 | 0.198% |
| 11 | `memset` | 2254 | 166302 | 82621 | 0.166% |
| 12 | `swrNote` | 2109 | 152842 | 45861 | 0.092% |
| 13 | `sn_write` | 1994 | 137378 | 47064 | 0.095% |
| 14 | `vsnprintf` | 1597 | 133903 | 69011 | 0.139% |
| 15 | `Runner_draw` | 1089 | 82756 | 36948 | 0.074% |
| 16 | `free` | 1015 | 74339 | 32390 | 0.065% |
| 17 | `stackPopInt32` | 933 | 54028 | 31593 | 0.063% |
| 18 | `handleConv` | 830 | 59896 | 24521 | 0.049% |
| 19 | `__moddi3` | 828 | 44541 | 0 | 0.000% |
| 20 | `swrMirrorFlush` | 797 | 61435 | 23693 | 0.048% |
| 21 | `memcpy` | 787 | 56953 | 32092 | 0.064% |
| 22 | `swrDrawText` | 752 | 57034 | 28090 | 0.056% |
| 23 | `malloc` | 749 | 53751 | 23093 | 0.046% |
| 24 | `strcasecmp` | 705 | 48288 | 3250 | 0.007% |
| 25 | `VM_callCodeIndex` | 599 | 46073 | 17501 | 0.035% |
| 26 | `__subdf3` | 465 | 33732 | 17808 | 0.036% |
| 27 | `VMBuiltins_getVariable` | 452 | 35452 | 14758 | 0.030% |
| 28 | `Profiler_exit` | 449 | 36999 | 17744 | 0.036% |
| 29 | `__adddf3` | 444 | 31389 | 14749 | 0.030% |
| 30 | `handleCall` | 419 | 29473 | 11394 | 0.023% |


By I-cache blocking cycles

| Rank | ELF function | I refills | I bus service cycles | I block cycles | Frame share |
| --- | --- | --- | --- | --- | --- |
| 1 | `executeLoop` | 18491 | 1249615 | 557773 | 1.121% |
| 2 | `printf_core` | 9933 | 691990 | 262067 | 0.527% |
| 3 | `builtin_draw_sprite` | 5272 | 377344 | 180663 | 0.363% |
| 4 | `Instance_setSelfVar` | 4032 | 309388 | 176243 | 0.354% |
| 5 | `handlePush` | 2940 | 227820 | 125559 | 0.252% |
| 6 | `resolveVariableRead` | 3809 | 276949 | 118068 | 0.237% |
| 7 | `__udivdi3` | 2379 | 184738 | 98592 | 0.198% |
| 8 | `swrDrawSpriteInternal` | 2620 | 208483 | 89311 | 0.179% |
| 9 | `memset` | 2254 | 166302 | 82621 | 0.166% |
| 10 | `resolveVariableWrite` | 3740 | 273093 | 69042 | 0.139% |
| 11 | `vsnprintf` | 1597 | 133903 | 69011 | 0.139% |
| 12 | `sn_write` | 1994 | 137378 | 47064 | 0.095% |
| 13 | `swrNote` | 2109 | 152842 | 45861 | 0.092% |
| 14 | `vfprintf` | 3069 | 204129 | 42412 | 0.085% |
| 15 | `Runner_draw` | 1089 | 82756 | 36948 | 0.074% |
| 16 | `free` | 1015 | 74339 | 32390 | 0.065% |
| 17 | `memcpy` | 787 | 56953 | 32092 | 0.064% |
| 18 | `stackPopInt32` | 933 | 54028 | 31593 | 0.063% |
| 19 | `swrDrawText` | 752 | 57034 | 28090 | 0.056% |
| 20 | `handleConv` | 830 | 59896 | 24521 | 0.049% |
| 21 | `swrMirrorFlush` | 797 | 61435 | 23693 | 0.048% |
| 22 | `malloc` | 749 | 53751 | 23093 | 0.046% |
| 23 | `__subdf3` | 465 | 33732 | 17808 | 0.036% |
| 24 | `Profiler_exit` | 449 | 36999 | 17744 | 0.036% |
| 25 | `VM_callCodeIndex` | 599 | 46073 | 17501 | 0.035% |
| 26 | `__truncdfsf2` | 357 | 25626 | 15817 | 0.032% |
| 27 | `VMBuiltins_getVariable` | 452 | 35452 | 14758 | 0.030% |
| 28 | `__adddf3` | 444 | 31389 | 14749 | 0.030% |
| 29 | `executeCode` | 336 | 21328 | 13951 | 0.028% |
| 30 | `stbds_hm_find_slot` | 371 | 27192 | 12274 | 0.025% |


### deltarune dodge — trace

Top 30 by count cover 79.75% of I refills and 3.34% of frame cycles in I blocking. Top 30 by blocking cover 3.40% of frame cycles.

Unattributed: 1213 refills, 1791 I-block cycles (0.003% of the frame cycles).

By refill count

| Rank | ELF function | I refills | I bus service cycles | I block cycles | Frame share |
| --- | --- | --- | --- | --- | --- |
| 1 | `executeLoop` | 18825 | 1274790 | 422031 | 0.742% |
| 2 | `printf_core` | 5529 | 371877 | 128994 | 0.227% |
| 3 | `builtin_draw_sprite` | 5366 | 369856 | 210840 | 0.371% |
| 4 | `resolveVariableWrite` | 4918 | 342444 | 146861 | 0.258% |
| 5 | `swrDrawSpriteInternal` | 3850 | 292082 | 133749 | 0.235% |
| 6 | `vfprintf` | 3729 | 252936 | 144834 | 0.255% |
| 7 | `Instance_setSelfVar` | 3691 | 279417 | 129257 | 0.227% |
| 8 | `frame_tick` | 2567 | 180782 | 33178 | 0.058% |
| 9 | `__udivdi3` | 1800 | 142811 | 84734 | 0.149% |
| 10 | `handleCall` | 1746 | 119038 | 50229 | 0.088% |
| 11 | `stackPopInt32` | 1672 | 125297 | 40334 | 0.071% |
| 12 | `Runner_draw` | 1309 | 98734 | 44533 | 0.078% |
| 13 | `swrNote` | 1155 | 67051 | 30500 | 0.054% |
| 14 | `handlePush` | 1077 | 78809 | 28497 | 0.050% |
| 15 | `resolveVariableRead` | 1048 | 74732 | 36818 | 0.065% |
| 16 | `swrMirrorFlush` | 942 | 71628 | 18720 | 0.033% |
| 17 | `swrDrawText` | 811 | 60853 | 27308 | 0.048% |
| 18 | `tryReadStaticFallback.isra.0` | 807 | 53705 | 0 | 0.000% |
| 19 | `__moddi3` | 778 | 42070 | 0 | 0.000% |
| 20 | `VM_callCodeIndex` | 747 | 54251 | 22162 | 0.039% |
| 21 | `malloc` | 599 | 42581 | 19978 | 0.035% |
| 22 | `free` | 574 | 37106 | 20392 | 0.036% |
| 23 | `handleConv` | 574 | 42310 | 17782 | 0.031% |
| 24 | `__adddf3` | 474 | 33458 | 16367 | 0.029% |
| 25 | `__subdf3` | 459 | 32319 | 17115 | 0.030% |
| 26 | `memcpy` | 458 | 32498 | 29552 | 0.052% |
| 27 | `__muldf3` | 379 | 26568 | 12960 | 0.023% |
| 28 | `SWRenderer_profDrawRectangle` | 374 | 27294 | 11628 | 0.020% |
| 29 | `VMBuiltins_getVariable` | 373 | 30761 | 12282 | 0.022% |
| 30 | `__divdf3` | 354 | 23793 | 8796 | 0.015% |


By I-cache blocking cycles

| Rank | ELF function | I refills | I bus service cycles | I block cycles | Frame share |
| --- | --- | --- | --- | --- | --- |
| 1 | `executeLoop` | 18825 | 1274790 | 422031 | 0.742% |
| 2 | `builtin_draw_sprite` | 5366 | 369856 | 210840 | 0.371% |
| 3 | `resolveVariableWrite` | 4918 | 342444 | 146861 | 0.258% |
| 4 | `vfprintf` | 3729 | 252936 | 144834 | 0.255% |
| 5 | `swrDrawSpriteInternal` | 3850 | 292082 | 133749 | 0.235% |
| 6 | `Instance_setSelfVar` | 3691 | 279417 | 129257 | 0.227% |
| 7 | `printf_core` | 5529 | 371877 | 128994 | 0.227% |
| 8 | `__udivdi3` | 1800 | 142811 | 84734 | 0.149% |
| 9 | `handleCall` | 1746 | 119038 | 50229 | 0.088% |
| 10 | `Runner_draw` | 1309 | 98734 | 44533 | 0.078% |
| 11 | `stackPopInt32` | 1672 | 125297 | 40334 | 0.071% |
| 12 | `resolveVariableRead` | 1048 | 74732 | 36818 | 0.065% |
| 13 | `frame_tick` | 2567 | 180782 | 33178 | 0.058% |
| 14 | `swrNote` | 1155 | 67051 | 30500 | 0.054% |
| 15 | `memcpy` | 458 | 32498 | 29552 | 0.052% |
| 16 | `handlePush` | 1077 | 78809 | 28497 | 0.050% |
| 17 | `swrDrawText` | 811 | 60853 | 27308 | 0.048% |
| 18 | `VM_callCodeIndex` | 747 | 54251 | 22162 | 0.039% |
| 19 | `free` | 574 | 37106 | 20392 | 0.036% |
| 20 | `malloc` | 599 | 42581 | 19978 | 0.035% |
| 21 | `swrMirrorFlush` | 942 | 71628 | 18720 | 0.033% |
| 22 | `handleConv` | 574 | 42310 | 17782 | 0.031% |
| 23 | `__subdf3` | 459 | 32319 | 17115 | 0.030% |
| 24 | `__adddf3` | 474 | 33458 | 16367 | 0.029% |
| 25 | `__truncdfsf2` | 309 | 21886 | 14856 | 0.026% |
| 26 | `Profiler_exit` | 293 | 22982 | 13023 | 0.023% |
| 27 | `__muldf3` | 379 | 26568 | 12960 | 0.023% |
| 28 | `VMBuiltins_getVariable` | 373 | 30761 | 12282 | 0.022% |
| 29 | `SWRenderer_profDrawRectangle` | 374 | 27294 | 11628 | 0.020% |
| 30 | `stbds_hm_find_slot` | 330 | 28327 | 11397 | 0.020% |


### deltarune field — timing

Top 30 by count cover 90.16% of I refills and 5.53% of frame cycles in I blocking. Top 30 by blocking cover 5.58% of frame cycles.

Unattributed: 264 refills, 746 I-block cycles (0.002% of the frame cycles).

By refill count

| Rank | ELF function | I refills | I bus service cycles | I block cycles | Frame share |
| --- | --- | --- | --- | --- | --- |
| 1 | `executeLoop` | 14186 | 945180 | 417412 | 1.398% |
| 2 | `printf_core` | 7232 | 503327 | 191441 | 0.641% |
| 3 | `builtin_draw_sprite` | 4818 | 343946 | 164524 | 0.551% |
| 4 | `Instance_setSelfVar` | 3565 | 272438 | 154708 | 0.518% |
| 5 | `resolveVariableWrite` | 2951 | 215296 | 47501 | 0.159% |
| 6 | `vfprintf` | 2776 | 183319 | 33788 | 0.113% |
| 7 | `resolveVariableRead` | 2617 | 190653 | 78998 | 0.265% |
| 8 | `handlePush` | 2204 | 174630 | 99390 | 0.333% |
| 9 | `memset` | 1842 | 136176 | 65172 | 0.218% |
| 10 | `__udivdi3` | 1769 | 140450 | 78151 | 0.262% |
| 11 | `sn_write` | 1633 | 118446 | 38730 | 0.130% |
| 12 | `swrDrawSpriteInternal` | 1602 | 125789 | 52721 | 0.177% |
| 13 | `swrNote` | 1526 | 114377 | 35218 | 0.118% |
| 14 | `vsnprintf` | 1393 | 115904 | 55360 | 0.185% |
| 15 | `stackPopInt32` | 773 | 42707 | 25924 | 0.087% |
| 16 | `__moddi3` | 718 | 38447 | 0 | 0.000% |
| 17 | `swrMirrorFlush` | 564 | 42666 | 11571 | 0.039% |
| 18 | `free` | 518 | 36249 | 13969 | 0.047% |
| 19 | `strcasecmp` | 493 | 34227 | 2613 | 0.009% |
| 20 | `Runner_draw` | 458 | 33543 | 14814 | 0.050% |
| 21 | `handleConv` | 334 | 24929 | 11223 | 0.038% |
| 22 | `resolveLocalSlot` | 246 | 18510 | 4256 | 0.014% |
| 23 | `Runner_step` | 231 | 18929 | 7250 | 0.024% |
| 24 | `tryReadStaticFallback.isra.0` | 223 | 20997 | 0 | 0.000% |
| 25 | `memcpy` | 219 | 16556 | 11049 | 0.037% |
| 26 | `VMBuiltins_getVariable` | 218 | 17170 | 7658 | 0.026% |
| 27 | `executeCode` | 199 | 12300 | 8087 | 0.027% |
| 28 | `VMBuiltins_setVariable` | 182 | 14590 | 6285 | 0.021% |
| 29 | `VM_callCodeIndex` | 169 | 13247 | 6183 | 0.021% |
| 30 | `malloc` | 168 | 11400 | 5813 | 0.019% |


By I-cache blocking cycles

| Rank | ELF function | I refills | I bus service cycles | I block cycles | Frame share |
| --- | --- | --- | --- | --- | --- |
| 1 | `executeLoop` | 14186 | 945180 | 417412 | 1.398% |
| 2 | `printf_core` | 7232 | 503327 | 191441 | 0.641% |
| 3 | `builtin_draw_sprite` | 4818 | 343946 | 164524 | 0.551% |
| 4 | `Instance_setSelfVar` | 3565 | 272438 | 154708 | 0.518% |
| 5 | `handlePush` | 2204 | 174630 | 99390 | 0.333% |
| 6 | `resolveVariableRead` | 2617 | 190653 | 78998 | 0.265% |
| 7 | `__udivdi3` | 1769 | 140450 | 78151 | 0.262% |
| 8 | `memset` | 1842 | 136176 | 65172 | 0.218% |
| 9 | `vsnprintf` | 1393 | 115904 | 55360 | 0.185% |
| 10 | `swrDrawSpriteInternal` | 1602 | 125789 | 52721 | 0.177% |
| 11 | `resolveVariableWrite` | 2951 | 215296 | 47501 | 0.159% |
| 12 | `sn_write` | 1633 | 118446 | 38730 | 0.130% |
| 13 | `swrNote` | 1526 | 114377 | 35218 | 0.118% |
| 14 | `vfprintf` | 2776 | 183319 | 33788 | 0.113% |
| 15 | `stackPopInt32` | 773 | 42707 | 25924 | 0.087% |
| 16 | `Runner_draw` | 458 | 33543 | 14814 | 0.050% |
| 17 | `free` | 518 | 36249 | 13969 | 0.047% |
| 18 | `swrMirrorFlush` | 564 | 42666 | 11571 | 0.039% |
| 19 | `handleConv` | 334 | 24929 | 11223 | 0.038% |
| 20 | `memcpy` | 219 | 16556 | 11049 | 0.037% |
| 21 | `executeCode` | 199 | 12300 | 8087 | 0.027% |
| 22 | `VMBuiltins_getVariable` | 218 | 17170 | 7658 | 0.026% |
| 23 | `Runner_step` | 231 | 18929 | 7250 | 0.024% |
| 24 | `Profiler_exit` | 152 | 12500 | 6298 | 0.021% |
| 25 | `VMBuiltins_setVariable` | 182 | 14590 | 6285 | 0.021% |
| 26 | `VM_callCodeIndex` | 169 | 13247 | 6183 | 0.021% |
| 27 | `handlePop` | 166 | 11847 | 5855 | 0.020% |
| 28 | `malloc` | 168 | 11400 | 5813 | 0.019% |
| 29 | `__truncdfsf2` | 123 | 9020 | 5731 | 0.019% |
| 30 | `loop` | 130 | 11153 | 5565 | 0.019% |


### deltarune field — trace

Top 30 by count cover 88.59% of I refills and 3.66% of frame cycles in I blocking. Top 30 by blocking cover 3.72% of frame cycles.

Unattributed: 944 refills, 1153 I-block cycles (0.003% of the frame cycles).

By refill count

| Rank | ELF function | I refills | I bus service cycles | I block cycles | Frame share |
| --- | --- | --- | --- | --- | --- |
| 1 | `executeLoop` | 14836 | 1006989 | 307112 | 0.848% |
| 2 | `builtin_draw_sprite` | 4848 | 331707 | 188770 | 0.521% |
| 3 | `resolveVariableWrite` | 4212 | 286309 | 119452 | 0.330% |
| 4 | `printf_core` | 3480 | 230305 | 76802 | 0.212% |
| 5 | `Instance_setSelfVar` | 3156 | 236325 | 104838 | 0.289% |
| 6 | `vfprintf` | 2901 | 196266 | 120332 | 0.332% |
| 7 | `swrDrawSpriteInternal` | 2318 | 174791 | 83246 | 0.230% |
| 8 | `frame_tick` | 2035 | 143254 | 26508 | 0.073% |
| 9 | `__udivdi3` | 1530 | 123024 | 74965 | 0.207% |
| 10 | `stackPopInt32` | 1464 | 109899 | 35098 | 0.097% |
| 11 | `handleCall` | 1148 | 78054 | 32908 | 0.091% |
| 12 | `swrNote` | 809 | 44541 | 25134 | 0.069% |
| 13 | `tryReadStaticFallback.isra.0` | 711 | 47071 | 0 | 0.000% |
| 14 | `__moddi3` | 707 | 38104 | 0 | 0.000% |
| 15 | `swrMirrorFlush` | 606 | 45730 | 11602 | 0.032% |
| 16 | `Runner_draw` | 576 | 43047 | 19616 | 0.054% |
| 17 | `resolveVariableRead` | 518 | 37680 | 17350 | 0.048% |
| 18 | `handleConv` | 278 | 20913 | 9282 | 0.026% |
| 19 | `resolveLocalSlot` | 277 | 21130 | 5829 | 0.016% |
| 20 | `malloc` | 268 | 19624 | 9506 | 0.026% |
| 21 | `free` | 245 | 15328 | 8377 | 0.023% |
| 22 | `Runner_step` | 229 | 18661 | 6820 | 0.019% |
| 23 | `VM_callCodeIndex` | 217 | 16713 | 7658 | 0.021% |
| 24 | `VMBuiltins_getVariable` | 175 | 13944 | 5206 | 0.014% |
| 25 | `VMBuiltins_setVariable` | 175 | 13258 | 6174 | 0.017% |
| 26 | `handlePush` | 170 | 12096 | 4045 | 0.011% |
| 27 | `handlePop` | 157 | 11062 | 5460 | 0.015% |
| 28 | `executeCode` | 150 | 10909 | 6039 | 0.017% |
| 29 | `Runner_getMouseRoomPosition` | 138 | 9901 | 3804 | 0.010% |
| 30 | `__divdf3` | 132 | 9513 | 4325 | 0.012% |


By I-cache blocking cycles

| Rank | ELF function | I refills | I bus service cycles | I block cycles | Frame share |
| --- | --- | --- | --- | --- | --- |
| 1 | `executeLoop` | 14836 | 1006989 | 307112 | 0.848% |
| 2 | `builtin_draw_sprite` | 4848 | 331707 | 188770 | 0.521% |
| 3 | `vfprintf` | 2901 | 196266 | 120332 | 0.332% |
| 4 | `resolveVariableWrite` | 4212 | 286309 | 119452 | 0.330% |
| 5 | `Instance_setSelfVar` | 3156 | 236325 | 104838 | 0.289% |
| 6 | `swrDrawSpriteInternal` | 2318 | 174791 | 83246 | 0.230% |
| 7 | `printf_core` | 3480 | 230305 | 76802 | 0.212% |
| 8 | `__udivdi3` | 1530 | 123024 | 74965 | 0.207% |
| 9 | `stackPopInt32` | 1464 | 109899 | 35098 | 0.097% |
| 10 | `handleCall` | 1148 | 78054 | 32908 | 0.091% |
| 11 | `frame_tick` | 2035 | 143254 | 26508 | 0.073% |
| 12 | `swrNote` | 809 | 44541 | 25134 | 0.069% |
| 13 | `Runner_draw` | 576 | 43047 | 19616 | 0.054% |
| 14 | `resolveVariableRead` | 518 | 37680 | 17350 | 0.048% |
| 15 | `memcpy` | 112 | 7552 | 12685 | 0.035% |
| 16 | `swrMirrorFlush` | 606 | 45730 | 11602 | 0.032% |
| 17 | `malloc` | 268 | 19624 | 9506 | 0.026% |
| 18 | `handleConv` | 278 | 20913 | 9282 | 0.026% |
| 19 | `free` | 245 | 15328 | 8377 | 0.023% |
| 20 | `VM_callCodeIndex` | 217 | 16713 | 7658 | 0.021% |
| 21 | `Runner_step` | 229 | 18661 | 6820 | 0.019% |
| 22 | `loop` | 130 | 10746 | 6235 | 0.017% |
| 23 | `VMBuiltins_setVariable` | 175 | 13258 | 6174 | 0.017% |
| 24 | `executeCode` | 150 | 10909 | 6039 | 0.017% |
| 25 | `resolveLocalSlot` | 277 | 21130 | 5829 | 0.016% |
| 26 | `handlePop` | 157 | 11062 | 5460 | 0.015% |
| 27 | `VMBuiltins_getVariable` | 175 | 13944 | 5206 | 0.014% |
| 28 | `__truncdfsf2` | 103 | 7318 | 4866 | 0.013% |
| 29 | `__divdf3` | 132 | 9513 | 4325 | 0.012% |
| 30 | `__umoddi3` | 83 | 4768 | 4226 | 0.012% |


### deltarune bmenu — timing

Top 30 by count cover 84.86% of I refills and 5.68% of frame cycles in I blocking. Top 30 by blocking cover 5.73% of frame cycles.

Unattributed: 517 refills, 2466 I-block cycles (0.006% of the frame cycles).

By refill count

| Rank | ELF function | I refills | I bus service cycles | I block cycles | Frame share |
| --- | --- | --- | --- | --- | --- |
| 1 | `executeLoop` | 18056 | 1217043 | 541034 | 1.386% |
| 2 | `printf_core` | 9796 | 680972 | 259120 | 0.664% |
| 3 | `builtin_draw_sprite` | 5345 | 380575 | 182857 | 0.468% |
| 4 | `Instance_setSelfVar` | 3971 | 304993 | 172689 | 0.442% |
| 5 | `resolveVariableRead` | 3678 | 266730 | 113372 | 0.290% |
| 6 | `resolveVariableWrite` | 3428 | 249448 | 62142 | 0.159% |
| 7 | `vfprintf` | 3040 | 201242 | 40048 | 0.103% |
| 8 | `handlePush` | 2935 | 228675 | 126546 | 0.324% |
| 9 | `swrDrawSpriteInternal` | 2571 | 206191 | 88840 | 0.228% |
| 10 | `__udivdi3` | 2399 | 186505 | 100081 | 0.256% |
| 11 | `memset` | 2095 | 154454 | 75564 | 0.194% |
| 12 | `swrNote` | 2024 | 149384 | 47452 | 0.122% |
| 13 | `sn_write` | 1829 | 127675 | 45169 | 0.116% |
| 14 | `vsnprintf` | 1594 | 133916 | 69880 | 0.179% |
| 15 | `Runner_draw` | 931 | 71631 | 31163 | 0.080% |
| 16 | `stackPopInt32` | 908 | 52316 | 31322 | 0.080% |
| 17 | `free` | 870 | 64046 | 33155 | 0.085% |
| 18 | `__moddi3` | 838 | 44986 | 0 | 0.000% |
| 19 | `swrMirrorFlush` | 811 | 62381 | 23534 | 0.060% |
| 20 | `strcasecmp` | 805 | 53666 | 3186 | 0.008% |
| 21 | `handleConv` | 773 | 55910 | 22534 | 0.058% |
| 22 | `memcpy` | 724 | 52041 | 30394 | 0.078% |
| 23 | `swrDrawText` | 722 | 54207 | 26133 | 0.067% |
| 24 | `malloc` | 665 | 46044 | 21659 | 0.055% |
| 25 | `VM_callCodeIndex` | 474 | 35964 | 13665 | 0.035% |
| 26 | `Profiler_exit` | 415 | 33483 | 15436 | 0.040% |
| 27 | `SWRenderer_profDrawRectangle` | 389 | 28197 | 12148 | 0.031% |
| 28 | `VMBuiltins_getVariable` | 342 | 26969 | 11405 | 0.029% |
| 29 | `stbds_hm_find_slot` | 321 | 23742 | 10439 | 0.027% |
| 30 | `swrOverlayFlushHeld` | 303 | 23509 | 7180 | 0.018% |


By I-cache blocking cycles

| Rank | ELF function | I refills | I bus service cycles | I block cycles | Frame share |
| --- | --- | --- | --- | --- | --- |
| 1 | `executeLoop` | 18056 | 1217043 | 541034 | 1.386% |
| 2 | `printf_core` | 9796 | 680972 | 259120 | 0.664% |
| 3 | `builtin_draw_sprite` | 5345 | 380575 | 182857 | 0.468% |
| 4 | `Instance_setSelfVar` | 3971 | 304993 | 172689 | 0.442% |
| 5 | `handlePush` | 2935 | 228675 | 126546 | 0.324% |
| 6 | `resolveVariableRead` | 3678 | 266730 | 113372 | 0.290% |
| 7 | `__udivdi3` | 2399 | 186505 | 100081 | 0.256% |
| 8 | `swrDrawSpriteInternal` | 2571 | 206191 | 88840 | 0.228% |
| 9 | `memset` | 2095 | 154454 | 75564 | 0.194% |
| 10 | `vsnprintf` | 1594 | 133916 | 69880 | 0.179% |
| 11 | `resolveVariableWrite` | 3428 | 249448 | 62142 | 0.159% |
| 12 | `swrNote` | 2024 | 149384 | 47452 | 0.122% |
| 13 | `sn_write` | 1829 | 127675 | 45169 | 0.116% |
| 14 | `vfprintf` | 3040 | 201242 | 40048 | 0.103% |
| 15 | `free` | 870 | 64046 | 33155 | 0.085% |
| 16 | `stackPopInt32` | 908 | 52316 | 31322 | 0.080% |
| 17 | `Runner_draw` | 931 | 71631 | 31163 | 0.080% |
| 18 | `memcpy` | 724 | 52041 | 30394 | 0.078% |
| 19 | `swrDrawText` | 722 | 54207 | 26133 | 0.067% |
| 20 | `swrMirrorFlush` | 811 | 62381 | 23534 | 0.060% |
| 21 | `handleConv` | 773 | 55910 | 22534 | 0.058% |
| 22 | `malloc` | 665 | 46044 | 21659 | 0.055% |
| 23 | `Profiler_exit` | 415 | 33483 | 15436 | 0.040% |
| 24 | `VM_callCodeIndex` | 474 | 35964 | 13665 | 0.035% |
| 25 | `SWRenderer_profDrawRectangle` | 389 | 28197 | 12148 | 0.031% |
| 26 | `VMBuiltins_getVariable` | 342 | 26969 | 11405 | 0.029% |
| 27 | `executeCode` | 256 | 16239 | 10986 | 0.028% |
| 28 | `__truncdfsf2` | 243 | 17519 | 10763 | 0.028% |
| 29 | `stbds_hm_find_slot` | 321 | 23742 | 10439 | 0.027% |
| 30 | `handleCall` | 291 | 19727 | 9002 | 0.023% |


### deltarune bmenu — trace

Top 30 by count cover 83.01% of I refills and 3.96% of frame cycles in I blocking. Top 30 by blocking cover 4.00% of frame cycles.

Unattributed: 1102 refills, 1274 I-block cycles (0.003% of the frame cycles).

By refill count

| Rank | ELF function | I refills | I bus service cycles | I block cycles | Frame share |
| --- | --- | --- | --- | --- | --- |
| 1 | `executeLoop` | 18391 | 1243474 | 411174 | 0.893% |
| 2 | `builtin_draw_sprite` | 5475 | 377320 | 215254 | 0.468% |
| 3 | `printf_core` | 5387 | 362113 | 123153 | 0.267% |
| 4 | `resolveVariableWrite` | 4675 | 324422 | 139122 | 0.302% |
| 5 | `swrDrawSpriteInternal` | 3828 | 292382 | 133311 | 0.290% |
| 6 | `vfprintf` | 3775 | 256186 | 146822 | 0.319% |
| 7 | `Instance_setSelfVar` | 3675 | 279056 | 128330 | 0.279% |
| 8 | `frame_tick` | 2587 | 182836 | 33606 | 0.073% |
| 9 | `__udivdi3` | 1813 | 142875 | 85328 | 0.185% |
| 10 | `stackPopInt32` | 1677 | 126121 | 39989 | 0.087% |
| 11 | `handleCall` | 1609 | 110334 | 46072 | 0.100% |
| 12 | `Runner_draw` | 1099 | 83565 | 37092 | 0.081% |
| 13 | `handlePush` | 1093 | 79228 | 28891 | 0.063% |
| 14 | `swrNote` | 1038 | 61077 | 30519 | 0.066% |
| 15 | `swrMirrorFlush` | 968 | 73126 | 19014 | 0.041% |
| 16 | `resolveVariableRead` | 841 | 59935 | 29671 | 0.064% |
| 17 | `swrDrawText` | 794 | 58817 | 27307 | 0.059% |
| 18 | `tryReadStaticFallback.isra.0` | 789 | 52455 | 0 | 0.000% |
| 19 | `__moddi3` | 768 | 41545 | 0 | 0.000% |
| 20 | `VM_callCodeIndex` | 628 | 45754 | 18610 | 0.040% |
| 21 | `malloc` | 536 | 37278 | 18282 | 0.040% |
| 22 | `free` | 488 | 31355 | 16954 | 0.037% |
| 23 | `handleConv` | 469 | 34712 | 15623 | 0.034% |
| 24 | `SWRenderer_profDrawRectangle` | 407 | 28408 | 11332 | 0.025% |
| 25 | `memcpy` | 350 | 24216 | 24082 | 0.052% |
| 26 | `__muldf3` | 250 | 17909 | 8445 | 0.018% |
| 27 | `stbds_hm_find_slot` | 248 | 19847 | 8399 | 0.018% |
| 28 | `Profiler_exit` | 247 | 19588 | 11393 | 0.025% |
| 29 | `VMBuiltins_getVariable` | 242 | 19930 | 7641 | 0.017% |
| 30 | `Profiler_enter` | 239 | 19193 | 7110 | 0.015% |


By I-cache blocking cycles

| Rank | ELF function | I refills | I bus service cycles | I block cycles | Frame share |
| --- | --- | --- | --- | --- | --- |
| 1 | `executeLoop` | 18391 | 1243474 | 411174 | 0.893% |
| 2 | `builtin_draw_sprite` | 5475 | 377320 | 215254 | 0.468% |
| 3 | `vfprintf` | 3775 | 256186 | 146822 | 0.319% |
| 4 | `resolveVariableWrite` | 4675 | 324422 | 139122 | 0.302% |
| 5 | `swrDrawSpriteInternal` | 3828 | 292382 | 133311 | 0.290% |
| 6 | `Instance_setSelfVar` | 3675 | 279056 | 128330 | 0.279% |
| 7 | `printf_core` | 5387 | 362113 | 123153 | 0.267% |
| 8 | `__udivdi3` | 1813 | 142875 | 85328 | 0.185% |
| 9 | `handleCall` | 1609 | 110334 | 46072 | 0.100% |
| 10 | `stackPopInt32` | 1677 | 126121 | 39989 | 0.087% |
| 11 | `Runner_draw` | 1099 | 83565 | 37092 | 0.081% |
| 12 | `frame_tick` | 2587 | 182836 | 33606 | 0.073% |
| 13 | `swrNote` | 1038 | 61077 | 30519 | 0.066% |
| 14 | `resolveVariableRead` | 841 | 59935 | 29671 | 0.064% |
| 15 | `handlePush` | 1093 | 79228 | 28891 | 0.063% |
| 16 | `swrDrawText` | 794 | 58817 | 27307 | 0.059% |
| 17 | `memcpy` | 350 | 24216 | 24082 | 0.052% |
| 18 | `swrMirrorFlush` | 968 | 73126 | 19014 | 0.041% |
| 19 | `VM_callCodeIndex` | 628 | 45754 | 18610 | 0.040% |
| 20 | `malloc` | 536 | 37278 | 18282 | 0.040% |
| 21 | `free` | 488 | 31355 | 16954 | 0.037% |
| 22 | `handleConv` | 469 | 34712 | 15623 | 0.034% |
| 23 | `Profiler_exit` | 247 | 19588 | 11393 | 0.025% |
| 24 | `SWRenderer_profDrawRectangle` | 407 | 28408 | 11332 | 0.025% |
| 25 | `__truncdfsf2` | 210 | 14881 | 9682 | 0.021% |
| 26 | `executeCode` | 207 | 15623 | 9414 | 0.020% |
| 27 | `RValue_toString.isra.0` | 219 | 16711 | 8582 | 0.019% |
| 28 | `__muldf3` | 250 | 17909 | 8445 | 0.018% |
| 29 | `stbds_hm_find_slot` | 248 | 19847 | 8399 | 0.018% |
| 30 | `VMBuiltins_setVariable` | 235 | 19029 | 8281 | 0.018% |


## Build and fidelity

Frozen runner `f1d8542`; legacy profile, Ubuntu container GCC 13.2.0, `-O2`, RV32IMAFC, ILP32F, `-ffunction-sections -fdata-sections -falign-functions=64 -falign-loops=64`, global `OF_PC`, native script replacements disabled. The ELF, full flags, substitutions and exact source revision are recorded in the JSON. The copied SDK also adds those alignment flags; matching alignment alone does not establish parity with the v0.7 card’s compiler, link order or addresses. This does not use the `f42a23c` sprite section-ordering experiment.

32 KiB two-way I-cache with next-line hardware prefetch; 128 KiB two-way D-cache; 64-byte lines. No CPU RTL parameters were changed. The observer is compiled only behind `HARNESS_CACHE_PROFILE` and runtime-enabled by `CACHE_PROFILE=1`. It adds no firmware instructions and preserves the original cycles and oracles. The optional free/unlimited I-cache counterfactual was not run.

Cached harness-allocated framebuffer, fixed 800 audio pairs, deterministic virtual clock, substituted allocator/kernel/storage/audio services, no hardware interrupts/GPU/display scheduling or physical SD latency. The timed loop includes reached game, render and mix code, but neither production kernel ABI nor the physical board is reproduced. Quiet removes diagnostic scanout traffic; actual device traffic can change refill tails. D-block excludes other store-buffer/writeback backpressure. Field is walking; bmenu samples attack meters, not an entire battle phase.

The frame-level result does not show I-cache refills dominating these complete frames. The narrower claim about scattered sprite/culling code remains undecided: this baseline and these windows do not isolate the device’s 150-instruction path, and the waiting counters are observational. Use the timing rankings as measured candidates for a layout experiment, then compare an isolated same-build path or a separately captured candidate; no speedup bound was measured here.

## Evidence

Raw CSV, ELF, simulator, wrapper, copied observer sources, original replay results and capture artifacts are hash-checked when generating this report. All inputs are private and stay under the harness directory; Docker mounts only the independent measurement copy.

| Game/window/build | Observer | ELF SHA-256 | Profile result SHA-256 |
| --- | --- | --- | --- |
| undertale/flowey/timing | 900f61ac0020e091 | 534dd0ff1368aa6da9b2dec1a65207fb67f83cc5023ca47aa9e512a091d74db9 | 0ba80a8e413881486fb880d584ac320b677aeb1531b7fbad1780b37a3105205d |
| undertale/flowey/trace | 900f61ac0020e091 | ad2c916e08d1ea55abe68d1cd67e0417d080e79a13dc0fb2f001d4621aaee8c2 | b44c327cce7ad86ef92ceb93a4c082d8cd0ff2cf0714d50cb1558350143d0f05 |
| deltarune/dodge/timing | 900f61ac0020e091 | ef3e9d9101d9a88fbacd46501700068ddd0d1b2677db1f4ce19638800d36cdb0 | 1552b5f2cac30f3aa25b7d2dc59bceb4854889d7878d7ca0c978419e9e9c33df |
| deltarune/dodge/trace | 900f61ac0020e091 | 0996687e17af0c9dcbc6aa079c603ca6a52bb9c01b327aafcc812d7e147e2c26 | 7766f6a6ae83371f4734717bfd16b571fa6e50beebc8a558da16662cf8e2d05f |
| deltarune/field/timing | 900f61ac0020e091 | d63cc5086538e2d71f2b7c825cb119cf49c1aef32b9ad70653c4eeae9213c8fd | eda6922d46220e0c63e69cfcbef313997f43b862052ee9ac8463b8345657cf0c |
| deltarune/field/trace | 900f61ac0020e091 | 04f278c31d45f63b2cf04a764920c2155ca1508926312e36f3b802192f7267a9 | 9b6569e265a193600e4cfdef1a8117782bb4d8b733ed7806b772fe65cc0e4c9a |
| deltarune/bmenu/timing | 900f61ac0020e091 | 688d0fd8881075b4633d0c4dda82bb4358febc6460c293af0c0d5386eaa1c9d6 | 5e6165c4cca293c27b59a9e22b0e9bfb7197ff9ca8e458ad5d2137c52f2928f3 |
| deltarune/bmenu/trace | 900f61ac0020e091 | 6f990ede2e36391ccc5ee9cf98a990454a60e5e09f7f8f7e3405beb0bdd7ec17 | 20cf7f57ccca0676c8a21239b16523bce3669bd5b3e4920c6966386fb8032820 |


Additional observer checks (each in its own independent copy):

| Game/window | Placement | Mode | Check | Result SHA-256 |
| --- | --- | --- | --- | --- |
| deltarune/dodge | sdram | speed | bad state rejected | 3902d8249528d8722c23c6822adcdcaca1dbbad264cb3ccf2655d588fea54e4b |
| deltarune/dodge | sdram | speed | observer disabled, identical | dd50af703bd83113076de63df65c73ed388bf0679b42dc4b9f31ed3b147b2d6b |
| deltarune/dodge | sdram | speed | bad state rejected | 3c05e5068d95ee887fc560e07e008c37b1401bd5f0f71f32cf7cba8da4c83f7d |
| undertale/flowey | sdram | speed | bad state rejected | 065e9220f44f1c7220504269887da09c3602929f07ee62070b4dde908cb533fc |
| undertale/flowey | sdram | speed | observer disabled, identical | 1b327e324c85e058581409223eecae73004a81288ac1fca63c7aee5368ba1c2d |
| undertale/flowey | sdram | speed | bad state rejected | 29f969b3b7df468f8c4c4ccfb89fe4377b681c88e3a2fe58584776d0e4787321 |
| deltarune/dodge | sdram | accuracy | scanout, identical | 5f34159a37813697e342c1a821e327e5bcdae14d2451cc224988fef5aad98b3d |
| deltarune/dodge | bram | accuracy | scanout, identical | a1b7d6c0ab6fe6a59165ccdee29fa2182ac1eb8d0393d221d4000d2458da586f |
| undertale/flowey | sdram | accuracy | scanout, identical | bb66e933679bb7d951ada29093f047b3d4d7d397ce080cdab5c31cd6106f3e36 |
| undertale/flowey | bram | accuracy | scanout, identical | e5df1cb8c524ee0797187b2b4d4e8b43fdd85063eb9df687efd5f481bc57599b |
