#!/usr/bin/env python3
"""Isolated Pico8Pocket cart smoke tests and same-ELF os25 frame replay."""
import argparse
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import run as base
import route as routes

IMAGE = 'undertale-vm-os25-frames:local'
PRIVATE = ROOT / 'experiments/pico8'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def docker(case, command, work='.', env=None):
    endpoint = os.environ.get('HARNESS_DOCKER_HOST', 'unix://' + str(Path.home() / '.config/colima/default/docker.sock'))
    args = ['docker', '--config', str(ROOT / 'build/docker-config'), '-H', endpoint,
            'run', '--rm', '-v', str(case) + ':/work', '-w', '/work/' + work]
    for name, value in (env or {}).items():
        args += ['-e', f'{name}={value}']
    return args + [IMAGE, *command]


def execute(command, log, timeout=600):
    if log.exists():
        raise ValueError('Preserve existing evidence: ' + str(log))
    with log.open('w') as stream:
        try:
            result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
            code = result.returncode
        except subprocess.TimeoutExpired:
            code = 'timeout'
    return code


def create(source, archive, name, route=None):
    base.verify_inputs()
    if not re.fullmatch('[a-z0-9][a-z0-9-]*', name):
        raise ValueError('Use a simple case name')
    case = PRIVATE / name
    case.mkdir(parents=True, exist_ok=False)
    source = source.resolve()
    for path in ['src', 'include', 'patches', 'mk']:
        shutil.copytree(source / path, case / 'source' / path)
    for path in ['miniz', 'z8lua']:
        shutil.copytree(source / '.deps/fake-08/libs' / path, case / 'source/.deps/fake-08/libs' / path,
                        ignore=shutil.ignore_patterns('.git'))
    shutil.copytree(ROOT / 'inputs/sdk/musl', case / 'musl')
    shutil.copytree(ROOT / 'inputs/sdk/include', case / 'sdk/include')
    shutil.copytree(ROOT / 'pico8', case / 'pico8', ignore=shutil.ignore_patterns('__pycache__'))
    if route:
        save(case / 'pico8/route.json', route)
    (case / 'platform').mkdir()
    for filename in ['bridge.c', 'start.S', 'link.ld']:
        shutil.copy2(ROOT / 'fullframe' / filename, case / 'platform' / filename)
    simulator = ROOT / 'build/fullframe/rtl/obj/Vtb_system'
    shutil.copy2(simulator, case / 'simulator')
    records = []
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            if not info.filename.lower().endswith(('.p8', '.p8.png')) or info.filename.startswith('__MACOSX/'):
                continue
            data = z.read(info)
            folder = case / 'carts' / f'{len(records):03d}'
            folder.mkdir(parents=True)
            (folder / 'cart.bin').write_bytes(data)
            records.append(dict(id=folder.name, name=info.filename, sha256=sha(folder / 'cart.bin'), size=len(data)))
    if not records:
        raise ValueError('No carts in ZIP')
    inventory = {str(p.relative_to(case)): sha(p) for p in case.rglob('*') if p.is_file()}
    manifest = dict(source_revision=subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip(),
                    source_status=subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain'], text=True),
                    archive_sha256=sha(archive), carts=records, files=inventory,
                    harness_revision=subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
                    frozen_input_manifest_sha256=sha(ROOT / 'input-manifest.json'),
                    cpu_lock_sha256=sha(ROOT / 'cpu-lock.json'),
                    cpu_sha256=sha(base.CPU), simulator_sha256=sha(simulator),
                    platform='os25 100MHz; shipped Pico8Pocket uses os20', warmup_frames=180,
                    measured_frames=3, native_frames=600, input_seed=7, route=route or {},
                    audio='fixed 48000/FPS pairs per frame; no hardware scheduling',
                    evidence_scope='cart runtime, indexed pixels, display palette and PCM; no OS/menu/SD/GPU')
    save(case / 'case.json', manifest)
    print('CASE', case, 'carts=', len(records), flush=True)
    return case


