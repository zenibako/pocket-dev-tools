"""Import, verify and compare preserved benchmark evidence."""
import argparse
import json
from pathlib import Path
import sys

from .adapters import FORMATS
from .model import compare_runs
from .store import collect, inspect_source, load_run


ROOT = Path(__file__).resolve().parent.parent


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    inspect = commands.add_parser('inspect', help='list accumulated Butterscotch reports before selecting one')
    inspect.add_argument('source', type=Path)
    imp = commands.add_parser('import', help='copy selected evidence; never modifies its source')
    imp.add_argument('--format', required=True, choices=FORMATS)
    imp.add_argument('--source', required=True, type=Path)
    imp.add_argument('--metadata', required=True, type=Path)
    imp.add_argument('--attachment', action='append', default=[], type=Path)
    imp.add_argument('--report-index', type=int, help='zero-based report/case index; required when ambiguous')
    imp.add_argument('--output', type=Path, default=ROOT / 'build/benchmarks')
    verify = commands.add_parser('verify', help='check the archived bundle hashes, not device behavior')
    verify.add_argument('run', type=Path)
    compare = commands.add_parser('compare', help='describe deltas between compatible evidence bundles')
    compare.add_argument('baseline', type=Path)
    compare.add_argument('candidate', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'inspect':
            print(json.dumps(inspect_source(args.source), indent=2))
        elif args.command == 'import':
            if not args.output.resolve().is_relative_to((ROOT / 'build').resolve()):
                raise ValueError('output must be inside this harness build/ directory; SD cards are read only')
            print(collect(args.source, args.metadata, args.format, output=args.output,
                          attachments=args.attachment, report_index=args.report_index))
        elif args.command == 'verify':
            run = load_run(args.run)
            print(json.dumps(dict(run_id=run['run_id'], backend=run['backend'], checks=run['checks'],
                                  archive_hashes='verified', device_behavior='not_retested'), indent=2))
        else:
            print(json.dumps(compare_runs(load_run(args.baseline), load_run(args.candidate)),
                             indent=2, allow_nan=False))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
