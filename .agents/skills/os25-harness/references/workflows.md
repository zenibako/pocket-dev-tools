# Detailed harness workflows

All repository paths below are relative to the located harness root, not this
skill directory. Read only the section and maintained README needed for the task.

Use this harness for functional replay and simulated CPU/memory comparisons.
Read the harness README (`README.md` under the harness root)
and, for complete frames, its full-frame README (`fullframe/README.md` under the harness root).
They contain the maintained build procedure, source provenance and fidelity limits.

## Locate the isolated checkout and its inputs

Use the standalone `pocket-harness` repository (legacy checkout name
`openfpga-os25-harness`), located as described in the skill. Commands run from its
root. Read SETUP.md (`SETUP.md` under the harness root) to import compatible frozen inputs with
`bootstrap.py`. The tool validates file hashes and copies sources, never changing
the supplied game-port, OS or SDK source roots. Only this repository is mounted
at `/work` in Docker. Use its Python launchers; avoid port deployment commands.

`inputs/`, `captures/`, `build/`, `experiments/` and `battle_fixtures.inc` are
private ignored state. A Git checkout alone cannot run game captures. Imports
require fresh absent destinations and reject external links. Preserve baseline
evidence; revision experiments keep independent baseline/candidate snapshots
inside this repository. Keep assets, bytecode and checkpoints out of commits.
No SD card is needed or used.

Run `python3 run.py verify` before an experiment. It checks the frozen input
hashes in `input-manifest.json`. The runner snapshot is `f1d8542`; editing a sibling port does not change replay.
CPU generator source/submodule pins and known netlist are in `cpu-lock.json`. Do not rewrite hashes to make an unexpected mismatch pass.
For a candidate engine change, prepare a separate, explicitly recorded private
snapshot and retain the baseline evidence; rebuild and recapture that candidate.

## Choose the workload

| Workload | Command / evidence | What it exercises |
| --- | --- | --- |
| Pico8Pocket fixed-seed cart/scene A/B on os20 | `python3 pico8/cpu_platform.py verify`; `python3 pico8/run.py create --platform os20`; `pico8/README.md` | Native/QEMU checkpoint and indexed pixel/palette/PCM oracles, quiet/scanout RTL runtime replay at 90 MHz |
| Synthetic and captured VM events | `python3 run.py all --jobs 4`; `build/results.json` | BC16/BC17 interpreter and value/variable handling; six captured leaf events use checked builtin transcripts |
| Complete battle frames | `python3 fullframe/run.py run`; `build/fullframe/results.json` after `python3 fullframe/report.py` | Consecutive real game-loop iterations, all reached scripts/builtins, collision, software rendering and audio mixing |
| Revision experiments | `python3 experiments.py`; bench/README.md (`bench/README.md` under the harness root) | Frozen revisions, cross-build pixels/PCM, separate traced/timing ELFs, both modes and additional Deltarune windows |
| Passive cache/pipeline profile | `python3 cache_profile.py --case EXACT_CASE`; cacheprobe/README.md (`cacheprobe/README.md` under the harness root) | I/D refills, architectural retirement/CPI, dependencies, FPU/divider/store-buffer waits and branch recovery; unchanged CPU/firmware in independent copies |
| Sprite-culling microprobe | `python3 sprite_probe.py --snapshot NAME`; spriteprobe/README.md (`spriteprobe/README.md` under the harness root) | Pinned staged renderer probe, renderer/GML profiling disabled, 24 repeated call batches with strict oracles and passive pipeline counters |
| Identical-ELF hardware calibration | `python3 calibration.py`; calibration/README.md (`calibration/README.md` under the harness root) | One normal SDK ELF with separate bare RTL entry, asset-free arithmetic/memory/renderer probes, 72 intervals, QEMU/RTL oracles and prepared hardware payload |

## Pico8Pocket os20 performance

Use the separate `pico8/` adapter for Pico8Pocket, introduced in harness commit
`7e747e7`. Read `pico8/README.md`; this workflow is independent of Butterscotch's
`experiments.py` windows and calibration. Locate the harness as described in the
skill: the `harness` argument, `OS25_HARNESS_ROOT`, then a sibling `pocket-harness`
or legacy `openfpga-os25-harness` checkout, asking once if none is found.

