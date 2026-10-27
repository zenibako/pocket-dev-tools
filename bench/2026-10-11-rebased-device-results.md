# Rebased Deltarune device reports, 2026-10-11

The new save follows the Pocket build of experiment revision
0f7fb40014c1f9695bd0959fdb495eba91c08734, rebased onto main d157e5b.
The prepared card has fresh Speed/Accuracy rebased entries for both games and
keeps Script times in Debug, off by default. The first save contains Speed
reports; the subsequent Accuracy result is recorded below. Association with
that build comes from this session; the reports contain
no revision label or independent loaded-ELF hash. The previous report's build
is unknown and is an observational comparison, not a controlled baseline.

## Latest result

Both reports identify OS 0.7.0, core variant 0 and CPU 100 MHz. Compare the last
independent earlier report (143.9 seconds) with the final report (141.8 seconds).
The elapsed route saves 2.1 seconds, or 1.46%, over 3,600 frames. Load to first
frame changes from 11.6 to 11.4 seconds. Work excludes display flip.

| Scene | Previous work ms/frame | Latest work ms/frame | Change |
| --- | ---: | ---: | ---: |
| Opening text | 27.5 | 27.4 | -0.36% |
| Creation screens | 66.4 | 66.1 | -0.45% |
| Town yard | 26.5 | 25.9 | -2.26% |
| Field | 42.4 | 41.2 | -2.83% |
| Battle menu/attack | 60.7 | 58.7 | -3.29% |
| Battle dodging | 70.9 | 71.2 | +0.42% |
| Battle next turn | 61.9 | 58.3 | -5.82% |

Six scene means improve; dodge is 0.3 ms slower. Its total time also changes
from 71.4 to 71.7 ms. The battle workload differs: dodge has 46 sprites and
10 text calls per frame instead of 45/8; next turn has 52 sprites, 22 text and
19 rectangle calls instead of 55/23/17. The earlier scenes' rounded draw counts
match. These differences and real-time audio prevent assigning the route or
battle changes entirely to optimization. Next-turn audio pairs decrease from
3,002 to 2,825, with mix time 13.1/11.7 ms; dodge pairs are 3,432/3,446.

## Texture reads and direct probe

The final boot log confirms 8 pages in 7,169 tiles of 64, embedded in music.bin
at 43,832 KB, and direct reads of up to 64 KB. The benchmark reaches its normal
halt, without a texture-read timeout message in this run. This adds device
execution evidence for the 64-pixel embedded format beyond the
[combined main harness comparison](2026-10-11-combined-main-results.md), which
used frozen standalone 128-pixel packs and substituted file services.
It does not validate every DMA error/recovery case or establish an output oracle.

| Four-KB read probe | Previous ms | Latest ms |
| --- | ---: | ---: |
| Texture after texture | 4.6 | 4.6 |
| Texture after music | 12.6 | 4.6 |
| Music after texture | 4.7 | 4.9 |
| Music after music | 4.8 | 5.5 |
| Texture after idle | 4.9 | 3.9 |
| Texture after data.win | 40.4 | 20.3 |

The previous retained boot log also uses the embedded 64-pixel format, so the
probe change cannot be attributed simply to introducing that format. General
SD throughput is similar: staged 1-MB reads are 1,507/1,514 KB/s, copied reads
1,297/1,291 KB/s. One probe pair does not establish repeatability or mechanism.

The sprite probe shows no outside-view improvement: 5.11/5.50 microseconds.
Whole draw is 62.74/62.36, texture lookup 2.68/2.67, and clock reads 16.79/16.79.
This report provides no evidence of an outside-view sprite-call saving.
This is not a profiler-only comparison; that optimization is already merged.

The next requested device measurement was Deltarune Benchmark accuracy rebased,
with Script times left off; its result is below. A repeat Speed run would help establish workload
and read-probe variation, but the older report cannot identify an exact control
without additional build provenance. No rebuild or SD copy accompanied analysis.

## Provenance

Input: 9e9a21f8-70ea-4484-ae9c-492855ed6504/deltarune_1.sav, 116,831 bytes.

Input SHA-256:
c212da2e91f8defcf988f86127f345da55f89595b4a1a9dbda51363a85a2db25.

