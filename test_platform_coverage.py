"""Coverage counts declarations and observations without promoting them to proof."""
import copy
import unittest

from benchmarks.coverage import coverage_matrix
from test_benchmarks import metadata


def profile(variant='os25', clock=100000000, name=None):
    return dict(schema_version=1, id=name or f'{variant}-{clock}',
                variant=variant, clock_hz=clock,
                cpu=dict(isa='rv32imafc', issue_width=2, icache_bytes=32768,
                         dcache_bytes=65536, config_sha256='a' * 64),
                sources=dict(os_revision='os-revision', sdk_revision='sdk-revision'),
                artifacts=dict(os_sha256='b' * 64, bitstream_sha256='c' * 64,
                               loader_sha256='d' * 64), features=[])


def run(name='run-1', *, variant='os25', clock=100000000,
        backend='device', bound=True, correctness='not_checked'):
    from benchmarks.profiles import bind_profile
    meta = metadata(rows=['frame'])
    meta['build']['elf_sha256'] = 'e' * 64
    meta['platform'].update(variant=variant, clock_hz=clock)
    result = dict(run_id=name, metadata=meta, backend=backend, adapter='fixture',
                  comparison_config={}, checks=dict(complete=True, correctness=correctness),
                  rows=[dict(id='frame', samples=10, metrics=dict(frame_mean_us=123))])
    if bound:
        result['platform_profile'] = bind_profile(profile(variant, clock), meta)
    return result


def selected(matrix, variant='os25', clock=100000000, row=0):
    return next(cell for cell in matrix['rows'][row]['cells']
                if cell['variant'] == variant and cell['clock_hz'] == clock)


