#!/usr/bin/env python3
"""Run inside the harness toolchain container; never access the original checkouts."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
OS = ROOT / 'inputs/os'
BUILD = ROOT / 'build'
CPU = OS / 'src/fpga/vendor/vexriscv/VexiiRiscv/VexiiRiscv_os25.v'
SRC = ROOT / 'inputs/butterscotch/src'
UNITS = ['vm', 'gml_array', 'gml_method', 'instance', 'int_int_hashmap', 'int_rvalue_hashmap', 'stb_ds']
VARIANTS=['sdram','bram','negative','battle-negative']
DEFINES = ['USE_FLOAT_REALS', 'NO_RVALUE_INT64', 'ENABLE_WAD16', 'ENABLE_WAD17', 'ENABLE_VM_GML_PROFILER']
sys.path.insert(0, str(OS / 'tools'))
from check_pocket_memory_contention import once, pocket_sdram_twin
from check_pocket_gpu_transport import sdram_parameters


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, log, **kwargs):
    print('Running', str(log.relative_to(ROOT)), flush=True)
    with log.open('w') as stream:
        subprocess.run(list(map(str, command)), stdout=stream, stderr=subprocess.STDOUT, check=True, **kwargs)


def save(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def firmware():
    from elftools.elf.elffile import ELFFile
    from battle_fixtures import generate
    captured=generate()
    for variant, extra in [('sdram', []), ('bram', ['-DUT_FAST_LOOP']), ('negative', ['-DHARNESS_EXPECT_BIAS=1']), ('battle-negative', ['-DHARNESS_BATTLE_EXPECT_BIAS=1'])]:
        dest = BUILD / variant
        dest.mkdir(exist_ok=True)
        command = ['riscv64-unknown-elf-gcc', '-march=rv32imafc_zicsr_zifencei', '-mabi=ilp32f',
                   '-O2', '-g', '-ffunction-sections', '-fdata-sections', '-falign-functions=64', '-falign-loops=64',
                   '-fno-tree-loop-distribute-patterns', '-nostdinc',
                   '-ffreestanding', '-nostdlib', '-nostartfiles', '-isystem', ROOT / 'inputs/sdk/musl/include',
                   '-I' + str(ROOT / 'inputs/sdk/include'), '-I' + str(SRC),
                   '-I' + str(ROOT / 'inputs/butterscotch/vendor/stb/ds'),
                   *['-D' + d for d in DEFINES], *extra,
                   ROOT / 'start.S', ROOT / 'runtime.c', ROOT / 'services.c', ROOT / 'workloads.c', ROOT / 'battle_replay.c',
                   *[SRC / (u + '.c') for u in UNITS], '-Wl,-T,' + str(ROOT / 'link.ld'),
                   '-Wl,--gc-sections', '-Wl,-Map,' + str(dest / 'program.map'),
                   '-L' + str(ROOT / 'inputs/sdk/musl/lib'), '-lc', '-lm', '-lgcc', '-o', dest / 'program.elf']
        run(command, dest / 'compile.log')
        bram = bytearray(struct.pack('<I', 0x00000013) * 8192)
        struct.pack_into('<II', bram, 0, 0x103202b7, 0x00028067)
        image = bytearray()
        with (dest / 'program.elf').open('rb') as f:
            elf = ELFFile(f)
            assert elf.header.e_entry == 0x10320000
            sections = {}
            for section in elf.iter_sections():
                if not (section.header.sh_flags & 2) or not section.header.sh_size:
                    continue
                address, size = section.header.sh_addr, section.header.sh_size
                sections[section.name] = dict(address=address, bytes=size)
                if section.header.sh_type == 'SHT_NOBITS':
                    continue
                data = section.data()
                if 0x4000 <= address and address + size <= 0x7800:
                    bram[address:address + size] = data
                elif 0x10320000 <= address and address + size < 0x10400000:
                    offset = address - 0x10320000
                    if len(image) < offset + size:
                        image.extend(bytes(offset + size - len(image)))
                    image[offset:offset + size] = data
                else:
                    raise RuntimeError(f'Unexpected ELF load section {section.name} at {address:x}')
            symbols = elf.get_section_by_name('.symtab')
            loop = next(s for s in symbols.iter_symbols() if s.name == 'executeLoop')
            loop_address = loop.entry.st_value
            if variant == 'bram':
                assert 0x4000 <= loop_address < 0x7800
            else:
                assert 0x10320000 <= loop_address < 0x10400000
        (dest / 'program.bin').write_bytes(image)
        header = 'WIDTH=32;\nDEPTH=8192;\nADDRESS_RADIX=DEC;\nDATA_RADIX=HEX;\nCONTENT BEGIN\n'
        content = ''.join(f'{i} : {value[0]:08x};\n' for i, value in enumerate(struct.iter_unpack('<I', bram)))
        (dest / 'firmware.mif').write_text(header + content + 'END;\n')
        save(dest / 'firmware.json', dict(variant=variant, compiler=list(map(str, command)), sections=sections,
             execute_loop_address=loop_address, elf_sha256=digest(dest / 'program.elf'),
             image_sha256=digest(dest / 'program.bin'), bram_sha256=digest(dest / 'firmware.mif'),
             source_hashes={str(p.relative_to(ROOT)):digest(p) for p in
                 [ROOT / 'start.S', ROOT / 'runtime.c', ROOT / 'services.c', ROOT / 'workloads.c', ROOT / 'battle_replay.c', ROOT / 'link.ld',
                  ROOT / 'input-manifest.json', ROOT / 'battle_replay.h', ROOT / 'battle_fixtures.inc', ROOT / 'battle_fixtures.py',
                  ROOT / 'captures/replay-manifest.json', *[ROOT / r['capture_path'] for r in captured],
                  *[ROOT / 'captures' / game / 'manifest.json' for game in ['undertale','deltarune']], *[SRC / (u + '.c') for u in UNITS]]},
             compiler_version=subprocess.run(['riscv64-unknown-elf-gcc', '--version'], capture_output=True,
                                             text=True, check=True).stdout.splitlines()[0]))


def rtl(jobs):
    dest = BUILD / 'rtl'
    dest.mkdir(exist_ok=True)
    target = OS / 'src/fpga/targets/pocket'
    test = OS / 'src/fpga/test'
    probe = '.PHONY: harness-defs\nharness-defs:\n\t@echo $(DEFS)\n'
    defs = subprocess.run(['make', '-s', '--no-print-directory', '-f', 'Makefile', '-f', '-',
                          'VARIANT=os25', 'harness-defs'], input=probe, cwd=target,
                          capture_output=True, text=True, check=True).stdout.strip().split()
    config = dict(variant=dict(target='pocket', variant='os25', defs=' '.join(defs)))
    memory = sdram_parameters(config, dest)
    pre = (dest / 'preprocessed-pocket.v').read_text()
    block = re.search(r'gpu_core\s*#\((.*?)\)\s*gpu\s*\(', pre, re.S).group(1)
    block = re.sub(r'//[^\n]*', '', block)
    gpu = dict((name, int(value)) for name, value in re.findall(r'\.(\w+)\(\s*(\d+)\s*\)', block))
    if len(gpu) != block.count('.'):
        raise RuntimeError('Unhandled production GPU parameter')
    top = (test / 'tb_system_sdram.v').read_text()
    top = once(top, 'module tb_system (', 'module tb_system (\n    output wire [31:0] harness_sdram_errors,')
    top = once(top, 'endmodule', 'assign harness_sdram_errors = sdram_chip.errors;\nendmodule')
    top, count = re.subn(r'io_sdram\s+(\w+)\s*\(', "assign phy_ncs = 1'b0;\nio_sdram #(" +
                        ','.join(f'.{key}({value})' for key, value in memory.items()) + r') \1 (', top)
    assert count == 1
    top = once(top, '    .phy_ncs(phy_ncs),', '')
    top = once(top, 'gpu_core gpu (', 'gpu_core #(' + ','.join(f'.{k}({v})' for k,v in gpu.items()) + ') gpu (')
    (dest / 'top.v').write_text(top)
    twin = pocket_sdram_twin(OS, dest)
    cpp = (test / 'tb_system_sdram_main.cpp').read_text()
    cpp = once(cpp, '#define VSYNC_PERIOD 16667', '#define VSYNC_PERIOD 1666667')
    cpp = once(cpp, 'c - last_m1_activity > 1500000', 'c - last_m1_activity > 15000000')
    cpp = once(cpp, '        if (uart_buf.find("HAL init")',
               '        const size_t failure = uart_buf.find("VMHARNESS FAIL");\n'
               "        if (failure != std::string::npos && uart_buf.find('\\n', failure) != std::string::npos) { exit_code = 2; break; }\n"
               '        if (uart_buf.find("HAL init")')
    cpp = once(cpp, '    uint32_t final_pc =',
               '    std::printf("\\n=== UART BEGIN ===\\n%s\\n=== UART END ===\\n", uart_buf.c_str());\n'
               '    std::printf("SDRAM errors=%u\\n", tb->harness_sdram_errors);\n'
               '    if (tb->harness_sdram_errors) exit_code = 3;\n'
               '    uint32_t final_pc =')
    cpp = once(cpp, '        tick_cycle();\n        if (tb->inj_burst_rd)', '''        tick_half(false);
        const bool aw_take = tb->dbg_aw_valid && tb->dbg_aw_ready;
        const uint32_t aw_addr = tb->dbg_aw_addr, aw_len = tb->dbg_aw_len;
        const bool w_take = tb->dbg_w_valid && tb->dbg_w_ready;
        const uint32_t w_data = tb->dbg_w_data, w_strb = tb->dbg_w_strb;
        tb->vsync = (cpu_cycles % VSYNC_PERIOD == 0);
        tick_half(true); cpu_cycles++;
        if (tb->inj_burst_rd)''')
    cpp = once(cpp, 'if (tb->dbg_aw_valid && tb->dbg_aw_ready)\n'
               '            aw_fifo.push_back({tb->dbg_aw_addr >> 2, tb->dbg_aw_len});',
               'if (aw_take) aw_fifo.push_back({aw_addr >> 2, aw_len});')
    cpp = once(cpp, 'if (tb->dbg_w_valid && tb->dbg_w_ready)\n'
               '            push_w_beat(tb->dbg_w_data, tb->dbg_w_strb, c);',
               'if (w_take) push_w_beat(w_data, w_strb, c);')
    (dest / 'main.cpp').write_text(cpp)
    (dest / 'test.mk').write_text(f'include {test}/Makefile\n'
        f'SYSTEM_SDRAM_SRCS := $(subst tb_system_sdram.v,{dest}/top.v,$(SYSTEM_SDRAM_SRCS))\n'
        f'SYSTEM_SDRAM_SRCS := $(subst io_sdram_mister_test.v,{twin},$(SYSTEM_SDRAM_SRCS))\n')
    command = ['make', '-f', dest / 'test.mk', dest / 'obj/Vtb_system',
               f'SYSTEM_SDRAM_DIR={dest}/obj', f'SYSTEM_SDRAM_CPP={dest}/main.cpp',
               f'VEXII_MISTER={CPU}', f'VERILATOR=verilator -j {jobs} ' + ' '.join('+define+' + d for d in defs)]
    run(command, dest / 'build.log', cwd=test)
    save(dest / 'rtl.json', dict(cpu_sha256=digest(CPU), definitions=defs, sdram_parameters=memory,
         gpu_parameters=gpu, simulator_sha256=digest(dest / 'obj/Vtb_system'),
         wrapper_sha256=digest(dest / 'top.v'), runner_sha256=digest(dest / 'main.cpp'),
         controller_twin_sha256=digest(twin),
         verilator=subprocess.run(['verilator', '--version'], capture_output=True, text=True, check=True).stdout.strip()))


EXPECTED_HASHES = ['120c7196', '060c5eb2', 'c50bf85f', '120c7196', '120c7196', 'c0501cf6', 'c0501cf6', '080c61d8']


def results():
    from battle_fixtures import captures
    captures() # Check every selected capture against its source manifest.
    battles=json.loads((ROOT / 'captures/replay-manifest.json').read_text())
    simulator = BUILD / 'rtl/obj/Vtb_system'
    report = dict(scope='Synthetic VM fixtures and captured numeric battle events with checked external-call transcripts; simulated cycles at 100 MHz, not measured Pocket performance',
                  rtl=json.loads((BUILD / 'rtl/rtl.json').read_text()), runs={}, battle_runs={}, captures=battles,
                  input_manifest_sha256=digest(ROOT / 'input-manifest.json'),
                  harness_sources={name:digest(ROOT / name) for name in ['workloads.c', 'services.c', 'runtime.c', 'start.S', 'link.ld', 'harness.py', 'run.py', 'Dockerfile', 'battle_replay.c', 'battle_replay.h', 'battle_fixtures.py', 'battle_fixtures.inc', 'capture.py', 'capture/capture_hooks.c']},
                  firmware={v:json.loads((BUILD / v / 'firmware.json').read_text()) for v in VARIANTS})
    if digest(simulator) != report['rtl']['simulator_sha256']:
        raise RuntimeError('Simulator changed since RTL build')
    if digest(CPU) != report['rtl']['cpu_sha256']:
        raise RuntimeError('CPU netlist changed; rebuild RTL')
    for variant in VARIANTS:
        dest = BUILD / variant
        if any(digest(ROOT / name) != sha for name, sha in report['firmware'][variant]['source_hashes'].items()):
            raise RuntimeError('Firmware sources changed; rebuild firmware')
        for name, field in [('program.elf', 'elf_sha256'), ('program.bin', 'image_sha256'), ('firmware.mif', 'bram_sha256')]:
            if digest(dest / name) != report['firmware'][variant][field]:
                raise RuntimeError('Firmware artifact changed since build')
        for traffic in (['quiet'] if variant in ['negative','battle-negative'] else ['quiet', 'scanout']):
            # 80 words/line is the existing 8-bit, 320-wide diagnostic scanout.
            # 3175 cycles x 525 lines approximates 60 Hz; 480 active lines.
            env = dict(os.environ, SCAN_ENABLE=str(int(traffic == 'scanout')), SCAN_PERIOD='3175',
                       SCAN_LEN='80', SCAN_ACTIVE='480', SCAN_TOTAL='525', SCAN_BASE_HW='0x1800000',
                       STRIKE_SCAN_PERIOD='1000000000')
            logfile = dest / (traffic + '.log')
            with logfile.open('w') as stream:
                proc = subprocess.run([str(simulator), 'program.bin', '40000000'], cwd=dest,
                                      env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=600)
            log = logfile.read_text()
            if variant in ['negative','battle-negative']:
                reason='battle independent return oracle' if variant=='battle-negative' else 'independent return oracle'
                if proc.returncode != 2 or 'VMHARNESS FAIL '+reason not in log:
                    raise RuntimeError('Negative oracle did not fail closed')
                report.setdefault('negative_tests',{})[variant] = dict(exit_code=proc.returncode, expected_failure=True)
                print('PASS',variant,'oracle: simulator rejected the wrong expected result', flush=True)
                continue
            if proc.returncode or 'VMHARNESS PASS HAL init' not in log or 'VMHARNESS FAIL' in log:
                raise RuntimeError(f'{variant}/{traffic}: simulator failed; inspect {logfile}')
            if 'WCONF: mism=0 spurious=0 exp_fifo=0 aw_fifo=0 run_left=0' not in log:
                raise RuntimeError('AXI write delivery failed')
            if 'R mismatches=0  scanout mismatches=0  rlast slips=0  orphan beats=0  DRAM strikes=0' not in log:
                raise RuntimeError('Memory read/protocol oracle failed')
            if 'SDRAM errors=0' not in log:
                raise RuntimeError('SDRAM chip timing/refresh oracle failed')
            if log.count('=== UART BEGIN ===') != 1 or log.count('=== UART END ===') != 1:
                raise RuntimeError('Missing UART transcript')
            uart = log.split('=== UART BEGIN ===', 1)[1].split('=== UART END ===', 1)[0]
            rows = []
            for match in re.finditer(r'^VMRESULT (\d+) (\d+) (\d+) ([0-9a-f]+) (\d+) (\d+) (\w+)$', uart, re.M):
                kind, round_, cycles, hash_, repeats, size, name = match.groups()
                kind, round_, cycles, repeats, size = map(int, (kind, round_, cycles, repeats, size))
                if kind not in range(8) or round_ not in range(3) or cycles <= 0 or repeats != 2 or hash_ != EXPECTED_HASHES[kind]:
                    raise RuntimeError('Invalid workload result')
                rows.append(dict(kind=kind, round=round_, cycles=cycles, hash=hash_, repeats=repeats,
                                 code_bytes=size, name=name, simulated_ms_per_execute=cycles / repeats / 100000))
            if len(rows) != 24 or {(r['kind'], r['round']) for r in rows} != {(k,r) for k in range(8) for r in range(3)}:
                raise RuntimeError('Missing or duplicate workloads')
            battle_rows=[]
            for match in re.finditer(r'^BATTLERESULT (\d+) (\d+) (\d+) ([0-9a-f]+) (\d+) (\d+) (\w+)$',uart,re.M):
                index,round_,cycles,hash_,repeats,ops,name=match.groups()
                index,round_,cycles,repeats,ops=map(int,(index,round_,cycles,repeats,ops))
                if index not in range(len(battles)) or round_ not in range(3):raise RuntimeError('Invalid battle result index')
                expected=battles[index]
                if cycles<=0 or repeats!=2 or ops!=expected['ops'] or hash_!=expected['hash'] or name!=expected['name']:
                    raise RuntimeError('Captured battle result oracle failed')
                battle_rows.append(dict(index=index,round=round_,cycles=cycles,hash=hash_,repeats=repeats,ops_per_execute=ops,
                                        name=name,game=expected['game'],phase=expected['phase'],simulated_ms_per_execute=cycles/repeats/100000))
            if len(battle_rows)!=3*len(battles) or {(r['index'],r['round']) for r in battle_rows}!={(i,r) for i in range(len(battles)) for r in range(3)}:
                raise RuntimeError('Missing or duplicate captured battle workloads')
            report['battle_runs'][variant+'/'+traffic]=battle_rows
            report['runs'][variant + '/' + traffic] = rows
            print('PASS', variant, traffic, f'24 synthetic + {len(battle_rows)} captured rows, exact hashes and memory oracles', flush=True)
    save(BUILD / 'results.json', report)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action', choices=['firmware', 'rtl', 'run', 'all'])
    ap.add_argument('--jobs', type=int, default=4)
    args = ap.parse_args()
    if args.jobs < 1: ap.error('--jobs must be positive')
    BUILD.mkdir(exist_ok=True)
    if args.action in ['firmware', 'all']: firmware()
    if args.action in ['rtl', 'all']: rtl(args.jobs)
    if args.action in ['run', 'all']: results()


if __name__ == '__main__':
    main()
