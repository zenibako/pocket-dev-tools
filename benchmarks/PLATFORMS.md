# Platform profiles and experiments

Use one explicit profile per actual OS/CPU/clock/artifact combination. `os20`
and `os25` are variant labels; neither determines the clock or cache sizes.
The coverage reporter always shows these four independent cells:

| Variant | 90 MHz | 100 MHz |
| --- | --- | --- |
| os20 | separate profile and device evidence | separate profile and device evidence |
| os25 | separate profile and device evidence | separate profile and device evidence |

These are independent catalog axes, not mandatory support targets for each
project. Evaluate a compatible shortlist and record why other profiles are
incompatible, deferred or unselected. Use the
[project selection workflow](SELECTION.md) to decide which tested configuration
best meets a new port's performance and correctness requirements.

Representing a cell does not establish that its bitstream builds, meets timing,
or works on hardware. Profiles declare intended artifacts. They do not attest
what was flashed. The collector reads files and writes private Mac-side records;
it does not build a core, deploy it or write to the card. The `harness-revision`
importer remains limited to the pinned os25/100 MHz Butterscotch report format.
The separate [Pico8 replay adapter](../pico8/README.md) can use os20/90 MHz;
profile registration does not establish equivalence to its simulated platform.

## Create a profile from actual artifacts

Prepare `build/platform-definition.json` with the version-1 shape below, using
the actual CPU configuration and exact OS/SDK source identities. This excerpt is
an illustrative synthetic definition, not a hardware profile:

```json
{
  "schema_version": 1,
  "id": "fixture-os20-90",
  "description": "Synthetic shape only; replace every identity and CPU declaration",
  "variant": "os20",
  "clock_hz": 90000000,
  "cpu": {
    "isa": "rv32imafc",
    "issue_width": 2,
    "icache_bytes": 32768,
    "dcache_bytes": 65536
  },
  "sources": {"os_revision": "fixture-os-source", "sdk_revision": "fixture-sdk-source"},
  "features": []
}
```

`features` is an explicit unique list of relevant enabled CPU/platform features.
Declare CPU/cache fields from the selected configuration, including local
changes; a source revision alone cannot identify a dirty build. The creator
hashes the exact four supplied local files:

```sh
python3 -m benchmarks profile create build/platform-definition.json \
  --os-bin build/package/os.bin --bitstream build/package/core.rbf \
  --loader build/package/loader.bin --cpu-config build/package/cpu.cfg \
  --output build/platforms/os20-90.json
python3 -m benchmarks profile verify build/platforms/os20-90.json \
  --os-bin build/package/os.bin --bitstream build/package/core.rbf \
  --loader build/package/loader.bin --cpu-config build/package/cpu.cfg
```

Those paths are examples: explicitly select the artifacts actually packaged,
including the loader containing the intended OS image where applicable.
`profile verify` checks byte hashes; it does not inspect loader embedding, fit,
timing closure, source-to-binary correspondence or hardware behavior.

The complete profile adds required lowercase SHA-256 values:
`cpu.config_sha256` and `artifacts.os_sha256`, `bitstream_sha256`,
`loader_sha256`. A supplied hash is checked, never replaced to hide a mismatch.
Missing identities, unknown fields, unsupported clocks and unknown/unversioned
sources are rejected. Canonical compact sorted JSON (UTF-8, escaped non-ASCII,
no newline) determines its SHA-256. Labels and descriptions participate too.
Keep the definition immutable; a rebuild or metadata correction creates a new
profile. Creation requires an unused output file under this harness's `build/`.

## Bind device imports

Record matching `platform.variant` and a known `platform.clock_hz` in the run's
metadata. Optional `build.runtime_sha256`, `bitstream_sha256`, `loader_sha256`,
`cpu_config_sha256`, `os_revision` and `sdk_revision`, when present, must match
the profile. A present null identity conflicts with a complete profile; omit
an unavailable optional declaration instead of inventing it.

```sh
python3 -m benchmarks import --format butterscotch-device \
  --source build/copied-pocket-log.sav --metadata build/device-run.json \
  --report-index 0 --profile build/platforms/os20-90.json
```

