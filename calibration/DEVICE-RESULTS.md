# Pocket calibration compared with os25 RTL

Device evidence received 2026-10-10. The supplied save contains all 72 timed intervals, a passing numerical oracle for every interval, pixel hash `64bf7c25`, and `CALIBRATION PASS HAL init`. The build ID matches the prepared calibration ELF. The save transport worked.

For this identical-binary calibration, the Pocket agrees closely with the harness: the largest difference between workload means and quiet RTL is **3.15%**. The outside-view sprite call differs by **0.13%**, the first-check call by **0.006%**, and the inside draw by **0.11%**. This supports the CPU and memory timing model for these controlled workloads. It does not validate every game frame or resolve the previously reported v0.7 game probe.

## Sprite calls

Means of three batches, 2,000 calls per batch. At 100 MHz, 100 cycles = 1 microsecond.

| Probe | Pocket cycles/call | Quiet RTL cycles/call | Pocket microseconds/call | Quiet RTL microseconds/call | Difference |
| --- | ---: | ---: | ---: | ---: | ---: |
| sprite-door | 74.086 | 74.082 | 0.740858 | 0.740817 | +0.006% |
| sprite-outside | 480.771 | 480.140 | 4.807710 | 4.801400 | +0.131% |
| sprite-inside | 5444.091 | 5438.144 | 54.440905 | 54.381443 | +0.109% |

The old device observations were 4.6–6.5 microseconds for the first-check probe and about 19.9 microseconds for the outside-view probe. This calibration instead measures 0.741 and 4.808 microseconds on the Pocket itself. A general fourfold error in RTL CPU speed or refill latency is therefore not supported by this run. The earlier gap requires investigation of the workload, build and measurement context; its cause is not established here.

The calibration uses the pinned real renderer with generated artwork, fixed geometry, precomputed texture metadata/copies and a cached framebuffer. Renderer and GML profiling are compiled out, and warm-up is performed before measurement. It does not load the original Deltarune assets or checkpoint. The device reports OS v0.9.0; the earlier game figures were reported for v0.7. Those differences prevent assigning the old gap to one specific cause.

## All workloads

Each row averages three equal-sized batches. Differences are relative to quiet RTL. The Pocket range is the minimum and maximum batch cycles/op, not a confidence interval. An operation is defined by the calibration workload; it is not necessarily one retired instruction. See [SAVE-RESULTS.md](SAVE-RESULTS.md) for operation definitions, RTL CPI and stall/refill observations.

| Workload | Pocket cycles/op | Quiet RTL cycles/op | Scanout RTL cycles/op | Pocket vs quiet | Pocket batch range cycles/op |
| --- | ---: | ---: | ---: | ---: | ---: |
| loop | 2.039 | 2.039 | 2.039 | +0.016% | 2.017–2.080 |
| integer-dependent | 1.254 | 1.255 | 1.255 | -0.036% | 1.252–1.257 |
| integer-independent | 1.255 | 1.255 | 1.255 | -0.034% | 1.254–1.257 |
| multiply-dependent | 3.005 | 3.006 | 3.006 | -0.027% | 3.003–3.007 |
| divide-dependent | 9.257 | 9.257 | 9.257 | -0.004% | 9.255–9.259 |
| cached-load-chain | 3.051 | 3.004 | 3.004 | +1.565% | 3.003–3.145 |
| capacity-load-chain | 61.462 | 59.814 | 62.733 | +2.756% | 60.755–62.286 |
| uncached-load-chain | 23.965 | 23.245 | 24.364 | +3.094% | 23.184–24.457 |
| cached-stream | 8.836 | 8.681 | 8.994 | +1.779% | 8.678–9.014 |
| fp-add-dependent | 7.048 | 7.004 | 7.004 | +0.620% | 7.003–7.133 |
| fp-multiply-dependent | 5.004 | 5.004 | 5.004 | -0.005% | 5.002–5.005 |
| fp-divide | 17.254 | 17.254 | 17.254 | -0.002% | 17.253–17.257 |
| conversion-roundtrip | 11.254 | 11.254 | 11.254 | -0.003% | 11.252–11.256 |
| int-to-fp | 5.255 | 5.256 | 5.256 | -0.007% | 5.254–5.258 |
| fp-to-int | 2.255 | 2.256 | 2.256 | -0.027% | 2.253–2.258 |
| icache-64k-stream | 49.492 | 47.983 | 50.355 | +3.147% | 48.068–50.436 |
| sprite-inside | 5444.091 | 5438.144 | 5438.144 | +0.109% | 5443.350–5444.847 |
| sprite-door | 74.086 | 74.082 | 74.082 | +0.006% | 74.072–74.096 |
| sprite-texture-found | 238.428 | 238.129 | 238.129 | +0.126% | 238.089–239.094 |
| sprite-drawing-entered | 440.534 | 431.123 | 431.123 | +2.183% | 431.103–448.113 |
| sprite-clipped | 564.434 | 563.122 | 563.122 | +0.233% | 563.122–566.124 |
| sprite-setup | 743.117 | 742.149 | 742.149 | +0.130% | 743.083–743.135 |
| sprite-layers-flushed | 931.269 | 930.189 | 930.193 | +0.116% | 931.070–931.635 |
| sprite-outside | 480.771 | 480.140 | 480.140 | +0.131% | 480.103–481.125 |

