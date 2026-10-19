# Pico8Pocket runtime adapter

This experimental second workload follows the boundary in
[ARCHITECTURE.md](../ARCHITECTURE.md): shared CPU/cache/memory infrastructure,
separate deterministic cart route, checkpoint and output oracles. The existing
Butterscotch inputs and baseline remain unchanged. Pico8Pocket's
`docs/architecture.md` identifies its shipped platform as **os20**; this
adapter historically ran **os25**. New performance cases can select a separate
**os20 at 90 MHz** platform with `--platform os20`. Existing os25 cases and the
Butterscotch baseline remain unchanged. Simulated timings cannot be presented
as physical Pocket performance.

Scene reports: [Celeste 2](CELESTE2-OS20.md), [Moss Moss](MOSS-OS20.md),
the [iterator/callback A/B experiments](ITERATOR-OS20.md), and the
[table-identity optimization](FOREACH-TABLE-OS20.md), and
[PCM output-pair batching](AUDIO-PAIRS-OS20.md), and the
[rejected environment-lookup experiments](ENV-LOOKUP-OS20.md),
[fixed-layout lookup diagnostic](ENV-LAYOUT-CONTROL-OS20.md),
[single-result peek experiment](PEEK-SINGLE-OS20.md), and
[warm immediate-return call experiments](EMPTY-LUA-CALL-OS20.md), and
[rendering API costs](RENDER-COSTS-OS20.md), and the
[complete-tile experiments](TILE-FULL-OS20.md), and
[remapped-palette tiles and placement controls](TILE-PALETTE-LAYOUT-OS20.md), and
[the two-path tile hybrid](TILE-HYBRID-OS20.md), and
[the deeper palette investigation](TILE-DEEP-OS20.md), and
[the separate draw-identity experiment](DRAW-IDENTITY-OS20.md), and
[its cause-isolation and combined BRAM follow-up](DRAW-IDENTITY-DEEP-OS20.md),
[the source palette PR matrix](PALETTE-SOURCE-OS20.md), and
[source components and compiler-budget attribution](PALETTE-COMPONENTS-OS20.md),
[matched GC-wrapper policy controls](GC-POLICY-OS20.md),
[accepted-audio palette and selective GC experiments](ACCEPTED-COMBOS-OS20.md),
[isolated palette leaves and Pocket A/B package](PALETTE-LEAF-OS20.md),
[the corrected A/B package boot filenames](VARIANT-BOOT-FIX.md),
[Pocket capture builds and report instructions](POCKET-CAPTURE.md),
[capture status and persistence diagnostics](CAPTURE-PERSISTENCE.md),
[the first physical Pocket Trailhead reports](POCKET-TRAILHEAD-20261018.md),
[detailed Pocket capture and controlled runs](POCKET-DETAILED-CONTROLLED.md),
[the moving Celeste grapple preset and packages](POCKET-GRAPPLE-CONTROLLED.md),
[physical grapple/Moss results and stall attribution](POCKET-GRAPPLE-RESULTS-20261018.md),
[grapple inherited-field cost diagnostics](GRAPPLE-COSTS-OS20.md),
[the guarded inheritance shortcut and regression matrix](GUARDED-DELEGATE-OS20.md),
[the isolated Moss regression causes](GUARDED-MOSS-ISOLATION-OS20.md),
[the preserved lookup and cold-helper placement experiment](GUARDED-COLD-PLACEMENT-OS20.md),
[the stable-image Moss controls and source refinements](MOSS-STABLE-IMAGE-OS20.md),
and [the explicit callback payload/tag experiment](SCALAR-CALLBACK-OS20.md).

Build the os20 platform once before creating os20 cases:

```sh
python3 pico8/cpu_platform.py build --jobs 4
python3 pico8/cpu_platform.py verify
python3 pico8/run.py create --source /absolute/pico8pocket \
  --archive /absolute/carts.zip --name os20-fixed --platform os20 \
  --hash-seed 0x5eed1234 --measure-frames 12
```

The launcher privately copies the locked CPU sources and generates the frozen
OS `8318f25` os20 configuration: dual issue, 32 KiB I-cache, 64 KiB D-cache,
reduced-accuracy FMA and a 4-slot/32-operation store buffer. It resolves os20's
production SDRAM/GPU macros, including the 660-cycle refresh interval, sets the
peripheral clock register to 90 MHz, scales the 74 MHz bridge clock ratio, vsync
and diagnostic scanout cadence, and records CPU/simulator/source hashes. Each
os20 replay reads and validates the actual MMIO clock register before timing.
Completed platform builds are preserved; `rtl` can resume an incomplete build.

