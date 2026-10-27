"""Explicit platform declarations and artifact identities, without device attestation."""
import copy
import hashlib
import json
from pathlib import Path
import re

from .model import number, text, validate_metadata


_PROFILE_FIELDS = {'schema_version', 'id', 'variant', 'clock_hz', 'cpu', 'sources',
                   'artifacts', 'features'}
_CPU_FIELDS = {'isa', 'issue_width', 'icache_bytes', 'dcache_bytes', 'config_sha256'}
_SOURCE_FIELDS = {'os_revision', 'sdk_revision'}
_ARTIFACT_FIELDS = {'os_sha256', 'bitstream_sha256', 'loader_sha256'}
_BUILD_IDENTITIES = {
    'runtime_sha256': ('artifacts', 'os_sha256'),
    'bitstream_sha256': ('artifacts', 'bitstream_sha256'),
    'loader_sha256': ('artifacts', 'loader_sha256'),
    'cpu_config_sha256': ('cpu', 'config_sha256'),
    'os_revision': ('sources', 'os_revision'),
    'sdk_revision': ('sources', 'sdk_revision'),
}


def _fields(value, required, label, *, optional=()):
    if not isinstance(value, dict):
        raise ValueError(f'{label} must be an object')
    if required - value.keys():
        raise ValueError(f'{label} missing required fields: {sorted(required - value.keys())}')
    if value.keys() - required - set(optional):
        raise ValueError(f'{label} has unknown fields')
    return value


def _hash(value, label):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError(f'{label} must be a lowercase SHA-256')
    return value


def validate_profile(profile):
    """Validate a version-1 declaration and return an independent copy."""
    _fields(profile, _PROFILE_FIELDS, 'profile', optional={'description'})
    if type(profile['schema_version']) is not int or profile['schema_version'] != 1:
        raise ValueError('profile.schema_version must be 1')
    text(profile['id'], 'profile.id')
    if profile['variant'] not in ('os20', 'os25'):
        raise ValueError('profile.variant must be os20 or os25')
    number(profile['clock_hz'], 'profile.clock_hz', integer=True, minimum=1)
    if profile['clock_hz'] not in (90000000, 100000000):
        raise ValueError('profile.clock_hz must be 90000000 or 100000000')
    cpu = _fields(profile['cpu'], _CPU_FIELDS, 'profile.cpu')
    text(cpu['isa'], 'profile.cpu.isa')
    number(cpu['issue_width'], 'profile.cpu.issue_width', integer=True, minimum=1)
    for field in ('icache_bytes', 'dcache_bytes'):
        number(cpu[field], f'profile.cpu.{field}', integer=True)
    _hash(cpu['config_sha256'], 'profile.cpu.config_sha256')
    sources = _fields(profile['sources'], _SOURCE_FIELDS, 'profile.sources')
    for field in _SOURCE_FIELDS:
        identity = text(sources[field], f'profile.sources.{field}')
        if identity.strip().lower() in ('unknown', 'unversioned'):
            raise ValueError(f'profile.sources.{field} must identify an exact source revision')
    artifacts = _fields(profile['artifacts'], _ARTIFACT_FIELDS, 'profile.artifacts')
    for field in _ARTIFACT_FIELDS:
        _hash(artifacts[field], f'profile.artifacts.{field}')
    features = profile['features']
    if not isinstance(features, list):
        raise ValueError('profile.features must be a list of strings')
    for feature in features:
        text(feature, 'profile feature')
    if len(features) != len(set(features)):
        raise ValueError('duplicate profile features')
    if 'description' in profile and not isinstance(profile['description'], str):
        raise ValueError('profile.description must be a string')
    return copy.deepcopy(profile)


def profile_digest(profile):
    """SHA-256 of sorted, compact JSON (UTF-8, escaped non-ASCII, no newline)."""
    definition = validate_profile(profile)
    canonical = json.dumps(definition, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def bind_profile(profile, metadata):
    """Bind matching declared identities without rewriting run metadata.

    The caller controls evidence backend eligibility. This binding identifies
    intended artifacts; it does not prove what was flashed on a physical device.
    """
    definition = validate_profile(profile)
    metadata = validate_metadata(metadata)
    platform = metadata['platform']
    if platform['variant'] != definition['variant']:
        raise ValueError('profile variant does not match metadata.platform.variant')
    if platform['clock_hz'] is None or platform['clock_hz'] != definition['clock_hz']:
        raise ValueError('profile requires a known matching metadata.platform.clock_hz')
    for field, (section, name) in _BUILD_IDENTITIES.items():
        if field in metadata['build'] and metadata['build'][field] != definition[section][name]:
            raise ValueError(f'profile does not match metadata.build.{field}')
    return dict(definition=definition, sha256=profile_digest(definition))


def validate_binding(binding, metadata):
    """Check the stored digest and metadata agreement; return a detached binding."""
    _fields(binding, {'definition', 'sha256'}, 'platform_profile')
    _hash(binding['sha256'], 'platform_profile.sha256')
    validated = bind_profile(binding['definition'], metadata)
    if binding['sha256'] != validated['sha256']:
        raise ValueError('platform profile hash mismatch')
    return validated


def _file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _file_identities(*, os_bin, bitstream, loader, cpu_config):
    return {'cpu': {'config_sha256': _file_hash(cpu_config)},
            'artifacts': {'os_sha256': _file_hash(os_bin),
                          'bitstream_sha256': _file_hash(bitstream),
                          'loader_sha256': _file_hash(loader)}}


def profile_from_files(definition, *, os_bin, bitstream, loader, cpu_config):
    """Hash four explicit files, filling only omitted artifact/config hashes.

    CPU architecture, cache sizes and clock are always supplied by the caller.
    A supplied hash is checked rather than replaced. No profile file is written.
    """
    _fields(definition, _PROFILE_FIELDS - {'artifacts'}, 'profile',
            optional={'artifacts', 'description'})
    profile = copy.deepcopy(definition)
    cpu = _fields(profile['cpu'], _CPU_FIELDS - {'config_sha256'}, 'profile.cpu',
                  optional={'config_sha256'})
    artifacts = profile.setdefault('artifacts', {})
    _fields(artifacts, set(), 'profile.artifacts', optional=_ARTIFACT_FIELDS)
    identities = _file_identities(os_bin=os_bin, bitstream=bitstream,
                                  loader=loader, cpu_config=cpu_config)
    for section, values in identities.items():
        for field, actual in values.items():
            target = cpu if section == 'cpu' else artifacts
            if field in target:
                _hash(target[field], f'profile.{section}.{field}')
                if target[field] != actual:
                    raise ValueError(f'profile.{section}.{field} hash mismatch')
            else:
                target[field] = actual
    return validate_profile(profile)


def verify_profile_artifacts(profile, *, os_bin, bitstream, loader, cpu_config):
    """Check all four local file hashes and return the validated profile.

    Matching bytes make no claims about bitstream validity or device state.
    """
    definition = validate_profile(profile)
    identities = _file_identities(os_bin=os_bin, bitstream=bitstream,
                                  loader=loader, cpu_config=cpu_config)
    for section, values in identities.items():
        for field, actual in values.items():
            if definition[section][field] != actual:
                raise ValueError(f'profile.{section}.{field} hash mismatch')
    return definition
