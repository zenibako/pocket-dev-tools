"""Descriptive device experiments with explicit platform factors and fixed controls."""
import copy
import re

from .model import compare_rows, validate_metadata, validate_rows
from .profiles import validate_binding


_FACTORS = ('clock', 'variant', 'runtime')
_BUILD_IDENTITIES = {
    'runtime_sha256': ('artifacts', 'os_sha256'),
    'bitstream_sha256': ('artifacts', 'bitstream_sha256'),
    'loader_sha256': ('artifacts', 'loader_sha256'),
    'os_revision': ('sources', 'os_revision'),
    'sdk_revision': ('sources', 'sdk_revision'),
    'cpu_config_sha256': ('cpu', 'config_sha256'),
}
_MISSING = object()


def _differences(left, right, path):
    """Retain every declared identity difference, including optional field presence."""
    if isinstance(left, dict) and isinstance(right, dict):
        result = []
        for key in sorted(left.keys() | right.keys()):
            result.extend(_differences(left.get(key, _MISSING), right.get(key, _MISSING),
                                       f'{path}.{key}'))
        return result
    if left == right:
        return []
    item = dict(path=path, baseline=None if left is _MISSING else copy.deepcopy(left),
                candidate=None if right is _MISSING else copy.deepcopy(right))
    if left is _MISSING or right is _MISSING:
        item.update(baseline_present=left is not _MISSING, candidate_present=right is not _MISSING)
    return [item]


def _known_hash(value, label):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError(f'{label} requires a known lowercase SHA-256')


def _validate_run(run):
    if run.get('backend') != 'device':
        raise ValueError('platform experiments require device evidence')
    if not isinstance(run.get('adapter'), str) or not run['adapter'].strip():
        raise ValueError('platform experiments require a known adapter')
    metadata = validate_metadata(run['metadata'])
    validate_rows(run['rows'], metadata)
    checks = run.get('checks', {})
    if checks.get('complete') is not True or checks.get('correctness') == 'reported_fail':
        raise ValueError('failed or incomplete platform runs cannot be compared')
    binding = run.get('platform_profile')
    if not isinstance(binding, dict):
        raise ValueError('platform experiments require validated platform_profile bindings')
    validate_binding(binding, metadata)
    _known_hash(metadata['build'].get('elf_sha256'), 'build.elf_sha256')
    compiler = metadata['build']['compiler']
    if (not isinstance(compiler, str) or not compiler.strip()
            or compiler.strip().lower() in ('unknown', 'unversioned')):
        raise ValueError('platform experiments require a known compiler and flags')
    if any(not flag.strip() or flag.strip().lower() in ('unknown', 'unversioned')
           for flag in metadata['build']['flags']):
        raise ValueError('platform experiments require known compiler flags')
    device = metadata['platform'].get('device_id')
    if (not isinstance(device, str) or not device.strip()
            or device.strip().lower() in ('unknown', 'unversioned')):
        raise ValueError('platform experiments require a known device_id')
    _known_hash(metadata['conditions'].get('asset_manifest_sha256'),
                'conditions.asset_manifest_sha256')
    reported = run.get('reported_platform')
    if reported is not None:
        if not isinstance(reported, dict):
            raise ValueError('reported_platform must be an object')
        if reported.get('clock_hz') != metadata['platform']['clock_hz']:
            raise ValueError('reported_platform clock differs from metadata/profile')
    return binding['definition']


def _actual_factors(left, right):
    changed = set()
    if left['clock_hz'] != right['clock_hz']:
        changed.add('clock')
    cpu_left = {k: v for k, v in left['cpu'].items() if k != 'config_sha256'}
    cpu_right = {k: v for k, v in right['cpu'].items() if k != 'config_sha256'}
    if (left['variant'] != right['variant'] or cpu_left != cpu_right
            or set(left['features']) != set(right['features'])):
        changed.add('variant')
    if (left['sources'] != right['sources']
            or ('variant' not in changed
                and left['cpu']['config_sha256'] != right['cpu']['config_sha256'])
            or (not changed and left['artifacts'] != right['artifacts'])):
        changed.add('runtime')
    return changed


