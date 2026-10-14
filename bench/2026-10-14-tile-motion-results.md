# Reusing translated tile pictures

This follows the [spade tile profile](2026-10-14-spade-tile-profile.md).
The measured chase contains a 240-tile run whose appearance and relative layout
remain unchanged while every tile moves by (0, -20) room pixels per frame.
The desktop diagnostic checks all 3,600 tile transitions over frames 480–495.
The old absolute-position key rebuilt the whole picture on every frame.

## Source and implementation

- Dedicated port branch: `experiment/spade-tile-cache`.
- Base: `a7157b6703b67d8e657550da3ac4e628d863b316`; its production renderer is
  identical to `3d07523` and retains the original classifier.
- Harness candidate: `f24a52fcc6f02194da1e5ef4ec18d320295a19d4`.
- Device candidate: `6373a843193e7bcaa09c999a04a98c02a5c62cd1`; only the
  benchmark label/check was added after the harness source revision. The
  renderer file is byte-identical to the harness candidate.

The content key retains tile order, source rectangles, tint, dimensions and
relative effective positions, including fractional phase. The existing scale,
blend and half-size even/integer eligibility checks remain. Cached storage is
immutable; each queued draw receives its own position metadata. The compositor
checks up to four storage blocks for a translated destination block and clips
all four source edges. Flattened composites include placements in their keys.
No classifier shortcut or direct-drawing admission experiment was retained.

The pressure regression exposed an existing hazard: below-grid replay hides the
pending queue while sprite loads may request texture eviction. A reader guard
now prevents freeing picture storage while composition/grid replay uses it.
Forced eviction reproduced an ASan heap-use-after-free before that guard and
passes afterward; eviction succeeds again after replay finishes.

## Simulated results

Fresh independent base/candidate cases use GCC 16.2.0, production port flags,
native scripts, BRAM interpreter, 64-byte alignment, uncached framebuffer,
1,680-cycle clock charge, fixed audio and quiet traffic. These are three-frame
complete-loop timing means, **simulated at 100 MHz**.

| Window | Mode | Base ms/frame | Reuse ms/frame | Change |
| --- | --- | ---: | ---: | ---: |
| Deltarune spades, 490–492 | Speed | 171.031710 | 120.094703 | -29.7822% |
| Deltarune spades, 490–492 | Accuracy | 482.658940 | 273.900720 | -43.2517% |
| Deltarune Castle Front, 150–152 | Speed | 24.670783 | 25.093257 | +1.7124% |
| Undertale Flowey, 2400–2402 | Speed | 17.869660 | 17.875983 | +0.0354% |

The gain is concentrated in the moving chase. Castle Front adds 0.422474 ms
in this sample; Undertale is effectively unchanged. These results do not
establish physical Pocket speedups. Use the fresh within-pair controls rather
than comparing absolute means across earlier separately built cases.

Spades and Castle Front retain the documented controlled setup: seed 7,
room jumps at frame 30 after setup at 29; solo Kris in room 43 for spades,
Kris/Susie in room 46 at the castle. They are recreations, not imported saves.
Post-timing guards check room, requested mode, visible spades where required,
inactive battle sampling, disabled draw diagnostics and a null script profiler.
Undertale uses the existing Flowey route and its recorded instrumentation.

## Verification

All 16 cases (two revisions × four windows/modes × traced/timing) pass repeated
QEMU capture and same-ELF RTL output/state checks. All 16 corrupted-state
oracles are rejected. All 16 cross-revision/traced-timing comparisons agree on
pixels, PCM and pair counts; 192 direct raw channel comparisons across both
repeats agree. Pointer-bearing state is checked only within the same ELF.
The validated report records exact source/ELF/flags/checkpoint/result hashes.

For each game, ASan/UBSan fixtures pass 368 translated-picture frames,
1,960 classifier pictures, 499 sprite clipping cases, 149 font sampling cases
and 1,260 battle contrast cases. The movement fixture covers solid/empty/mixed
images, all placement phases, negative views, nonzero ports, held clears,
duplicate placements, queue-capacity flush, fractional/layer offsets,
source/order/content invalidation, independently moving flat layers, and
forced eviction during below/above grid replay. Against the original renderer,
the final fixture rejects 40 disposable allocations where reuse requires one.
Both games pass strict port lint; the benchmark label/window/wrong-room fixture
passes under sanitizers.

Two complete 519-frame desktop runs of the device benchmark route retain
seeded earlier reports and leave a normal-save sentinel unchanged. The macOS
SDL compatibility loader needs `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`
for these ASan binaries. A separate C++98 syntax comparison encounters the same
two existing `safeCalloc` conversion errors in base/candidate; no passing full
C++98 build is claimed.

The original 1,631 frozen inputs still verify, and the ten adapter tests pass.
Independent static review found no remaining actionable issue after the
fixture-proven eviction guard and expanded coverage were added.

## Evidence and limitations

Private evidence: `build/tile-motion-r1/` contains `results.json`, all case paths,
per-build and negative logs, the diagnostic summary, comparison JSON and direct
raw-byte checks. Port sanitizer/desktop-route logs remain at
`butterscotch-spade-tile-cache/src/openfpga/out/tile-motion/`.

The harness retains its substituted allocator, OS/file/clock/audio services,
three-frame cold RTL cache window and frozen 128-pixel standalone texture packs.
The Pocket uses embedded 64-pixel packs and real SD, interrupts, display and
live audio scheduling. No universal calibration factor or physical FPS claim
is made. Device comparison is the next validation step.

## Pocket build and protocol

After the full harness report passed, all three device ELFs built successfully
at entry `0x10400000`. Base was exported independently from `a7157b6`; reuse
and ordinary play use `6373a84`. Their exact flags and SHA-256 hashes are in
`butterscotch-spade-tile-cache/src/openfpga/out/tile-motion-device-6373a84/manifest.json`.
The build gate verifies the completed 16-case report, all raw comparisons and
renderer equality to `f24a52f` before invoking any device build.

The overlay at that directory's `overlay/` contains nine files and adds:

- `Deltarune Spades tile base`: automatic fresh/volatile Speed chase benchmark.
- `Deltarune Spades tile reuse`: the same benchmark with picture reuse.
- `Deltarune tile reuse`: ordinary play using the normal save.

The benchmark pair measures frames 490–492 and 493–519 and halts automatically.
Run base then reuse, exiting through the Analogue menu after each to flush the
appended `Saves/butterscotch/common/deltarune_1.sav`. Script times starts off;
no manual toggle is needed. The ordinary-play entry does not run the benchmark.

All three overlay instance/config/program bindings pass. A separately copied
full card plus overlay passes all nine instance bindings. All nine overlay
hashes verify; the six previously delivered overlay files remain unchanged.
The bundle contains no runtime, core, game-data or save replacement. Nothing
was copied to the SD card, pushed or published. The new overlay is ready for
copying and will be left unchanged during the user's transfer.
