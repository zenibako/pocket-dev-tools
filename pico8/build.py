"""Run inside an isolated Pico8 case using the existing harness toolchain."""
from pathlib import Path
import hashlib
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor

ROOT = Path('/work')


def build():
    d = ROOT / 'build/pico8'
    d.mkdir(parents=True, exist_ok=True)
    p = ROOT / 'source'
    z = p / '.deps/fake-08/libs/z8lua'
    names = 'eris lapi lauxlib lbaselib lcode lcorolib lctype ldblib ldebug ldo ldump lfunc lgc linit llex lmem lobject lopcodes lparser lpico8lib lstate lstring lstrlib ltable ltablib ltm lundump lvm lzio'.split()
    common = ['-march=rv32imafc_zicsr_zifencei', '-mabi=ilp32f', '-O3', '-flto', '-g',
              '-fomit-frame-pointer', '-ffunction-sections', '-fdata-sections',
              '-falign-functions=64', '-falign-loops=64', '-fno-tree-loop-distribute-patterns',
              '-ffreestanding', '-nostdinc', '-isystem', '/work/musl/include', '-D_GNU_SOURCE',
              '-I/work/pico8', '-I/work/sdk/include', '-I' + str(p / 'include'),
              '-I' + str(z), '-I' + str(p / '.deps/fake-08/libs/miniz')]
    cpp = ['-x', 'c++', '-std=c++17', '-fwrapv', '-DLUA_USE_LONGJMP', '-fno-exceptions',
           '-fno-rtti', '-fno-threadsafe-statics', '-include', 'stdlib.h',
           '-include', str(p / 'include/p8p/vm_fasttext.h'), '-I' + str(p / 'src/compat/cxx')]
    jobs = [(z / (name + '.c'), cpp) for name in names]
    jobs += [(p / 'src/runtime' / name, cpp) for name in ['runtime.cpp', 'cart.c', 'cart_png.c', 'audio.c']]
    jobs += [(ROOT / 'pico8/runner.cpp', cpp), (ROOT / 'source/.deps/fake-08/libs/miniz/miniz.c', ['-std=c11']),
             (ROOT / 'platform/bridge.c', ['-std=c11', '-fno-lto']), (ROOT / 'platform/start.S', []),
             (ROOT / 'pico8/clock.c', ['-std=c11'])]
    def compile_one(job):
        index, (path, flags) = job
        obj = d / f'{index}.o'
        with (d / f'{index}.log').open('w') as log:
            subprocess.run(['riscv64-unknown-elf-gcc', *common, *flags, '-c', str(path), '-o', str(obj)],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        return str(obj)
    with ThreadPoolExecutor(max_workers=4) as pool:
        objects = list(pool.map(compile_one, enumerate(jobs)))
    wraps = ['fopen', 'printf', 'fprintf', 'vfprintf', 'vprintf', 'puts', 'fputs', 'putchar', 'fwrite']
    command = ['riscv64-unknown-elf-gcc', *common, '-nostdlib', '-nostartfiles', '-static', *objects,
               '-Wl,-T,/work/platform/link.ld', '-Wl,--gc-sections', '-Wl,-Map,' + str(d / 'program.map'),
               *['-Wl,--wrap=' + name for name in wraps], '-L/work/musl/lib',
               '-Wl,--start-group', '-lc', '-lm', '-lgcc', '-Wl,--end-group', '-o', str(d / 'program.elf')]
    with (d / 'link.log').open('w') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    from elftools.elf.elffile import ELFFile
    with (d / 'program.elf').open('rb') as stream:
        elf = ELFFile(stream)
        symbols = {s.name: int(s.entry.st_value) for s in elf.get_section_by_name('.symtab').iter_symbols()}
        if symbols['_rtl_start'] != 0x10400000:
            raise ValueError('Unexpected bare entry')
        fast = elf.get_section_by_name('.app_fasttext')
        if not fast or not 0 < fast.header.sh_size <= 0x3800:
            raise ValueError('VM BRAM placement missing or too large')
        (d / 'bram.bin').write_bytes(fast.data())
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    (d / 'build.json').write_text(json.dumps(dict(compiler=subprocess.check_output(
        ['riscv64-unknown-elf-gcc', '--version'], text=True).splitlines()[0], flags=common + cpp,
        command=command, symbols=symbols, elf_sha256=digest(d / 'program.elf'),
        bram_sha256=digest(d / 'bram.bin'), cpu_parameter_changes={},
        vm_placement='BRAM', allocator='existing fullframe bounded segregated allocator'), indent=2) + '\n')
    print('BUILT RV32 Pico8 checkpoint runner', flush=True)


if __name__ == '__main__':
    build()
