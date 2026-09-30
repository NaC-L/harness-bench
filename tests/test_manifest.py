import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from bench.manifest import load_manifest, record_invocation
from bench.runner import Harness
from bench.tasks import Task


class ManifestTests(unittest.TestCase):
    def test_file_capture_limits_and_repo_boundary(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / 'benchmark'
            repo.mkdir()
            files = {'text.txt': b'overlay\n', 'limit.txt': b'x' * (64 * 1024),
                     'large.txt': b'x' * (64 * 1024 + 1), 'binary.bin': b'\xff',
                     'nul.bin': b'abc\0def'}
            for name, contents in files.items():
                (repo / name).write_bytes(contents)
            (root / 'outside.txt').write_text('not captured', encoding='utf-8')
            h = Harness('fake', 'none', ['{benchmark_dir}/' + name for name in files] +
                        ['{benchmark_dir}/../outside.txt', '{benchmark_dir}/missing', str(root / 'outside.txt')],
                        [], {}, 'hash')
            task = Task('tiny', repo, 'tiny', 'test', 'Fix', 30, [])
            results = root / 'results'
            with patch('bench.runner.runtime_values', return_value={'benchmark_dir': str(repo)}), \
                 patch('bench.manifest.subprocess.run', side_effect=FileNotFoundError('no node')):
                record_invocation(results, [h], [task], trials=2, jobs=3, alternate_order=False,
                                  timeout=None, versions={'fake': 'v1'}, config=root / 'external.toml')
            invocation = load_manifest(results)['invocations'][0]
            self.assertIsNone(invocation['node'])
            self.assertEqual(invocation['config'], str((root / 'external.toml').resolve()))
            captured = invocation['harnesses']['fake']['files']
            self.assertEqual(set(captured), set(files))
            self.assertEqual(captured['text.txt']['contents'], 'overlay\n')
            self.assertEqual(len(captured['limit.txt']['contents']), 64 * 1024)
            for name in ('large.txt', 'binary.bin', 'nul.bin'):
                self.assertIsNone(captured[name]['contents'])
            for name, contents in files.items():
                self.assertEqual(captured[name]['sha256'], hashlib.sha256(contents).hexdigest())

    def test_load_missing_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertIsNone(load_manifest(Path(temp)))