Integer arithmetic, multiply/divide and the conversion workloads agree within 0.04% on their means. Dependent FP addition is 0.62% slower, with one elevated batch; the other FP arithmetic tests agree within 0.01%. The cached pointer chain and intermediate sprite-drawing probe also have elevated individual batches. Interrupts are a possible explanation for such variation, but this log does not record interrupt events and cannot establish that cause.

The capacity-load, uncached-load, cached-stream and I-cache-stream means are 1.78–3.15% slower than quiet RTL and 1.64–2.03% faster than diagnostic scanout RTL. They lie between the two simulated traffic conditions. This is consistent with some unmatched device memory traffic, but is not proof that the injector reproduces the real display/audio schedule.

The Pocket save measures elapsed cycles only. It does not expose retired instructions, cache refill counts, or hardware stall attribution. The separate RTL observations remain simulated; close elapsed-time agreement supports using them for these workloads, without independently proving each stall classification on the device.

## Evidence and limits

- Build ID: `e0a503254fcd861d`; CPU: 100,000,000 Hz; OS version: `00000900`; core variant: `0`; capabilities version: `4`.
- ELF SHA-256: `6b36cc1aa44e2d101c0b82bdf230c81dafd9cc1b551657f415d7635183511ec8`.
- Original 5,009-byte save SHA-256: `e935af69bdab737c8ff66d7e53feb5acc1464ec635ec9b242e26e4a241314297`. The text ends at byte 5,008, followed by a NUL terminator.
- Pinned renderer source: `3c2d37a22a194d1745a72e0dd9b9677e4bd6f8fc` from the isolated `perf/mirrored-blend` snapshot.
- Compiler: GCC `13.2.0-11ubuntu1+12`, RV32imafc_zicsr_zifencei / ilp32f, O2, function/data sections, function and loop alignment of 64 bytes. Hardware and RTL use the prepared identical ELF layout, with separate SDK and bare RTL entry points.
- CPU RTL SHA-256: `4bfafb0ae2ce2cd5c46713ee1f0242a1f4a022cfb6974a812e3206d468879b22`; observer: `0711991b745113db`; CPU/cache parameters unchanged.
- Quiet result SHA-256: `8e50318015c1587fd14480545d29dcaaa426552122199c2ceae27e22139c5754`.
- Scanout result SHA-256: `eb99c522cb3ed85c6b683ebf0a7b4c2dab4aaa7a33af69b628a0e2e4a845da71`.

The source ELF hash and its manifest were checked locally, and the device log reports its matching embedded build ID and expected outputs. The device does not independently hash its loaded ELF or FPGA bitstream. Core identity rests on the supplied Pocket evidence and instance selection; variant 0 is not a bitstream hash.

Hardware runs normal SDK/musl startup with platform-default interrupts. RTL uses the bare entry point, and stack/TLS placement and initial cache state can differ. The framebuffer is cached. Real display/audio activity is unmatched; scanout is an 80-word-per-line, 480/525-line diagnostic injector. Logging, validation and save writes occur after all measured intervals.

Comparison command:

```sh
python3 calibration.py compare \
  --case experiments/calibrations/cal-e0a503254fcd861d \
  --elf experiments/calibrations/cal-e0a503254fcd861d/hardware/calibration.elf \
  --log /path/to/calibration_log.sav \
  --core-note 'User supplied Pocket save; core bitstream hash not supplied'
```

Private evidence directory: `experiments/calibrations/cal-e0a503254fcd861d/build/calibration/hardware-e935af69bdab737c/`. It contains the original save, decoded log, comparison JSON and generated table. The comparison rechecked the reference oracles, ELF/artifact hashes and both RTL replay reports. An independent calculation checked the save hash, all 72 values and table arithmetic.

The frozen baseline and prior reports were preserved. All writes stayed inside this harness repository; the active game worktree, SDK/OS source roots and SD card were untouched.
