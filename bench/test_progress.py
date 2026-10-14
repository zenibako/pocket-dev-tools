"""Independent guards for later Deltarune replay setup."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

import experiments
from bench import build


class ProgressReplayTests(unittest.TestCase):
    def test_scene_is_recorded_without_changing_opening_windows(self):
        self.assertEqual(experiments.WINDOWS['deltarune']['dodge'], 3323)
        self.assertEqual(experiments.WINDOWS['deltarune']['spades'], 490)
        self.assertEqual(experiments.SCENES['spades']['room'], 43)
        self.assertEqual(experiments.SCENES['castle']['room'], 46)
        self.assertIn('char[1]=0,char[2]=0', experiments.SCENES['spades']['globals'])
        self.assertIn('char[1]=2,char[2]=0', experiments.SCENES['castle']['globals'])

    def test_setup_follows_benchmark_and_precedes_game_loop(self):
        original = 'utBenchStart();\n    int ret = loop(args, UT_GAME_NAME);'
        result = build.scene_main(original, experiments.SCENES['spades'])
        self.assertNotIn('utBenchStart();', result)
        self.assertLess(result.index('utSaveFsSetVolatile(true);'), result.index('utPlatformSetJumps'))
        self.assertLess(result.index('utPlatformSetUncapped(true);'), result.index('int ret = loop'))
        self.assertLess(result.index('utPlatformSetJumps'), result.index('int ret = loop'))
        self.assertIn('{29, -1, "darkzone=1,char[1]=0,char[2]=0,plot=60,interact=0"}', result)
        self.assertIn('{30, 43, NULL}', result)
        self.assertIn('40:Z,55:Z', result)
        self.assertIn('475:Z', result)
        self.assertIn('utPlatformSetInputScript("");', build.scene_main(original, experiments.SCENES['castle']))
        self.assertEqual(build.scene_main(original, None), original)

    def test_renamed_scene_setup_keeps_mode_and_room(self):
        original = 'ofBenchStart();\n    int ret = loop(args, OF_GAME_NAME);'
        result = build.scene_main(original, experiments.SCENES['spades'])
        self.assertNotIn('ofBenchStart();', result)
        self.assertIn('ofSaveFsSetVolatile(true);', result)
        self.assertIn('static const OfJump', result)
        self.assertIn('ofPlatformSetJumps(frame_scene_jumps, 2);', result)
        self.assertIn('loop(args, OF_GAME_NAME)', result)

    def test_renamed_sources_include_game_snapshot_and_codec(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            port = root / 'src/openfpga'
            (port / 'platform').mkdir(parents=True)
            (port / 'platform/of_bench.h').touch()
            (port / 'platform/of_battle_ui.c').touch()
            (root / 'vendor/zstd').mkdir(parents=True)
            (root / 'vendor/zstd/zstd.c').touch()
            with patch.object(build.capture, 'SRC', root / 'src'), patch.object(build.capture, 'PORT', port), patch.object(build.capture, 'VENDOR', root / 'vendor'):
                files = build.sources('deltarune')
            for name in ['of_bench.c', 'of_native.c', 'game_deltarune.c', 'of_state_requests.c', 'of_snapshot_envelope.c', 'of_battle_ui.c']:
                self.assertIn(port / 'platform' / name, files)
            self.assertIn(root / 'vendor/zstd/zstd.c', files)
            self.assertNotIn(port / 'platform/of_pack_read.c', files)
            self.assertNotIn(port / 'platform/ut_bench.c', files)

    def test_bad_or_changed_scene_is_rejected(self):
        with self.assertRaises(ValueError):
            build.scene_main('int ret = loop(args, UT_GAME_NAME);', {'room': -1})
        with self.assertRaises(RuntimeError):
            build.scene_main('different entry point', experiments.SCENES['castle'])

    def test_optional_battle_module_is_included_only_when_present(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            port = root / 'src/openfpga'
            (port / 'platform').mkdir(parents=True)
            with patch.object(build.capture, 'SRC', root / 'src'), patch.object(build.capture, 'PORT', port), patch.object(build.capture, 'VENDOR', root / 'vendor'):
                module = port / 'platform/ut_battle_ui.c'
                self.assertNotIn(module, build.sources())
                module.write_text('')
                self.assertIn(module, build.sources())

    def test_comparison_rejects_different_scene_setup(self):
        config = dict(game='deltarune', window='spades', first_frame=490,
                      mode='speed', framebuffer='uncached', clock_cost=1680,
                      audio='fixed', native='enabled', scene=experiments.SCENES['spades'])
        candidate = dict(config, scene=experiments.SCENES['castle'])
        captures = [(config, Path('.'), {'rows': []}), (candidate, Path('.'), {'rows': []})]
        with patch.object(experiments, 'checked_capture', side_effect=captures):
            with self.assertRaisesRegex(ValueError, 'scene'):
                experiments.compare(SimpleNamespace(baseline=Path('base'), candidate=Path('sharp')))

    def test_report_pairs_only_matching_scene_timing(self):
        config = dict(snapshot_sha256='snapshot', mode='speed', window='spades',
                      game='deltarune', variant='bram', profile='port', framebuffer='uncached',
                      clock_cost=1680, audio='fixed', alignment=True, compiler='gcc',
                      scene=experiments.SCENES['spades'])
        traced = dict(build_kind='trace', revision='revision', native_scripts='enabled',
                      compiler_version='gcc16', config=config)
        timing = dict(traced, build_kind='timing', config=dict(config))
        other_scene = dict(timing, config=dict(config, scene=experiments.SCENES['castle']))
        self.assertIs(experiments.timing_partner(traced, [other_scene, timing]), timing)
        self.assertIsNone(experiments.timing_partner(traced, [other_scene]))


if __name__ == '__main__':
    unittest.main()
