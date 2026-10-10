"""Comparison regression tests: pointers, real output changes and stale evidence."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import experiments


class CompilerSwitchTest(unittest.TestCase):
    def test_define_and_undefine_order_is_preserved(self):
        self.assertEqual(experiments.compiler_switches('-DUT_CACHED_HELD_ROWS -DENABLE_VM_GML_PROFILER -UENABLE_VM_GML_PROFILER'),
                         ['-DUT_CACHED_HELD_ROWS', '-DENABLE_VM_GML_PROFILER', '-UENABLE_VM_GML_PROFILER'])

    def test_numeric_defines_and_empty_control(self):
        self.assertEqual(experiments.compiler_switches(''), [])
        self.assertEqual(experiments.compiler_switches('-DCOUNT=2000 -DRATE=0.5'), ['-DCOUNT=2000', '-DRATE=0.5'])

    def test_file_plugin_shell_and_split_arguments_are_rejected(self):
        for flags in ['-include /tmp/code.h', '-o /tmp/program', '-fplugin=code',
                      '-Wl,-T,/tmp/link.ld', '-D NAME', '-UFOO=1', '-DNAME=$(id)',
                      '-DNAME=@file', '-DNAME=/tmp/file']:
            with self.subTest(flags=flags), self.assertRaises(ValueError):
                experiments.compiler_switches(flags)


class ComparisonTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def case(self, name, *, changed_pixel=None, changed_pcm=None, state=0, mode='accuracy'):
        root = self.root / name
        directory = root / 'build/fullframe/deltarune/bram'
        directory.mkdir(parents=True)
        (root / 'input-manifest.json').write_text('{"sources":{}}')
        (root / 'snapshot.json').write_text(json.dumps({'revision': name}))
        config = dict(game='deltarune', variant='bram', window='dodge', first_frame=3323,
                      mode=mode, kind='trace', framebuffer='cached', clock_cost=0, audio='fixed')
        (root / 'experiment.json').write_text(json.dumps(config))
        (directory / 'program.elf').write_bytes(b'fixture')
        repeats = []
        for repeat in range(2):
            folder = directory / f'repeat-{repeat}'
            folder.mkdir()
            files = {}
            for index in range(3):
                pixel = b'\x01\x00' if changed_pixel == index else b'\x00\x00'
                pcm = b'\x01\x00\x00\x00' if changed_pcm == index else b'\x00' * 4
                for extension, data in [('rgb555', pixel), ('pcm', pcm), ('ppm', b'P6\n1 1\n255\n' + b'\0' * 3)]:
                    name = f'frame-{index}.{extension}'
                    (folder / name).write_bytes(data)
                    files[name] = experiments.sha(folder / name)
            repeats.append(files)
        manifest = dict(rows=[[3323+i, state, 0, 0, 1, 0, 0, 0] for i in range(3)],
                        repeats=repeats, build={'sources': {}}, elf_sha256=experiments.sha(directory / 'program.elf'))
        (directory / 'capture.json').write_text(json.dumps(manifest))
        return root

    def compare(self, baseline, candidate):
        args = argparse.Namespace(baseline=baseline, candidate=candidate, output=self.root / 'report/results.json')
        with contextlib.redirect_stdout(io.StringIO()):
            result = experiments.compare(args)
        return result, json.loads(args.output.read_text())

    def test_pointer_state_changes_do_not_fail_output_comparison(self):
        passed, report = self.compare(self.case('a', state=0x10001000), self.case('b', state=0x10002000))
        self.assertTrue(passed)
        self.assertFalse(report['state_hash_compared'])

    def test_one_pixel_reports_first_frame_and_retains_both_images(self):
        passed, report = self.compare(self.case('a'), self.case('b', changed_pixel=1))
        self.assertFalse(passed)
        first = report['first_difference']
        self.assertEqual((first['frame'], first['field']), (3324, 'pixels'))
        self.assertEqual(first['different_pixels'], 1)
        for path in first['images'].values():
            self.assertTrue(Path(path).is_file())

    def test_pcm_change_is_detected(self):
        passed, report = self.compare(self.case('a'), self.case('b', changed_pcm=0))
        self.assertFalse(passed)
        self.assertEqual(report['first_difference']['field'], 'pcm')

    def test_stale_capture_cannot_be_blessed_by_comparison(self):
        a, b = self.case('a'), self.case('b')
        (b / 'build/fullframe/deltarune/bram/program.elf').write_bytes(b'changed binary')
        with self.assertRaisesRegex(ValueError, 'executable'):
            self.compare(a, b)

    def test_raw_audio_length_must_match_pair_count(self):
        a, b = self.case('a'), self.case('b')
        path = b / 'build/fullframe/deltarune/bram/capture.json'
        manifest = json.loads(path.read_text())
        manifest['rows'][0][4] = 2
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'PCM count'):
            self.compare(a, b)

    def test_probe_calls_are_not_mistaken_for_pcm_and_audio_must_be_empty(self):
        root = self.case('probe')
        config_path = root / 'experiment.json'
        config = json.loads(config_path.read_text())
        config['workload'] = 'sprite-probe'
        config_path.write_text(json.dumps(config))
        path = root / 'build/fullframe/deltarune/bram/capture.json'
        manifest = json.loads(path.read_text())
        for row in manifest['rows']:
            row[4] = 2000
        for repeat, files in enumerate(manifest['repeats']):
            folder = path.parent / f'repeat-{repeat}'
            for index in range(3):
                name = f'frame-{index}.pcm'
                (folder / name).write_bytes(b'')
                files[name] = experiments.sha(folder / name)
        path.write_text(json.dumps(manifest))
        experiments.checked_capture(root)
        audio = path.parent / 'repeat-1/frame-0.pcm'
        audio.write_bytes(b'\0' * 4)
        manifest['repeats'][1][audio.name] = experiments.sha(audio)
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'PCM count'):
            experiments.checked_capture(root)

    def test_speed_and_accuracy_are_not_silently_compared(self):
        with self.assertRaisesRegex(ValueError, 'mode'):
            self.compare(self.case('a'), self.case('b', mode='speed'))

    def test_realtime_audio_cannot_claim_cross_build_pcm_agreement(self):
        a, b = self.case('a'), self.case('b')
        for root in [a, b]:
            path = root / 'experiment.json'
            config = json.loads(path.read_text())
            config['audio'] = 'realtime'
            path.write_text(json.dumps(config))
        with self.assertRaisesRegex(ValueError, 'fixed audio'):
            self.compare(a, b)

    def test_native_script_settings_must_match(self):
        a, b = self.case('a'), self.case('b')
        path = b / 'experiment.json'
        config = json.loads(path.read_text())
        config['native'] = 'enabled'
        path.write_text(json.dumps(config))
        with self.assertRaisesRegex(ValueError, 'native script'):
            self.compare(a, b)

    def test_audio_accounting_catches_dropped_time_after_last_poll(self):
        result = dict(config={'audio': 'realtime'}, rows=[{'cycles': 30000000}],
                      frame_costs=[{'audio_pairs_consumed': 800}])
        with self.assertRaisesRegex(ValueError, 'complete frame'):
            experiments.check_audio_costs(result)
        result['frame_costs'][0]['audio_pairs_consumed'] = 14400
        experiments.check_audio_costs(result)


if __name__ == '__main__':
    unittest.main()
