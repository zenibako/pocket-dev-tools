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
Ordered extra `-D`/`-U` flags are included in compatibility and reproduced in
candidate builds. An absent flag list and an empty list are equivalent.

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

## Reference validation and private baselines

The original implementation at commit `e8dedcab7649ee86550be6fad8d075676f4dbbe2`
was tested with published Butterscotch v0.7.7 source
`3b9fcfd56a589c300bb8423f2b61951bf8cb5749`: 20 configurations, 60 frame rows,
12 rejected state controls and a real one-pixel regression rejected with exit 2.
Those private captures and indices remain in their original checkout. They are
not distributed with this repository or a reusable public baseline dataset.

This integration preserves the central repository's newer ordered flag support,
Pico8/calibration infrastructure and accepted-SDRAM-write draining checks.
Fresh integration validation on 2026-10-28 passed 20 replay configurations
(60 frame rows), 12 negative controls and eight cross-build pixel/PCM comparisons
for the same published source. The host suite ran 199 tests with three explicit
dependency/private-fixture skips; 18 startup/placement checks passed in the
prepared toolchain, including the fresh SDRAM ELF. An automatic Git-exported
candidate passed. A separately captured, replay-valid corruption then failed
with exit 2: one changed pixel per frame, identical PCM/counts and six retained
images. The private reference remained unchanged. Both shared skills passed
schema/reference checks and an independent cross-project routing review.

Changed tooling requires freshly verified cases and a new index; do not copy or
rewrite an earlier index's paths/hashes to make it eligible. Use the exact
`BASELINE` path printed by registration in your checkout:

```sh
python3 regression.py check --baseline BASELINE_INDEX \
  --repo /absolute/path/to/butterscotch-port \
  --revision CANDIDATE_REVISION --jobs 1
```

The read-only source repository must contain the requested Git revision and the
original frozen revision. Set `HARNESS_DOCKER_HOST` for your local daemon when
needed. Keep source exports, cases, baseline indices and retained mismatch
images in their private ignored directories.

For other projects, read the [shared regression contract](../benchmarks/REGRESSIONS.md).
Use their existing tests and supported evidence adapters; this CLI does not add
Pico8Pocket, VVVVVV or generic application replay.
