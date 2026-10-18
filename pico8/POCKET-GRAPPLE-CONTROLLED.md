# Celeste 2 movement and grapple capture — 2026-10-18

This extends [detailed capture and controlled runs](POCKET-DETAILED-CONTROLLED.md) after the physical stationary captures showed that their workload did not reproduce moving gameplay stalls. No optimization is promoted by this change.

The [physical Pocket results](POCKET-GRAPPLE-RESULTS-20261018.md) now compare repeated moving Trailhead and Moss runs and identify the grapple throw as the recurring stall window.

## Install and run

The combined ZIP contains both **PICO-8 capture baseline** and **PICO-8 capture palette**:

`experiments/pico8-sources/celeste-grapple-20261018-r1/pico8pocket-capture-grapple-ab.zip`

SHA-256: `97e2c55433c9eee1f9abf75eb8a714f779b930eee02cb40dc06c7e23d0d5625f`.

Individual archives in the same directory: `pico8pocket-capbase.zip` and `pico8pocket-capleaf.zip`.

Extract at the SD root and replace the previous capture files. The core names stay the same. Load the supported Celeste 2 cart, press Select for the in-core menu, leave R DETAIL ON, and press the L shoulder button for AUTO. You can start from the title screen or any scene.

ARM stands still for 100 logical warmup frames. REC then measures 300 frames of movement: running, jumping, two opening grapple points, four further jump/grapple loops on a safe platform, and a settled endpoint. Native observation verifies six throws, six successful attachments, six releases, a 43-pixel pull and zero deaths. These bounded loops do not traverse the entire level or cover transitions and death/respawn stalls.

The journal labels the new workload `trailhead-grapple-v1`; prior `trailhead-still-v1` records remain distinct. Moss Moss still uses `moss-seed7-v1`. Both routes draw every frame and stop by logical frame count. They are different workloads from manual adaptive gameplay captures.

The benchmark uses the existing fresh seeded VM, keeps the original game paused, disables benchmark cart persistence, overrides mid-frame gameplay input, and restores the original game on completion or cancellation. Select cancels. The completion screen remains sticky: release all buttons, wait at least one second, then press Select again.

Collect three AUTO runs per core/game with matched audio/display settings and DETAIL ON. Matching OFF repeats can assess enabled collection cost. Exit through the Analogue menu before retrieving `/Saves/pico8/common/p8pcapbase.bench` and `/Saves/pico8/common/p8pcapleaf.bench`. Reports append to existing compatible journals; no carts/settings/saves/report payloads are bundled.

## Verification

Both variants pass 31 native test commands each: ten existing suites, the optional real-cart grapple oracle, and application modes 0–19. These cover normal/manual capture, controlled ON/OFF, physical-input interference, cancellation, native-state interruption, setup/runtime/seed errors, tampered initial/final scenes, original-runtime isolation, and final-boundary cancellation in both games.

The new route is tested red/green against the stationary implementation. A separate export regression catches incorrect Moss field labels for the new Celeste ID. ASan/UBSan with production longjmp passes the real-cart oracle and focused application completion/OFF/Moss/final-cancellation cases; process-lifetime leaks and known legacy signed fixed-point shift checks are excluded. An isolated mutation removing the grapple button is rejected by the real-cart success checks. Independent source review found no findings and compared all 400 masks to the discovery fixture.

Independent input-file playback, bypassing the production route generator, repeats both variants three times with per-frame debug observations enabled/disabled. All runs reach the same scene and channel hashes; query-disabled runs observe only the two boundaries. The measured route does not depend on per-frame Lua instrumentation. The Pocket application retains boundary-only queries; its only new per-frame work is bounded mask selection.

Three repeated raw-channel captures per variant/detail mode in **both games** compare all 300 measured frames byte-for-byte: pixels, screen palettes and fixed-rate test PCM. All 12 runs per game agree; corrupted-pixel negative controls are rejected. Fixed PCM correctness is separate from live Pocket audio scheduling. These collectors perform file I/O and supply correctness evidence, not performance timings.

Celeste inputs: final Lua seed `5eed1234`, 100 warmup + 300 measured frames, indices 100–399, input FNV32 `941f4bfd`. Initial world vector `3,0,1,79,12,152,0`; final `3,0,1,79,205,120,0`. Measured-channel FNV32: pixels `2d05137f`, palette `1ef89385`, fixed PCM `292bb6e1`; final framebuffer `4a1e47da`.

Moss input FNV32 remains `98d32619`; final scene and pixel/palette/fixed-PCM hashes match the prior route reference. Detail timing, audio algorithm, palette optimization, VM patch policy and persistence code are unchanged.

## Production packages

| Variant | Signed source | ELF SHA-256 | BRAM / 14336 bytes |
| --- | --- | --- | ---: |
| Baseline | `69219a101bd3984a6d5cc1650b4d2b6858a11d5a` | `a81a1c2bbad041193d62cadc38ea2fd5a72bda2d660c64819925bde3be9d41d2` | 14182 |
| Palette | `94a388f0b529d1c2eca65a2cc55bd8d713951a1d` | `6125bba795fa79bdc68568b957d9699a99b2a9dab85f6b324f7e4332890495d8` | 14322 |

Both source commits have verified GPG signatures. Production links, APF validation, short filename/slot bindings, ZIP integrity, exact embedded source IDs and ELF bytes pass. The exact pinned kernel filename-resolution host test rejects the historical long-name package and accepts both new cores. All 531 dependency files match the prior independently reproduced dependency copies. FPGA/OS/loader bytes match the previous package. BRAM sizes are unchanged; relocation/code bytes differ, so older timing/layout evidence is not substituted for measurements of these ELFs.

Private scripts, traces, source review, raw captures, sanitizer/mutation evidence, manifests and build logs are under `experiments/pico8-sources/celeste-grapple-20261018-r1/`. Existing isolated source worktrees were reused; earlier signed commits and delivery archives remain preserved. The active Pico8Pocket checkout, original SDK/OS sources and SD card were not modified. No push, PR or deployment was performed. Physical behavior, detailed timing and live audio remain for the user's Pocket tests.
