import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from bench.runner import Harness, run_one, run_matrix, expand, executable, version, context_hashes
from bench.tasks import Task, load_task, run_check, tap_results
from bench import report

FAKE = Path(__file__).parent / 'fixtures' / 'fake_harness.py'


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        d = self.root / 'tiny'
        for p in ('repo/src', 'repo/test', 'hidden_tests'):
            (d / p).mkdir(parents=True)
        (d / 'task.toml').write_text('id="tiny"\ntimeout_sec=30\ncheck=["node","--test"]\n')
        (d / 'prompt.md').write_text('Fix value. Literal {session_id} must stay untouched.')
        (d / 'repo/src/value.js').write_text('module.exports = 0;\n')
        (d / 'repo/package.json').write_text('{"type":"commonjs"}\n')
        code = "const t=require('node:test'); const a=require('node:assert/strict'); t('value',()=>a.equal(require('../src/value'),42));\n"
        (d / 'repo/test/visible.test.js').write_text(code)
        (d / 'hidden_tests/hidden.test.js').write_text(code)
        self.task = load_task(d)

    def harness(self, mode):
        return Harness(mode, 'none', [sys.executable, str(FAKE.resolve()), mode],
                       [sys.executable, '--version'], {}, mode)

    def run_mode(self, mode, **kwargs):
        return run_one(self.task, self.harness(mode), self.root / 'results', **kwargs)

    def test_solution_and_artifacts(self):
        row = self.run_mode('solve')
        self.assertTrue(row['passed'], row)
        self.assertEqual(row['tests_pass'], 2)
        artifact = Path(row['artifact_dir'])
        self.assertTrue((artifact / 'patch.diff').read_text())
        self.assertTrue((artifact / 'check.txt').exists())
        self.assertEqual(json.loads((artifact / 'run.json').read_text())['run_id'], row['run_id'])
        self.assertFalse(Path(row['workdir']).exists())
        self.assertTrue((artifact / 'check-visible.txt').exists())
        self.assertTrue(row['visible_passed'])
        self.assertEqual(row['visible_tests_pass'], 1)
        self.assertEqual(row['hidden_tests_pass'], 1)
        self.assertEqual(row['baseline_passing_tests'], 0)
        self.assertEqual(row['regressions'], [])
        self.assertIsNone(row['agent_completion'])

    def test_matrix_records_manifest_before_running_with_template_file(self):
        from bench.manifest import load_manifest
        from bench.runner import fingerprint, runtime_values
        h = self.harness('solve')
        h.command[1] = '{benchmark_dir}/tests/fixtures/fake_harness.py'
        results = self.root / 'matrix'
        rows = run_matrix([self.task], [h], results, trials=1, jobs=1,
                          alternate_order=True, timeout=25, config=Path('harnesses.toml'))
        self.assertTrue(rows[0]['passed'])
        manifest = load_manifest(results)
        self.assertEqual(manifest['schema_version'], 1)
        self.assertEqual(len(manifest['invocations']), 1)
        invocation = manifest['invocations'][0]
        self.assertEqual(invocation['trials'], 1)
        self.assertEqual(invocation['jobs'], 1)
        self.assertTrue(invocation['alternate_order'])
        self.assertEqual(invocation['timeout'], 25)
        self.assertEqual(invocation['config'], 'harnesses.toml')
        self.assertEqual(invocation['tasks'], {'tiny': fingerprint(self.task.dir)})
        self.assertTrue(invocation['started'].endswith('+00:00'))
        self.assertTrue(invocation['platform'])
        self.assertTrue(invocation['python'])
        self.assertTrue(invocation['node'].startswith('v'))
        harness = invocation['harnesses']['solve']
        self.assertEqual(harness['command'], h.command)
        self.assertEqual(harness['kind'], 'none')
        self.assertEqual(harness['config_hash'], 'solve')
        self.assertEqual(harness['version'], rows[0]['harness_version'])
        file = harness['files']['tests/fixtures/fake_harness.py']
        self.assertEqual(file['contents'], FAKE.read_text(encoding='utf-8'))
        import hashlib
        self.assertEqual(file['sha256'], hashlib.sha256(FAKE.read_bytes()).hexdigest())
        self.assertNotIn(runtime_values()['benchmark_dir'], harness['command'][1])
        with patch('bench.runner.run_one', side_effect=RuntimeError('interrupted')):
            with self.assertRaisesRegex(RuntimeError, 'interrupted'):
                run_matrix([self.task], [h], results)
        self.assertEqual(len(load_manifest(results)['invocations']), 2)

    def test_noop_fails(self):
        row = self.run_mode('noop')
        self.assertFalse(row['passed'])
        self.assertEqual(row['tests_fail'], 2)
        self.assertFalse(row['visible_passed'])
        self.assertEqual(row['hidden_tests_fail'], 1)
        self.assertEqual(row['regressions'], [])

    def test_regression_of_baseline_passing_hidden_test_fails_run(self):
        (self.task.repo / 'src/helper.js').write_text('module.exports = 1;\n')
        (self.task.hidden_tests / 'helper.test.js').write_text(
            "const t=require('node:test'); const a=require('node:assert/strict'); "
            "t('helper keeps one',()=>a.equal(require('../src/helper'),1));\n")
        row = self.run_mode('regress')
        self.assertTrue(row['visible_passed'])
        self.assertFalse(row['passed'])
        self.assertEqual(row['baseline_passing_tests'], 1)
        self.assertEqual(row['regressions'], ['helper keeps one'])

    def test_tap_results_top_level_only_with_duplicate_names(self):
        output = "ok 1 - a\nnot ok 2 - b\n    ok 1 - nested\nok 3 - s # SKIP\nok 4 - a\n"
        self.assertEqual(tap_results(output), {'a': True, 'b': False, 'a (2)': True})
        self.assertEqual(tap_results('no tap here'), {})

    def test_omp_json_runs_require_completed_stream(self):
        for command, checked in ((['omp', '--mode', 'json'], True), (['herdr-omp', 'json'], False)):
            for status in ('completed', 'incomplete'):
                with self.subTest(command=command, status=status):
                    h = self.harness('solve')
                    h.kind = 'omp'
                    h.command = [*h.command, *command]
                    with patch('bench.sessions.collect', return_value={'session_files': []}), \
                         patch('bench.sessions.omp_completion', return_value=(status, [])) as completion:
                        row = run_one(self.task, h, self.root / 'omp-status')
                    self.assertEqual(completion.called, checked)
                    self.assertEqual(row['agent_completion'], status if checked else None)
                    self.assertEqual(row['agent_retries'], 0 if checked else None)
                    self.assertEqual(row['passed'], status == 'completed' or not checked)

    def test_tamper_fails_even_if_restored_tests_pass(self):
        row = self.run_mode('tamper')
        self.assertFalse(row['passed'])
        self.assertEqual(row['tests_fail'], 0)
        self.assertEqual(row['tampered_files'], ['test/extra.test.js', 'test/visible.test.js'])

    def test_timeout(self):
        row = self.run_mode('hang', timeout=1)
        self.assertTrue(row['timed_out'])
        self.assertFalse(row['passed'])
        self.assertLess(row['wall_time_sec'], 10)

    def test_nonzero_exit_and_missing_cli(self):
        self.assertEqual(self.run_mode('error')['agent_exit_code'], 3)
        h = self.harness('noop')
        h.command = ['no-such-harness-bench-executable']
        row = run_one(self.task, h, self.root / 'missing')
        self.assertFalse(row['passed'])
        self.assertTrue(row['errors'])

    def test_parallel_matrix(self):
        results = self.root / 'matrix'
        rows = run_matrix([self.task], [self.harness('solve')], results, trials=2, jobs=2)
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r['passed'] for r in rows))
        self.assertEqual(len(report.load(results / 'runs.jsonl')), 2)
        self.assertNotEqual(rows[0]['workdir'], rows[1]['workdir'])

    def test_prompt_braces_are_not_expanded_twice(self):
        self.assertEqual(expand(['{prompt}'], {'prompt': '{session_id}', 'session_id': 'actual'}), ['{session_id}'])

    def test_grading_timeout(self):
        self.task.check = [sys.executable, '-c', 'import time; time.sleep(60)']
        self.task.check_timeout_sec = 1
        result = run_check(self.task, self.task.repo, include_hidden=False)
        self.assertTrue(result.timed_out)
        self.assertFalse(result.passed)

    def test_visible_only_check_does_not_overlay_hidden_tests(self):
        result = run_check(self.task, self.task.repo, include_hidden=False)
        self.assertEqual(result.tests_fail, 1)
        self.assertFalse((self.task.repo / 'test/hidden.test.js').exists())

    def test_only_omp_and_pi_redirect_session_lookup(self):
        for kind in ('omp', 'pi', 'claude', 'codex'):
            with self.subTest(kind=kind):
                h = self.harness('solve')
                h.kind = kind
                h.env = {'CODEX_HOME': str(self.root / 'custom-codex')}
                with patch('bench.sessions.collect', return_value={'session_files': []}) as collect, \
                     patch('bench.sessions.pi_completion', return_value=('completed', [])):
                    row = run_one(self.task, h, self.root / 'lookup')
                self.assertEqual(collect.call_args.kwargs['env']['CODEX_HOME'], h.env['CODEX_HOME'])
                session_dir = collect.call_args.kwargs['session_dir']
                if kind in ('omp', 'pi'):
                    # Temp dirs have aliases (macOS /private/var, Windows 8.3 names); compare the directory.
                    self.assertEqual(Path(session_dir).resolve(), (Path(row['artifact_dir']) / 'sessions').resolve())
                else:
                    self.assertIsNone(session_dir)

    def test_custom_path_and_version_environment(self):
        env = {'PATH': str(Path(sys.executable).parent), 'BENCH_VERSION': 'custom-version'}
        argv = [Path(sys.executable).name, '-c', 'import os; print(os.environ[\"BENCH_VERSION\"])']
        h = self.harness('solve')
        h.env, h.version_command = env, argv
        with patch.dict(os.environ, {'PATH': ''}):
            self.assertEqual(Path(executable(argv, env)[0]), Path(sys.executable))
            self.assertEqual(version(h), 'custom-version')

    def test_config_hashes_follow_state_override(self):
        state = self.root / 'custom-claude'
        state.mkdir()
        settings = state / 'settings.json'
        settings.write_text('{\"model\":\"pinned\"}')
        hashes = context_hashes('claude', {'CLAUDE_CONFIG_DIR': str(state)})
        self.assertEqual(list(hashes), [str(settings)])
        self.assertEqual(len(hashes[str(settings)]), 64)

    def test_pi_failed_stream_cannot_pass_even_with_solved_code(self):
        for status in ('completed', 'error', 'incomplete'):
            with self.subTest(status=status):
                h = self.harness('solve')
                h.kind = 'pi'
                with patch('bench.sessions.collect', return_value={'session_files': []}), \
                     patch('bench.sessions.pi_completion', return_value=(status, [])):
                    row = run_one(self.task, h, self.root / 'pi-status')
                self.assertEqual(row['tests_fail'], 0)
                self.assertEqual(row['agent_completion'], status)
                self.assertEqual(row['passed'], status == 'completed')

    def test_runtime_paths_expand_in_run_and_version(self):
        h = self.harness('solve')
        h.command[0] = '{python}'
        h.version_command = ['{python}', '--version']
        row = run_one(self.task, h, self.root / 'runtime-paths')
        self.assertTrue(row['passed'])
        self.assertEqual(row['command'][0], sys.executable)
        self.assertTrue(version(h).startswith('Python '))

    def test_pi_settings_hashes_follow_state_override(self):
        state = self.root / 'custom-pi'
        state.mkdir()
        settings = state / 'settings.json'
        settings.write_text('{"thinkingLevel":"high"}')
        hashes = context_hashes('pi', {'PI_CODING_AGENT_DIR': str(state)})
        self.assertEqual(list(hashes), [str(settings)])


class MatrixOrderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tasks = [Task(name, self.root / name, name, 'test', 'Fix it.', 30, [])
                      for name in ('first', 'second', 'third')]
        self.harnesses = [Harness(name, 'none', [], [], {}, name)
                          for name in ('baseline', 'candidate')]

    def matrix_order(self, **kwargs):
        def record(task, harness, results, trial, *args):
            return {'task': task.id, 'harness': harness.name, 'trial': trial,
                    'passed': True, 'wall_time_sec': 0}
        results = self.root / 'matrix'
        with patch('bench.runner.version', return_value='fake'), \
             patch('bench.runner.run_one', side_effect=record) as run:
            rows = run_matrix(self.tasks, self.harnesses, results, **kwargs)
        observed = [(call.args[0].id, call.args[1].name, call.args[3])
                    for call in run.call_args_list]
        self.assertEqual(observed, [(row['task'], row['harness'], row['trial']) for row in rows])
        self.assertEqual(report.load(results / 'runs.jsonl'), rows)
        self.assertEqual([h.name for h in self.harnesses], ['baseline', 'candidate'])
        return observed

    def test_alternate_order_three_tasks(self):
        self.assertEqual(self.matrix_order(alternate_order=True), [
            ('first', 'baseline', 1), ('first', 'candidate', 1),
            ('second', 'candidate', 1), ('second', 'baseline', 1),
            ('third', 'baseline', 1), ('third', 'candidate', 1),
        ])

    def test_alternate_order_continues_across_trials(self):
        self.assertEqual(self.matrix_order(trials=2, alternate_order=True), [
            ('first', 'baseline', 1), ('first', 'candidate', 1),
            ('second', 'candidate', 1), ('second', 'baseline', 1),
            ('third', 'baseline', 1), ('third', 'candidate', 1),
            ('first', 'candidate', 2), ('first', 'baseline', 2),
            ('second', 'baseline', 2), ('second', 'candidate', 2),
            ('third', 'candidate', 2), ('third', 'baseline', 2),
        ])

    def test_default_order_unchanged(self):
        self.assertEqual(self.matrix_order(trials=2), [
            ('first', 'baseline', 1), ('first', 'candidate', 1),
            ('second', 'baseline', 1), ('second', 'candidate', 1),
            ('third', 'baseline', 1), ('third', 'candidate', 1),
            ('first', 'baseline', 2), ('first', 'candidate', 2),
            ('second', 'baseline', 2), ('second', 'candidate', 2),
            ('third', 'baseline', 2), ('third', 'candidate', 2),
        ])

    def test_alternate_order_rejects_parallel_jobs_before_side_effects(self):
        results = self.root / 'invalid'
        for jobs in (2, 4):
            with self.subTest(jobs=jobs), \
                 patch('bench.runner.version') as version_call, \
                 patch('bench.runner.run_one') as run:
                with self.assertRaisesRegex(ValueError, 'alternate_order requires jobs=1'):
                    run_matrix(self.tasks, self.harnesses, results, jobs=jobs, alternate_order=True)
                version_call.assert_not_called()
                run.assert_not_called()
                self.assertFalse(results.exists())


