import unittest

from bench import report

TASKS = ('alpha', 'beta', 'gamma')


def row(harness, task, trial, *, tokens=1000, wall=10.0, passed=True, verified=True, **extra):
    metrics = {'input_tokens': tokens // 2, 'output_tokens': tokens // 4, 'cache_read_tokens': tokens // 4,
               'cache_write_tokens': 0, 'cost_usd': 0.01, 'auxiliary_calls': 0, 'auxiliary_tokens': 0,
               'verified_after_final_edit': verified, 'reproduced_before_first_edit': False}
    base = {'harness': harness, 'harness_kind': 'omp', 'harness_version': '1.0', 'task': task, 'trial': trial,
            'prompt_hash': 'p-' + task, 'task_hash': 't-' + task, 'context_hashes': {},
            'passed': passed, 'agent_exit_code': 0, 'timed_out': False, 'tampered_files': [],
            'agent_completion': 'completed', 'agent_retries': 0, 'regressions': [],
            'wall_time_sec': wall, 'metrics': metrics}
    base.update(extra)
    return base


def arm(harness, trials=3, **kwargs):
    return [row(harness, task, trial, **kwargs) for task in TASKS for trial in range(1, trials + 1)]


class CompareTests(unittest.TestCase):
    def verdict(self, rows, **kwargs):
        return report.compare(rows, 'base', 'cand', **kwargs)

    def test_identical_arms_are_equivalent(self):
        result = self.verdict(arm('base') + arm('cand'))
        self.assertEqual(result['verdict'], 'equivalent', result)
        self.assertEqual(set(result['dimensions'].values()), {'same'})
        self.assertEqual(result['reasons'], [])
        self.assertIn('correctness at ceiling: every run passed, so these tasks cannot distinguish correctness',
                      result['warnings'])

    def test_fewer_tokens_is_better(self):
        result = self.verdict(arm('base') + arm('cand', tokens=800))
        self.assertEqual(result['verdict'], 'better')
        self.assertEqual(result['dimensions']['tokens'], 'better')

    def test_fewer_tokens_but_slower_is_tradeoff(self):
        result = self.verdict(arm('base') + arm('cand', tokens=800, wall=12.0))
        self.assertEqual(result['verdict'], 'tradeoff')
        self.assertEqual(result['dimensions']['time'], 'worse')

    def test_single_extra_failure_is_worse_despite_fewer_tokens(self):
        cand = arm('cand', tokens=800)
        cand[0]['passed'] = False
        result = self.verdict(arm('base') + cand)
        self.assertEqual(result['verdict'], 'worse')
        self.assertEqual(result['dimensions']['correctness'], 'worse')

    def test_lower_verification_rate_is_worse(self):
        cand = arm('cand')
        cand[0]['metrics']['verified_after_final_edit'] = False
        result = self.verdict(arm('base') + cand)
        self.assertEqual(result['verdict'], 'worse')
        self.assertEqual(result['dimensions']['safety'], 'worse')

    def test_change_within_margin_is_equivalent(self):
        result = self.verdict(arm('base') + arm('cand', tokens=950))
        self.assertEqual(result['verdict'], 'equivalent')

    def test_same_mean_effect_is_called_only_when_the_interval_supports_it(self):
        # Every candidate averages 20% fewer tokens; only the run-to-run spread differs.
        def cand(spread):
            return [row('cand', task, trial, tokens=800 + spread * (trial - 2))
                    for task in TASKS for trial in (1, 2, 3)]
        tight = self.verdict(arm('base') + cand(20))
        self.assertEqual(tight['verdict'], 'better')
        interval = tight['intervals']['tokens_per_correct']
        self.assertLess(interval['high'], 0.9)
        self.assertLessEqual(interval['low'], interval['ratio'])
        no_loss = self.verdict(arm('base') + cand(400))
        self.assertEqual((no_loss['verdict'], no_loss['dimensions']['tokens']), ('inconclusive', 'non-inferior'))
        self.assertIn('tokens: no loss beyond 10%, but neither a gain nor equivalence is established',
                      no_loss['reasons'])
        noisy = self.verdict(arm('base') + cand(700))
        self.assertEqual((noisy['verdict'], noisy['dimensions']['tokens']), ('inconclusive', 'uncertain'))
        self.assertTrue(any('may be more than 10% worse' in reason for reason in noisy['reasons']), noisy['reasons'])

    def test_too_few_trials_is_inconclusive(self):
        cand = [r for r in arm('cand') if not (r['task'] == 'beta' and r['trial'] == 3)]
        result = self.verdict(arm('base') + cand)
        self.assertEqual(result['verdict'], 'inconclusive')
        self.assertIn('cand/beta: 2 trials < 3', result['reasons'])

    def test_different_task_inputs_are_inconclusive(self):
        cand = arm('cand')
        cand[0]['task_hash'] = 'changed'
        result = self.verdict(arm('base') + cand)
        self.assertEqual(result['verdict'], 'inconclusive')
        self.assertIn('task inputs differ for alpha', result['reasons'])

    def test_unknown_metrics_are_inconclusive_not_zero(self):
        cand = arm('cand', metrics=None)
        result = self.verdict(arm('base') + cand)
        self.assertEqual(result['verdict'], 'inconclusive')
        self.assertIn('token usage unknown', result['reasons'])
        self.assertIsNone(result['scorecards']['cand']['tokens_per_correct'])

    def test_unknown_or_identical_harness_raises(self):
        with self.assertRaisesRegex(ValueError, 'no runs for harness: cand'):
            self.verdict(arm('base'))
        with self.assertRaisesRegex(ValueError, 'must differ'):
            report.compare(arm('base'), 'base', 'base')

    def test_failed_attempt_tokens_count_toward_cost_per_correct(self):
        rows = arm('base', trials=1)
        rows[0]['passed'] = False
        card = report.scorecard(rows)
        self.assertEqual(card['passed'], 2)
        self.assertEqual(card['total_tokens'], 3000)
        self.assertEqual(card['tokens_per_correct'], 1500)
        self.assertEqual(card['uncached_tokens_per_correct'], 1125)

    def test_scorecard_percentiles_and_legacy_rows(self):
        rows = [{'harness': 'x', 'task': 't', 'passed': True, 'agent_exit_code': 0, 'wall_time_sec': float(w)}
                for w in range(1, 11)]
        card = report.scorecard(rows)
        self.assertEqual(card['median_wall_time_sec'], 5.5)
        self.assertEqual(card['p90_wall_time_sec'], 9.0)
        self.assertEqual(card['max_wall_time_sec'], 10.0)
        self.assertEqual(card['regression_unknown_runs'], 10)
        self.assertIsNone(card['verification_rate'])
        self.assertIsNone(card['retries'])
        self.assertIsNone(card['hidden_tests_pass'])
        self.assertEqual(card['classification_counts'],
                         {'success': 10, 'solution_failure': 0, 'infrastructure_failure': 0, 'unknown': 0})

    def test_classification_uses_explicit_failure_evidence(self):
        cases = [
            ('success', {'passed': True}),
            ('solution_failure', {'tests_fail': 1}),
            ('solution_failure', {'hidden_tests_fail': 1}),
            ('solution_failure', {'check_exit_code': 1}),
            ('solution_failure', {'timed_out': True}),
            ('solution_failure', {'check_timed_out': True}),
            ('solution_failure', {'tampered_files': ['test/hidden.js']}),
            ('solution_failure', {'regressions': ['previously passing test']}),
            ('solution_failure', {'agent_completion': 'incomplete'}),
            ('solution_failure', {'agent_completion': 'error',
                                  'errors': ['Pi final assistant stopped with error']}),
            ('infrastructure_failure', {'agent_exit_code': None,
                                        'errors': ['FileNotFoundError: CLI not found: absent']}),
            ('infrastructure_failure', {'errors': ['CalledProcessError: runner setup command failed']}),
            ('infrastructure_failure', {'errors': ['PermissionError: cannot launch grader'],
                                        'check_exit_code': None}),
            ('infrastructure_failure', {'errors': ['APIError: provider unavailable'],
                                        'tests_fail': 4, 'check_exit_code': 1}),
            ('solution_failure', {'errors': ['Pi automatic retry ended unsuccessfully'],
                                        'agent_completion': 'error', 'check_exit_code': 1}),
            ('solution_failure', {'errors': ['APIError: unavailable'], 'tampered_files': ['package.json']}),
            ('solution_failure', {'errors': ['APIError: unavailable'], 'timed_out': True}),
            ('unknown', {'agent_exit_code': 1}),
            ('unknown', {'errors': ['tool command failed']}),
            ('unknown', {'metrics': {'errors': ['No matching omp session files found']}}),
        ]
        for expected, fields in cases:
            with self.subTest(expected=expected, fields=fields):
                card = report.scorecard([row('base', 'alpha', 1, **{'passed': False, **fields})])
                self.assertEqual(card['classification_counts'][expected], 1)
                self.assertEqual(sum(card['classification_counts'].values()), 1)

    def test_legacy_missing_failure_fields_are_unknown_not_infrastructure_or_unfinished(self):
        card = report.scorecard([{'passed': False}, {}])
        self.assertEqual(card['classification_counts'],
                         {'success': 0, 'solution_failure': 0, 'infrastructure_failure': 0, 'unknown': 2})
        self.assertEqual(card['runs'], 2)
        self.assertEqual(card['passed'], 0)
        self.assertEqual(card['unfinished_runs'], 0)
        self.assertIsNone(card['tokens_per_correct'])

    def test_infrastructure_contamination_retains_attempt_costs_and_blocks_positive_verdict(self):
        base, cand = arm('base'), arm('cand', tokens=500)
        base[0].update(passed=False, tests_fail=1, wall_time_sec=100)
        cand[0].update(passed=False, tests_fail=1, wall_time_sec=100, errors=['APIError: service unavailable'])
        result = self.verdict(base + cand)
        self.assertEqual(result['verdict'], 'inconclusive')
        self.assertEqual(result['dimensions']['correctness'], 'same')
        self.assertEqual(result['dimensions']['tokens'], 'better')
        card = result['scorecards']['cand']
        self.assertEqual(card['classification_counts']['infrastructure_failure'], 1)
        self.assertEqual(card['passed'], 8)
        self.assertEqual(card['total_tokens'], 4500)
        self.assertEqual(card['tokens_per_correct'], 562.5)
        self.assertAlmostEqual(card['cost_usd'], 0.09)
        self.assertAlmostEqual(card['cost_per_correct'], 0.09 / 8)
        self.assertEqual(card['median_wall_time_sec'], 10)
        self.assertEqual(card['p90_wall_time_sec'], 100)
        self.assertEqual(card['max_wall_time_sec'], 100)
        self.assertIn('infrastructure contamination: base 0/9 runs; cand 1/9 runs; all failed attempts retained',
                      result['reasons'])
        task = result['per_task']['alpha']
        self.assertEqual(task['scorecards']['cand']['tokens_per_correct'], 750)
        self.assertEqual(task['ratios']['tokens_per_correct'], 0.5)

    def test_infrastructure_contamination_does_not_hide_correctness_or_safety_worsening(self):
        for fields, dimension in (({'passed': False}, 'correctness'),
                                  ({'metrics': {'verified_after_final_edit': False,
                                                'input_tokens': 500, 'output_tokens': 500}}, 'safety')):
            with self.subTest(dimension=dimension):
                base, cand = arm('base'), arm('cand')
                base[0].update(passed=False, errors=['APIError: unavailable'])
                cand[0].update(passed=False, errors=['APIError: unavailable'])
                cand[1].update(fields)
                result = self.verdict(base + cand)
                self.assertEqual(result['verdict'], 'worse')
                self.assertEqual(result['dimensions'][dimension], 'worse')
                self.assertTrue(any('infrastructure contamination' in reason for reason in result['reasons']))

    def test_task_timeout_is_classified_and_counted_as_safety_failure(self):
        cand = arm('cand')
        cand[0].update(passed=False, check_timed_out=True)
        result = self.verdict(arm('base') + cand)
        self.assertEqual(result['scorecards']['cand']['timeouts'], 1)
        self.assertEqual(result['scorecards']['cand']['classification_counts']['solution_failure'], 1)
        self.assertEqual(result['dimensions']['safety'], 'worse')

    def test_per_task_effects_expose_tradeoffs_hidden_by_aggregate(self):
        cand = [row('cand', task, trial, tokens=tokens)
                for task, tokens in zip(TASKS, (500, 1500, 1000)) for trial in (1, 2, 3)]
        rows = arm('base') + cand
        result = self.verdict(rows)
        self.assertEqual(result['verdict'], 'equivalent')
        self.assertEqual(result['intervals']['tokens_per_correct']['ratio'], 1)
        for task, ratio in zip(TASKS, (0.5, 1.5, 1.0)):
            item = result['per_task'][task]
            self.assertEqual(item['ratios']['tokens_per_correct'], ratio)
            self.assertEqual(item['ratios']['uncached_tokens_per_correct'], ratio)
            self.assertEqual(item['ratios']['median_wall_time_sec'], 1)
            self.assertEqual(item['ratios']['p90_wall_time_sec'], 1)
            self.assertEqual(item['pass_rate_difference'], 0)
        for text in (report.render_comparison(result),
                     report.render_markdown(result, rows, results_label='results/tradeoffs')):
            self.assertIn('| base | 9 | 0 | 0 | 0 |', text)
            self.assertIn('| alpha | cand | 3/3 | 500 | 375 | 10.0 | 10.0 | 3 / 0 / 0 / 0 |', text)
            self.assertIn('| alpha | +0.0 | 0.50 | 0.50 | 1.00 | 1.00 |', text)
            self.assertIn('| beta | +0.0 | 1.50 | 1.50 | 1.00 | 1.00 |', text)
            self.assertIn('descriptive only; no per-task winner or confidence claim', text)

    def test_per_task_pass_rate_differences_expose_cancelling_correctness_changes(self):
        base, cand = arm('base'), arm('cand')
        base[0].update(passed=False, tests_fail=1)
        cand[3].update(passed=False, tests_fail=1)
        result = self.verdict(base + cand)
        self.assertEqual(result['dimensions']['correctness'], 'same')
        self.assertAlmostEqual(result['per_task']['alpha']['pass_rate_difference'], 1 / 3)
        self.assertAlmostEqual(result['per_task']['beta']['pass_rate_difference'], -1 / 3)
        text = report.render_comparison(result)
        self.assertIn('| alpha | +33.3 | 0.67 | 0.67 | 1.00 | 1.00 |', text)
        self.assertIn('| beta | -33.3 | 1.50 | 1.50 | 1.00 | 1.00 |', text)

    def test_per_task_missing_arm_and_undefined_ratios_stay_unknown(self):
        result = self.verdict(arm('base') + [r for r in arm('cand') if r['task'] != 'alpha'])
        item = result['per_task']['alpha']
        self.assertEqual(item['scorecards']['cand']['runs'], 0)
        self.assertIsNone(item['pass_rate_difference'])
        self.assertTrue(all(ratio is None for ratio in item['ratios'].values()))
        self.assertIn('| alpha | unknown | unknown | unknown | unknown | unknown |',
                      report.render_comparison(result))

    def test_render_comparison(self):
        text = report.render_comparison(self.verdict(arm('base') + arm('cand', metrics=None)))
        self.assertTrue(text.startswith('Verdict: inconclusive (cand vs baseline base, margin 10%, min trials 3)'))
        self.assertIn('| tokens | unknown | 1000 total / 750 uncached per correct, 0 aux calls | '
                      'unknown total / unknown uncached per correct, unknown aux calls |', text)
        self.assertIn('Reasons:\n- token usage unknown', text)
        self.assertIn('verification unknown; verification comparison skipped', text)


    def test_correctness_floor_warning(self):
        result = self.verdict(arm('base', passed=False) + arm('cand', passed=False))
        self.assertIn('correctness at floor: no run passed', result['warnings'])
        self.assertNotIn('correctness at ceiling: every run passed, so these tasks cannot distinguish correctness',
                         result['warnings'])

    def test_ceiling_warning_requires_both_arms_at_ceiling(self):
        result = self.verdict(arm('base') + arm('cand', passed=False))
        self.assertFalse(any('correctness at' in warning for warning in result['warnings']))

    def test_markdown_without_manifest(self):
        rows = arm('base') + arm('cand', metrics=None)
        text = report.render_markdown(self.verdict(rows), rows, results_label='results/shared')
        self.assertTrue(text.startswith('# cand vs base\n'))
        for part in ('Verdict: inconclusive', '| Dimension |', '## Per-task results',
                     '| alpha | base | 3/3 | 10.0 | 1000 | 750 |',
                     '| alpha | cand | 3/3 | 10.0 | unknown | unknown |',
                     '## Setup', 'No manifest.json; setup not recorded.', '## Reasons', '## Warnings',
                     '## Reproduce', '--results results/shared', '--config CONFIG',
                     '## How to read this', 'Unknown ≠ 0'):
            self.assertIn(part, text)
        self.assertIn('config path not recorded; replace CONFIG with the harness configuration.', text)

    def test_markdown_with_setup_differing_argv_and_overlays(self):
        rows = arm('base') + arm('cand')
        manifest = {'schema_version': 1, 'invocations': [{
            'started': '2026-09-30T10:00:00+00:00', 'config': 'benchmark-demo.toml',
            'trials': 4, 'jobs': 1, 'alternate_order': True, 'timeout': 90,
            'platform': 'Windows-test', 'python': '3.14', 'node': 'v22',
            'tasks': {'alpha': 'a' * 64, 'beta': 'b' * 64},
            'harnesses': {
                'base': {'kind': 'omp', 'version': '1.0', 'config_hash': 'base-config',
                         'command': ['omp', '--config', '{benchmark_dir}/base.yml', '--same'],
                         'files': {'base.yml': {'sha256': 'base-hash', 'contents': 'inline: off\n'},
                                   'shared.py': {'sha256': 'same-hash', 'contents': 'not an overlay difference'}}},
                'cand': {'kind': 'omp', 'version': '2.0', 'config_hash': 'cand-config',
                         'command': ['omp', '--config', '{benchmark_dir}/cand.yml', '--same'],
                         'files': {'cand.yml': {'sha256': 'cand-hash', 'contents': 'inline: on\n'},
                                   'shared.py': {'sha256': 'same-hash', 'contents': 'not an overlay difference'}}}}}]}
        text = report.render_markdown(self.verdict(rows), rows, manifest, results_label='results/shared')
        for part in ('base: kind omp, version 1.0', 'cand: kind omp, version 2.0', 'Trials/jobs: 4/1',
                     'Windows-test', 'Python: 3.14; Node: v22', 'Command template argv difference',
                     '{benchmark_dir}/base.yml', '{benchmark_dir}/cand.yml', 'inline: off', 'inline: on',
                     'alpha: aaaaaaaaaaaa', '--config benchmark-demo.toml',
                     '--trials 4 --jobs 1', '--alternate-order', '--timeout 90'):
            self.assertIn(part, text)
        self.assertNotIn('not an overlay difference', text)
        self.assertNotIn('--same', text)
        self.assertNotIn('No manifest.json', text)

    def test_markdown_multiple_invocations_preserves_setup(self):
        rows = arm('base') + arm('cand')
        manifest = {'invocations': [
            {'started': 'first', 'harnesses': {'base': {'version': '1'}}, 'tasks': {}, 'trials': 1},
            {'started': 'second', 'harnesses': {'cand': {'version': '2'}}, 'tasks': {}, 'trials': 3}]}
        text = report.render_markdown(self.verdict(rows), rows, manifest, results_label='results/shared')
        self.assertIn('Invocation first', text)
        self.assertIn('Invocation second', text)


