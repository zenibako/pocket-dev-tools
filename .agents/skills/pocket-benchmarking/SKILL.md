---
name: pocket-benchmarking
description: Use when planning benchmark-specific Analogue Pocket cores, collecting on-device benchmark logs or screenshots, or comparing host, simulated, and device benchmark evidence with pocket-harness.
---

# Pocket benchmarking

Keep correctness, timing domain, build identity and physical-device validation
explicit across project-owned workloads.

## Locate and route

Resolve this file's canonical path; use the `pocket-harness` checkout containing
it. Run collector commands from that root, where `benchmarks/__main__.py` lives.
Read the current project's instructions, architecture and pinned runtime before
using its performance/build skills. Older skill prose can lag deployed hardware.

Read the [collector guide](../../../benchmarks/README.md) for metadata, formats,
transfer paths and comparison rules. Use **os25-harness** for actual supported
RV32 capture/replay/profiling; read its canonical
[entry point](../os25-harness/SKILL.md). Result adapters do not add RTL workloads.

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
`compare`. The collector
checks archive hashes and compatibility; it does not establish physical behavior
or independently repeat source correctness tests. Preserve reported failures and
explicit unknowns. Synthetic examples are parser fixtures, not device evidence.

Compare matching domains/configurations and sampling denominators. Keep profile
and timing evidence distinct; overlapping counters and counterfactual modes are
not additive. Use paired device trials for variability, plus project correctness
and gameplay/launch/save/audio/sleep checks. The validated RTL applications remain
Butterscotch Undertale/Deltarune on the pinned os25 model; current os20 consumers
need separate platform/workload validation.

For consumer discovery, stale guidance and remaining integrations, read the
[dated project audit](../../../docs/skills/2026-10-27-pocket-benchmarking-audit.md).
This skill depends on its checkout's maintained docs; copying SKILL.md alone is
not a standalone installation.
