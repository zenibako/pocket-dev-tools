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

The repository name describes its hardware target. It currently supports one
runner, with two games. This is not yet a generic plugin API: another os25
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

The `benchmarks/` Python package supplies an application-independent evidence
envelope and archival transfer CLI. Its format adapters consume reports rather
than execute applications. Importing VVVVVV host or device evidence does not add
a VVVVVV CPU/replay adapter; importing PICO-8 device summaries does not validate
the os20 platform. Native source bytes, declared configuration, reported checks
and timing domains stay explicit. See `benchmarks/README.md` for the transfer
workflow and remaining device-side integrations.

All dependencies retain their upstream licenses in private input copies. No
vendor RTL, SDK archives, game assets, bytecode or checkpoints are tracked here.
Extraction provenance is Butterscotch commit `88008f7` and skill commit `6328cff`.