The format's existing checks still apply, including logged clock/firmware and
complete report selection. Do not map the device's numeric `core variant` field
to `os20`/`os25`; it is not a reliable OS-profile identifier.
Screenshot-backed `device-summary` imports accept profiles as well, and remain
manual, unchecked transcriptions. Host and simulation imports reject profile
bindings to avoid treating packaged hardware as an identical timing backend.

The bundle preserves exact `platform-profile.json` bytes and hashes them in
`manifest.json`. `result.json` contains `platform_profile: {definition, sha256}`;
the digest also participates in run identity. `verify`, comparisons and matrix
loading check both the binding and original profile file. Legacy bundles remain
readable without being rewritten. Hashes detect stale content; these archives
are not signed attestations.

## Inspect coverage

```sh
python3 -m benchmarks matrix --runs build/benchmarks \
  --profiles build/platforms/os20-90.json build/platforms/os25-100.json \
  --project butterscotch --game undertale --case flowey-battle \
  --output build/platform-coverage.json
```

`--runs` accepts one or more explicit bundle or store directories; stores load
their immediate child bundles. Invalid, stale or interrupted bundles fail the
command. It does not recursively scan a workspace. Duplicate run IDs are
rejected. Use explicit selected bundles when a store contains unrelated work.
`--profiles` accepts zero or more registered declarations, independently of runs.
Omit `--runs` to see the untested/registered cells before collection. JSON is
printed; optional output files must be unused paths under `build/`.

Each row fixes project, game, full case, application source/ELF/compiler/flags,
conditions, timing backend, device, extra platform settings and adapter config.
Different scope produces a separate row; a matrix row is not permission to
compare its timings. Cells contain profile IDs/digests, run IDs, per-evidence
counts, checks, failures and full build/deployment context. They do not average
or rescale timing measurements.

| Cell status | Meaning |
| --- | --- |
| `untested` | No selected run or registered profile |
| `profile_registered` | Declaration exists; no selected observation |
| `provisional` | Device identity lacks a profile, or evidence is incomplete |
| `host_observed` | Complete host evidence in its own backend row |
| `simulated` | Complete simulation evidence in its own backend row |
| `device_observed` | Complete device evidence bound to a profile; correctness may be unchecked |
| `device_reported_pass` | Such evidence also retains a source-reported PASS |
| `reported_fail` | A selected run reports failure; retained even alongside passing runs |

Counts preserve mixed evidence within a cell; inspect `failures` as well as
status. Incomplete runs remain listed and cannot become device observations.
A screenshot transcription does not acquire PASS by importing successfully.
Unknown clocks/variants appear in `unclassified` with reasons. Explicit
`conditions.synthetic_fixture: true` inputs appear only in the exclusion list.
Counts measure imported records, not independent physical trials. No status
means independently verified correctness, fit or hardware acceptance.
`untested` means no selected evidence; it is not a requirement to build/test that
cell. Project applicability and evaluation scope belong in the selection note.

## Choose the comparison mode

| Mode | What may change | Interpretation |
| --- | --- | --- |
| `software` (default) | Application source/ELF on the fixed platform/toolchain | Descriptive software delta |
| `platform` | Explicitly declared platform factors with the same ELF/toolchain | Controlled combined platform delta |
| `configuration` | Known application source/ELF/toolchain and platform identities | Whole-configuration delta with a required reason |

The default software comparison continues to hold platform, workload,
conditions, compiler/flags/SDK/runtime and sampling fixed while application
source/ELF may change:

```sh
python3 -m benchmarks compare build/benchmarks/BASELINE build/benchmarks/CANDIDATE
```

Two bound runs require identical profiles. Bound versus unbound is rejected.
Two legacy unbound runs can still produce descriptive deltas, explicitly marked
`qualification: provisional`, including when their clocks are unknown. They
cannot establish coverage with complete platform identity.

Use explicit platform mode for the same application binary and assets on the
same physical device:

```sh
python3 -m benchmarks compare build/benchmarks/OS20_90 build/benchmarks/OS20_100 \
  --mode platform --vary clock
python3 -m benchmarks compare build/benchmarks/OS20_90 build/benchmarks/OS25_100 \
  --mode platform --vary clock --vary variant --vary runtime
```

The second command is an example of a combined experiment; supply only the
factors actually changed. Declared and detected factors must match exactly:

