import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from bench import report
from bench.export import export, sanitize
from bench.manifest import load_manifest
from bench.runner import run_matrix, runtime_values
from tests import test_runner


class SanitizeTests(unittest.TestCase):
    def test_every_spelling_of_a_root_is_replaced(self):
        # CI failures: Windows TEMP given as 8.3 short name but resolved paths are long,
        # and macOS /var/folders is an alias of /private/var/folders.
        aliases = {r'C:\Users\RUNNER~1\AppData\Local\Temp': r'C:\Users\runneradmin\AppData\Local\Temp',
                   '/var/folders/ab/T': '/private/var/folders/ab/T'}
        with patch('bench.export.os.path.realpath', side_effect=lambda p: aliases.get(p, p)), \
             patch('bench.export.os.name', 'nt'):
            windows = sanitize(r'C:\Users\runneradmin\AppData\Local\Temp\x and C:\Users\RUNNER~1\AppData\Local\Temp\y',
                               benchmark_dir=r'D:\a\bench', home=r'C:\Users\runneradmin',
                               temp=r'C:\Users\RUNNER~1\AppData\Local\Temp')
        self.assertEqual(windows, r'{temp}\x and {temp}\y')
        with patch('bench.export.os.path.realpath', side_effect=lambda p: aliases.get(p, p)), \
             patch('bench.export.os.name', 'posix'):
            mac = sanitize('/private/var/folders/ab/T/x /var/folders/ab/T/y', benchmark_dir='/Users/r/bench',
                           home='/Users/r', temp='/var/folders/ab/T')
        self.assertEqual(mac, '{temp}/x {temp}/y')

    def test_nested_paths_both_separator_styles_and_escaped_json(self):
        roots = {'benchmark_dir': r'C:\Users\Private\Desktop\benchmark',
                 'home': r'C:\Users\Private', 'temp': r'C:\Users\Private\AppData\Local\Temp'}
        value = {roots['home'] + r'\.omp\config.yml': [
            roots['benchmark_dir'] + r'\overlay.yml', 'C:/Users/Private/Desktop/benchmark/task',
            roots['temp'] + r'\work', 'C:/Users/Private/AppData/Local/Temp/work',
            roots['home'] + r'\.omp', 1, None, True,
            {'command': json.dumps(roots['temp'] + r'\escaped')} ]}
        clean = sanitize(value, **roots)
        self.assertEqual(list(clean), [r'~\.omp\config.yml'])
        values = next(iter(clean.values()))
        self.assertEqual(values[:5], [r'{benchmark_dir}\overlay.yml', '{benchmark_dir}/task',
                                     r'{temp}\work', '{temp}/work', r'~\.omp'])
        self.assertEqual(values[5:8], [1, None, True])
        self.assertEqual(json.loads(values[8]['command']), r'{temp}\escaped')
        for root in roots.values():
            self.assertNotIn(root, repr(clean))
        self.assertEqual(sanitize(value, **roots), clean)
        self.assertEqual(sanitize(clean, **roots), clean)

    @unittest.skipUnless(os.name == 'nt', 'Windows case-insensitive path matching')
    def test_windows_paths_are_case_insensitive(self):
        self.assertEqual(sanitize('c:/users/private/desktop/bench/overlay',
                                  benchmark_dir=r'C:\Users\Private\Desktop\Bench',
                                  home=r'C:\Users\Private', temp=r'C:\Temp'), '{benchmark_dir}/overlay')


