# Capture status and persistence diagnostics

The first [Pocket capture build](POCKET-CAPTURE.md) displayed BENCH SAVED,
but the user found no report files after normal Analogue-menu exit, including
a recursive Saves search. They also reported that recording was hard to see
and gameplay presses dismissed the completion menu.

The accidental dismissal is reproduced by the real-app synthetic-input test:
spamming physical A across completion resumes the old menu. The new result
screen stays paused, waits at least one second, observes all buttons released,
and accepts a fresh Select press. A yellow ARM/red REC label is painted in the
spare scanout border, outside the cartridge viewport, once per retained page
and state change. Profiling stays disabled and cartridge pixels are untouched.

## New package

Private A/B ZIP:
`experiments/pico8-sources/capture-persistence-fix-20261018-r1/pico8pocket-capture-diagnostic-ab.zip`

SHA-256: `5711dfc1975e6ee3703d799e867eb30e06486367fcd9c696427c8b0096ece472`

Extract over the existing capture bundle at the SD root, replacing its core,
instance and application files. Entries remain **PICO-8 capture baseline** and
**PICO-8 capture palette**. There are no cartridges, settings, saves or report
payloads in the package. Old packages and evidence remain preserved.

Run **one** capture first: Select, then physical Y. After two seconds ARM changes
to REC for the thirty-second window. Completion holds FPS, mean runtime cost,
write result, FILE BOUND, DT8 entry, before/after SIZE, HW flags and the report
filename on screen. Release the buttons and make a fresh Select press to return
to the in-core menu, then exit normally through the Analogue menu.

Expected new report paths:

- `/Saves/pico8/common/p8pcapbase.bench`
- `/Saves/pico8/common/p8pcapleaf.bench`

If still absent, return a photo of the result screen before dismissing it. It
provides measurements and the missing hardware evidence even without SD output.
Do not repeat the complete matrix until one report persists.

## What changed in storage

Slot8 keeps its address `0x20380000`, capacity `0x40000`, nonvolatile flag and
declaration position. Its name now fits APF's 15-character label limit. The report
has an explicit short filename in both core data and instance JSON; parameters
`0xA0` request missing-buffer initialization and retain the prior restart bit,
while removing slot 0 filename cloning. The first package used `0x84`, cloning
slot 0 and requesting no initialization. These changes correct the declaration
and make the expected common-folder path explicit; they do **not** establish
which hardware condition caused the missing files.

[Analogue's data-slot contract](https://www.analogue.co/developer/docs/openfpga/core-definition-files/data-json)
documents these flags. Initialization fills missing nonvolatile memory; its text
does not promise that this alone repairs file creation. The
[SD folder rules](https://www.analogue.co/developer/docs/openfpga/directories-and-sd-folder-structure)
explain the earlier retrieval ambiguity: Saves mirrors asset paths. The user's
empty recursive search ruled out a simple subfolder oversight in this run.

The app now verifies the boot-discovered report filename resolves to slot 8,
scans the actual datatable, checks the applicable size-commit contract, writes
and closes, reopens and compares all CRAM bytes, then reads settled metadata.
All diagnostics run after measurement while paused. The exact matched OS,
loader and bitstream are retained.

Result codes:

| Code | Meaning |
| --- | --- |
| 0 | CRAM readback and size metadata verified; SD flush remains unverified |
| -5 | Expected report filename is not bound to slot 8 |
| -6 | Slot8 table entry could not be read/found |
| -7 | Full CRAM file readback did not match |
| -8 | Post-close binding, entry or size changed/did not match |
| -9 | Legacy hardware found slot 8 outside fixed entry 8; refused before writing |
| -1 through -4 | Collector, allocation, file I/O or journal rejection |

The prior POSIX path could open a supported CRAM slot independently of a live
host filename. Its successful close confirms only a buffer/size operation, not
SD persistence. Source comments about compacted versus declared table layouts
are inconsistent; a scanned ID may also be stale. Therefore neither a table
match nor same-session readback is presented as proof of an SD transaction.
Actual HW flags and the before/after entry are needed to decide the next step.
No firmware, bitstream or global save-layout fix is asserted.

## Validation and provenance

Signed sources:

- Baseline: `b59770e65f81132bc2642507881f44020467acc5`;
  ELF SHA-256 `60d75b986257faf21579929e1a85dba7b9ad0bf7c409c73de913277888a54bb1`.
- Candidate: `d67bd15986c0b381bc264154f227e4aed985d8b0`;
  ELF SHA-256 `4c96c1b961eb667d70559e923093e4a851cfb33f68a5ed4d0e3dcb5591f7ab1f`.

Both links and APF package validations pass. BRAM now uses 14,176/14,314 bytes,
respectively, versus 14,182/14,322 in the earlier capture build. VM/runtime source
is unchanged, but compiler/layout differences mean old timing numbers must not
be reused for these images. Capture, marker, probe and cold platform-diagnostic
objects match byte-for-byte between the variants. All 531 copied dependency
files and matched OS/FPGA/loader assets retain their original bytes.

Both native core/runtime suites pass; six real-app modes cover normal capture
with button spam, menu/profiler/native-state interruptions, absent report binding
and misplaced legacy entries. Collector, UI and probe unit suites pass ASan/UBSan.
Variant packaging tests check filename limits, aliases, slot order, explicit
report names, initialization and label bounds. A stale-clock release-gate defect
was reproduced and fixed; a fresh post-export clock plus wrap-tested gate is used.
The result UI was rendered and inspected using a native synthetic-clock frame;
its displayed 30 FPS is test data, not Pocket evidence.

The MMIO query sequence follows exact pinned a58aacd `targets/pocket/file.c`.
Preserved `save.c`, `regs.h`, and fit-source 92202ab `core_top.v` are verified
against GitHub Git blob identities. Source presence alone does not prove actual
installed feature bits; the result screen now reports those bits. Direct table
queries are bounded and run outside capture; they do not modify save sizes or
bytes. The actual root cause of missing SD reports remains unconfirmed until
the new Pocket observation. No SD deployment or remote push was performed.

All build, test, negative, source and package evidence remains private under
`experiments/pico8-sources/capture-persistence-fix-20261018-r1`.
