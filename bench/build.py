#!/usr/bin/env python3
"""Build a revision experiment, with explicit tracing and platform choices."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import capture


def sources(game="deltarune"):
    src, port, vendor = capture.SRC, capture.PORT, capture.VENDOR
    renamed = (port / 'platform/of_bench.h').is_file()
    prefix = 'of' if renamed else 'ut'
    menu = [port / 'platform' / n for n in [prefix + '_menu.c', prefix + '_font.c', prefix + '_battle_ui.c']
            if (port / 'platform' / n).is_file()]
    return [port / 'main.c', *[port / 'platform' / n for n in
            ['of_platform.c', 'of_diag.c', 'of_log.c', 'of_perf.c', 'of_audio_system.c',
             prefix + '_bench.c', prefix + '_strings.c', prefix + '_save_fs.c', prefix + '_native.c']], *menu,
            *([port / 'platform' / n for n in ['game_' + game + '.c', 'of_state_requests.c', 'of_snapshot_envelope.c']] if renamed else []),
            *sorted(src.glob('*.c')), *sorted((src / 'sw').glob('*.c')),
            *sorted((src / 'image').glob('*.c')), *sorted((src / 'debug_font').glob('*.c')),
            src / 'video/null_video.c', src / 'embedded/stb_impl.c',
            *sorted((vendor / 'bzip2').glob('*.c')),
            *[vendor / n for n in ['sha1/sha1.c', 'md5/md5.c', 'base64/base64.c',
                                 'miniz/miniz.c', 'miniz/miniz_tdef.c', 'miniz/miniz_tinfl.c']],
            *([vendor / 'zstd/zstd.c'] if (vendor / 'zstd/zstd.c').is_file() else []),
            src / 'physics/physics.c', src / 'physics/disabled/physics_disabled.c']


def scene_main(main, scene):
    if scene is None:
        return main
    required = {'room', 'setup_frame', 'jump_frame', 'globals', 'input', 'require_spades'}
    if (not isinstance(scene, dict) or not required <= set(scene) or set(scene) - required - {'benchmark_diagnostics'} or
            type(scene['room']) is not int or scene['room'] < 0 or
            type(scene['setup_frame']) is not int or scene['setup_frame'] < 0 or
            type(scene['jump_frame']) is not int or scene['jump_frame'] <= scene['setup_frame'] or
            not isinstance(scene['globals'], str) or not isinstance(scene['input'], str) or
            type(scene['require_spades']) is not bool or scene.get('benchmark_diagnostics', False) is not False):
        raise ValueError('Invalid controlled scene setup')
    # Keep the benchmark argument's seed/mode selection, but reproduce ordinary
    # play rather than turning on the benchmark's per-draw clock diagnostics.
    # Volatile saves remain mandatory for private, repeatable captures.
    renamed = 'ofBenchStart();' in main
    prefix, typename, macro = ('of', 'Of', 'OF') if renamed else ('ut', 'Ut', 'UT')
    main = capture.once(main, prefix + 'BenchStart();', prefix + 'SaveFsSetVolatile(true);')
    setup = ('    static const ' + typename + 'Jump frame_scene_jumps[] = {\n'
             f'        {{{scene["setup_frame"]}, -1, {json.dumps(scene["globals"])}}},\n'
             f'        {{{scene["jump_frame"]}, {scene["room"]}, NULL}}\n'
             '    };\n'
             '    utPlatformSetUncapped(true);\n'
             '    utPlatformSetJumps(frame_scene_jumps, 2);\n'
             f'    utPlatformSetInputScript({json.dumps(scene["input"])});\n')
    setup = setup.replace('utPlatform', prefix + 'Platform')
    anchor = '    int ret = loop(args, ' + macro + '_GAME_NAME);'
    return capture.once(main, anchor, setup + anchor)


def port_flags(game, directory):
    # Resolve only the declarative prefix, before header-cache cleanup and SDK
    # recipes. Never run the port Makefile's build/deploy targets or shell probes.
    text = (capture.PORT / 'Makefile').read_text().split('# Neither sdk.mk')[0]
    text, count = re.subn(r'ifeq \(\$\(wildcard \$\(SDK_DIR\)/sdk.mk\),\).*?endif', '', text, flags=re.S)
    if count != 1:
        raise RuntimeError('Port Makefile SDK check anchor changed')
    text += "\n.PHONY: experiment-flags\nexperiment-flags:\n\t@printf '%s\\n' $(CFLAGS)\n"
    path = directory / 'flags.mk'
    path.write_text(text)
    options = []
    if (capture.PORT / 'platform/of_bench.h').is_file():
        options = ['SAVESTATES=0', 'TARGET=pocket',
                   'STATE_GAME_ID=' + capture.sha(capture.PORT / ('games/' + game + '/data.win'))[:16]]
    result = subprocess.run(['make', '-s', '--no-print-directory', '-f', str(path),
                             'GAME=' + game, *options, 'experiment-flags'], cwd=capture.PORT,
                            capture_output=True, text=True, check=True)
    return result.stdout.splitlines()


def build(game, variant, compiler):
    config = json.loads((ROOT / 'experiment.json').read_text())
    directory = ROOT / 'build/fullframe' / game / variant
    directory.mkdir(parents=True, exist_ok=True)
    src, port, vendor = capture.SRC, capture.PORT, capture.VENDOR
    renamed = (port / 'platform/of_bench.h').is_file()
    prefix = 'of' if renamed else 'ut'
    fast_loop = 'OF_FAST_LOOP' if renamed else 'UT_FAST_LOOP'
    paths = sources(game)
    loop = capture.once((src / 'loop.c').read_text(),
                        '            uint64_t frameStartNow = nowNanos();',
                        '            frame_begin(runner);\n            uint64_t frameStartNow = nowNanos();')
    loop = capture.once(loop, '            lastFrameTime = nowNanos();\n        }',
                        '            lastFrameTime = nowNanos();\n            frame_end(runner);\n        }')
    (directory / 'loop.c').write_text('#include "frame.h"\n' + loop)
    vm = (src / 'vm.c').read_text()
    if variant == 'bram':
        vm = capture.once(vm, '#if defined(' + fast_loop + ') && !defined(OF_PC)', '#if defined(' + fast_loop + ')')
    if config['kind'] == 'trace':
        vm = capture.once(vm, '        uint32_t instr = BinaryUtils_readUint32Aligned(bytecodeBase + ip);',
                          '        uint32_t instr = BinaryUtils_readUint32Aligned(bytecodeBase + ip);\n        frame_tick(ctx,ip,instr);')
        vm = capture.once(vm, 'RValue VM_executeCode(VMContext* ctx, int32_t codeIndex) {',
                          'RValue VM_executeCode(VMContext* ctx, int32_t codeIndex) {\n    frame_event(codeIndex);')
    (directory / 'vm.c').write_text('#include "frame.h"\n' + vm)
    main = capture.once((port / 'main.c').read_text(), 'int main(int argc, char **argv)',
                        'int game_main(int argc, char **argv)')
    main = scene_main(main, config.get('scene'))
    (directory / 'main.c').write_text(main)
    native = capture.once((port / ('platform/' + prefix + '_native.c')).read_text(),
                          'void ' + prefix + 'NativeInstall(Runner *runner) {',
                          'void ' + prefix + 'NativeInstall(Runner *runner) {\n    if(FRAME_DISABLE_NATIVE)return;')
    (directory / (prefix + '_native.c')).write_text(native)
    paths = [directory / 'loop.c' if p == src / 'loop.c' else
             directory / 'vm.c' if p == src / 'vm.c' else
             directory / 'main.c' if p == port / 'main.c' else
             directory / (prefix + '_native.c') if p == port / ('platform/' + prefix + '_native.c') else p for p in paths]
    paths += [ROOT / 'fullframe' / n for n in ['bridge.c', 'platform.c', 'runtime.c', 'start.S']]
    flags = ['-march=rv32imafc_zicsr_zifencei', '-mabi=ilp32f', '-O2', '-g',
             '-ffunction-sections', '-fdata-sections', '-fno-tree-loop-distribute-patterns',
             '-nostdinc', '-nostdlib', '-nostartfiles', '-ffreestanding',
             '-isystem', str(ROOT / 'inputs/sdk/musl/include')]
    includes = [directory, port, port / 'platform', src, src / 'sw', src / 'image', src / 'video',
                src / 'debug_font', ROOT / 'fullframe', ROOT / 'inputs/sdk/include',
                *[vendor / n for n in ['stb/ds', 'stb/image', 'stb/vorbis', 'bzip2', 'sha1', 'md5', 'base64', 'miniz']]]
    if (vendor / 'zstd').is_dir():
        includes.append(vendor / 'zstd')
    app_flags = port_flags(game, directory)
    if variant == 'sdram':
        app_flags = [x for x in app_flags if x != '-D' + fast_loop]
    if config['profile'] == 'legacy':
        app_flags += ['-DOF_PC', '-falign-functions=64', '-falign-loops=64']
    else:
        # Compile all game/port OF_PC fences as device code. Only the SDK ABI is
        # substituted: no real kernel/services table exists in this test process.
        (directory / 'of.h').write_text('#define OF_PC 1\n#include "' +
            str(ROOT / 'inputs/sdk/include/of.h') + '"\n#undef OF_PC\n' +
            'void of_file_slot_register(uint32_t,const char*);\n'
            'void of_file_set_idle_hook(void (*)(void));\n'
            'int of_file_slot_find(const char*,uint32_t*);\n'
            'uint32_t of_file_async_max_read(void);\n'
            'void *of_file_dma_stage_alloc(uint32_t,uint32_t);\n'
            'int of_file_read_async(int,uint32_t,void*,uint32_t,void (*)(int,int));\n'
            'int of_file_async_poll(void);\nint of_file_async_busy(void);\n')
    if config['alignment']:
        app_flags += ['-falign-functions=64', '-falign-loops=64']
    # Apply after the port defaults so an explicit -U can disable a profiler.
    # Ordered tokens are recorded in the case identity and build metadata.
    app_flags += config.get('extra_cflags', [])
    defines = ['FRAME_TARGET=' + str(config['first_frame'] - 1),
               'FRAME_DISABLE_NATIVE=' + str(int(config['native'] == 'disabled')),
               'FRAME_TIMING=' + str(int(config['kind'] == 'timing')),
               'FRAME_SPEED=' + str(int(config['mode'] == 'speed')),
               'FRAME_FB_UNCACHED=' + str(int(config['framebuffer'] == 'uncached')),
               'FRAME_CLOCK_COST=' + str(config['clock_cost']),
               'FRAME_AUDIO_REALTIME=' + str(int(config['audio'] == 'realtime'))]
    if renamed:
        defines.append('FRAME_PORT_RENAMED=1')
    if config.get('scene'):
        defines += ['FRAME_SCENE_ROOM=' + str(config['scene']['room']),
                    'FRAME_SCENE_SPADES=' + str(int(config['scene']['require_spades']))]
    wraps = ['fopen', 'printf', 'fprintf', 'vfprintf', 'vprintf', 'puts', 'fputs', 'putchar', 'fwrite']
    command = [compiler, *flags, *app_flags, *['-D' + x for x in defines],
               *['-I' + str(p) for p in includes], *map(str, paths),
               '-Wl,-T,' + str(ROOT / 'fullframe/link.ld'), '-Wl,--gc-sections',
               '-Wl,-Map,' + str(directory / 'program.map'), *['-Wl,--wrap=' + x for x in wraps],
               '-L' + str(ROOT / 'inputs/sdk/musl/lib'), '-lc', '-lm', '-lgcc',
               '-o', str(directory / 'program.elf')]
    with (directory / 'compile.log').open('w') as log:
        subprocess.run(command, cwd=port, stdout=log, stderr=subprocess.STDOUT, check=True)
    nm = compiler.removesuffix('gcc') + 'nm'
    symbols = subprocess.check_output([nm, str(directory / 'program.elf')], text=True)
    if config['kind'] == 'timing' and any(re.search(r'\b' + n + r'$', symbols, re.M) for n in ['frame_tick', 'frame_event']):
        raise RuntimeError('Timing executable retained per-opcode/event instrumentation')
    tracked = [*paths, ROOT / 'fullframe/frame.h', ROOT / 'fullframe/link.ld',
               ROOT / 'fullframe/build.py', ROOT / 'experiment.json', port / 'Makefile']
    if config['profile'] == 'port':
        tracked.append(directory / 'of.h')
    metadata = dict(command=command, sources={str(p.relative_to(ROOT)): capture.sha(p) for p in tracked},
                    compiler_version=subprocess.check_output([compiler, '--version'], text=True).splitlines()[0],
                    config=config, vm_trace=config['kind'] == 'trace', app_flags=app_flags,
                    substitutions=['harness allocator', 'virtual file/clock/input/audio services',
                                   'SDK declarations shim; device source branches compiled, kernel ABI not reproduced'],
                    timing_audio_hash=False if config['kind'] == 'timing' else True)
    (directory / 'build.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print('Built', game, variant, config['kind'], config['mode'], metadata['compiler_version'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--game', required=True)
    parser.add_argument('--variant', required=True)
    parser.add_argument('--compiler', default='riscv64-unknown-elf-gcc')
    args = parser.parse_args()
    build(args.game, args.variant, args.compiler)
