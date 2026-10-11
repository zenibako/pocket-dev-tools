# Combined main comparison, 2026-10-11

This follows the [profiler comparison](2026-10-10-profiler-rebase-results.md)
after its merge and the texture-I/O changes. Baseline is
6100fcc11c9ad81bff70173d854393df40a1deb3; combined main is
dd28a6e39085e1973f0cac78056be2c024f540e7. Both retain
ENABLE_VM_GML_PROFILER and the Script times debug option.

## Timing and correctness

Twelve cases use GCC 16.2.0, port profile, native scripts enabled, 64-byte
function/loop alignment, BRAM interpreter, uncached framebuffer, 1,680-cycle
clock-read charge, fixed 800 stereo pairs/frame and quiet memory traffic.
Each checkpoint starts with cold caches and runs three consecutive frames:
Undertale Flowey 2400–2402 and Deltarune dodge 3323–3325. Timing builds omit
VM tracing and in-loop PCM hashing; traced builds validate those fields.
Script profiling remains compiled into both kinds.

| Timing sample | Base ms/frame | Main ms/frame | Change |
| --- | ---: | ---: | ---: |
| Undertale Flowey Speed | 15.934430 | 15.921637 | -0.080% |
| Deltarune dodge Speed | 79.967220 | 78.358390 | -2.012% |
| Deltarune dodge Accuracy | 161.263437 | 159.512423 | -1.086% |

These are simulated milliseconds at the pinned 100 MHz os25 clock. All nine
timing frames improve individually. The Deltarune means save 1.609 ms in Speed
and 1.751 ms in Accuracy. This is a combined revision comparison; it does not
isolate the profiler, texture reader, compiler layout or substituted file service.
The traced Accuracy mean is effectively flat (170.104410/170.115220 ms), so
traced instrumentation cannot supply the performance estimate.

All twelve cases pass repeated QEMU capture agreement, same-binary RTL output
and memory checks, and corrupted-state negative controls. Six base/main and
six trace/timing comparisons match raw RGB555 pixels, stereo PCM and pair
counts: 36 frame pairs. All nine paired traced opcode/event counts match.
The validating report was regenerated after the user-run matrix, rechecking
source, input, ELF, capture, simulator and positive/negative log hashes.
The original 1,631 frozen input hashes also pass fresh verification.

## Harness adapter and storage coverage

The first main case failed to link because the existing adapter did not define
platformPackRead, platformPackRefusedNanos or utPlatformReadCosts. Its failed
case and the six successful baseline cases are preserved.

The active case templates come from bench/, copied over fullframe/ by
experiments.py. bench/platform.c now defines the three hooks when
PLATFORM_PACK_READ is enabled. Pack reads use the existing wrapped fopen,
seek and exact-size fread service; refusal time and the physical read-cost
probe return zero. All six successful main cases contain byte-identical copies
of this adapter. Old baseline cases use their preserved adapter.

The main renderer/read-window code runs against the harness file service.
Production of_pack_read.c DMA allocation, asynchronous completion, host refusal,
timeouts and fallback sequencing are not exercised. File-service latency is
substituted, so this does not establish Pocket SD-read improvements.

Base/main data.win, textures.bin, music.bin and the additional Deltarune audio
and language files have identical hashes. Both frozen texture packs use 128-pixel
tiles; neither music file contains a UTXT embedded texture footer. The tested
reader therefore uses the separate texture file. Newly generated 64-pixel packs
and the embedded music-file layout still need separate validation, along with
actual Pocket storage/audio behavior. These sampled frames are not full-game
or full-benchmark coverage. The older profiler-only device measurements remain
separate evidence and do not measure this combined main revision.

## Evidence

Private build/combined-dd28-verified/ contains regenerated results.json,
summary.json, cases.json, twelve comparison reports and asset-audit.json.
The source snapshots, failed case and all original replay evidence stay ignored.

Baseline snapshot manifest SHA-256:
9d572dfa5bcb8e6bdf26b8ea8049a3906dd732bbf6f06e7828372b90e5201b34.

Main snapshot manifest SHA-256:
6ade3a13f0a63b5b75d8b9a69b5665a61c1ea50c02a3d79ee57ff67a450d1921.

CPU lock SHA-256:
f06eead7ccd9be1c9892fe18c9cfee61318307ccedbe38b5771054612587a94c.

| Snapshot | Game/window | Mode | Kind | Exact CASE under experiments/cases/ |
| --- | --- | --- | --- | --- |
| combined-base-20261011-135818 | undertale/flowey | speed | trace | combined-base-20261011-135818-undertale-flowey-speed-trace-2a13387eb32cae9f |
| combined-base-20261011-135818 | undertale/flowey | speed | timing | combined-base-20261011-135818-undertale-flowey-speed-timing-8a8a159a7921d2f4 |
| combined-base-20261011-135818 | deltarune/dodge | speed | trace | combined-base-20261011-135818-deltarune-dodge-speed-trace-d280bcc73d55b844 |
| combined-base-20261011-135818 | deltarune/dodge | speed | timing | combined-base-20261011-135818-deltarune-dodge-speed-timing-fed5c96a0bc4635c |
| combined-base-20261011-135818 | deltarune/dodge | accuracy | trace | combined-base-20261011-135818-deltarune-dodge-accuracy-trace-a0302c93d370890b |
| combined-base-20261011-135818 | deltarune/dodge | accuracy | timing | combined-base-20261011-135818-deltarune-dodge-accuracy-timing-606bab6c79b832db |
| combined-main-pack-adapter-20261011-145741 | undertale/flowey | speed | trace | combined-main-pack-adapter-20261011-145741-undertale-flowey-speed-trace-b7936f900f4ff8f8 |
| combined-main-pack-adapter-20261011-145741 | undertale/flowey | speed | timing | combined-main-pack-adapter-20261011-145741-undertale-flowey-speed-timing-c6bdd8fc2fec3680 |
| combined-main-pack-adapter-20261011-145741 | deltarune/dodge | speed | trace | combined-main-pack-adapter-20261011-145741-deltarune-dodge-speed-trace-c72a3f1d37c91518 |
| combined-main-pack-adapter-20261011-145741 | deltarune/dodge | speed | timing | combined-main-pack-adapter-20261011-145741-deltarune-dodge-speed-timing-c3dabc463ecd2ab1 |
| combined-main-pack-adapter-20261011-145741 | deltarune/dodge | accuracy | trace | combined-main-pack-adapter-20261011-145741-deltarune-dodge-accuracy-trace-ae676aff5b5564f9 |
| combined-main-pack-adapter-20261011-145741 | deltarune/dodge | accuracy | timing | combined-main-pack-adapter-20261011-145741-deltarune-dodge-accuracy-timing-913439922cdf8a6a |
