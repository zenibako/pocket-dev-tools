# Interpreter isolation — os20, 2026-10-19

**The Moss regression disappears in the controlled combined image.** With the
new interpreter and guarded callback in otherwise baseline surroundings, Moss
steady costs 1.680% less quiet / 1.630% less with scanout; Celeste's full grapple
throw costs 15.817% / 15.213% less. This proves a regression-free combination is
possible in these windows. It is a diagnostic binary construction, not yet a
normal source build or a Pocket package.

The ordinary source placement trial remains rejected: moving the scalar
callback into the existing cold section improves Celeste further but leaves
Moss 1.992% / 1.935% slower than baseline. The interpreter's instructions remain
unchanged in that trial. The remaining loss therefore involves interactions
with the surrounding image; changing one cold callback slot is insufficient.

This follows the [explicit callback ABI experiment](SCALAR-CALLBACK-OS20.md)
and [stable-image controls](MOSS-STABLE-IMAGE-OS20.md). Baseline is the accepted
audio/palette revision `db6bced088a69c82c2be0256947e0a5d2794afd2`. Scalar donor is
`1e459bf`; cold-section source is signed `ff1ada5`. All results are simulated
os20 at 90 MHz, with unchanged carts, routes, fixed PCM and final seed
`0x5eed1234`. They are not physical Pocket FPS or whole-game results.

## Results

Mean measured runtime cost including fixed PCM, milliseconds; lower is better.
The [validated CSV](INTERPRETER-ISOLATION-OS20.csv) contains 14 scene/variant/
traffic rows, individual frame changes and exact result/ELF hashes.

| Change | Scene, frames | Baseline quiet | Candidate quiet | Quiet change | Scanout change |
| --- | --- | ---: | ---: | ---: | ---: |
| Interpreter only, baseline surroundings | Moss steady, 180–191 | 48.686 | 47.867 | -1.680% | -1.630% |
| Guard + interpreter, baseline surroundings | Moss steady, 180–191 | 48.686 | 47.867 | -1.680% | -1.630% |
| Guard + interpreter, baseline surroundings | Celeste full throw, 305–306 | 94.453 | 79.514 | -15.817% | -15.213% |
| Guard + interpreter, baseline surroundings | Celeste whole grapple, 304–308 | 68.637 | 61.643 | -10.190% | -9.749% |
| Cold-section source build | Moss steady, 180–191 | 48.686 | 49.655 | +1.992% | +1.935% |
| Cold-section source build | Celeste full throw, 305–306 | 94.453 | 77.405 | -18.049% | -17.825% |
| Cold-section source build | Celeste whole grapple, 304–308 | 68.637 | 60.055 | -12.503% | -12.327% |

Moss's combined-image cycles equal the interpreter-only cycles in every measured
frame, in both traffic modes. The earlier ordinary scalar source build regressed
Moss 1.063% / 1.058%. Its interpreter is beneficial when tested within baseline
surroundings. These comparisons do not provide an additive decomposition of the
full-build loss or identify a particular cache conflict or stall mechanism.

Only these steady/grapple windows were tested in this round; GC, intro and
Trailhead windows remain future checks for a source candidate that passes.

## What changed inside the interpreter

A new unchanged-ELF Moss profile of `1e459bf` records 31,299,894 runtime-step
instructions versus baseline's 31,299,864: just 30 extra. No guard or `callTM`
execution occurs in this measured window. Every function's entry count matches.
The only self-instruction differences are `luaV_execute` -412, `luaV_concat`
+446 and `luaL_len` -4. Concat's difference is one additional nop per call.
These are executed instruction counts, not simulated time shares.

The VM's dynamic load/store opcode counts are identical. Its instruction savings
are 303 jumps and 109 nops. Shrinking formerly inlined callback paths lets two
hot fast-slot guards use a single conditional branch instead of a branch plus
jump. OP_LE and OP_LEN callback outlining accounts for 150 of the 196 removed
static bytes; the remaining 46 are not uniquely attributed to one compiler pass.
Those callback paths themselves do not execute in the Moss window.

A changed OP_RETURN register choice also permits a two-byte shift instruction
instead of a four-byte form, saving 60,152 of 61,498 fewer dynamically encoded
VM instruction bytes. This is encoding evidence, not a count of actual cache
fetches or an attribution of the measured speedup.

## Exact image controls

