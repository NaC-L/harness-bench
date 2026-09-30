import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from bench.__main__ import main
from bench.runner import Harness


class MainTests(unittest.TestCase):
    def setUp(self):
        self.tasks = [object()]
        self.harnesses = {name: Harness(name, 'omp', [], [], {}, name)
                          for name in ('omp-baseline', 'omp-inline')}

    def test_alternate_order_forwarded(self):
        argv = ['bench', '--config', 'benchmark-omp-descriptors.toml',
                '--results', 'results/omp-descriptors-pilot', 'run',
                '--harness', 'omp-baseline', 'omp-inline', '--trials', '2',
                '--jobs', '1', '--alternate-order']
        with patch.object(sys, 'argv', argv), \
             patch('bench.__main__.load_tasks', return_value=self.tasks), \
             patch('bench.__main__.load_harnesses', return_value=self.harnesses) as load, \
             patch('bench.__main__.run_matrix', return_value=[{'passed': True}]) as run:
            self.assertEqual(main(), 0)
        load.assert_called_once_with(Path('benchmark-omp-descriptors.toml'))
        run.assert_called_once_with(self.tasks, list(self.harnesses.values()),
                                    Path('results/omp-descriptors-pilot'), trials=2,
                                    jobs=1, timeout=None, keep_workdir=False, alternate_order=True,
                                    config=Path('benchmark-omp-descriptors.toml'))

    def test_default_order_and_parallel_jobs_forwarded(self):
        argv = ['bench', 'run', '--harness', 'omp-baseline', 'omp-inline', '--jobs', '2']
        with patch.object(sys, 'argv', argv), \
             patch('bench.__main__.load_tasks', return_value=self.tasks), \
             patch('bench.__main__.load_harnesses', return_value=self.harnesses), \
             patch('bench.__main__.run_matrix', return_value=[{'passed': True}]) as run:
            self.assertEqual(main(), 0)
        self.assertFalse(run.call_args.kwargs['alternate_order'])
        self.assertEqual(run.call_args.kwargs['jobs'], 2)
        self.assertEqual(run.call_args.args[1], list(self.harnesses.values()))

    def test_alternate_order_rejects_parallel_jobs_before_loading(self):
        argv = ['bench', 'run', '--harness', 'omp-baseline', 'omp-inline',
                '--jobs', '2', '--alternate-order']
        stderr = io.StringIO()
        with patch.object(sys, 'argv', argv), contextlib.redirect_stderr(stderr), \
             patch('bench.__main__.load_tasks') as tasks, \
             patch('bench.__main__.load_harnesses') as harnesses, \
             patch('bench.__main__.run_matrix') as run:
            with self.assertRaises(SystemExit) as error:
                main()
        self.assertEqual(error.exception.code, 2)
        self.assertIn('--alternate-order requires --jobs 1', stderr.getvalue())
        tasks.assert_not_called()
        harnesses.assert_not_called()
        run.assert_not_called()

    def test_compare_forwards_arguments(self):
        argv = ['bench', '--results', 'results/pilot', 'compare', '--baseline', 'a',
                '--candidate', 'b', '--margin', '0.2', '--min-trials', '5']
        result = {'verdict': 'equivalent'}
        with patch.object(sys, 'argv', argv), contextlib.redirect_stdout(io.StringIO()), \
             patch('bench.__main__.report.load', return_value=['row']) as load, \
             patch('bench.__main__.report.compare', return_value=result) as compare, \
             patch('bench.__main__.report.render_comparison', return_value='text') as render, \
             patch('bench.__main__.load_tasks') as tasks:
            self.assertEqual(main(), 0)
        load.assert_called_once_with(Path('results/pilot') / 'runs.jsonl')
        compare.assert_called_once_with(['row'], 'a', 'b', margin=0.2, min_trials=5)
        render.assert_called_once_with(result)
        tasks.assert_not_called()

    def test_compare_rejects_margin_outside_unit_interval(self):
        argv = ['bench', 'compare', '--baseline', 'a', '--candidate', 'b', '--margin', '1.5']
        stderr = io.StringIO()
        with patch.object(sys, 'argv', argv), contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as error:
                main()
        self.assertEqual(error.exception.code, 2)
        self.assertIn('must be in [0, 1)', stderr.getvalue())

    def test_compare_value_error_is_usage_error(self):
        argv = ['bench', 'compare', '--baseline', 'a', '--candidate', 'a']
        stderr = io.StringIO()
        with patch.object(sys, 'argv', argv), contextlib.redirect_stderr(stderr), \
             patch('bench.__main__.report.load', return_value=[]):
            with self.assertRaises(SystemExit) as error:
                main()
        self.assertEqual(error.exception.code, 2)
        self.assertIn('baseline and candidate must differ', stderr.getvalue())


    def test_compare_formats_and_deprecated_json_alias(self):
        result = {'verdict': 'equivalent'}
        for flags in (['--format', 'json'], ['--json'], ['--format', 'markdown']):
            with self.subTest(flags=flags):
                argv = ['bench', '--results', 'results/pilot', 'compare', '--baseline', 'a',
                        '--candidate', 'b', *flags]
                stdout = io.StringIO()
                with patch.object(sys, 'argv', argv), contextlib.redirect_stdout(stdout), \
                     patch('bench.__main__.report.load', return_value=['row']), \
                     patch('bench.__main__.report.compare', return_value=result), \
                     patch('bench.__main__.load_manifest', return_value={'schema_version': 1}) as manifest, \
                     patch('bench.__main__.report.render_markdown', return_value='# b vs a\n') as markdown:
                    self.assertEqual(main(), 0)
                if 'markdown' in flags:
                    self.assertEqual(stdout.getvalue(), '# b vs a\n')
                    markdown.assert_called_once_with(result, ['row'], {'schema_version': 1},
                                                     results_label=str(Path('results/pilot')))
                    manifest.assert_called_once_with(Path('results/pilot'))
                else:
                    self.assertEqual(json.loads(stdout.getvalue()), result)
                    markdown.assert_not_called()

    def test_compare_charts_dir_writes_svgs_and_embeds_posix_paths(self):
        from tests.test_charts import rows
        from bench.charts import render_charts
        from bench.report import compare
        records = rows()
        result = compare(records, 'base', 'cand')
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / 'charts'
            argument = str(directory)
            expected_prefix = argument.replace('\\', '/')
            argv = ['bench', '--results', 'results/pilot', 'compare', '--baseline', 'base',
                    '--candidate', 'cand', '--format', 'markdown', '--charts-dir', argument]
            stdout = io.StringIO()
            with patch.object(sys, 'argv', argv), contextlib.redirect_stdout(stdout), \
                 patch('bench.__main__.report.load', return_value=records), \
                 patch('bench.__main__.report.compare', return_value=result), \
                 patch('bench.__main__.load_manifest', return_value=None):
                self.assertEqual(main(), 0)
            for name, svg in render_charts(result, records).items():
                self.assertEqual((directory / name).read_text(encoding='utf-8'), svg)
                self.assertIn(f']({expected_prefix}/{name})', stdout.getvalue())
            self.assertIn('## Charts', stdout.getvalue())

    def test_compare_without_charts_dir_does_not_render_charts(self):
        argv = ['bench', 'compare', '--baseline', 'a', '--candidate', 'b', '--format', 'markdown']
        with patch.object(sys, 'argv', argv), contextlib.redirect_stdout(io.StringIO()), \
             patch('bench.__main__.report.load', return_value=['row']), \
             patch('bench.__main__.report.compare', return_value={'verdict': 'equivalent'}), \
             patch('bench.__main__.report.render_markdown', return_value='report'), \
             patch('bench.__main__.load_manifest', return_value=None), \
             patch('bench.__main__.render_charts') as charts:
            self.assertEqual(main(), 0)
        charts.assert_not_called()

    def test_compare_rejects_unknown_format(self):
        argv = ['bench', 'compare', '--baseline', 'a', '--candidate', 'b', '--format', 'csv']
        with patch.object(sys, 'argv', argv), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                main()
        self.assertEqual(error.exception.code, 2)

    def test_export_forwards_arguments(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'bundle'
            argv = ['bench', '--results', 'results/pilot', 'export', '--baseline', 'a',
                    '--candidate', 'b', '--out', str(out), '--margin', '0.2', '--min-trials', '2',
                    '--include-transcripts']
            with patch.object(sys, 'argv', argv), \
                 patch('bench.__main__.report.load', return_value=['row']) as load, \
                 patch('bench.__main__.export') as export, \
                 patch('bench.__main__.load_tasks') as tasks:
                self.assertEqual(main(), 0)
            load.assert_called_once_with(Path('results/pilot') / 'runs.jsonl')
            export.assert_called_once_with(['row'], Path('results/pilot'), out, 'a', 'b',
                                           margin=0.2, min_trials=2, include_transcripts=True)
            tasks.assert_not_called()

    def test_export_rejects_existing_out_before_loading(self):
        with tempfile.TemporaryDirectory() as temp:
            argv = ['bench', 'export', '--baseline', 'a', '--candidate', 'b', '--out', temp]
            stderr = io.StringIO()
            with patch.object(sys, 'argv', argv), contextlib.redirect_stderr(stderr), \
                 patch('bench.__main__.report.load') as load, patch('bench.__main__.export') as export:
                with self.assertRaises(SystemExit) as error:
                    main()
            self.assertEqual(error.exception.code, 2)
            self.assertIn('output directory already exists', stderr.getvalue())
            load.assert_not_called()
            export.assert_not_called()


if __name__ == '__main__':
    unittest.main()
