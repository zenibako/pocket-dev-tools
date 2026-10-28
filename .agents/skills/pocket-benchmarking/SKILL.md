---
name: pocket-benchmarking
description: Use when choosing platform profiles for a new Analogue Pocket project, planning benchmark cores, collecting device evidence, or comparing software and platform experiments with pocket-harness.
---

# Pocket benchmarking

Keep correctness, timing domain, build identity and physical-device validation
explicit across project-owned workloads.

## Locate and route

Canonical owner: <https://github.com/zenibako/pocket-dev-tools>, formerly
`pocket-harness`. Resolve this file's canonical path; use the verified checkout containing
it. Run collector commands from that root, where `benchmarks/__main__.py` lives.
Read the current project's instructions, architecture and pinned runtime before
using its performance/build skills. Older skill prose can lag deployed hardware.

Read the [collector guide](../../../benchmarks/README.md) for metadata, formats,
transfer paths and comparison rules. Use **os25-harness** for actual supported
RV32 capture/replay/profiling; read its canonical
[entry point](../os25-harness/SKILL.md). Result adapters do not add RTL workloads.
For artifact identity, four-cell coverage and deliberate platform changes, read
the [platform workflow](../../../benchmarks/PLATFORMS.md).
For a new port or a best-profile decision, use the
[project selection workflow](../../../benchmarks/SELECTION.md).

| Evidence | Collector format | Boundary |
| --- | --- | --- |
| Butterscotch standard/focused Pocket save-slot text | `butterscotch-device` | Inspect accumulated reports; select the intended complete block |
| VVVVVV complete host sweep output | `vvvvvv-host` | Host microseconds; CSV fragments may lack required counts/footer |
| VVVVVV/Pico8Pocket device screens | `device-summary` | Explicit transcription plus original screenshots; no OCR/correctness certification |
| Existing Butterscotch revision report | `harness-revision` | Select one case; archival import does not rerun its private provenance checks |

## Plan the device run

Prefer a dedicated benchmark core beside gameplay, with isolated settings,
progress, Memories identity and persistent result slots. Match pinned runtime,
bitstream, compiler and relevant production paths; record instrumentation and
pacing differences. A distinct core ID does not create an exporter. VVVVVV already
packages a benchmark core; current focused Butterscotch uses diagnostic entries.

Record real build/source and available binary hashes, hardware variant/clock,
route/seed/mode, warmup/sample roster, assets and effective settings. Put
`core_role` in `conditions`; put packaging IDs in optional `deployment` metadata.
Side-by-side A/B core IDs may differ while effective settings must match. For
PICO-8 record cart hash, logical/visible rates and render skipping separately.

Shortlist profiles compatible with the project's ISA/features, memory and SDK.
Record candidate, selected, incompatible or deferred profiles with reasons.
Each project evaluates its own shortlist; four-cell coverage is not a requirement.
Choose representative workloads, acceptance targets and metrics before testing.

Register each actual shortlisted combination with `profile create`:
declare CPU/ISA/issue/cache/features and OS/SDK sources, and hash the packaged OS,
bitstream, loader and CPU config. `profile verify` checks those local bytes.
Clock and variant are independent. A profile declares intended artifacts; it
does not attest what was flashed, timing closure or device correctness.

## Collect and assess

Finish sampling before screenshots or report writes. Butterscotch requires Quit
through the Analogue menu to flush save RAM, then mounting the card on the Mac.
Use explicitly selected source files; preserve raw evidence and keep bundles
private under this harness's `build/benchmarks/`. Do not modify the card.

```sh
python3 -m benchmarks --help
```

For Butterscotch logs, use `inspect` to select the intended report. Use `import`
with actual metadata for each format, then printed paths with `verify` and
`compare`. Bind device imports with `--profile` and a known matching clock and
variant. Host/simulation imports remain separate and cannot bind device profiles.
Legacy evidence stays readable and provisional; preserve its unknown identity.
The collector
checks archive hashes and compatibility; it does not establish physical behavior
or independently repeat source correctness tests. Preserve reported failures and
explicit unknowns. Synthetic examples are parser fixtures, not device evidence.

Compare matching domains/configurations and sampling denominators. Keep profile
and timing evidence distinct; overlapping counters and counterfactual modes are
not additive. Use paired device trials for variability, plus project correctness
and gameplay/launch/save/audio/sleep checks. The validated RTL applications remain
Butterscotch Undertale/Deltarune on the pinned os25 model. The separate Pico8
adapter can select bounded os20/90 MHz replay; read `os25-harness` and
`pico8/README.md` for its exact provenance and limits. VVVVVV replay remains
outside those workloads. The `harness-revision` evidence importer still accepts
only its original Butterscotch os25 report format.

## Check coverage and select a comparison

Run `matrix` with explicitly selected bundles/store directories and registered
profiles. Every exact workload/application/conditions/backend/device scope shows
all four cells. Inspect counts and failures, plus unclassified unknown-clock
runs and synthetic exclusions. `profile_registered` is a declaration;
`device_observed` may be unchecked; `device_reported_pass` retains a source PASS.
Screenshot transcription never creates correctness PASS. Simulation and host
evidence remain in separate rows. Counts are imports, not independent trials.
Keep evidence status separate from project applicability: an untested cell may
be deliberately unselected. Generic new project IDs can use screenshot-backed
`device-summary` imports; project-specific adapters and RTL scope stay bounded.

Use default `compare` for software regressions with the platform fixed. Two bound
runs need identical profiles; bound/unbound comparisons are rejected. For an
intentional platform experiment use `compare --mode platform` and declare each
actual `--vary clock`, `--vary variant` and/or `--vary runtime`. Require complete
device bindings, the same known compiler/flags, application source and ELF hash,
device ID, full workload/conditions and sampling roster. Record
`conditions.asset_manifest_sha256` for the actual asset set. Other effective
settings stay fixed. A changed application ELF does not qualify for this mode.
The platform workflow defines factor detection and exact CLI examples.

If SDK/platform support requires different ELFs, assess whole working
configurations using `compare --mode configuration --reason "why these builds differ"`.
Keep device, assets, full case/conditions, adapter and sample/metric rosters fixed.
Both runs need complete device profile bindings and known ELF/source/toolchain
identities. Inspect detected components, all field/presence differences, both full
configuration contexts and source checks/limits. Default and controlled platform
comparisons remain strict. Configuration deltas do not isolate a CPU, clock or
OS effect and do not automatically rank candidates. Use repeated device trials.
Recommend the best eligible tested configuration against the project's targets,
including variability and independent correctness/lifecycle results. A tie or
insufficient evidence is a valid decision. Leave irrelevant profiles unselected.

Preserve all disclosed artifact differences and source limitations. Keep literal
units, without 90/100 scaling. Multiple varying factors form a combined
experiment; they do not isolate a clock or CPU effect. Profiles and coverage do
not extend any replay model. Use the workload-specific replay guides separately.

For consumer discovery, stale guidance and remaining integrations, read the
[dated project audit](../../../docs/skills/2026-10-27-pocket-benchmarking-audit.md).
This skill depends on its checkout's maintained docs; copying SKILL.md alone is
not a standalone installation.
