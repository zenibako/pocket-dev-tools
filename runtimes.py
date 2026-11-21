#!/usr/bin/env python3
"""Pinned openfpgaCore runtime platforms for revision experiments.

The frozen os25 model in inputs/ stays the default. A runtime platform adds the
RTL tree of a published openfpgaCore runtime and the exact CPU netlists that
were fitted into its released bitstreams, so a Butterscotch revision can be
replayed on the CPU it actually ships with. The lock file in runtimes/ is
committed; the imported tree and netlists stay private under runtimes/<id>/.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parent
LOCKS = ROOT / 'runtimes'
NETLIST_DIR = 'src/fpga/vendor/vexriscv/VexiiRiscv'


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def locks():
    return {path.stem: json.loads(path.read_text()) for path in sorted(LOCKS.glob('*.json'))}


def platforms():
    """Map each selectable platform name to (runtime id, lock, platform entry)."""
    found = {}
    for runtime, lock in locks().items():
        for name, entry in lock['platforms'].items():
            if name in found or name == 'os25':
                raise ValueError('Duplicate runtime platform name: ' + name)
            found[name] = (runtime, lock, entry)
    return found


def tree(runtime):
    return LOCKS / runtime / 'os'


def verify(runtime, lock=None):
    """Check every pinned source and netlist byte of an imported runtime tree."""
    lock = lock or locks()[runtime]
    root = tree(runtime)
    if not root.is_dir():
        raise ValueError(f'Runtime {runtime} is not imported; run runtimes.py import')
    for name, digest in lock['sources'].items():
        path = root / name
        if not path.resolve().is_relative_to(root.resolve()) or not path.is_file() or sha(path) != digest:
            raise ValueError(f'Runtime source changed or missing: {runtime}/{name}')
    for name, entry in lock['platforms'].items():
        path = root / NETLIST_DIR / entry['netlist']
        if not path.is_file() or sha(path) != entry['netlist_sha256']:
            raise ValueError(f'Runtime netlist changed or missing: {runtime}/{name}')
    return root


def import_runtime(runtime, core, netlists):
    """Export the pinned commit's sources from a local openfpgaCore clone and add netlists.

    Reads Git objects only; the clone's working tree and submodules are not used.
    Netlists are generated files, so they are copied from an explicit directory
    and accepted only when their SHA-256 matches the lock.
    """
    lock = locks()[runtime]
    destination = tree(runtime)
    if destination.exists():
        raise ValueError(f'{destination} exists; preserve it or remove it explicitly')
    archive = subprocess.check_output(['git', '-C', str(core), 'archive', lock['commit'], *lock['export']])
    staging = destination.with_name('os.staging')
    if staging.exists():
        raise ValueError(f'{staging} exists from an interrupted import; inspect and remove it')
    staging.mkdir(parents=True)
    try:
        with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
            stream.extractall(staging, filter='data')
        (staging / NETLIST_DIR).mkdir(parents=True, exist_ok=True)
        for entry in lock['platforms'].values():
            source = Path(netlists) / entry['netlist']
            if sha(source) != entry['netlist_sha256']:
                raise ValueError(f'{source} is not the pinned netlist ({entry["netlist_sha256"][:12]}...)')
            shutil.copy2(source, staging / NETLIST_DIR / entry['netlist'])
    except BaseException:
        shutil.rmtree(staging)  # only the staging folder this call just created
        raise
    staging.rename(destination)
    verify(runtime, lock)
    print('Imported runtime', runtime, lock['commit'], 'at', destination, flush=True)


def main():
    parser = argparse.ArgumentParser(description='Pinned openfpgaCore runtime platforms')
    commands = parser.add_subparsers(dest='command', required=True)
    imported = commands.add_parser('import')
    imported.add_argument('--runtime', default='pocket-runtime-19d9d50')
    imported.add_argument('--core', type=Path, required=True, help='local zenibako/openfpgaCore clone containing the commit')
    imported.add_argument('--netlists', type=Path, required=True, help='directory holding the pinned VexiiRiscv_<variant>.v files')
    checked = commands.add_parser('verify')
    checked.add_argument('--runtime', default='pocket-runtime-19d9d50')
    args = parser.parse_args()
    if args.command == 'import':
        import_runtime(args.runtime, args.core, args.netlists)
    else:
        verify(args.runtime)
        print('PASS: runtime', args.runtime, 'matches its lock', flush=True)


if __name__ == '__main__':
    main()
