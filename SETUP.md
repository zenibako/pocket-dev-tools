# Local setup

Use Python 3.10+, Git, Docker/Colima, Clang, SDL2 and pkg-config. The Dockerfiles
provide the RV32 GCC, Verilator, Java/sbt and QEMU toolchains. All commands below
run from this repository root. Nothing deploys to a Pocket.

## Import an existing private snapshot

This is the shortest path for the validated Undertale/Deltarune baseline:

```sh
python3 bootstrap.py --from-harness /absolute/path/to/private/harness
python3 run.py verify
python3 capture.py all
python3 run.py all --jobs 4
```

The importer requires the same `input-manifest.json`, verifies all 1,631 frozen
files and 1,621 CPU source files, and imports private event captures if supplied.
It copies only the locked inputs and CPU sources, skipping Git metadata and
tool caches. It imports the known generated CPU netlist when available; a
different netlist is rejected. Otherwise `run.py all` generates it using the
pinned OS configuration and patches. It does not download game data.

To retain an existing private build/checkpoint matrix, add `--with-evidence`.
That explicitly copies `build/` as well, rebases internal asset links and rejects
links escaping the source harness. Run `python3 fullframe/report.py` afterward;
imported results remain historical until replayed. A changed harness source,
binary or capture can invalidate them. Do not edit hashes to suppress failures.

Imports require absent destination `inputs/`, `captures/` and, when requested,
`build/`. An invalid import is rejected before installing those directories.
Use a fresh checkout for a second snapshot; the tool does not overwrite one.

## Assemble from local dependency roots

An existing harness bundle is optional. Supply these exact source revisions:

| Dependency | Repository | Revision |
| --- | --- | --- |
| Butterscotch Pocket runner | `https://github.com/zenibako/Butterscotch.git` | `f1d8542e711b8c6a54ec735143b5e39d50678c4d` |
| openfpgaOS | `https://github.com/openfpgaOS/openfpgaOS.git` | `8318f25066b0b75d2e34081919dfc337ac6abf73` |
| openfpgaSDK | `https://github.com/openfpgaOS/openfpgaSDK.git` | `7882a0db06dd3a0324d2a2fe002972bd336444d9` |
| VexiiRiscv | `https://github.com/SpinalHDL/VexiiRiscv.git` | `580b76c3868512c8316bb7a3d3add81cad49a0dc` |
| SpinalHDL, CPU `ext/SpinalHDL` | `https://github.com/SpinalHDL/SpinalHDL.git` | `6f8510cdbb8ad7b8bcc0f6d58395669c4c4d7e2d` |
| rvls, CPU `ext/rvls` | `https://github.com/SpinalHDL/rvls.git` | `94f850e5f7c9a36e5aceb3810d658fffae55b497` |

Prepare independent clones at these revisions. Populate only the named CPU
submodules; the manifest verifies file contents rather than trusting a branch
name. The importer accepts the pinned upstream CPU files or their recorded OS
patches. CPU generation applies the patches only inside the imported copy.

```sh
python3 bootstrap.py \
    --butterscotch /absolute/path/to/pinned/Butterscotch \
    --os /absolute/path/to/pinned/openfpgaOS \
    --sdk /absolute/path/to/pinned/openfpgaSDK/src/sdk \
    --cpu /absolute/path/to/pinned/VexiiRiscv \
    --private-inputs /absolute/path/to/private/inputs
python3 run.py verify
python3 capture.py all
python3 run.py all --jobs 4
```

`--private-inputs` is optional when the source roots already contain every
hash-matching file. It provides missing or differing files under the same layout
as `inputs/`: `butterscotch/...`, `sdk/...`, `os/...`. This includes user-owned
game assets in `butterscotch/src/openfpga/` and `games/deltarune/`, and the
RV32 musl headers/archives in `sdk/musl/`. The SDK Git revision alone does not
supply built musl archives or proprietary assets. The frozen hashes identify
the precise baseline; raw purchased games require the port's asset preparation
before import. This tool does not implement that conversion or publish assets.

Optionally add `--captures /absolute/path/to/private/captures`. Otherwise
`capture.py all` builds observing host runners and generates the event fixtures.
It also creates source inventory consumed by the full-frame build. Do not skip
it on a clean build even if event captures were imported.

## Complete frames

After the base harness passes, follow [fullframe/README.md](fullframe/README.md)
to build the QEMU image, build both placements, capture each twice, prepare,
replay with quiet/scanout traffic and reject the bad-state oracles. Run
`python3 fullframe/report.py` for the complete eight-configuration matrix.

The launchers use `build/docker-config` and this user's Colima socket by default.
For another daemon set `HARNESS_DOCKER_HOST`, for example:

```sh
HARNESS_DOCKER_HOST=unix:///var/run/docker.sock python3 run.py all --jobs 4
```

Only the harness root is mounted at `/work`. Results are simulated CPU/memory
measurements; physical SD, display, GPU execution and hardware audio require
separate device testing.