If `build/platforms/os20` is absent, build once with
`python3 pico8/cpu_platform.py build --jobs 4`. If it exists without
`platform.json`, preserve failure evidence and inspect the logs; the documented
`rtl` action resumes wrapper compilation after successful CPU generation. An
existing completed platform is verified, never rebuilt in place.

```sh
python3 run.py verify
python3 pico8/cpu_platform.py verify
python3 pico8/run.py create --source SOURCE --archive CARTS_ZIP \
  --name NEW_CASE --platform os20 --hash-seed 0x5eed1234 --measure-frames 12
python3 pico8/run.py build --case EXACT_CASE
python3 pico8/run.py native --case EXACT_CASE --cart CART_ID
python3 pico8/run.py capture --case EXACT_CASE --cart CART_ID
python3 pico8/run.py replay --case EXACT_CASE --cart CART_ID
python3 pico8/run.py replay --case EXACT_CASE --cart CART_ID --traffic scanout
python3 pico8/run.py replay --case EXACT_CASE --cart CART_ID --negative
python3 pico8/run.py report --case EXACT_CASE
```

Create baseline/candidate cases from separate dependency-prepared source copies
under new names; keep source revision/status and file inventories. Always pass
`--platform os20`: the CLI and Python API still default to os25. Require recorded
`platform_name=os20`, `clock_hz=90000000`, CPU/simulator identity and matching
route/configuration. The final hash seed is checked in native/QEMU through
`PICOSEED 1592594996`; overriding only `luai_makeseed()` leaves address mixing.
RTL reads the actual MMIO clock register and emits `PICOCPU 90000000`.

Use `--setup`, `--input`, `--warmup-frames`, `--measure-frames` and
`--trace-frames` to reach the selected scene. Distinguish a reconstructed scene
from an imported device save and inspect gameplay coverage. Compare A/B on the
same seed, setup/input, window, compiler/flags/alignment, BRAM placement and
fixed audio model. Default native traces run 600 frames twice. QEMU checkpoint
and output must repeat. Inspect `capture.json` for both `passed=true` and
`native_output_equal=true`; QEMU repeatability alone does not gate native equality.
Require same-ELF quiet/scanout RTL
output/memory oracles. A deliberately corrupted pixel oracle must be rejected.
Independent raw pixel, display-palette and PCM exports plus pair counts are
needed for byte-identity claims; standard frame hashes alone do not establish it.
The standard CLI has no raw-channel exporter or cross-case compare action;
use a separately reviewed collector or limit the conclusion to hash agreement.
It also has no save-import option: setup/input recreate a scene; an actual
device-state import requires separate, validated import evidence. Resolve cart
IDs from each case inventory. Runtime changes use separate source snapshots;
authorized cart Lua changes use distinct cart archives with recorded hashes.

`report` calculates simulated runtime capacity as `90000000 / mean_cycles`,
and caps the FPS estimate at the cart's target. Keep historical os25 evidence
with its original 100 MHz clock; converting by frequency alone cannot model
dual issue, smaller data cache, divider/FPU or refresh changes. Existing os25
single-lane instruction/pipeline observers are not validated for os20.

The os20 platform uses frozen OS `8318f25`, dual issue at 90 MHz, 32 KiB I-cache,
64 KiB D-cache, reduced-accuracy FMA, 4-slot/32-op store buffer and 660-cycle
SDRAM refresh. Pico8Pocket's `scripts/fetch-deps.sh` identifies the production
runtime (currently `openfpgaCore` release `pocket-runtime-a58aacd`). Its CPU/cache/
SDRAM source profile agrees with the frozen adapter, but save-state gateware and
firmware differ. Keep `os20.rbf_r`, `os.bin` and `loader.bin` from one pinned
release: the bitstream's BRAM contents and OS must match builds. Recheck source
configuration when upgrading; preserve frozen cases and create a separately
pinned platform with recaptured evidence for any platform change. Source-profile
agreement does not establish fitted-bitstream equivalence or hardware timing
parity. Check device compiler/libc/flags,
alignment and BRAM layout separately; the harness uses GCC13 and a bounded
allocator. Runtime timing excludes presentation, adaptive skipping and OS/SD/
live audio scheduling, uses fixed PCM and starts with cold RTL caches. Do not
label it physical Pocket FPS or transfer Butterscotch's os25 calibration to it.

## Butterscotch calibration and sprite probes

