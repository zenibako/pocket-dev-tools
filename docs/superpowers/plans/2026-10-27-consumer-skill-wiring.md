# Pocket consumer skill wiring

> **For agentic workers:** Use the skill-creator and writing-skills workflow for the reference skills, with independent consumer tasks and a final read-only review.

**Goal:** Make the shared Pocket benchmark workflow discoverable in the existing
consumer projects and remove the stale skill routing identified by the audit.

**Architecture:** Keep the full workflow in pocket-harness. Each consumer gets a
short physical local `pocket-benchmarking` routing skill. Resolve the canonical
harness skill before reading its relative references. Bridge `.agents/skills`
and `.claude/skills` within each repository, never across repositories.

**Spec:** `docs/skills/2026-10-27-pocket-benchmarking-audit.md`, followed by the
user's explicit request to wire consumers and fix stale guidance.

## Constraints

- Scope is documentation, local skill routing and discovery. No game/runtime,
  configuration identifiers, pins, package allowlists or SD writes change.
- Respect existing dirty files/submodules; stage only this task's explicit paths.
- Use an explicitly established `POCKET_HARNESS_ROOT` or session-provided path.
  A sibling `pocket-harness` is a candidate only; verify its canonical skill and
  collector before use. Missing checkout means report the missing dependency.
- Do not copy the shared workflow or create cross-repository skill symlinks.
- Consumers retain their workload/build/semantic/release/hardware gates.
- Preserve os20/os25 and host/simulation/device distinctions.
- Local conventional commits are GPG signed; no branch/bookmark moves, push,
  merge, publication or global skill installation.
- User's latest cross-project request authorizes consumer documentation changes
  beyond the harness's default repository-only scope.

## Tasks

- [x] Installer: add local router/discovery bridge and current root routing;
  replace four historical SDK-era skill bodies with narrow archival redirects.
  Preserve existing skill names and resolve current owners from session context.
- [x] Pico8Pocket: add router/discovery bridge and root routing, reconcile current
  hardware/runtime guidance with pins, label historical os25 experiments clearly.
- [x] Butterscotch: add router/discovery bridge, connect existing owner skills to
  it and add focused root guidance without duplicating the shared workflow.
- [x] VVVVVV: add the same routing/discovery files in both active worktrees;
  retain revision-specific workload docs, native correctness and runtime identity.
- [x] openfpgaOS: bridge current root instructions into AGENTS, add native-hardware
  scoped router and local skill discovery without touching the dirty submodule.
- [x] Validate physical skill bodies and both catalogs using Harnessmith for
  Claude/Codex; resolve local links from both roots; independently test routing,
  missing-harness handling and corrected project ownership/hardware guidance.
- [x] Update audit with remediation evidence and remaining real exporter/platform
  gaps. Commit each repository/worktree's authorized files and verify signatures.

## Review and evidence

The existing audit is the baseline: missing `.agents` discovery, no VVVVVV/OS
skills, SDK-era installer routing, and conflicting Pico8 hardware facts. Validate
actual catalogs and fresh-agent application of the new references, not textual
assertions that prescribed prose exists. Record exact tested outcomes and don't
claim live host auto-selection or hardware verification from static audits.

Consumer tasks have disjoint files. The two VVVVVV worktrees share Git objects
but have different HEADs; edits and commits are sequential, and no checkout or
branch state is moved. Review the complete portfolio before committing.

## Completed evidence

Consumer signatures and clean working states were verified, preserving the OS
submodule modification. Two independent read-only reviews found no important
defects. Portfolio static results: 66 checks, 116 local links; private reports
are in `build/skill-wiring/`. The audit records all six consumer commits.
