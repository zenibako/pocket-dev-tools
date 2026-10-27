# Pocket benchmarking skill: consumer audit

Audited 2026-10-27. This is a source/discovery audit, not a new device run or
hardware qualification. Consumer repositories, global skill installations and
SD cards were not modified. Findings describe the inspected checkouts.

## Shared entry point and ownership

The canonical new skill is
[pocket-benchmarking](../../.agents/skills/pocket-benchmarking/SKILL.md).
It routes benchmark-core planning and evidence collection to the maintained
[collector guide](../../benchmarks/README.md). The existing
[os25-harness](../../.agents/skills/os25-harness/SKILL.md) retains execution,
capture/replay and profiling ownership. The skill adds no exporters or RTL
application support and duplicates neither the CLI nor its schema.

`pocket-harness/.agents/skills` is the canonical collection. Its new
`.claude/skills -> ../.agents/skills` bridge exposes the same files within this
repository; no second skill body is maintained. `AGENTS.md` also routes both
skills; `CLAUDE.md` already links to that instruction file.

Adding the skill here does not make it automatically available in sibling
repositories. During a consumer task, establish the actual harness checkout path,
open the canonical SKILL.md there, and run the collector from that checkout.
For repeatable integration, add a short reference in the consumer's existing
performance/verification skill or root instructions in a separately scoped change.
Avoid assuming this machine's absolute path or a particular sibling directory.

The consumer routing message can be as short as: use the shared
`pocket-benchmarking` skill from the established harness checkout for evidence
collection/comparison; retain this project's workload, build, semantic and release
checks. A reference is not proof that a host discovered/selected a skill.

## Findings by priority

1. **High: historical installer skills can route work into obsolete source.**
   `butterscotch-pocket` root instructions say it is the Go prep/plugin/release
   repository, and its old SDK/application trees are historical. Nevertheless,
   its `undertale-pocket-build`, `-perf`, `-verify` and platform-note skills still
   describe the old `src/undertale` layout. Follow the current root instructions;
   runner work belongs in `Butterscotch`. Archive or replace the old skills with
   small redirects in a consumer maintenance change.
2. **High: Pico8Pocket's performance skill has stale hardware values.** Its
   opening hardware paragraph says about 100 MHz and 8/32 KB caches, while current
   architecture/pins describe os20 dual issue at 90 MHz with 32/64 KiB caches.
   Read the effective pinned runtime/configuration before filling run metadata.
   Reconcile that skill separately; do not change intentional runtime IDs to
   match outdated prose.
3. **Medium: consumer discovery is incomplete.** Butterscotch, its installer and
   Pico8Pocket have only `.claude/skills`; they have no `.agents/skills` bridge.
   Neither VVVVVV checkout nor openfpgaOS has a repository skill collection.
   A successful Claude/Codex static audit does not install a skill or make a
   sibling checkout's skill visible. Add explicit routing before broadening
   discovery; verify the host's actual selected catalog after such wiring.
4. **Medium: result adapters and dedicated cores do not supply exporters.**
   VVVVVV has a dedicated benchmark core but keeps benchmark writes volatile.
   Pico8Pocket's variant packaging isolates program/settings/save filenames but
   does not create an automated suite or durable results export. Both currently
   use screenshot-backed summaries in this collector. Butterscotch focused
   diagnostics use separate entries/files under the normal core.
5. **Medium: deployed os20 ports are outside the validated os25 replay scope.**
   Both inspected VVVVVV checkouts pin os20. Pico8Pocket also uses os20. The
   standalone harness's validated workloads are Butterscotch on its pinned
   os25 model. Historical PICO-8 experiments and neighboring SM64 models are
   separate evidence, not current standalone support.
6. **Validation gap: focused seed equality is not a literal route-seed gate.**
   The importer checks the log's seed against declared metadata; it does not
   independently require 7. The current focused route requires seed 7. The
   collector guide now distinguishes these checks. A future route-registry gate
   can enforce that invariant; this skill addition does not change parser code.

## How each project should consume the skill

