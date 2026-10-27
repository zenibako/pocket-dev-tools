"""Import, verify and compare preserved benchmark evidence."""
import argparse
import json
from pathlib import Path
import sys

from .adapters import FORMATS
from .model import compare_runs, validate_project_id
from .comparison import compare_configuration_runs, compare_platform_runs
from .coverage import coverage_matrix
from .profiles import profile_digest, profile_from_files, verify_profile_artifacts
from .store import _read, collect, inspect_source, load_run


ROOT = Path(__file__).resolve().parent.parent


def _private_output(path):
    if not path.resolve().is_relative_to((ROOT / 'build').resolve()):
        raise ValueError('output must be inside this harness build/ directory; SD cards are read only')


def _emit(value, output=None):
    encoded = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n'
    if output is not None:
        _private_output(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('x') as stream:
            stream.write(encoded)
    print(encoded, end='')


def _matrix_runs(paths):
    runs = []
    for path in paths:
        if not path.is_dir():
            raise ValueError(f'run bundle/store is not a directory: {path}')
        if any((path / name).exists() for name in ('manifest.json', 'result.json', 'metadata.json', 'raw')):
            runs.append(load_run(path))
        else:
            # Only explicit stores and their immediate children; a partial child
            # fails verification instead of disappearing from coverage.
            for child in sorted(path.iterdir()):
                if child.is_dir():
                    runs.append(load_run(child))
    return runs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    inspect = commands.add_parser('inspect', help='list accumulated Butterscotch reports before selecting one')
    inspect.add_argument('source', type=Path)
    imp = commands.add_parser('import', help='copy selected evidence; never modifies its source')
    imp.add_argument('--format', required=True, choices=FORMATS)
    imp.add_argument('--source', required=True, type=Path)
    imp.add_argument('--metadata', required=True, type=Path)
    imp.add_argument('--profile', type=Path, help='bind a complete platform profile to device evidence')
    imp.add_argument('--attachment', action='append', default=[], type=Path)
    imp.add_argument('--report-index', type=int, help='zero-based report/case index; required when ambiguous')
    imp.add_argument('--output', type=Path, default=ROOT / 'build/benchmarks')
    verify = commands.add_parser('verify', help='check the archived bundle hashes, not device behavior')
    verify.add_argument('run', type=Path)
    compare = commands.add_parser('compare', help='describe deltas between compatible evidence bundles')
    compare.add_argument('baseline', type=Path)
    compare.add_argument('candidate', type=Path)
    compare.add_argument('--mode', choices=('software', 'platform', 'configuration'), default='software')
    compare.add_argument('--vary', choices=('clock', 'variant', 'runtime'), action='append', default=[])
    compare.add_argument('--reason', help='required explanation for a whole-configuration comparison')
    profile = commands.add_parser('profile', help='declare or verify explicit local platform artifacts')
    profile_commands = profile.add_subparsers(dest='profile_command', required=True)
    for name in ('create', 'verify'):
        action = profile_commands.add_parser(name)
        action.add_argument('definition', type=Path)
        action.add_argument('--os-bin', required=True, type=Path)
        action.add_argument('--bitstream', required=True, type=Path)
        action.add_argument('--loader', required=True, type=Path)
        action.add_argument('--cpu-config', required=True, type=Path)
        if name == 'create':
            action.add_argument('--output', type=Path, required=True)
    matrix = commands.add_parser('matrix', help='report four-cell coverage without aggregating timings')
    matrix.add_argument('--runs', type=Path, nargs='+', default=[])
    matrix.add_argument('--profiles', type=Path, nargs='+', default=[])
    matrix.add_argument('--project', type=validate_project_id, help='project ID, including a new project')
    matrix.add_argument('--game')
    matrix.add_argument('--case', dest='case_id')
    matrix.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'inspect':
            print(json.dumps(inspect_source(args.source), indent=2))
        elif args.command == 'import':
            _private_output(args.output)
            print(collect(args.source, args.metadata, args.format, output=args.output,
                          attachments=args.attachment, report_index=args.report_index,
                          profile_path=args.profile))
        elif args.command == 'verify':
            run = load_run(args.run)
            print(json.dumps(dict(run_id=run['run_id'], backend=run['backend'], checks=run['checks'],
                                  archive_hashes='verified', device_behavior='not_retested'), indent=2))
        elif args.command == 'compare':
            if args.mode != 'platform' and args.vary:
                raise ValueError('--vary requires --mode platform')
            if args.mode != 'configuration' and args.reason is not None:
                raise ValueError('--reason requires --mode configuration')
            baseline, candidate = load_run(args.baseline), load_run(args.candidate)
            if args.mode == 'configuration':
                result = compare_configuration_runs(baseline, candidate, reason=args.reason)
            elif args.mode == 'platform':
                result = compare_platform_runs(baseline, candidate, args.vary)
            else:
                result = compare_runs(baseline, candidate)
            _emit(result)
        elif args.command == 'profile':
            definition = json.loads(_read(args.definition))
            artifacts = dict(os_bin=args.os_bin, bitstream=args.bitstream,
                             loader=args.loader, cpu_config=args.cpu_config)
            if args.profile_command == 'create':
                _emit(profile_from_files(definition, **artifacts), args.output)
            else:
                checked = verify_profile_artifacts(definition, **artifacts)
                _emit(dict(profile=checked, sha256=profile_digest(checked),
                           artifact_hashes='verified', device_behavior='not_retested'))
        elif args.command == 'matrix':
            profiles = [json.loads(_read(path)) for path in args.profiles]
            _emit(coverage_matrix(_matrix_runs(args.runs), profiles, project=args.project,
                                  game=args.game, case_id=args.case_id), args.output)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
