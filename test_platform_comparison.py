"""Controlled platform experiments use synthetic identities, never device evidence."""
import copy
import unittest

from benchmarks.comparison import compare_platform_runs
from benchmarks.profiles import bind_profile


def profile():
    return dict(schema_version=1, id='fixture-os25-100', variant='os25',
                clock_hz=100000000,
                cpu=dict(isa='rv32imafc', issue_width=2, icache_bytes=32768,
                         dcache_bytes=131072, config_sha256='1'*64),
                sources=dict(os_revision='os-source', sdk_revision='sdk-source'),
                artifacts=dict(os_sha256='2'*64, bitstream_sha256='3'*64,
                               loader_sha256='4'*64), features=[])


def run(definition=None):
    definition = definition or profile()
    metadata = dict(schema_version=1, project='butterscotch', game='undertale', repeat=1,
                    build=dict(id='fixture-app', source_revision='app-source',
                               compiler='gcc-fixture', flags=['-O2'], elf_sha256='a'*64),
                    platform=dict(variant=definition['variant'], clock_hz=definition['clock_hz'],
                                  device_id='fixture-pocket'),
                    case=dict(id='battle', suite='focused', route_version='v1', mode='speed',
                              seed=7, warmup_frames=1, target_hz=30, expected_rows=['battle']),
                    conditions=dict(initial_state='fresh', audio='on', pacing='uncapped',
                                    asset_manifest_sha256='b'*64))
    return dict(run_id='fixture-run', backend='device', adapter='device-summary',
                metadata=metadata, platform_profile=bind_profile(definition, metadata),
                rows=[dict(id='battle', samples=20, metrics=dict(work_mean_us=10000))],
                checks=dict(complete=True, correctness='not_checked', identity='declared'),
                limits=['Manually transcribed; not independently checked.'])


def candidate(base=None, *, clock=False, variant=False, runtime=False):
    base = base or run()
    definition = copy.deepcopy(base['platform_profile']['definition'])
    definition['id'] = 'fixture-candidate'
    if clock:
        definition['clock_hz'] = 90000000
    if variant:
        definition['variant'] = 'os20'
        definition['cpu']['dcache_bytes'] = 65536
        definition['cpu']['config_sha256'] = '5'*64
    if clock or variant:
        definition['artifacts']['bitstream_sha256'] = '6'*64
    if runtime:
        definition['sources']['os_revision'] = 'os-candidate'
        definition['artifacts']['os_sha256'] = '7'*64
    result = run(definition)
    result['run_id'] = 'candidate-run'
    result['rows'][0]['metrics']['work_mean_us'] = 8000
    return result