class HeadlineTests(unittest.TestCase):
    """The headline must name the winner so readers never interpret a verdict word."""

    def headline(self, rows):
        return report.headline(report.compare(rows, 'base', 'cand'))

    def test_every_verdict_names_a_winner_or_says_there_is_none(self):
        cases = {
            'Winner: cand (candidate). Compared with base (baseline) it uses fewer tokens; '
            'correctness, time and safety are the same.': arm('base') + arm('cand', tokens=800),
            'No overall winner (tradeoff): cand (candidate) uses fewer tokens but runs slower '
            'than base (baseline).': arm('base') + arm('cand', tokens=800, wall=12.0),
            'No winner: cand (candidate) and base (baseline) are equivalent within the 10% margin.':
                arm('base') + arm('cand'),
        }
        for expected, rows in cases.items():
            with self.subTest(expected=expected):
                self.assertEqual(self.headline(rows), expected)
        worse = arm('base') + arm('cand')
        worse[-1]['passed'] = False
        # One failure is +12.5% tokens per correct, but resampling that cell's failure count puts the
        # interval's lower end at no change, so only the correctness gate is called.
        self.assertEqual(self.headline(worse), 'Winner: base (baseline). cand (candidate) passes fewer runs.')
        short = [r for r in arm('base') + arm('cand') if r['trial'] < 3]
        self.assertTrue(self.headline(short).startswith('No winner yet (inconclusive): base/alpha: 2 trials < 3'))

    def test_text_and_markdown_lead_with_the_headline(self):
        result = report.compare(arm('base') + arm('cand', tokens=800), 'base', 'cand')
        self.assertTrue(report.render_comparison(result).splitlines()[1].startswith('Winner: cand (candidate).'))
        markdown = report.render_markdown(result, arm('base') + arm('cand', tokens=800), results_label='r')
        self.assertIn('**Winner: cand (candidate).', markdown)
        self.assertIn('| Dimension | cand vs base | base (baseline) | cand (candidate) |', markdown)


if __name__ == '__main__':
    unittest.main()
