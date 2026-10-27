# Platform experiments implementation plan

> **For agentic workers:** Use test-driven implementation with disjoint modules and a final independent review.

**Goal:** Bind device evidence to explicit platform identities and safely compare
the os20/os25 × 90/100 MHz matrix.

**Architecture:** Profiles provide validation/hash binding, comparison owns
controlled platform experiments, coverage computes status-only matrices, and
the existing collector/CLI integrates them without changing frozen replay.

**Tech Stack:** Python 3.10+ standard library and unittest.

**Spec:** `docs/superpowers/specs/2026-10-27-platform-experiments-design.md`

## Global constraints

- Preserve legacy archives, strict software matching and simulated/device scope.
- No runtime/pin/config identifier changes or new hardware qualification claims.
- All new identity/provenance checks have negative tests and CLI execution.
- No output overwrite, source changes or SD writes; generated evidence is private.
- Local commits are conventional and GPG signed, without publication.

## Interfaces

```python
# profiles.py
validate_profile(profile: dict) -> dict
profile_digest(profile: dict) -> str
bind_profile(profile: dict, metadata: dict) -> dict  # {definition, sha256}
validate_binding(binding: dict, metadata: dict) -> dict
profile_from_files(definition: dict, *, os_bin, bitstream, loader, cpu_config) -> dict
verify_profile_artifacts(profile: dict, *, os_bin, bitstream, loader, cpu_config) -> dict

# model.py (shared metric arithmetic)
compare_rows(baseline: dict, candidate: dict) -> list[dict]

# comparison.py
compare_platform_runs(baseline: dict, candidate: dict, varied) -> dict

# coverage.py
coverage_matrix(runs, profiles=(), *, project=None, game=None, case_id=None) -> dict

# store.py
collect(..., profile_path=None)  # exact profile file + binding preserved
```

## Tasks

- [x] Profiles: implement the above contract in `benchmarks/profiles.py` with
  focused tests `test_platform_profiles.py`; verify schema/hash/source identity,
  all four cells and file hash conflicts. No dependency on store.py.
- [x] Controlled comparison: implement `benchmarks/comparison.py` and
  `test_platform_comparison.py`, consuming validated bindings and compare_rows.
  Check explicit factors, fixed workload/app/assets/toolchain/device and raw
  disclosure. Retain unknown/transcription limits and no frequency normalization.
- [x] Coverage: implement `benchmarks/coverage.py` and `test_platform_coverage.py`;
  compute four-cell status per exact scope, retain all failures/IDs, exclude
  synthetics and list unclassified unknown configurations.
- [x] Integration: extend store/model/CLI with profile binding, provisional
  software result qualification and actual profile/matrix/platform CLI tests.
  Test archival hashes and output containment/overwrite rejection.
- [x] Documentation/skill: maintain one reference for profile schema, commands,
  factors and coverage interpretation; update canonical skill to route there.
- [x] Verification: run full unittest suite, synthetic CLI pipeline, both target
  skill/catalog audits, local links and independent code/behavior review. Address
  findings. Deliver with a signed local commit and verify its signature/state.

## Dependency review

Profile and coverage modules are independently owned. Controlled comparison
consumes the agreed profile binding and row-delta APIs. Root integration owns
store/model/CLI only. New tests may initially fail on missing APIs; each worker
must record the failure before implementation. Parent resolves shared interfaces
and reviews the completed feature. No worker edits frozen inputs or consumer
repositories.

## Verification evidence

The initial focused tests failed on missing profile/comparison/coverage modules
and the absent collector/CLI integration. All 97 repository tests subsequently
passed, including synthetic profile create/verify/import, archive preservation,
strict and controlled comparison, matrix output and failure paths.

An independent local review ran 72 collector/platform tests and found no
actionable issues. CodeRabbit's external review was blocked by automatic approval
review because it would disclose private local changes to that third party;
the local review and tests completed instead. No external code review result is
claimed.

The old skill baseline could archive runs but lacked registration, coverage and
intentional platform-comparison guidance. A fresh-context forward evaluation of
the updated skill found all commands and controls, exercised help and confirmed
four untested empty-matrix cells. It identified the CPU-config/clock and
firmware-only classification boundaries, now explicit in the reference. This
is a reference retrieval check, not a measured skill-performance improvement.
Both Codex/Claude Harnessmith audits and both local skill catalogs passed
without warnings. Static discovery is not host auto-selection verification.
All 22 relative documentation links checked from the canonical and Claude skill
entries, collector/platform guides and repository README resolve.

All measurements remain synthetic in verification. No actual platform was
built, registered as hardware-qualified, flashed or tested, and frozen input
hashes and source pins remain unchanged. Final signature/state verification is
performed after the local signed commit.
