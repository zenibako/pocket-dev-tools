# Identical-binary calibration

Build `e0a503254fcd861d`, compiler `riscv64-unknown-elf-gcc (13.2.0-11ubuntu1+12) 13.2.0`. Hardware, QEMU and RTL use the same ELF; hardware execution is pending. All timings are simulated.

| Workload | Quiet cycles/op | Scanout cycles/op | Quiet CPI | Quiet I/D refills | Three quiet batch cycle totals |
| --- | --- | --- | --- | --- | --- |
| loop | 2.039 | 2.039 | 1.015 | 2/0 | 4255, 4129, 4137 |
| integer-dependent | 1.255 | 1.255 | 1.003 | 0/0 | 20601, 20530, 20508 |
| integer-independent | 1.255 | 1.255 | 1.003 | 0/0 | 20615, 20535, 20527 |
| multiply-dependent | 3.006 | 3.006 | 2.402 | 0/0 | 49281, 49184, 49192 |
| divide-dependent | 9.257 | 9.257 | 4.112 | 0/0 | 151651, 151571, 151563 |
| cached-load-chain | 3.004 | 3.004 | 2.402 | 0/0 | 49254, 49181, 49165 |
| capacity-load-chain | 59.814 | 62.733 | 47.811 | 0/49131 | 979489, 979510, 979529 |
| uncached-load-chain | 23.245 | 24.364 | 18.581 | 0/0 | 380651, 380699, 380648 |
| cached-stream | 8.681 | 8.994 | 2.671 | 0/12291 | 568999, 568831, 568790 |
| fp-add-dependent | 7.004 | 7.004 | 5.598 | 0/0 | 114741, 114684, 114671 |
| fp-multiply-dependent | 5.004 | 5.004 | 3.999 | 0/0 | 81974, 81934, 81920 |
| fp-divide | 17.254 | 17.254 | 13.789 | 0/0 | 282593, 282546, 282530 |
| conversion-roundtrip | 11.254 | 11.254 | 3.462 | 0/0 | 184348, 184284, 184270 |
| int-to-fp | 5.256 | 5.256 | 2.335 | 0/0 | 86117, 86045, 86045 |
| fp-to-int | 2.256 | 2.256 | 1.803 | 0/0 | 37008, 36903, 36903 |
| icache-64k-stream | 47.983 | 50.355 | 23.748 | 24637/0 | 393127, 393019, 393072 |
| sprite-inside | 5438.144 | 5438.144 | 1.339 | 0/0 | 10876488, 10876189, 10876189 |
| sprite-door | 74.082 | 74.082 | 1.299 | 0/0 | 148180, 148155, 148155 |
| sprite-texture-found | 238.129 | 238.129 | 1.280 | 2/0 | 476305, 476222, 476247 |
| sprite-drawing-entered | 431.123 | 431.123 | 1.373 | 0/0 | 862204, 862329, 862203 |
| sprite-clipped | 563.122 | 563.122 | 1.383 | 0/0 | 1126206, 1126306, 1126220 |
| sprite-setup | 742.149 | 742.149 | 1.403 | 0/0 | 1484350, 1484347, 1484197 |
| sprite-layers-flushed | 930.189 | 930.193 | 1.527 | 6/2 | 1860585, 1860336, 1860214 |
| sprite-outside | 480.140 | 480.140 | 1.341 | 2/0 | 960395, 960255, 960190 |

An operation is one explicit tested instruction (or one divide+add / conversion-roundtrip group), one loaded word, one I-cache block, or one sprite call. Loop, call and MMIO boundary overhead remain included. Do not compare differently defined operations. No validation or logging occurs between measured batches.

