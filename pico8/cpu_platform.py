#!/usr/bin/env python3
"""Build a separately pinned os20 simulator without replacing os25 inputs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import run as base

PLATFORM = ROOT / 'build/platforms/os20'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare():
    base.verify_inputs()
    PLATFORM.mkdir(parents=True, exist_ok=False)
    vendor = ROOT / 'inputs/os/src/fpga/vendor/vexriscv'
    target = PLATFORM / 'vendor'
    shutil.copytree(vendor, target, ignore=shutil.ignore_patterns('VexiiRiscv'))
    cpu = target / 'VexiiRiscv'
    lock = json.loads((ROOT / 'cpu-lock.json').read_text())
    for name, expected in lock['files'].items():
        source = vendor / 'VexiiRiscv' / name
        if sha(source) not in (expected['sha256'], expected.get('upstream_sha256')):
            raise ValueError('Locked CPU source changed: ' + name)
        dest = cpu / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
    with (PLATFORM / 'cpu-generation.log').open('x') as log:
        subprocess.run([*container(), 'bash', 'build/platforms/os20/vendor/generate_vexii.sh', 'os20'],
                       stdout=log, stderr=subprocess.STDOUT, check=True)


def container():
    endpoint = os.environ.get('HARNESS_DOCKER_HOST',
                 'unix://' + str(Path.home() / '.config/colima/default/docker.sock'))
    return ['docker', '--config', str(ROOT / 'build/docker-config'), '-H', endpoint,
            'run', '--rm', '-v', str(ROOT) + ':/work', '-w', '/work',
            '-e', 'HOME=/work/build/platforms/os20/toolcache',
            '-e', 'SBT_OPTS=-Duser.home=/work/build/platforms/os20/toolcache', base.IMAGE]


def compile_rtl(jobs):
    import harness
    import fullframe.rtl as frames
    cpu = PLATFORM / 'vendor/VexiiRiscv/VexiiRiscv_os20.v'
    harness.rtl(jobs, variant='os20', dest=PLATFORM / 'leaf', cpu=cpu)
    frames.rtl(jobs, dest=PLATFORM / 'rtl', leaf=PLATFORM / 'leaf', cpu=cpu)
    leaf = json.loads((PLATFORM / 'leaf/rtl.json').read_text())
    if leaf['sdram_parameters']['REFRESH_INTERVAL'] != 660:
        raise ValueError('Wrong os20 refresh cadence')
    sources = {str(p.relative_to(PLATFORM)): sha(p) for p in
               (PLATFORM / 'vendor').rglob('*') if p.is_file() and
               not any(x in p.parts for x in ('target', '.bloop', '.metals'))}
    manifest = dict(name='os20', clock_hz=90000000, scan_period=2858,
        cpu_sha256=sha(cpu), simulator_sha256=sha(PLATFORM / 'rtl/obj/Vtb_system'),
        frozen_input_manifest_sha256=sha(ROOT / 'input-manifest.json'),
        cpu_lock_sha256=sha(ROOT / 'cpu-lock.json'), sources=sources,
        rtl=leaf, provenance='os20 configuration pinned to frozen OS 8318f25; exact shipped bitstream source equivalence unproven')
    (PLATFORM / 'platform.json').write_text(json.dumps(manifest, indent=2) + '\n')


def checked():
    manifest = json.loads((PLATFORM / 'platform.json').read_text())
    if (manifest['name'], manifest['clock_hz'], manifest['scan_period']) != ('os20', 90000000, 2858):
        raise ValueError('Invalid os20 platform identity')
    for name, digest in manifest['sources'].items():
        if sha(PLATFORM / name) != digest:
            raise ValueError('Platform source changed: ' + name)
    if sha(PLATFORM / 'rtl/obj/Vtb_system') != manifest['simulator_sha256']:
        raise ValueError('Platform simulator changed')
    if sha(PLATFORM / 'vendor/VexiiRiscv/VexiiRiscv_os20.v') != manifest['cpu_sha256']:
        raise ValueError('Platform CPU netlist identity changed')
    for name, field in [('top.v', 'wrapper_sha256'), ('main.cpp', 'runner_sha256'),
                        ('io_sdram_pocket_test.v', 'controller_twin_sha256')]:
        if sha(PLATFORM / 'leaf' / name) != manifest['rtl'][field]:
            raise ValueError('Platform RTL source changed: ' + name)
    frame = json.loads((PLATFORM / 'rtl/rtl.json').read_text())
    if (frame['simulator_sha256'] != manifest['simulator_sha256'] or
        frame['source_sha256'] != sha(PLATFORM / 'rtl/main.cpp') or
        frame['leaf_rtl_sha256'] != sha(PLATFORM / 'leaf/rtl.json') or
        json.loads((PLATFORM / 'leaf/rtl.json').read_text()) != manifest['rtl']):
        raise ValueError('Platform frame replay provenance changed')
    if sha(ROOT / 'input-manifest.json') != manifest['frozen_input_manifest_sha256']:
        raise ValueError('Platform frozen input identity changed')
    if sha(ROOT / 'cpu-lock.json') != manifest['cpu_lock_sha256']:
        raise ValueError('Platform CPU lock changed')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['build', 'rtl', 'verify', '_rtl'])
    parser.add_argument('--jobs', type=int, default=4)
    args = parser.parse_args()
    if args.action == 'verify':
        base.verify_inputs()
        checked()
        print('PASS os20 platform hashes')
        return
    if (PLATFORM / 'platform.json').exists():
        raise ValueError('Preserve completed os20 platform evidence; do not replace its simulator')
    if args.action == '_rtl':
        compile_rtl(args.jobs)
        return
    if args.action == 'build':
        prepare()
    index = 0
    log_path = PLATFORM / 'rtl-build.log'
    while log_path.exists():
        index += 1
        log_path = PLATFORM / f'rtl-build-{index}.log'
    with log_path.open('x') as log:
        subprocess.run([*container(), 'python3', 'pico8/cpu_platform.py', '_rtl', '--jobs', str(args.jobs)],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    checked()
    base.verify_inputs()
    print('PASS os20 platform build', PLATFORM)


if __name__ == '__main__':
    main()
