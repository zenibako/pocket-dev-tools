# Rendering costs on the accepted audio build — 2026-10-16

Follow-up: [the complete-tile experiments](TILE-FULL-OS20.md) improve Celeste
but retain small Moss regressions; neither candidate is promoted.

The next shared experiment should specialize the existing **fully visible 8×8
tile blitter**, preserving both default and remapped palettes. Celeste spends
1.69–2.08 ms/frame inside the observed `spr` bodies; Moss spends about 1.02 ms
inside `map`, which uses the same blitter. Every visible tile in these four
windows is a complete, unclipped 8×8 tile. These are measured API intervals,
not the tile kernel's self time or a promise of recoverable savings.

This study measures and selects an experiment. It makes no runtime optimization,
package, deployment or performance-improvement claim. The accepted audio source
and production package remain unchanged. Earlier VM experiments are recorded in
[the call study](EMPTY-LUA-CALL-OS20.md); this follows the rendering opportunity
identified in [the Celeste study](CELESTE2-OS20.md).

## Observed API costs

Numbers below are **inclusive diagnostic C API body ms/frame** on simulated
os20 at 90 MHz, averaged across 12 frames. They include argument conversion,
state synchronization, helpers and some observer overhead. They exclude Lua
dispatch into the C API, its prologue before the first timer read, and cleanup
after the second read. A zero means no calls in this window.

| API | Celeste tower | Celeste Trailhead | Moss steady | Moss GC window |
|---|---:|---:|---:|---:|
| `spr` | 2.080 | 1.692 | 0.044 | 0.070 |
| `map` | 0 | 0 | 1.027 | 1.022 |
| `circfill` | 1.767 | 0.872 | 0.097 | 0.068 |
| `rectfill` | 1.141 | 0.028 | 0.097 | 0.090 |
| `rect` | 0 | 0 | 0.322 | 0.321 |
| `pset` | 0 | 0 | 0.322 | 0.422 |
| `print` | 0 | 0 | 0.219 | 0.218 |
| `cls` | 0.098 | 0.131 | 0.075 | 0.070 |

With diagnostic scanout traffic, `spr` is 2.084/1.697 ms in Celeste and `map`
is 1.030/1.033 ms in Moss. The leading API choice remains the same.
[The CSV](RENDER-COSTS-OS20.csv) retains all 25 measured APIs plus the empty
probe, call counts, mean cycles, maximum frame interval, scanout means, source
revision and case/ELF hashes. Read/state API costs remain separate from drawing:
for example, tower `peek`, `fget`, `pal` and `palt` cost 0.359, 0.311, 0.286
and 0.218 ms/frame respectively.

For context, previously accepted **uninstrumented** audio-build frame means
are 27.160, 42.322, 48.288 and 48.667 ms in this order. This study's diagnostic
frame means are 28.036, 44.313, 49.160 and 49.528 ms; with scanout they are
28.092, 44.435, 49.905 and 50.274 ms. Do not subtract scope intervals from the
accepted frame times or treat the difference between these builds as pure
observer cost. Runtime compiler policy and layout also differ. No new physical
Pocket FPS was measured.

The drawing API intervals sum to 5.087/2.723 ms in Celeste and 2.230/2.307 ms
in Moss. Rendering kernels alone therefore do not explain the entire frame.
The remaining diagnostic time includes Lua work, C-call machinery, audio,
unscoped APIs and observer work outside sampled intervals; it is not a measured
interpreter-only remainder. These scopes are not update/draw phase attribution.

## Why the tile path is the shared target

A separate native path census preserves all 600 output rows in each scene.
It counts executed paths without per-pixel counters; geometry counts are not
actual stores, opacity classification or cycle costs.

| Window | Visible full tiles/frame | Palette | Transparency |
|---|---:|---|---|
| Tower | 203 | Default | Default |
| Trailhead | 138 | Default | Default |
| Moss steady | 45 | Remapped | Default |
| Moss GC | 45.917 | Remapped | Default |

There are no visible partial tiles or odd source-start rows in these samples.
Celeste's general flipped sprite calls in these windows are rejected by clipping;
Moss also has one visible flipped sprite per frame. Those use another path and
must retain their existing behavior.

The current tile loop repeats generic clipping-width, odd-pixel, pair-loop and
palette/transparency handling. A bounded experiment can specialize complete
8×8 rows and move invariant color-mode decisions outside the pixel-pair loop,
while retaining the generic clipped path. Supporting only default colors would
miss Moss's measured tile workload. Keep transparent source pixels and remapped
colors correct; do not assume that default transparency means every pixel is
opaque. Relevant accepted source anchors are `src/runtime/runtime.cpp`:
`draw_sprite` at 696, `blit_tile` at 1360 and `api_map` at 1426.

The benefit must be established with fresh, matched, uninstrumented baseline
and candidate cases for both games under the same runtime compiler policy,
followed by a fitting production build. The accepted production ELF has only
154 BRAM bytes free: duplicating the entire blitter could erase the gain or
fail the fit. Code size, instruction layout and cache behavior remain important
trade-offs, as the prior VM experiments demonstrated. This study does not yet
quantify the tile kernel's fraction of `spr`/`map` time.

