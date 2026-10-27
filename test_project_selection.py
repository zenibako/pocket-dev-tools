"""New projects can evaluate a shortlist without acquiring replay support."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from benchmarks.__main__ import main
from benchmarks.adapters import parse_report
from benchmarks.coverage import coverage_matrix
from benchmarks.model import validate_metadata
from test_benchmarks import metadata, STANDARD, SWEEP
from test_platform_profiles import profile


class NewProjectSelectionTests(unittest.TestCase):
    def cli(self, root, *args):
        out, err = io.StringIO(), io.StringIO()
        with patch('benchmarks.__main__.ROOT', root), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                status = main([str(arg) for arg in args])
            except SystemExit as exc:
                status = exc.code
        return status, out.getvalue(), err.getvalue()

    def test_new_project_identity_is_explicit_and_bounded(self):
        for name in ('nova-pocket', 'newcore2', 'a', 'a' * 64):
            meta = metadata(project=name)
            self.assertEqual(validate_metadata(meta)['project'], name)
        for name in (None, True, 1, '', 'Nova', 'nova pocket', '../nova', '-nova', 'nova-', 'nova--pocket', 'a' * 65):
            with self.subTest(project=name), self.assertRaises(ValueError):
                validate_metadata(metadata(project=name))

    def test_new_project_cli_can_import_compare_and_inspect_a_shortlist(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # Synthetic signature fixture; the importer never certifies image contents.
            shot = root / 'fixture.png'
            shot.write_bytes(b'\x89PNG\r\n\x1a\nsynthetic-only')
            profiles, runs = [], []
            for variant, clock, duration in [('os20', 90000000, 1000), ('os25', 100000000, 800)]:
                definition = profile(variant, clock)
                meta = metadata(project='nova-pocket', game='nova', rows=['representative-scene'])
                meta['platform'].update(variant=variant, clock_hz=clock)
                meta['build']['elf_sha256'] = 'e' * 64
                meta['conditions']['asset_manifest_sha256'] = 'f' * 64
                paths = []
                for suffix, value in [('profile', definition), ('metadata', meta), ('summary', dict(rows=[dict(
                        id='representative-scene', samples=120, metrics=dict(frame_mean_us=duration))]))]:
                    path = root / f'{variant}-{suffix}.json'
                    path.write_text(json.dumps(value))
                    paths.append(path)
                profile_path, meta_path, summary_path = paths
                status, out, err = self.cli(root, 'import', '--format', 'device-summary',
                    '--source', summary_path, '--metadata', meta_path, '--attachment', shot, '--profile', profile_path)
                self.assertEqual(status, 0, err)
                profiles.append(profile_path)
                runs.append(Path(out.strip()))
            status, out, err = self.cli(root, 'matrix', '--runs', *runs, '--profiles', *profiles,
                                        '--project', 'nova-pocket')
            self.assertEqual(status, 0, err)
            cells = json.loads(out)['rows'][0]['cells']
            self.assertEqual(sum(c['counts']['total'] for c in cells), 2)
            self.assertEqual(sum(c['status'] == 'untested' for c in cells), 2)
            self.assertTrue(all(c['counts']['failures'] == 0 for c in cells))
            self.assertEqual(self.cli(root, 'compare', *runs)[0], 2)
            status, out, err = self.cli(root, 'compare', *runs, '--mode', 'platform', '--vary', 'clock', '--vary', 'variant')
            self.assertEqual(status, 0, err)
            result = json.loads(out)
            self.assertEqual(result['rows'][0]['metrics']['frame_mean_us']['delta'], -200)
            self.assertIn('transcribed', ' '.join(result['limits']))
            # A new SDK-specific application binary is a whole configuration experiment.
            changed_meta = json.loads(meta_path.read_text())
            changed_meta['build']['elf_sha256'] = 'd' * 64
            meta_path.write_text(json.dumps(changed_meta))
            status, out, err = self.cli(root, 'import', '--format', 'device-summary', '--source', summary_path,
                '--metadata', meta_path, '--attachment', shot, '--profile', profile_path)
            self.assertEqual(status, 0, err)
            self.assertEqual(self.cli(root, 'compare', runs[0], out.strip(), '--mode', 'platform',
                                     '--vary', 'clock', '--vary', 'variant')[0], 2)

    def test_new_project_filter_is_available_before_any_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            status, out, err = self.cli(Path(directory), 'matrix', '--project', 'nova-pocket')
            self.assertEqual(status, 0, err)
            row = json.loads(out)['rows'][0]
            self.assertEqual(row['scope']['project'], 'nova-pocket')
            self.assertEqual([c['status'] for c in row['cells']], ['untested'] * 4)
        with self.assertRaises(ValueError):
            coverage_matrix([], project='../nova')

    def test_new_ids_do_not_enable_project_specific_adapters(self):
        for format_name, raw in [('butterscotch-device', STANDARD), ('vvvvvv-host', SWEEP)]:
            with self.subTest(format=format_name), self.assertRaisesRegex(ValueError, 'project'):
                parse_report(format_name, raw, validate_metadata(metadata(project='nova-pocket')))


if __name__ == '__main__':
    unittest.main()
