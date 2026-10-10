# Pico8Pocket runtime adapter

This experimental second workload follows the boundary in
[ARCHITECTURE.md](../ARCHITECTURE.md): shared os25 CPU/cache/memory RTL,
separate deterministic cart route, checkpoint and output oracles. The existing
Butterscotch inputs and baseline remain unchanged. Pico8Pocket's
`docs/architecture.md` identifies its shipped platform as **os20**; this
adapter runs **os25**. Simulated timings cannot be presented as shipped-core
or physical Pocket performance.

Create an independent private case from the cloned, dependency-prepared port
and a supplied ZIP. Only `.p8` and `.p8.png` entries are copied; bundled desktop
executables and nested ZIPs are not executed. Cart names are metadata, never
filesystem destinations. The sole Docker mount is the case itself.

```sh
python3 pico8/run.py create --source /absolute/pico8pocket \
  --archive /absolute/carts.zip --name supplied-20261010
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
It retains the port's ordinary Lua hash seed, so address/time-dependent table
iteration can make pixel output nonrepeatable even when execution completes.
QEMU warms 180 frames, saves the complete allocator/VM/process state, then
executes three frames twice. Pixel, display-palette, PCM, input and target-FPS
oracles and complete checkpoints must repeat. RTL resumes that exact ELF and
compares all three frames, retaining the existing memory-delivery checks.
`time()` joins the existing virtual `clock_gettime`/`gettimeofday` model in
RV32 builds, making Lua's initial string hash seed repeatable at fixed addresses.
The VM dispatch and hot helpers use SDK BRAM sections; the bounded allocator
is the existing fullframe harness allocator, not production musl malloc.
The game state is warmed, but RTL caches start cold. Timed intervals include
the runtime step and fixed PCM render; they exclude output hashing, UART and
video presentation. Hashing/logging between samples can affect later caches.

`report` writes `REPORT.md`, `results.json` and `FPS.csv` for every supplied
cart. The FPS table records the target rate and estimates runtime capacity as
100 MHz divided by mean cycles over frames 180–182, capped at the target rate.
The CSV also retains uncapped capacity and mean simulated frame time. A cart
that fails before replay has a target rate where available, but no estimate.
These short samples can remain on title screens and exclude presentation,
OS scheduling and adaptive draw skipping; they are not measured Pocket FPS.

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