Patterned fills remain a useful Celeste-specific follow-up. Only the tower
executes the patterned span helper here: 15,063 rows over 12 frames, of which
14,302 (94.95%) are 8–31 pixels wide; 6,144 rows have no retained pixels and
8,919 have mixed keep masks. Trailhead and both Moss windows execute none.
Moss's solid spans are mostly 1–3 pixels wide (87.9%/88.9%), so a wide word-fill
experiment has less shared path coverage. Its many `pset` calls and 32 `rect`
calls/frame are measurable, but individually smaller targets than `map`.

## Compiler control and timing limits

Both current production and benchmark images use GCC 13.2. The original harness
compiles runtime.cpp with `-ffreestanding`; current production compilation does
not. This suppresses builtin lowering in the harness and produces out-of-line
four-byte `memcpy` calls that do not exist in production. The earlier Celeste
report's GCC13/GCC16 observation describes its historical comparison, not these
current builds.

A private compile-only control changes just runtime.cpp's compilation policy,
reusing the other 37 target objects and the original link command. Removing
`-ffreestanding` eliminates all 14 previously inspected renderer/screen-sync
`memcpy` callsites. This is a code-generation result, not an optimization gain.
Production inline four-byte copies can still lower to byte loads/stores.

All four timing diagnostics explicitly use that runtime-only builtin policy;
the other translation units and link retain their original flags. This is
recorded in each immutable build's `runtime_flags` and
`renderer_compile_mode=production-builtins-runtime-only`. An independent audit
compares actual machine-code bytes with the accepted production ELF:

| Uninstrumented helper | Bytes | Equal in all four diagnostic ELFs |
|---|---:|---|
| `blit_tile` | 522 | Yes |
| `draw_hspan_pattern` | 714 | Yes |
| `draw_rect_pattern` | 1690 | Yes |
| `screen_to_ram` clone | 150 | Yes |

The observed API wrappers themselves differ from production, and helper byte
equality does not establish full layout, allocator, hardware-service or timing
parity. No sampled helper has an out-of-line `memcpy` call.

RAII scopes wrap 25 public API bodies, without per-pixel/span timer reads. A
32-bit unsigned difference handles timer wrap; 64-bit accumulators collect the
intervals. Native and QEMU clocks return zero. Only RTL reads the validated
90 MHz MMIO timer. Per-frame depth/nesting checks rule out double-counted API
intervals in accepted logs. Eight empty scopes run outside the frame timer;
their per-frame average costs range from 28.875 to 35.375 cycles/call across
the quiet cases. Different code/cache/register context prevents subtracting
that calibration as an exact universal overhead. Probe output can also affect
cache state before subsequent frames. Reported API costs are uncorrected.

## Reproduction and validation

Accepted source is signed `9f4cd16f6d3d730b8edaab1102387c6958df5536`, the rebased
audio-pair candidate. The historical accepted cases record pre-rebase `9edffde`;
their prepared source differs from these diagnostic cases only in the explicitly
instrumented runtime.cpp. Source-file key sets and all other source hashes match.
The accepted production ELF remains
`c4af75204fe7f59633fbefc63091cebf95732acbe6ee320482404b7ff3ec2dd6`.

Private launcher `experiments/pico8-sources/render-costs-20261016-r1/study.py`
derives runtime/runner/header/build changes before snapshot inventory. Cases are
`experiments/pico8/render-costs-os20-{intro2,trailhead,moss-steady,moss-gc}-20261016-r1`.
They retain hash seed `0x5eed1234`, the original routes and cart inventories.
Celeste measures stationary recreated scenes over frames 100–111; Moss retains
seed-7 scripted input, frames 180–191 and 234–245. These are narrow windows,
not whole-game averages. Every diagnostic ELF fits at 14,040/14,336 BRAM bytes.

All four cases pass:

- Two matching 600-frame native transcripts and byte-identical raw pixels,
  palette and stereo PCM against the accepted cases. Each raw collector's 600
  `PICOFRAME` rows also matches its ordinary runner.
- Two matching QEMU captures/checkpoints/stacks and output equality with the
  accepted cases; prepared program/stack/firmware hashes remain valid.
- Quiet and scanout RTL output replay, all SDRAM/read/write/scanout memory
  checks, plus the deliberate output-oracle failure with exit code 2.
- Strict sparse scope completeness, probe counts, zero native/QEMU times,
  no nested/unbalanced scopes, and matching API call counts across native,
  both QEMU runs, both RTL modes and the separate path census.
- Fresh immutable case/binary inventories, log hashes, 1,631 frozen-input
  hashes and os20 platform hashes. Independent source/codegen and exporter
  reviews accompany the private evidence.

The timer fixture checks wrap, nesting and early-return cleanup. Removing the
unsigned wrap cast makes its retained mutant fail. The parser rejects seven
malformed/missing record fixtures and nonzero QEMU timing. `summarize.py`
freshly validates evidence before writing the CSV and private `summary.json`.

The companion private directories `render-path-census-20261016-r1` and
`render-compiler-control-20261016-r1` retain counter definitions, derived source,
compiler argument arrays, object/ELF hashes and disassemblies. Raw carts,
checkpoints and generated binaries remain private and ignored.

Final private evidence manifest covers 961 files. SHA-256:
`c9e4158b54053ab2cbed3c3e30e267f1f984b0222674f2cf6e1764cf598afcd2`.