**Production provenance:** Resolve the current runtime identity from
Pico8Pocket's `scripts/fetch-deps.sh`. As checked on 2026-10-16, it pins
`zenibako/openfpgaCore` at `a58aacd` and release `pocket-runtime-a58aacd`:
the `92202ab` FPGA fit with BRAM bootloader/OS `.fasttext` re-patched by the
firmware build. Keep `os20.rbf_r`, `os.bin` and `loader.bin` from that same pinned
release; the bitstream and OS must match builds. Its os20 CPU configuration,
generator, VexiiRiscv pin (`580b76c`), CPU system and Pocket SDRAM controller
are unchanged from frozen OS `8318f25`; save-state/CRAM0 handshake logic,
hardware mixer restoration and firmware differ. The fitter seed also changed
from 33 to 12. These production save/restore paths are outside runtime replay.
Recheck these sources on runtime upgrades. This confirms source-profile
continuity, not fitted-bitstream equivalence or device timing parity. Preserve
the frozen platform and its historical cases; a platform change needs a separate
pin and recaptured evidence.
The existing chip model retains conservative cycle timing checks. The compiler,
allocator, omitted OS/presentation work and cold caches remain harness limits.
Single-lane os25 instruction/pipeline observers are not validated for dual-issue
os20. The existing `create` default remains os25 for workflow compatibility;
use `--platform os20` explicitly for Pico8 performance experiments.

Create an independent private case from the cloned, dependency-prepared port
and a supplied ZIP. Only `.p8` and `.p8.png` entries are copied; bundled desktop
executables and nested ZIPs are not executed. Cart names are metadata, never
filesystem destinations. The sole Docker mount is the case itself.

```sh
python3 pico8/run.py create --source /absolute/pico8pocket \
  --archive /absolute/carts.zip --name supplied-20261010 \
  --platform os20 --hash-seed 0x5eed1234
python3 pico8/run.py build --case EXACT_CASE
python3 pico8/run.py native --case EXACT_CASE --jobs 4
python3 pico8/run.py capture --case EXACT_CASE --jobs 4
python3 pico8/run.py replay --case EXACT_CASE --jobs 4
python3 pico8/run.py report --case EXACT_CASE
```

Use `--pending-only` with `native`, `capture` or `replay` to resume a sweep
without replacing completed phase evidence. `analyze` can recover a completed
RTL log after a host-parser failure. A complete verdict, the UART transcript,
memory checks and output oracles are still required.

The native route executes 600 frames twice, including synthesizer work.
By default it retains the port's ordinary Lua hash seed, so address/time-dependent table
iteration can make pixel output nonrepeatable even when execution completes.
QEMU warms 180 frames, saves the complete allocator/VM/process state, then
executes three frames twice. Pixel, display-palette, PCM, input and target-FPS
oracles and complete checkpoints must repeat. RTL resumes that exact ELF and
compares all three frames, retaining the existing memory-delivery checks.
`capture.json` records `native_output_equal` separately from `passed`; require
both before interpreting timing. A repeatable QEMU capture can pass even if
native output disagrees. The standard runner exports channel hashes, checkpoint
and stack, not raw pixel/palette/PCM files or a cross-case comparison. Use a
separately validated collector for raw byte comparisons, or report hash agreement.
`time()` joins the existing virtual `clock_gettime`/`gettimeofday` model in
RV32 builds, making Lua's initial string hash seed repeatable at fixed addresses.
The VM dispatch and hot helpers use SDK BRAM sections; the bounded allocator
is the existing fullframe harness allocator, not production musl malloc.
The game state is warmed, but RTL caches start cold. Timed intervals include
the runtime step and fixed PCM render; they exclude output hashing, UART and
video presentation. Hashing/logging between samples can affect later caches.

`report` writes `REPORT.md`, `results.json` and `FPS.csv` for every supplied
cart. The FPS table records the selected platform and target rate and estimates
runtime capacity as its recorded clock (90 MHz os20 or 100 MHz os25) divided by
mean cycles over the recorded replay window, capped at the target rate.
The CSV also retains uncapped capacity and mean simulated frame time. A cart
that fails before replay has a target rate where available, but no estimate.
These short samples can remain on title screens and exclude presentation,
OS scheduling and adaptive draw skipping; they are not measured Pocket FPS.

`create --setup EXPR` evaluates one Lua expression after cart load, through the
port's `P8P_RUNTIME_DEBUG` hook, to reach a chosen scene; `--input none` holds
no buttons in every frame instead of the seed-7 route. Both are recorded in
`case.json` and `pico8/route.json`, are part of the case inventory and apply to
the native, QEMU and RTL runs alike. Compare cases only with the same route.
Without these options the input route remains unchanged.

