# Identical-binary calibration

Build `f6e0acd235b0c07c`, compiler `riscv64-unknown-elf-gcc (13.2.0-11ubuntu1+12) 13.2.0`. Hardware, QEMU and RTL use the same ELF; hardware execution is pending. All timings are simulated.

| Workload | Quiet cycles/op | Scanout cycles/op | Quiet CPI | Quiet I/D refills | Three quiet batch cycle totals |
| --- | --- | --- | --- | --- | --- |
| loop | 2.038 | 2.038 | 1.015 | 2/0 | 4248, 4129, 4137 |
| integer-dependent | 1.255 | 1.255 | 1.003 | 0/0 | 20601, 20530, 20508 |
| integer-independent | 1.256 | 1.256 | 1.003 | 0/0 | 20631, 20535, 20527 |
| multiply-dependent | 3.006 | 3.006 | 2.402 | 0/0 | 49291, 49184, 49192 |
| divide-dependent | 9.257 | 9.257 | 4.112 | 0/0 | 151651, 151571, 151563 |
| cached-load-chain | 3.004 | 3.004 | 2.401 | 0/0 | 49252, 49180, 49165 |
| capacity-load-chain | 59.817 | 62.733 | 47.814 | 0/49131 | 979494, 979539, 979666 |
| uncached-load-chain | 23.245 | 24.364 | 18.581 | 0/0 | 380651, 380680, 380657 |
| cached-stream | 8.682 | 8.995 | 2.671 | 0/12294 | 569024, 568896, 568844 |
| fp-add-dependent | 7.004 | 7.004 | 5.598 | 0/0 | 114741, 114684, 114671 |
| fp-multiply-dependent | 5.004 | 5.004 | 3.999 | 0/0 | 81988, 81934, 81920 |
| fp-divide | 17.254 | 17.254 | 13.789 | 0/0 | 282601, 282546, 282530 |
| conversion-roundtrip | 11.255 | 11.255 | 3.462 | 0/0 | 184372, 184294, 184294 |
| int-to-fp | 5.254 | 5.254 | 2.334 | 0/0 | 86099, 86027, 86013 |
| fp-to-int | 2.255 | 2.255 | 1.803 | 0/0 | 36990, 36903, 36903 |
| icache-64k-stream | 47.984 | 50.356 | 23.748 | 24637/0 | 393130, 393046, 393073 |
| sprite-inside | 5432.833 | 5432.833 | 1.338 | 0/0 | 10860526, 10868236, 10868236 |
| sprite-door | 74.082 | 74.082 | 1.299 | 0/0 | 148180, 148155, 148155 |
| sprite-texture-found | 238.139 | 238.132 | 1.280 | 2/0 | 476335, 476238, 476263 |
| sprite-drawing-entered | 431.130 | 431.130 | 1.373 | 0/0 | 862213, 862344, 862220 |
| sprite-clipped | 563.123 | 563.123 | 1.383 | 0/0 | 1126206, 1126312, 1126220 |
| sprite-setup | 742.153 | 742.153 | 1.403 | 0/0 | 1484376, 1484324, 1484215 |
| sprite-layers-flushed | 930.216 | 930.216 | 1.527 | 8/2 | 1860703, 1860360, 1860234 |
| sprite-outside | 480.145 | 480.145 | 1.341 | 2/0 | 960421, 960249, 960199 |

An operation is one explicit tested instruction (or one divide+add / conversion-roundtrip group), one loaded word, one I-cache block, or one sprite call. Loop, call and MMIO boundary overhead remain included. Do not compare differently defined operations. No validation or logging occurs between measured batches.

