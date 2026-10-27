"""Collection must catch wrong domains, incomplete runs and lost source evidence.

All measurements and build identities here are synthetic parser fixtures.
"""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from benchmarks.adapters import parse_report
from benchmarks.model import compare_runs, validate_metadata
from benchmarks.store import collect, inspect_source, load_run


STANDARD = b'''Butterscotch log, file for undertale
=== Undertale benchmark, speed, -O2 ===
OS 0.25.0, core variant 1, CPU 100 MHz
ms per frame:          work   total
intro, menu, naming     18.1   18.5
Flowey battle (640x480) 40.0   40.5
2600 frames in 65.3 s; full speed is 33.3
work = total minus display flip
--- end of report ---
'''
FOCUS = b'''=== Focused Deltarune benchmark normal ===
route card-castle-tiles; room 65 room_field_checkers4
build abcdef0123456789; seed 7; Speed; uncapped; input-frame windows
OS 0.25.0 core 1 CPU 100MHz
counterfactual: render=on audio=on profile=off
us/frame; work=own frame wall minus own flip; correlated samples
window N filtered mean median p95 max flip present
encounter-reveal 10 50 18000 17500 21000 22000 300 500
  blocks10 us: 18000
encounter-full 30 0 16000 15500 19000 20000 300 500
observation-reveal 10 90 19000 18500 22000 23000 300 500
observation-full 50 0 17000 16500 20000 21000 300 500
tiles-walk 70 0 22000 21500 25000 26000 300 500
tiles-reset-cycle 100 0 23000 22500 26000 27000 300 500
tiles-still 100 0 20000 19500 23000 24000 300 500
FOCUS PASS normal
--- end of report ---
'''
FOCUS_ROWS = ['encounter-reveal', 'encounter-full', 'observation-reveal',
              'observation-full', 'tiles-walk', 'tiles-reset-cycle', 'tiles-still']
SWEEP = b'''SWEEP_VIEW,1,49,52,53,-1,360,26400,8500,17000,42000,"Panic Room"
SWEEP_RESULT,1,49,52,53,-1,26400,8500,17000,47000,"Panic Room"
Final sweep passed: 1 cases, 1 scrolling cases; HOST wall time only
'''


def metadata(project='butterscotch', game='undertale', rows=None):
    return dict(schema_version=1, project=project, game=game, repeat=1,
                build=dict(id='fixture-build', source_revision='abcdef0123456789',
                           compiler='fixture-compiler', flags=['-O2']),
                platform=dict(variant='os25', clock_hz=100000000, device_id='fixture-pocket'),
                case=dict(id='fixture-route', suite='focused', route_version='fixture-v1',
                          mode='speed', seed=7, warmup_frames=0, target_hz=30,
                          expected_rows=rows or ['intro, menu, naming', 'Flowey battle (640x480)']),
                conditions=dict(initial_state='fresh', audio='on', pacing='uncapped'))


