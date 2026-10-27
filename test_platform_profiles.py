"""Profiles declare synthetic artifact identities, never hardware verification."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from benchmarks.profiles import (bind_profile, profile_digest, profile_from_files,
                                 validate_binding, validate_profile,
                                 verify_profile_artifacts)


def profile(variant='os25', clock_hz=100000000):
    return dict(schema_version=1, id=f'fixture-{variant}-{clock_hz}',
                variant=variant, clock_hz=clock_hz,
                cpu=dict(isa='rv32imafc', issue_width=2, icache_bytes=32768,
                         dcache_bytes=131072, config_sha256='a' * 64),
                sources=dict(os_revision='fixture-os-rev', sdk_revision='fixture-sdk-rev'),
                artifacts=dict(os_sha256='b' * 64, bitstream_sha256='c' * 64,
                               loader_sha256='d' * 64), features=['fpu', 'compressed'])


def metadata():
    return dict(schema_version=1, project='butterscotch', game='undertale', repeat=1,
                build=dict(id='fixture-build', source_revision='fixture-app-rev',
                           compiler='fixture-compiler', flags=['-O2']),
                platform=dict(variant='os25', clock_hz=100000000, device_id='fixture-device'),
                case=dict(id='fixture-case', suite='focused', route_version='v1',
                          mode='speed', seed=7, warmup_frames=0, target_hz=30,
                          expected_rows=['fixture-row']),
                conditions=dict(initial_state='fresh', audio='on', pacing='uncapped'))


class PlatformProfileTests(unittest.TestCase):
    def test_all_four_variant_clock_cells_validate_without_inference_or_mutation(self):
        for variant in ('os20', 'os25'):
            for clock in (90000000, 100000000):
                with self.subTest(variant=variant, clock=clock):
                    value = profile(variant, clock)
                    before = copy.deepcopy(value)
                    result = validate_profile(value)
                    self.assertEqual(result, before)
                    result['cpu']['issue_width'] = 1
                    result['features'].append('changed')
                    self.assertEqual(value, before)

    def test_rejects_unknown_fields_at_every_schema_level(self):
        for section in (None, 'cpu', 'sources', 'artifacts'):
            value = profile()
            (value if section is None else value[section])['typo'] = 'untrusted'
            with self.subTest(section=section), self.assertRaises(ValueError):
                validate_profile(value)

    def test_rejects_missing_required_fields_and_hashes(self):
        for section, field in [(None, 'schema_version'), (None, 'id'), (None, 'variant'),
                               (None, 'clock_hz'), (None, 'cpu'), (None, 'sources'),
                               (None, 'artifacts'), (None, 'features'),
                               ('cpu', 'isa'), ('cpu', 'issue_width'),
                               ('cpu', 'icache_bytes'), ('cpu', 'dcache_bytes'),
                               ('cpu', 'config_sha256'), ('sources', 'os_revision'),
                               ('sources', 'sdk_revision'), ('artifacts', 'os_sha256'),
                               ('artifacts', 'bitstream_sha256'), ('artifacts', 'loader_sha256')]:
            value = profile()
            del (value if section is None else value[section])[field]
            with self.subTest(section=section, field=field), self.assertRaises(ValueError):
                validate_profile(value)

    def test_rejects_wrong_types_nonfinite_numbers_and_duplicate_features(self):
        invalid = [(None, 'schema_version', True), (None, 'schema_version', 1.0),
                   (None, 'variant', 'os30'), (None, 'clock_hz', 95000000),
                   (None, 'clock_hz', True), (None, 'clock_hz', 100000000.0),
                   (None, 'clock_hz', float('inf')), (None, 'id', ''),
                   (None, 'description', None), (None, 'features', ('fpu',)),
                   (None, 'features', ['fpu', 'fpu']), (None, 'features', ['']),
                   (None, 'features', [float('nan')]), ('cpu', 'isa', None),
                   ('cpu', 'issue_width', 0), ('cpu', 'issue_width', True),
                   ('cpu', 'icache_bytes', -1), ('cpu', 'dcache_bytes', 1.0),
                   ('cpu', 'config_sha256', 'A' * 64),
                   ('artifacts', 'os_sha256', 'b' * 63),
                   ('artifacts', 'bitstream_sha256', None),
                   ('artifacts', 'loader_sha256', True)]
        invalid += [('sources', field, value) for field in ('os_revision', 'sdk_revision')
                    for value in (None, '', '  ', 'unknown', 'unversioned', 123)]
        for section, field, bad in invalid:
            value = profile()
            (value if section is None else value[section])[field] = bad
            with self.subTest(section=section, field=field, value=bad), self.assertRaises(ValueError):
                validate_profile(value)
        for bad in (None, [], 'profile'):
            with self.subTest(value=bad), self.assertRaises(ValueError):
                validate_profile(bad)

    def test_digest_covers_complete_definition_and_is_key_order_independent(self):
        value = profile()
        # Hash expectation uses the documented JSON encoding, independent of the API.
        expected = hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                            allow_nan=False).encode('utf-8')).hexdigest()
        self.assertEqual(profile_digest(value), expected)
        reordered = {key: value[key] for key in reversed(value)}
        self.assertEqual(profile_digest(reordered), expected)
        value['description'] = 'Synthetic fixture only'
        self.assertNotEqual(profile_digest(value), expected)
        value['cpu']['config_sha256'] = None
        with self.assertRaises(ValueError):
            profile_digest(value)

    def test_binding_checks_all_declared_identities_and_copies_inputs(self):
        value, meta = profile(), metadata()
        meta['build'].update(runtime_sha256='b' * 64, bitstream_sha256='c' * 64,
                             loader_sha256='d' * 64, os_revision='fixture-os-rev',
                             sdk_revision='fixture-sdk-rev')
        original_profile, original_meta = copy.deepcopy(value), copy.deepcopy(meta)
        binding = bind_profile(value, meta)
        self.assertEqual(binding['definition'], value)
        self.assertEqual(binding['sha256'], profile_digest(value))
        checked = validate_binding(binding, meta)
        checked['definition']['features'].append('mutation')
        self.assertEqual(binding['definition'], value)
        self.assertEqual(value, original_profile)
        self.assertEqual(meta, original_meta)

    def test_binding_rejects_unknown_clock_mismatches_and_invalid_metadata(self):
        mismatches = [('platform', 'variant', 'os20'), ('platform', 'clock_hz', None),
                      ('platform', 'clock_hz', 90000000), ('build', 'runtime_sha256', 'e' * 64),
                      ('build', 'bitstream_sha256', 'e' * 64),
                      ('build', 'loader_sha256', 'e' * 64),
                      ('build', 'sdk_revision', 'different-sdk'),
                      ('build', 'os_revision', 'different-os'),
                      ('build', 'sdk_revision', None), ('build', 'loader_sha256', None),
                      ('build', 'source_revision', 'unknown')]
        for section, field, bad in mismatches:
            meta = metadata()
            meta[section][field] = bad
            before = copy.deepcopy(meta)
            with self.subTest(section=section, field=field), self.assertRaises(ValueError):
                bind_profile(profile(), meta)
            self.assertEqual(meta, before)

    def test_binding_rejects_tampered_digest_definition_and_extra_fields(self):
        binding = bind_profile(profile(), metadata())
        for change in ('digest', 'definition', 'extra', 'missing', 'malformed'):
            changed = copy.deepcopy(binding)
            if change == 'digest':
                changed['sha256'] = 'e' * 64
            elif change == 'definition':
                changed['definition']['cpu']['dcache_bytes'] = 65536
            elif change == 'extra':
                changed['unrecognized'] = True
            elif change == 'missing':
                del changed['sha256']
            else:
                changed['sha256'] = 'E' * 64
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_binding(changed, metadata())
        changed_meta = metadata()
        changed_meta['platform']['variant'] = 'os20'
        with self.assertRaises(ValueError):
            validate_binding(binding, changed_meta)


class PlatformArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.paths = {}
        for name in ('os_bin', 'bitstream', 'loader', 'cpu_config'):
            path = self.root / name
            path.write_bytes(f'synthetic {name} fixture'.encode())
            self.paths[name] = path

    def test_creator_hashes_four_explicit_files_without_mutating_or_writing(self):
        definition = profile('os20', 100000000)
        del definition['artifacts']
        del definition['cpu']['config_sha256']
        before = copy.deepcopy(definition)
        contents = {path: path.read_bytes() for path in self.paths.values()}
        created = profile_from_files(definition, **self.paths)
        self.assertEqual(created['variant'], 'os20')
        self.assertEqual(created['clock_hz'], 100000000)
        self.assertEqual(created['cpu']['issue_width'], 2)
        for key, name in [('os_sha256', 'os_bin'), ('bitstream_sha256', 'bitstream'),
                          ('loader_sha256', 'loader')]:
            self.assertEqual(created['artifacts'][key], hashlib.sha256(contents[self.paths[name]]).hexdigest())
        self.assertEqual(created['cpu']['config_sha256'],
                         hashlib.sha256(contents[self.paths['cpu_config']]).hexdigest())
        self.assertEqual(definition, before)
        self.assertEqual(set(self.root.iterdir()), set(contents))
        self.assertEqual({path: path.read_bytes() for path in contents}, contents)
        self.assertIsInstance(verify_profile_artifacts(created, **self.paths), dict)

    def test_creator_accepts_matching_hashes_and_rejects_any_supplied_conflict(self):
        definition = profile()
        del definition['artifacts']
        del definition['cpu']['config_sha256']
        created = profile_from_files(definition, **self.paths)
        self.assertEqual(profile_from_files(created, **self.paths), created)
        for section, field in [('cpu', 'config_sha256'), ('artifacts', 'os_sha256'),
                               ('artifacts', 'bitstream_sha256'), ('artifacts', 'loader_sha256')]:
            bad = copy.deepcopy(created)
            bad[section][field] = '0' * 64
            before = copy.deepcopy(bad)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'hash|SHA-256'):
                profile_from_files(bad, **self.paths)
            self.assertEqual(bad, before)

    def test_verifier_detects_tampering_in_each_artifact_and_missing_files(self):
        definition = profile()
        del definition['artifacts']
        del definition['cpu']['config_sha256']
        created = profile_from_files(definition, **self.paths)
        for name, path in self.paths.items():
            original = path.read_bytes()
            path.write_bytes(b'tampered fixture')
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'hash|SHA-256'):
                verify_profile_artifacts(created, **self.paths)
            path.write_bytes(original)
        self.paths['os_bin'].unlink()
        with self.assertRaises((ValueError, OSError)):
            verify_profile_artifacts(created, **self.paths)

    def test_creator_still_requires_declared_cpu_and_rejects_unknown_fields(self):
        for change in ('cpu', 'extra', 'artifacts_extra', 'null_artifacts', 'null_config_hash'):
            value = profile()
            del value['artifacts']
            del value['cpu']['config_sha256']
            if change == 'cpu':
                del value['cpu']['issue_width']
            elif change == 'extra':
                value['guess'] = True
            elif change == 'artifacts_extra':
                value['artifacts'] = {'unknown': 'a' * 64}
            elif change == 'null_artifacts':
                value['artifacts'] = None
            else:
                value['cpu']['config_sha256'] = None
            with self.subTest(change=change), self.assertRaises(ValueError):
                profile_from_files(value, **self.paths)


if __name__ == '__main__':
    unittest.main()
