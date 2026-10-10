# Sprite-culling microprobe

This adapter replays `swrSpriteCostProbe` from an explicitly pinned private
revision snapshot. It measures direct renderer calls rather than whole frames
or GML instruction costs. See [RESULTS.md](RESULTS.md) for the measured case and
its comparability limits, and [bench/README.md](../bench/README.md) for snapshot
creation, isolation and private asset requirements.

From the harness root, first export the desired revision with
`experiments.py snapshot`. Then:

```sh
python3 sprite_probe.py --snapshot SNAPSHOT_NAME --selection 40x40
python3 cache_profile.py --case EXACT_PRINTED_PROBECASE
python3 cache_profile.py --case EXACT_PRINTED_PROBECASE --disabled
python3 cache_profile.py --case EXACT_PRINTED_PROBECASE --negative
python3 sprite_report.py --result EXACT_POSITIVE_RESULT --checks EXACT_DISABLED_RESULT EXACT_NEGATIVE_RESULT --output build/sprite-probe/results.json --markdown spriteprobe/RESULTS.md
```

Each invocation uses an absent destination and preserves previous evidence.
Only independently copied harness directories are mounted in Docker. No
deployment, SD access or modification of the supplied source checkout occurs.

The generated adapter removes `SW_DRAW_PROFILE` and
`ENABLE_VM_GML_PROFILER`, enables only the independent `SWR_SPRITE_PROBE`
stop/path gates, and rejects unwanted profiling/tracing symbols in the ELF.
It runs eight 2,000-call batches three times, after the probe's original warm
draw. The 40×40 selection forces the older fallback search; `grid` retains the
newer preference and can fail if no valid sprite is selected at the checkpoint.
Setup and validation stay outside exact MMIO clock intervals. SDK 64-byte
function/loop alignment is applied. The interpreter uses application BRAM;
renderer code uses SDRAM. CPU/cache parameters remain unchanged.

Two captures must agree on RAM/stack checkpoints, all 24 oracles, geometry and
raw pixel/PCM artifacts. The regular, enabled and disabled RTL runs must agree
exactly on batch cycles and oracles. The negative control must reject a corrupted
oracle. Audio is suppressed; oracle field 4 contains call count, not PCM pairs.
Raw events retain per-sample refill distributions and retirement/dependency
histograms. Reported stall sources overlap; exclusive accounting is a stated
presentation priority rather than a causal speedup estimate.
State/pixel hashing and logs between batches can change cache and predictor
contents. Their time is excluded, but their effect on later batches is retained.

This currently supports the staged probe source shape on `perf/mirrored-blend`
at `3c2d37a`. Source substitutions fail closed when their expected anchors
change. The adapter runs at the start of Deltarune frame 3323. It does not prove
the physical card's compiler, binary layout, checkpoint or OS revision matches.
