#!/usr/bin/env python3
"""Build a revision experiment, with explicit tracing and platform choices."""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import capture


def source_generation():
    """Recognize supported platform layouts without guessing from revisions."""
    generations = [name for name in ['ut', 'of']
                   if (capture.PORT / ('platform/' + name + '_native.c')).is_file()]
    if len(generations) != 1:
        raise RuntimeError('Unsupported or ambiguous port source generation')
    return generations[0]


def sources(game='undertale', directory=None):
    if source_generation() == 'of':
        if directory is None:
            raise RuntimeError('Current source selection requires a private build directory')
        declared = declarative_port(game, directory)['SRCS']
        root = capture.SRC.parent.resolve()
        paths = []
        for name in declared:
            path = Path(name)
            path = (path if path.is_absolute() else capture.PORT / path).resolve()
            if (not path.is_relative_to(root) or path.suffix != '.c' or not path.is_file()
                    or re.search(r'(?:^|_)pc(?:_|\.)|sdl', path.name, re.I)):
                raise RuntimeError('Unsupported port source: ' + name)
            if path in paths:
                raise RuntimeError('Duplicate port source: ' + name)
            paths.append(path)
        if not paths:
            raise RuntimeError('Port source list is empty')
        return paths
    src, port, vendor = capture.SRC, capture.PORT, capture.VENDOR
    return [port / 'main.c', *[port / 'platform' / n for n in
            ['of_platform.c', 'of_diag.c', 'of_log.c', 'of_perf.c', 'of_audio_system.c',
             'ut_bench.c', 'ut_strings.c', 'ut_save_fs.c', 'ut_native.c']],
            *sorted(src.glob('*.c')), *sorted((src / 'sw').glob('*.c')),
            *sorted((src / 'image').glob('*.c')), *sorted((src / 'debug_font').glob('*.c')),
            src / 'video/null_video.c', src / 'embedded/stb_impl.c',
            *sorted((vendor / 'bzip2').glob('*.c')),
            *[vendor / n for n in ['sha1/sha1.c', 'md5/md5.c', 'base64/base64.c',
                                 'miniz/miniz.c', 'miniz/miniz_tdef.c', 'miniz/miniz_tinfl.c']],
            src / 'physics/physics.c', src / 'physics/disabled/physics_disabled.c']


