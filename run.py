#!/usr/bin/env python3
"""Host launcher. Docker gets exactly one bind mount: this isolated directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / 'build'
CPU = ROOT / 'inputs/os/src/fpga/vendor/vexriscv/VexiiRiscv/VexiiRiscv_os25.v'
IMAGE = 'undertale-vm-os25-harness:local'


def verify_inputs():
    manifest = json.loads((ROOT / 'input-manifest.json').read_text())
    changed = [name for name, expected in manifest['sources'].items()
               if not (ROOT / name).is_file() or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected]
    if changed:
        raise SystemExit('Frozen input changed: ' + ', '.join(changed[:10]))
    print(f'PASS: {len(manifest["sources"])} frozen input files match their snapshot hashes', flush=True)


def host_reference():
    from battle_fixtures import generate
    captured=generate()
    units = ['vm', 'gml_array', 'gml_method', 'instance', 'int_int_hashmap', 'int_rvalue_hashmap', 'stb_ds']
    defines = ['USE_FLOAT_REALS', 'NO_RVALUE_INT64', 'ENABLE_WAD16', 'ENABLE_WAD17', 'ENABLE_VM_GML_PROFILER']
    command = ['clang', '-O1', '-g', '-fsanitize=address,undefined',
               *['-D' + d for d in defines], '-Iinputs/butterscotch/src', '-Iinputs/butterscotch/vendor/stb/ds',
               'workloads.c', 'runtime.c', 'services.c', 'battle_replay.c',
               *['inputs/butterscotch/src/' + u + '.c' for u in units], '-lm']
    env = dict(os.environ, ASAN_OPTIONS='detect_leaks=0', UBSAN_OPTIONS='halt_on_error=1')
    for variant in ['reference','negative','battle-negative']:
        dest = BUILD / ('host-'+variant)
        define={'reference':[], 'negative':['-DHARNESS_EXPECT_BIAS=1'], 'battle-negative':['-DHARNESS_BATTLE_EXPECT_BIAS=1']}[variant]
        subprocess.run([*command, *define, '-o', str(dest)], cwd=ROOT, check=True)
        with dest.with_suffix('.log').open('w') as stream:
            result = subprocess.run([str(dest)], env=env, stdout=stream, stderr=subprocess.STDOUT)
        log = dest.with_suffix('.log').read_text()
        if variant!='reference':
            reason='battle independent return oracle' if variant=='battle-negative' else 'independent return oracle'
            assert result.returncode == 2 and 'VMHARNESS FAIL '+reason in log
        else:
            assert result.returncode == 0 and 'VMHARNESS PASS HAL init' in log and log.count('VMRESULT ') == 24 and log.count('BATTLERESULT ')==3*len(captured)
    print('PASS: host ASan/UBSan reference and deliberately wrong oracle', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['verify', 'host', 'toolchain', 'cpu', 'firmware', 'rtl', 'run', 'all'])
    parser.add_argument('--jobs', type=int, default=4)
    args = parser.parse_args()
    BUILD.mkdir(exist_ok=True)
    verify_inputs()
    if args.action == 'verify': return
    if args.action in ['host', 'all']: host_reference()
    if args.action == 'host': return
    config = BUILD / 'docker-config'
    config.mkdir(exist_ok=True)
    # Do not invoke the user's locked Keychain helper for public images.
    (config / 'config.json').write_text('{"auths":{"https://index.docker.io/v1/":{}}}\n')
    endpoint = os.environ.get('HARNESS_DOCKER_HOST', 'unix://' + str(Path.home() / '.config/colima/default/docker.sock'))
    docker = ['docker', '--config', str(config), '-H', endpoint]
    if args.action in ['toolchain', 'all']:
        with (ROOT / 'Dockerfile').open('rb') as source:
            subprocess.run([*docker, 'build', '-t', IMAGE, '-'], stdin=source, check=True)
    if args.action == 'toolchain': return
    container = [*docker, 'run', '--rm', '-v', f'{ROOT}:/work', '-w', '/work',
                 '-e', 'HOME=/work/build/toolcache', '-e', 'SBT_OPTS=-Duser.home=/work/build/toolcache', IMAGE]
    if args.action == 'cpu' or (args.action == 'all' and not CPU.is_file()):
        with (BUILD / 'cpu-generation.log').open('w') as log:
            subprocess.run([*container, 'bash', 'inputs/os/src/fpga/vendor/vexriscv/generate_vexii.sh', 'os25'],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
    if args.action == 'cpu': return
    subprocess.run([*container, 'python3', 'harness.py', args.action, '--jobs', str(args.jobs)], check=True)
    verify_inputs()


if __name__ == '__main__':
    main()