| Workload | I block/op | D block/op | RAW hold/op | Execute freeze/op | Branch recovery/op | Int→FP freeze/op |
| --- | --- | --- | --- | --- | --- | --- |
| loop | 0.006 | 0.000 | 0.001 | 0.005 | 0.015 | 0.000 |
| integer-dependent | 0.000 | 0.000 | 0.000 | 0.001 | 0.002 | 0.000 |
| integer-independent | 0.000 | 0.000 | 0.000 | 0.001 | 0.002 | 0.000 |
| multiply-dependent | 0.000 | 0.000 | 1.750 | 0.001 | 0.003 | 0.000 |
| divide-dependent | 0.000 | 0.000 | 1.000 | 6.002 | 0.003 | 0.000 |
| cached-load-chain | 0.000 | 0.000 | 1.750 | 0.001 | 0.002 | 0.000 |
| capacity-load-chain | 0.000 | 51.811 | 3.500 | 0.001 | 0.001 | 0.000 |
| uncached-load-chain | 0.000 | 0.000 | 19.462 | 20.243 | 0.001 | 0.000 |
| cached-stream | 0.000 | 3.117 | 2.125 | 0.000 | 0.000 | 0.000 |
| fp-add-dependent | 0.000 | 0.000 | 5.750 | 0.001 | 0.003 | 0.000 |
| fp-multiply-dependent | 0.000 | 0.000 | 3.750 | 0.001 | 0.002 | 0.000 |
| fp-divide | 0.000 | 0.000 | 0.000 | 16.001 | 0.002 | 0.000 |
| conversion-roundtrip | 0.000 | 0.000 | 7.000 | 4.001 | 0.002 | 3.000 |
| int-to-fp | 0.000 | 0.000 | 0.000 | 3.001 | 0.003 | 3.000 |
| fp-to-int | 0.000 | 0.000 | 0.000 | 1.001 | 0.003 | 0.000 |
| icache-64k-stream | 2.150 | 0.000 | 0.000 | 0.001 | 43.818 | 0.000 |
| sprite-inside | 0.000 | 0.000 | 616.501 | 61.008 | 288.079 | 48.003 |
| sprite-door | 0.000 | 0.000 | 9.004 | 6.008 | 0.031 | 6.003 |
| sprite-texture-found | 0.013 | 0.000 | 45.004 | 6.008 | 0.045 | 6.003 |
| sprite-drawing-entered | 0.000 | 0.000 | 55.002 | 61.008 | 0.056 | 48.003 |
| sprite-clipped | 0.000 | 0.000 | 78.006 | 61.008 | 0.051 | 48.003 |
| sprite-setup | 0.000 | 0.000 | 98.003 | 61.008 | 18.081 | 48.003 |
| sprite-layers-flushed | 0.022 | 0.000 | 113.998 | 61.008 | 86.098 | 48.003 |
| sprite-outside | 0.005 | 0.000 | 57.998 | 64.007 | 0.069 | 51.002 |

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
| cached-stream | none | 49/49/52/62/73 |
| fp-add-dependent | none | none |
| fp-multiply-dependent | none | none |
| fp-divide | none | none |
| conversion-roundtrip | none | none |
| int-to-fp | none | none |
| fp-to-int | none | none |
| icache-64k-stream | 49/68/68/83/148 | none |
| sprite-inside | none | none |
| sprite-door | none | none |
| sprite-texture-found | 54/54/54/54/98 | none |
| sprite-drawing-entered | none | none |
| sprite-clipped | none | none |
| sprite-setup | none | none |
| sprite-layers-flushed | 52/69/69/69/103 | 49/49/49/49/52 |
| sprite-outside | 52/52/52/52/96 | none |

Refill durations run from accepted AXI read to last response. They are transaction latency, not CPU stall; outstanding transactions can overlap. All three batches are pooled by refill count when computing quantiles.

Two byte-identical QEMU reference logs, all numerical/pixel oracles, both quiet and diagnostic scanout memory checks, identical enabled/disabled-observer quiet cycles, and QEMU/RTL corrupted-oracle rejection passed. CPU/cache parameters are unchanged. Per-batch histograms, masks and CPI are retained in the private machine-readable report.

ELF SHA-256: `6b36cc1aa44e2d101c0b82bdf230c81dafd9cc1b551657f415d7635183511ec8`. SDK hardware entry `0x1040004e`; bare RTL entry `0x10400000`. Source revision `3c2d37a22a194d1745a72e0dd9b9677e4bd6f8fc`. The artifact is an SDK application ELF, not a replacement FPGA bitstream or SD-card image.

The generated sprite is deterministic calibration artwork using the real renderer/item-cache path. It has static geometry and precomputed texture copies, no asset reads or timed allocation. This does not recreate the original Deltarune checkpoint or establish physical Pocket timing. Hardware startup uses real musl/SDK ABI; bare RTL skips kernel startup. OS interrupts and actual display/audio traffic, stack/TLS placement and initial cache state remain unmatched. Diagnostic scanout is the 80-word, 480/525-line injector.

Private hardware deliverable: `experiments/calibrations/cal-e0a503254fcd861d/hardware/calibration.elf`. No source checkout, SDK source or SD card was modified. See [README.md](README.md) for preparation and comparison instructions.

This revision saves the latest complete calibration log as NUL-terminated text through save slot 11 `calibration_log.sav`, after every measurement and oracle check. QEMU saved text matches stdout; failed-run logging and failure to create the log were checked. Bare RTL skips file writes. Physical save-slot persistence awaits the device run and exit through the Analogue menu.