| Factor | What changes |
| --- | --- |
| `clock` | `clock_hz`, independently of variant |
| `variant` | Variant label, CPU/ISA/issue/cache semantics, or enabled features |
| `runtime` | OS/SDK source, CPU-config implementation within unchanged CPU semantics, or artifact-only changes with no clock/variant change |

Associated artifact hashes may change with clock/variant and are disclosed in
full. OS/SDK source changes also require `runtime`. Firmware differences require
`runtime`; reported numeric core differences require `variant` and are never
used to infer the OS label. Arbitrary extra settings remain fixed controls.
Profile ID/description changes alone are not a platform experiment.
A changed CPU-config hash without changed CPU semantics requires `runtime`,
including when its file also contains the changed clock. That conservative
classification keeps uninspected implementation changes explicit. A firmware
label change alone cannot establish a runtime experiment without a changed
profile source/config/artifact identity.

Platform mode requires complete device runs with validated profiles, identical
known compiler/flags, application source and non-null `build.elf_sha256`, known
equal `platform.device_id`, full case/conditions, adapter and sample/metric
rosters. Record `conditions.asset_manifest_sha256` as the lowercase SHA-256 of
the stable manifest identifying the actual game/cart asset set. Build labels,
repeat number and `deployment.core_id` may differ. Other deployment settings
remain fixed. If the port requires a different ELF for a new SDK/OS, that pair
does not qualify as a controlled platform-only experiment.

Output retains literal-unit deltas and every declared profile/metadata
difference, including binary hashes. It never rescales timings by 90/100.
Several varying factors describe a combined change without isolating causality.
Paired repeated device trials, independent project correctness and gameplay,
launch/save/audio/sleep checks remain separate requirements. Preserve the
transcription, unchecked-oracle and instrumentation limits of the source runs.

## Compare profiles requiring different ELFs

Use configuration mode when SDK/platform support requires a rebuilt application
and you want to evaluate the resulting working configurations:

```sh
python3 -m benchmarks compare build/benchmarks/BASELINE build/benchmarks/CANDIDATE \
  --mode configuration --reason "The candidate SDK requires a rebuilt ELF and different compiler flags."
```

`--reason` is required, nonempty and preserved exactly. It is the caller's
explanation, not an independently verified fact. It does not waive workload or
evidence checks. `--vary` belongs only
to platform mode, while `--reason` belongs only to configuration mode. The
existing software and controlled platform comparisons keep their restrictions.

Both sides require validated device profiles, complete runs, known application
source/ELF, compiler and flags, a known physical device ID and an asset-manifest
hash. Reported failure, unknown correctness status, missing identities, host or
simulation evidence cannot enter this mode. An unchecked screenshot-backed run
may be described, with its unchecked status and transcription limits retained.

The configurations may differ in application source, ELF SHA-256, compiler,
flags and profile identities. Optional runtime/SDK/loader/config declarations
must agree with each side's profile; differing optional-field presence is
disclosed. Build labels, repeat numbers and deployment core IDs may differ.
Project/game, physical device, full case/conditions (including assets, seed,
pacing and audio), adapter/config, extra build/settings and sample/metric
rosters remain fixed. Other deployment settings remain fixed too. Reported
hardware differences must correspond to actual changed profile factors;
unknown nested reported settings are not silently ignored.

Output includes:

- `assessment: descriptive_configuration_experiment` and
  `attribution: whole_configuration_only`.
- The `comparison_reason`, run IDs and both profile digests.
- Detected `changed_components`: application, toolchain, clock, variant and/or
  runtime. These are detected changes, not claims of isolated causality.
- Field-by-field `differences` for profiles, metadata, source checks and reported
  hardware, with both values and explicit presence flags for added/removed fields.
- Full `configurations.baseline` and `.candidate` metadata, profile bindings,
  checks and source limitations, including identities that stayed the same.
- Literal-unit row deltas, preserving both source limitations and the absence
  of statistical significance, independent correctness or an automatic winner.

Labels/repeat numbers alone do not constitute a changed configuration. Timings
are never frequency-rescaled. The result can inform which complete working
configuration met the project's targets; it cannot isolate an OS, CPU, cache,
clock, compiler or application effect. Use repeated trials, independent project
checks and the [selection workflow](SELECTION.md) for a scoped recommendation.
