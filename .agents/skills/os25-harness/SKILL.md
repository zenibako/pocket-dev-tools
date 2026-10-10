---
name: os25-harness
description: Run and interpret the isolated os25 RV32/Verilator harness for Undertale and Deltarune Chapter 1, including captured VM events and complete battle frames. Use for CPU/cache/SDRAM or BRAM experiments, deterministic state/pixel/audio replay, and testing Pocket constraints without using the active checkout or SD card.
---

# Testing with the os25 CPU and memory RTL

Use this harness for functional replay and simulated CPU/memory comparisons.
Read the [harness README](../../../README.md)
and, for complete frames, its [full-frame README](../../../fullframe/README.md).
They contain the maintained build procedure, source provenance and fidelity limits.

## Locate the isolated checkout and its inputs

Use the standalone `openfpga-os25-harness` repository. Commands run from its
root. Read [SETUP.md](../../../SETUP.md) to import compatible frozen inputs with
`bootstrap.py`. The tool validates file hashes and copies sources, never changing
the supplied game-port, OS or SDK source roots. Only this repository is mounted
at `/work` in Docker. Use its Python launchers; avoid port deployment commands.

`inputs/`, `captures/`, `build/` and `battle_fixtures.inc` are private ignored
state. A Git checkout alone cannot run game captures. Imports require fresh
absent destinations and reject external links. Preserve the baseline in a
separate checkout for candidate experiments. Keep assets, bytecode and checkpoints
out of commits. No SD card is needed or used.

Run `python3 run.py verify` before an experiment. It checks the frozen input
hashes in `input-manifest.json`. The runner snapshot is `f1d8542`; editing a sibling port does not change replay.
CPU generator source/submodule pins and known netlist are in `cpu-lock.json`. Do not rewrite hashes to make an unexpected mismatch pass.
For a candidate engine change, prepare a separate, explicitly recorded private
snapshot and retain the baseline evidence; rebuild and recapture that candidate.

## Choose the workload

| Workload | Command / evidence | What it exercises |
| --- | --- | --- |
| Synthetic and captured VM events | `python3 run.py all --jobs 4`; `build/results.json` | BC16/BC17 interpreter and value/variable handling; six captured leaf events use checked builtin transcripts |
| Complete battle frames | `python3 fullframe/run.py run`; `build/fullframe/results.json` after `python3 fullframe/report.py` | Consecutive real game-loop iterations, all reached scripts/builtins, collision, software rendering and audio mixing |

The event workload excludes real rendering and mixing; its cycles cannot stand
in for battle frame time. The complete-frame workload currently covers Undertale
Flowey frames 2400–2402 and Deltarune Chapter 1 enemy-turn frames 3323–3325 in
`room_field2`. Both follow the benchmark route with seed 7, fresh volatile saves
and native script acceleration disabled. Coverage is these windows, not every
battle or the whole game.

## Run or rebuild complete frames

With the prepared private state already present:

```sh
python3 run.py verify
python3 fullframe/run.py run --game deltarune --variant bram --traffic scanout
```

Omit `--game` to run both games. `--variant sdram` executes the interpreter in
SDRAM; `--variant bram` must place `executeLoop` at `0x4000` in application BRAM.
The ELF placement check rejects a BRAM build that silently kept the loop in
SDRAM. `--traffic quiet` removes diagnostic display contention; `scanout` adds it.

After changing full-frame firmware, for each affected variant:

```sh
python3 fullframe/run.py build --variant bram
python3 fullframe/run.py capture --variant bram
python3 fullframe/run.py prepare --variant bram
python3 fullframe/run.py run --variant bram --traffic quiet
python3 fullframe/run.py run --variant bram --traffic scanout
python3 fullframe/run.py run --variant bram --negative
```

Repeat with `sdram` when comparing placement. If the simulator generator or RTL
changes, run `python3 fullframe/run.py rtl --jobs 4` before replay. New toolchain
setup and the full matrix sequence are in the full-frame README. The base image
is `undertale-vm-os25-harness:local`; `fullframe/run.py toolchain` adds QEMU in
`undertale-vm-os25-frames:local`. The launchers use `build/docker-config` to avoid
the noninteractive Docker credential-helper problem. Their default daemon is
Colima; `HARNESS_DOCKER_HOST` overrides it. This is separate from the SDK's
ordinary device-build container and `USE_SDK_CONTAINER` setting.

## Verify the result before interpreting cycles

The same RV32 binary runs under QEMU to capture and under Verilator to replay.
Two captures must have identical RAM/stack checkpoints and frame oracles.
RTL replay checks game state, RGB555 pixel and PCM checksums, sample-pair counts,
opcode/event counts and VM traces, clean VM stacks, and SDRAM/AXI delivery.
Use the reference PPMs under `build/fullframe/<game>/<variant>/repeat-0/` when a
visual check helps explain a mismatch.

Run `python3 fullframe/report.py` after all requested configurations. Its complete
matrix requires both games × SDRAM/BRAM × quiet/scanout: eight configurations,
24 frame rows, and four deliberately corrupted state oracles rejected. A partial
run is useful but does not satisfy that aggregate report. Hash changes, timeout,
trap or oracle failure require investigation; preserve the failing log.

State hashes include RV32 pointers and instance layout: require equality between
QEMU and RTL for the same binary/checkpoint, not between different candidate
binaries. For a behavior-preserving optimization, independently compare baseline
and candidate pixels, PCM and relevant game values on the same route and seed.
Recapturing a candidate reference alone does not prove unchanged behavior.

## Interpret timing and hardware constraints

Call these results **simulated**. The copied production os25 CPU has a 100 MHz
clock, 32 KiB I-cache, 128 KiB D-cache and single-precision FPU, with the production
fabric, Pocket SDRAM controller/arbiter and registered BRAM model. Timing uses
MMIO `0x40000004`; cycle CSRs trap in this configuration. That MMIO use is verified
in the harness, not a newly verified timing API for the deployed v0.7 runtime.

Full-frame timing includes opcode tracing and the harness platform/allocator;
validation and UART output are outside the timed loop. The first frame has cold
caches. Compare matching game windows, seeds, binaries and traffic settings;
`simulated_ms` converts cycles assuming 100 MHz. Do not label these values as
measured Pocket FPS or compare them directly with device benchmark rows.

The harness bounds its heap to about 51 MiB and the SDK application map, using
its own splitting/coalescing allocator. Framebuffers are harness-allocated cached
SDRAM, so framebuffer load/store costs do not reproduce the deployed runtime's
uncached framebuffer alias. Clock, input and audio queue are deterministic models;
real mixed PCM is checked. File reads use an uncached CRAM0 mailbox at `0x30000000`
after CPU ownership is enabled through `0x4e000000`, serving only private assets.
Physical SD latency, production malloc behavior, kernel timing, hardware audio,
interrupts, GPU execution, display scheduling, synthesis fit and board behavior
are outside this test. Scanout is diagnostic traffic, not the display controller.

For claims about actual speed, framebuffer alias costs, audio underruns or card
behavior, use the game port’s device benchmark after relevant replay/desktop
checks pass. Keep simulated and device evidence distinct.
