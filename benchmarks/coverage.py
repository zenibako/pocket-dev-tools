"""Pure status coverage of declared platforms, without timing aggregation.

Callers load and verify evidence bundles before passing their normalized runs.
A profile binding identifies intended artifacts, never the flashed device state.
"""
import copy
import json

from .model import text, validate_metadata
from .profiles import profile_digest, validate_binding, validate_profile


_CELLS = tuple((variant, clock) for variant in ('os20', 'os25')
               for clock in (90000000, 100000000))
_COUNTS = ('total', 'profile_bound', 'provisional', 'host', 'simulated',
           'device_observed', 'reported_pass', 'device_reported_pass', 'failures')


def _key(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _scope(metadata, run):
    # Runtime and platform artifacts can differ across matrix cells. Their full
    # declarations stay in each run context rather than being silently discarded.
    return dict(project=metadata['project'], game=metadata['game'],
                case=copy.deepcopy(metadata['case']),
                application={field: copy.deepcopy(metadata['build'].get(field))
                             for field in ('source_revision', 'elf_sha256', 'compiler', 'flags')},
                conditions=copy.deepcopy(metadata['conditions']), backend=run['backend'],
                device_id=metadata['platform'].get('device_id'),
                platform_extras={k: copy.deepcopy(v) for k, v in metadata['platform'].items()
                                 if k not in ('variant', 'clock_hz', 'device_id')},
                adapter=run.get('adapter'),
                comparison_config=copy.deepcopy(run.get('comparison_config')),
                source_config=copy.deepcopy(run.get('source_config')),
                metadata_extras={k: copy.deepcopy(v) for k, v in metadata.items()
                                 if k not in ('schema_version', 'project', 'game', 'repeat',
                                              'build', 'platform', 'case', 'conditions',
                                              'deployment')})


def _cell(variant, clock, profiles):
    matching = [copy.deepcopy(binding) for binding in profiles
                if (binding['definition']['variant'], binding['definition']['clock_hz'])
                == (variant, clock)]
    return dict(variant=variant, clock_hz=clock,
                status='profile_registered' if matching else 'untested',
                profiles=matching, profile_ids=[], profile_sha256s=[], run_ids=[],
                counts=dict.fromkeys(_COUNTS, 0), failures=[], runs=[])


def _row(scope, profiles):
    return dict(scope=scope, cells=[_cell(v, c, profiles) for v, c in _CELLS])


def _finish(cell):
    # Declarations with the same label and different hashes remain inspectable.
    cell['profiles'] = sorted({binding['sha256']: binding for binding in cell['profiles']}.values(),
                              key=lambda binding: (binding['definition']['id'], binding['sha256']))
    cell['profile_ids'] = sorted({binding['definition']['id'] for binding in cell['profiles']})
    cell['profile_sha256s'] = sorted({binding['sha256'] for binding in cell['profiles']})
    cell['runs'].sort(key=lambda run: run['run_id'])
    cell['run_ids'] = [run['run_id'] for run in cell['runs']]
    cell['failures'].sort(key=lambda failure: failure['run_id'])
    counts = cell['counts']
    if any(run['checks']['correctness'] == 'reported_fail' for run in cell['runs']):
        cell['status'] = 'reported_fail'
    elif counts['device_reported_pass']:
        cell['status'] = 'device_reported_pass'
    elif counts['device_observed']:
        cell['status'] = 'device_observed'
    elif counts['simulated']:
        cell['status'] = 'simulated'
    elif counts['host']:
        cell['status'] = 'host_observed'
    elif counts['total']:
        cell['status'] = 'provisional'


def coverage_matrix(runs, profiles=(), *, project=None, game=None, case_id=None):
    """Report all four cells per exact selected workload/application scope.

    Counts describe imported records, not independent experimental trials. Runs
    with duplicate IDs are rejected. Explicit synthetic fixtures are listed as
    exclusions, and unknown variants/clocks remain unclassified. Nothing here
    reads files, reruns correctness checks, or aggregates measurement timings.
    """
    registered = []
    for profile in profiles:
        definition = validate_profile(profile)
        registered.append(dict(definition=definition, sha256=profile_digest(definition)))
    rows, seen, unclassified, excluded = {}, set(), [], []
    for run in runs:
        if not isinstance(run, dict):
            raise ValueError('run must be an object')
        run_id = text(run.get('run_id'), 'run.run_id')
        if run_id in seen:
            raise ValueError(f'duplicate run ID: {run_id}')
        seen.add(run_id)
        metadata = validate_metadata(run.get('metadata'))
        if ((project is not None and metadata['project'] != project)
                or (game is not None and metadata['game'] != game)
                or (case_id is not None and metadata['case']['id'] != case_id)):
            continue
        backend = run.get('backend')
        if backend not in ('host', 'simulation', 'device'):
            raise ValueError(f'unsupported run backend: {backend!r}')
        checks = run.get('checks')
        if (not isinstance(checks, dict) or type(checks.get('complete')) is not bool
                or checks.get('correctness') not in ('not_checked', 'reported_pass', 'reported_fail')):
            raise ValueError('run.checks must declare completion and reported correctness')
        binding = None
        if 'platform_profile' in run:
            binding = validate_binding(run['platform_profile'], metadata)
            if backend != 'device':
                raise ValueError('platform profile bindings require device evidence')
        if metadata['conditions'].get('synthetic_fixture') is True:
            excluded.append(run_id)
            continue
        scope = _scope(metadata, run)
        dimensions = (metadata['platform']['variant'], metadata['platform']['clock_hz'])
        if dimensions not in _CELLS:
            reasons = []
            if dimensions[0] not in ('os20', 'os25'):
                reasons.append(f'unknown variant: {dimensions[0]}')
            if dimensions[1] not in (90000000, 100000000):
                reasons.append(f'unknown or unsupported clock_hz: {dimensions[1]}')
            unclassified.append(dict(run_id=run_id, reason='; '.join(reasons),
                                     platform=copy.deepcopy(metadata['platform']), scope=scope,
                                     checks=copy.deepcopy(checks)))
            continue
        row = rows.setdefault(_key(scope), _row(scope, registered))
        cell = next(cell for cell in row['cells']
                    if (cell['variant'], cell['clock_hz']) == dimensions)
        counts = cell['counts']
        counts['total'] += 1
        counts['profile_bound'] += binding is not None
        complete = checks['complete']
        counts['provisional'] += binding is None or not complete
        counts['reported_pass'] += checks['correctness'] == 'reported_pass'
        counts['host'] += backend == 'host' and complete
        counts['simulated'] += backend == 'simulation' and complete
        observed = backend == 'device' and binding is not None and complete
        counts['device_observed'] += observed
        counts['device_reported_pass'] += observed and checks['correctness'] == 'reported_pass'
        reasons = []
        if checks['correctness'] == 'reported_fail':
            reasons.append('reported correctness failure')
        if not complete:
            reasons.append('incomplete run')
        if reasons:
            counts['failures'] += 1
            cell['failures'].append(dict(run_id=run_id, reason='; '.join(reasons),
                                         checks=copy.deepcopy(checks)))
        context = dict(run_id=run_id, build=copy.deepcopy(metadata['build']),
                       platform=copy.deepcopy(metadata['platform']),
                       checks=copy.deepcopy(checks), repeat=metadata['repeat'],
                       deployment=copy.deepcopy(metadata.get('deployment')),
                       reported_platform=copy.deepcopy(run.get('reported_platform')),
                       limits=copy.deepcopy(run.get('limits', [])))
        if binding is not None:
            context['platform_profile'] = binding
            cell['profiles'].append(copy.deepcopy(binding))
        cell['runs'].append(context)
    if not rows:
        scope = dict(project=project, game=game, case={'id': case_id}, application=None,
                     conditions=None, backend=None, device_id=None, platform_extras={},
                     adapter=None, comparison_config=None, source_config=None, metadata_extras={})
        rows[_key(scope)] = _row(scope, registered)
    for row in rows.values():
        for cell in row['cells']:
            _finish(cell)
    return dict(schema_version=1, rows=[rows[key] for key in sorted(rows)],
                unclassified=sorted(unclassified, key=lambda run: run['run_id']),
                excluded_synthetic_run_ids=sorted(excluded),
                limits=['Profiles declare intended artifacts; they do not attest flashed device state.',
                        'Imports and reported PASS checks do not establish independent correctness.',
                        'Counts describe imported records, not independent device trials.',
                        'Timing measurements are not pooled, averaged or frequency-normalized.'])