| Project | Existing owner | Shared-skill handoff | Remaining application work |
| --- | --- | --- | --- |
| Butterscotch: Undertale/Deltarune | `butterscotch-pocket-perf`, `-verify`, `-build` | Build/run the project-owned route; collect standard/focused `.sav` via `butterscotch-device`, or archive a selected `harness-revision` case | Dedicated benchmark-core packaging; automatic package/run manifests; preserve independent pixels/audio and lifecycle gates |
| butterscotch-pocket installer | Root instructions, Go prep/plugin and pinned release pipeline | Record the exact pinned source/package/runtime, then collect that package's evidence through the harness | Fix archival skill routing; benchmark ZIPs remain separate from normal release allowlists |
| VVVVVV | `openfpga/README.md`, benchmark source and smoke/renderer tests; no local skills | `BENCH=1` builds `zenibako.vvvvvvbench`; complete host sweep uses `vvvvvv-host`; Pocket pages use `device-summary` with originals | Durable result export, automatic manifests and separately validated target replay |
| Pico8Pocket | `pico8pocket-performance`, `-compat`, `-release` | Build/test the named cart/core; use `device-summary`, recording cart hash, logical/visible rates, render skipping and audio | Reconcile stale hardware prose; durable exporter and os20/PICO-8 replay adapter |
| openfpgaOS / SDK | `CLAUDE.md`, per-variant configuration and RTL/fit/runtime checks | Use the skill as an evidence checklist for actual game-consumer runs; keep OS-only results in native OS tooling | Collector has no `openfpgaos` project or generic OS result adapter; do not relabel hardware tests as game runs |

For every handoff, resolve the canonical harness path rather than copying skill
text. Keep project build/release/compatibility owners responsible for their
existing gates. Collection never grants deployment, pin changes or publication.

## Concrete evidence and pitfalls

**Butterscotch.** The [performance skill](../../../Butterscotch/.claude/skills/butterscotch-pocket-perf/SKILL.md)
and its [focused reference](../../../Butterscotch/.claude/skills/butterscotch-pocket-perf/references/focused-benchmarks.md)
already select concrete routes and require report identity/sample checks.
The [focused diagnostic guide](../../../Butterscotch/src/openfpga/docs/2026-10-18-focused-pocket-benchmark.md)
documents the five modes and Quit-to-flush procedure. Its saved report uses
`FOCUS PASS/FAIL` plus the end marker; post-dump UI success text need not appear
in the file. The new skill routes these logs into the collector without taking
over workload creation or correctness verification.

**Installer.** [Current root guidance](../../../butterscotch-pocket/CLAUDE.md)
and the [approved repurposing design](../../../butterscotch-pocket/docs/superpowers/specs/2026-10-18-install-entrypoint-design.md)
override its [historical build skill](../../../butterscotch-pocket/.claude/skills/undertale-pocket-build/SKILL.md).
The [release guide](../../../butterscotch-pocket/docs/BUILD.md) excludes benchmark
instances, purchased inputs, saves, logs and device metadata from public packages.
Do not import private run bundles into a release allowlist.

**Pico8Pocket.** Compare the [performance skill](../../../pico8pocket/.claude/skills/pico8pocket-performance/SKILL.md)
with [current architecture](../../../pico8pocket/docs/architecture.md) before
selecting a timing model. The [variant script](../../../pico8pocket/scripts/variant-core.sh)
supports isolated A/B filenames while sharing OS/pad assets; a different shared
`os.bin` must not overwrite the other core's runtime. Hashes and effective settings
belong in metadata; package/core IDs alone are not hardware identity.

**VVVVVV.** The [performance checkout guide](../../../vvvvvv-perf/openfpga/README.md)
contains focused/exhaustive presets; inspect the selected revision rather than
assuming the plugin checkout contains all performance work. `SWEEP_VIEW` in
`openfpga/src/pocket_final_sweep.cpp` is guarded by `OF_PC`; `SWEEP_RESULT` comes
from `openfpga/tests/final_sweep_smoke.cpp`. Both are host microseconds.
`openfpga/sdl3/savefs.c` keeps benchmark writes volatile. A summary peak can span
all viewports and need not occur in the worst-average viewport.