class ExportTests(unittest.TestCase):
    def setUp(self):
        test_runner.RunnerTests.setUp(self)
        self.results = self.root / 'results'
        harnesses = []
        for name in ('base', 'cand'):
            h = test_runner.RunnerTests.harness(self, 'solve')
            h.name = name
            h.command[1] = '{benchmark_dir}/tests/fixtures/fake_harness.py'
            harnesses.append(h)
        with contextlib.redirect_stdout(io.StringIO()):
            self.rows = run_matrix([self.task], harnesses, self.results)
        self.assertTrue(all(row['passed'] for row in self.rows))
        self.out = self.root / 'bundle'
        local = str(Path.home()) + '/private/config; ' + tempfile.gettempdir() + '/private/work'
        for row in self.rows:
            artifact = Path(row['artifact_dir'])
            (artifact / 'sessions' / 'session.jsonl').write_text(json.dumps({'path': local}), encoding='utf-8')
            (artifact / 'stderr.txt').write_text(local, encoding='utf-8')
            row['context_hashes'] = {str(Path.home() / '.omp' / 'config.yml'): 'hash'}
            row['metrics']['session_files'] = [str(artifact / 'sessions' / 'session.jsonl')]
            with (artifact / 'patch.diff').open('a', encoding='utf-8') as stream:
                stream.write('\n' + local)
        self.unrelated = dict(self.rows[0], harness='unrelated', run_id='not-exported')

    def test_default_export_is_portable_and_excludes_transcripts(self):
        export(self.rows + [self.unrelated], self.results, self.out, 'base', 'cand', min_trials=1)
        self.assertTrue((self.out / 'REPORT.md').exists())
        self.assertTrue((self.out / 'manifest.json').exists())
        clean = report.load(self.out / 'runs.jsonl')
        self.assertEqual(len(clean), 2)
        self.assertEqual({row['harness'] for row in clean}, {'base', 'cand'})
        self.assertFalse((self.out / 'runs' / 'not-exported').exists())
        for row in clean:
            self.assertIsNone(row['workdir'])
            self.assertEqual(row['artifact_dir'], 'runs/' + row['run_id'])
            artifact = self.out / row['artifact_dir']
            for name in ('patch.diff', 'check.txt', 'check-visible.txt'):
                self.assertTrue((artifact / name).exists())
            for name in ('sessions', 'stdout.jsonl', 'stderr.txt', 'run.json'):
                self.assertFalse((artifact / name).exists())
        for path in self.out.rglob('*'):
            if path.is_file():
                text = path.read_text(encoding='utf-8')
                for root in (str(Path.home()), tempfile.gettempdir()):
                    self.assertNotIn(root.lower(), text.lower())
                    self.assertNotIn(root.replace('\\', '/').lower(), text.lower())
                self.assertNotIn('AppData', text)
        self.assertEqual(report.compare(clean, 'base', 'cand', min_trials=1)['verdict'], 'inconclusive')
        self.assertIn('token usage unknown', report.compare(clean, 'base', 'cand', min_trials=1)['reasons'])
        markdown = (self.out / 'REPORT.md').read_text(encoding='utf-8')
        self.assertIn('works on an exported bundle without model access', markdown)
        self.assertIn(f'--results results/{self.out.name}-rerun run', markdown)
        self.assertNotIn('{temp}', markdown.split('## Reproduce')[1])
        self.assertIn('compare --baseline base --candidate cand', markdown)
        self.assertEqual(load_manifest(self.out)['schema_version'], 1)

    def test_include_transcripts_sanitizes_copied_text(self):
        export(self.rows, self.results, self.out, 'base', 'cand', min_trials=1, include_transcripts=True)
        for row in self.rows:
            artifact = self.out / 'runs' / row['run_id']
            self.assertTrue((artifact / 'stdout.jsonl').exists())
            self.assertTrue((artifact / 'stderr.txt').exists())
            session = artifact / 'sessions' / 'session.jsonl'
            self.assertTrue(session.exists())
            text = session.read_text(encoding='utf-8')
            self.assertNotIn(str(Path.home()).replace('\\', '\\\\'), text)
            self.assertNotIn('AppData', text)
            self.assertIn('~', text)
            self.assertIn('{temp}', text)
            json.loads(text)

    def test_existing_out_is_refused_without_overwriting(self):
        self.out.mkdir()
        sentinel = self.out / 'existing.txt'
        sentinel.write_text('keep', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'output directory already exists'):
            export(self.rows, self.results, self.out, 'base', 'cand', min_trials=1)
        self.assertEqual(sentinel.read_text(encoding='utf-8'), 'keep')
        self.assertEqual(list(self.out.iterdir()), [sentinel])

    def test_manifest_absent_and_missing_optional_artifacts(self):
        (self.results / 'manifest.json').unlink()
        for row in self.rows:
            (Path(row['artifact_dir']) / 'check-visible.txt').unlink()
        export(self.rows, self.results, self.out, 'base', 'cand', min_trials=1)
        self.assertFalse((self.out / 'manifest.json').exists())
        self.assertIn('No manifest.json; setup not recorded.', (self.out / 'REPORT.md').read_text(encoding='utf-8'))
        self.assertTrue(all((self.out / 'runs' / row['run_id'] / 'patch.diff').exists() for row in self.rows))

    def test_invalid_comparison_does_not_create_out(self):
        with self.assertRaisesRegex(ValueError, 'no runs for harness: missing'):
            export(self.rows, self.results, self.out, 'base', 'missing', min_trials=1)
        self.assertFalse(self.out.exists())
