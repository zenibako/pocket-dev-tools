# Routine regressions against a preserved baseline

Use a project-owned reference to check routine software updates before repeating
a device benchmark campaign. This follows the [evidence contract](README.md),
[platform comparison rules](PLATFORMS.md) and [workload boundaries](../ARCHITECTURE.md).
The reusable part is the evidence and decision contract. Each project keeps its
own workload, build commands, correctness oracles and hardware acceptance tests.

## Select an execution path

| Project or evidence | Available path | Scope |
| --- | --- | --- |
| Butterscotch on pinned os25 | [`regression.py baseline/check`](../docs/REGRESSION.md) | Automated complete-frame roster, repeat captures, RTL and negative controls; fixed audio |
| Pico8Pocket | [`pico8/` launcher](../pico8/README.md) | Its bounded cart/platform/seed workflow; the Butterscotch regression command does not accept Pico8 cases |
| VVVVVV | Project host tests and `vvvvvv-host` collection | Complete host sweeps; device summaries need screenshots and separate correctness checks; no VVVVVV RTL adapter |
| Another port | Project tests plus supported [evidence collection](README.md) | Adopt the contract below; automatic target replay requires a validated workload adapter |

Use the shared checkout verified by the calling skill and record its commit.
Check its current CLI help before using commands. A collector format, platform
profile or renamed repository does not add replay support. Missing tools or
private inputs are coverage gaps, not successful checks.

## Establish the accepted reference once

Choose representative workloads and project acceptance criteria before sampling.
Record the accepted source revision, application and asset hashes, platform/core
identity, compiler/version/ordered flags, native replacements, instrumentation,
memory placement, pacing, input route, seed, warmup and sample/frame roster.
Select profiles the project actually supports; four-cell coverage is not required.

Run the project's independent correctness tests and reproducibility checks.
Where replay exists, require same-binary capture/replay agreement and the
adapter's negative controls. Include a known bad candidate to demonstrate that
the cross-build decision catches the intended regression. A fresh reference
captured from a broken candidate can pass its own replay.

Preserve the accepted raw outputs, source/build identity, validation logs and
configuration as a new immutable case or hashed bundle. Record the exact paths
and digest in a private project baseline reference. Scope that reference to the
workloads actually verified. Baseline registration is separate from candidate
checking; it must never overwrite an existing reference or promote a candidate.

For supported Butterscotch cases, register the completed roster with:

```sh
python3 regression.py baseline --name accepted-reference --cases BASELINE_CASE_1 BASELINE_CASE_2
```

Use the printed index with `check --repo PORT_REPOSITORY --revision CANDIDATE_REVISION`.
Its configuration comes from the reference, including ordered extra flags;
the command creates independent candidates and never recaptures the baseline.
See the [exact CLI contract](../docs/REGRESSION.md) for controls and exit codes.
These are Butterscotch commands, not a generic project adapter interface.

## Check each candidate independently

1. Export/build the explicit candidate revision into a fresh private workspace.
   Keep the accepted baseline's files and index unchanged.
2. Match workload, assets, platform, compiler/settings and measurement domain.
   Trace and timing builds are separate evidence. Preserve ordered `-D`/`-U`
   flags; dropping or reordering them can change the workload.
3. Run candidate correctness and negative controls, then compare the relevant
   outputs independently across builds. For deterministic rendering/audio,
   compare raw pixels, geometry, palettes where applicable, PCM and sample counts.
   Pointer-bearing state hashes compare only the same ELF/checkpoint.
4. Retain failures, raw logs, both differing images and the detected changes.
   Stale, incomplete, incompatible or missing-control evidence fails a regression
   gate. Investigate changed output before explicitly accepting a new baseline.

Use only channels the adapter actually exports. Pico8's normal runner exports
channel hashes; raw-byte equality needs a separately verified collector. For
other projects, use their own defined output invariants and report unavailable
channels. Unknown identity or screenshot transcription does not become a
correctness PASS merely because numeric comparisons are possible.

Supported collector bundles can be retained and compared with:

```sh
python3 -m benchmarks verify BASELINE_BUNDLE
python3 -m benchmarks verify CANDIDATE_BUNDLE
python3 -m benchmarks compare BASELINE_BUNDLE CANDIDATE_BUNDLE
```

Collection verifies archive integrity and reports compatible numeric deltas; it
does not rerun project tests or act as an output-regression gate. Preserve both
inputs' `source_checks` and limitations. A project's wrapper must require its
own correctness results and define any acceptance decision. Do not invent a
universal slowdown threshold from one run or compare host, simulated and device
timings as one domain.

## Deliberate configuration changes and device coverage

A compiler, SDK, CPU, clock or effective-setting change requires a separately
recorded experiment and accepted reference. Use the existing comparison modes:
controlled platform comparisons require the same application ELF; profiles
requiring different ELFs use whole-configuration mode with an explicit reason
and all detected changes retained. See [profile selection](SELECTION.md).
BRAM/SDRAM comparisons can include compiler inlining differences, so their
timing deltas describe complete compiled configurations.

A routine pass covers its selected workload and oracles. Run the project's
applicable device checks for changes involving actual storage, save/Memory
compatibility, display/audio scheduling, runtime ABI, sleep/wake or hardware.
Performance claims and best-profile choices need representative paired device
trials. Keep physical SD behavior, audible quality and board timing separate
from simulation. Game data, carts, saves, captures and baseline bundles stay
private; share the scripts, contract and declared coverage.
