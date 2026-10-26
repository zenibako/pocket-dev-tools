# Benchmark collection and transfer

The collector wraps existing evidence; it does not launch games, deploy builds,
write an SD card, add device exporters or extend the validated RTL applications.
It needs Python 3.10+ with no additional dependencies. Run commands from the
`pocket-harness` root.

## What currently leaves the Pocket

| Project | Device evidence | Transfer |
| --- | --- | --- |
| Butterscotch standard | Text in `Saves/butterscotch/common/undertale_1.sav` or `deltarune_1.sav` | Quit through the Analogue menu, mount the card, import the chosen file |
| Focused Deltarune tiles | Five accumulated reports in `Saves/butterscotch/common/deltarune_tiles_1.sav` | Quit through the Analogue menu after each mode; inspect and select each report |
| VVVVVV | Results pages on screen; benchmark writes currently stay in memory | Screenshot every page after measurement; import explicit transcriptions with their screenshots |
| Pico8Pocket | Profiler/menu screens, without a shared durable benchmark export | Import an explicitly identified device summary with screenshots; no PICO-8 RTL claim |

Pocket screenshots are normally under `Memories/Screenshots/` on the card. Take
them after a measured segment: capture pauses can contaminate frame times.
Butterscotch logs are NUL-padded and may include old/duplicate reports. A saved
focused report ends with `FOCUS PASS/FAIL <mode>` and `--- end of report ---`;
the UI's later “log saved” message need not be present in the file.

The `benchmarks/*.json` files in the surrounding build workspace are APF launch
descriptors, not measurement files. Do not import them as results.

## Before the run: record its identity

Prepare a metadata JSON for the exact package and case. Keep it with the package
on the Mac; the current device programs do not automatically emit this manifest.
Use `examples/undertale.json` as the shape, replacing its explicitly synthetic
identities and conditions with the actual ones. Copy that file under private
`build/` before editing. Record the source revision and build ID before copying
the build to the card. Hash the packaged ELF/runtime/bitstream when available.
Never guess the compiler, flashed binary or omitted measurements.

Version 1 required metadata:

- `schema_version: 1`, `project` (`butterscotch`, `vvvvvv`, `pico8pocket`), `game`,
  and integer `repeat` starting at 1.
- `build`: nonempty `id`, `source_revision`, `compiler` (string or explicit null),
  `flags` (list). Optional lowercase `elf_sha256`, `runtime_sha256`,
  `bitstream_sha256`, and additional provenance such as SDK revision are preserved.
- `platform`: `variant`, `clock_hz` (integer or explicit null), optional
  `device_id` and `firmware`. Device identity should distinguish separate units.
- `case`: `id`, `suite` (`smoke`, `focused`, `exhaustive`), `route_version`, `mode`,
  `seed` (integer or explicit null), `warmup_frames`, `target_hz`, and the exact
  `expected_rows` roster. Seed/warmup values describe the actual route.
- `conditions`: nonempty `initial_state`, `audio`, `pacing`. Add framebuffer,
  asset hashes, render skipping, cold/warm storage and other relevant settings.
  Extra settings participate in comparisons; keep their representation stable.

`case.target_hz` describes the intended game schedule; it does not rescale source
timings. Missing sample counts remain null. Unknown compiler/binary identity
limits provenance. “Embedded” means a source ID matched a focused log, not that
the collector has verified the flashed executable.

## Import a Butterscotch save-slot log

After the benchmark finishes, quit through the Analogue menu to flush the slot,
then mount the card on the Mac. Import reads the source and copies it locally.
No file is removed or rewritten on the card.

```sh
python3 -m benchmarks inspect /Volumes/Pocket/Saves/butterscotch/common/undertale_1.sav
python3 -m benchmarks import --format butterscotch-device \
  --source /Volumes/Pocket/Saves/butterscotch/common/undertale_1.sav \
  --metadata build/undertale-run.json --report-index 0
```

`inspect` lists zero-based report indices, titles, available source IDs and
completion markers. Choose the intended completed report; index 0 is merely
an example, not necessarily the newest run. If there are multiple headers, an
explicit index is mandatory, including for repeated identical reports.

For the focused tiles log, import each selected mode with its own metadata.
`route_version` must be `card-castle-tiles-v1`; `mode` is `normal`, `no-render`,
`no-audio`, `core`, or `profile`. All seven window names are required. The adapter
checks seed 7, the embedded source ID when versioned, CPU frequency, settings,
completion and window sample minima. `FOCUS FAIL` is retained as failed evidence
and cannot be compared as a performance improvement.

Standard reports require the device OS/CPU line but do not embed a source commit
or independent correctness oracle. Their source attribution remains declared.

## VVVVVV and other device summaries

