---
name: pocket-release
description: Use when preparing or reviewing Analogue Pocket releases, distribution assets, plugin icons, dependency updates, drafts or publication across Pocket ports.
---

# Shared Pocket release workflow

Canonical owner: <https://github.com/zenibako/pocket-dev-tools> (formerly
`pocket-harness`). Resolve this file's real path and read
[the release contract](../../../docs/RELEASING.md) from that checkout.
Read the consumer's local release skill and guide as well: they own commands,
asset inventories, runtime pins, supported games and hardware acceptance.

## Candidate

- Establish the authorized scope, project, intended version and full source
  commit. Preserve unrelated work; use clean isolated source for packaging.
- Preserve matched SDK/API/runtime/loader/bitstream pins and hashes unless a
  reviewed dependency update is explicitly in scope. Hashes identify bytes;
  changing hashes does not validate compatibility.
- Run the project's required tests and complete distribution CI on the exact
  candidate. Include core, plugin/native/WASI tools where applicable, source,
  licenses, provenance and checksums. Icon-only changes still ship complete
  releases. Never use a tools-only latest release.
- Inspect the actual archives, source identities, runtime bytes and checksums.
  Exclude purchased inputs, converted game packs, saves, captures and private
  logs; preserve legitimate project-owned fixtures and licensed source.
- Record desktop/simulation checks separately from physical Pocket launch,
  controls/audio, progress saves and applicable Memories/sleep checks. Keep
  unperformed checks explicit; CI is not hardware proof.

## Plugin presentation and delivery

Inspect every manifest `logo_url`, including embedded data URIs. For the
Pocket Sync v7.1.1 compact-row layout, use a 40×40 PNG export retaining the
original artwork/transparency; this is a client workaround, not a schema limit.
Keep generators and embedded/file copies consistent. The full Plugins screen
uses separate sizing, so check both views. Resolve the actual published URL:
a local change is not a delivered fix. Details and sources are in the contract.

## Draft and publish

Use the local project's workflow and version rules. Obtain explicit version/tag
and release authorization, recognizing authorization already given in the
session. Draft approval alone does not authorize stable publication. Inspect
complete draft assets before an authorized publication. Preserve published
assets/checksums; deliver corrections in the next authorized complete release.
After publication verify visibility, exact tag/commit, latest-release routing,
asset set/hashes and plugin logo bytes/dimensions. Inspect uncertain outcomes
before retrying; never overwrite tags, force history or mask failed checks.

Report candidate/PR/release links, checks and remaining device work. Respect the
user's authorship rules for external notes/comments. This skill does not grant
permission to merge, publish, change pins or write an SD card.
