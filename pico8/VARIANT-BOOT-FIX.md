# Palette A/B package boot filename fix

The original palette A/B ZIP has a packaging defect: its ELF and INI basenames
are 26 ASCII bytes, but the pinned Pocket runtime's file-slot registry stores
only 23 bytes plus a terminator. Both names truncate to the same string.
The boot probe suppresses the ELF as a duplicate of the INI, and the full
`ELF=` name cannot resolve. Generated settings and save names also exceed the
runtime limit. Matching names across the ZIP, INI and JSON was insufficient.

This is confirmed against the exact runtime source pin
`a58aacd940c1b433c030b97f8207d2c7e03307c8`:

- `kernel/syscall.c:406` defines `FILE_SLOT_NAME_MAX` as 24.
- `dir_probe_slots` uses that bounded buffer and suppresses duplicate names.
- `targets/pocket/file.c:943` limits the copied basename to `name_max - 1`.
- `kernel/main.c:211` resolves the full configured ELF name through that registry.

The packaging fix is signed source commit `1b8a3ac`. It uses the shorter
`p8p<SUFFIX>` asset stem and rejects variants whose longest `_0.sav` basename
would exceed 23 bytes. For both supplied variants, ELF/INI/CFG names are now
18 bytes and save names are 20 bytes. Core identifiers and descriptions stay
the same. Updated copies of the former APF instance JSON names are included
for already installed test cores; slot 0's APF instance is not part of the
runtime's 1–31 file-slot probe.

## Corrected Pocket package

Use the new private artifact:

`experiments/pico8-sources/variant-boot-fix-20261017-r1/pico8pocket-palette-leaf-ab-fixed.zip`

SHA-256:
`e606e0a931d553cf106b4018e5700279cd538106fe35faa55d6d92a8ab63adce`

Extract it over the previous A/B test bundle at the SD root, replacing its
configuration JSONs. Fully close and reopen either test core. The core entries
remain **PICO-8 accepted audio baseline** and **PICO-8 isolated palette test**.
No original core files, cartridges, settings or saves are included. Existing
PICO-8 cart files are used as before.

The application ELFs, os20 bitstreams, OS and loaders are byte-identical to the
previous package. Only generated variant names and their bindings change, so
[the existing performance results](PALETTE-LEAF-OS20.md) still apply. The palette
candidate remains experimental. Test normal gameplay with diagnostics hidden
first because profiling disables the no-op `pal()` path.

## Verification

The regression tests fail against the old packager for the supplied suffixes,
the maximum supported name, and failure to reject overlong names. All three
tests pass with the fix. They check actual generated ZIP bindings, INI lookup,
ELF payload identity, unique settings/save names, compatibility JSON equality,
and the name-length boundary.

An additional ASan/UBSan host test extracts the exact pinned kernel's registry,
probe and resolver functions. With modeled HAL filename delivery, both old
package instances reproduce the missing-ELF lookup and duplicate suppression;
both corrected instances resolve ELF slot 3 and every settings/save binding.
This validates name resolution without claiming a physical Pocket boot.

The corrected ZIP is independently checked for integrity, exact ELF and pinned
runtime bytes, consistent metadata, safe paths, distinct core/save references
and absence of cartridges or saved data. No SD deployment or runtime/SDK change
was performed. Private evidence, exact pinned source hashes, red/green logs,
source commit and package manifests are preserved under
`experiments/pico8-sources/variant-boot-fix-20261017-r1`.
