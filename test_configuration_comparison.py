"""Whole-configuration deltas remain distinct from controlled platform effects."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest

from benchmarks import comparison
from benchmarks.__main__ import main
from benchmarks.profiles import bind_profile
from benchmarks.store import collect
from test_platform_comparison import run, candidate


REASON = 'Candidate SDK requires a rebuilt ELF and compiler flags.'


def configurations():
    baseline, changed = run(), candidate(clock=True, variant=True, runtime=True)
    changed['metadata']['project'] = baseline['metadata']['project'] = 'nova-pocket'
    changed['metadata']['build'].update(source_revision='candidate-app-source',
                                      elf_sha256='c' * 64, compiler='candidate-gcc', flags=['-O3'])
    changed['platform_profile']['definition']['sources']['sdk_revision'] = 'candidate-sdk-source'
    changed['platform_profile'] = bind_profile(changed['platform_profile']['definition'], changed['metadata'])
    return baseline, changed


class ConfigurationComparisonTests(unittest.TestCase):
    def compare(self, baseline, changed, reason=REASON):
        return comparison.compare_configuration_runs(baseline, changed, reason=reason)

    def test_different_elf_and_toolchain_are_disclosed_as_combined_configuration(self):
        baseline, changed = configurations()
        original = copy.deepcopy((baseline, changed))
        result = self.compare(baseline, changed)
        self.assertEqual(result['mode'], 'configuration')
        self.assertEqual(result['assessment'], 'descriptive_configuration_experiment')
        self.assertEqual(result['attribution'], 'whole_configuration_only')
        self.assertEqual(result['comparison_reason'], REASON)
        self.assertEqual(set(result['changed_components']), {'application', 'toolchain', 'clock', 'variant', 'runtime'})
        self.assertEqual(result['rows'][0]['metrics']['work_mean_us'],
                         dict(baseline=10000, candidate=8000, delta=-2000, percent=-20))
        differences = {entry['path']: entry for entry in result['differences']}
        self.assertEqual(differences['metadata.build.elf_sha256']['baseline'], 'a' * 64)
        self.assertEqual(differences['metadata.build.elf_sha256']['candidate'], 'c' * 64)
        for field in ('source_revision', 'compiler', 'flags'):
            self.assertIn(f'metadata.build.{field}', differences)
        self.assertIn('platform_profile.artifacts.bitstream_sha256', differences)
        self.assertIn('platform_profile.sources.os_revision', differences)
        self.assertEqual(differences['platform_profile.sources.sdk_revision']['candidate'], 'candidate-sdk-source')
        self.assertEqual(result['configurations']['baseline']['metadata'], baseline['metadata'])
        self.assertEqual(result['configurations']['candidate']['platform_profile'], changed['platform_profile'])
        self.assertIn('transcribed', ' '.join(result['limits']))
        self.assertIn('isolat', ' '.join(result['limits']))
        self.assertEqual((baseline, changed), original)

    def test_existing_platform_comparison_still_rejects_different_elf(self):
        baseline, changed = configurations()
        with self.assertRaises(ValueError):
            comparison.compare_platform_runs(baseline, changed, ['clock', 'variant', 'runtime'])

    def test_reason_is_required_and_labels_alone_do_not_create_an_experiment(self):
        baseline, changed = configurations()
        for reason in (None, '', '  ', True, ['because']):
            with self.subTest(reason=reason), self.assertRaises(ValueError):
                self.compare(baseline, changed, reason)
        labels = copy.deepcopy(baseline)
        labels['metadata']['repeat'] = 2
        labels['metadata']['build']['id'] = 'another-label'
        labels['platform_profile']['definition']['description'] = 'another-label'
        labels['platform_profile'] = bind_profile(labels['platform_profile']['definition'], labels['metadata'])
        with self.assertRaises(ValueError):
            self.compare(baseline, labels)

    def test_same_profile_can_compare_distinct_application_builds(self):
        baseline = run()
        changed = copy.deepcopy(baseline)
        changed['metadata']['build']['elf_sha256'] = 'c' * 64
        self.assertEqual(self.compare(baseline, changed)['changed_components'], ['application'])

    def test_unknown_source_placeholders_cannot_masquerade_as_application_changes(self):
        for source in ('UNKNOWN', ' unknown ', 'Unversioned'):
            baseline = run()
            changed = copy.deepcopy(baseline)
            changed['metadata']['build']['source_revision'] = source
            with self.subTest(source=source), self.assertRaises(ValueError):
                self.compare(baseline, changed)

    def test_workload_assets_device_sampling_and_extra_settings_stay_fixed(self):
        mutations = [lambda r: r['metadata'].update(project='other-project'),
                     lambda r: r['metadata'].update(game='other-game'),
                     lambda r: r['metadata']['platform'].update(device_id='other-device'),
                     lambda r: r['metadata']['platform'].update(framebuffer='other-layout'),
                     lambda r: r['metadata']['case'].update(seed=8),
                     lambda r: r['metadata']['case'].update(warmup_frames=2),
                     lambda r: r['metadata']['conditions'].update(audio='off'),
                     lambda r: r['metadata']['conditions'].update(pacing='capped'),
                     lambda r: r['metadata']['conditions'].update(asset_manifest_sha256='d' * 64),
                     lambda r: r['metadata']['build'].update(uncontrolled_setting='changed'),
                     lambda r: r['metadata'].update(uncontrolled_setting='changed'),
                     lambda r: r['metadata'].update(deployment={'save_namespace': 'other'}),
                     lambda r: r['rows'][0].update(samples=19),
                     lambda r: r['rows'][0]['metrics'].update(other_us=3),
                     lambda r: r.update(adapter='another-adapter'),
                     lambda r: r.update(comparison_config={'other': True}),
                     lambda r: r.update(source_config={'other': True})]
        for mutate in mutations:
            baseline, changed = configurations()
            mutate(changed)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                self.compare(baseline, changed)

    def test_both_sides_need_valid_known_complete_device_identity(self):
        mutations = [lambda r: r.update(backend='host'), lambda r: r.update(backend='simulation'),
                     lambda r: r.pop('platform_profile'),
                     lambda r: r['platform_profile'].update(sha256='f' * 64),
                     lambda r: r['metadata']['build'].update(elf_sha256=None),
                     lambda r: r['metadata']['build'].update(compiler='unknown'),
                     lambda r: r['metadata']['build'].update(flags=['unknown']),
                     lambda r: r['metadata']['build'].update(source_revision='unknown'),
                     lambda r: r['metadata']['platform'].update(device_id=None),
                     lambda r: r['metadata']['conditions'].pop('asset_manifest_sha256'),
                     lambda r: r['checks'].update(complete=False),
                     lambda r: r['checks'].update(correctness='reported_fail'),
                     lambda r: r['checks'].update(correctness='unknown'),
                     lambda r: r.update(limits='malformed limits')]
        for side in (0, 1):
            for mutate in mutations:
                pair = list(configurations())
                mutate(pair[side])
                with self.subTest(side=side, mutation=mutate), self.assertRaises(ValueError):
                    self.compare(*pair)

    def test_check_differences_and_optional_identity_presence_are_preserved(self):
        baseline, changed = configurations()
        changed['metadata']['build']['runtime_sha256'] = changed['platform_profile']['definition']['artifacts']['os_sha256']
        changed['checks']['correctness'] = 'reported_pass'
        result = self.compare(baseline, changed)
        differences = {item['path']: item for item in result['differences']}
        self.assertFalse(differences['metadata.build.runtime_sha256']['baseline_present'])
        self.assertTrue(differences['metadata.build.runtime_sha256']['candidate_present'])
        self.assertEqual(differences['checks.correctness']['baseline'], 'not_checked')
        self.assertEqual(result['configurations']['candidate']['checks']['correctness'], 'reported_pass')
        self.assertIn('independent correctness', ' '.join(result['limits']))

    def test_reported_hardware_differences_require_matching_profile_changes(self):
        baseline, changed = configurations()
        for value, firmware, number in [(baseline, 'old-fw', 1), (changed, 'new-fw', 2)]:
            value['reported_platform'] = dict(clock_hz=value['metadata']['platform']['clock_hz'],
                                              firmware=firmware, core_number=number)
        result = self.compare(baseline, changed)
        self.assertIn('reported_platform.firmware', {d['path'] for d in result['differences']})
        changed['reported_platform']['extra'] = {'firmware': 'uncontrolled'}
        with self.assertRaises(ValueError):
            self.compare(baseline, changed)
        baseline, changed = configurations()
        baseline['reported_platform'] = dict(clock_hz=100000000)
        with self.assertRaises(ValueError):
            self.compare(baseline, changed)
        baseline = run()
        changed = copy.deepcopy(baseline)
        changed['metadata']['build']['elf_sha256'] = 'c' * 64
        changed['metadata']['platform']['firmware'] = 'unaccounted-for-fw'
        with self.assertRaises(ValueError):
            self.compare(baseline, changed)


class ConfigurationCLITests(unittest.TestCase):
    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                status = main([str(value) for value in args])
            except SystemExit as exc:
                status = exc.code
        return status, out.getvalue(), err.getvalue()

    def test_configuration_mode_uses_verified_bundles_and_explicit_reason(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shot = root / 'synthetic.png'
            shot.write_bytes(b'\x89PNG\r\n\x1a\nsynthetic-only')
            bundles = []
            for index, value in enumerate(configurations()):
                source, metadata, profile = [root / f'{index}-{name}.json' for name in ('source', 'metadata', 'profile')]
                source.write_text(json.dumps(dict(rows=value['rows'])))
                metadata.write_text(json.dumps(value['metadata']))
                profile.write_text(json.dumps(value['platform_profile']['definition']))
                bundles.append(collect(source, metadata, 'device-summary', output=root/'runs',
                                       attachments=[shot], profile_path=profile))
            status, out, err = self.cli('compare', *bundles, '--mode', 'configuration', '--reason', REASON)
            self.assertEqual(status, 0, err)
            self.assertEqual(json.loads(out)['attribution'], 'whole_configuration_only')
            self.assertEqual(self.cli('compare', *bundles, '--mode', 'configuration')[0], 2)
            self.assertEqual(self.cli('compare', *bundles, '--mode', 'configuration', '--reason', REASON, '--vary', 'clock')[0], 2)
            self.assertEqual(self.cli('compare', *bundles, '--reason', REASON)[0], 2)
            self.assertEqual(self.cli('compare', *bundles, '--mode', 'platform', '--reason', REASON,
                                      '--vary', 'clock', '--vary', 'variant', '--vary', 'runtime')[0], 2)
            self.assertEqual(self.cli('compare', *bundles, '--mode', 'platform',
                                      '--vary', 'clock', '--vary', 'variant', '--vary', 'runtime')[0], 2)
            (bundles[1]/'platform-profile.json').write_text('{}')
            self.assertEqual(self.cli('compare', *bundles, '--mode', 'configuration', '--reason', REASON)[0], 2)


if __name__ == '__main__':
    unittest.main()
