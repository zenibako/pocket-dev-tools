#!/usr/bin/env python3
"""Register immutable replay baselines and check independently captured candidates."""
import argparse
import contextlib
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import struct
import subprocess
import tempfile
import uuid

import experiments

ROOT = Path(__file__).resolve().parent
FIELDS = ('game', 'window', 'first_frame', 'mode', 'kind', 'variant', 'profile',
          'native', 'alignment', 'framebuffer', 'clock_cost', 'audio', 'compiler',
          'adapter_sources', 'launcher_sha256')
MEMORY_CHECKS = ('WCONF: mism=0 spurious=0 exp_fifo=0 aw_fifo=0 run_left=0',
                 'R mismatches=0  scanout mismatches=0  rlast slips=0  orphan beats=0  DRAM strikes=0',
                 'SDRAM errors=0')


def read(path):
    return json.loads(path.read_text())


def local_case(path):
    root = Path(path).resolve()
    if not root.is_relative_to((ROOT / 'experiments/cases').resolve()):
        raise ValueError('Case must be inside this harness experiments/cases')
    return root


def extra_cflags(config):
    flags = config.get('extra_cflags', [])
    if not isinstance(flags, list) or any(not isinstance(token, str) for token in flags):
        raise ValueError('Extra flags metadata must be an ordered list of switches')
    return experiments.compiler_switches(shlex.join(flags))


def config_key(config):
    identity = {f: config[f] for f in FIELDS}
    identity['extra_cflags'] = extra_cflags(config)
    return json.dumps(identity, sort_keys=True)


def checked_path(root, name):
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Evidence path escapes case: ' + str(path))
    return path


def log_rows(text):
    rows = []
    for match in re.finditer(r'^FRAMERESULT (\d+) (\d+) ([0-9a-f]+) ([0-9a-f]+) ([0-9a-f]+) (\d+) (\d+) (\d+) ([0-9a-f]+)$', text, re.M):
        f, cycles, state, pixels, pcm, pairs, opcodes, events, trace = match.groups()
        rows.append(dict(oracle=[int(f), int(state, 16), int(pixels, 16), int(pcm, 16),
                                int(pairs), int(opcodes), int(events), int(trace, 16)],
                         cycles=int(cycles), simulated_ms=int(cycles) / 100000))
    if len(rows) != 3 or 'FRAMEHARNESS PASS HAL init' not in text or 'FRAMEHARNESS FAIL' in text:
        raise ValueError('Incomplete or failed frame log')
    return rows


def rtl_uart(text):
    begin, end = '=== UART BEGIN ===', '=== UART END ==='
    if text.count(begin) != 1 or text.count(end) != 1 or text.index(begin) >= text.index(end):
        raise ValueError('Incomplete or ambiguous RTL UART summary')
    if 'FRAMEHARNESS FAIL' in text:
        raise ValueError('RTL frame log failed outside or inside UART summary')
    return text.split(begin, 1)[1].split(end, 1)[0]


def verify_pixels(folder, index, oracle):
    # frame_ppm emits this exact P6 header and tightly packed RGB555 pixels.
    # Its mode validator allows at most 640x480 and fixes stride to width*2.
    ppm = (folder / f'frame-{index}.ppm').read_bytes()
    header = re.match(rb'P6\n([1-9][0-9]*) ([1-9][0-9]*)\n255\n', ppm)
    if not header:
        raise ValueError('Invalid PPM pixel geometry/header')
    width, height = map(int, header.groups())
    if width > 640 or height > 480:
        raise ValueError('PPM pixel geometry exceeds renderer bounds')
    pixels = (folder / f'frame-{index}.rgb555').read_bytes()
    if len(pixels) != width * height * 2:
        raise ValueError('Incomplete RGB555 pixel bytes for PPM geometry')
    rgb = ppm[header.end():]
    if len(rgb) != width * height * 3:
        raise ValueError('Incomplete PPM pixel payload')
    digest = 2166136261
    for byte in pixels:
        digest = ((digest ^ byte) * 16777619) & 0xffffffff
    if digest != oracle:
        raise ValueError('Raw RGB555 pixel oracle differs from capture log')
    # Match frame_ppm's channel conversion, including its zero low three bits.
    expected = bytearray()
    for (pixel,) in struct.iter_unpack('<H', pixels):
        expected.extend((((pixel >> 10) & 31) << 3, ((pixel >> 5) & 31) << 3,
                         (pixel & 31) << 3))
    if rgb != expected:
        raise ValueError('PPM pixels differ from raw RGB555 capture')
    return [width, height]