**Runtime.** [os20.cfg](../../../openfpgaOS/src/fpga/vendor/vexriscv/configs/os20.cfg)
and [os25.cfg](../../../openfpgaOS/src/fpga/vendor/vexriscv/configs/os25.cfg) are
different CPU/cache/clock configurations. [OS instructions](../../../openfpgaOS/CLAUDE.md)
also separate the default RTL regression set from GPU/scanout/system tests.
Neither importing a report nor replaying frames establishes fit, timing closure,
physical storage, presentation, audio or board behavior.

## Audit scope and revisions

| Checkout | Inspected revision/state |
| --- | --- |
| pocket-harness | `c0775f9` before this skill addition |
| Butterscotch | `a90891d5`, clean |
| butterscotch-pocket | `af0600a`, clean |
| Pico8Pocket | `fec7ce5`, clean |
| VVVVVV perf | `2881be8e9bc8bbb5864e948b3bf39252daca4de0`, clean |
| VVVVVV plugin | `a234dc1124738cbf52d08bc79299baf024059810`, clean |
| openfpgaOS | `902a8adc11309c50c8954af2864ddf893c8b1b0c`, pre-existing modified VexiiRiscv submodule; untouched |
| Harnessmith | `07f4c4749063ea7bd079870e6b9923635e0ffad6`, clean |

These paths/revisions are audit observations, not future dependency pins. The
existing harness input manifest and CPU lock were not changed.

## Validation method and limits

A fresh-context, no-new-skill baseline used the existing docs/CLI to answer a
mixed VVVVVV host/device comparison request plus Deltarune and Pico8 transfer
variants. It correctly rejected cross-domain speedup and import-as-correctness
claims. No behavior failure or improvement is claimed; the new skill provides
discovery and reference routing. The independent forward evaluation used the same
request through the new canonical entry point. It imported two synthetic build
identities from the checked-in report, verified both bundles and compared their
four rows successfully with zero deltas. Checks remained `not_checked` and the
comparison `descriptive_only`; no device or independent-trial claim was made.
The owned temporary directory was removed. That evaluation identified the
Butterscotch-only `inspect` boundary and the seed-validation gap above; the skill
and guide were corrected accordingly.

Harnessmith static audits and catalogs check both Claude and Codex targets.
The `.claude` root bridge is audited separately. Relative documentation links
are checked from both local entry paths. All linked documentation is required
with this checkout: compiling or installing SKILL.md alone does not bundle the
root docs. Cross-repository symlinks can resolve relative links against the wrong
repository; use canonical paths until host resolution is verified.

The system skill-creator validator requires PyYAML, absent from the tested system
and bundled Python environments. Its failure is a missing validation dependency,
not a passing check. Harnessmith provides an independent structural check.
Both new-skill audits passed without warnings, and both catalogs list the two
canonical local skills without duplicate names. All 33 checked documentation
links resolve from their local entry paths. The existing 46 collector regression
tests passed. Raw static reports are private at
`build/skill-audit/2026-10-27-static-final.json` and can be reproduced below.

Static proxy-token estimates are not measured context use; host auto-selection
and post-restart discovery have not been empirically verified. No device run,
firmware build, deployment, consumer remediation or global installation occurred.

To reproduce static audits from the sibling `harnessmith` checkout:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m harnessmith ../pocket-harness/.agents/skills/pocket-benchmarking --target codex --audit --json --fail-on warning
PYTHONDONTWRITEBYTECODE=1 python3 -m harnessmith ../pocket-harness/.agents/skills/pocket-benchmarking --target claude --audit --json --fail-on warning
PYTHONDONTWRITEBYTECODE=1 python3 -m harnessmith catalog ../pocket-harness/.agents/skills --target codex --json --fail-on warning
PYTHONDONTWRITEBYTECODE=1 python3 -m harnessmith catalog ../pocket-harness/.claude/skills --target claude --json --fail-on warning
```