The current VVVVVV screen exporter is manual. Make a JSON with `rows`, each
containing `id`, `samples` (integer or null) and a `metrics` object. Metric names
end in units, for example `frame_mean_us` and `frame_max_us`. Convert displayed
milliseconds to microseconds explicitly: 32.7 ms becomes 32700 us. Use stable
room/state IDs, not truncated screen names, and capture every required page.

```sh
python3 -m benchmarks import --format device-summary \
  --source build/vvvvvv-device-values.json --metadata build/vvvvvv-device-run.json \
  --attachment /Volumes/Pocket/Memories/Screenshots/page-1.png
```

Repeat `--attachment` for additional pages. A screenshot attachment is mandatory;
the importer does not perform OCR, inspect pixels or certify the transcription.
For ranked summaries, a room's peak across all viewports is a
`cross_view_max_us`; it need not belong to its worst-average viewport. Declare
the rows the screen actually reports, rather than claiming per-viewport samples
that the screenshot does not provide. No percentile is invented from an average.

This format can archive Pico8Pocket device values as well. Record logical and
visible FPS independently (for example `logical_hz`, `visible_hz`), alongside
render skipping, audio and cart hash. It does not establish a validated PICO-8
simulation adapter or automate cart launch.

## Host and simulation imports

```sh
python3 -m benchmarks import --format vvvvvv-host \
  --source build/vvvvvv-host.log --metadata build/vvvvvv-host-run.json
python3 -m benchmarks import --format harness-revision \
  --source build/revision-report.json --metadata build/replay-run.json --report-index 0
```

VVVVVV `SWEEP_VIEW` and `SWEEP_RESULT` CSV lines are host-only microseconds.
The adapter requires the successful smoke-test footer and matching case counts.
Use `view:mode:x:y:entry_y:camera` and `result:mode:x:y` for expected row IDs.
Mode 0 means stabilizer on, mode 1 off; camera -1 means continuous scrolling.
View peaks and cross-view summary peaks remain separate metrics. The recorded
source revision must contain the intended focused/exhaustive benchmark work.

`harness-revision` accepts the `experiments.py report` JSON with `cases`, one
selected case per import. Expected rows are `frame:<number>`. It preserves
configurations, reported negative-oracle status, substitutions and exclusions.
The adapter retains the report's original os25/100 MHz cycle model. Collection
archives that report; run the original verifier to recheck private source,
capture, ELF and RTL provenance before treating its simulation result as current.

## Saved bundle and comparison

Import prints the newly created directory under `build/benchmarks/<run-id>/`:

```text
metadata.json       exact original metadata bytes
raw/000.sav         exact source bytes (extension follows source)
raw/001.png         optional screenshot attachment
result.json         versioned normalized rows, checks and limitations
manifest.json       hashes for every stored file, written last
```

The directory is private and ignored. Imports refuse to overwrite an existing
run. Renaming an identical source does not create a new run; changing `repeat`
is a declaration about a real repeated trial, not permission to count one run
multiple times. Back up bundles as ordinary private files. Hashes detect stale
or accidentally changed content; they are not signatures or device attestation.

```sh
python3 -m benchmarks verify build/benchmarks/RUN_ID
python3 -m benchmarks compare build/benchmarks/BASELINE_ID build/benchmarks/CANDIDATE_ID
```

Verification checks archived file hashes, not physical behavior. Comparison
refuses different timing domains, adapters, projects/games, cases, declared or
reported platform, conditions, compiler/SDK/runtime context, row rosters and
sample counts (including the standard report's known total). Simulation
adapter/launcher hashes, substitutions and oracle exclusions also participate.
Application source/build IDs, ELF hashes and repeat numbers may differ. It emits descriptive deltas without inferring
statistical significance or an overall speedup. Host times remain host times;
simulated cycles remain simulated; device transcriptions stay unverified.

Use repeated, paired real-device runs to measure variance. Compare both normal
game pacing and fixed-work diagnostics, and test launch, storage, audio, saves
and supported sleep separately. Bitstream fit and timing closure are additional
hardware gates; this collector does not run them.

## Local smoke example

The checked-in example is synthetic, contains no assets, and is not a device
measurement. It exercises the transfer path without a Pocket:

```sh
python3 -m benchmarks import --format butterscotch-device \
  --source benchmarks/examples/undertale-report.txt \
  --metadata benchmarks/examples/undertale.json
python3 -m unittest test_benchmarks -v
```

## Remaining integrations

VVVVVV/Pico8Pocket need device-side durable exporters and build manifests to
eliminate manual transcription/attribution. PICO-8 also needs a separately
validated os20 RTL adapter; VVVVVV needs its own target replay adapter. None of
those are silently supplied by a result-format adapter. Existing immutable
Butterscotch replay matrices remain unchanged.
