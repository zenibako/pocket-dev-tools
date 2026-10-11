# Pico8Pocket adapter results

Summaries of baseline/candidate studies run through this adapter. Cart-level
tables, raw logs and reports stay in the ignored private cases named below.
Every timing is **simulated**: os25 RTL at 100 MHz, runtime step plus fixed PCM
render over frames 180–182 with cold CPU caches. Pico8Pocket ships os20; none
of this is a measured Pocket frame rate. See [README.md](README.md) for limits.

## 2026-10-10: z8lua call fast path (pico8pocket PR #10)

Baseline `main` `033762e`; candidate `877baae`, later merged as `442a836`. The
only compiled difference is `lvm.c` through `patches/z8lua-call-fastpath.patch`.

**Celeste Classic 2, level 2** (`create --setup` with `goto_level(2)`,
`--input none`): mean 2,834,848 → 2,808,286 cycles quiet (−0.94%) and
2,841,541 → 2,811,856 with diagnostic scanout (−1.04%). Pixel, palette and PCM
hashes are identical across builds for 600 native frames and the RV32 window.
Repeat captures, RTL replay, memory oracles and the corrupted-oracle control
pass for both builds.

**Supplied 68-cart suite, shared seed-7 route:** 67 carts replay on both
builds; Backrooms fails before the window on both. Over the 65 like-for-like
carts the candidate is cheaper on 36 and dearer on 29: median −0.14%, mean
−0.53%, range −14.34% to +5.83%, summed cycles −0.28%. For the 26 carts below
their target rate on either build, summed cycles change by +0.18%. Output
hashes are identical for 66 of 67.

Two carts are left out of those statistics. Bunny Envmap (+8.74%) is a tech
demo and was not investigated. Grippy's output differs between builds: its
pixels depend on the Lua hash seed, which mixes in code and heap addresses, so
its +10.15% is not a like-for-like cost and this run cannot say whether the
patch changes its behaviour.

**Reading:** no cross-cart speedup or regression is established. The earlier
tline study saw −6.1% to +3.8% on carts that never ran the changed code, so
most single-cart changes here are within layout and hash-seed noise. A
forced-equal seed control was not run; `luai_makeseed()=0` alone does not
equalise the seed.

Private evidence: `experiments/pico8/calls-suite-main-r1`,
`calls-suite-candidate-r1` (`COMPARISON.md`, `comparison.csv`, `compare.py`),
`calls-tower-main-r2`, `calls-tower-candidate-r2`, and the failed first setup
expression in `calls-tower-main-r1`. Sources and the run log are under
`experiments/pico8-sources/calls-20261010`.