Calibration preparation is isolated and never implies installation. Require
both repeated QEMU references, negative QEMU/RTL oracles, quiet observer on/off
equality and diagnostic scanout before its report/hardware bundle. Preserve the
same ELF hash for device testing; `compare` validates a supplied hardware log
against that ELF and reference. Record the actual core/OS identity separately.
Measured addresses match, but kernel startup, interrupts and display/audio
activity differ. No logging/validation occurs between calibration intervals.
The save-enabled calibration uses the benchmark's NUL-terminated save-slot
log, with its own `calibration_log.sav` filename in slot 11. Prepare its private
Pocket overlay; never touch the SD card. After a separately authorized device
run, exit through the Analogue menu and collect the raw `.sav`. QEMU checks
saved text and write failure; actual Pocket persistence is a device check. The supplied 2026-10-10 save
passed all 72 calibration intervals; `calibration/DEVICE-RESULTS.md` records the
matching ELF and physical comparison. This is evidence for that controlled
calibration, not a general full-frame timing guarantee.

Microprobe intervals are batches of direct renderer calls, not complete game
frames. Require both disabled-observer and corrupted-oracle controls from the
same case. Record sprite selection, view/scale geometry, warm-up, compiler,
alignment and snapshot revision. Do not claim a physical probe's timing was
reproduced merely because the simulated workload passes. Device binary and
checkpoint parity are separate evidence.

The event workload excludes real rendering and mixing; its cycles cannot stand
in for battle frame time. The original complete-frame workload covers Undertale
Flowey frames 2400–2402 and Deltarune Chapter 1 enemy-turn frames 3323–3325 in
`room_field2`. Both follow the benchmark route with seed 7, fresh volatile saves
and native script acceleration disabled. Coverage is these windows, not every
battle or the whole game.

## Compare a candidate before a device run

Read bench/README.md (`bench/README.md` under the harness root) for command syntax and verified
limits. `experiments.py snapshot` exports `src/` and `vendor/` from an explicit
Git revision, reads only Git objects from the supplied port, and retains verified
private assets. Use a new snapshot name; never overwrite baseline evidence.
`run --kind both` produces separately labeled traced correctness and untraced
timing cases. Docker mounts only one independently copied case at a time.

Run matching windows and modes for baseline and candidate, then `compare` their
printed CASE paths. Require identical raw RGB555, raw PCM and pair counts for a
behavior-preserving change. State pointers are deliberately ignored across
builds. A same-build QEMU/RTL pass cannot establish unchanged rendering/mixing.
Differences exit 2 and retain both PPMs; investigate rather than recapture over
the baseline. `report` verifies source/ELF/artifact hashes and labels build kind,
compiler, native script setting, costs and oracle exclusions.

The default revision run covers only Deltarune `dodge`; `--kind both` selects
traced/timing builds, not both games. Run each selected game/window for both
snapshots, retaining exact CASE paths. For example:

```sh
python3 experiments.py run --snapshot BASELINE --game undertale --window flowey --kind both --mode speed --native enabled
python3 experiments.py run --snapshot CANDIDATE --game undertale --window flowey --kind both --mode speed --native enabled
python3 experiments.py run --snapshot BASELINE --game deltarune --window dodge --kind both --mode speed --native enabled
python3 experiments.py run --snapshot CANDIDATE --game deltarune --window dodge --kind both --mode speed --native enabled
```

Repeat Deltarune with `--window field` or `bmenu` when relevant. Select compiler,
placement and other flags explicitly when comparing those dimensions; the
example uses the current launcher defaults for them. Compare corresponding
traced cases and corresponding timing cases, not a trace against a timing case.

Supported revision windows: Undertale `flowey` 2400–2402; Deltarune `field`
2800–2802, `bmenu` 3120–3122 (menu/attack section), `dodge` 3323–3325.
`--mode speed` uses `--bench-smooth`; Accuracy uses `--bench`.
Port profile enables native scripts by default; legacy disables them.
`--native` is explicit: comparisons must match its setting. The port profile has
no global `OF_PC` or extra alignment, but substitutes SDK declarations/kernel
services. Do not describe that as full device build/ABI parity. Card compiler
version and measured alignment remain unknown; see the recorded SDK flag conflict.

Optional uncached framebuffer, 1,680-cycle clock charge and realtime audio have
passed both supplied device-revision replays. They remain cost assumptions.
Realtime QEMU PCM/count cannot match cycle-dependent RTL consumption and those
fields are explicitly excluded; cross-build comparison refuses realtime cases.
Use fixed audio for regression checks, and report underruns as simulated.
Timing ELFs omit per-opcode/event hooks and in-loop PCM hashing; pair a traced
case with timing evidence when checking audio correctness.

