# Accepted-audio palette and selective GC experiments — os20 / 90 MHz

Three independent source experiments use accepted audio revision `9f4cd16` as a common baseline: portable palette fast paths, a shared GC wrapper in BRAM, and GC inlining at the four VM sites. Prior global GC attributes are absent. These follow the [palette compiler investigation](PALETTE-COMPONENTS-OS20.md) and [global GC-policy controls](GC-POLICY-OS20.md).

Mean frame-time changes below are simulated quiet RTL; positive values are slower. The [complete CSV](ACCEPTED-COMBOS-OS20.csv) includes scanout, exact milliseconds, capacity/capped FPS, warm-frame changes and source/ELF identities.

| Window | Audio + palette | Shared BRAM GC | VM-only GC inline |
| --- | ---: | ---: | ---: |
| Celeste tower | -1.175779% | +5.026751% | +0.999373% |
| Celeste Trailhead | +1.566037% | +5.269338% | +1.430330% |
| Moss steady | -2.172080% | +3.195610% | +0.985232% |
| Moss GC | -2.114387% | +2.715019% | +1.583961% |

No candidate passes the requirement that all four quiet and scanout windows avoid regression. Each slows Trailhead. The palette version improves the other three quiet windows, but this does not remove the first-level trade-off. None is promoted.

| Window | Baseline quiet ms | Baseline capped FPS |
| --- | ---: | ---: |
| Celeste tower | 25.838042 | 30.000 |
| Celeste Trailhead | 42.152333 | 23.723 |
| Moss steady | 49.635506 | 20.147 |
| Moss GC | 50.000123 | 20.000 |

## Source changes and production fit

| Variant | Signed source revision | Production BRAM bytes | Free of 14,336 |
| --- | --- | ---: | ---: |
| Accepted audio baseline | `9f4cd16` | 14,182 | 154 |
| Audio + palette | `83bb9ba` | 14,302 | 34 |
| Shared BRAM GC | `c21e8f6` | 13,984 | 352 |
| VM-only GC inline | `2404686` | 14,206 | 130 |

The palette candidate copies the previously tested runtime implementation unchanged and retains both the accepted audio boundary tests and palette transition tests. It adds the empty `pal()` fast path and stateless draw-palette identity check. There is no cached palette state or save-layout change.

The shared-wrapper candidate adds an `OF_FASTTEXT` declaration of `luaC_step`. That existing macro includes `noinline`, BRAM placement and alignment. It keeps one GC body in BRAM instead of duplicating it in callers.

The VM-only candidate introduces one shared inline body for the existing running/stopped GC semantics. Only the VM check macro and fast Lua-call site request forced inlining; the public wrapper delegates to that body under ordinary compiler policy. The patch preserves debt checks, saved PC/top handling, base reload and yield behavior. Other callers retain automatic policy.

## Generated code and attribution

Disassembly verifies all twenty images separately: sixteen benchmark ELFs and four production ELFs. Shared BRAM GC has exactly four VM calls to one BRAM wrapper. VM-only GC has four direct forced-step calls with their running-state guards, no VM wrapper calls and no remaining inline-helper symbol. Production also has an unrelated allocator emergency-GC guard, verified against its full-collection call.

These remain whole-build source experiments. Ordinary automatic inlining differs between production and benchmark: the baseline VM has one wrapper call and three direct forced-step calls in production, versus three wrapper calls and one forced-step call in the harness. The palette variant retains those respective shapes. Matching the runtime builtin policy does not establish whole-program layout parity.

The VM-only production build retains baseline sizes in the ordinary pre-call and two fast C-call helpers. In the benchmark, however, both fast C-call helpers automatically inline the public wrapper, growing by 24 bytes and nine instructions each. Their source policy is unchanged. The VM itself shrinks by 44 bytes in that benchmark, while production grows by 28 bytes. Restricting the explicit attribute to VM sites therefore does not hold all other generated code fixed.

The BRAM-wrapper version leaves more free space but adds calls where GC guards were previously inline. Its smaller code is slower in these Celeste windows. These observations establish actual placement and compiler decisions, not isolated cycle attribution. Cache layout, register allocation, calls and other optimizer decisions still move together; the timings cannot assign the entire change to one wrapper or prove a single cause.

## Verification and scope

All sixteen new cases pass repeated native/QEMU agreement, native output equality, strict quiet/scanout RTL memory oracles and deliberate corrupted-output rejection. Each candidate matches the baseline for 600 frames of raw indexed pixels, palettes and PCM, including audio pair counts. Each source worktree passes the native core and runtime suites.

The real-z8lua GC fixture verifies stopped, running and restarted collection with live tables, strings, closures and calls. The VM-only candidate passes with AddressSanitizer and UndefinedBehaviorSanitizer across every translation unit. A private mutant bypassing the running-state guard is rejected by sixteen stopped-debt assertions. The dependency patch independently reproduces all three prepared files from the baseline.

Production ELF links are separate from benchmark links and all fit the unchanged budget. Dependency pins, frozen inputs, CPU platform, accepted audio source, active checkout and original palette branch remain unchanged. Experimental commits and evidence stay private; no package or deployment follows from these measurements.

Measurements use recreated scenes, fixed seed `0x5eed1234`, twelve measured frames and the production runtime builtin policy. Celeste windows are tower/Trailhead frames 100–111; Moss windows are 180–191 and 234–245. Timings are simulated os20 at 90 MHz, not measured Pocket FPS. The harness substitutes allocation and OS services, and production and harness code layout differ.

Private launchers, source commits, raw output, native/sanitizer/mutation tests, production ELFs, disassembly audits and validating exporters are preserved under `experiments/pico8-sources/accepted-combos-20261017-r1`.
