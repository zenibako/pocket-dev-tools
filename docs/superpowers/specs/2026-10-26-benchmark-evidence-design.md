# Unified benchmark evidence

Approved approach: the 2026-10-26 chat proposal, followed by “let's do it”.

## Existing decisions

- `ARCHITECTURE.md` keeps application hooks separate and requires separately
  validated hardware adapters. The validated RTL workloads remain Butterscotch.
- `bench/README.md` defines immutable revision evidence and explicit timing limits.
- `../Butterscotch/src/openfpga/docs/2026-10-18-focused-pocket-benchmark.md`
  defines scene rejection, own-frame work, correlated samples and log flushing.
- `../vvvvvv-perf/openfpga/README.md` defines focused/exhaustive suites, host CSV
  units and device results pages. Its CSV is not device output.

## Deliverable

Add a standard-library Python evidence collector in this repository. It wraps
existing reports without modifying firmware, frozen inputs, active game sources,
SDK pins or SD cards. It imports Butterscotch standard/focused save-slot logs,
VVVVVV host sweep CSV, existing harness revision reports, and manually transcribed
device summaries with their original screenshots. It compares compatible runs
without mixing host, simulation and device timing domains.

This is the first working integration of the approved approach. Writing a new
VVVVVV device exporter, PICO-8 RTL adapter, device calibration and new hardware
runs are separate application/platform work. Imports cannot establish those gates.

## Preferred device packaging

The user's follow-up preference is dedicated benchmark cores, installed beside
normal gameplay cores. Prefer isolated settings, progress, result slots and
Memories identity, automatic suite launch, visible build identification and
post-sampling report persistence. Reuse the gameplay build's matched pinned
runtime/bitstream and relevant production paths. Shared immutable assets require
matching hashes; shared OS files must not be overwritten by a different runtime.
Keep normal gameplay pacing and lifecycle acceptance as separate required cases.

Record the effective core role in `conditions.core_role` so benchmark/gameplay
cases cannot be silently compared. Optional declared `deployment` metadata holds
core ID/save namespace/package hash and may differ for side-by-side A/B packages.
Existing core packaging/exporters are unchanged by this collector preference.

## Contract

Version 1 metadata records project/game, source/build identity, compiler and flags,
platform variant/clock/device, case/suite/route/mode/seed/target rate/warmup/expected
rows, conditions and repeat number. Optional binary/runtime hashes are explicitly
unknown when absent. Preserve all metadata and raw source bytes. Distinguish
declared identity from embedded identity; no collector can prove what was flashed.

Normalized rows use named numeric metrics with explicit units, optional sample
counts and stable identifiers. Absence is not zero. No percentiles are synthesized
from averages. Comparison requires equal backend, adapter, workload configuration,
row roster and sampling denominators. Compiler/settings differences are explicit
comparison failures. Build identity and repeat number may differ. Comparisons
report numeric deltas, not independent correctness or statistical significance.

## Transfer and validation

Butterscotch saves contain NUL-padded text and potentially multiple report blocks.
Require a complete end marker and explicit report index when ambiguous. Focused
reports must have the matching PASS/FAIL line and seven windows; check mode, seed,
clock and resolved embedded build identity against metadata. Preserve FAIL runs
as failed evidence. Standard reports have no commit ID: attribution stays declared.

VVVVVV SWEEP_VIEW/SWEEP_RESULT are host microseconds. Require the completed smoke
test footer and matching row counts. Keep view rows and cross-view summaries
separate. Device summaries require screenshot attachments, explicit units and
expected rows; mark transcription and correctness as unverified.

Import only explicitly selected files. Create a new immutable local run directory
under `build/benchmarks`, copy raw files plus metadata, hash every stored artifact,
and write normalized results. Never delete or overwrite source/destination runs.
Reject incomplete, malformed, duplicate-row, non-finite, mismatched or stale
evidence. A new import is not a new physical run. Repeated identical evidence with
the same metadata is deduplicated. Loading/comparing rechecks stored hashes.

Existing harness revision reports retain their reported verification status and
limits; collection is archival, not a rerun of their private source/hash checks.

## Acceptance

Test actual CLI round trips with synthetic, explicitly non-device fixtures;
NUL padding, accumulated reports, incomplete/failing reports, build/mode/clock
mismatches, host/device separation, screenshot requirements, stale hashes,
no-overwrite behavior, roster/sample mismatch and compatible comparison deltas.
Run the existing tooling regression suite. No speed or device claim is implied.
