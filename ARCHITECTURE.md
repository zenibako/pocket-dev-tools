# Infrastructure and workloads

This extraction preserves the verified design described in [README.md](README.md)
and [fullframe/README.md](fullframe/README.md). It changes repository ownership
and setup, not the CPU configuration or the game runtime used in the baseline.

| Layer | Current implementation | Reuse |
| --- | --- | --- |
| Dependency setup | `bootstrap.py`, input manifest, CPU lock | Hash-checked isolated source copies |
| CPU/memory platform | OS os25 RTL, chip models and Verilator wrappers in `harness.py` | os25 CPU, caches, bus fabric, SDRAM/BRAM and memory delivery checks |
| Build launchers | `run.py`, Dockerfiles | Single-directory build isolation and toolchain |
| VM workload | `workloads.c`, `services.c`, `battle_replay.*`, `battle_fixtures.py`, `capture/` | Butterscotch BC16/BC17 and event transcripts |
| Complete frames | `fullframe/` | Butterscotch game-loop checkpoint, rendering/audio platform, QEMU capture and RTL replay |
| Hardware calibration | `calibration.py`, `calibration/` | One SDK ELF with normal hardware entry and separate bare RTL entry; asset-free numerical/renderer probes, QEMU oracles and passive pipeline counters |
| Experimental Pico8 runtime | `pico8/` | Independent cart snapshot, deterministic RV32 checkpoint, indexed pixels/palette/PCM oracles and os25 replay; shipped os20 remains outside scope |

The repository name describes its hardware target. Its original validated
baseline supports Butterscotch with two games; `pico8/` adds an experimental
runtime workload on the same os25 platform. This is not yet a generic plugin API: another os25
application needs a firmware entry point/linker map, deterministic capture route,
checkpoint restore and independent output oracles. It can share the existing
CPU/memory infrastructure. A core using different CPU/cache/bus configuration
also needs a separately pinned platform adapter and its own validation.

Keep game-specific hooks with the workload until a second adapter demonstrates
which interfaces should be shared. Preserve the current baseline when adding
one; do not silently change its manifests or reference captures.

The game-port repository can record this repository's commit in a small JSON
dependency reference. Keep the harness as a sibling checkout rather than copying
private state into the game repo or building against the active port sources.

All dependencies retain their upstream licenses in private input copies. No
vendor RTL, SDK archives, game assets, bytecode or checkpoints are tracked here.
Extraction provenance is Butterscotch commit `88008f7` and skill commit `6328cff`.