def _fixed_metadata(left, right):
    # Identifiers identify a trial or deployment, while the application binary is fixed.
    for metadata in (left, right):
        metadata.pop('repeat', None)
        metadata['build'].pop('id', None)
        for key in _BUILD_IDENTITIES:
            metadata['build'].pop(key, None)
        metadata['platform'].pop('variant', None)
        metadata['platform'].pop('clock_hz', None)
        metadata['platform'].pop('firmware', None)
        if 'deployment' in metadata:
            deployment = metadata['deployment']
            if not isinstance(deployment, dict):
                raise ValueError('deployment must be an object')
            deployment.pop('core_id', None)
            if not deployment:
                metadata.pop('deployment')
    if left != right:
        raise ValueError('incompatible fixed application/toolchain/device/case/conditions/settings')


def compare_platform_runs(baseline, candidate, varied):
    """Compare fixed-workload device trials without clock scaling or causal claims."""
    if (isinstance(varied, (str, bytes)) or not isinstance(varied, (list, tuple, set, frozenset))
            or any(not isinstance(factor, str) or factor not in _FACTORS for factor in varied)
            or len(varied) != len(set(varied))):
        raise ValueError('varied factors must be an explicit set of clock, variant and/or runtime')
    left_profile, right_profile = (_validate_run(run) for run in (baseline, candidate))
    actual = _actual_factors(left_profile, right_profile)
    if not actual or actual != set(varied):
        raise ValueError('declared varied factors must exactly match actual semantic platform differences')
    for key in ('adapter', 'comparison_config', 'source_config'):
        if baseline.get(key) != candidate.get(key):
            raise ValueError(f'incompatible {key}')
    left, right = baseline['metadata'], candidate['metadata']
    # Optional build declarations may differ only where represented by both profiles.
    for key, (section, field) in _BUILD_IDENTITIES.items():
        if left['build'].get(key, _MISSING) != right['build'].get(key, _MISSING):
            if (key not in left['build'] or key not in right['build']
                    or left['build'][key] != left_profile[section][field]
                    or right['build'][key] != right_profile[section][field]):
                raise ValueError(f'incompatible undeclared build.{key} difference')
    _fixed_metadata(copy.deepcopy(left), copy.deepcopy(right))
    if (left['platform'].get('firmware', _MISSING) != right['platform'].get('firmware', _MISSING)
            and 'runtime' not in actual):
        raise ValueError('platform firmware differences require runtime factor')
    reported_left, reported_right = baseline.get('reported_platform'), candidate.get('reported_platform')
    if (reported_left is None) != (reported_right is None):
        raise ValueError('incompatible reported_platform presence')
    if reported_left is not None:
        for difference in _differences(reported_left, reported_right, 'reported_platform'):
            key = difference['path'].removeprefix('reported_platform.')
            factor = {'clock_hz': 'clock', 'firmware': 'runtime', 'core_number': 'variant'}.get(key)
            if factor not in actual:
                raise ValueError(f'incompatible {difference["path"]}')
            if key == 'core_number' and any(type(value) is not int or value < 0 for value in
                                            (difference['baseline'], difference['candidate'])):
                raise ValueError('reported_platform.core_number must be a numeric core identity')
    differences = (_differences(left_profile, right_profile, 'platform_profile')
                   + _differences(left, right, 'metadata'))
    if reported_left is not None:
        differences.extend(_differences(reported_left, reported_right, 'reported_platform'))
    limits = [
        'Profile binding declares intended artifacts; it does not attest flashed-device identity.',
        'No statistical significance or independent correctness is inferred; reported PASS remains reported.',
        'Timings retain their original units without frequency rescaling.',
        'Repeated imports are not independent device trials.',
    ]
    if len(actual) > 1:
        limits.append('Several platform factors changed together; these deltas do not isolate their individual causes.')
    for run in (baseline, candidate):
        for limit in run.get('limits', []):
            if limit not in limits:
                limits.append(limit)
    return dict(schema_version=1, mode='platform', backend='device',
                assessment='descriptive_platform_experiment', qualification='profile_bound',
                varied_factors=[factor for factor in _FACTORS if factor in actual],
                baseline=baseline.get('run_id'), candidate=candidate.get('run_id'),
                baseline_profile_sha256=baseline['platform_profile']['sha256'],
                candidate_profile_sha256=candidate['platform_profile']['sha256'],
                differences=differences, rows=compare_rows(baseline, candidate), limits=limits)
