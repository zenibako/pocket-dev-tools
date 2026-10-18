# Low-overhead Pocket A/B capture builds

The original [palette A/B trial](PALETTE-LEAF-OS20.md) produced differences too
small to judge reliably by eye. Its on-screen profiler also disables the
candidate's no-op `pal()` path. These fresh instrumented builds add a dedicated
capture using the existing unconditional main-loop timings, with that profiler
hidden and its hook disabled. No new optimization is promoted.

## Package and use

Private combined package:
`experiments/pico8-sources/pocket-capture-20261018-r1/pico8pocket-capture-ab.zip`

SHA-256: `252d3b389cd3366ee724b1a0fe3e46b27fed1f99b23959e0777ad538ecb8afa6`

The two separately installed cores are **PICO-8 capture baseline**
(`zenibako.pico8capbase`) and **PICO-8 capture palette**
(`zenibako.pico8capleaf`). They use existing carts and have distinct settings,
saves and report names. All runtime-bound basenames fit the 23-byte limit from
[the boot filename fix](VARIANT-BOOT-FIX.md). No carts, save data, settings or
pre-existing reports are shipped. The combined ZIP includes `BENCHMARK.md`.

Reach a matching scene in each core, press Select, then physical Y from the
main in-core menu (`Y BENCH 30S`). The game resumes, warms for two seconds, and
records approximately thirty seconds without an overlay. Completion pauses in
the in-core menu with `BENCH SAVED`. Opening a menu, toggling profiling, any
native Memory/sleep request, or runtime failure cancels instead of exporting.

Reports append repeated captures. Exit normally through the Analogue menu to
flush nonvolatile data to SD, then return both `/Saves/pico8/p8pcapbase.bench`
and `/Saves/pico8/p8pcapleaf.bench`. Three runs per matching scene, same audio,
scale and input conditions, help distinguish small effects from run variation.
Capture in the same scene order on each core: Celeste before Trailhead,
Trailhead, then Moss Moss; identify the Moss activity separately. Scene labels
are not inferred from game RAM. The hardware paths and flush remain unverified
until the user's Pocket test.

## What the reports mean

A fixed-size 256 KiB NUL-padded text journal records source build ID, pinned
runtime, cart content hash, controls and audio/display settings per capture.
It records loop and presentation-call rates, draw counts, render divisors,
measured-work budget overruns and mean/p95/p99/max timings in microseconds.
Runtime timing includes GC. In these builds the runtime service hook polls
input; synthesis runs in the separately timed outer audio pump, not mid-frame.
Presentation timing is also separate. Presentation-call rates are
not an independent hardware scanout measurement. Percentiles use nearest rank.

Capture uses a bounded 4096-frame RAM buffer. It adds no timer calls, heap
allocation, formatting or report I/O during collection; export does the sorting,
formatting and fixed-size write afterward while paused. Frame periods include
pacing and collector bookkeeping. The two builds carry identical capture code;
compiler/cache layout and production random seeds can still affect the result.
This is a matched instrumented comparison, not a zero-overhead guarantee.

Existing app-unused data slot 8 is relabeled for the report. Its address
`0x20380000`, `0x40000` capacity, flags and declaration position are unchanged.
Settings/cartdata continue using `save:0` (data slot 10), with states in 10–19.
No extra slot was inserted: os20's legacy writeback mapping is positional.
Unknown, full or incomplete report journals are refused. A failed write can
still damage that report; export is not transactional or a synchronous SD flush.

## Source and verification

| Variant | Signed source | Production ELF SHA-256 | BRAM bytes |
| --- | --- | --- | ---: |
| Accepted audio + capture | `07e01f55c63b6e0a1c7f17673ff8f9ef771e3122` | `c559fb95dca3ede100cc689ba044661a0bdc279737cbf033ca4c8d0fd9ec128e` | 14,182 |
| Palette leaf + capture | `fbeec0103029669bcd0bc351b2e851bd89a0fa4d` | `ac9dc58fbf4ab00b5d26e3046aedce0f2fd7a0114cd1cbbc7d67caae989c1d84` | 14,322 |

The `src/runtime/` code, VM/GC implementations and copied dependency bytes remain
unchanged from their respective accepted/palette parents. Both BRAM sizes match
their original production builds; the candidate retains 14 bytes free. The
collector is compiled outside LTO. The build ID is a generated header and
main-object prerequisite; final builds pass the selected signed revision.

Both source variants pass core/runtime native suites, capture/export tests,
all four real-app integration modes and three variant packaging tests. Capture
unit tests also pass ASan/UBSan. Negative evidence reproduces absent collector,
missing menu action, malformed-journal overwrite and native failed-load capture
contamination before their fixes. Tests cover warm-up exclusion, timing wrap,
percentile boundaries, no-draw samples, capacity and append/rejection behavior.

The real-app test uses actual main/runtime/menu code with synthetic clock,
controller and display services. It verifies successful completion after warmup,
profiler shutdown and no export on menu/profiler/failed-state interruption. It
is not a hardware benchmark. Native smoke suites skip local Celeste acceptance
when no cart is installed in those worktrees; unchanged runtime source and the
retained earlier cart output evidence are separate from the new app-loop tests.

Both offline production links and APF package validations pass. A host test using
exact pinned kernel functions reproduces the old filename failure and resolves
both new ELF bindings correctly. Final checks compare packaged ELF bytes, build
IDs, filename limits, save-table positions and matched pinned OS/FPGA/loader
assets. Physical boot, SD writeback and capture timing overhead remain for Pocket
validation. No deployment, runtime/SDK modification or push was performed.

Private build logs, source scopes, firmware fixture, manifests and packages are
preserved under `experiments/pico8-sources/pocket-capture-20261018-r1`.