def declarative_port(game, directory):
    # Only read the declarative prefix. Reject executable make constructs before
    # make sees it; neither shell expansion nor an untrusted recipe is required.
    if game not in ['undertale', 'deltarune']:
        raise RuntimeError('Unsupported game: ' + game)
    original = (capture.PORT / 'Makefile').read_text()
    marker = '# Neither sdk.mk'
    if original.count(marker) != 1:
        raise RuntimeError('Port Makefile declarative boundary anchor changed')
    text = original.split(marker)[0]
    text, count = re.subn(r'ifeq \(\$\(wildcard \$\(SDK_DIR\)/sdk.mk\),\).*?endif', '', text, flags=re.S)
    if count > 1:
        raise RuntimeError('Port Makefile SDK check anchor changed')
    # This exact upstream probe binds production native save states, a service
    # this harness disables. Omit it before validation rather than executing its
    # shell, accepting arbitrary inactive branches, or inventing a game identity.
    state_probe = '''ifneq ($(wildcard $(G)data.win),)
ifndef STATE_GAME_ID
STATE_GAME_ID := $(shell python3 -c 'import hashlib; h=hashlib.sha256(); f=open("$(G)data.win", "rb"); [h.update(b) for b in iter(lambda:f.read(1048576), b"")]; print(h.hexdigest()[:16])')
endif
ifeq ($(STATE_GAME_ID),)
$(error Could not fingerprint data.win; when compiling in a container pass STATE_GAME_ID=<host SHA256 prefix>)
endif
endif
'''
    if text.count(state_probe) > 1:
        raise RuntimeError('Native state fingerprint probe anchor changed')
    text = text.replace(state_probe, '# Harness: native state fingerprint unavailable\n')
    logical = text.replace('\\\n', ' ')
    safe_functions = {'abspath', 'wildcard', 'foreach', 'if', 'or', 'error'}
    reserved = {'SHELL', 'MAKEFILES', 'MAKEFLAGS', 'GNUMAKEFLAGS', 'MAKEOVERRIDES', 'CURDIR'}
    for raw in logical.splitlines():
        # Make treats escaped # as a literal, so splitting there could hide an
        # executable expansion from validation while leaving it active in make.
        # Supported port declarations require no escaped comment syntax.
        if r'\#' in raw:
            raise RuntimeError('Unsafe Makefile escaped comment syntax')
        line = raw.split('#', 1)[0].strip()
        if not line:
            continue
        assignment = re.match(r'^(?:export[ \t]+)?([A-Za-z_][A-Za-z_0-9]*)\s*(?:[:+?]?=)', line)
        conditional = re.match(r'^(?:(?:else )?ifn?eq\s*\(|else$|endif$)', line)
        expansion = line.startswith('$(error ')
        exported = re.fullmatch(r'export[ \t]+([A-Za-z_][A-Za-z_0-9]*)', line)
        if raw.startswith('\t') or not (assignment or conditional or expansion or exported):
            raise RuntimeError('Non-declarative or unsafe Makefile line: ' + line)
        declaration = assignment or exported
        if declaration and declaration[1] in reserved:
            raise RuntimeError('Unsafe Makefile variable: ' + declaration[1])
        if re.search(r'\$(?!\()', line):
            raise RuntimeError('Unsafe Makefile expansion')
        for expr in re.finditer(r'\$\(([^()]*)', line):
            head = expr[1]
            function = re.match(r'([A-Za-z_][A-Za-z_0-9]*)\s+', head)
            if function:
                if function[1] not in safe_functions:
                    raise RuntimeError('Unsafe Makefile function: ' + function[1])
            elif not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', head):
                raise RuntimeError('Unsafe Makefile variable expansion')
    text += "\n$(info HARNESS_CFLAGS=$(CFLAGS))\n$(info HARNESS_SRCS=$(SRCS))\n.PHONY: experiment-flags\nexperiment-flags:\n"
    path = directory / 'flags.mk'
    path.write_text(text)
    # An empty working directory prevents unrelated asset-migration probes from
    # interpreting the frozen input layout. CURDIR still resolves private sources.
    with tempfile.TemporaryDirectory(prefix='.flags-', dir=directory) as scratch:
        result = subprocess.run(['make', '-rR', '-s', '--no-print-directory', '-f', str(path.resolve()),
                                 'CURDIR=' + str(capture.PORT.resolve()), 'GAME=' + game, 'experiment-flags'],
                                cwd=scratch, env={'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'LC_ALL': 'C'},
                                capture_output=True, text=True, check=True)
    values = {}
    for key in ['CFLAGS', 'SRCS']:
        rows = [line.removeprefix('HARNESS_' + key + '=') for line in result.stdout.splitlines()
                if line.startswith('HARNESS_' + key + '=')]
        if len(rows) != 1:
            raise RuntimeError('Ambiguous declarative Makefile output: ' + key)
        values[key] = shlex.split(rows[0])
    return values


def port_flags(game, directory):
    return declarative_port(game, directory)['CFLAGS']


def instrument_vm(vm, generation, kind, variant):
    if generation not in ['ut', 'of'] or kind not in ['trace', 'timing']:
        raise RuntimeError('Unsupported VM adapter configuration')
    if variant == 'bram':
        name = generation.upper() + '_FAST_LOOP'
        vm = capture.once(vm, '#if defined(' + name + ') && !defined(OF_PC)', '#if defined(' + name + ')')
    if kind == 'trace':
        anchor = ('        uint32_t instr = BinaryUtils_readUint32Aligned(bytecodeBase + ip);'
                  if generation == 'ut' else
                  '        OpWord opword = {BinaryUtils_readUint32Aligned(bytecodeBase + ip)};')
        # The current dispatch wraps the same raw word in OpWord. Read its value
        # once, at the original instruction address, before ip advances.
        vm = capture.once(vm, anchor, anchor + '\n        frame_tick(ctx,ip,' +
                          ('instr' if generation == 'ut' else 'opword.value') + ');')
        signature = re.compile(r'RValue VM_executeCode\(VMContext\* ctx, int32_t codeIndex(?:, [^\n{};]*)?\) \{')
        matches = list(signature.finditer(vm))
        if len(matches) != 1:
            raise RuntimeError('VM event hook anchor changed')
        at = matches[0].end()
        vm = vm[:at] + '\n    frame_event(codeIndex);' + vm[at:]
    return vm


def build(game, variant, compiler):
    config = json.loads((ROOT / 'experiment.json').read_text())
    directory = ROOT / 'build/fullframe' / game / variant
    directory.mkdir(parents=True, exist_ok=True)
    src, port, vendor = capture.SRC, capture.PORT, capture.VENDOR
    generation = source_generation()
    paths = sources(game, directory)
    loop = capture.once((src / 'loop.c').read_text(),
                        '            uint64_t frameStartNow = nowNanos();',
                        '            frame_begin(runner);\n            uint64_t frameStartNow = nowNanos();')
    loop = capture.once(loop, '            lastFrameTime = nowNanos();\n        }',
                        '            lastFrameTime = nowNanos();\n            frame_end(runner);\n        }')
    (directory / 'loop.c').write_text('#include "frame.h"\n' + loop)
    vm = instrument_vm((src / 'vm.c').read_text(), generation, config['kind'], variant)
    (directory / 'vm.c').write_text('#include "frame.h"\n' + vm)
    main = capture.once((port / 'main.c').read_text(), 'int main(int argc, char **argv)',
                        'int game_main(int argc, char **argv)')
    (directory / 'main.c').write_text(main)
    native_name = generation + '_native.c'
    native_function = generation + 'NativeInstall'
    native_anchor = 'void ' + native_function + '(Runner *runner) {'
    native = capture.once((port / 'platform' / native_name).read_text(),
                          native_anchor, native_anchor + '\n    if(FRAME_DISABLE_NATIVE)return;')
    (directory / native_name).write_text(native)
    paths = [directory / 'loop.c' if p == src / 'loop.c' else
             directory / 'vm.c' if p == src / 'vm.c' else
             directory / 'main.c' if p == port / 'main.c' else
             directory / native_name if p == port / 'platform' / native_name else p for p in paths]
    paths += [ROOT / 'fullframe' / n for n in ['bridge.c', 'platform.c', 'runtime.c', 'start.S']]
    flags = ['-march=rv32imafc_zicsr_zifencei', '-mabi=ilp32f', '-O2', '-g',
             '-ffunction-sections', '-fdata-sections', '-fno-tree-loop-distribute-patterns',
             '-nostdinc', '-nostdlib', '-nostartfiles', '-ffreestanding',
             '-isystem', str(ROOT / 'inputs/sdk/musl/include')]
    includes = [directory, port, port / 'platform', src, src / 'sw', src / 'image', src / 'video',
                src / 'debug_font', ROOT / 'fullframe', ROOT / 'inputs/sdk/include',
                *[vendor / n for n in ['stb/ds', 'stb/image', 'stb/vorbis', 'bzip2', 'sha1', 'md5', 'base64', 'miniz', 'zstd']]]
    app_flags = port_flags(game, directory)
    if variant == 'sdram':
        app_flags = [x for x in app_flags if x not in ['-DUT_FAST_LOOP', '-DOF_FAST_LOOP']]
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
    defines = ['FRAME_CURRENT_PORT=' + str(int(generation == 'of')),
               'FRAME_TARGET=' + str(config['first_frame'] - 1),
               'FRAME_DISABLE_NATIVE=' + str(int(config['native'] == 'disabled')),
               'FRAME_TIMING=' + str(int(config['kind'] == 'timing')),
               'FRAME_SPEED=' + str(int(config['mode'] == 'speed')),
               'FRAME_FB_UNCACHED=' + str(int(config['framebuffer'] == 'uncached')),
               'FRAME_CLOCK_COST=' + str(config['clock_cost']),
               'FRAME_AUDIO_REALTIME=' + str(int(config['audio'] == 'realtime'))]
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
                    config=config, source_generation=generation, vm_trace=config['kind'] == 'trace', app_flags=app_flags,
                    substitutions=['harness allocator', 'virtual file/clock/input/audio services',
                                   'async storage unavailable; synchronous private file bridge',
                                   ('global OF_PC host declarations and source branches' if config['profile'] == 'legacy' else
                                    'SDK declarations shim; device source branches compiled, kernel ABI not reproduced'),
                                   *(['native production save-state services and game fingerprint probe disabled',
                                      'virtual asset directory /frame-assets replaces the process cwd']
                                     if generation == 'of' else [])],
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
