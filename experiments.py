#!/usr/bin/env python3
"""Create isolated revision snapshots, replay windows and compare actual outputs."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import struct
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parent
PRIVATE = ROOT / 'experiments'
WINDOWS = {'undertale': {'flowey': 2400},
           'deltarune': {'field': 2800, 'bmenu': 3120, 'dodge': 3323,
                        'spades': 490, 'castle': 150}}
# Controlled recreations, not imported player progress. Setup occurs well before
# the checkpoint so the sampled frames cover warmed, sustained scene work.
SCENES = {name: dict(room=room, setup_frame=29, jump_frame=30,
                    globals='darkzone=1,char[1]=' + ('0' if name == 'spades' else '2') +
                            ',char[2]=0,plot=60,interact=0',
                    input=','.join(f'{frame}:Z' for frame in range(40, 490, 15)) if name == 'spades' else '',
                    require_spades=name == 'spades', benchmark_diagnostics=False)
          for name, room in [('spades', 43), ('castle', 46)]}


def compiler_switches(value):
    """Only explicit preprocessor experiments; never compiler file/plugin options."""
    tokens = shlex.split(value)
    for token in tokens:
        if not re.fullmatch(r'-D[A-Za-z_][A-Za-z_0-9]*(?:=[A-Za-z_0-9.+-]+)?|-U[A-Za-z_][A-Za-z_0-9]*', token):
            raise ValueError('Extra flags must be single -DNAME[=VALUE] or -UNAME tokens: ' + token)
    return tokens


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def copy_tree(source, destination):
    # APFS clones retain isolation without duplicating every private asset block.
    if destination.exists():
        raise ValueError('Destination already exists: ' + str(destination))
    destination.parent.mkdir(parents=True, exist_ok=True)
    if os.uname().sysname == 'Darwin':
        subprocess.run(['cp', '-cR', str(source), str(destination)], check=True)
    else:
        shutil.copytree(source, destination, symlinks=True)
    for link in destination.rglob('*'):
        if link.is_symlink() and not link.resolve().is_relative_to(destination.resolve()):
            raise ValueError('Copied link escapes isolated directory: ' + str(link))


def tooling(destination):
    destination.mkdir(parents=True, exist_ok=True)
    # Copy tooling only. Input roots, capture directories and Git metadata are
    # never linked into a case; Docker receives exactly this case's directory.
    for name in ['run.py', 'harness.py', 'capture.py', 'battle_fixtures.py', 'battle_replay.c',
                 'battle_replay.h', 'runtime.c', 'services.c', 'workloads.c', 'start.S',
                 'link.ld', 'Dockerfile', 'cpu-lock.json']:
        shutil.copy2(ROOT / name, destination / name)
    for name in ['capture', 'fullframe']:
        shutil.copytree(ROOT / name, destination / name, ignore=shutil.ignore_patterns('__pycache__'))
    for name in ['build.py', 'rtl.py', 'runtime.c', 'platform.c', 'bridge.c', 'start.S']:
        shutil.copy2(ROOT / 'bench' / name, destination / 'fullframe' / name)
    (destination / 'build/docker-config').mkdir(parents=True)
    (destination / 'build/docker-config/config.json').write_text('{"auths":{}}\n')


def verify_inputs(root):
    manifest = json.loads((root / 'input-manifest.json').read_text())
    for name, digest in manifest['sources'].items():
        path = root / name
        if not path.resolve().is_relative_to(root.resolve()) or sha(path) != digest:
            raise ValueError('Snapshot input changed: ' + name)


def snapshot(args):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', args.name):
        raise ValueError('Snapshot name must contain lowercase letters, digits and hyphens')
    verify_inputs(ROOT)
    destination = PRIVATE / 'snapshots' / args.name
    if destination.exists():
        raise ValueError('Snapshot exists; choose a new name to preserve its evidence')
    revision = subprocess.check_output(['git', '-C', str(args.repo), 'rev-parse', args.revision + '^{commit}'], text=True).strip()
    archive = subprocess.check_output(['git', '-C', str(args.repo), 'archive', revision, 'src', 'vendor'])
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.bootstrap-snapshot-', dir=ROOT) as temp:
        staging = Path(temp)
        copy_tree(ROOT / 'inputs', staging / 'inputs')
        runner = staging / 'inputs/butterscotch'
        old_revision = json.loads((ROOT / 'input-manifest.json').read_text())['source_revisions']['butterscotch-mirror']
        old_files = subprocess.check_output(['git', '-C', str(args.repo), 'ls-tree', '-r', '--name-only', old_revision, 'src', 'vendor'], text=True).splitlines()
        for name in old_files:
            file = runner / name
            if file.is_file():
                file.unlink()
        exported = {}
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            for item in tar:
                name = Path(item.name)
                if name.is_absolute() or '..' in name.parts or name.parts[0] not in ['src', 'vendor']:
                    raise ValueError('Unsafe Git archive path')
                if item.isdir():
                    (runner / name).mkdir(parents=True, exist_ok=True)
                elif item.isfile():
                    path = runner / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(tar.extractfile(item).read())
                    path.chmod(item.mode)
                    exported[item.name] = sha(path)
                else:
                    raise ValueError('Unsupported Git archive link: ' + item.name)
        patch_hash = None
        if args.patch:
            for line in args.patch.read_text().splitlines():
                if line.startswith(('--- ', '+++ ')):
                    name = line[6:].split('\t')[0]
                    path = Path(name)
                    if '..' in path.parts or path.is_absolute() or path.parts[0] not in ['src', 'vendor'] or path.suffix not in ['.c', '.h']:
                        raise ValueError('Patch must change only runner source .c/.h files')
            subprocess.run(['git', 'apply', '--directory=' + str(runner.relative_to(ROOT)), str(args.patch.resolve())], cwd=ROOT, check=True)
            patch_hash = sha(args.patch)
        manifest = json.loads((ROOT / 'input-manifest.json').read_text())
        manifest['source_revisions']['butterscotch-mirror'] = revision
        manifest['sources'] = {name: digest for name, digest in manifest['sources'].items()
                               if not name.startswith('inputs/butterscotch/')}
        for file in sorted(runner.rglob('*')):
            if file.is_file():
                manifest['sources'][str(file.relative_to(staging))] = sha(file)
        save(staging / 'input-manifest.json', manifest)
        save(staging / 'snapshot.json', dict(name=args.name, revision=revision, parent_manifest_sha256=sha(ROOT / 'input-manifest.json'),
                                           exported_sources=exported, patch_sha256=patch_hash,
                                           manifest_sha256=sha(staging / 'input-manifest.json')))
        staging.rename(destination)
    verify_inputs(destination)
    print('Snapshot', args.name, revision, 'preserved independently at', destination, flush=True)


def docker(root, *command):
    endpoint = os.environ.get('HARNESS_DOCKER_HOST', 'unix://' + str(Path.home() / '.config/colima/default/docker.sock'))
    return ['docker', '--config', str(root / 'build/docker-config'), '-H', endpoint,
            'run', '--rm', '-v', str(root) + ':/work', '-w', '/work',
            'undertale-vm-os25-frames:local', *command]


def platform():
    # Simulator code is independent of game revision/window/mode. Build once per
    # adapter hash and copy its verified artifacts into each isolated case.
    version = sha(ROOT / 'bench/rtl.py')[:16]
    root = PRIVATE / 'platform' / version
    if not root.exists():
        tooling(root)
        copy_tree(ROOT / 'inputs', root / 'inputs')
        shutil.copy2(ROOT / 'input-manifest.json', root / 'input-manifest.json')
        copy_tree(ROOT / 'build/rtl', root / 'build/rtl')
    output = root / 'build/fullframe/rtl/rtl.json'
    if not output.exists():
        subprocess.run(docker(root, 'python3', 'fullframe/rtl.py', 'rtl', '--jobs', '4'), check=True)
    return root


def create_case(args, kind):
    extra_cflags = compiler_switches(getattr(args, 'extra_cflags', ''))
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', args.snapshot):
        raise ValueError('Unsafe snapshot name')
    source = PRIVATE / 'snapshots' / args.snapshot
    verify_inputs(source)
    if args.window not in WINDOWS[args.game]:
        raise ValueError('Window is unavailable for this game')
    config = dict(snapshot=args.snapshot, game=args.game, window=args.window,
                  first_frame=WINDOWS[args.game][args.window], mode=args.mode, kind=kind,
                  variant=args.variant, profile=args.profile, alignment=args.alignment,
                  native=('enabled' if args.profile == 'port' else 'disabled') if args.native == 'profile' else args.native,
                  framebuffer=args.framebuffer, clock_cost=args.clock_cost, audio=args.audio,
                  compiler=args.compiler, snapshot_sha256=sha(source / 'snapshot.json'),
                  adapter_sources={p.name: sha(p) for p in sorted((ROOT / 'bench').iterdir()) if p.is_file() and p.suffix in ['.c', '.S', '.py']},
                  launcher_sha256=sha(Path(__file__)))
    if extra_cflags:
        config['extra_cflags'] = extra_cflags
    if args.window in SCENES:
        config['scene'] = SCENES[args.window]
    key = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:16]
    root = PRIVATE / 'cases' / (args.snapshot + '-' + args.game + '-' + args.window + '-' + args.mode + '-' + kind + '-' + key)
    if root.exists():
        if json.loads((root / 'experiment.json').read_text()) != config:
            raise ValueError('Case configuration changed')
        if not (root / 'case-ready.json').exists():
            raise ValueError('Incomplete case; preserve it and create a new snapshot name')
        verify_inputs(root)
        return root
    runtime = platform()
    tooling(root)
    copy_tree(source / 'inputs', root / 'inputs')
    for name in ['input-manifest.json', 'snapshot.json']:
        shutil.copy2(source / name, root / name)
    save(root / 'experiment.json', config)
    copy_tree(runtime / 'build/rtl', root / 'build/rtl')
    copy_tree(runtime / 'build/fullframe/rtl', root / 'build/fullframe/rtl')
    save(root / 'case-ready.json', dict(config_sha256=sha(root / 'experiment.json')))
    return root


def capture_case(root, config):
    game, variant = config['game'], config['variant']
    subprocess.run(['python3', str(root / 'fullframe/run.py'), 'capture', '--game', game, '--variant', variant], check=True)
    directory = root / 'build/fullframe' / game / variant
    manifest = json.loads((directory / 'capture.json').read_text())
    for repeat in range(2):
        for index in range(3):
            for extension in ['rgb555', 'pcm']:
                name = f'frame-{index}.{extension}'
                digest = sha(directory / f'repeat-{repeat}' / name)
                manifest['repeats'][repeat][name] = digest
                if repeat and digest != manifest['repeats'][0][name]:
                    raise ValueError('Non-reproducible raw ' + extension + ' capture')
        if config['framebuffer'] == 'uncached':
            manifest['repeats'][repeat]['framebuffer.bin'] = sha(directory / f'repeat-{repeat}/framebuffer.bin')
    if config['framebuffer'] == 'uncached' and manifest['repeats'][0]['framebuffer.bin'] != manifest['repeats'][1]['framebuffer.bin']:
        raise ValueError('Non-reproducible framebuffer checkpoint')
    save(directory / 'capture.json', manifest)


def run_case(args, kind):
    root = create_case(args, kind)
    config = json.loads((root / 'experiment.json').read_text())
    directory = root / 'build/fullframe' / args.game / args.variant
    if args.stage in ['build', 'all']:
        if args.compiler == 'container':
            subprocess.run(docker(root, 'python3', 'fullframe/build.py', '--game', args.game, '--variant', args.variant), check=True)
        else:
            subprocess.run(['python3', str(root / 'fullframe/build.py'), '--game', args.game,
                            '--variant', args.variant, '--compiler', args.compiler], check=True)
    if args.stage in ['capture', 'all']:
        capture_case(root, config)
    if args.stage in ['prepare', 'all']:
        subprocess.run(docker(root, 'python3', 'fullframe/rtl.py', 'prepare', '--game', args.game, '--variant', args.variant), check=True)
    if args.stage in ['replay', 'all']:
        subprocess.run(docker(root, 'python3', 'fullframe/rtl.py', 'run', '--game', args.game,
                              '--variant', args.variant, '--traffic', args.traffic,
                              *(['--negative'] if args.negative else [])), check=True)
        if not args.negative:
            check_audio_costs(json.loads((directory / (args.traffic + '-results.json')).read_text()))
    verify_inputs(root)
    print('CASE', root, flush=True)
    return root


def checked_capture(root):
    config = json.loads((root / 'experiment.json').read_text())
    verify_inputs(root)
    directory = root / 'build/fullframe' / config['game'] / config['variant']
    manifest = json.loads((directory / 'capture.json').read_text())
    for name, digest in manifest['build']['sources'].items():
        if sha(root / name) != digest:
            raise ValueError('Stale capture source: ' + name)
    if sha(directory / 'program.elf') != manifest['elf_sha256']:
        raise ValueError('Stale captured executable')
    for repeat, files in enumerate(manifest['repeats']):
        for name, digest in files.items():
            if sha(directory / f'repeat-{repeat}' / name) != digest:
                raise ValueError('Capture artifact changed: ' + name)
        for index, row in enumerate(manifest['rows']):
            name = f'frame-{index}.pcm'
            # Probe rows reuse field 4 for call count, and suppress audio entirely.
            pcm_pairs = 0 if config.get('workload') == 'sprite-probe' else row[4]
            if (directory / f'repeat-{repeat}' / name).stat().st_size != pcm_pairs * 4:
                raise ValueError('PCM count disagrees with raw samples')
    return config, directory, manifest


def compare(args):
    baseline, base_dir, base = checked_capture(args.baseline)
    candidate, cand_dir, cand = checked_capture(args.candidate)
    for field in ['game', 'window', 'first_frame', 'mode', 'framebuffer', 'clock_cost', 'audio']:
        if baseline[field] != candidate[field]:
            raise ValueError('Comparison configuration differs: ' + field)
    if baseline.get('scene') != candidate.get('scene'):
        raise ValueError('Comparison scene setup differs')
    if baseline.get('native', 'enabled' if baseline.get('profile') == 'port' else 'disabled') != candidate.get('native', 'enabled' if candidate.get('profile') == 'port' else 'disabled'):
        raise ValueError('Comparison native script setting differs')
    if baseline['audio'] != 'fixed':
        raise ValueError('Cross-build PCM comparison requires fixed audio; realtime RTL audio has no deterministic QEMU PCM oracle')
    differences = []
    for index, (old, new) in enumerate(zip(base['rows'], cand['rows'])):
        if old[0] != new[0]:
            raise ValueError('Frame routes differ')
        checks = [('pixels', 'rgb555'), ('pcm_pairs', None), ('pcm', 'pcm')]
        for field, extension in checks:
            a = old[4] if extension is None else base['repeats'][0][f'frame-{index}.{extension}']
            b = new[4] if extension is None else cand['repeats'][0][f'frame-{index}.{extension}']
            if a != b:
                difference = dict(frame=old[0], field=field, baseline=a, candidate=b)
                if field == 'pixels':
                    folder = args.output.parent / f'{args.output.stem}-frame-{old[0]}'
                    folder.mkdir(parents=True, exist_ok=True)
                    for name, directory in [('baseline', base_dir), ('candidate', cand_dir)]:
                        shutil.copy2(directory / f'repeat-0/frame-{index}.ppm', folder / (name + '.ppm'))
                    difference['images'] = {name: str((folder / (name + '.ppm')).resolve()) for name in ['baseline', 'candidate']}
                    a_bytes = (base_dir / f'repeat-0/frame-{index}.rgb555').read_bytes()
                    b_bytes = (cand_dir / f'repeat-0/frame-{index}.rgb555').read_bytes()
                    if len(a_bytes) == len(b_bytes):
                        pixels = [i for i, (a, b) in enumerate(zip(struct.iter_unpack('<H', a_bytes), struct.iter_unpack('<H', b_bytes))) if a != b]
                        difference['different_pixels'] = len(pixels)
                        difference['first_pixel_index'] = pixels[0]
                differences.append(difference)
    if len(base['rows']) != 3 or len(cand['rows']) != 3:
        raise ValueError('Incomplete comparison window')
    report = dict(identical=not differences, first_difference=differences[0] if differences else None,
                  differences=differences, baseline=str(args.baseline.resolve()), candidate=str(args.candidate.resolve()),
                  baseline_revision=json.loads((args.baseline / 'snapshot.json').read_text())['revision'],
                  candidate_revision=json.loads((args.candidate / 'snapshot.json').read_text())['revision'],
                  baseline_build_kind=baseline['kind'], candidate_build_kind=candidate['kind'],
                  configuration={field: baseline[field] for field in ['game', 'window', 'first_frame', 'mode', 'framebuffer', 'clock_cost', 'audio']},
                  compared_fields=['raw RGB555 SHA256', 'raw PCM SHA256', 'PCM pair count'],
                  frame_count=3, state_hash_compared=False,
                  capture_hashes=[sha(base_dir / 'capture.json'), sha(cand_dir / 'capture.json')])
    save(args.output, report)
    print('identical' if report['identical'] else f"different: frame {differences[0]['frame']} field {differences[0]['field']}", flush=True)
    return report['identical']


def check_audio_costs(result):
    if result['config']['audio'] != 'realtime':
        return
    for row, costs in zip(result['rows'], result['frame_costs']):
        # Queue consumption must cover the whole timed frame, including time
        # after its final game poll. Allow a small margin for boundary MMIO and
        # bookkeeping outside the measured interval, plus fractional rounding.
        expected = row['cycles'] * 48000 / 100000000
        if abs(costs['audio_pairs_consumed'] - expected) > 64:
            raise ValueError('Realtime audio consumption does not cover the complete frame')


def timing_partner(record, records):
    return next((r for r in records if r['build_kind']=='timing' and r['revision']==record['revision']
                 and r['native_scripts']==record['native_scripts']
                 and r['config'].get('scene') == record['config'].get('scene')
                 and r['config'].get('extra_cflags', []) == record['config'].get('extra_cflags', [])
                 and all(r['config'][f]==record['config'][f] for f in
                         ['snapshot_sha256','mode','window','game','variant','profile','framebuffer','clock_cost','audio',
                          'alignment','compiler'])
                 and r['compiler_version']==record['compiler_version']), None)


def report_cases(args):
    records = []
    references = json.loads((ROOT / 'bench/device-references.json').read_text())
    for root in args.cases:
        config, directory, capture = checked_capture(root)
        result = json.loads((directory / (args.traffic + '-results.json')).read_text())
        check_audio_costs(result)
        prepared = json.loads((directory / 'prepared.json').read_text())
        rtl = json.loads((root / 'build/fullframe/rtl/rtl.json').read_text())
        if result['prepared'] != prepared or result['rtl'] != rtl or result['config'] != config:
            raise ValueError('Stale case result')
        checks = [(directory / (args.traffic + '.log'), result['log_sha256']),
                  (directory / 'capture.json', prepared['capture_sha256']),
                  (directory / 'program.bin', prepared['image_sha256']),
                  (directory / 'stack.bin', prepared['stack_sha256']),
                  (directory / 'firmware.mif', prepared['bram_sha256']),
                  (root / 'build/fullframe/rtl/obj/Vtb_system', rtl['simulator_sha256']),
                  (root / 'fullframe/rtl.py', rtl['generator_sha256']),
                  (root / 'build/fullframe/rtl/main.cpp', rtl['source_sha256']),
                  (root / 'build/rtl/rtl.json', rtl['leaf_rtl_sha256'])]
        if prepared['framebuffer_sha256']:
            checks.append((directory / 'framebuffer.bin', prepared['framebuffer_sha256']))
        for path, digest in checks:
            if sha(path) != digest:
                raise ValueError('Case evidence changed: ' + str(path))
        negative_verified = False
        negative_path = directory / 'negative-results.json'
        if negative_path.exists():
            negative = json.loads(negative_path.read_text())
            if (not negative['rejected'] or negative['prepared'] != prepared
                    or negative['rtl'] != rtl or sha(directory / 'negative.log') != negative['log_sha256']):
                raise ValueError('Stale negative-oracle evidence')
            negative_verified = True
        mean = sum(row['simulated_ms'] for row in result['rows']) / len(result['rows'])
        revision = json.loads((root / 'snapshot.json').read_text())['revision']
        reference = next((r for r in references['measurements'] if r['revision'] == revision
                          and config['game'] == r['game'] and config['window'] == r['window']
                          and config['mode'] == r['mode']), None)
        distance = None if reference is None else dict(device_ms=reference['ms'],
                    difference_ms=mean-reference['ms'], difference_percent=(mean/reference['ms']-1)*100,
                    comparable_window=False, reason='Three cold-cache replay frames versus device benchmark section mean')
        records.append(dict(case=str(root.resolve()), revision=revision, build_kind=config['kind'],
                            native_scripts=config.get('native', 'enabled' if config['profile']=='port' else 'disabled'),
                            config=config, mean_simulated_ms=mean, compiler_version=result['compiler_version'],
                            device_compiler_version=references['device_compiler_version'],
                            device_distance=distance, rows=result['rows'], frame_costs=result['frame_costs'],
                            oracle_excluded_fields=result['oracle_excluded_fields'],
                            negative_oracle_rejected=negative_verified,
                            source_flags=capture['build']['app_flags'], substitutions=capture['build']['substitutions'],
                            result_sha256=sha(directory / (args.traffic + '-results.json'))))
    timing_pairs = []
    for record in records:
        if record['build_kind'] != 'trace':
            continue
        partner = timing_partner(record, records)
        if partner:
            timing_pairs.append(dict(revision=record['revision'], mode=record['config']['mode'],
                                     window=record['config']['window'], traced_ms=record['mean_simulated_ms'],
                                     extra_cflags=record['config'].get('extra_cflags', []),
                                     timing_ms=partner['mean_simulated_ms'],
                                     removed_instrumentation_ms=record['mean_simulated_ms']-partner['mean_simulated_ms']))
    save(args.output, dict(cases=records, timing_pairs=timing_pairs, device_references=references,
                          limits=['simulated, not physical Pocket frame time',
                                  'kernel ABI, allocator, storage latency and hardware audio remain substitutions',
                                  'no calibration or tuning to supplied device measurements',
                                  'timing build omits VM tracing and in-loop PCM hashing; traced build validates PCM',
                                  'realtime audio is cycle-dependent; QEMU PCM/count oracles excluded explicitly']))
    for record in records:
        print(record['revision'][:7], record['config']['mode'], record['config']['window'],
              record['build_kind'], round(record['mean_simulated_ms'], 3), 'simulated ms',
              record['device_distance'], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    snap = commands.add_parser('snapshot')
    snap.add_argument('--name', required=True)
    snap.add_argument('--revision', required=True)
    snap.add_argument('--repo', type=Path, required=True)
    snap.add_argument('--patch', type=Path)
    run = commands.add_parser('run')
    run.add_argument('--snapshot', required=True)
    run.add_argument('--game', choices=WINDOWS, default='deltarune')
    run.add_argument('--window', choices=sorted({name for windows in WINDOWS.values() for name in windows}), default='dodge')
    run.add_argument('--mode', choices=['accuracy', 'speed'], default='accuracy')
    run.add_argument('--kind', choices=['trace', 'timing', 'both'], default='both')
    run.add_argument('--profile', choices=['port', 'legacy'], default='port')
    run.add_argument('--native', choices=['profile', 'enabled', 'disabled'], default='profile')
    run.add_argument('--compiler', default='container', help='container or absolute host GCC path')
    run.add_argument('--alignment', action='store_true')
    run.add_argument('--extra-cflags', default='', help='Ordered -DNAME[=VALUE]/-UNAME experiment switches')
    run.add_argument('--variant', choices=['sdram', 'bram'], default='bram')
    run.add_argument('--traffic', choices=['quiet', 'scanout'], default='quiet')
    run.add_argument('--framebuffer', choices=['cached', 'uncached'], default='cached')
    run.add_argument('--clock-cost', type=int, choices=[0, 1680], default=0)
    run.add_argument('--audio', choices=['fixed', 'realtime'], default='fixed')
    run.add_argument('--stage', choices=['build', 'capture', 'prepare', 'replay', 'all'], default='all')
    run.add_argument('--negative', action='store_true')
    cmp = commands.add_parser('compare')
    cmp.add_argument('--baseline', type=Path, required=True)
    cmp.add_argument('--candidate', type=Path, required=True)
    cmp.add_argument('--output', type=Path, required=True)
    report = commands.add_parser('report')
    report.add_argument('--cases', nargs='+', type=Path, required=True)
    report.add_argument('--traffic', choices=['quiet', 'scanout'], default='quiet')
    report.add_argument('--output', type=Path, required=True)
    replay = commands.add_parser('replay')
    replay.add_argument('--case', type=Path, required=True)
    replay.add_argument('--traffic', choices=['quiet','scanout'], default='quiet')
    replay.add_argument('--negative', action='store_true')
    args = parser.parse_args()
    if args.command == 'snapshot':
        snapshot(args)
    elif args.command == 'run':
        for kind in ['trace', 'timing'] if args.kind == 'both' else [args.kind]:
            run_case(args, kind)
    elif args.command == 'replay':
        root = args.case.resolve()
        if not root.is_relative_to((PRIVATE/'cases').resolve()):
            raise ValueError('Replay case must be inside this harness experiments/cases')
        config, _, _ = checked_capture(root)
        subprocess.run(docker(root, 'python3','fullframe/rtl.py','run','--game',config['game'],
                              '--variant',config['variant'],'--traffic',args.traffic,
                              *(['--negative'] if args.negative else [])), check=True)
        if not args.negative:
            directory = root / 'build/fullframe' / config['game'] / config['variant']
            check_audio_costs(json.loads((directory / (args.traffic + '-results.json')).read_text()))
    elif args.command == 'report':
        report_cases(args)
    elif not compare(args):
        parser.exit(2)


if __name__ == '__main__':
    main()
