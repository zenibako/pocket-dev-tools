# Shared Pocket release contract

The canonical release skill is [pocket-release](../.agents/skills/pocket-release/SKILL.md).
This repository owns common release checks; each port owns its build commands,
version rules, package inventory and physical acceptance criteria. This follows
[the existing workload boundary](../ARCHITECTURE.md) and the
[consumer routing pattern](superpowers/plans/2026-10-27-consumer-skill-wiring.md).
No common CI runner or game build system is introduced.

## Consumer authorities

| Project | Local release authority |
| --- | --- |
| Butterscotch | `.agents/skills/pocket-release/SKILL.md`, `src/openfpga/docs/BUILD.md`, `src/openfpga/release/core.lock.json` |
| Pico8Pocket | `.agents/skills/pico8pocket-release/SKILL.md`, `docs/RELEASING.md`, `scripts/fetch-deps.sh` |
| VVVVVV | `.agents/skills/pocket-release/SKILL.md`, `openfpga/release/README.md`, `openfpga/release/runtime.lock.json` |

Use the actual checkout's workflows and pins, not commands copied from another
port. Stronger local requirements remain in force. Benchmark collection/replay
can supply evidence but does not replace project correctness or hardware gates.

## Resolve the shared checkout

Use the root explicitly established in the session, then `POCKET_DEV_TOOLS_ROOT`,
then legacy `POCKET_HARNESS_ROOT`. If explicit roots conflict, resolve the
conflict before selecting one. A sibling `pocket-dev-tools` or `pocket-harness`
is only a candidate. Verify `.agents/skills/pocket-release/SKILL.md` and
`docs/RELEASING.md`, confirm Git identity against the canonical repository
(`zenibako/pocket-dev-tools`, or its former name), and record the full commit.
Resolve the skill's canonical path before opening relative references.
If missing, report the dependency and continue applicable local checks; do not
claim the shared checklist passed, invent a replacement or copy its body.
No cross-repository skill symlinks. Within-repository `.claude/skills` aliases
remain supported. Existing checkout directory names and `POCKET_HARNESS_ROOT`
do not need to change after the repository rename.

## Test build versions

Device test builds of the next release report `<next>-rc.<N>` in core.json so
Pocket tools can tell them from the published release. Every port gets that
value from [`pocket_version.py`](../pocket_version.py) in this checkout, called
by its `make package-test`, so the heuristic lives in one place:

- `N` counts the commits since the newest `vX.Y.Z` tag merged into HEAD.
- `<next>` is `NEXT_VERSION` when set, else the committed core.json version when
  a release prep commit already bumped it past that tag (ports pass
  `--core-json`), else the tag with its patch number bumped.
- The result must fit core.json's 31-character `metadata.version`.
- A missing tag means `git fetch --tags`, or `git fetch --unshallow --tags` in a
  shallow clone.

Ports find this checkout with the order in *Resolve the shared checkout* above
and fail clearly when it is missing. Each port still validates `CORE_VERSION`
before deleting or writing its package, since it can be passed by hand.
Release builds keep the plain `X.Y.Z` from the release tag.

## Plugin icon verification

The compact Pocket Sync v7.1.1 plugin row renders natural image dimensions;
the full Plugins screen separately sets 120×120. A 40×40 export avoids a huge
compact row. Recheck the consumer implementation when it changes:

- [Compact component](https://github.com/neil-morrison44/pocket-sync/blob/40f09811a9e7631f720b7aaa206ba686056d5449/src/components/plugins/miniItem/index.tsx)
- [Compact CSS](https://github.com/neil-morrison44/pocket-sync/blob/40f09811a9e7631f720b7aaa206ba686056d5449/src/components/plugins/miniItem/index.css)
- [Full Plugins CSS](https://github.com/neil-morrison44/pocket-sync/blob/40f09811a9e7631f720b7aaa206ba686056d5449/src/components/plugins/index.css)

This is a renderer workaround, not an official image-size constraint. Preserve
original artwork and licenses; resize only plugin exports, not core binary
icons, platform banners or game assets. Verify intrinsic size, alpha, embedded
PNG/file agreement and generator repeatability. Check the actual image in both
layouts and record fixture versus live-application evidence explicitly.

Butterscotch and VVVVVV manifests reference latest-release `plugin_icon.png`;
Pico8Pocket embeds its PNG in root `plugin.json`, matching
`assets/branding/plugin-thumbnail.png`. Download/resolve the published manifest
and image after release, following redirects. Local fixes do not change
installed or published assets. Investigate stale URLs/cache before resizing
again. Never replace published release bytes to make a URL appear fixed.

## Review evidence

Record the source commit, complete CI link, artifact inventory and verified
hashes, exact runtime identity, installation/Memory compatibility, known issues
and performed/unperformed hardware checks. Keep raw owned game data and device
logs private; publish only sanitized findings. A repository being public does
not make ignored local inputs or historical evidence suitable for publication.
