"""Shared metadata, units and conservative comparison rules (schema version 1)."""
import copy
import json
import math
import re


def text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{label} must be a nonempty string')
    return value


def number(value, label, *, integer=False, minimum=0):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value < minimum
            or (integer and not isinstance(value, int))):
        raise ValueError(f'{label} must be a finite {"integer" if integer else "number"} >= {minimum}')
    return value


def object_value(value, label):
    if not isinstance(value, dict):
        raise ValueError(f'{label} must be an object')
    return value


def validate_project_id(value):
    """Allow explicit new projects without implying an adapter or replay model."""
    if (not isinstance(value, str) or len(value) > 64
            or not re.fullmatch(r'[a-z][a-z0-9]*(?:-[a-z0-9]+)*', value)):
        raise ValueError('project must be a lowercase ID of 1-64 letters/digits with single internal hyphens')
    return value


def validate_metadata(metadata):
    """Validate declared run identity without filling unknown facts with guesses."""
    object_value(metadata, 'metadata')
    if type(metadata.get('schema_version')) is not int or metadata['schema_version'] != 1:
        raise ValueError('metadata.schema_version must be 1')
    validate_project_id(metadata.get('project'))
    text(metadata.get('game'), 'game')
    number(metadata.get('repeat'), 'repeat', integer=True, minimum=1)
    build = object_value(metadata.get('build'), 'build')
    for field in ('id', 'source_revision'):
        text(build.get(field), f'build.{field}')
    if build['source_revision'] in ('unknown', 'unversioned'):
        raise ValueError('build.source_revision must identify the source revision')
    if 'compiler' not in build or (build['compiler'] is not None and not isinstance(build['compiler'], str)):
        raise ValueError('build.compiler must be a string or explicit null')
    if not isinstance(build.get('flags'), list) or any(not isinstance(v, str) for v in build['flags']):
        raise ValueError('build.flags must be a list of strings')
    for field in ('elf_sha256', 'runtime_sha256', 'bitstream_sha256'):
        value = build.get(field)
        if value is not None and (not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value)):
            raise ValueError(f'build.{field} must be a lowercase SHA-256 or null')
    platform = object_value(metadata.get('platform'), 'platform')
    text(platform.get('variant'), 'platform.variant')
    if 'clock_hz' not in platform:
        raise ValueError('platform.clock_hz must be supplied or explicit null')
    if platform['clock_hz'] is not None:
        number(platform['clock_hz'], 'platform.clock_hz', integer=True, minimum=1)
    if platform.get('device_id') is not None:
        text(platform['device_id'], 'platform.device_id')
    case = object_value(metadata.get('case'), 'case')
    for field in ('id', 'route_version', 'mode'):
        text(case.get(field), f'case.{field}')
    if case.get('suite') not in ('smoke', 'focused', 'exhaustive'):
        raise ValueError('case.suite must be smoke, focused or exhaustive')
    if 'seed' not in case:
        raise ValueError('case.seed must be supplied or explicit null')
    if case['seed'] is not None:
        number(case['seed'], 'case.seed', integer=True)
    number(case.get('warmup_frames'), 'case.warmup_frames', integer=True)
    number(case.get('target_hz'), 'case.target_hz', minimum=0.000001)
    roster = case.get('expected_rows')
    if not isinstance(roster, list) or not roster:
        raise ValueError('case.expected_rows must be a nonempty list')
    for row in roster:
        text(row, 'expected row')
    if len(set(roster)) != len(roster):
        raise ValueError('duplicate expected row')
    conditions = object_value(metadata.get('conditions'), 'conditions')
    for field in ('initial_state', 'audio', 'pacing'):
        text(conditions.get(field), f'conditions.{field}')
    try:
        json.dumps(metadata, allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise ValueError('metadata must contain finite JSON values') from exc
    return copy.deepcopy(metadata)


def validate_rows(rows, metadata):
    if not isinstance(rows, list) or not rows:
        raise ValueError('missing measurement rows')
    identifiers = []
    for row in rows:
        object_value(row, 'row')
        identifiers.append(text(row.get('id'), 'row.id'))
        if 'samples' not in row:
            raise ValueError('row.samples must be supplied or explicit null')
        if row['samples'] is not None:
            number(row['samples'], 'row.samples', integer=True)
        metrics = object_value(row.get('metrics'), 'row.metrics')
        if not metrics:
            raise ValueError('missing row metrics')
        for key, value in metrics.items():
            if not re.fullmatch(r'[a-z][a-z0-9_]*_(us|cycles|bytes|count|frames|pairs|percent|hz)', key):
                raise ValueError(f'metric {key!r} must name an explicit unit')
            number(value, f'metric {key}')
    if len(identifiers) != len(set(identifiers)):
        raise ValueError('duplicate measurement row')
    if set(identifiers) != set(metadata['case']['expected_rows']):
        raise ValueError('measurement roster differs from case.expected_rows')
    return rows


def compare_runs(baseline, candidate):
    """Describe comparable deltas; never infer correctness or significance."""
    for run in (baseline, candidate):
        validate_metadata(run['metadata'])
        validate_rows(run['rows'], run['metadata'])
        if not run['checks']['complete'] or run['checks']['correctness'] == 'reported_fail':
            raise ValueError('failed or incomplete runs cannot establish performance improvements')
    for key in ('backend', 'adapter', 'comparison_config', 'reported_platform'):
        if baseline.get(key) != candidate.get(key):
            raise ValueError(f'incompatible {key}')
    # Imports without profiles remain readable, but cannot acquire artifact identity
    # merely by comparing with a later, fully declared run.
    from .profiles import validate_binding
    bindings = []
    for run in (baseline, candidate):
        binding = run.get('platform_profile')
        if binding is not None:
            if run['backend'] != 'device':
                raise ValueError('platform profile binding requires device evidence')
            binding = validate_binding(binding, run['metadata'])
        bindings.append(binding)
    if bindings[0] != bindings[1]:
        raise ValueError('incompatible platform profiles')
    left, right = baseline['metadata'], candidate['metadata']
    for key in ('project', 'game', 'case', 'platform', 'conditions'):
        if left[key] != right[key]:
            raise ValueError(f'incompatible {key}')
    # Application identity may change; its compiler/SDK/runtime context may not.
    excluded = {'id', 'source_revision', 'elf_sha256'}
    left_build = {k: v for k, v in left['build'].items() if k not in excluded}
    right_build = {k: v for k, v in right['build'].items() if k not in excluded}
    if left_build != right_build:
        raise ValueError('incompatible build compiler/flags/SDK/runtime context')
    rows = compare_rows(baseline, candidate)
    return dict(schema_version=1, mode='software', backend=baseline['backend'], assessment='descriptive_only',
                qualification='profile_bound' if bindings[0] else 'provisional',
                baseline=baseline.get('run_id'), candidate=candidate.get('run_id'), rows=rows,
                limits=['No statistical significance, independent correctness or cross-device speedup is inferred.',
                        'Profiles declare intended artifacts; they do not attest which artifacts were flashed.',
                        'Build attribution may be declared; inspect raw evidence and checks.',
                        'Runs without profiles have provisional platform identity.',
                        'Repeated imports are not independent device trials.'])


def compare_rows(baseline, candidate):
    """Shared arithmetic after identity controls; retain sampling denominators."""
    for run in (baseline, candidate):
        validate_rows(run['rows'], run['metadata'])
    left = baseline['metadata']
    a = {row['id']: row for row in baseline['rows']}
    b = {row['id']: row for row in candidate['rows']}
    if a.keys() != b.keys():
        raise ValueError('incompatible row roster')
    rows = []
    for name in left['case']['expected_rows']:
        if a[name]['samples'] != b[name]['samples'] or a[name]['metrics'].keys() != b[name]['metrics'].keys():
            raise ValueError(f'incompatible sampling or metrics for {name}')
        metrics = {}
        for key, old in a[name]['metrics'].items():
            new = b[name]['metrics'][key]
            metrics[key] = dict(baseline=old, candidate=new, delta=new-old,
                                percent=None if old == 0 else (new-old)/old*100)
        rows.append(dict(id=name, metrics=metrics))
    return rows