Use `--cart ID` to restrict a phase. For a repeatable cart, verify diagnostic
scanout and a deliberately corrupted pixel oracle as controls:

```sh
python3 pico8/run.py replay --case EXACT_CASE --cart 000 --traffic scanout
python3 pico8/run.py replay --case EXACT_CASE --cart 000 --negative
python3 pico8/run.py report --case EXACT_CASE
```

All earlier evidence is preserved. Failed builds need a new case after an
adapter repair. Each case records source revision, archive and file hashes,
CPU/netlist and simulator identity. Private cases and cart-level reports live
under ignored `experiments/pico8/`. The frozen baseline is verified before
snapshotting. No deployment or Pocket SD access occurs.

For an adapter repair that leaves all native sources and carts byte-identical,
`build --reuse-native-from EARLIER_CASE` validates those inventories and imports
the native binary and its raw logs. The import manifest identifies the earlier
case and binary. RV32 captures and replay use the freshly built target ELF.

This is bounded runtime smoke coverage, not PICO-8 conformance or game
completion. Index/palette pixels and synthesized PCM are compared, not physical
video/audio output. OS/menu scheduling, persistent cartdata/saves, filesystem
multicart loading, the presentation pass, GPU and device timing remain outside
this adapter. Input stays within six game buttons. A common script can remain
on a title screen in some carts; successful execution alone does not prove
useful gameplay coverage. Failed carts remain visible in the matrix.

## Fixed final hash seeds and longer GC traces

`create --hash-seed 0x5eed1234` bypasses the final `makeseed(L)` result in
private z8lua sources. Overriding `luai_makeseed()` alone does **not** fix the
final seed: Lua also mixes process addresses. Seeds from 0 to 0xffffffff are
accepted, including zero. Every fixed-seed runner reads the actual Lua state,
checks the expected value, and emits `PICOSEED`; a missing hook fails the build.
The transformation happens before the immutable case inventory. No source
checkout or frozen input is edited. Production seeding remains unchanged.

`--warmup-frames`, `--measure-frames` and `--trace-frames` configure the
checkpoint frame, replay length (1–60), and native/long-QEMU route length.
Defaults remain 180, 3 and 600. The oracle array, parsers, cycle limit and report
all use the recorded sizes; existing cases retain their original settings.
Native evidence import now also checks benchmark headers and route flags.

```sh
python3 pico8/run.py create --source /absolute/pico8pocket \
  --archive /absolute/carts.zip --name fixed-gc \
  --platform os20 --hash-seed 0x5eed1234 --measure-frames 12 --trace-gc
python3 pico8/run.py build --case EXACT_CASE
python3 pico8/run.py native --case EXACT_CASE --cart 023
python3 pico8/run.py trace --case EXACT_CASE --cart 023
python3 pico8/run.py capture --case EXACT_CASE --cart 023
python3 pico8/run.py replay --case EXACT_CASE --cart 023
```

`--trace-gc` inserts identical diagnostic hooks into private runtime and z8lua
snapshots. It requires an explicit seed. `trace` preserves two long QEMU logs,
checks output and counter repeatability, and compares native output. QEMU
counts describe RV32 allocation and GC scheduling; all scope times are zero.
Native scope times are monotonic nanoseconds. RTL scope times are simulated
cycles at the recorded platform clock. Hashes and checkpoint pointers compare within the same ELF;
only independent output rows and semantic counters compare across builds.

`PICOGC` records logical new/realloc/free calls, requested and released bytes,
failures, allocator time, allocation time inside GC, inclusive GC time,
outer GC/full-collection entry counts, completed cycles, heap/debt/state/string
occupancy, atomic/finalizer time, GC time by frame phase, and collector steps
by entry state. A null allocation's old size is a type tag, so it is never
counted as released bytes. Allocation bytes exclude pooled slab reservations.
GC is observed around both forced incremental steps and full collections,
including work triggered by frame coroutine setup before update/draw.

The phase times sum to inclusive GC time. Do not add inclusive GC and all
allocator time: allocator work inside GC appears in both. A nonoverlapping
partition is GC time, allocator time minus allocator time inside GC, and the
remaining frame time. Atomic/finalizer scope times are also nested
observations, not extra costs. A Lua error or unbalanced scope invalidates the
run. Run matching cases without `--trace-gc` as speed controls; diagnostic
hooks, logging and code layout can change timing even with identical output.
