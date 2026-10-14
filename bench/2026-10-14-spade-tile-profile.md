# Spade tile profiling and rejected classifier trials

This follows the [main 8d3cb19 comparison](main-8d3cb19-spades-results.md)
and the user's subsequent Pocket base/sharp reports. The experiment uses the
same recreated room 43, solo Kris, seed 7 and frames 490–492. It does not import
the player's save or measure all later Dark World areas.

## Device evidence

The supplied log has one independent base/sharp pair; the repeated base block
is byte-identical, not replication. Both are Speed on OS 0.9.0, variant 0,
100 MHz, with Script times and detailed draw timings off.

| Device window | Base work ms/frame | Sharp work ms/frame |
| --- | ---: | ---: |
| Frames 490–492 | 173.3 | 173.6 |
| Frames 493–519 | 176.2 | 176.4 |

These differences do not establish a sharpening regression or gain. The longer
base window spends 123.2 ms in the draw phase, 46.1 ms in step and 5.9 ms in
sound. The draw phase includes draw-event scripts as well as rasterization.
About 243 sprite-part/tile calls occur per frame. Zero detail columns mean
instrumentation is disabled. Steady slow frames show no asset reads.

## Passive profile

The exact successful sharp timing case at `3d07523` was observed without firmware
changes. Observer-on and observer-off replay reproduce the original frame cycles
and all oracles exactly; the corrupted-state control is rejected. CPU parameters
are unchanged. The three frames retire 26,284,803 native instructions, including:

| Function | Retired instructions over three frames |
| --- | ---: |
| swrRunClassify | 4,438,601 |
| memcpy | 4,051,216 |
| swrDrawHLineInt.part.0 | 3,518,910 |
| Runner_findLayerElementById | 2,966,400 |
| executeLoop | 2,598,213 |

The horizontal fill function also records 6,465,699 dispatch-blocked cycles with
uncached-I/O freeze asserted. These overlapping counters are observations, not
additive wall-time attribution or predicted recoverable speedup.

A separate desktop diagnostic of the real device benchmark route logs one new
240-tile picture every frame from 480–495. Keys and vertical bounds change;
pictures are 300 pixels wide and roughly 760–774 high at half size. This confirms
repeated construction/classification rather than successful cache reuse in that
route. The diagnostic has been removed from production sources.

## Trials

First, deferred cache admission avoided creating a picture until its contents
repeated. An asset-free pixel fixture rejected this approach: direct half-size
drawing and cached composition can differ for partial coverage. This throwaway
trial was not committed or built for the device.

Two exact classifier variants then passed output checks but lost performance:

| Revision / implementation | Simulated ms/frame | Versus control |
| --- | ---: | ---: |
| 3d07523, original classifier | 168.719947 | — |
| f2c9c91, stop at first mixed texel | 180.627823 | +7.0578% |
| 62ae79e, check for mixture after each row | 172.235860 | +2.0839% |

GCC 16.2.0, native scripts, BRAM interpreter, 64-byte alignment, Speed,
uncached framebuffer, 1,680-cycle clock charge, fixed audio and quiet traffic
match the prior control. These are three-frame **simulated** means at 100 MHz,
not physical Pocket results. Both candidates have repeated QEMU capture and
positive same-ELF RTL evidence. The first also has a separate traced case.
Cross-revision and first-candidate traced/timing pixels, PCM and pair counts
agree; 48 direct raw channel comparisons agree across both repeats.

The classifier fixture checks 1,960 pictures with empty, solid, mixed and partial
edge blocks under ASan/UBSan for both games. Independent review additionally
checks 38,025 cases in each of four opacity configurations. A C++ goto-scope
issue in the row trial was found during review; neither trial is being retained,
and the production renderer has been restored byte-for-byte to `3d07523`.

The macOS linked ASan fixture initially stalled in SDL's startup error dialog,
before main. The classifier fixture was rerun without the unused SDL library,
using `PC_SDL_LIBS=` and `-Wl,-dead_strip`, and passed. Interrupted clipping
fixtures are not counted as successful tests.

## Disposition and evidence

Keep the classifier fixture, discard the production trials, and leave the
published Pocket overlay untouched. No slower candidate is handed to the user.
A possible next design is to determine when a moving tile run can reuse picture
contents independently of its position. Its clipping, coverage and cache
invalidation behavior need explicit characterization before implementation.
This is a proposal, not a measured optimization.

Private evidence is under `build/spades-tile-classify-r1/` and
`build/spades-tile-classify-r2/`. The latter contains selected case paths,
validated report, comparison JSON, raw-byte checks, observer provenance and
independent sanitizer review artifacts. Original passive observer results remain
under `experiments/cache-profiles/`. Rejected snapshots and cases are preserved.

The Undertale control exposed a harness asset-layout bug before compilation:
renamed port sources expect `games/undertale/data.win`, while the frozen assets
are at `data.win`. The adapter now prefers the modern path, supports the older
Undertale path, passes the resolved directory to the flags-only Make invocation,
and refuses absent Deltarune data. Ten adapter tests, a real frozen Undertale
Makefile flags check and verification of the original 1,631 inputs pass. No
Undertale full-frame comparison is claimed for these rejected trials.
