# Unused VM helper cleanup: not included in PR #15

The cleanup passes correctness and production checks but fails the strict
no-regression timing gate against PR revision `c400307`. After reviewing the
results, the user chose to leave PR #15 unchanged. Its verified remote head
remains `c400307`; cleanup commit `43356f0` is signed and local only.

Simulated **os20/90 MHz**, fixed seed `0x5eed1234`, fixed PCM, identical input
routes and measured windows. These are changes in runtime cost relative to the
PR, not physical Pocket FPS. Lower is better.

| Scene | Quiet change | Scanout change |
| --- | ---: | ---: |
| Moss steady | +0.193% | +0.284% |
| Moss GC | +0.029% | +0.061% |
| Celeste full throw | -0.393% | -0.346% |
| Celeste whole grapple | -0.290% | -0.281% |
| Trailhead | -0.102% | -0.110% |
| Intro | +0.045% | -0.015% |

Moss steady adds about 0.093–0.139 ms/frame. Both Moss windows remain faster than
the older accepted audio/palette baseline, but that does not satisfy the requested
no-regression check against the current PR. The earlier intro caveat against the
accepted baseline is separate from these incremental changes. Exact means,
per-frame deltas and both comparison baselines are in
[HELPER-CLEANUP-OS20.csv](HELPER-CLEANUP-OS20.csv).

## Scope and verification

The local change removes `luaV_callindex` and `luaV_delegatebits` and their private
header declarations. `luaV_delegateget`, `luaV_delegateclosure` and actual `callTM`
behavior are retained. Tests now invoke fallback via real Lua operations, retaining
all five VM callback sites, light-C/captured-C closures, callable-table and invalid
callback paths, mutation, false/missing values and no-result assignment. A direct
production typed-guard contract remains. The replacement suite passes before and
after helper removal; core/runtime/delegate tests and assertion-enabled VM syntax
checks pass. All 18 patches reapply to pristine pinned z8lua and reproduce all
62 prepared source/header files. No removed helper references remain.

All five cases pass repeated native/QEMU output, quiet/scanout RTL, negative pixel
controls and memory oracles. Full native indexed pixels, palettes, PCM bytes and
pair counts match the preceding PR captures over each complete 400/600-frame
route. Target checks compare measured-window channel hashes/pair counts, not full
raw target channels. Heap bases and build flags match the preceding cases.

The clean production ELF builds offline, excludes both removed symbols, retains
entry `0x10400000` and all five hot functions in order, and uses unchanged BRAM
capacity `0x375a/0x3800`. Its cold section shrinks from 1,074 to 728 bytes. Removing
unused code/declarations changes linked placement and relocation bytes; this
experiment does not attribute the timing differences to a particular hardware
stall mechanism.

Production ELF SHA-256:
`e9922f7e22152af7610cce518cf93fa60b0729a7f6e9e47ca29ab3a941e552dc`.

Private evidence: `experiments/pico8-sources/helper-cleanup-20261019-r1/`.
`report.py` revalidates source manifests, flags, raw channels, repeats, seed/clock,
UART cycles and memory/negative oracles. `validation.json` records completeness
and the failed no-regression gate. `verify-production.py` checks clean-source
provenance, symbol removal, startup, section membership and BRAM fit. Earlier
cases, the active port checkout, original SDK/OS and SD remain untouched. No PR
comment, thread resolution, package or deployment was made for this cleanup.
