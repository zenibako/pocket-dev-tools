# Complete battle-frame replay

This extension executes three consecutive complete game-loop frames on the
production os25 CPU/fabric/SDRAM RTL. Undertale covers Flowey frames 2400–2402;
Deltarune Chapter 1 covers an enemy turn in `room_field2`, frames 3323–3325.
All VM events and game services reached by those frames execute, including
script calls, instance changes, collision checks, software sprite rendering,
texture reads, and platform ADPCM decoding/mixing. Native script acceleration
is disabled. The original numeric event fixtures are separate and unchanged.

## Run

Run from the standalone repository root. Follow [SETUP.md](../SETUP.md) first. Only this directory
is mounted at `/work` in Docker. Its copied assets are read; checkpoints, images,
logs and reports are written here. The active checkout and SD card are not used.
The harness code is tracked; local source snapshots, assets, captured bytecode,
checkpoints and generated output are ignored, as described in the main README.

The base toolchain and os25 RTL must be built first. After importing inputs,
create event captures with `python3 capture.py all`, then run
`python3 run.py all --jobs 4`. A snapshot imported with `--with-evidence` may
already contain these artifacts; verify its evidence before reusing it.
The extension adds QEMU user emulation to the base toolchain image:

```sh
python3 fullframe/run.py toolchain
python3 fullframe/run.py rtl --jobs 4
for variant in sdram bram; do
    python3 fullframe/run.py build --variant "$variant"
    python3 fullframe/run.py capture --variant "$variant"
    python3 fullframe/run.py prepare --variant "$variant"
    python3 fullframe/run.py run --variant "$variant" --traffic quiet
    python3 fullframe/run.py run --variant "$variant" --traffic scanout
    python3 fullframe/run.py run --variant "$variant" --negative
done
python3 fullframe/report.py
```

For an existing prepared capture, `python3 fullframe/run.py run --game deltarune`
replays only Deltarune in SDRAM. `--variant bram` places `executeLoop` in application
BRAM at `0x4000`; all other game code and state remain in SDRAM. `--traffic scanout`
adds diagnostic display traffic. `--negative` deliberately changes the first
expected state hash and requires the firmware to reject it.

## Capture and independent checks

The same RV32 executable runs under QEMU and Verilator. QEMU performs the existing
`platform/ut_bench.c` route from fresh volatile saves with random seed 7. Immediately
before the chosen battle window, assembly saves the stack pointer, callee-saved
integer/float registers and floating-point control register. The snapshot contains
the entire loaded SDRAM image, BSS, allocated/freed heap and stack. BRAM code comes
from the ELF. Two QEMU captures must produce byte-identical RAM and stack files,
and identical frame results, before a checkpoint can be replayed.

The RTL starts with empty caches, restores that process, and advances all three
frames consecutively. The checkpoint is loaded before reset is released; normal
CPU execution performs subsequent SDRAM writes. It does not reconstruct individual
events or substitute a transcript for builtins. Each completed frame must match:

* Frame number and a recursive checksum of globals, instances, structs, variables,
  strings, arrays, methods, fixed instance fields and BC17 local-slot maps.
* Every RGB555 framebuffer byte and every PCM sample submitted by the mixer.
* PCM sample-pair count, executed VM opcode count, event-call count and the trace
  checksum of code indices, bytecode offsets and instructions.
* Clean VM stacks, plus the existing SDRAM/AXI delivery and ordering checks.

`repeat-0/frame-0.ppm` through `frame-2.ppm` retain the reference rendered frames.
The observed VM counts are 1,181/1,183/1,198 opcodes and 17 events per Undertale
frame; Deltarune executes 18,120/18,343/17,949 opcodes and 53/59/54 events.
Both games submit 800 stereo PCM sample pairs per frame.

`build/fullframe/results.json` collects eight configurations, 24 frame rows,
four rejected bad-state oracles, all source/capture/ELF/simulator hashes and logs.
The report command verifies that evidence against current files and rejects stale
results. The launchers also verify all 1,631 frozen input hashes before and after
work. Changing firmware requires rebuilding, recapturing and preparing it again.

Verified on 2026-10-10: all eight configurations passed, with 24 matching frame
rows and all four intentional state mismatches rejected. The existing event
fixtures also passed their host ASan/UBSan reference and negative-oracle checks.
Mean instrumented game-loop time over each three-frame window, at the modeled
100 MHz CPU clock:

| Game | SDRAM quiet | SDRAM scanout | BRAM quiet | BRAM scanout |
| --- | ---: | ---: | ---: | ---: |
| Undertale | 26.02 ms | 30.15 ms | 25.95 ms | 29.95 ms |
| Deltarune Chapter 1 | 322.39 ms | 354.88 ms | 318.18 ms | 347.88 ms |

These measurements include VM instrumentation and the harness platform/allocator
costs described below. They support comparisons within this harness; an
uninstrumented production build needs separate profiling.

## Hardware fidelity and timing limits

The CPU, caches, FPU, bus fabric, Pocket SDRAM controller, arbiter and registered
BRAM model are the same verified os25 sources used by the existing harness.
Memory placement follows the copied SDK `app.ld`: executable/state SDRAM starts
at `0x10400000`; the heap grows from the ELF end and stops at `0x13a00000`;
the stack is captured at `0x13f80000..0x13fff000`. The harness allocator splits and
coalesces blocks within that bound; it is not production musl malloc.

Frame cycle timing uses production MMIO `0x40000004`, surrounding the real loop's
input/update/render/audio/present work. Validation and output occur afterward.
Opcode tracing overhead is included, and the first frame starts with cold caches.
`simulated_ms` assumes a 100 MHz CPU. These numbers do not measure physical Pocket
FPS or the cost of a production uninstrumented build.

The platform clock advances by 16,666,667 ns per frame. Physical controls are
idle; the existing benchmark route supplies deterministic game input. A virtual
audio queue consumes 800 sample pairs per frame and validates actual mixed PCM.
Read-only asset requests use an uncached CRAM0 mailbox at `0x30000000`, with CPU
ownership enabled through `0x4e000000`. The simulator serves only files inside the
private copied asset directory; the CPU copies payloads through its memory buses.
Filesystem host latency and physical SD timing are not modeled.

Scanout uses the diagnostic injector: 320 words per 640-pixel RGB555 line,
480 active of 525 lines, one line per 3,175 CPU cycles. It adds a representative
display bandwidth load from a separate memory range, without implementing the
display controller's scheduling or showing its output. GPU RTL remains idle
because these captures use the software renderer. Hardware audio traffic,
interrupts, synthesis/resource fit and board behavior still require separate
tests. Existing unsupported game/renderer features remain unsupported; passing
these windows does not prove every battle or the full game compatible.

The extension follows the copied `platform/ut_bench.c`, SDK `app.ld`,
`generate_vexii.sh`, `cpu_system.v`, and the OS CPU/memory experiment documentation
referenced by the main README. Source revisions remain recorded in
`input-manifest.json`. These local captures include proprietary game state,
bytecode and assets; no files have been uploaded or published.

The harness framebuffer uses cached SDRAM; the deployed runtime uses an uncached
framebuffer alias. Its memory costs are therefore not equivalent to the device.
State hashes contain pointers and must match QEMU/RTL for the same binary; compare
pixels, PCM and relevant game values separately across candidate binaries.