def checked(case):
    case = case.resolve()
    if not case.is_relative_to(PRIVATE.resolve()):
        raise ValueError('Expected an isolated case under experiments/pico8')
    manifest = json.loads((case / 'case.json').read_text())
    for name, digest in manifest['files'].items():
        if sha(case / name) != digest:
            raise ValueError('Snapshot changed: ' + name)
    binaries = case / 'build/binaries.json'
    if binaries.exists():
        for name, digest in json.loads(binaries.read_text()).items():
            if sha(case / name) != digest:
                raise ValueError('Changed binary: ' + name)
    return manifest


def build(case, reuse_native=None):
    checked(case)
    d = case / 'build'
    d.mkdir(exist_ok=True)
    p = case / 'source'
    z = p / '.deps/fake-08/libs/z8lua'
    names = 'eris lapi lauxlib lbaselib lcode lcorolib lctype ldblib ldebug ldo ldump lfunc lgc linit llex lmem lobject lopcodes lparser lpico8lib lstate lstring lstrlib ltable ltablib ltm lundump lvm lzio'.split()
    flags = ['-x', 'c++', '-std=c++17', '-O2', '-fwrapv', '-DPICO_NATIVE', '-DLUA_USE_LONGJMP',
               '-Wno-deprecated-declarations',
               '-I' + str(p / 'include'), '-I' + str(z), '-I' + str(p / '.deps/fake-08/libs/miniz'),
              ] + routes.flags(case / 'pico8')
    paths = [case / 'pico8/runner.cpp', *[p / 'src/runtime' / n for n in ['runtime.cpp', 'cart.c', 'cart_png.c', 'audio.c']],
             *[z / (n + '.c') for n in names], p / '.deps/fake-08/libs/miniz/miniz.c']
    objdir = d / 'native-objects'
    def compile_one(job):
        index, path = job
        obj = objdir / f'{index}.o'
        if execute(['c++', *flags, '-c', str(path), '-o', str(obj)], objdir / f'{index}.log'):
            raise ValueError('Native object failed: ' + str(path))
        return str(obj)
    if reuse_native:
        previous = reuse_native.resolve()
        old = checked(previous)
        current = checked(case)
        inputs = lambda m: {n: h for n, h in m['files'].items() if n.startswith('source/') or n == 'pico8/runner.cpp'}
        if inputs(old) != inputs(current) or old['carts'] != current['carts']:
            raise ValueError('Cannot import native evidence for different source or carts')
        shutil.copy2(previous / 'build/native', d / 'native')
        for cart in current['carts']:
            for filename in ['native-0.log', 'native-1.log', 'native.json']:
                src = previous / 'carts' / cart['id'] / filename
                shutil.copy2(src, case / 'carts' / cart['id'] / filename)
                if sha(src) != sha(case / 'carts' / cart['id'] / filename):
                    raise ValueError('Native import changed evidence')
        save(d / 'native-import.json', dict(case=str(previous), case_sha256=sha(previous / 'case.json'),
             binary_sha256=sha(d / 'native'), policy='identical native source, cart inventory and copied raw logs'))
    else:
        objdir.mkdir()
        with ThreadPoolExecutor(max_workers=4) as pool:
            objects = list(pool.map(compile_one, enumerate(paths)))
        if execute(['c++', *objects, '-lm', '-o', str(d / 'native')], d / 'native-build.log'):
            raise ValueError('Native link failed; inspect native-build.log')
    if execute(docker(case, ['python3', 'pico8/build.py']), d / 'rv32-build.log'):
        raise ValueError('RV32 build failed; inspect per-object and link logs')
    save(d / 'binaries.json', {str(p.relative_to(case)): sha(p) for p in [d / 'native', d / 'pico8/program.elf', d / 'pico8/bram.bin', d / 'pico8/build.json']})