class AdapterTests(unittest.TestCase):
    def focus_metadata(self):
        meta = metadata(game='deltarune', rows=FOCUS_ROWS)
        meta['case'].update(mode='normal', route_version='card-castle-tiles-v1')
        return meta

    def test_nul_padding_is_not_parsed_as_another_report(self):
        result = parse_report('butterscotch-device', STANDARD + b'\0' + STANDARD, metadata())
        self.assertEqual(result['backend'], 'device')
        self.assertEqual(result['rows'][0]['metrics']['work_mean_us'], 18100)
        self.assertEqual(result['rows'][1]['metrics']['total_mean_us'], 40500)
        self.assertIsNone(result['rows'][0]['samples'])
        self.assertEqual(result['checks']['identity'], 'declared')
        self.assertEqual(result['checks']['correctness'], 'not_checked')

    def test_accumulated_reports_require_selection_and_keep_failed_runs(self):
        raw = FOCUS + FOCUS.replace(b'FOCUS PASS normal', b'FOCUS FAIL normal')
        with self.assertRaisesRegex(ValueError, 'report.index'):
            parse_report('butterscotch-device', raw, self.focus_metadata())
        result = parse_report('butterscotch-device', raw, self.focus_metadata(), 1)
        self.assertEqual(result['checks']['correctness'], 'reported_fail')
        self.assertEqual(result['report_index'], 1)

    def test_focus_uses_saved_pass_marker_not_post_dump_ui_text(self):
        result = parse_report('butterscotch-device', FOCUS, self.focus_metadata())
        self.assertEqual(result['checks']['identity'], 'embedded')
        self.assertEqual(result['checks']['correctness'], 'reported_pass')
        self.assertEqual(result['rows'][0]['metrics']['work_p95_us'], 21000)
        self.assertEqual(result['rows'][0]['samples'], 10)

    def test_truncated_duplicate_missing_and_wrong_scene_reports_are_rejected(self):
        cases = [FOCUS.replace(b'--- end of report ---', b''),
                 FOCUS.replace(b'FOCUS PASS normal', b''),
                 FOCUS.replace(b'encounter-full 30', b'encounter-reveal 30'),
                 FOCUS.replace(b'tiles-still 100 0 20000 19500 23000 24000 300 500\n', b''),
                 FOCUS.replace(b'encounter-reveal 10', b'encounter-reveal 1'),
                 FOCUS.replace(b'room 65 room_field_checkers4', b'room 1 wrong_scene')]
        for raw in cases:
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    parse_report('butterscotch-device', raw, self.focus_metadata())

    def test_embedded_identity_mode_seed_and_clock_must_match(self):
        for old, new in [(b'abcdef0123456789', b'1111111111111111'),
                         (b'benchmark normal', b'benchmark profile'),
                         (b'seed 7;', b'seed 8;'), (b'100MHz', b'90MHz')]:
            with self.subTest(old=old):
                with self.assertRaises(ValueError):
                    parse_report('butterscotch-device', FOCUS.replace(old, new), self.focus_metadata())
        with self.assertRaisesRegex(ValueError, 'game'):
            parse_report('butterscotch-device', STANDARD, metadata(game='deltarune'))

    def test_host_text_cannot_be_imported_as_device_measurements(self):
        raw = STANDARD.replace(b'OS 0.25.0, core variant 1, CPU 100 MHz\n', b'')
        with self.assertRaisesRegex(ValueError, 'device'):
            parse_report('butterscotch-device', raw, metadata())

    def test_vvvvvv_views_and_cross_view_peaks_stay_separate_and_host_only(self):
        meta = metadata('vvvvvv', 'vvvvvv', ['view:1:49:52:53:-1', 'result:1:49:52'])
        result = parse_report('vvvvvv-host', SWEEP, meta)
        self.assertEqual(result['backend'], 'host')
        self.assertEqual(result['rows'][0]['samples'], 360)
        self.assertEqual(result['rows'][0]['metrics']['frame_max_us'], 42000)
        self.assertEqual(result['rows'][1]['metrics']['cross_view_max_us'], 47000)
        self.assertNotIn('frame_max_us', result['rows'][1]['metrics'])
        for raw in [SWEEP.split(b'Final sweep')[0], SWEEP.replace(b'1 cases', b'2 cases'),
                    SWEEP.replace(b',26400,', b',nan,'), SWEEP + SWEEP]:
            with self.assertRaises(ValueError):
                parse_report('vvvvvv-host', raw, meta)

    def test_manual_device_values_require_units_and_do_not_become_correctness_pass(self):
        meta = metadata('vvvvvv', 'vvvvvv', ['party-time-off'])
        raw = json.dumps(dict(rows=[dict(id='party-time-off', samples=240,
                  metrics=dict(work_mean_us=32700, frame_max_us=50000))])).encode()
        result = parse_report('device-summary', raw, meta)
        self.assertEqual(result['backend'], 'device')
        self.assertEqual(result['checks']['correctness'], 'not_checked')
        self.assertIn('transcribed', ' '.join(result['limits']))
        for metric in [dict(mean=32.7), dict(work_mean_us=float('nan')),
                       dict(work_mean_us=-1)]:
            with self.assertRaises(ValueError):
                parse_report('device-summary', json.dumps(dict(rows=[dict(
                    id='party-time-off', samples=240, metrics=metric)])).encode(), meta)

    def test_simulation_wrap_keeps_limits_and_does_not_claim_fresh_verification(self):
        meta = metadata(rows=['frame:2400', 'frame:2401'])
        config = dict(game='undertale', mode='speed', window='flowey', variant='bram')
        raw = json.dumps(dict(cases=[dict(config=config, revision='abcdef0123456789',
              negative_oracle_rejected=True, rows=[dict(oracle=[2400], cycles=100000,
              simulated_ms=1), dict(oracle=[2401], cycles=200000, simulated_ms=2)],
              substitutions=['virtual files'], oracle_excluded_fields=['pcm'])],
              limits=['physical SD not modeled'])).encode()
        result = parse_report('harness-revision', raw, meta)
        self.assertEqual(result['backend'], 'simulation')
        self.assertEqual(result['rows'][0]['metrics']['frame_cycles'], 100000)
        self.assertEqual(result['checks']['correctness'], 'reported_pass')
        self.assertIn('physical SD not modeled', result['limits'])
        self.assertEqual(result['source_config'], config)

        invalid = json.loads(raw)
        invalid['cases'][0]['rows'][0]['simulated_ms'] = float('nan')
        with self.assertRaises(ValueError):
            parse_report('harness-revision', json.dumps(invalid).encode(), meta)

    def test_metadata_rejects_missing_roster_boolean_counts_and_nonfinite_values(self):
        for field, value in [('expected_rows', []), ('warmup_frames', True),
                             ('target_hz', float('inf'))]:
            meta = metadata()
            meta['case'][field] = value
            with self.assertRaises(ValueError):
                validate_metadata(meta)

    def test_simulator_adapter_hash_changes_are_not_application_speedups(self):
        meta = metadata(rows=['frame:2400'])
        config = dict(game='undertale', mode='speed', window='flowey', variant='bram',
                      adapter_sources={'platform.c': 'a'*64}, launcher_sha256='b'*64)
        raw = dict(cases=[dict(config=config, revision=meta['build']['source_revision'],
                 rows=[dict(oracle=[2400], cycles=100000, simulated_ms=1)])])
        base = parse_report('harness-revision', json.dumps(raw).encode(), meta)
        for field, replacement in [('adapter_sources', {'platform.c': 'c'*64}),
                                   ('launcher_sha256', 'd'*64)]:
            changed = copy.deepcopy(raw)
            changed['cases'][0]['config'][field] = replacement
            candidate = parse_report('harness-revision', json.dumps(changed).encode(), meta)
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, 'incompatible'):
                    compare_runs(base, candidate)


