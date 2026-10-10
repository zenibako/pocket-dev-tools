# Undertale / Deltarune Chapter 1 os25 VM harness

This standalone repository tests the os25 VexiiRiscv CPU and Pocket memory
RTL with Verilator. Its first workload is the Butterscotch interpreter running
Undertale and Deltarune Chapter 1. Builds mount only this repository in Docker.
They do not access an active game-port checkout or an SD card.

The CPU/cache/fabric/SDRAM/BRAM infrastructure can support other os25 applications.
The current VM fixtures, capture hooks and frame platform are Butterscotch adapters;
adding another core requires its own workload and oracles. See
[ARCHITECTURE.md](ARCHITECTURE.md) for that boundary.

## Setup and private inputs

Start with [SETUP.md](SETUP.md). `bootstrap.py` imports compatible local source
roots or an existing private snapshot, checks their frozen hashes and copies them
into this repository. It never changes those source directories. A fresh Git
checkout contains tooling and hash manifests; game assets, bytecode, checkpoints,
SDK archives and generated output remain private and ignored.

The frozen runner is `f1d8542`, OS `8318f25`, SDK `7882a0d`; CPU and submodule
pins are recorded in `cpu-lock.json`. The surrounding game-port sources do not
change a replay. This repository was extracted from Butterscotch tooling commit
`88008f7`, with project skill guidance from `6328cff`. Neither source checkout
was removed or moved.

Complete battle-frame replay is available in [fullframe/README.md](fullframe/README.md).
It restores a full RV32 process checkpoint and runs three consecutive real
game-loop frames for each game, including scripts, collision, software rendering
and audio mixing. The original event-fixture harness below remains available.

For revision snapshots, baseline/candidate pixel and PCM comparison, separate
traced/timing executables, Speed mode and optional cost assumptions, use
[Revision experiments](bench/README.md). The original baseline is preserved.

[Passive cache profiling](cacheprobe/README.md) counts real I/D refill handshakes,
pipeline blocking and measured latency distributions, and attributes I-cache
traffic to ELF functions. [Frozen Speed-mode results](cacheprobe/RESULTS.md)
cover traced and untraced full-frame windows from both games.

[Pipeline results](cacheprobe/PIPELINE-RESULTS.md) add architectural retirement/CPI,
load and other operand dependencies, FPU/divider freezes, store-buffer waits and
branch recovery. The original cache evidence remains preserved separately.

[Sprite microprobe](spriteprobe/README.md) replays a pinned branch's staged
renderer probe with renderer/GML profiling disabled. Its separate
[results](spriteprobe/RESULTS.md) break down direct call cycles, native CPI,
cache refills and pipeline waits; these are simulated batch timings.

## Run

From this directory, with Python 3, Docker/Colima and host Clang installed.
After importing or generating private event captures:

```sh
python3 run.py all --jobs 4
```

The first invocation builds the toolchain image. Setup imports CPU source and
SpinalHDL/rvls at their pinned revisions.
CPU generation is skipped when the generated os25 netlist exists. To explicitly
regenerate it, use `python3 run.py cpu`.

Individual actions are `verify`, `host`, `toolchain`, `cpu`, `firmware`, `rtl`,
and `run`. To recapture from the local, privately copied game assets, install
host SDL2/pkg-config and run:

```sh
python3 capture.py all
python3 run.py host
python3 run.py firmware
python3 run.py run
```

`capture.py` builds two observing desktop runners under `build/capture`. Each
game follows the existing `platform/ut_bench.c` input route twice, using seed 7,
volatile fresh saves, and `UT_NO_NATIVE=1`. Only the private asset copies are
read; frame images, logs and capture outputs stay in this directory. Capture
windows are Undertale frames 2388–2402 and Deltarune frames 3323–3327.
Only byte-identical records across both runs are eligible for selection.

For example, after changing a synthetic workload:

```sh
python3 run.py host
python3 run.py firmware
python3 run.py run
```