def parse(log, count):
    text = log.read_text()
    if '=== UART BEGIN ===' in text:
        transcripts = re.findall(r'=== UART BEGIN ===\n(.*?)\n=== UART END ===', text, re.S)
        if len(transcripts) != 1:
            raise ValueError('Missing or duplicate UART transcript')
        text = transcripts[0] + '\n'
    rows = []
    cycles = []
    for match in re.finditer(r'^PICOFRAME (\d+) (\d+) ([0-9a-f]{8}) ([0-9a-f]{8}) ([0-9a-f]{8}) (\d+) (\d+) (\d+)$', text, re.M):
        frame, elapsed, pixel, palette, pcm, pairs, buttons, fps = match.groups()
        rows.append([int(frame), int(pixel, 16), int(palette, 16), int(pcm, 16), int(pairs), int(buttons), int(fps), 0])
        cycles.append(int(elapsed))
    if len(rows) != count or 'PICOHARNESS PASS HAL init' not in text or 'FRAMEHARNESS FAIL' in text:
        raise ValueError('Incomplete or failed cart run')
    first = 0 if count == 600 else 180
    if [r[0] for r in rows] != list(range(first, first + count)):
        raise ValueError('Wrong frame sequence')
    return rows, cycles


def native(case, cart):
    folder = case / 'carts' / cart['id']
    codes = []
    for repeat in range(2):
        codes.append(execute([str(case / 'build/native'), str(folder / 'cart.bin'), '600'], folder / f'native-{repeat}.log', timeout=120))
    status = dict(returncodes=codes, passed=False, completed=codes == [0, 0],
                  logs={f'native-{r}.log': sha(folder / f'native-{r}.log') for r in range(2)})
    if codes == [0, 0]:
        a, _ = parse(folder / 'native-0.log', 600)
        b, _ = parse(folder / 'native-1.log', 600)
        status.update(passed=a == b, repeat_equal=a == b, fps=a[-1][6], distinct_pixels=len({r[1] for r in a}))
    save(folder / 'native.json', status)
    return status


def capture(case, cart):
    folder = case / 'carts' / cart['id']
    codes = []
    for repeat in range(2):
        work = folder / f'qemu-{repeat}'
        work.mkdir()
        (work / 'cart.bin').symlink_to('../cart.bin')
        codes.append(execute(docker(case, ['qemu-riscv32', '-B', '0x100000000', '/work/build/pico8/program.elf'],
                                    str(work.relative_to(case))), work / 'capture.log', timeout=180))
    status = dict(returncodes=codes, passed=False,
                  logs={f'qemu-{r}/capture.log': sha(folder / f'qemu-{r}/capture.log') for r in range(2)})
    if codes == [0, 0]:
        a, _ = parse(folder / 'qemu-0/capture.log', 3)
        b, _ = parse(folder / 'qemu-1/capture.log', 3)
        hashes = [{name: sha(folder / f'qemu-{r}' / name) for name in ['checkpoint.bin', 'stack.bin', 'capture.log']} for r in range(2)]
        status.update(passed=a == b and hashes[0] == hashes[1], rows=a, repeat_hashes=hashes)
        host = json.loads((folder / 'native.json').read_text())
        if host['passed']:
            n, _ = parse(folder / 'native-0.log', 600)
            status['native_output_equal'] = n[180:183] == a
        if status['passed']:
            build = json.loads((case / 'build/pico8/build.json').read_text())
            checkpoint = bytearray((folder / 'qemu-0/checkpoint.bin').read_bytes())
            offset = build['symbols']['frame_expected'] - 0x10400000
            if offset < 0 or offset + 96 > len(checkpoint):
                raise ValueError('Expected oracle storage outside checkpoint')
            checkpoint[offset:offset+96] = struct.pack('<24I', *[x for row in a for x in row])
            (folder / 'program.bin').write_bytes(checkpoint)
            shutil.copy2(folder / 'qemu-0/stack.bin', folder / 'stack.bin')
            bram = bytearray(struct.pack('<I', 0x13) * 8192)
            struct.pack_into('<II', bram, 0, 0x104002b7, 0x00028067)
            hot = (case / 'build/pico8/bram.bin').read_bytes()
            bram[0x4000:0x4000+len(hot)] = hot
            (folder / 'firmware.mif').write_text('WIDTH=32;\nDEPTH=8192;\nADDRESS_RADIX=DEC;\nDATA_RADIX=HEX;\nCONTENT BEGIN\n' +
                ''.join(f'{i} : {struct.unpack_from("<I", bram, i*4)[0]:08X};\n' for i in range(8192)) + 'END;\n')
            status['prepared'] = {name: sha(folder / name) for name in ['program.bin', 'stack.bin', 'firmware.mif']}
    save(folder / 'capture.json', status)
    return status