## Attribute cache costs

Use the exact experiment case path and check its configuration before profiling;
revision/window/build-kind names alone do not distinguish memory placement,
compiler or native settings. `cache_profile.py` requires an existing successful
replay for the selected traffic. It creates a new private measurement copy and
rejects any changed frame cycles/oracles. `--disabled` checks the runtime switch;
`--negative` checks bad-state rejection. Keep original cases and old observer
versions as evidence. No CPU parameter changes are made by this observer.

Read the counter definitions (`cacheprobe/README.md` under the harness root) before interpreting
a result. I-cache full transaction latency includes speculative/prefetch
traffic and overlapping responses; its sum is not frame stall. The fetch hold
alone misses REDO/flush/retry cost. Use the union of fetch hold and the passive
shadow of the pinned CPU's miss-recovery waiting event, separately from the D
refill waiter and I/D overlap. Instructions can commit during a block; even the
no-commit subset is observational rather than uniquely causal lost cycles.
Rank refill line bases and blocked/missing PCs separately, leaving ELF padding
unattributed. Check both traced and timing builds; tracing changes code/layout.

`cache_report.py` verifies/reanalyses raw CSV, ELF, simulator, copied observer,
source replay and capture evidence before generating the named baseline study.
The f1d8542 results (`cacheprobe/RESULTS.md` under the harness root) show the scope and limitations;
frame-wide shares do not settle the isolated device sprite-culling hypothesis.
Any free/unlimited-cache or ordering experiment needs its own recorded changes
and verified evidence; do not infer its speedup from summed bus latency.

Observer v3 adds canonical ctrl5 CommitService retirement and CPI. Keep that
separate from the older ctrl4 commit-decision count. Inspect operand dependencies,
store-buffer waits, shared integer/FP divider freezes, FP reservations/conversions,
uncached I/O and branch recovery before attributing time to a cache. Raw masks
preserve overlaps; a disjoint reporting priority is not a causal speedup estimate.
`pipeline_report.py` verifies all eight windows/builds and writes separate output;
see pipeline results (`cacheprobe/PIPELINE-RESULTS.md` under the harness root). Timing still has
renderer/GML profiling, including note formatting, so it is not profiler-free.
Full-frame CPI does not determine an isolated device path's CPI.

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

For the Butterscotch workflows below, call results **simulated**. The copied production os25 CPU has a 100 MHz
clock, 32 KiB I-cache, 128 KiB D-cache and single-precision FPU, with the production
fabric, Pocket SDRAM controller/arbiter and registered BRAM model. Timing uses
MMIO `0x40000004`; cycle CSRs trap in this configuration. That MMIO use is verified
in the harness, not a newly verified timing API for the deployed v0.7 runtime.

Original full-frame timing includes opcode tracing and the harness
platform/allocator;
validation and UART output are outside the timed loop. The first frame has cold
caches. Compare matching game windows, seeds, binaries and traffic settings;
`simulated_ms` converts cycles assuming 100 MHz. Do not label these values as
measured Pocket FPS or compare them directly with device benchmark rows.

The original harness bounds its heap to about 51 MiB and the SDK application map,
using
its own splitting/coalescing allocator. Framebuffers are harness-allocated cached
SDRAM, so framebuffer load/store costs do not reproduce the deployed runtime's
uncached framebuffer alias. Clock, input and audio queue are deterministic models;
real mixed PCM is checked. File reads use an uncached CRAM0 mailbox at `0x30000000`
after CPU ownership is enabled through `0x4e000000`, serving only private assets.
Physical SD latency, production malloc behavior, kernel timing, hardware audio,
interrupts, GPU execution, display scheduling, synthesis fit and board behavior
are outside this test. Scanout is diagnostic traffic, not the display controller.

Revision experiment timing and default/optional service models are documented
separately in the bench README. Their three cold-cache frames and substituted
services do not directly predict device benchmark section means. Preserve the
original fullframe evidence as the reproduction of the old numerical baseline.

For claims about actual speed, framebuffer alias costs, audio underruns or card
behavior, use the game port’s device benchmark after relevant replay/desktop
checks pass. Keep simulated and device evidence distinct.