The launcher defaults to this machine's Colima socket. Override it for another
Docker daemon with `HARNESS_DOCKER_HOST`, for example
`HARNESS_DOCKER_HOST=unix:///var/run/docker.sock python3 run.py all`.
The public-image Docker configuration is private to `build/docker-config`.

## Coverage and oracles

Both BC16 (Undertale) and BC17 (Deltarune Chapter 1) are compiled into the same
image. The bytecode fixtures use real `VM_executeCode` and production value,
instance, array/method and hash-map code. The interpreter sources are unchanged.

| Fixture | Checks |
| --- | --- |
| BC16 integer arithmetic | 64 groups of `3 * 7 + 2`, result 23 |
| BC16 float arithmetic | 64 groups of `1.25 * 2 + 0.5`, exact result 3 |
| BC16 branch | Counter loop stops at 64 |
| BC16 locals | 16 direct-index locals, 128 updates, result 23 |
| BC17 locals | Same updates with sparse IDs `100 + 97*i` |
| BC17 self | Every instance variable equals its initial value plus 8 |
| BC17 global | Same oracle through the global-scope instance |
| BC17 script call | 64 real script calls, argument 5 plus 8, result 13 |

Each synthetic fixture performs one untimed initialization execution, then three measured
rounds of two executions each. Timing surrounds only `VM_executeCode`; validation
and UART formatting occur afterward. MMIO counter-read overhead is included.
Each return and final self/global variable
state has an independent oracle. Frame/stack cleanup and repeat hashes are checked.

Six captured **numeric VM event calls** extend this coverage:

| Game / scene | Captured event | Executed opcodes on capture host |
| --- | --- | --- |
| Undertale / Flowey battle | winkstar Step | 14 |
| Undertale / Flowey battle | guidearrows Alarm 0 | 6 |
| Undertale / Flowey battle | guidearrows Alarm 1 | 6 |
| Deltarune Chapter 1 / enemy turn | grazebox Draw | 48 |
| Deltarune Chapter 1 / enemy turn | shake Create | 16 |
| Deltarune Chapter 1 / enemy turn | growtangle Draw | 14 |

`captures/<game>/manifest.json` identifies the selected JSON files and records
source game, observing runner, source-file, hook and frame-image hashes.
`captures/replay-manifest.json` connects fixture indices to exact event names,
source frames, room names and independently derived output hashes. The host
battle images were visually checked; Deltarune battles overlay `room_field2`
rather than switching to a separate battle room.

The raw patched bytecode words are unchanged. Each replay restores the captured
numeric variables, occupied hash-map keys, capacities and probe layout, plus
BC17 local-slot maps. Unreferenced values are undefined placeholders, so the
fixture preserves lookup structure without copying arbitrary pointer graphs.
Only supported numeric events are selected; this is a small sample of battle
VM execution, not a complete battle frame or a compatibility test of all scripts.

Builtin variable reads/writes and drawing calls use an ordered transcript from
the actual game runner. The replay checks receiver IDs, indices, argument counts,
exact numeric types/bits, and every builtin write. Unexpected or missing calls
fail. Expected return values, final numeric variables, map keys and local-slot
maps are checked after execution. Input key down/pressed/released state is also
saved as capture provenance. The selected events occur between key presses.

Each captured event has one untimed warmup and three rounds of two executions.
Its initial state is restored before **every** execution, outside the timed
region. Captured opcode counts are host observations, not a target instruction
counter. Timed replay includes the external-call transcript checker; it excludes
actual sprite rendering, collision, audio and the full builtin implementation.
Use these numbers to compare these replay configurations, not to estimate whole
battle frame time or Pocket FPS.

The host reference uses AddressSanitizer and UndefinedBehaviorSanitizer.
Leak detection is disabled because the host's Apple ASan does not support it.
Both deliberately wrong synthetic and captured return oracles must fail on
host and RTL, so a false success or missing failure path is rejected.

Two images execute the same tests: interpreter in SDRAM behind the instruction
cache, and interpreter in application BRAM at `0x4000` using `UT_FAST_LOOP`.
ELF sections determine the SDRAM preload and BRAM MIF. The loader verifies the
entry point, reserved BRAM limit and `executeLoop` placement.

