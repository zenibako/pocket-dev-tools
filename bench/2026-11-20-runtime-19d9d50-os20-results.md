# Runtime 19d9d50: Butterscotch on os20 and os25 (2026-11-20)

Butterscotch releases move from os25 to os20 of
[pocket-runtime-19d9d50](https://github.com/zenibako/openfpgaCore/releases/tag/pocket-runtime-19d9d50)
in zenibako/butterscotch-pocket#132. These cases replay that build on the
pinned runtime platforms (`--cpu-platform rt-os25|rt-os20`, see
[README.md](README.md#runtime-platforms)). All times are **simulated**, at each
platform's recorded 100 MHz clock.

## Configuration

Butterscotch `5c3f9ef` (same game code as `f5bf841`), port profile, native
scripts enabled, Accuracy, BRAM interpreter, quiet traffic, cached framebuffer,
fixed audio, GCC 13.2.0 container, `--alignment --loop-align 8` (the 19d9d50
SDK flags). Three-frame windows from a cold-cache checkpoint; one run each.

## Timing (timing builds, mean simulated ms per frame)

| Window | frozen os25 | rt-os25 | rt-os20 | rt-os20 vs rt-os25 | Pocket os20 vs os25 |
| --- | ---: | ---: | ---: | ---: | --- |
| Undertale `flowey` 2400–2402 | 13.837 | 13.303 | 12.786 | −3.9% | battle tour −5.7% (battles −3.8 to −8.5%) |
| Deltarune `bmenu` 3120–3122 | 61.515 | 60.121 | 55.637 | −7.5% | battle menu −4.3% |
| Deltarune `dodge` 3323–3325 | 88.654 | 86.586 | 78.982 | −8.8% | dodging −5.7%; benchmark −7.0% |

Cycles per frame: frozen os25 1,401,175/1,354,624/1,395,349,
6,416,754/5,916,135/6,121,527 and 8,505,749/9,501,672/8,588,839; rt-os25
1,347,788/1,301,301/1,341,826, 6,272,735/5,778,907/5,984,524 and
8,323,590/9,297,524/8,354,789; rt-os20 1,316,635/1,217,164/1,301,970,
5,806,527/5,341,870/5,542,784 and 7,585,649/8,471,866/7,637,140.

The Pocket column is one paired device run of the same `f5bf841` ELF on the
19d9d50 os20 and os25 bitstreams (Undertale battle tour and Deltarune
benchmark, Accuracy). Direction agrees. The model is less favourable to os20
than the device for Undertale and 2–3 points more favourable for the Deltarune
battle windows; the harness does not model scanout, audio hardware or
interrupt traffic, which the device keeps. The frozen-to-rt-os25 step
(−2 to −4%) is the 19d9d50 fabric (open-row tracking, scanout sub-bursts) with
the same ELF configuration.

Deltarune `field` fails its QEMU state oracle at frame 2801 on frozen os25,
rt-os25 and rt-os20 alike (expected `cd70523a`, actual `02f87ab5`), so it is a
current-port adapter limitation, not a CPU difference. Its passing frame 2800
is not used as a sample.

## Outputs and reduced-accuracy FMA

rt-os20's CPU is generated with `--fma-reduced-accuracy`; rt-os25 and QEMU use
IEEE fused multiply-add. Traced builds on rt-os25 and rt-os20 of the same
snapshot and configuration produced identical state hash, raw pixels, PCM hash,
sample-pair count, opcode count, event count and trace hash in all nine frames
above, and both pass the QEMU oracles. The two cases' loadable ELF bytes are
identical (the files differ only in debug paths), so the state hashes compare
the same binary. Within these windows reduced-accuracy
FMA changed no game value or output. This is a sample of nine frames, not
whole-game coverage; dynamic FMA counts were not measured.

QEMU has no reduced-accuracy FMA mode. If a future rt-os20 case fails its QEMU
oracle while the matching rt-os25 case passes, compare rt-os20 against rt-os25
RTL outputs before treating it as a port regression.
