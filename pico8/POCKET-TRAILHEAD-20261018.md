# Physical Pocket Trailhead capture — 2026-10-18

The user supplied one baseline and one palette-candidate report from the
[diagnostic capture package](CAPTURE-PERSISTENCE.md). Both cover Celeste 2
Trailhead along the same course, with movement not exactly matched. These are
physical-device report aggregates, not simulated timings or a controlled-input
A/B experiment. No source optimization is promoted on this evidence.

## Results

| Metric | Baseline | Palette candidate | Candidate change |
| --- | ---: | ---: | ---: |
| Logical FPS | 19.255 | 18.589 | -3.46% |
| Presentation-call FPS | 11.226 | 11.260 | +0.30% |
| Mean loop period | 51.933 ms | 53.793 ms | +3.58% |
| 95th-percentile period | 81.452 ms | 85.259 ms | +4.67% |
| 99th-percentile period | 107.018 ms | 111.428 ms | +4.12% |
| Maximum period | 118.080 ms | 203.526 ms | +72.36% |
| Mean runtime step, mixed draw/skip | 41.236 ms | 42.456 ms | +2.96% |
| Mean runtime step with draw | 50.565 ms | 51.489 ms | +1.83% |
| Derived mean step without draw | 28.191 ms | 28.579 ms | +1.38% |
| Derived presentation cost per call | 2.962 ms | 2.978 ms | +0.54% |

Baseline ran 578 logical frames and presented 337 images in 30.017521 seconds.
Candidate ran 558 and presented 338 in 30.016626 seconds. Near-identical image
counts explain why visible smoothness was difficult to distinguish. The
candidate completed 20 fewer logical frames in this pair.

Draw share changed from 58.30% to 60.57%. Divisor 1/2 counts were 104/474 for the
baseline and 132/426 for the candidate; neither used divisors 3/4. The higher
candidate draw fraction mixes more expensive draw frames into its per-logical-
frame average. This is one reason not to read the mixed-step percentage as an
isolated renderer regression. Even the separate draw/skip averages still cover
unmatched game states and GC/audio activity.

The runtime step consumed 79.40%/78.92% of observed wall time. Outer audio
consumed 16.47%/16.76%, and presentation 3.33%/3.35%. Mid-frame audio and GC are
already inside the runtime step. These are measured-region contributions, not
independent recoverable speedups. Audio time per frame is also affected by loop
rate; reports do not contain audio-pair counts for normalization.

The candidate's runtime-step maximum was 171.955 ms versus 87.925 ms baseline;
presentation maxima remained 3.187/3.048 ms. This narrows the large reported
spike to the broad runtime region rather than a comparable final-presentation
spike. Aggregated maxima lack frame identities, so do not pair or sum them.
The reports cannot distinguish update, draw, GC, mid-frame audio, cache effects
or route-dependent work as the cause.

## Validation and persistence

Both files have the expected 262144-byte size, one complete BEGIN/END record and
NUL padding. Counts, totals, rounded means and derived FPS are internally
consistent. Build IDs match the exact packaged source revisions:

- Baseline `b59770e65f81132bc2642507881f44020467acc5`.
- Candidate `d67bd15986c0b381bc264154f227e4aed985d8b0`.

Both identify the same cart content, pinned 90 MHz os20 runtime, profile hook off,
volume 100/unmuted, scale 2, controls, two-second warmup and 30-second requested
window. Neither is truncated. Both report a bound file, slot 8 at entry 8 with
initial size 0, and HW flags `0x8103e35b` (including feature bit 24). The actual
reported bit is preferable to prior assumptions about which size-commit
capability the fitted image contains. It is not an independent bitstream hash.

Receiving the two valid files establishes that the new package produced reports
that could be retrieved for these runs. It does not isolate which declaration
change repaired the initial missing-file behavior; no retrospective root cause
or synchronous SD-flush claim is made.

Exact user-supplied bytes, SHA-256 hashes, parsed fields, arithmetic checks and
derived comparisons are preserved privately in
`experiments/pico8-device/trailhead-20261018-r1/analysis.json` with both `.bench`
files. No game assets are included in tracked evidence.

## Decision

This pair favors the accepted baseline for Trailhead and gives no reason to
promote the palette candidate. It agrees in direction with the retained
simulated Trailhead regression, but its percentage is not a simulation
calibration or controlled confirmation. The input differs, the scheduler mixes
draw/skip work differently, and one pair supplies no repeat-run uncertainty.

For confirmation, take three captures per build while standing at the same
Trailhead position, keeping audio/settings the same, then repeat at a fixed
Moss Moss position. Keep the scene order the same in both journals and alternate
builds when practical. Use repeat means and tail behavior before deciding whether
any gain in Moss compensates for a Trailhead regression.