| Workload | I block/op | D block/op | RAW hold/op | Execute freeze/op | Branch recovery/op | Int→FP freeze/op |
| --- | --- | --- | --- | --- | --- | --- |
| loop | 0.006 | 0.000 | 0.001 | 0.005 | 0.014 | 0.000 |
| integer-dependent | 0.000 | 0.000 | 0.000 | 0.001 | 0.002 | 0.000 |
| integer-independent | 0.000 | 0.000 | 0.000 | 0.001 | 0.002 | 0.000 |
| multiply-dependent | 0.000 | 0.000 | 1.750 | 0.001 | 0.003 | 0.000 |
| divide-dependent | 0.000 | 0.000 | 1.000 | 6.002 | 0.003 | 0.000 |
| cached-load-chain | 0.000 | 0.000 | 1.750 | 0.001 | 0.002 | 0.000 |
| capacity-load-chain | 0.000 | 51.815 | 3.500 | 0.001 | 0.000 | 0.000 |
| uncached-load-chain | 0.000 | 0.000 | 19.462 | 20.244 | 0.000 | 0.000 |
| cached-stream | 0.000 | 3.118 | 2.125 | 0.000 | 0.000 | 0.000 |
| fp-add-dependent | 0.000 | 0.000 | 5.750 | 0.001 | 0.003 | 0.000 |
| fp-multiply-dependent | 0.000 | 0.000 | 3.750 | 0.001 | 0.002 | 0.000 |
| fp-divide | 0.000 | 0.000 | 0.000 | 16.001 | 0.002 | 0.000 |
| conversion-roundtrip | 0.000 | 0.000 | 7.000 | 4.001 | 0.003 | 3.000 |
| int-to-fp | 0.000 | 0.000 | 0.000 | 3.001 | 0.002 | 3.000 |
| fp-to-int | 0.000 | 0.000 | 0.000 | 1.001 | 0.003 | 0.000 |
| icache-64k-stream | 2.151 | 0.000 | 0.000 | 0.001 | 43.819 | 0.000 |
| sprite-inside | 0.000 | 0.000 | 616.999 | 61.008 | 284.096 | 48.003 |
| sprite-door | 0.000 | 0.000 | 9.004 | 6.008 | 0.031 | 6.003 |
| sprite-texture-found | 0.013 | 0.000 | 45.004 | 6.008 | 0.053 | 6.003 |
| sprite-drawing-entered | 0.000 | 0.000 | 55.002 | 61.008 | 0.062 | 48.003 |
| sprite-clipped | 0.000 | 0.000 | 78.004 | 61.008 | 0.052 | 48.003 |
| sprite-setup | 0.000 | 0.000 | 98.002 | 61.008 | 18.083 | 48.003 |
| sprite-layers-flushed | 0.040 | 0.000 | 113.994 | 61.008 | 86.109 | 48.003 |
| sprite-outside | 0.005 | 0.000 | 57.997 | 64.007 | 0.074 | 51.002 |

These are overlapping observed conditions, including cycles with retirement; do not add them or interpret them as recoverable time. The machine-readable report also retains instruction mix, FP/multiply/load dependencies, divider/conversion waits, branch mispredict counts and a disjoint no-retirement partition using the documented observer priority.

| Workload | Quiet I refill cycles min/p50/p90/p99/max | Quiet D refill cycles min/p50/p90/p99/max |
| --- | --- | --- |
| loop | 52/52/52/52/96 | none |
| integer-dependent | none | none |
| integer-independent | none | none |
| multiply-dependent | none | none |
| divide-dependent | none | none |
| cached-load-chain | none | none |
| capacity-load-chain | none | 49/54/54/56/110 |
| uncached-load-chain | none | none |
| cached-stream | none | 49/49/52/59/80 |
| fp-add-dependent | none | none |
| fp-multiply-dependent | none | none |
| fp-divide | none | none |
| conversion-roundtrip | none | none |
| int-to-fp | none | none |
| fp-to-int | none | none |
| icache-64k-stream | 49/68/68/83/148 | none |
| sprite-inside | none | none |
| sprite-door | none | none |
| sprite-texture-found | 52/52/52/52/96 | none |
| sprite-drawing-entered | none | none |
| sprite-clipped | none | none |
| sprite-setup | none | none |
| sprite-layers-flushed | 52/69/96/96/98 | 52/52/52/52/52 |
| sprite-outside | 52/52/52/52/96 | none |

Refill durations run from accepted AXI read to last response. They are transaction latency, not CPU stall; outstanding transactions can overlap. All three batches are pooled by refill count when computing quantiles.

Two byte-identical QEMU reference logs, all numerical/pixel oracles, both quiet and diagnostic scanout memory checks, identical enabled/disabled-observer quiet cycles, and QEMU/RTL corrupted-oracle rejection passed. CPU/cache parameters are unchanged. Per-batch histograms, masks and CPI are retained in the private machine-readable report.

ELF SHA-256: `59f9545ad7bf7a621b48f07c912e7c6b0a1ec4260be0d1594d3d2526eb03b5bd`. SDK hardware entry `0x1040004e`; bare RTL entry `0x10400000`. Source revision `3c2d37a22a194d1745a72e0dd9b9677e4bd6f8fc`. The artifact is an SDK application ELF, not a replacement FPGA bitstream or SD-card image.

The generated sprite is deterministic calibration artwork using the real renderer/item-cache path. It has static geometry and precomputed texture copies, no asset reads or timed allocation. This does not recreate the original Deltarune checkpoint or establish physical Pocket timing. Hardware startup uses real musl/SDK ABI; bare RTL skips kernel startup. OS interrupts and actual display/audio traffic, stack/TLS placement and initial cache state remain unmatched. Diagnostic scanout is the 80-word, 480/525-line injector.

Private hardware deliverable: `experiments/calibrations/cal-f6e0acd235b0c07c/hardware/calibration.elf`. No source checkout, SDK source or SD card was modified. See [README.md](README.md) for preparation and comparison instructions.
