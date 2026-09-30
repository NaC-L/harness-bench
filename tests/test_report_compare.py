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
        # One failure: 9 runs of tokens over 8 correct is +12.5% per correct, beyond the 10% margin.
        self.assertEqual(self.headline(worse),
                         'Winner: base (baseline). cand (candidate) passes fewer runs and uses more tokens.')
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
