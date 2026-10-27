# Choose a platform for a project

The goal is the best supported configuration for this project's workloads.
Each project evaluates a shortlist of plausible profiles. The four-cell matrix
is an inventory of evidence; it does not require every project to build, support
or test all four combinations. An unselected cell is not a failing requirement.

Start from [platform identities and commands](PLATFORMS.md) and the project's
architecture/build decisions. Existing project results can suggest candidates;
they do not establish which CPU/cache/clock configuration wins for a new port.

## Shortlist candidates

Record a small private selection note under `build/` with each actual profile
ID/digest, disposition and reason:

| Disposition | Meaning for this project |
| --- | --- |
| Candidate | Compatible enough to evaluate against the project's goals |
| Selected | Preferred among the eligible configurations actually tested |
| Incompatible | A known ISA, feature, memory, SDK/API or packaging requirement excludes it |
| Deferred | Plausible, but outside this evaluation's scope or awaiting a build |
| Not considered | No present reason to evaluate it |

These dispositions belong to the selection note, separately from collector
evidence statuses. The CLI does not infer compatibility, parse this note, or
change `untested` into `incompatible`. A generic archived runtime is an available
candidate, not proof of a supported consumer package. Retain source/build/timing
uncertainty as qualifications of that candidate.

For example, a new port might evaluate os20/90 and os25/100, deliberately exclude
os20/100 and defer os25/90. Completing that two-profile evaluation is sufficient
for a scoped recommendation. There is no requirement to fill the other cells.

## Use representative device workloads

Choose the performance objective before collecting data: frame budget and tail
latency, loading, audio headroom, or another concrete requirement of the port.
Use real scenes/carts that represent its CPU, drawing, memory and I/O costs.
Keep workload, assets, initial state, seed, warmup, sampling, pacing and observer
settings fixed where practical. Record the exact application and platform bytes.

Use repeated paired trials on the same Pocket. Collect the metrics the source
actually provides, including sample counts and variability. Averages cannot
establish a tail-latency win; one noisy run cannot establish a reliable winner.
Test the project's correctness and lifecycle requirements independently. A fast
configuration that fails those requirements is not an eligible recommendation.

Compare the shortlisted candidates on the same scenes and acceptance criteria.
Record tradeoffs across scenes, not only the most favorable benchmark. If the
results are within observed variability, report a tie or insufficient evidence.
With one tested candidate, report demonstrated suitability rather than claiming
it is faster than untested alternatives.

## Bring a new project into the collector

`metadata.project` is a stable lowercase ID, 1–64 characters: letters/digits
starting with a letter, with single internal hyphens. Existing IDs remain valid;
a new port can use `nova-pocket` without editing an allowlist.

The generic entry path is `device-summary`: explicit measurements plus original
PNG/JPEG/GIF screenshots. Follow the [collector guide](README.md) for row units,
metadata and source preservation. Use only measurements actually visible in the
original source. Transcription stays unchecked; import never creates correctness
PASS. An automatic text/binary exporter requires an appropriate validated
adapter. New IDs do not add a host adapter or RV32/RTL workload.

For a two-profile shortlist, with real definitions and measurements already
prepared under `build/`:

```sh
python3 -m benchmarks matrix --project nova-pocket --game nova \
  --profiles build/platforms/nova-os20-90.json build/platforms/nova-os25-100.json

python3 -m benchmarks import --format device-summary \
  --source build/nova-os20-90-values.json --metadata build/nova-os20-90-run.json \
  --attachment build/nova-os20-90-page1.png --profile build/platforms/nova-os20-90.json
```

Repeat collection/import for the other candidate and actual repeated trials.
Use the printed bundle paths with `verify` and `matrix --runs ... --project
nova-pocket`. Pass only relevant registered profiles. The matrix still shows
all four axes; interpret them through the project's shortlist. Different
application binaries produce separate evidence scopes.

## Choose a comparison and record the decision

If the same application ELF, known toolchain, assets, device and full workload
controls work across both profiles, use the controlled platform mode:

```sh
python3 -m benchmarks compare build/benchmarks/OS20_90_RUN build/benchmarks/OS25_100_RUN \
  --mode platform --vary clock --vary variant
```

Add `--vary runtime` when detected source/config/runtime changes require it.
The [factor rules](PLATFORMS.md) govern the actual differences. Changing multiple
factors evaluates their combined effect; it does not isolate clock or CPU
causality. Ordinary software regressions continue to use the strict default mode.

If a different SDK or platform needs a different application ELF, evaluate the
complete working configurations. Retain each ELF/toolchain/settings identity and
the reasons it differs. Read the archived rows side by side on the same
workloads, with repeated device trials and independent correctness evidence.
The collector's strict and controlled comparators intentionally reject this
pair; there is no automatic configuration-ranking command. A practical result
can support “configuration A met our targets better than configuration B.” It
cannot attribute the difference solely to the OS, cache or clock. Do not relax
identity checks or relabel the two binaries to obtain a platform comparison.

End the selection note with the evaluated candidates and evidence bundle IDs,
performance/variability against the chosen targets, correctness and lifecycle
results, selected profile or tie, and remaining qualifications. Explain why any
other profiles were excluded or deferred. Recommend the best among the eligible
tested configurations; scope the conclusion to this project and workload set.
