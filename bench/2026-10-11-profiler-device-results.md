# Rebased profiler Pocket result, 2026-10-11

The uploaded Deltarune save contains the labeled Speed reports from the
[rebased base/profiler card](2026-10-10-profiler-rebase-results.md). Both identify
OS 0.7.0, core variant 0 and CPU 100 MHz. The card uses baseline e484ccc and
candidate 86140c1, based on main 308c17c, with Script times compiled in and
disabled by default. This is the feature-preserving change, separate from the
older profiler compile-out experiment.

## Device measurements

The table uses reported work time, excluding display flip. These are rounded
scene means over the device route, not the harness's three-frame samples.

| Scene | Base ms/frame | Profiler ms/frame | Change |
| --- | ---: | ---: | ---: |
| Opening text | 27.6 | 27.3 | -1.09% |
| Creation screens | 67.4 | 66.8 | -0.89% |
| Town yard | 27.4 | 27.3 | -0.36% |
| Field | 43.8 | 43.4 | -0.91% |
| Battle menu/attack | 67.4 | 66.7 | -1.04% |
| Battle dodging | 78.3 | 77.6 | -0.89% |
| Battle next turn | 63.3 | 62.6 | -1.11% |

The complete 3,600-frame route drops from 148.2 to 146.9 seconds: 1.3 seconds
saved, or 0.88% less elapsed time. Total frame times also improve in every scene;
dodge total changes from 78.8 to 78.1 ms. Load to first frame is 11.6/11.5 seconds.

The draw-call counts match in every scene at the report's precision. The direct
sprite probe is unchanged: whole draw 60.48/60.48 microseconds, texture lookup
2.66/2.66, and outside-view draw 5.09/5.10. Clock reads are 16.83 in both reports.
This is consistent with a VM-path improvement rather than a sprite-call saving.

Audio output is scheduled in real time on the device. Reported stereo pairs per
frame decrease by roughly 0.5–1.0% in the candidate, including dodge 3,780/3,746.
Audio costs do not uniformly decrease: dodge mix is 7.3/7.4 ms, while battle
menu mix is 10.3/9.8. These are coupled workload/scheduling differences, so the
whole-route gain does not isolate the removed profiler loads and calls.

## Interpretation and next measurement

All seven scene means improve. This supports keeping the optimization while
retaining Script times in Debug. The device dodge work improvement is 0.89%,
versus the rebased harness's simulated 0.30%. The harness validates matching
pixels/PCM/counts with fixed audio and substituted services; its three cold-cache
frames are not equivalent to the device scene mean. Do not apply a scaling factor.

There is one independent base report and one candidate report. The two base
occurrences in the save are byte-identical report copies, not repeat measurements.
This pair is encouraging but cannot establish run-to-run variance or the exact
repeatable gain. No Script times enable/disable marker appears in the log;
disabled state is inferred from the prepared default-off benchmark entries.
Report labels associate the runs with the card build, but are not independent
hashes of the loaded ELFs. The save does not supply a device output oracle.

The next useful device pair is Deltarune Benchmark accuracy base, followed by
Deltarune Benchmark accuracy profiler, with Script times off. The rebased harness
only predicts a 0.08% Accuracy gain, so a substantial gain there remains unproven.
This analysis makes no change to the ready-to-copy card tree.

## Evidence

Input: f0fbbc61-102b-4676-bfa4-b80f8b896f40/deltarune_1.sav, 119,324 bytes.

Input SHA-256: e62919660e14a28c4031b505ce2505de2c6994debf19d22eed1493a1d5cadd86.

Removing NUL bytes exposes labeled base reports at lines 371 and 1129, and the
candidate at line 1884. The older unlabeled/texture reports are excluded.
The report blocks, including their title and end marker, hash to:

- Base: 04013828b5923e3c495007cc45ed5c25438ea8d4cc15eb80d8fed81bfd336f52.
- Candidate: 9145db3087f6d781df00201f43f99f1d84c61a7c753fbe95289ee3c470ab4201.

Private build/profiler-device-308/reports.txt retains the unique report blocks;
comparison.json records the input hash, occurrence lines, report hashes and
unrounded arithmetic on the reported rounded means. Game logs remain ignored.