class CoverageTests(unittest.TestCase):
    def test_empty_selection_has_all_four_untested_cells(self):
        matrix = coverage_matrix([], project='butterscotch', game='undertale', case_id='route')
        self.assertEqual(len(matrix['rows']), 1)
        row = matrix['rows'][0]
        self.assertEqual(row['scope']['project'], 'butterscotch')
        self.assertEqual(row['scope']['game'], 'undertale')
        self.assertEqual(row['scope']['case']['id'], 'route')
        self.assertEqual([(c['variant'], c['clock_hz']) for c in row['cells']],
                         [('os20', 90000000), ('os20', 100000000),
                          ('os25', 90000000), ('os25', 100000000)])
        self.assertTrue(all(c['status'] == 'untested' for c in row['cells']))

    def test_profiles_register_all_permutations_without_device_claims(self):
        profiles = [profile(v, c) for v in ('os20', 'os25')
                    for c in (90000000, 100000000)]
        matrix = coverage_matrix([], profiles)
        for cell in matrix['rows'][0]['cells']:
            self.assertEqual(cell['status'], 'profile_registered')
            self.assertEqual(cell['profile_ids'], [f"{cell['variant']}-{cell['clock_hz']}"])
            self.assertEqual(cell['counts']['device_observed'], 0)
            self.assertEqual(cell['run_ids'], [])

    def test_four_cells_are_independent_and_do_not_contain_timing_aggregates(self):
        values = [run(f'{v}-{c}', variant=v, clock=c)
                  for v in ('os20', 'os25') for c in (90000000, 100000000)]
        original = copy.deepcopy(values)
        matrix = coverage_matrix(values)
        self.assertEqual(len(matrix['rows']), 1)
        for cell in matrix['rows'][0]['cells']:
            self.assertEqual(cell['status'], 'device_observed')
            self.assertEqual(cell['counts']['total'], 1)
            self.assertEqual(cell['counts']['profile_bound'], 1)
            self.assertEqual(cell['counts']['device_observed'], 1)
            self.assertNotIn('rows', cell['runs'][0])
        self.assertEqual(values, original)
        self.assertNotIn('hardware_verified', str(matrix))
        self.assertNotIn('frame_mean_us', str(matrix))

    def test_pass_failure_and_unchecked_evidence_are_retained_together(self):
        values = [run('pass', correctness='reported_pass'),
                  run('fail', correctness='reported_fail'), run('unchecked')]
        cell = selected(coverage_matrix(values))
        self.assertEqual(cell['status'], 'reported_fail')
        self.assertEqual(set(cell['run_ids']), {'pass', 'fail', 'unchecked'})
        self.assertEqual(cell['counts']['reported_pass'], 1)
        self.assertEqual(cell['counts']['failures'], 1)
        self.assertEqual(cell['failures'][0]['run_id'], 'fail')
        self.assertEqual(selected(coverage_matrix([values[0]]))['status'], 'device_reported_pass')

    def test_unbound_device_pass_is_provisional(self):
        cell = selected(coverage_matrix([run(bound=False, correctness='reported_pass')]))
        self.assertEqual(cell['status'], 'provisional')
        self.assertEqual(cell['counts']['provisional'], 1)
        self.assertEqual(cell['counts']['device_observed'], 0)
        self.assertEqual(cell['counts']['device_reported_pass'], 0)

    def test_host_and_simulation_have_separate_scopes_without_device_promotion(self):
        values = [run('host', backend='host', bound=False, correctness='reported_pass'),
                  run('sim', backend='simulation', bound=False, correctness='reported_pass')]
        matrix = coverage_matrix(values)
        self.assertEqual(len(matrix['rows']), 2)
        by_backend = {row['scope']['backend']: selected(matrix, row=i)
                      for i, row in enumerate(matrix['rows'])}
        self.assertEqual(by_backend['host']['status'], 'host_observed')
        self.assertEqual(by_backend['simulation']['status'], 'simulated')
        for cell in by_backend.values():
            self.assertEqual(cell['counts']['device_reported_pass'], 0)
            self.assertEqual(cell['counts']['device_observed'], 0)

    def test_synthetic_fixtures_are_excluded_not_counted_as_physical_runs(self):
        value = run('synthetic', correctness='reported_pass')
        value['metadata']['conditions']['synthetic_fixture'] = True
        matrix = coverage_matrix([value])
        self.assertEqual(matrix['excluded_synthetic_run_ids'], ['synthetic'])
        self.assertEqual(selected(matrix)['status'], 'untested')
        self.assertEqual(selected(matrix)['counts']['total'], 0)

    def test_unknown_configurations_are_unclassified_with_reasons(self):
        values = [run('unknown-clock', clock=None, bound=False),
                  run('unknown-variant', variant='unknown', bound=False),
                  run('other-clock', clock=80000000, bound=False)]
        matrix = coverage_matrix(values)
        self.assertEqual(len(matrix['unclassified']), 3)
        for item in matrix['unclassified']:
            self.assertTrue(item['reason'])
        self.assertTrue(all(cell['counts']['total'] == 0
                            for row in matrix['rows'] for cell in row['cells']))

    def test_duplicate_run_ids_are_rejected_including_different_contents(self):
        value = run()
        for duplicate in (copy.deepcopy(value), run(correctness='reported_pass')):
            with self.assertRaisesRegex(ValueError, 'duplicate.*run'):
                coverage_matrix([value, duplicate])

    def test_exact_scope_separates_workload_application_device_and_platform_extras(self):
        base = run('base')
        edits = [lambda m: m['case'].update(seed=8),
                 lambda m: m['case'].update(expected_rows=['different']),
                 lambda m: m['build'].update(source_revision='other-source'),
                 lambda m: m['build'].update(elf_sha256='f' * 64),
                 lambda m: m['build'].update(compiler='other-compiler'),
                 lambda m: m['build'].update(flags=['-O3']),
                 lambda m: m['conditions'].update(audio='off'),
                 lambda m: m['platform'].update(device_id='other-device'),
                 lambda m: m['platform'].update(firmware='other-firmware')]
        for edit in edits:
            other = copy.deepcopy(base)
            other['run_id'] = 'other'
            edit(other['metadata'])
            # Roster isn't consumed or averaged by the coverage reporter.
            if other['metadata']['case']['expected_rows'] == ['different']:
                other['rows'][0]['id'] = 'different'
            with self.subTest(edit=edit):
                self.assertEqual(len(coverage_matrix([base, other])['rows']), 2)
        label = copy.deepcopy(base)
        label['run_id'] = 'label'
        label['metadata']['build']['id'] = 'different-label'
        self.assertEqual(len(coverage_matrix([base, label])['rows']), 1)

    def test_filters_and_no_matches_keep_selected_empty_scope(self):
        value = run()
        matrix = coverage_matrix([value], project='vvvvvv', game='vvvvvv', case_id='selected')
        self.assertEqual(matrix['rows'][0]['scope']['case'], {'id': 'selected'})
        self.assertEqual(selected(matrix)['status'], 'untested')
        matrix = coverage_matrix([value], project='butterscotch', game='undertale',
                                 case_id='fixture-route')
        self.assertEqual(selected(matrix)['run_ids'], ['run-1'])

    def test_profile_and_binding_tampering_are_rejected(self):
        bad = profile()
        bad['artifacts']['os_sha256'] = 'invalid'
        with self.assertRaises(ValueError):
            coverage_matrix([], [bad])
        value = run()
        value['platform_profile']['sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            coverage_matrix([value])
        value = run()
        value['metadata']['platform']['clock_hz'] = 90000000
        with self.assertRaises(ValueError):
            coverage_matrix([value])

    def test_profile_id_reuse_retains_both_hashes_and_full_run_context(self):
        from benchmarks.profiles import bind_profile
        first, second = run('first'), run('second')
        changed = profile()
        changed['artifacts']['loader_sha256'] = 'f' * 64
        second['platform_profile'] = bind_profile(changed, second['metadata'])
        cell = selected(coverage_matrix([first, second]))
        self.assertEqual(len(cell['profile_ids']), 1)
        self.assertEqual(len(cell['profile_sha256s']), 2)
        self.assertEqual(len(cell['profiles']), 2)
        self.assertEqual(cell['runs'][0]['build'], first['metadata']['build'])
        self.assertEqual(cell['runs'][1]['platform_profile'], second['platform_profile'])

    def test_incomplete_run_is_not_a_device_observation_or_reported_pass(self):
        value = run(correctness='reported_pass')
        value['checks']['complete'] = False
        cell = selected(coverage_matrix([value]))
        self.assertEqual(cell['status'], 'provisional')
        self.assertEqual(cell['counts']['device_observed'], 0)
        self.assertEqual(cell['counts']['device_reported_pass'], 0)
        self.assertEqual(cell['counts']['failures'], 1)
        self.assertIn('incomplete', cell['failures'][0]['reason'])


if __name__ == '__main__':
    unittest.main()