class ReportTests(unittest.TestCase):
    def test_pass_at_k(self):
        self.assertEqual(report.pass_at_k(4, 1, 2), 0.5)
        self.assertIsNone(report.pass_at_k(1, 1, 2))
        self.assertEqual(report.pass_at_k(3, 0, 1), 0)
        self.assertEqual(report.pass_at_k(3, 3, 1), 1)

    def test_unknown_cost_and_separate_cohorts(self):
        rows = [{'harness': 'a', 'task': 'x', 'config_hash': 'v1', 'passed': True,
                 'wall_time_sec': 2, 'metrics': {'cost_usd': None}},
                {'harness': 'a', 'task': 'x', 'config_hash': 'v1', 'passed': False,
                 'wall_time_sec': 4, 'metrics': {'cost_usd': 0.1}},
                {'harness': 'a', 'task': 'x', 'config_hash': 'v2', 'passed': True, 'metrics': {}}]
        out = report.summarize(rows)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]['wall_time_median_sec'], 3)
        self.assertEqual(out[0]['cost_known_runs'], 1)
        self.assertEqual(out[0]['cost_usd_median'], 0.1)
        self.assertEqual(out[0]['pass@1'], 0.5)
        self.assertIn('unknown', report.render(rows))

    def test_task_revision_models_and_context_split_cohorts(self):
        base = {'harness': 'a', 'task': 'x', 'passed': True,
                'task_hash': 'r1', 'context_hashes': {'settings': 'c1'},
                'metrics': {'models': ['m1']}}
        rows = [base, {**base, 'task_hash': 'r2'},
                {**base, 'context_hashes': {'settings': 'c2'}},
                {**base, 'metrics': {'models': ['m2']}}]
        self.assertEqual(len(report.summarize(rows)), 4)


if __name__ == '__main__':
    unittest.main()