After stripping NUL bytes, seven report occurrences contain six distinct blocks.
The previous report at lines 380 and 1111 is an exact retained copy, counted
once. The latest report begins at line 1824. Block hashes, title through end
marker excluding its trailing newline:

- Previous: 7b7eca22327ba284a2f69b17edf342e89efae3cecfd34e965114e92e48c128e9.
- Latest: 6915a11e05b26dec4bf6e35bcc70050b0f9e7352b7bbfc7d712ea6ca2ae2f0cd.

Private build/rebased-device-0f7fb40/ contains the deduplicated report blocks
and comparison.json with input/block hashes, line numbers, seven scene means,
draw counts and arithmetic. The prepared card's independent file hashes remain
in the game checkout's out/device-0f7fb40/card-manifest.json. At this upload,
Accuracy and Undertale device measurements were absent.

## Accuracy follow-up

The next save adds one independent Accuracy report at line 2179. Its Speed
reports are exact retained copies, including the 141.8-second report at lines
238 and 1019. They provide no new Speed measurements. Core, OS and clock match,
and the Accuracy run reaches its normal halt using the embedded 64-pixel pack
and direct texture reads, without a texture timeout message.

The earlier Accuracy reference is the labeled UT_PROFILER_FAST308 build
(86140c1 based on main 308c17c), recorded in the
[profiler device comparison](2026-10-11-profiler-device-results.md).
This comparison includes all subsequent merged renderer and texture-I/O changes;
it is not a profiler-only or immediate-pre-rebase control. Both builds retain
Script times, off by default.

| Accuracy scene | Earlier work ms/frame | Rebased work ms/frame | Change |
| --- | ---: | ---: | ---: |
| Opening text | 36.2 | 36.4 | +0.55% |
| Creation screens | 132.1 | 131.4 | -0.53% |
| Town yard | 28.3 | 26.9 | -4.95% |
| Field | 85.8 | 82.4 | -3.96% |
| Battle menu/attack | 124.9 | 104.3 | -16.49% |
| Battle dodging | 171.3 | 142.1 | -17.05% |
| Battle next turn | 118.2 | 105.6 | -10.66% |

The route drops from 245.1 to 231.9 seconds: 13.2 seconds saved, or 5.39% less
elapsed time. Load to first frame is 11.7 seconds in both. Unlike the latest
Speed comparison, all seven scenes' rounded sprite/tile/text/background/rectangle
call counts match. This is stronger workload agreement, but aggregate counts
are not a pixel/PCM oracle and one pair cannot establish variance.

Most dodge savings appear in drawing: 144.1/116.9 ms, versus step 18.0/17.5.
Reported rectangle time is 20.7/8.2 and sprite time 87.8/78.3 ms. The older
costly translucent rectangle/held-clear rows disappear from the top draw table.
This supports a drawing-path gain without isolating individual commits or
providing disjoint attribution. Real-time audio is coupled: dodge stereo pairs
fall from 8,161 to 6,854, with mix 14.6/12.3 ms.

The read probe is consistent with the latest Speed run: texture after music
4.6 ms, texture after data.win 22.0 ms. The direct sprite probe does not improve
against the older report: whole draw 110.12/113.19 microseconds, outside-view
5.09/5.50, texture lookup 2.66/2.68. The frame gains do not imply a faster direct
40x40 call. Outside-view cost matches the current Speed run at 5.50 microseconds.

Both rebased Deltarune modes have completed on device. Undertale device coverage
and repeatability remain unmeasured. The card tree was left untouched.

Accuracy input: b5b246b4-77ae-43f6-b871-e192d410350b/deltarune_1.sav,
131,783 bytes, SHA-256
44ea07af8d07ce9647a1a8b2158de69bc5e660be7d157030f6fa792699559ae3.

Latest Accuracy block SHA-256:
9819bd199f72cd4aeecdaa67efc1e291c10ca5c935f93c055c2f494cff1d1e4d.

Earlier FAST308 block SHA-256:
8dbc66633b8fb2eccfa7b3ca248b06e98d935f8134f1deabded99a56ee78cf3c.

Private build/rebased-device-0f7fb40/accuracy/ contains both blocks and
comparison.json with arithmetic, call counts, timing breakdowns, hashes and
the verified retained-Speed identities.
