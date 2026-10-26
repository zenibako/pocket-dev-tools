# Benchmark Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Collect existing host, simulated and Pocket reports into comparable, preserved evidence bundles.

**Architecture:** Project adapters parse existing formats into a versioned record.
An append-only local store preserves original bytes and metadata; a CLI imports,
verifies and compares bundles. Physical device work remains explicitly labeled.

**Tech Stack:** Python 3.10+ standard library, unittest, existing project reports.

**Spec:** `docs/superpowers/specs/2026-10-26-benchmark-evidence-design.md`

## Global Constraints

- Work only in this repository; never modify an SD card or active game sources.
- Do not change dependency pins, manifests or private replay evidence.
- Preserve original bytes; reject overwrite and stale hashes.
- Keep host, simulation and device timing separate.
- An imported report does not establish independently verified device correctness.
- Every commit must be GPG signed.

## Task 1: Contracts, collection and project adapters

**Files:** Create `benchmarks/{__init__,__main__,model,adapters,store}.py`,
`test_benchmarks.py`.

**Interfaces:**

```python
def validate_metadata(metadata: dict) -> dict: ...
def parse_report(format_name: str, raw: bytes, metadata: dict,
                 report_index: int | None = None) -> dict: ...
def collect(source, metadata_path, format_name, *, output, attachments=(),
            report_index=None): ...
def load_run(directory) -> dict: ...
def compare_runs(baseline: dict, candidate: dict) -> dict: ...
```

- [x] Write real-format synthetic fixtures and tests for NUL-padded and accumulated
  Butterscotch reports, focused PASS/FAIL, exact identities, host sweep rows,
  screenshot transcription and simulated report preservation.
- [x] Run `python3 -m unittest test_benchmarks -v`; confirm missing collector fails.
- [x] Implement strict metadata, numeric/row validation and report parsing.
- [x] Implement immutable collection, hash verification and compatible comparisons.
- [x] Implement `python3 -m benchmarks import|verify|compare` with nonzero errors
  and no traceback for invalid user input.
- [x] Run the tests, then exercise subprocess CLI transfer/verify/compare with
  temporary files. Inspect stored raw bytes and normalized units.

## Task 2: Usable transfer instructions and verification

**Files:** Create `benchmarks/README.md`, example metadata/summary files; update
`README.md`, `ARCHITECTURE.md` and this plan's completed checkboxes.

**Interfaces:** Commands documented against the implemented CLI; examples are
explicitly synthetic, not device measurements or production build identities.

- [x] Document actual save-slot paths, quit/flush, card-to-Mac import, explicit
  report selection, host CSV and screenshot limitations, outputs and comparison.
- [x] Run `python3 -m unittest discover -v`, `python3 -m benchmarks --help`, example
  imports, `git diff --check` and inspect the final file list.
- [x] Warm signing with `gpg-warm-agent`, commit with a conventional message and
  Codex attribution; verify commit signature and clean working state.

## Plan review

The spec's acceptance cases map to Task 1 tests; transfer/limits map to Task 2.
No dependency downloads, firmware builds, deployment, bookmark moves or remote
publication are part of these tasks. The harness checkout is clean and detached;
execute locally there without changing a shared branch.