def replay(case, cart, traffic='quiet', negative=False):
    folder = case / 'carts' / cart['id']
    capture = json.loads((folder / 'capture.json').read_text())
    if not capture['passed']:
        return dict(skipped='No repeatable RV32 capture')
    for name, digest in capture['prepared'].items():
        if sha(folder / name) != digest:
            raise ValueError('Changed replay input: ' + name)
    label = traffic + ('-negative' if negative else '')
    dest = folder / label
    dest.mkdir()
    for name in ['program.bin', 'stack.bin', 'firmware.mif']:
        (dest / name).symlink_to('../' + name)
    build = json.loads((case / 'build/pico8/build.json').read_text())
    env = dict(SCAN_ENABLE=int(traffic == 'scanout'), SCAN_PERIOD=3175, SCAN_LEN=80,
               SCAN_ACTIVE=480, SCAN_TOTAL=525, SCAN_BASE_HW='0x1800000',
               STRIKE_SCAN_PERIOD=1000000000, CACHE_PROFILE=0,
               FRAME_BAD_ORACLE=int(negative), FRAME_EXPECTED_ADDRESS=build['symbols']['frame_expected'])
    code = execute(docker(case, ['/work/simulator', 'program.bin', '50000000'], str(dest.relative_to(case)), env),
                   dest / 'rtl.log', timeout=900)
    return finish_replay(case, cart, traffic, negative, code)


def finish_replay(case, cart, traffic, negative, code):
    folder = case / 'carts' / cart['id']
    capture = json.loads((folder / 'capture.json').read_text())
    for name, digest in capture['prepared'].items():
        if sha(folder / name) != digest:
            raise ValueError('Changed replay input: ' + name)
    label = traffic + ('-negative' if negative else '')
    dest = folder / label
    if (dest / 'results.json').exists():
        raise ValueError('Preserve previous replay analysis')
    text = (dest / 'rtl.log').read_text()
    memory = all(token in text for token in ['SDRAM errors=0',
        'R mismatches=0  scanout mismatches=0  rlast slips=0  orphan beats=0  DRAM strikes=0',
        'WCONF: mism=0 spurious=0 exp_fifo=0 aw_fifo=0 run_left=0'])
    result = dict(returncode=code, memory_oracles=memory, passed=False, negative=negative,
                  log_sha256=sha(dest / 'rtl.log'))
    if negative:
        result['passed'] = code == 2 and memory and 'pixel/palette/PCM/input/FPS oracle' in text
    elif code == 0:
        rows, cycles = parse(dest / 'rtl.log', 3)
        result.update(passed=memory and rows == capture['rows'], rows=rows, cycles=cycles,
                      simulated_ms=[n / 100000 for n in cycles])
    save(dest / 'results.json', result)
    return result


def analyze(case, cart, traffic, negative):
    label = traffic + ('-negative' if negative else '')
    log = case / 'carts' / cart['id'] / label / 'rtl.log'
    verdict = re.findall(r'^cycles=\d+ PC=0x[0-9a-f]+ exit=(\d+)$', log.read_text(), re.M)
    if len(verdict) != 1:
        raise ValueError('Missing complete simulator verdict')
    return finish_replay(case, cart, traffic, negative, int(verdict[0]))


