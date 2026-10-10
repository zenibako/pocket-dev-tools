# Pocket / RTL calibration

This workload follows [ARCHITECTURE.md](../ARCHITECTURE.md), the isolated
[revision experiments](../bench/README.md), and the discrepancy recorded in
[spriteprobe/RESULTS.md](../spriteprobe/RESULTS.md). It does not alter the
frozen baseline. All build products stay in a new ignored calibration case.

The hardware deliverable and RTL input use the same ELF. Normal hardware/QEMU
startup uses SDK musl `crt1.o`, the SDK constructor and application linker map;
a separate `_rtl_start` initializes the bare simulation environment. Measured
functions and static fixture addresses are therefore identical, rather than
merely compiled from similar source. QEMU reference mode substitutes zero for
the MMIO clock, checks outputs, and never supplies target timing.

Explicit RISC-V microkernels exercise loop overhead, dependent/independent
integer arithmetic, multiply/divide, cached and uncached pointer chains,
working sets exceeding L1, float arithmetic/conversions, and an instruction
stream exceeding the 32 KiB I-cache. Results have independent numerical oracles.
Loops cannot be removed by C optimization. Measured durations include their
loop and boundary overhead, which is reported rather than subtracted.

The real pinned software renderer draws a deterministic generated 40×40 sprite
at half scale into a cached 320×240 static framebuffer. Its texture/item/pack
metadata and precomputed half-size copy use fixed storage: no texture I/O or
allocation is reached. The fixture is calibration data, not sprite 42's artwork
or a full Deltarune checkpoint. Probe stop/path gates are enabled separately;
renderer/GML profiling is disabled. It repeats the staged probe order
6,5,4,3,2,1,0,outside three times after warm-up. Output and validation are deferred
until all measurements finish, eliminating inter-batch hashing/UART pollution.

The hardware app reports to stdout only. Preparing it does not install a core,
copy files to an SD card, run a deployment target or modify the source checkout.
It requires the Pocket os25 core and a compatible openfpgaOS SDK application
loader. Its actual execution on hardware remains a separate test. OS interrupts,
display/audio scheduling and FPGA timing are absent from bare RTL replay;
quiet and diagnostic scanout runs bound only the modeled memory traffic.
Stack/TLS placement and initial cache contents also differ between the two
startup paths; shared static addresses do not imply identical complete state.

## Build and verify

Use a previously verified observer-v3 sprite/platform result and an isolated
source snapshot. The SDK path is read only: two extra files (`app.ld` and
`of_init.c`) are copied into the case with hashes and Git provenance. The musl
archives/headers and renderer sources come from frozen private inputs.

```sh
python3 calibration.py build --snapshot sprite-perf-3c2 \
  --sdk /absolute/read-only/openfpgaSDK/src/sdk \
  --platform-result /absolute/verified/quiet-results.json
python3 calibration.py reference --case EXACT_CALCASE
python3 calibration.py replay --case EXACT_CALCASE
python3 calibration.py replay --case EXACT_CALCASE --disabled
python3 calibration.py replay --case EXACT_CALCASE --negative
python3 calibration.py replay --case EXACT_CALCASE --traffic scanout
python3 calibration.py report --case EXACT_CALCASE
```

Each command preserves earlier evidence. Failed builds/replays need a fresh
case rather than replacement logs. Docker mounts only `EXACT_CALCASE`.
If simulation completed successfully but host analysis failed, `analyze` takes
the same `--case`, `--traffic`, `--disabled` and `--negative` options and analyzes
the preserved log/events without repeating or replacing the simulation.
`report` requires all four replays, identical quiet observer-on/off results,
two identical QEMU logs and rejected QEMU/RTL negative oracles. It checks source,
ELF, simulator and raw-event hashes and regenerates the numerical summaries.
No CPU/cache parameters change. The fixed diagnostic scanout uses 80 words
per line, 3,175-cycle line period and 480 active / 525 total lines.

The [simulated results](RESULTS.md) identify the prepared case. Its `hardware/`
directory contains `calibration.elf`, disassembly, `SHA256SUMS`, provenance
manifest and run instructions. This is an application ELF for the normal SDK
loader, not a core bitstream. Its `_start` entry uses musl/SDK startup; the bare
RTL entry is a separate symbol retained in the same ELF.

The loops run three consecutive batches after a full untimed microkernel warm-up.
The sprite suite runs three rounds with one untimed inside draw per round.
There are 72 intervals in total. One operation means one tested instruction,
except divide-dependent (divide plus add), conversion-roundtrip (two conversions
plus increment), int-to-fp (increment plus conversion), loop (one iteration),
memory (one loaded word), I-cache (one 64-byte block), and sprite (one call).
Loop, call and MMIO overhead remain included. Cached/capacity load chains share
identical instructions; only the data working set differs. The uncached chain
uses the physical SDRAM alias after CBO.FLUSH, with no simulated syscall charges.

## Later hardware comparison

Preparation never deploys or runs the app. On a separately authorized physical
test, use the os25 core and compatible 100 MHz Pocket OS. Keep the exact ELF and
record the core/OS build, mode, display/audio activity and complete stdout log.
The app checks Pocket capabilities, SDRAM aliases and clock before running.
Core variant zero alone cannot prove which synthesized core is loaded.
It needs no game assets, takes no application arguments and writes no files.

Once the log is available, compare it locally without connecting to the device:

```sh
python3 calibration.py compare --case EXACT_CALCASE \
  --elf /absolute/copy-of-tested/calibration.elf --log /absolute/hardware.log \
  --core-note 'os25; record exact core and OS identity here'
```

The comparison rejects a different ELF, build ID, clock, pixel hash, numerical
result, iteration/operation count or sample order. It saves the supplied log
and per-workload ratios in a fresh private directory. Physical execution and
core identity rely on supplied evidence. RTL retirement/CPI and overlapping
stall counters describe simulation only; a duration ratio does not by itself
identify the cause of a device discrepancy.
