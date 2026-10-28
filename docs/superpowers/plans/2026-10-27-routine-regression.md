# Routine regression implementation plan

> **For agentic workers:** Use subagent-driven-development for the current-port adapter and independent review; the coordinator owns private restoration and integration. Track tasks here and in the plan's ignored ledger.

**Goal:** Restore the pinned historical inputs and provide immutable current-port baseline/candidate checks without a card trip for routine software updates.

**Architecture:** Preserve `input-manifest.json`, `cpu-lock.json`, original fullframe workflow and historical adapter behavior. Restore the exact frozen private inputs with bootstrap, extend the revision adapter by detected source generation, and retain separately named current source snapshots. A routine runner pins baseline case paths/configuration and compares independent captures, verifies RTL/oracle evidence and reports simulated timing separately from correctness.

**Tech stack:** Python standard library, C/RV32, existing QEMU/Verilator and Docker launchers.

**Spec:** User-approved scope in this conversation; existing boundaries in `ARCHITECTURE.md`, `SETUP.md`, `bench/README.md`, `fullframe/README.md` and `.agents/skills/os25-harness/SKILL.md`.

## Global constraints

- Work only in this harness repository; source port419ef894 and external dependency roots are read-only. No SD access, remote writes, publications or CPU-pin changes.
- Restore all1631 frozen manifest inputs and1621 CPU-lock files; do not rewrite hashes to accommodate missing/different input bytes.
- Private assets/checkpoints/source copies remain ignored. Existing `build/` packaging/profiles must be preserved; bootstrap without `--with-evidence`.
- Preserve historical adapter support. Current baseline is public draft sourcefcabf548, with source419ef894 as the first candidate; no assertion of device/SDK/ABI parity or physical timing follows from simulation.
- Fixed deterministic audio and same route/seed/native/renderer/configuration are required for cross-build output comparison. Pointer hashes compare only the same binary under QEMU/RTL.
- Commit code/docs with conventional GPG-signed messages; no pushes implied.

## Task 1: Restore frozen inputs (coordinator)

- [ ] Inventory existing local snapshots or pinned Git objects/archives and private owned assets; record concrete sources in ignored `build/restoration-discovery.md`.
- [ ] Use `bootstrap.py` with exact compatible bundle or independently staged pinned source roots. Preserve preexisting `build/`; destinations `inputs/` and `captures/` must be absent.
- [ ] Run `python3 -m unittest test_bootstrap.py`, `python3 run.py verify`, and verify CPU file hashes/netlist against `cpu-lock.json`. Preserve an import receipt with input/source manifests and hashes.
- [ ] Prepare base toolchain/RTL with existing Python launchers; preserve original baseline and verify original fullframe matrix when ready.

## Task 2: Support current port revision adapter (implementer)

**Files:** `bench/build.py`, `bench/runtime.c`, `bench/bridge.c`, `bench/platform.c` as required, focused adapter test file(s), `bench/README.md`. Keep historical `fullframe/` sources unchanged unless a shared launcher interface needs a verified fix.

- [ ] Read the existing builders/capture/revision paths and read-only current419ef894 source anchors. Write failing behavioral tests for old/current layout source selection, safe declarative flags, actual hook generation, VM state traversal and deterministic environment routing. Tests must exercise generated/compiled behavior, not only grep source.
- [ ] Detect supported source generations. Preserve ut_* historical sources/hooks while compiling current of_* platform/game sources and required Zstandard using the source's declarative Makefile list; don't include PC/SDL-only platform sources in RV32.
- [ ] Adapt current instruction dispatch/event hooks and VM currentCallFrame traversal; preserve exact untraced timing behavior and instrumentation exclusions. Route BS_* controls for current sources and UT_* for historical.
- [ ] Retain isolated SDK/kernel-service substitutions explicitly. Do not claim native production OS/state-service coverage. Add narrowly needed shim/stubs and test their fail-closed behavior.
- [ ] Run focused adapter tests and existing `test_experiments.py`; self-review. Report modified files, test evidence, behavioral limits and any integration blockers. Coordinator owns the final signed commit.

## Task 3: Establish baseline and routine gate (coordinator)

**Files:** existing `experiments.py`/new `regression.py` and focused tests as needed, `bench/README.md`/`README.md`; private baseline registry/cases under ignored `build/`/`experiments/`.

- [ ] Snapshotfcabf548 and419ef894 under fresh immutable names via existing Git-object export, using verified imported assets. All comparisons keep baseline unchanged and candidate independently copied.
- [ ] Add a minimal baseline/check CLI around existing experiments if current commands cannot express a reusable verified baseline selection. Pin case configuration and provenance; never auto-promote candidates or overwrite baseline evidence. A failed/incomplete/stale run must fail the command.
- [ ] Validate actual current-port repeat QEMU captures, traced and timing cases, both games/required matrix; run RTL positive and corrupted-oracle controls. Exact raw RGB555, fixed PCM and pair counts must agree across baseline/candidate for a behavior-preserving update.
- [ ] Run a known intentional pixel corruption in a disposable candidate and require the routine comparison to reject it, retaining evidence.
- [ ] Record a private verified baseline index and a local routine command. Timing figures are simulated; no automatic performance pass threshold without validated variance.
- [ ] Run affected unit tests/full suite, independent spec+quality review, signature/clean-status checks; commit and report one ready-to-use command plus physical testing boundaries.

## Progress

Implementation is authorized by the user's request to restore inputs and update the existing adapter. Resolve reversible integration choices without another approval loop. If local source inputs are genuinely unavailable, continue all independent adapter work and report exact missing hashes rather than guessing new pins.
