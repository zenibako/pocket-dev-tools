#!/usr/bin/env python3
"""Import hash-verified local dependencies; never modify the source directories."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parent
CPU_PATH = Path('inputs/os/src/fpga/vendor/vexriscv/VexiiRiscv')


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def relative(name):
    path = Path(name)
    if path.is_absolute() or '..' in path.parts or '.git' in path.parts:
        raise ValueError(f'Unsafe manifest path: {name}')
    return path


def confined(root, name):
    path = root / relative(name)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'Link escapes source directory: {path}')
    return path


def check(path, expected):
    if not path.is_file() or sha(path) not in expected:
        raise ValueError(f'Missing or incompatible frozen input: {path}')


def cpu_files(source, destination, lock):
    # Both the pinned upstream source and the OS-patched source are accepted.
    # generate_vexii.sh applies the pinned patches only in the destination.
    for name, entry in lock['files'].items():
        path = confined(source, name)
        check(path, list(entry.values()))
        copy_file(path, destination / relative(name))
    netlist = lock['netlist']
    path = confined(source, netlist['path'])
    if path.exists():
        check(path, [netlist['sha256']])
        copy_file(path, destination / netlist['path'])


def copy_file(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def copy_tree(source, destination, source_root, destination_root):
    """Copy evidence while rebasing internal links; reject external links."""
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        if item.name in ['.git', '__pycache__', '.DS_Store']:
            continue
        out = destination / item.name
        if item.is_symlink():
            target = item.resolve(strict=True)
            if not target.is_relative_to(source_root):
                raise ValueError(f'Link escapes source directory: {item}')
            out.symlink_to(os.path.relpath(destination_root / target.relative_to(source_root), out.parent))
        elif item.is_dir():
            copy_tree(item, out, source_root, destination_root)
        elif item.is_file():
            copy_file(item, out)
        else:
            raise ValueError(f'Unsupported input file: {item}')


def import_inputs(args):
    manifest = json.loads((ROOT / 'input-manifest.json').read_text())
    lock = json.loads((ROOT / 'cpu-lock.json').read_text())
    bundle = args.from_harness.resolve() if args.from_harness else None
    if bundle:
        if (bundle / 'input-manifest.json').read_bytes() != (ROOT / 'input-manifest.json').read_bytes():
            raise ValueError('Snapshot manifest differs from this harness revision')
        roots = {name: bundle / 'inputs' / name for name in ['butterscotch', 'os', 'sdk']}
        cpu = bundle / CPU_PATH
    else:
        roots = {name: getattr(args, name).resolve() for name in ['butterscotch', 'os', 'sdk']}
        cpu = args.cpu.resolve()
    entries = ['inputs']
    captures = bundle / 'captures' if bundle else args.captures
    if captures and captures.is_dir():
        entries.append('captures')
    if args.with_evidence:
        if not bundle or not (bundle / 'build').is_dir():
            raise ValueError('--with-evidence needs an existing harness build directory')
        entries.append('build')
    if any((ROOT / name).exists() or (ROOT / name).is_symlink() for name in entries):
        raise ValueError('Import requires absent destination inputs/captures/build; use a fresh checkout')
    # Validate and copy into a temporary directory before publishing any inputs.
    with tempfile.TemporaryDirectory(prefix='.bootstrap-', dir=ROOT) as temp:
        staged = Path(temp)
        for name, digest in manifest['sources'].items():
            path = relative(name)
            if len(path.parts) < 3 or path.parts[0] != 'inputs' or path.parts[1] not in roots:
                raise ValueError(f'Unexpected input path: {name}')
            source = confined(roots[path.parts[1]], Path(*path.parts[2:]))
            if args.private_inputs and (not source.is_file() or sha(source) != digest):
                source = confined(args.private_inputs.resolve(), Path(*path.parts[1:]))
            check(source, [digest])
            copy_file(source, staged / path)
        cpu_files(cpu, staged / CPU_PATH, lock)
        if 'captures' in entries:
            source_root = bundle or captures.resolve()
            destination_root = staged if bundle else staged / 'captures'
            copy_tree(captures.resolve(), staged / 'captures', source_root, destination_root)
        if 'build' in entries:
            copy_tree(bundle / 'build', staged / 'build', bundle, staged)
        # Use relative links so the staged tree remains valid after these renames.
        for name in entries:
            (staged / name).rename(ROOT / name)
    print(f'PASS imported {len(manifest["sources"])} frozen inputs and {len(lock["files"])} CPU sources', flush=True)
    if 'build' in entries:
        print('Imported evidence is historical until replayed; run fullframe/report.py to check its hashes.')
    elif 'captures' not in entries:
        print('Run python3 capture.py all to create private event captures before run.py all.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-harness', type=Path, help='Existing compatible private harness snapshot')
    for name in ['butterscotch', 'os', 'sdk', 'cpu']:
        parser.add_argument('--' + name, type=Path, help='Local pinned source root (see SETUP.md)')
    parser.add_argument('--private-inputs', type=Path, help='Private inputs/ export for game assets or SDK libraries')
    parser.add_argument('--captures', type=Path, help='Optional compatible private captures directory')
    parser.add_argument('--with-evidence', action='store_true', help='Also import existing build evidence; default is a clean build')
    args = parser.parse_args()
    if args.from_harness:
        if any(getattr(args, name) for name in ['butterscotch', 'os', 'sdk', 'cpu', 'private_inputs', 'captures']):
            parser.error('--from-harness cannot be mixed with component sources')
    elif not all(getattr(args, name) for name in ['butterscotch', 'os', 'sdk', 'cpu']):
        parser.error('Supply --from-harness or all four component source roots')
    try:
        import_inputs(args)
    except (ValueError, OSError) as error:
        parser.exit(1, f'Import failed: {error}\n')


if __name__ == '__main__':
    main()
