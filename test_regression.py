"""Synthetic disk fixtures exercise validation, never constitute device evidence."""
import argparse
import contextlib
import json
from pathlib import Path
import shutil
import tempfile
import subprocess
import unittest
from unittest.mock import patch

import experiments
try:
    import regression
except ModuleNotFoundError:
    regression = None


class RegressionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.enterContext(contextlib.redirect_stdout(__import__('io').StringIO()))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        # Only location globals are replaced. Capture, report and comparison run normally.
        for module in [experiments, regression]:
            if module:
                self.enterContext(patch.object(module, 'ROOT', self.root))
        self.enterContext(patch.object(experiments, 'PRIVATE', self.root / 'experiments'))
        (self.root / 'bench').mkdir()
        for name in ['build.py', 'rtl.py', 'runtime.c', 'bridge.c']:
            (self.root / 'bench' / name).write_text('synthetic adapter ' + name)
        (self.root / 'experiments.py').write_text(Path(experiments.__file__).read_text())
        (self.root / 'bench/device-references.json').write_text('{"measurements":[],"device_compiler_version":null}')
        (self.root / 'input-manifest.json').write_text('{"sources":{},"source_revisions":{}}')
        (self.root / 'compiler').write_text('#!/bin/sh\necho "synthetic compiler 1"\n')
        (self.root / 'compiler').chmod(0o755)

    def save(self, path, data):
        experiments.save(path, data)

    def file(self, path, data=b'synthetic'):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return experiments.sha(path)

    def case(self, name, *, revision='a' * 40, pixel=False, native='enabled', kind='trace', audio='fixed'):
        root = self.root / 'experiments/cases' / name
        d = root / 'build/fullframe/deltarune/bram'
        d.mkdir(parents=True)
        self.save(root / 'input-manifest.json', {'sources': {}, 'source_revisions': {'butterscotch-mirror': revision}})
        self.save(root / 'snapshot.json', dict(name=name, revision=revision, exported_sources={}, patch_sha256=None,
                    parent_manifest_sha256=experiments.sha(self.root / 'input-manifest.json'),
                    manifest_sha256=experiments.sha(root / 'input-manifest.json')))
        adapter = {p.name: experiments.sha(p) for p in (self.root / 'bench').iterdir() if p.suffix in ['.c', '.S', '.py']}
        config = dict(snapshot=name, snapshot_sha256=experiments.sha(root / 'snapshot.json'),
                      game='deltarune', window='dodge', first_frame=3323, mode='accuracy', kind=kind,
                      variant='bram', profile='port', native=native, alignment=True,
                      framebuffer='cached', clock_cost=0, audio=audio, compiler=str(self.root / 'compiler'),
                      adapter_sources=adapter, launcher_sha256=experiments.sha(self.root / 'experiments.py'))
        self.save(root / 'experiment.json', config)
        self.save(root / 'case-ready.json', {'config_sha256': experiments.sha(root / 'experiment.json')})
        self.file(root / 'fullframe/rtl.py', (self.root / 'bench/rtl.py').read_bytes())
        for name, digest in adapter.items():
            shutil.copy2(self.root / 'bench' / name, root / 'fullframe' / name)
        self.file(root / 'build/fullframe/rtl/main.cpp')
        self.file(root / 'build/rtl/rtl.json')
        self.file(root / 'build/fullframe/rtl/obj/Vtb_system')
        rtl = dict(simulator_sha256=experiments.sha(root / 'build/fullframe/rtl/obj/Vtb_system'),
                   generator_sha256=experiments.sha(root / 'fullframe/rtl.py'),
                   source_sha256=experiments.sha(root / 'build/fullframe/rtl/main.cpp'),
                   leaf_rtl_sha256=experiments.sha(root / 'build/rtl/rtl.json'))
        self.save(root / 'build/fullframe/rtl/rtl.json', rtl)
        for name in ['program.elf', 'program.bin', 'stack.bin', 'firmware.mif']:
            self.file(d / name)
        # FNV-1a of eight zero bytes / 01 00 followed by six zero bytes.
        rows = [[3323+i, 1, 0x3e801244 if pixel and i == 0 else 0x9be17165, 3, 1, 6, 7, 8] for i in range(3)]
        log = 'FRAMEHARNESS PASS HAL init\n' + ''.join(
            f'FRAMERESULT {r[0]} 100000 1 {r[2]:08x} 3 1 6 7 8\n' for r in rows)
        repeats = []
        for repeat in range(2):
            files = {}
            for name in ['checkpoint.bin', 'stack.bin', 'checkpoint-info.bin']:
                files[name] = self.file(d / f'repeat-{repeat}' / name)
            files['capture.log'] = self.file(d / f'repeat-{repeat}/capture.log', log.encode())
            for index in range(3):
                for ext, data in [('rgb555', (b'\x01\x00' + b'\0'*6) if pixel and index == 0 else b'\0'*8),
                                  ('pcm', b'\0'*4), ('ppm', b'P6\n2 2\n255\n' +
                                   ((b'\0\0\x08'+b'\0'*9) if pixel and index == 0 else b'\0'*12))]:
                    name = f'frame-{index}.{ext}'
                    files[name] = self.file(d / f'repeat-{repeat}' / name, data)
            repeats.append(files)
        build = dict(sources={'experiment.json': experiments.sha(root / 'experiment.json')},
                     config=config, command=[str(self.root / 'compiler'), '-O2'],
                     compiler_version='synthetic compiler 1', vm_trace=kind=='trace',
                     timing_audio_hash=kind=='trace', app_flags=['-O2'], substitutions=['synthetic only'])
        self.save(d / 'build.json', build)
        self.save(d / 'capture.json', dict(game='deltarune', variant='bram', seed=7, rows=rows,
                    repeats=repeats, build=build, elf_sha256=experiments.sha(d / 'program.elf')))
        prepared = dict(image_sha256=experiments.sha(d / 'program.bin'), stack_sha256=experiments.sha(d / 'stack.bin'),
                        bram_sha256=experiments.sha(d / 'firmware.mif'), capture_sha256=experiments.sha(d / 'capture.json'),
                        elf_sha256=experiments.sha(d / 'program.elf'), framebuffer_sha256=None)
        self.save(d / 'prepared.json', prepared)
        log += ''.join(f'FRAMECOST {r[0]} 0 800 0\n' for r in rows)
        log = '=== UART BEGIN ===\n' + log + '=== UART END ===\n'
        log += ('WCONF: mism=0 spurious=0 exp_fifo=0 aw_fifo=0 run_left=0\n'
                'R mismatches=0  scanout mismatches=0  rlast slips=0  orphan beats=0  DRAM strikes=0\nSDRAM errors=0\n')
        self.file(d / 'quiet.log', log.encode())
        self.save(d / 'quiet-results.json', dict(config=config, game='deltarune', variant='bram', traffic='quiet',
                    build_kind=kind, compiler_version='synthetic compiler 1', prepared=prepared, rtl=rtl,
                    log_sha256=experiments.sha(d / 'quiet.log'), oracle_excluded_fields=[3] if kind=='timing' else [],
                    rows=[dict(oracle=r, cycles=100000, simulated_ms=1) for r in rows],
                    frame_costs=[dict(frame=r[0], clock_reads=0, audio_pairs_consumed=800, audio_underrun_pairs=0) for r in rows]))
        self.file(d / 'negative.log', b'FRAMEHARNESS FAIL frame 3323\n')
        self.save(d / 'negative-results.json', dict(game='deltarune', variant='bram', rejected=True,
                    prepared=prepared, rtl=rtl, log_sha256=experiments.sha(d / 'negative.log')))
        return root

    def baseline(self, cases, name='verified'):
        self.assertIsNotNone(regression, 'The routine regression CLI is not implemented')
        return regression.baseline(argparse.Namespace(name=name, cases=cases, traffic='quiet'))

    def check(self, path, candidates):
        return regression.check(argparse.Namespace(baseline=path, candidate_cases=candidates,
                    repo=None, revision=None, jobs=1))

    def test_platform_build_honors_bounded_jobs(self):
        version = experiments.sha(self.root / 'bench/rtl.py')[:16]
        platform = self.root / 'experiments/platform' / version
        platform.mkdir(parents=True)
        # Substitute only external Docker execution, keeping platform's build path real.
        script = ('import json,pathlib,sys; p=pathlib.Path("build/fullframe/rtl/rtl.json"); '
                  'p.parent.mkdir(parents=True); p.write_text(json.dumps({"jobs":int(sys.argv[-1])}))')
        with patch.object(experiments, 'docker', lambda root, *cmd:
                          ['python3', '-c', script, *cmd]):
            with contextlib.chdir(platform):
                result = experiments.platform(jobs=1)
        self.assertEqual(result, platform)
        self.assertEqual(json.loads((platform / 'build/fullframe/rtl/rtl.json').read_text()), {'jobs': 1})

    def test_baseline_is_write_once_and_check_does_not_modify_it(self):
        base = self.case('baseline')
        path = self.baseline([base])
        before = path.read_bytes()
        self.assertTrue(self.check(path, [self.case('candidate', revision='b'*40)]))
        self.assertEqual(path.read_bytes(), before)
        with self.assertRaisesRegex(ValueError, 'exists'):
            self.baseline([base])
        index = json.loads(path.read_text())
        self.assertEqual(index['revision'], 'a'*40)
        self.assertEqual(len(index['cases']), 1)

    def test_pixel_mismatch_fails_and_retains_report_images(self):
        path = self.baseline([self.case('baseline')])
        self.assertFalse(self.check(path, [self.case('candidate', pixel=True, revision='b'*40)]))
        reports = list((self.root / 'build/regressions/checks').glob('*/comparison-*.json'))
        self.assertEqual(len(reports), 1)
        report = json.loads(reports[0].read_text())
        self.assertEqual(report['first_difference']['field'], 'pixels')
        for image in report['first_difference']['images'].values():
            self.assertTrue(Path(image).exists())

    def test_missing_negative_or_incomplete_rows_cannot_be_registered(self):
        root = self.case('incomplete')
        d = root / 'build/fullframe/deltarune/bram'
        (d / 'negative-results.json').unlink()
        with self.assertRaisesRegex(ValueError, 'negative'):
            self.baseline([root])
        self.assertFalse((self.root / 'build/regressions/baselines/verified.json').exists())

    def test_mutated_baseline_capture_is_rejected(self):
        root = self.case('baseline')
        path = self.baseline([root])
        (root / 'build/fullframe/deltarune/bram/repeat-1/frame-0.rgb555').write_bytes(b'\x01\0')
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.check(path, [self.case('candidate')])

    def test_current_adapter_or_compiler_changes_cannot_reuse_baseline(self):
        path = self.baseline([self.case('baseline')])
        candidate = self.case('candidate')
        (self.root / 'compiler').write_text('#!/bin/sh\necho "synthetic compiler 2"\n')
        with self.assertRaisesRegex(ValueError, 'compiler|toolchain'):
            self.check(path, [candidate])

    def test_incompatible_roster_and_duplicate_or_mixed_revision_are_rejected(self):
        base = self.case('baseline')
        path = self.baseline([base])
        with self.assertRaisesRegex(ValueError, 'configuration|roster'):
            self.check(path, [self.case('candidate', native='disabled')])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.baseline([base, self.case('duplicate')], name='duplicates')
        with self.assertRaisesRegex(ValueError, 'revision'):
            self.baseline([base, self.case('different', kind='timing', revision='b'*40)], name='mixed')

    def test_result_rows_cannot_be_replaced_with_empty_success(self):
        root = self.case('empty')
        p = root / 'build/fullframe/deltarune/bram/quiet-results.json'
        result = json.loads(p.read_text())
        result['rows'] = []
        self.save(p, result)
        with self.assertRaisesRegex(ValueError, 'Incomplete|incomplete'):
            self.baseline([root])

    def test_repeats_must_agree_even_when_their_recorded_hashes_are_updated(self):
        root = self.case('unrepeatable')
        d = root / 'build/fullframe/deltarune/bram'
        p = d / 'repeat-1/frame-0.rgb555'
        p.write_bytes(b'\x01\0')
        capture = json.loads((d / 'capture.json').read_text())
        capture['repeats'][1][p.name] = experiments.sha(p)
        self.save(d / 'capture.json', capture)
        with self.assertRaisesRegex(ValueError, 'repeat|reproducible'):
            self.baseline([root])


    def test_changed_adapter_and_result_log_are_rejected(self):
        base = self.case('baseline')
        path = self.baseline([base])
        candidate = self.case('candidate')
        (self.root / 'bench/runtime.c').write_text('changed adapter')
        with self.assertRaisesRegex(ValueError, 'adapter'):
            self.check(path, [candidate])

    def test_incomplete_replay_log_oracle_and_exclusions_fail(self):
        root = self.case('wrong-log')
        d = root / 'build/fullframe/deltarune/bram'
        text = (d / 'quiet.log').read_text().replace('FRAMERESULT 3324', 'IGNORED 3324')
        (d / 'quiet.log').write_text(text)
        result = json.loads((d / 'quiet-results.json').read_text())
        result['log_sha256'] = experiments.sha(d / 'quiet.log')
        self.save(d / 'quiet-results.json', result)
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            self.baseline([root])
        root = self.case('excluded')
        p = root / 'build/fullframe/deltarune/bram/quiet-results.json'
        result = json.loads(p.read_text())
        result['oracle_excluded_fields'] = [1, 2, 3]
        self.save(p, result)
        with self.assertRaisesRegex(ValueError, 'exclusions'):
            self.baseline([root])

    def test_metadata_rewrite_cannot_bless_changed_baseline(self):
        base = self.case('baseline')
        path = self.baseline([base])
        p = base / 'build/fullframe/deltarune/bram/negative-results.json'
        value = json.loads(p.read_text())
        value['rejected'] = False
        self.save(p, value)
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.check(path, [self.case('candidate')])

    def test_missing_repeat_files_and_realtime_are_rejected(self):
        root = self.case('missing-repeat')
        p = root / 'build/fullframe/deltarune/bram/capture.json'
        value = json.loads(p.read_text())
        del value['repeats'][1]['frame-0.rgb555']
        self.save(p, value)
        with self.assertRaisesRegex(ValueError, 'repeat'):
            self.baseline([root])
        root = self.case('realtime', audio='realtime')
        with self.assertRaisesRegex(ValueError, 'fixed audio'):
            self.baseline([root])

    def test_same_baseline_cannot_be_its_own_candidate(self):
        base = self.case('baseline')
        path = self.baseline([base])
        with self.assertRaisesRegex(ValueError, 'independent'):
            self.check(path, [base])

    def test_current_shared_capture_tool_must_match_copied_case(self):
        (self.root / 'fullframe').mkdir()
        (self.root / 'fullframe/run.py').write_text('current shared launcher')
        root = self.case('old-launcher')
        (root / 'fullframe/run.py').write_text('old shared launcher')
        with self.assertRaisesRegex(ValueError, 'tooling|launcher'):
            self.baseline([root])

    def test_cost_counters_must_match_raw_replay_log(self):
        root = self.case('wrong-costs')
        p = root / 'build/fullframe/deltarune/bram/quiet-results.json'
        result = json.loads(p.read_text())
        result['frame_costs'][0]['clock_reads'] = 12345
        self.save(p, result)
        with self.assertRaisesRegex(ValueError, 'cost'):
            self.baseline([root])


    def test_container_compiler_must_match_recorded_version(self):
        fake = self.root / 'fake-docker'
        fake.write_text('#!/bin/sh\nif [ "$1" = image ]; then echo sha256:fixture; '
                        'else echo "unexpected compiler version"; fi\n')
        fake.chmod(0o755)
        with patch.object(experiments, 'docker', lambda root, *cmd: [str(fake), 'run', *cmd]):
            with self.assertRaisesRegex(ValueError, 'compiler|toolchain'):
                regression.compiler_identity({'compiler': 'container'}, 'recorded compiler')

    def test_cli_mismatch_exit_and_failure_report_are_retained(self):
        path = self.baseline([self.case('baseline')])
        candidate = self.case('candidate', pixel=True)
        script = ('import pathlib,sys;sys.path.insert(0,sys.argv[1]);import regression,experiments;'
                  'regression.ROOT=experiments.ROOT=pathlib.Path(sys.argv[2]);'
                  'experiments.PRIVATE=experiments.ROOT/"experiments";'
                  'sys.argv=["regression.py","check","--baseline",sys.argv[3],'
                  '"--candidate-cases",sys.argv[4]];regression.main()')
        result = subprocess.run(['python3', '-c', script, str(Path(__file__).parent), str(self.root),
                                 str(path), str(candidate)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        reports = list((self.root / 'build/regressions/checks').glob('*/check.json'))
        self.assertEqual(len(reports), 1)
        self.assertFalse(json.loads(reports[0].read_text())['passed'])
        self.assertFalse(json.loads(reports[0].read_text())['device_validated'])


    def refresh_evidence(self, root):
        """Update fixture hashes without changing its independent raw-log oracles."""
        d = root / 'build/fullframe/deltarune/bram'
        capture = json.loads((d / 'capture.json').read_text())
        for repeat, files in enumerate(capture['repeats']):
            for name in files:
                files[name] = experiments.sha(d / f'repeat-{repeat}' / name)
        self.save(d / 'capture.json', capture)
        prepared = json.loads((d / 'prepared.json').read_text())
        prepared['capture_sha256'] = experiments.sha(d / 'capture.json')
        self.save(d / 'prepared.json', prepared)
        rtl = json.loads((root / 'build/fullframe/rtl/rtl.json').read_text())
        for name in ['quiet', 'negative']:
            path = d / (name + '-results.json')
            result = json.loads(path.read_text())
            result['prepared'] = prepared
            result['rtl'] = rtl
            self.save(path, result)

    def test_candidate_only_simulator_wrapper_or_leaf_drift_fails(self):
        path = self.baseline([self.case('baseline')])
        for index, (name, field) in enumerate([
                ('build/fullframe/rtl/obj/Vtb_system', 'simulator_sha256'),
                ('build/fullframe/rtl/main.cpp', 'source_sha256'),
                ('build/rtl/rtl.json', 'leaf_rtl_sha256')]):
            with self.subTest(field=field):
                candidate = self.case('drift-' + str(index))
                (candidate / name).write_bytes(b'coherently changed platform')
                rtl_path = candidate / 'build/fullframe/rtl/rtl.json'
                rtl = json.loads(rtl_path.read_text())
                rtl[field] = experiments.sha(candidate / name)
                self.save(rtl_path, rtl)
                self.refresh_evidence(candidate)
                with self.assertRaisesRegex(ValueError, 'platform'):
                    self.check(path, [candidate])

    def test_empty_or_truncated_pixel_files_cannot_register(self):
        for index, raw in enumerate([b'', b'\0', b'\0'*6]):
            with self.subTest(length=len(raw)):
                root = self.case('bad-pixels-' + str(index))
                d = root / 'build/fullframe/deltarune/bram'
                for repeat in range(2):
                    (d / f'repeat-{repeat}/frame-0.rgb555').write_bytes(raw)
                self.refresh_evidence(root)
                with self.assertRaisesRegex(ValueError, 'pixel|RGB555'):
                    self.baseline([root], name='invalid-' + str(index))

    def test_raw_pixels_must_match_logged_fnv_oracle(self):
        root = self.case('wrong-oracle')
        d = root / 'build/fullframe/deltarune/bram'
        for repeat in range(2):
            (d / f'repeat-{repeat}/frame-0.rgb555').write_bytes(b'\x01\0'+b'\0'*6)
            (d / f'repeat-{repeat}/frame-0.ppm').write_bytes(b'P6\n2 2\n255\n'+b'\0\0\x08'+b'\0'*9)
        self.refresh_evidence(root)
        with self.assertRaisesRegex(ValueError, 'pixel.*oracle|RGB555.*oracle'):
            self.baseline([root])

    def test_ppm_geometry_and_pixels_must_correspond_to_raw_capture(self):
        for index, ppm in enumerate([
                b'P6\n0 2\n255\n', b'P6\n641 2\n255\n',
                b'P6\n2 2\n255\n' + b'\0'*9,
                b'P6\n2 2\n255\n' + b'\x08' + b'\0'*11,
                b'P6\n2 2\n255\n' + b'\0'*13]):
            with self.subTest(index=index):
                root = self.case('bad-ppm-' + str(index))
                d = root / 'build/fullframe/deltarune/bram'
                for repeat in range(2):
                    (d / f'repeat-{repeat}/frame-0.ppm').write_bytes(ppm)
                self.refresh_evidence(root)
                with self.assertRaisesRegex(ValueError, 'PPM|pixel'):
                    self.baseline([root], name='ppm-' + str(index))


    def test_equal_pixel_bytes_with_different_frame_geometry_fail_with_images(self):
        path = self.baseline([self.case('baseline')])
        candidate = self.case('different-shape')
        d = candidate / 'build/fullframe/deltarune/bram'
        for repeat in range(2):
            (d / f'repeat-{repeat}/frame-0.ppm').write_bytes(b'P6\n4 1\n255\n' + b'\0'*12)
        self.refresh_evidence(candidate)
        self.assertFalse(self.check(path, [candidate]))
        reports = list((self.root / 'build/regressions/checks').glob('*/comparison-*.json'))
        self.assertEqual(len(reports), 1)
        first = json.loads(reports[0].read_text())['first_difference']
        self.assertEqual((first['frame'], first['field']), (3323, 'geometry'))
        self.assertEqual(first['baseline'], [2, 2])
        self.assertEqual(first['candidate'], [4, 1])
        self.assertEqual(Path(first['images']['baseline']).read_bytes(), b'P6\n2 2\n255\n' + b'\0'*12)
        self.assertEqual(Path(first['images']['candidate']).read_bytes(), b'P6\n4 1\n255\n' + b'\0'*12)


    def replay_log(self, root, text):
        d = root / 'build/fullframe/deltarune/bram'
        (d / 'quiet.log').write_text(text)
        p = d / 'quiet-results.json'
        result = json.loads(p.read_text())
        result['log_sha256'] = experiments.sha(d / 'quiet.log')
        self.save(p, result)

    def test_live_uart_duplicate_uses_only_bounded_summary(self):
        root = self.case('live-uart')
        p = root / 'build/fullframe/deltarune/bram/quiet.log'
        text = p.read_text()
        uart = text.split('=== UART BEGIN ===\n')[1].split('=== UART END ===')[0]
        self.replay_log(root, uart + 'simulation complete\n' + text)
        path = self.baseline([root])
        self.assertTrue(path.exists())

    def test_bounded_uart_requires_complete_unique_summary(self):
        for index, change in enumerate([
                lambda text: text.replace('=== UART BEGIN ===\n', ''),
                lambda text: text.replace('=== UART END ===\n', ''),
                lambda text: text.replace('=== UART END ===', '=== UART BEGIN ===\n=== UART END ==='),
                lambda text: text + text,
                lambda text: text.replace('FRAMERESULT 3324', 'MISSING 3324'),
                lambda text: text.replace('FRAMECOST 3324', 'MISSINGCOST 3324'),
                lambda text: text.replace('=== UART END ===',
                        'FRAMERESULT 3323 100000 1 9be17165 3 1 6 7 8\n=== UART END ==='),
                lambda text: text.replace('=== UART END ===',
                        'FRAMECOST 3323 0 800 0\n=== UART END ==='),
                lambda text: 'FRAMEHARNESS FAIL outside UART\n' + text]):
            with self.subTest(index=index):
                root = self.case('bad-uart-' + str(index))
                p = root / 'build/fullframe/deltarune/bram/quiet.log'
                self.replay_log(root, change(p.read_text()))
                with self.assertRaisesRegex(ValueError, 'UART|Incomplete|failed|cost'):
                    self.baseline([root], name='bad-uart-' + str(index))


if __name__ == '__main__':
    unittest.main()
