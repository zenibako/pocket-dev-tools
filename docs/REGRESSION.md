# Routine software regression checks

This gate builds on [revision experiments](../bench/README.md),
[complete-frame replay](../fullframe/README.md) and the workload boundaries in
[ARCHITECTURE.md](../ARCHITECTURE.md). It checks selected Undertale and Deltarune
Chapter 1 windows with the pinned os25 CPU and memory simulation. It does not
establish physical Pocket timing, hardware compatibility or production kernel,
allocator, storage, save-state and audio-service parity.

## Register a verified baseline

Prepare independent revision cases using the existing experiment workflow. Each
selected case must have two reproducible QEMU captures, a complete three-frame
RTL replay for the chosen traffic and a rejected corrupted-state oracle. Trace
and timing are separate cases. Fixed audio is required. Use exact printed CASE
paths rather than guessing their names.

```sh
python3 regression.py baseline --name current-verified --traffic quiet --cases BASELINE_CASE_1 BASELINE_CASE_2
```

The command prints its BASELINE path under ignored
`build/regressions/baselines/`. Existing names cannot be overwritten. The index
records the actual case roster, source revision, configuration, compiler version
and identity, adapter/shared tooling and hashes of source, binary, raw capture,
RTL, logs and results. Registration rejects stale, incomplete, mixed-revision or
duplicate evidence and missing negative controls. Raw RGB555 must have the PPM
geometry, reproduce the logged pixel FNV oracle, and convert exactly to the
retained PPM pixels. Geometry is bounded by the renderer’s 640×480 mode limit.
An index covering a subset makes claims only about that subset.

The routine current-port roster is Accuracy, BRAM/quiet, port profile, native
scripts enabled, alignment enabled, cached framebuffer, no charged clock cost
and fixed audio: Undertale Flowey plus Deltarune field, menu/attack and dodge,
with trace and timing for each. Registration requires all eight selected cases
to pass. Other coherent supplied configurations remain explicit.

## Check a source revision

Use the printed baseline path and a read-only source repository containing the
requested Git revision and the original frozen revision:

```sh
python3 regression.py check --baseline build/regressions/baselines/current-verified.json --repo /absolute/path/to/port --revision REVISION --jobs 1
```

Before creating candidates, the gate verifies the frozen baseline evidence and
current tooling/compiler. It exports a fresh uniquely named private snapshot,
then builds, captures and replays a matching candidate for every baseline case,
including negative controls. Candidate settings come from the index. The baseline
is never rebuilt, replayed, recaptured or promoted from a candidate.

`--jobs` bounds simulator compilation and defaults to one. The routine launcher
honors `HARNESS_DOCKER_HOST`. When unset, it recognizes the existing
`~/.config/colima/default/docker.sock` and `~/.colima/default/docker.sock` paths
for generated candidates. For registration or inspection of container-compiler
cases, set `HARNESS_DOCKER_HOST` explicitly if the existing launcher default is
unavailable. No global Docker settings or dependency pins are changed.

To inspect already completed independent candidates without starting builds:

```sh
python3 regression.py check --baseline build/regressions/baselines/current-verified.json --candidate-cases CANDIDATE_CASE_1 CANDIDATE_CASE_2
```

This path applies the same capture, replay, negative-control, configuration,
compiler and tooling checks. Candidates must also use the exact baseline
simulator binary, generated wrapper and leaf RTL identities. Both paths require
the complete exact baseline
roster and one candidate source revision. The baseline case itself cannot serve
as a candidate. Changed tooling or compiler requires separately verified new
baseline cases and a new index name; it cannot silently reuse old evidence.

A successful check requires identical frame width/height, raw RGB555, raw fixed
PCM and PCM pair counts for every frame. A shape change is an output mismatch
even when its flat pixel bytes match. Pointer-bearing game-state hashes are checked only
between QEMU and RTL for each binary. Cross-build comparison excludes those
pointers. Timing builds omit in-loop PCM hashing; their raw QEMU PCM remains
compared, and traced cases provide same-binary RTL PCM validation.