def compare_cases(baseline, candidate, output):
    # Keep the existing raw-byte comparison and enrich its durable report with
    # geometry: equal flat pixel bytes can represent different shaped images.
    with contextlib.redirect_stdout(io.StringIO()):
        experiments.compare(argparse.Namespace(baseline=Path(baseline['case']),
                            candidate=Path(candidate['case']), output=output))
    report = read(output)
    geometry_differences = []
    for index, (old, new) in enumerate(zip(baseline['geometry'], candidate['geometry'])):
        if old == new:
            continue
        frame = baseline['config']['first_frame'] + index
        folder = output.parent / f'{output.stem}-frame-{frame}'
        folder.mkdir(parents=True, exist_ok=True)
        images = {}
        for name, record in [('baseline', baseline), ('candidate', candidate)]:
            config = record['config']
            source = (Path(record['case']) / 'build/fullframe' / config['game'] / config['variant']
                      / f'repeat-0/frame-{index}.ppm')
            target = folder / (name + '.ppm')
            shutil.copy2(source, target)
            images[name] = str(target.resolve())
        geometry_differences.append(dict(frame=frame, field='geometry', baseline=old,
                                        candidate=new, images=images))
    report['differences'] = sorted(geometry_differences + report['differences'], key=lambda d: d['frame'])
    report['identical'] = not report['differences']
    report['first_difference'] = report['differences'][0] if report['differences'] else None
    report['compared_fields'].append('frame width/height')
    experiments.save(output, report)
    first = report['first_difference']
    print('identical' if report['identical'] else f"different: frame {first['frame']} field {first['field']}", flush=True)
    return report['identical']


