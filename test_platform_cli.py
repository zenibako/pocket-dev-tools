"""Synthetic end-to-end platform identity and CLI persistence checks."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from benchmarks.__main__ import main
from benchmarks.model import compare_runs
from benchmarks.store import collect, load_run
from test_benchmarks import metadata, STANDARD, SWEEP
from test_platform_profiles import profile


class PlatformIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.meta = metadata()
        self.meta['build']['elf_sha256'] = 'e' * 64
        self.meta['conditions']['asset_manifest_sha256'] = 'f' * 64
        self.source = self.root / 'source.txt'
        self.source.write_bytes(STANDARD)
        self.metadata = self.write('metadata.json', self.meta)
        self.profile = self.write('profile.json', profile())

    def write(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value, indent=4) + '\n')
        return path

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with patch('benchmarks.__main__.ROOT', self.root), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = main([str(arg) for arg in args])
        return status, out.getvalue(), err.getvalue()

    def bundle(self, *, bound=True, name='runs'):
        return collect(self.source, self.metadata, 'butterscotch-device',
                       output=self.root / name, profile_path=self.profile if bound else None)

    def test_profile_bytes_are_preserved_and_tampering_detected(self):
        folder = self.bundle()
        run = load_run(folder)
        self.assertEqual(run['platform_profile']['definition'], profile())
        self.assertEqual((folder / 'platform-profile.json').read_bytes(), self.profile.read_bytes())
        (folder / 'platform-profile.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            load_run(folder)

    def test_bound_identity_differs_and_legacy_comparisons_are_provisional(self):
        bound = load_run(self.bundle())
        legacy = load_run(self.bundle(bound=False))
        self.assertNotEqual(bound['run_id'], legacy['run_id'])
        self.assertEqual(compare_runs(legacy, legacy)['qualification'], 'provisional')
        self.assertEqual(compare_runs(bound, bound)['qualification'], 'profile_bound')
        with self.assertRaisesRegex(ValueError, 'profile'):
            compare_runs(legacy, bound)

    def test_profile_binding_is_device_only_and_requires_known_matching_clock(self):
        self.meta['platform']['clock_hz'] = None
        self.metadata = self.write('metadata.json', self.meta)
        with self.assertRaises(ValueError):
            self.bundle()
        host = metadata(project='vvvvvv', game='vvvvvv', rows=['view:1:49:52:53:-1', 'result:1:49:52'])
        self.source.write_bytes(SWEEP)
        self.metadata = self.write('host.json', host)
        with self.assertRaisesRegex(ValueError, 'device'):
            collect(self.source, self.metadata, 'vvvvvv-host', output=self.root / 'host', profile_path=self.profile)

    def test_cli_profile_create_verify_and_no_overwrite(self):
        definition = profile()
        del definition['artifacts']
        del definition['cpu']['config_sha256']
        definition_path = self.write('definition.json', definition)
        flags = []
        for flag in ('os-bin', 'bitstream', 'loader', 'cpu-config'):
            path = self.root / flag
            path.write_bytes(flag.encode())
            flags.extend([f'--{flag}', path])
        output = self.root / 'build/platforms/fixture.json'
        self.assertEqual(self.cli('profile', 'create', definition_path, *flags, '--output', output)[0], 0)
        self.assertEqual(self.cli('profile', 'verify', output, *flags)[0], 0)
        self.assertEqual(self.cli('profile', 'create', definition_path, *flags, '--output', output)[0], 2)
        (self.root / 'loader').write_bytes(b'wrong')
        self.assertEqual(self.cli('profile', 'verify', output, *flags)[0], 2)
        self.assertEqual(self.cli('profile', 'create', definition_path, *flags, '--output', self.root / 'outside.json')[0], 2)

    def test_cli_controlled_clock_experiment_and_strict_default(self):
        first = self.bundle()
        self.meta['platform']['clock_hz'] = 90000000
        self.metadata = self.write('metadata90.json', self.meta)
        self.profile = self.write('profile90.json', profile(clock_hz=90000000))
        self.source.write_bytes(STANDARD.replace(b'100 MHz', b'90 MHz'))
        second = self.bundle()
        self.assertEqual(self.cli('compare', first, second)[0], 2)
        self.assertEqual(self.cli('compare', first, second, '--vary', 'clock')[0], 2)
        status, out, err = self.cli('compare', first, second, '--mode', 'platform', '--vary', 'clock')
        self.assertEqual(status, 0, err)
        report = json.loads(out)
        self.assertEqual(report['assessment'], 'descriptive_platform_experiment')
        self.assertEqual(report['varied_factors'], ['clock'])
        self.assertEqual(report['rows'][0]['metrics']['work_mean_us']['delta'], 0)

    def test_cli_import_matrix_and_invalid_bundle(self):
        status, out, err = self.cli('import', '--format', 'butterscotch-device', '--source', self.source,
                                    '--metadata', self.metadata, '--profile', self.profile)
        self.assertEqual(status, 0, err)
        folder = Path(out.strip())
        report_file = self.root / 'build/matrix.json'
        status, out, err = self.cli('matrix', '--runs', folder.parent, '--profiles', self.profile,
                                    '--project', 'butterscotch', '--output', report_file)
        self.assertEqual(status, 0, err)
        report = json.loads(out)
        self.assertEqual(len(report['rows'][0]['cells']), 4)
        self.assertEqual(report, json.loads(report_file.read_text()))
        self.assertEqual(self.cli('matrix', '--runs', folder, '--output', report_file)[0], 2)
        (folder.parent / 'incomplete').mkdir()
        self.assertEqual(self.cli('matrix', '--runs', folder.parent)[0], 2)
        status, out, err = self.cli('matrix', '--project', 'pico8pocket')
        self.assertEqual(status, 0, err)
        self.assertEqual([cell['status'] for cell in json.loads(out)['rows'][0]['cells']], ['untested'] * 4)


if __name__ == '__main__':
    unittest.main()