class StoreTests(unittest.TestCase):
    def setUp(self):
        # The CLI deliberately writes only in the harness's private build tree.
        private = Path(__file__).resolve().parent / 'build'
        private.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='benchmark-tests-', dir=private)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'undertale_1.sav'
        self.source.write_bytes(STANDARD + b'\0\xff\x00')
        self.meta = self.root / 'run.json'
        self.meta.write_text(json.dumps(metadata()))
        self.output = self.root / 'runs'

    def collect(self, **kwargs):
        return collect(self.source, self.meta, 'butterscotch-device', output=self.output, **kwargs)

    def test_import_preserves_source_and_rejects_overwrite_or_stale_evidence(self):
        original = self.source.read_bytes()
        folder = self.collect()
        run = load_run(folder)
        raw = folder / run['evidence'][0]['path']
        self.assertEqual(raw.read_bytes(), original)
        self.assertEqual(self.source.read_bytes(), original)
        self.assertEqual(run['evidence'][0]['sha256'], hashlib.sha256(original).hexdigest())
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.collect()
        renamed = self.root / 'copied-log.sav'
        renamed.write_bytes(original)
        with self.assertRaisesRegex(ValueError, 'already exists'):
            collect(renamed, self.meta, 'butterscotch-device', output=self.output)
        raw.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'hash'):
            load_run(folder)

    def test_result_and_metadata_tampering_and_path_escape_are_rejected(self):
        for target in ['result.json', 'metadata.json']:
            with self.subTest(target=target):
                output = self.root / target.replace('.', '-')
                folder = collect(self.source, self.meta, 'butterscotch-device', output=output)
                value = json.loads((folder / target).read_text())
                value['tampered'] = True
                (folder / target).write_text(json.dumps(value))
                with self.assertRaisesRegex(ValueError, 'hash'):
                    load_run(folder)

        folder = self.collect()
        manifest = json.loads((folder / 'manifest.json').read_text())
        manifest['files']['../undertale_1.sav'] = hashlib.sha256(self.source.read_bytes()).hexdigest()
        (folder / 'manifest.json').write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'escapes'):
            load_run(folder)

    def test_manual_summary_requires_a_screenshot_attachment(self):
        self.meta.write_text(json.dumps(metadata('vvvvvv', 'vvvvvv', ['room'])))
        self.source.write_text(json.dumps(dict(rows=[dict(id='room', samples=240,
                                                         metrics=dict(work_mean_us=32000))])))
        with self.assertRaisesRegex(ValueError, 'screenshot'):
            collect(self.source, self.meta, 'device-summary', output=self.output)
        screenshot = self.root / 'page-1.png'
        screenshot.write_bytes(b'\x89PNG\r\n\x1a\nsynthetic screenshot fixture')
        folder = collect(self.source, self.meta, 'device-summary', output=self.output,
                         attachments=[screenshot])
        self.assertEqual(len(load_run(folder)['evidence']), 2)

    def test_invalid_import_leaves_no_run_and_never_changes_input(self):
        self.source.write_bytes(STANDARD.split(b'--- end')[0])
        original = self.source.read_bytes()
        with self.assertRaises(ValueError):
            self.collect()
        self.assertEqual(self.source.read_bytes(), original)
        self.assertFalse(self.output.exists())

    def test_inspection_lists_completed_and_truncated_accumulated_reports(self):
        self.source.write_bytes(STANDARD + FOCUS.split(b'--- end')[0] + b'\0' + STANDARD)
        reports = inspect_source(self.source)
        self.assertEqual([item['index'] for item in reports], [0, 1])
        self.assertEqual([item['complete'] for item in reports], [True, False])
        self.assertEqual(reports[1]['embedded_build'], 'abcdef0123456789')

    def test_compatible_comparison_reports_literal_delta_without_cross_domain_mixing(self):
        base = load_run(self.collect())
        self.source.write_bytes(STANDARD.replace(b'18.1', b'16.1'))
        candidate = load_run(self.collect())
        result = compare_runs(base, candidate)
        self.assertEqual(result['rows'][0]['metrics']['work_mean_us']['delta'], -2000)
        self.assertAlmostEqual(result['rows'][0]['metrics']['work_mean_us']['percent'], -2000 / 181)
        self.assertEqual(result['assessment'], 'descriptive_only')
        for target, key, value in [('run', 'backend', 'host'), ('case', 'mode', 'accuracy'),
                                   ('platform', 'variant', 'os20'), ('build', 'compiler', 'other')]:
            changed = copy.deepcopy(candidate)
            (changed if target == 'run' else changed['metadata'][target])[key] = value
            with self.subTest(target=target):
                with self.assertRaisesRegex(ValueError, 'incompatible'):
                    compare_runs(base, changed)

    def test_different_sampling_and_failed_runs_cannot_be_compared_as_improvements(self):
        base = load_run(self.collect())
        for change in ['sampling', 'failed', 'roster']:
            candidate = copy.deepcopy(base)
            if change == 'sampling':
                candidate['rows'][0]['samples'] = 2
            elif change == 'failed':
                candidate['checks']['correctness'] = 'reported_fail'
            else:
                candidate['rows'].pop()
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    compare_runs(base, candidate)

    def test_reported_hardware_and_total_frames_are_comparison_requirements(self):
        meta = metadata()
        meta['platform']['clock_hz'] = None
        base = parse_report('butterscotch-device', STANDARD, meta)
        for old, new in [(b'0.25.0', b'0.26.0'), (b'variant 1', b'variant 2'),
                         (b'100 MHz', b'90 MHz'), (b'2600 frames', b'2700 frames')]:
            candidate = parse_report('butterscotch-device', STANDARD.replace(old, new), meta)
            with self.subTest(old=old):
                with self.assertRaisesRegex(ValueError, 'incompatible'):
                    compare_runs(base, candidate)

    def test_runtime_and_sdk_changes_cannot_hide_inside_build_provenance(self):
        base = load_run(self.collect())
        for field, value in [('runtime_sha256', 'a'*64), ('bitstream_sha256', 'b'*64),
                             ('sdk_revision', 'different-sdk')]:
            candidate = copy.deepcopy(base)
            candidate['metadata']['build'][field] = value
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, 'incompatible'):
                    compare_runs(base, candidate)

    def test_cli_software_comparison_retains_source_limits_and_checks(self):
        meta = metadata(rows=['frame:2400'])
        self.meta.write_text(json.dumps(meta))
        config = dict(game='undertale', mode='speed', window='flowey', variant='bram')
        folders, runs = [], []
        for checked, limit in [(True, 'physical SD not modeled'),
                               (False, 'hardware audio not modeled')]:
            report = dict(cases=[dict(config=config, revision=meta['build']['source_revision'],
                negative_oracle_rejected=checked,
                rows=[dict(oracle=[2400], cycles=100000, simulated_ms=1)])],
                limits=[limit, 'shared source limitation'])
            self.source.write_text(json.dumps(report))
            folder = collect(self.source, self.meta, 'harness-revision', output=self.output)
            folders.append(folder)
            runs.append(load_run(folder))
        result = subprocess.run([sys.executable, '-m', 'benchmarks', 'compare',
            *(str(folder) for folder in folders)], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        comparison = json.loads(result.stdout)
        for run in runs:
            for limit in run['limits']:
                self.assertIn(limit, comparison['limits'])
        self.assertEqual(comparison['limits'].count('shared source limitation'), 1)
        self.assertEqual(comparison['source_checks'],
                         dict(baseline=runs[0]['checks'], candidate=runs[1]['checks']))
        self.assertEqual(comparison['source_checks']['candidate']['correctness'], 'not_checked')
        self.assertEqual(comparison['rows'][0]['metrics']['frame_cycles']['delta'], 0)

    def test_cli_rejects_nonobject_revision_reports_without_traceback_or_output(self):
        for value in [[], 'not a report', 42, None, False]:
            with self.subTest(value=value):
                raw = json.dumps(value)
                self.source.write_text(raw)
                result = subprocess.run([sys.executable, '-m', 'benchmarks', 'import',
                    '--format', 'harness-revision', '--source', str(self.source),
                    '--metadata', str(self.meta), '--output', str(self.output)],
                    text=True, capture_output=True)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn('expected an experiments.py revision report with cases', result.stderr)
                self.assertNotIn('Traceback', result.stderr)
                self.assertEqual(result.stdout, '')
                self.assertFalse(self.output.exists())
                self.assertEqual(self.source.read_text(), raw)

    def test_cli_import_verify_compare_and_missing_input_exit_status(self):
        command = [sys.executable, '-m', 'benchmarks']
        imported = subprocess.run(command + ['import', '--format', 'butterscotch-device',
            '--source', str(self.source), '--metadata', str(self.meta), '--output', str(self.output)],
            text=True, capture_output=True)
        self.assertEqual(imported.returncode, 0, imported.stderr)
        folder = Path(imported.stdout.strip())
        for args in [['verify', str(folder)], ['compare', str(folder), str(folder)]]:
            result = subprocess.run(command + args, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            json.loads(result.stdout)
        failed = subprocess.run(command + ['verify', str(self.root / 'absent')],
                                text=True, capture_output=True)
        self.assertEqual(failed.returncode, 2)
        self.assertNotIn('Traceback', failed.stderr)


if __name__ == '__main__':
    unittest.main()