def tooling_identity(config):
    adapter = {p.name: experiments.sha(p) for p in sorted((ROOT / 'bench').iterdir())
               if p.is_file() and p.suffix in ['.c', '.S', '.py']}
    if adapter != config['adapter_sources'] or experiments.sha(ROOT / 'experiments.py') != config['launcher_sha256']:
        raise ValueError('Current adapter or launcher changed; establish a new verified baseline')
    # Include the shared launch/capture/linker code copied into revision cases.
    paths = [ROOT / n for n in ['run.py', 'harness.py', 'capture.py', 'battle_fixtures.py',
             'battle_replay.c', 'battle_replay.h', 'runtime.c', 'services.c', 'workloads.c',
             'start.S', 'link.ld', 'Dockerfile', 'cpu-lock.json', 'input-manifest.json']]
    for folder in ['capture', 'fullframe']:
        paths.extend(p for p in (ROOT / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    return {str(p.relative_to(ROOT)): experiments.sha(p) for p in sorted(paths) if p.exists()}


def compiler_identity(config, version):
    if config['compiler'] == 'container':
        command = experiments.docker(ROOT, 'true')
        prefix = command[:command.index('run')]
        image = subprocess.check_output([*prefix, 'image', 'inspect', '--format', '{{.Id}}',
                                        'undertale-vm-os25-frames:local'], text=True).strip()
        if not image:
            raise ValueError('Container toolchain image identity unavailable')
        actual = subprocess.check_output(experiments.docker(ROOT, 'riscv64-unknown-elf-gcc', '--version'),
                                         text=True).splitlines()[0]
        if actual != version:
            raise ValueError('Current container compiler differs from captured toolchain')
        return dict(image=image, compiler_version=version)
    compiler = Path(config['compiler'])
    if not compiler.is_absolute() or not compiler.is_file():
        raise ValueError('Compiler must be an existing absolute path')
    actual = subprocess.check_output([str(compiler), '--version'], text=True).splitlines()[0]
    if actual != version:
        raise ValueError('Current compiler version differs from captured toolchain')
    tools = [compiler]
    if compiler.name.endswith('gcc'):
        tools.extend(compiler.with_name(compiler.name[:-3] + n) for n in ['as', 'ld', 'nm', 'objcopy'])
    return dict(compiler_version=actual,
                binaries={str(p): experiments.sha(p) for p in tools if p.is_file()})


def inspect_case(path, traffic):
    root = local_case(path)
    config, directory, capture = experiments.checked_capture(root)
    extra_cflags(config)
    if config.get('workload') or config['audio'] != 'fixed':
        raise ValueError('Routine regression requires complete game frames and fixed audio')
    if config['window'] not in experiments.WINDOWS.get(config['game'], {}):
        raise ValueError('Unsupported game/window configuration')
    if config['first_frame'] != experiments.WINDOWS[config['game']][config['window']]:
        raise ValueError('Frame configuration differs from supported route')
    frames = [config['first_frame'] + i for i in range(3)]
    rows = capture['rows']
    result = read(directory / (traffic + '-results.json'))
    if (len(rows) != 3 or any(len(r) != 8 for r in rows) or [r[0] for r in rows] != frames
            or len(result['rows']) != 3 or len(result['frame_costs']) != 3):
        raise ValueError('Incomplete regression frame rows')
    snapshot = read(root / 'snapshot.json')
    manifest = read(root / 'input-manifest.json')
    build = read(directory / 'build.json')
    if (snapshot['manifest_sha256'] != experiments.sha(root / 'input-manifest.json')
            or config['snapshot_sha256'] != experiments.sha(root / 'snapshot.json')
            or snapshot['revision'] != manifest['source_revisions']['butterscotch-mirror']
            or snapshot['parent_manifest_sha256'] != experiments.sha(ROOT / 'input-manifest.json')
            or read(root / 'case-ready.json')['config_sha256'] != experiments.sha(root / 'experiment.json')):
        raise ValueError('Snapshot/configuration provenance changed')
    if (capture['build'] != build or build['config'] != config or capture['seed'] != 7
            or capture['game'] != config['game'] or capture['variant'] != config['variant']
            or result['game'] != config['game'] or result['variant'] != config['variant']
            or result['traffic'] != traffic or result['build_kind'] != config['kind']
            or result['compiler_version'] != build['compiler_version']
            or build['vm_trace'] != (config['kind'] == 'trace')
            or build['timing_audio_hash'] != (config['kind'] == 'trace')):
        raise ValueError('Build/capture configuration changed')
    ignored = [3] if config['kind'] == 'timing' else []
    if config['kind'] not in ['trace', 'timing'] or result['oracle_excluded_fields'] != ignored:
        raise ValueError('Unexpected regression oracle exclusions')
    if len(capture['repeats']) != 2:
        raise ValueError('Incomplete repeat capture evidence')
    required = ['checkpoint.bin', 'stack.bin', 'checkpoint-info.bin']
    required += [f'frame-{i}.{ext}' for i in range(3) for ext in ['rgb555', 'pcm', 'ppm']]
    if config['framebuffer'] == 'uncached':
        required.append('framebuffer.bin')
    for name in required:
        if any(name not in r for r in capture['repeats']):
            raise ValueError('Incomplete repeat artifact: ' + name)
        if capture['repeats'][0][name] != capture['repeats'][1][name]:
            raise ValueError('Non-reproducible repeat capture: ' + name)
    geometry = []
    for repeat in range(2):
        if 'capture.log' not in capture['repeats'][repeat]:
            raise ValueError('Incomplete repeat capture log')
        observed = log_rows((directory / f'repeat-{repeat}/capture.log').read_text())
        if [r['oracle'] for r in observed] != rows:
            raise ValueError('Capture rows differ from raw repeat log')
        for index, row in enumerate(rows):
            dimensions = verify_pixels(directory / f'repeat-{repeat}', index, row[2])
            if repeat == 0:
                geometry.append(dimensions)
    replay_text = (directory / (traffic + '.log')).read_text()
    uart = rtl_uart(replay_text)
    observed = log_rows(uart)
    if observed != result['rows']:
        raise ValueError('Replay rows differ from raw log')
    if any(token not in replay_text for token in MEMORY_CHECKS):
        raise ValueError('Incomplete memory-oracle evidence')
    if any(r['cycles'] <= 0 or any(r['oracle'][i] != expected[i] for i in range(8) if i not in ignored)
           for r, expected in zip(result['rows'], rows)):
        raise ValueError('Replay oracle differs from capture')
    if [r['frame'] for r in result['frame_costs']] != frames:
        raise ValueError('Incomplete frame cost rows')
    costs = [dict(frame=int(f), clock_reads=int(c), audio_pairs_consumed=int(n), audio_underrun_pairs=int(u))
             for f, c, n, u in re.findall(r'^FRAMECOST (\d+) (\d+) (\d+) (\d+)$', uart, re.M)]
    if costs != result['frame_costs']:
        raise ValueError('Frame cost counters differ from raw replay log')
    if not (directory / 'negative-results.json').exists():
        raise ValueError('Missing negative-oracle rejection')
    negative = read(directory / 'negative-results.json')
    if (negative['game'] != config['game'] or negative['variant'] != config['variant']
            or 'FRAMEHARNESS FAIL frame ' not in (directory / 'negative.log').read_text()):
        raise ValueError('Invalid negative-oracle rejection')
    tooling = tooling_identity(config)
    for name, digest in config['adapter_sources'].items():
        if experiments.sha(checked_path(root, 'fullframe/' + name)) != digest:
            raise ValueError('Copied adapter changed: ' + name)
    for name, digest in tooling.items():
        if name == 'input-manifest.json' or (name.startswith('fullframe/')
                and Path(name).name in config['adapter_sources']):
            continue
        if experiments.sha(checked_path(root, name)) != digest:
            raise ValueError('Copied shared tooling changed: ' + name)
    # Existing experiment reporting verifies prepared binary, RTL, capture and log hashes.
    # Run it after shape checks so an empty result cannot be mistaken for success.
    with tempfile.TemporaryDirectory(prefix='regression-report-', dir=ROOT / 'build') as tmp:
        output = Path(tmp) / 'report.json'
        experiments.report_cases(argparse.Namespace(cases=[root], traffic=traffic, output=output))
        record = read(output)['cases'][0]
    if not record['negative_oracle_rejected']:
        raise ValueError('Missing negative-oracle rejection')
    # Freeze metadata and every raw evidence/source file checked above. Changes are
    # rejected even when someone rewrites their local manifest to match new bytes.
    names = ['experiment.json', 'snapshot.json', 'input-manifest.json', 'case-ready.json',
             'build/fullframe/rtl/rtl.json', 'build/fullframe/rtl/main.cpp',
             'build/fullframe/rtl/obj/Vtb_system', 'build/rtl/rtl.json']
    names += list(build['sources'])
    names += ['fullframe/' + name for name in config['adapter_sources']]
    names += [str((directory / n).relative_to(root)) for n in ['build.json', 'capture.json', 'prepared.json',
              'program.elf', 'program.bin', 'stack.bin', 'firmware.mif', traffic + '.log',
              traffic + '-results.json', 'negative.log', 'negative-results.json']]
    for repeat, files in enumerate(capture['repeats']):
        names += [str((directory / f'repeat-{repeat}' / n).relative_to(root)) for n in files]
    if config['framebuffer'] == 'uncached':
        names.append(str((directory / 'framebuffer.bin').relative_to(root)))
    return dict(case=str(root), revision=snapshot['revision'], config=config,
                geometry=geometry,
                compiler=compiler_identity(config, build['compiler_version']), tooling=tooling,
                platform={field: read(root / 'build/fullframe/rtl/rtl.json')[field] for field in
                          ['simulator_sha256', 'generator_sha256', 'source_sha256', 'leaf_rtl_sha256']},
                evidence={n: experiments.sha(checked_path(root, n)) for n in sorted(set(names))},
                mean_simulated_ms=record['mean_simulated_ms'])


def inspect_roster(cases, traffic):
    if not cases:
        raise ValueError('Empty regression roster')
    (ROOT / 'build').mkdir(exist_ok=True)
    records = [inspect_case(c, traffic) for c in cases]
    if len({config_key(r['config']) for r in records}) != len(records):
        raise ValueError('duplicate configuration in regression roster')
    if len({r['revision'] for r in records}) != 1:
        raise ValueError('Mixed source revisions in regression roster')
    return records


def baseline(args):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', args.name):
        raise ValueError('Baseline name must contain lowercase letters, digits and hyphens')
    path = ROOT / 'build/regressions/baselines' / (args.name + '.json')
    if path.exists():
        raise ValueError('Baseline exists; choose a new name')
    records = inspect_roster(args.cases, args.traffic)
    value = dict(schema=1, name=args.name, revision=records[0]['revision'], traffic=args.traffic,
                 cases=records, scope='Simulated replay only; no physical Pocket validation')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        stream.write(json.dumps(value, indent=2) + '\n')
    print('BASELINE', path, flush=True)
    return path


def fresh_candidates(args, records, traffic, run_id):
    if args.jobs < 1:
        raise ValueError('jobs must be positive')
    # The existing launchers propagate this setting to nested case capture calls.
    if 'HARNESS_DOCKER_HOST' not in os.environ:
        for socket in [Path.home() / '.config/colima/default/docker.sock', Path.home() / '.colima/default/docker.sock']:
            if socket.exists():
                os.environ['HARNESS_DOCKER_HOST'] = 'unix://' + str(socket)
                break
    name = 'regression-' + run_id
    experiments.snapshot(argparse.Namespace(name=name, revision=args.revision, repo=args.repo, patch=None))
    cases = []
    for record in records:
        config = record['config']
        options = {f: config[f] for f in FIELDS if f not in ['first_frame', 'adapter_sources', 'launcher_sha256', 'kind']}
        options['extra_cflags'] = shlex.join(extra_cflags(config))
        run = argparse.Namespace(**options, snapshot=name, traffic=traffic, stage='all', negative=False, jobs=args.jobs)
        root = experiments.run_case(run, config['kind'])
        run.stage, run.negative = 'replay', True
        experiments.run_case(run, config['kind'])
        cases.append(root)
    return cases


def check(args):
    index = read(args.baseline)
    if index['schema'] != 1 or not index['cases'] or index['revision'] != index['cases'][0]['revision']:
        raise ValueError('Invalid baseline index')
    # Verify every frozen file before reading current metadata or running anything.
    for record in index['cases']:
        root = local_case(record['case'])
        for name, digest in record['evidence'].items():
            if experiments.sha(checked_path(root, name)) != digest:
                raise ValueError('Baseline evidence changed: ' + name)
    records = inspect_roster([r['case'] for r in index['cases']], index['traffic'])
    if records != index['cases']:
        raise ValueError('Baseline tooling/compiler/evidence changed')
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:12]
    directory = ROOT / 'build/regressions/checks' / run_id
    directory.mkdir(parents=True)
    try:
        cases = args.candidate_cases
        if not cases:
            if not args.repo or not args.revision:
                raise ValueError('Supply --candidate-cases or both --repo and --revision')
            cases = fresh_candidates(args, records, index['traffic'], run_id.lower())
        candidates = inspect_roster(cases, index['traffic'])
        by_config = {config_key(r['config']): r for r in candidates}
        if set(by_config) != {config_key(r['config']) for r in records}:
            raise ValueError('Candidate configuration roster differs from baseline')
        passed, comparisons = True, []
        for i, base in enumerate(records):
            candidate = by_config[config_key(base['config'])]
            if candidate['case'] in {r['case'] for r in records}:
                raise ValueError('Candidate must be independent of baseline cases')
            if candidate['compiler'] != base['compiler'] or candidate['tooling'] != base['tooling']:
                raise ValueError('Candidate compiler/toolchain or tooling differs')
            if candidate['platform'] != base['platform']:
                raise ValueError('Candidate simulator/RTL platform differs from baseline')
            output = directory / f'comparison-{i:02d}.json'
            identical = compare_cases(base, candidate, output)
            passed = passed and identical
            comparisons.append(dict(report=str(output), identical=identical,
                baseline_mean_simulated_ms=base['mean_simulated_ms'],
                candidate_mean_simulated_ms=candidate['mean_simulated_ms']))
        experiments.report_cases(argparse.Namespace(cases=[Path(r['case']) for r in records + candidates],
                                 traffic=index['traffic'], output=directory / 'results.json'))
        experiments.save(directory / 'check.json', dict(passed=passed, baseline=str(Path(args.baseline).resolve()),
                         baseline_sha256=experiments.sha(Path(args.baseline)), comparisons=comparisons,
                         timing='Simulated only; no automatic performance threshold', device_validated=False))
        print('CHECK', directory, 'PASS' if passed else 'FAIL', flush=True)
        return passed
    except Exception as error:
        experiments.save(directory / 'check.json', dict(passed=False, error=str(error), device_validated=False))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    register = commands.add_parser('baseline', help='Register existing verified cases once')
    register.add_argument('--name', required=True)
    register.add_argument('--cases', nargs='+', type=Path, required=True)
    register.add_argument('--traffic', choices=['quiet', 'scanout'], default='quiet')
    run = commands.add_parser('check', help='Compare independent candidates to a frozen baseline')
    run.add_argument('--baseline', type=Path, required=True)
    source = run.add_mutually_exclusive_group(required=True)
    source.add_argument('--repo', type=Path)
    source.add_argument('--candidate-cases', nargs='+', type=Path)
    run.add_argument('--revision')
    run.add_argument('--jobs', type=int, default=1)
    args = parser.parse_args()
    if args.command == 'check' and bool(args.repo) != bool(args.revision):
        parser.error('--repo and --revision must be supplied together')
    try:
        if args.command == 'baseline':
            baseline(args)
        elif not check(args):
            parser.exit(2)
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