class PlatformComparisonTests(unittest.TestCase):
    def test_clock_deltas_use_original_units_and_disclose_artifacts(self):
        baseline, changed = run(), candidate(clock=True)
        result = compare_platform_runs(baseline, changed, ['clock'])
        self.assertEqual(result['mode'], 'platform')
        self.assertEqual(result['assessment'], 'descriptive_platform_experiment')
        self.assertEqual(result['qualification'], 'profile_bound')
        self.assertEqual(result['varied_factors'], ['clock'])
        self.assertEqual(result['baseline'], 'fixture-run')
        self.assertEqual(result['candidate'], 'candidate-run')
        self.assertEqual(result['baseline_profile_sha256'], baseline['platform_profile']['sha256'])
        self.assertEqual(result['candidate_profile_sha256'], changed['platform_profile']['sha256'])
        self.assertEqual(result['rows'][0]['metrics']['work_mean_us'],
                         dict(baseline=10000, candidate=8000, delta=-2000, percent=-20))
        diffs = {item['path']: item for item in result['differences']}
        self.assertEqual(diffs['platform_profile.clock_hz']['baseline'], 100000000)
        self.assertEqual(diffs['platform_profile.artifacts.bitstream_sha256']['candidate'], '6'*64)
        self.assertIn('transcribed', ' '.join(result['limits']))
        self.assertIn('flashed', ' '.join(result['limits']))

    def test_variant_runtime_and_combined_factors_are_explicit(self):
        for factors, flags in [(['variant'], dict(variant=True)),
                               (['runtime'], dict(runtime=True)),
                               (['clock', 'variant', 'runtime'],
                                dict(clock=True, variant=True, runtime=True))]:
            with self.subTest(factors=factors):
                result = compare_platform_runs(run(), candidate(**flags), factors)
                self.assertEqual(result['varied_factors'], factors)
                if len(factors) > 1:
                    self.assertIn('isolat', ' '.join(result['limits']))

    def test_four_cells_keep_clock_independent_of_variant(self):
        for variant, clock in [('os20', 90000000), ('os20', 100000000),
                               ('os25', 90000000), ('os25', 100000000)]:
            definition = profile()
            definition.update(variant=variant, clock_hz=clock)
            baseline = run(definition)
            changed = candidate(baseline, runtime=True)
            with self.subTest(variant=variant, clock=clock):
                self.assertEqual(compare_platform_runs(baseline, changed, ['runtime'])['backend'], 'device')

    def test_only_declared_actual_factors_are_accepted(self):
        for factors in [[], ['variant'], ['clock', 'runtime'], ['unknown'], 'clock', ['clock', 'clock']]:
            with self.subTest(factors=factors), self.assertRaises(ValueError):
                compare_platform_runs(run(), candidate(clock=True), factors)
        for factors in [[], ['clock'], ['runtime']]:
            with self.subTest(noop=factors), self.assertRaises(ValueError):
                compare_platform_runs(run(), run(), factors)

    def test_profile_identity_or_description_alone_does_not_create_a_factor(self):
        changed = candidate()
        changed['platform_profile']['definition']['description'] = 'another label'
        changed['platform_profile'] = bind_profile(changed['platform_profile']['definition'], changed['metadata'])
        with self.assertRaises(ValueError):
            compare_platform_runs(run(), changed, ['runtime'])

    def test_implementation_and_artifact_only_changes_are_runtime(self):
        for section, field in [('cpu', 'config_sha256'), ('artifacts', 'loader_sha256')]:
            changed = candidate()
            changed['platform_profile']['definition'][section][field] = '8'*64
            changed['platform_profile'] = bind_profile(changed['platform_profile']['definition'], changed['metadata'])
            with self.subTest(field=field):
                self.assertEqual(compare_platform_runs(run(), changed, ['runtime'])['varied_factors'], ['runtime'])

    def test_feature_or_cpu_semantic_changes_are_variant(self):
        for section, field, value in [('cpu', 'issue_width', 1), ('cpu', 'isa', 'rv32imc'),
                                       (None, 'features', ['fixture-feature'])]:
            changed = candidate()
            definition = changed['platform_profile']['definition']
            (definition if section is None else definition[section])[field] = value
            changed['platform_profile'] = bind_profile(definition, changed['metadata'])
            with self.subTest(field=field):
                self.assertEqual(compare_platform_runs(run(), changed, ['variant'])['varied_factors'], ['variant'])

    def test_runtime_source_cannot_hide_in_pure_clock_or_variant(self):
        for flags in [dict(clock=True), dict(variant=True)]:
            with self.subTest(flags=flags), self.assertRaises(ValueError):
                compare_platform_runs(run(), candidate(runtime=True, **flags), list(flags))

    def test_both_runs_require_device_bound_complete_successful_evidence(self):
        mutations = [lambda r: r.update(backend='host'), lambda r: r.update(backend='simulation'),
                     lambda r: r.pop('platform_profile'),
                     lambda r: r['platform_profile'].update(sha256='f'*64),
                     lambda r: r['checks'].update(complete=False),
                     lambda r: r['checks'].update(correctness='reported_fail'),
                     lambda r: r.update(adapter='other-adapter')]
        for side in (0, 1):
            for mutate in mutations:
                pair = [run(), candidate(clock=True)]
                mutate(pair[side])
                with self.subTest(side=side, mutate=mutate), self.assertRaises(ValueError):
                    compare_platform_runs(*pair, ['clock'])

    def test_fixed_application_toolchain_assets_device_and_settings(self):
        mutations = [lambda r: r['metadata']['build'].update(source_revision='other-source'),
                     lambda r: r['metadata']['build'].update(elf_sha256=None),
                     lambda r: r['metadata']['build'].update(elf_sha256='e'*64),
                     lambda r: r['metadata']['build'].update(compiler=None),
                     lambda r: r['metadata']['build'].update(compiler='unknown'),
                     lambda r: r['metadata']['build'].update(compiler='other-gcc'),
                     lambda r: r['metadata']['build'].update(flags=['-O3']),
                     lambda r: r['metadata']['build'].update(extra_setting='changed'),
                     lambda r: r['metadata']['platform'].update(device_id=None),
                     lambda r: r['metadata']['platform'].update(device_id='other-device'),
                     lambda r: r['metadata']['platform'].update(extra_setting='changed'),
                     lambda r: r['metadata']['conditions'].pop('asset_manifest_sha256'),
                     lambda r: r['metadata']['conditions'].update(asset_manifest_sha256='unknown'),
                     lambda r: r['metadata']['conditions'].update(asset_manifest_sha256='c'*64),
                     lambda r: r['metadata']['conditions'].update(audio='off'),
                     lambda r: r['metadata']['case'].update(seed=8),
                     lambda r: r.update(comparison_config={'mode': 'different'}),
                     lambda r: r['rows'][0].update(samples=21),
                     lambda r: r['rows'][0]['metrics'].update(frame_max_us=123)]
        for mutate in mutations:
            changed = candidate(clock=True)
            mutate(changed)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                compare_platform_runs(run(), changed, ['clock'])

    def test_build_and_repeat_deployment_labels_do_not_change_controls(self):
        changed = candidate(clock=True)
        changed['metadata']['build']['id'] = 'other-package'
        changed['metadata']['repeat'] = 2
        changed['metadata']['deployment'] = {'core_id': 'candidate-core'}
        self.assertEqual(compare_platform_runs(run(), changed, ['clock'])['varied_factors'], ['clock'])

    def test_profile_represented_build_identities_can_change_but_cannot_be_omitted(self):
        baseline, changed = run(), candidate(clock=True, runtime=True)
        for value in (baseline, changed):
            definition = value['platform_profile']['definition']
            value['metadata']['build'].update(runtime_sha256=definition['artifacts']['os_sha256'],
                sdk_revision=definition['sources']['sdk_revision'],
                bitstream_sha256=definition['artifacts']['bitstream_sha256'])
        self.assertEqual(compare_platform_runs(baseline, changed, ['clock', 'runtime'])['varied_factors'],
                         ['clock', 'runtime'])
        changed['metadata']['build'].pop('runtime_sha256')
        with self.assertRaises(ValueError):
            compare_platform_runs(baseline, changed, ['clock', 'runtime'])

    def test_clock_plus_config_implementation_change_requires_runtime(self):
        changed = candidate(clock=True)
        changed['platform_profile']['definition']['cpu']['config_sha256'] = '9'*64
        changed['platform_profile'] = bind_profile(changed['platform_profile']['definition'], changed['metadata'])
        with self.assertRaises(ValueError):
            compare_platform_runs(run(), changed, ['clock'])
        self.assertEqual(compare_platform_runs(run(), changed, ['clock', 'runtime'])['varied_factors'],
                         ['clock', 'runtime'])

    def test_unrelated_deployment_and_top_level_settings_remain_fixed(self):
        for section in (None, 'deployment'):
            changed = candidate(clock=True)
            (changed['metadata'] if section is None else changed['metadata'].setdefault(section, {}))['setting'] = 'different'
            with self.subTest(section=section), self.assertRaises(ValueError):
                compare_platform_runs(run(), changed, ['clock'])

    def test_runtime_allows_reported_and_declared_firmware_change(self):
        baseline, changed = run(), candidate(runtime=True)
        baseline['metadata']['platform']['firmware'] = '0.25.0'
        changed['metadata']['platform']['firmware'] = '0.25.1'
        baseline['reported_platform'] = dict(firmware='0.25.0', core_number=1, clock_hz=100000000)
        changed['reported_platform'] = dict(firmware='0.25.1', core_number=1, clock_hz=100000000)
        result = compare_platform_runs(baseline, changed, ['runtime'])
        self.assertIn('reported_platform.firmware', [item['path'] for item in result['differences']])

    def test_reported_core_number_is_compared_without_mapping_to_os_label(self):
        baseline, changed = run(), candidate(variant=True)
        baseline['reported_platform'] = dict(firmware='0.25.0', core_number=99, clock_hz=100000000)
        changed['reported_platform'] = dict(firmware='0.25.0', core_number=1, clock_hz=100000000)
        self.assertEqual(compare_platform_runs(baseline, changed, ['variant'])['varied_factors'], ['variant'])
        for mutation in [dict(firmware='0.20.0'), dict(clock_hz=90000000), dict(extra='changed')]:
            invalid = copy.deepcopy(changed)
            invalid['reported_platform'].update(mutation)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                compare_platform_runs(baseline, invalid, ['variant'])

    def test_reported_platform_presence_and_extra_settings_are_controls(self):
        baseline, changed = run(), candidate(clock=True)
        baseline['reported_platform'] = dict(firmware='0.25.0', core_number=1, clock_hz=100000000)
        with self.assertRaises(ValueError):
            compare_platform_runs(baseline, changed, ['clock'])
        changed['reported_platform'] = dict(firmware='0.25.0', core_number=1, clock_hz=90000000)
        self.assertEqual(compare_platform_runs(baseline, changed, ['clock'])['varied_factors'], ['clock'])

    def test_runtime_cannot_hide_changes_in_extra_nested_reported_settings(self):
        baseline, changed = run(), candidate(runtime=True)
        baseline['reported_platform'] = dict(clock_hz=100000000, extra={'firmware': 'setting-a'})
        changed['reported_platform'] = dict(clock_hz=100000000, extra={'firmware': 'setting-b'})
        with self.assertRaises(ValueError):
            compare_platform_runs(baseline, changed, ['runtime'])

    def test_unknown_flags_and_missing_adapters_are_not_known_controls(self):
        for mutation in (lambda r: r['metadata']['build'].update(flags=['unknown']),
                         lambda r: r.pop('adapter')):
            baseline, changed = run(), candidate(clock=True)
            mutation(baseline)
            mutation(changed)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                compare_platform_runs(baseline, changed, ['clock'])


if __name__ == '__main__':
    unittest.main()
