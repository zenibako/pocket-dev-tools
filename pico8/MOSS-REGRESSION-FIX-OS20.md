# Moss regression recovery and dense iterator

The normal source build fixes the measured Moss regression while retaining the
guarded inherited-field shortcut for Celeste 2. It does **not** pass a strict
all-scene runtime-cost gate: the intro remains 0.58–0.75% slower. PR #15 stays a
draft, and physical Pocket performance for this source revision remains untested.

| Scene | Quiet ms | Change | Scanout ms | Change |
| --- | ---: | ---: | ---: | ---: |
| Moss steady | 48.686 → 48.042 | -1.32% | 49.419 → 48.741 | -1.37% |
| moss-gc | 49.041 → 48.331 | -1.45% | 49.806 → 49.056 | -1.51% |
| Celeste full throw | 94.453 → 74.857 | -20.75% | 94.660 → 75.000 | -20.77% |
| Celeste whole grapple | 68.637 → 58.973 | -14.08% | 68.794 → 59.101 | -14.09% |
| trailhead | 42.929 → 41.066 | -4.34% | 43.022 → 41.193 | -4.25% |
| intro2 | 25.740 → 25.890 | +0.58% | 25.789 → 25.983 | +0.75% |

Timings are **simulated os20 at 90 MHz**, fixed seed `0x5eed1234`, fixed PCM,
accepted audio/palette baseline `db6bced` (same tree as merged `77bcd69`). Windows:
Moss steady 180–191, Moss GC 234–245, grapple 304–308/full throw 305–306,
Trailhead and intro 100–111. Intro costs about 0.15–0.19 ms more and stays below
33.33 ms of runtime in this harness; that does not establish device frame pacing.

## Source change and trade-off

`api_all_next` handles dense array slots containing tables in a small path;
primitives, sparse entries, numeric hash slots and end transitions use the
original general traversal in `all_next_slow`. Every fallback precedes iterator
state writes. Identity/deletion behavior, result copying and GC barriers remain
intact. The common RV32 stack frame falls from 48 bytes in the general inlined
array-probe experiment to 16 bytes. No array pointer is retained across cart code.

Five measured hot lookup/iterator sections are grouped with the project linker
script using natural function alignment. No absolute function addresses or binary
patches are used. The internal callback uses explicit payload/tag values and its
original ordinary-text placement; the non-LTO delegate helper remains cold.
Production LTO must receive function/data-section flags at link time, and the
collecting augmentation precedes the SDK script. The SDK is unchanged. Startup
is retained at `0x10400000` and asserted during linking.

Moss does not execute the new guarded callback in its sampled steady window.
Earlier image controls showed beneficial interpreter changes when surrounding
code stayed fixed, so the source regression was not extra guard work. Actual
iterator work reduction plus deliberate grouping mitigates the whole-image
interaction; this does not prove a particular cache conflict or branch stall.

Alphabetical function order, source-unit LTO partitioning, the five-function
group alone, and the general inlined array probe all retained a Moss loss. The
first combined probe/group candidate improved steady Moss but lost 0.15% in its
GC window and 1.53–1.76% in the intro. The dense path is the selected source.
Restoring the cold callback on that path still lost 1.60–1.78% in the intro and
is excluded. Percentages from separate layouts are not additive contributions.

## Verification and provenance

Core/runtime/delegate tests pass, including repeated table identity, deletion,
array growth with GC, mixed-value transitions, hash entries and metamethod
bypass. An initial 256-item numeric test overflowed PICO-8 fixed-point arithmetic;
the fixture was corrected to 128 items before implementation. All 18 patches
reapply to pristine pinned z8lua and reproduce all 62 prepared source/header files.
Assertion-enabled VM compilation passes.

All five selected cases pass repeated native/QEMU output, quiet and scanout RTL,
corrupted-pixel negative checks and memory oracles. Native indexed pixels,
palettes, PCM bytes and pair counts match baseline over each complete 400/600-frame
route. Target comparisons cover hashes and pair counts in measured windows;
full target raw channels were not collected. Case implementation inventories are
identical across source revisions `55d9e35` and `c400307`; their only Git difference
is added tests. The selected production ELF is from clean signed `c400307`.

The production ELF builds offline, preserves entry/constructors/BSS and has
nonoverlapping loads. BRAM uses `0x375a` of `0x3800` bytes (166 bytes free).
ELF SHA-256: `578fa706c75b79f22fc8f9c5a6090fb464c6f11da9886024315308b9cddb5404`.
Two explicit production failures exposed missing LTO function sections; corrected
builds and the startup-address check are retained. No package, SD installation,
active checkout or original SDK/OS was changed.

Private evidence: `experiments/pico8-sources/moss-link-order-20261019-r1/`.
`report.py` revalidates source manifests, original launcher hashes, raw channels,
repeat captures, clock/seed, RTL cycles and memory/negative oracles before writing
[MOSS-REGRESSION-FIX-OS20.csv](MOSS-REGRESSION-FIX-OS20.csv). `accept.py` records
Moss/gameplay acceptance and the failed strict all-scene gate separately.
Production provenance, semantic reviews and all rejected/failed cases remain
private. A codegen filename collision was corrected by preserving original
launcher versions and regenerating policy-specific audits; timings were unchanged.