def parallel(case, records, fn, jobs):
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = {pool.submit(fn, case, cart): cart for cart in records}
        for future in as_completed(futures):
            cart = futures[future]
            try:
                result = future.result()
                print(cart['id'], cart['name'], 'PASS' if result.get('passed') else result, flush=True)
            except Exception as exc:
                print(cart['id'], cart['name'], 'ERROR', repr(exc), flush=True)
                save(case / 'carts' / cart['id'] / (fn.__name__ + '-error.json'), dict(error=repr(exc)))


def report(case):
    manifest = checked(case)
    results = []
    for cart in manifest['carts']:
        folder = case / 'carts' / cart['id']
        row = dict(cart)
        for phase, filename in [('native', 'native.json'), ('qemu', 'capture.json'),
                                ('rtl', 'quiet/results.json'), ('scanout', 'scanout/results.json'),
                                ('negative', 'quiet-negative/results.json')]:
            if (folder / filename).exists():
                row[phase] = json.loads((folder / filename).read_text())
                result = row[phase]
                for name, digest in result.get('logs', {}).items():
                    if sha(folder / name) != digest:
                        raise ValueError('Changed capture log: ' + name)
                if result.get('passed'):
                    if phase == 'native':
                        a, _ = parse(folder / 'native-0.log', 600)
                        b, _ = parse(folder / 'native-1.log', 600)
                        if a != b:
                            raise ValueError('Native repeat mismatch')
                    elif phase == 'qemu':
                        for r, hashes in enumerate(result['repeat_hashes']):
                            for name, digest in hashes.items():
                                if sha(folder / f'qemu-{r}' / name) != digest:
                                    raise ValueError('Changed QEMU evidence: ' + name)
                            rows, _ = parse(folder / f'qemu-{r}/capture.log', 3)
                            if rows != result['rows']:
                                raise ValueError('Changed QEMU rows')
                    else:
                        log = folder / Path(filename).parent / 'rtl.log'
                        if sha(log) != result['log_sha256']:
                            raise ValueError('Changed RTL log')
                        if phase != 'negative':
                            rows, cycles = parse(log, 3)
                            if rows != result['rows'] or cycles != result['cycles'] or rows != row['qemu']['rows']:
                                raise ValueError('Changed RTL result rows')
        if row.get('qemu', {}).get('passed'):
            row['target_fps'] = row['qemu']['rows'][-1][6]
        else:
            native_log = folder / 'native-0.log'
            targets = re.findall(r'^PICOFRAME \d+ \d+ [0-9a-f]{8} [0-9a-f]{8} [0-9a-f]{8} \d+ \d+ (\d+)$',
                                 native_log.read_text() if native_log.exists() else '', re.M)
            row['target_fps'] = int(targets[-1]) if targets else None
        timing = row.get('rtl', {})
        if timing.get('passed'):
            mean_cycles = sum(timing['cycles']) / len(timing['cycles'])
            row['runtime_capacity_fps'] = 100000000 / mean_cycles
            row['estimated_os25_fps'] = min(row['target_fps'], row['runtime_capacity_fps'])
            row['mean_simulated_frame_ms'] = mean_cycles / 100000
        results.append(row)
    save(case / 'results.json', dict(manifest=manifest, results=results))
    lines = ['# Pico8Pocket supplied-cart test results', '',
             f"Source revision: `{manifest['source_revision']}`. {len(results)} ZIP cart entries.", '',
             'The runtime smoke route runs 600 frames twice on the native host, with seed-7 scripted six-button input and fixed 48 kHz audio rendering. RV32 QEMU runs 180 warm-up frames, captures a checkpoint twice, and emits independent pixel, palette, PCM, input and FPS oracles for frames 180–182. RTL resumes that exact binary and process state.', '',
             '**Platform limit:** RTL is os25 at a simulated 100 MHz. Pico8Pocket ships os20. These tests do not establish shipped-core performance, whole-game compatibility, Pocket display/audio scheduling, SD saves or system-menu behavior.', '',
             '| Cart | Target FPS | Estimated os25 FPS | Native ×2 (600 frames) | QEMU ×2 (183 frames) | os25 RTL (3 frames) | Simulated frame ms |',
             '|---|---:|---:|---|---|---|---|']
    completed = sum(r.get('native', {}).get('completed', False) for r in results)
    repeatable = sum(r.get('native', {}).get('passed', False) for r in results)
    lines[6:6] = [f'Native execution completed both 600-frame runs for **{completed}/{len(results)}** carts; **{repeatable}/{len(results)}** produced identical repeats. NONREPEATABLE indicates completed execution with differing output, rather than a runtime error.', '']
    lines[8:8] = ['Game state is warmed for 180 frames; RTL CPU caches start cold. Timed intervals include the runtime step and fixed PCM render, excluding output hashes, UART and video presentation. Between-frame hashing/logging can affect later caches.', '']
    lines[10:10] = ['Estimated os25 FPS is `min(target FPS, 100,000,000 / mean runtime cycles)` over frames 180–182. It is a runtime-only estimate on os25, not measured Pocket FPS. Video presentation, OS scheduling and adaptive draw skipping are excluded. Some carts stay on titles/menus under this shared input route. Backrooms has no FPS estimate because it fails before the replay window.', '']
    for row in results:
        labels = []
        for phase in ['native', 'qemu', 'rtl']:
            r = row.get(phase)
            labels.append('PASS' if r and r.get('passed') else 'NONREPEATABLE' if r and r.get('completed') else 'FAIL' if r else
                          'SKIP (RV32 failure)' if phase == 'rtl' and row.get('qemu') and not row['qemu']['passed'] else '—')
        timings = ', '.join(f'{n:.2f}' for n in row.get('rtl', {}).get('simulated_ms', [])) or '—'
        target = str(row['target_fps']) if row['target_fps'] else '—'
        estimate = f"{row['estimated_os25_fps']:.1f}" if 'estimated_os25_fps' in row else '—'
        lines.append('| ' + row['name'].replace('|', '\\|') + ' | ' + target + ' | ' + estimate + ' | ' + ' | '.join(labels) + ' | ' + timings + ' |')
    lines += ['', '## Failures', '']
    for row in results:
        folder = case / 'carts' / row['id']
        for name in ['native-0.log', 'qemu-0/capture.log', 'quiet/rtl.log']:
            log = folder / name
            if log.exists():
                errors = [s.strip() for s in log.read_text(errors='replace').splitlines() if 'FRAMEHARNESS FAIL' in s]
                if errors:
                    lines.append(f"- `{row['name']}` ({name}): " + errors[0].replace('FRAMEHARNESS FAIL FRAMEHARNESS FAIL', 'FRAMEHARNESS FAIL'))
        if row.get('native', {}).get('completed') and not row['native']['passed']:
            lines.append(f"- `{row['name']}` completed both native runs, but pixel/palette/PCM rows differed. Native Lua hash seeding includes wall time and process addresses; RV32 uses a virtual clock and fixed addresses. Treat this as a reproducibility finding, not proof of a game bug.")
        if row.get('rtl') and not row['rtl']['passed']:
            lines.append(f"- `{row['name']}` RTL failed with return code {row['rtl']['returncode']}; see `carts/{row['id']}/quiet/rtl.log`.")
    if manifest.get('route'):
        lines += ['', '**Route override:** ' + json.dumps(manifest['route'], sort_keys=True) +
                  '. A setup expression is evaluated once after cart load; input `none` replaces the seed-7 route with no buttons in every frame.']
    previews = case / 'previews-final/contact-sheet.png'
    if previews.exists():
        lines += ['', '## Native frame previews', '',
                  f'[Open the contact sheet]({previews}). These use the native runtime at frame 182 where successful; Backrooms is shown at its last successful frame 121. Some carts remain at titles or menus under the shared input route. Grippy pixels vary with Lua hash seed.', '']
    lines += ['', f'Evidence directory: `{case}`. Raw carts, captures and logs remain private and ignored.', '']
    (case / 'REPORT.md').write_text('\n'.join(lines))
    with (case / 'FPS.csv').open('w', newline='') as stream:
        columns = ['id', 'cart', 'target_fps', 'estimated_os25_fps', 'runtime_capacity_fps',
                   'mean_simulated_frame_ms', 'native_completed', 'native_repeatable', 'qemu_repeatable', 'rtl_passed']
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in results:
            writer.writerow(dict(id=row['id'], cart=row['name'], target_fps=row['target_fps'],
                estimated_os25_fps=round(row['estimated_os25_fps'], 3) if 'estimated_os25_fps' in row else '',
                runtime_capacity_fps=round(row['runtime_capacity_fps'], 3) if 'runtime_capacity_fps' in row else '',
                mean_simulated_frame_ms=round(row['mean_simulated_frame_ms'], 3) if 'mean_simulated_frame_ms' in row else '',
                native_completed=row.get('native', {}).get('completed', False),
                native_repeatable=row.get('native', {}).get('passed', False),
                qemu_repeatable=row.get('qemu', {}).get('passed', False), rtl_passed=row.get('rtl', {}).get('passed', False)))
    print('REPORT', case / 'REPORT.md', flush=True)
    for phase in ['native', 'qemu', 'rtl', 'scanout', 'negative']:
        attempted = [r[phase] for r in results if phase in r]
        print(phase, sum(r.get('passed', False) for r in attempted), '/', len(attempted), flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action', choices=['create', 'build', 'native', 'capture', 'replay', 'analyze', 'report', 'all'])
    ap.add_argument('--case', type=Path)
    ap.add_argument('--source', type=Path)
    ap.add_argument('--archive', type=Path)
    ap.add_argument('--name')
    ap.add_argument('--setup', help='create: Lua expression evaluated once after cart load')
    ap.add_argument('--input', choices=['seed7', 'none'], default='seed7', help='create: button route')
    ap.add_argument('--cart', help='Exact cart ID, e.g. 000')
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--traffic', choices=['quiet', 'scanout'], default='quiet')
    ap.add_argument('--negative', action='store_true')
    ap.add_argument('--reuse-native-from', type=Path, help='Import byte-identical native source/cart evidence from an earlier case')
    ap.add_argument('--pending-only', action='store_true', help='Preserve completed phase results and run only pending carts')
    args = ap.parse_args()
    if args.action == 'create':
        if not all([args.source, args.archive, args.name]):
            ap.error('create requires --source, --archive, --name')
        create(args.source, args.archive, args.name, routes.validate(args.setup, args.input))
        return
    if not args.case:
        ap.error('Specify --case')
    case = args.case.resolve()
    manifest = checked(case)
    records = [r for r in manifest['carts'] if not args.cart or r['id'] == args.cart]
    if not records:
        ap.error('Unknown cart ID')
    def pending(filename):
        return [r for r in records if not args.pending_only or not (case / 'carts' / r['id'] / filename).exists()]
    if args.action in ['build', 'all']:
        build(case, args.reuse_native_from)
    if args.action in ['native', 'all']:
        parallel(case, pending('native.json'), native, args.jobs)
    if args.action in ['capture', 'all']:
        parallel(case, pending('capture.json'), capture, args.jobs)
    if args.action in ['replay', 'all']:
        label = args.traffic + ('-negative' if args.negative else '')
        parallel(case, pending(label + '/results.json'), lambda c, r: replay(c, r, args.traffic, args.negative), args.jobs)
    if args.action == 'analyze':
        parallel(case, records, lambda c, r: analyze(c, r, args.traffic, args.negative), args.jobs)
    if args.action in ['report', 'all']:
        report(case)


if __name__ == '__main__':
    main()