Each image runs with quiet SDRAM and synthetic scanout contention. The existing
OS testbench checks CPU read data, scanout data, AXI ordering and delivered writes
against the external chip model. Any missing result, incorrect hash, timeout,
trap, unexpected VM service call or memory-oracle failure rejects the run.

The validated matrix has 96 synthetic and 72 captured result rows (six captured
events, three rounds, four configurations), plus two intentional failure images. The machine-readable
report includes each image's compiler, section placement and input hashes.
Changing a firmware source without rebuilding is rejected.

## Hardware fidelity and limits

**Simulated:** cycle counts from the production MMIO cycle counter at
`0x40000004`, functional results and
memory delivery for these exact source snapshots. `build/results.json` records
all rounds. Conversion to milliseconds assumes the os25 100 MHz CPU clock.
These are not physical Pocket measurements or complete-game FPS.

The CPU is generated with the copied production `generate_vexii.sh os25` and
os25 configuration: 32 KiB instruction cache, 128 KiB data cache, single-precision
FPU, production branch prediction and memory attributes. SDRAM parameters and
GPU feature parameters are extracted from the production Pocket top level using
its Make-resolved os25 macros. The actual CPU fabric, SDRAM arbiter/slave and
Pocket SDRAM controller are reused. BRAM uses the OS behavioral M10K model with
its registered read latency. The external SDRAM/CRAM chip models are behavioral.

Scanout is the existing diagnostic injector, not the entire display controller:
80 32-bit words per line, 480 active of 525 lines, one line per 3175 CPU cycles,
roughly 60 Hz. Its deterministic traffic is useful for comparing memory contention;
it does not reproduce the game's actual display mode. GPU command execution,
audio mixer traffic, SD streaming and interrupts are not exercised by these VM
fixtures. The GPU RTL is present with os25 parameters but stays idle.

The VM context and already-resolved bytecode metadata are constructed directly.
The harness bypasses game loading, VM initialization, asset decoding and game
builtins. Captured external calls use checked transcripts; all other game
services fail closed. A small bounded harness allocator
uses SDRAM `0x10400000..0x13700000`; libc formatting/math use the copied SDK musl
libraries. The allocator is not production musl malloc, so its timings must not
be used to predict production allocation performance.

**Inferred:** this is substantially closer to Pocket CPU/cache/SDRAM behavior
than a desktop VM benchmark. Physical FPGA timing closure, resource fit, refresh
retention and board-specific effects still require synthesis and hardware tests.
Synthetic BC16/BC17 coverage does not prove full Undertale or Deltarune compatibility.
The ignored private inputs contain local game assets and captured proprietary
bytecode/state. Keep those inputs local; no game data or captures were uploaded
or published. The event-fixture images contain only the selected events;
the separate full-frame images contain the live game process and private assets.

## Provenance and evidence

`input-manifest.json` records the original source revisions and SHA-256 hashes of
1,631 copied inputs. `run.py verify` checks every frozen input. CPU generation
patches only the privately cloned CPU source; it does not modify those copied
inputs. CPU git revision: `580b76c3868512c8316bb7a3d3add81cad49a0dc`;
SpinalHDL: `6f8510cdbb8ad7b8bcc0f6d58395669c4c4d7e2d`;
rvls: `94f850e5f7c9a36e5aceb3810d658fffae55b497`.

The implementation follows the existing OS fixtures in
`inputs/os/tools/check_pocket_gpu_transport.py`,
`inputs/os/tools/check_pocket_memory_contention.py`, and
`inputs/os/src/fpga/test/tb_system_sdram_main.cpp`.
Existing experiment context was read from the OS's SM64 CPU/coupled/schedule
experiment READMEs and its CPU-stress test documentation before implementation.

Evidence is kept under `build/`: host reference/negative logs, CPU-generation
log, firmware ELF/map/MIF files and hashes, generated RTL wrapper and simulator,
quiet/scanout logs, both negative RTL logs, observing-runner logs and matching
frame images, raw repeated captures, and the machine-readable results.
All of these are disposable harness outputs; none is deployed to a Pocket.
