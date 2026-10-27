# Platform profiles and controlled experiments

Approved by the user's request to add platform profiles, a coverage matrix,
controlled comparison and skill guidance. Reconciles
`2026-10-26-benchmark-evidence-design.md`, `benchmarks/README.md`, the dated
consumer audit and the existing strict comparison rules. No frozen CPU inputs,
runtime identifiers, source pins, active consumers or SD files change.

## Profile contract

A version-1 profile is an immutable declaration with required fields:

```json
{
  "schema_version": 1,
  "id": "example-os20-90",
  "variant": "os20",
  "clock_hz": 90000000,
  "cpu": {
    "isa": "rv32imafc", "issue_width": 2,
    "icache_bytes": 32768, "dcache_bytes": 65536,
    "config_sha256": "64 lowercase hexadecimal characters"
  },
  "sources": {"os_revision": "exact source identity", "sdk_revision": "exact SDK identity"},
  "artifacts": {
    "os_sha256": "64 lowercase hexadecimal characters",
    "bitstream_sha256": "64 lowercase hexadecimal characters",
    "loader_sha256": "64 lowercase hexadecimal characters"
  },
  "features": []
}
```

This illustrative shape is not a measured or valid literal profile. The profile
creator hashes four explicitly supplied local files (OS, bitstream, loader and
CPU config). It never infers clock from variant or overwrites conflicting hashes.
The four initial cells are os20/os25 × 90/100 MHz; all need their own actual
artifacts. CPU/cache fields are declared, not invented from the variant label.
Canonical sorted JSON determines the profile SHA-256. Optional description is
descriptive; unknown schema fields are rejected. No checked-in profile claims
that hardware was built or tested.

`import --profile FILE` requires a device result, known matching metadata clock
and variant, and agreement with any supplied runtime/bitstream/loader/SDK/OS
identities. It retains original profile bytes in the hashed bundle and embeds
`platform_profile: {definition, sha256}` in the result. The run identity includes
the binding. Binding states the intended artifact identity, not flashed-device
attestation. Legacy imports remain unchanged and readable.

## Comparisons

The default software comparison preserves existing strict compatibility. Two
bound runs require matching profiles. Unbound legacy comparisons remain
descriptive and explicitly provisional; bound versus unbound is incompatible.

The new explicit platform mode is device-only, with complete validated bindings,
known equal compiler/flags, equal application source and non-null ELF SHA-256,
equal nonempty device ID, matching full case/conditions/sample roster, and a
required `conditions.asset_manifest_sha256` identifying game/cart assets.
Both runs must be complete and not report failure. Transcribed results remain
unchecked; profiling is not correctness verification.

The caller declares `--vary clock`, `variant`, and/or `runtime`. Actual semantic
differences must match the declared factors. Clock is independent of variant.
Variant includes CPU/cache/feature changes. Runtime includes source/SDK changes,
CPU-config implementation changes within a nominal variant, and artifact-only
changes with no clock/variant change. Associated binary hashes may change when
clock/variant changes, but are always disclosed; CPU/source/settings controls
still apply. Extra profile/metadata differences are not silently ignored.
Changing several factors produces a combined experiment, not isolated causality.
No timings are rescaled by 90/100. The existing simulation importer remains
limited to the pinned os25/100 MHz model; profiles do not extend its coverage.

## Coverage

Matrix rows are grouped by exact workload/application/conditions/backend/device
scope and always expose all four cells. Each cell retains profile IDs, run IDs,
counts and failures; provisional, host, simulated and device evidence remain
distinct. A declared profile is `profile_registered`, not `built` or
`hardware_verified`. Imported device PASS remains a reported check. No stage is
promoted merely because hashes exist or a summary imports successfully.
Unknown clocks/variants are listed as unclassified. Explicit synthetic fixtures
are excluded from physical coverage. Empty selected scopes show untested cells.
Coverage aggregates identities and status, never mixes or averages timing rows.

## CLI and persistence

Add `profile create`, `profile verify`, `matrix`, `import --profile` and
`compare --mode software|platform --vary ...`. JSON output is inspectable;
optional output files remain inside the private harness build directory and
refuse overwrite. Matrix inputs are explicitly selected bundles or their
immediate store directory; load verifies archived hashes and rejects stale or
incomplete bundles. Existing source files and archives are not rewritten.

## Verification and skill

Write failing tests first for all four permutations, missing/conflicting hashes,
profile preservation/tampering, legacy compatibility, all controlled factors,
uncontrolled app/asset/device changes, synthetic/provisional coverage and actual
CLI round trips. Run the existing regression suite and an independent review.
Update the canonical skill and maintained reference; consumer routers already
read that canonical skill, so their bodies need no duplicated workflow changes.