The 10,528-byte scalar VM fits in the original 10,724-byte BRAM slot at
`0x47ec`; unused tail bytes stay original. Its private 53-word dispatch table
replaces the baseline table at the original SDRAM address. All other ordinary
functions, data and placement stay baseline. The combined variant starts from
the previously validated baseline-plus-guard image, retaining its four-byte
lookup callback retarget and 920-byte helper island.

Relinking original read-only objects with `--emit-relocs` produces metadata ELFs
whose loaded segments are byte-identical to the measured originals. Those
metadata ELFs are not executed. The transplant retargets 128 external calls
(99 AUIPC/JALR, 25 JAL32, four CJAL16) and 22 absolute instruction relocations,
including reused high-base loads. All 53 dispatch targets land on instruction
boundaries. The four compressed calls were initially mislabeled as 32-bit in
a discovery manifest; a range assertion stopped construction before an ELF was
written. Corrected manifests preserve the old versions and verify all encodings.

All private callee clones match outside verified relocation fields; the old
scalarized and new explicit callback conventions have separately verified
seven-word compatibility. Celeste's baseline callees were independently checked
against the Moss baseline. Full-file checks verify each derived ELF differs from
its exact donor only in the declared VM/table regions.

Timing reuses the exact baseline checkpoint and stack, changing only the declared
SDRAM callback/helper/table bytes and BRAM interpreter. The saved resume context
is between frames, outside the VM. Each derived ELF also performs its own two
QEMU captures and full-route output check. Moss's warm SDRAM matches baseline
outside declared regions; unused C-stack contents differ, so the timing control
holds the baseline stack explicitly. Celeste's own warm heap may differ after
guarded calls; its timing likewise starts from the held baseline state. This is
a controlled intervention, not a substitute for device startup behavior.

## Source placement trial and next anchors

The source trial annotates static `callTM` with `noinline` and the existing
`.p8p_vm_cold` section on ELF targets. It does not use GCC's `cold` attribute.
The callback leaves its early 256-byte ordinary-text slot. The VM's complete
opcode/register/width/order sequence remains identical to the scalar donor,
except verified call/data relocation immediates; its dispatch entries match.
Lookup remains the exact baseline body. The callback's two-byte shrink comes
from a compressed call to the nearby guard; its ABI/frame remain unchanged.

This retains the helpful interpreter shape but does not restore the broader
layout. Five hot SDRAM functions have unchanged normalized bodies across
baseline, scalar and cold-section builds while their addresses move:
`api_all_next`, `fastchain`, `luaV_gettable`, `api_foreach`, and `icache_miss`.
They account for 4,629,388 self instructions, 14.79% of measured runtime-step
instructions. These provide concrete anchors for a subsequent linker-order
control. Address movement alone does not establish a hardware cache conflict.

## Verification and delivery status

All five result cases pass repeated QEMU/native output agreement, quiet/scanout
RTL, corrupted-pixel negative controls and memory oracles. Derived images match
per-frame pixel/palette/PCM hashes and pair counts over all 600 Moss or 400
Celeste frames; target raw channels were not collected. The ordinary source
trial additionally matches native raw pixels, palettes, PCM and pair counts.
Final seed, 90 MHz MMIO clock, immutable source cases and prepared image hashes
are validated. Independent review checks ELF scope, relocations, callees and
held warm state. A strict Moss warm-RAM assertion was added after review; all
existing captures satisfy it. Warm-state descriptive metadata was corrected to
name callback/helper changes too; original JSONs are retained and timing data
is unchanged.

Native core/runtime/delegate tests and assertion-enabled syntax checks pass.
All 18 patches reproduce all 62 prepared C/header files. Prior scalar-source
compatibility evidence remains in its report; no new state-format change is
introduced. The optional local-cart acceptance skip and inherited line-hook
limitation remain as documented there. The cold source builds an offline
production ELF: BRAM `0x375a` (166 bytes free), cold section `0x532`. Production
machine-code/layout parity and physical Pocket performance are unverified.

Private evidence root: `experiments/pico8-sources/moss-vm-isolation-20261019-r1/`.
`report.py` validates the CSV from replay logs and exact prepared images.
`profile-scalar/`, `dynamic-comparison.json`, `discovery/`,
`discovery-cold-slot/`, and `discovery-hot-layout/` retain profiling and assembly
proof. `metadata-corrections.json` records descriptive-only corrections.
Source work is confined to the existing private boundary worktree. Active port,
original SDK/OS, SD card and old cases were untouched. No package, push, PR update
or deployment was performed. A normal source build reproducing the successful
controlled layout is still required before hardware delivery.