Each attempted candidate check has a new ignored directory under
`build/regressions/checks/`. It retains the combined verified results,
per-case comparisons, simulated timing summaries and `check.json`. Pixel or geometry
mismatches retain both reference PPM images. A mismatch exits 2; stale,
incomplete, incompatible or failed evidence exits nonzero. Failed builds and
captures remain in their own private candidate directories. Baseline preflight
errors occur before candidate execution and are printed directly.

Timing values are simulated; there is no automatic slowdown threshold without
validated variance. The test fixtures in `test_regression.py` are synthetic and
exercise gate behavior, hashes and exit codes. They provide no real-game replay
or device evidence. Physical SD behavior, audible quality, Memories and
sleep/wake require separate on-device testing.

## Verify the tooling

```sh
python3 -m unittest -v test_regression test_experiments test_bench_adapter test_bench_cwd test_bench_placement test_bench_startup
```

Startup integration checks require RV32 GCC, objcopy and QEMU. Real ELF
placement checks require pyelftools and the private preflight ELF. Tests without
their required tools or private inputs skip explicitly; exercise those checks
in the prepared isolated toolchain before claiming integration coverage.

Keep private inputs, snapshots, checkpoints, game data, images and build outputs
ignored. Neither command publishes or deploys anything, and no SD card is used.

## Local verification: 2026-10-28

The retained release baseline uses published v0.7.7 source
`3b9fcfd56a589c300bb8423f2b61951bf8cb5749` and the eight-case routine roster above:

```text
build/regressions/baselines/release-v077-3b9fcfd5-accuracy-bram-20261028.json
SHA256 bec2070986cfa2091ff59fcdfef8d6360ea1297a58028a42572582811ffbcc25
```

Compiler: RV32 GCC 13.2.0, container image
`sha256:8be4da076020970a8b1c3e3061c74b614c4d1ad75c59396da736bf99bee3384a`.
The pinned os25 CPU runs at a modeled 100 MHz. Verilator is 5.040.

Actual repeat captures, RTL replays and corrupted-state controls passed:

| Window | Build kinds | Interpreter placement | Traffic | Configurations / frames |
| --- | --- | --- | --- | --- |
| Undertale Flowey | trace, timing | BRAM, SDRAM | quiet, scanout | 8 / 24 |
| Deltarune dodge | trace, timing | BRAM, SDRAM | quiet, scanout | 8 / 24 |
| Deltarune field | trace, timing | BRAM | quiet | 2 / 6 |
| Deltarune menu/attack | trace, timing | BRAM | quiet | 2 / 6 |

This is 20 configurations, 60 frame rows and 12 distinct rejected bad-state
controls. All eight placement/build-kind output comparisons passed. Eight
earlier/final BRAM comparisons also passed, with byte-identical prepared program
images. The unchanged historical workload reproduced its eight configurations,
24 frames, four negative controls and recorded simulated timings.

The real routine CLI independently exported and checked `419ef894` against
`fcabf548`: all eight comparisons matched pixels, PCM and counts. That initial
proof retains its earlier adapter identity. The release baseline was captured
afresh after the startup-range and inline-placement fixes; no capture hashes
were rewritten or old captures relabeled.

A separate one-case probe index references the release's Deltarune dodge trace
case. A disposable source patch flipping pixel 0 passed its own repeat capture,
RTL replay and bad-state control, then the real regression command rejected it
with exit 2: one differing pixel in each frame, unchanged PCM/counts and six
retained PPMs. Both baseline indices and all eight release cases' pinned files
remained unchanged.

Private receipts are under `build/published-startup-v3-20261028/`,
`build/historical-verification-20261028/` and
`build/routine-validation-20261028/pixel-regression-proof.json`. The host suite
reported 170 tests with two explicit dependency skips; all 18 placement/startup
checks passed inside the isolated toolchain, including the skipped integration
coverage. All 1,631 original inputs, 1,621 CPU source files and the generated
netlist retain their frozen hashes.

From this harness directory, replace `CANDIDATE_REVISION` with an explicit Git
revision available in the read-only source repository:

```sh
HARNESS_DOCKER_HOST=unix:///Users/chanderson/.colima/default/docker.sock \
python3 regression.py check \
  --baseline build/regressions/baselines/release-v077-3b9fcfd5-accuracy-bram-20261028.json \
  --repo /Users/chanderson/Projects/pocket-build/butterscotch-pocket \
  --revision CANDIDATE_REVISION --jobs 1
```
