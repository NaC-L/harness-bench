import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bench import report
from bench.environment import ancestor_context
from bench.manifest import load_manifest, record_invocation
from bench.runner import Harness, load_harnesses, run_one
from bench.tasks import load_task
from tests.test_report_compare import arm

# Child records what it was launched with, so the test observes the real environment.
PROBE = ("import json,os,sys,pathlib; s=os.environ.get('PI_CODING_AGENT_DIR'); "
         "pathlib.Path(sys.argv[1]).write_text(json.dumps({'state': s, 'profile': os.environ.get('OMP_PROFILE'), "
         "'secret': os.environ.get('SECRET_X'), 'files': sorted(os.listdir(s)) if s else None}))")


class IsolationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        d = self.root / 'tiny'
        for p in ('repo/src', 'repo/test', 'hidden_tests', 'solution'):
            (d / p).mkdir(parents=True)
        (d / 'task.toml').write_text('id="tiny"\ntimeout_sec=30\ncheck=["node","--test"]\n')
        (d / 'prompt.md').write_text('Fix value.')
        (d / 'repo/src/value.js').write_text('module.exports = 0;\n')
        (d / 'repo/test/v.test.js').write_text(
            "const t=require('node:test');const a=require('node:assert/strict');"
            "t('value',()=>a.equal(require('../src/value'),0));\n")
        self.task = load_task(d)
        self.template = self.root / 'template'
        self.template.mkdir()
        (self.template / 'config.yml').write_bytes(b'memory:\n  backend: "off"\n')
        self.seen = self.root / 'seen.json'

    def harness(self, env_commands=None):
        return Harness('iso', 'omp', [sys.executable, '-c', PROBE, str(self.seen)], [sys.executable, '--version'],
                       {}, 'hash', str(self.template),
                       env_commands if env_commands is not None else
                       {'SECRET_X': [sys.executable, '-c', "print('s3cret' + '-token')"]})

    def run_isolated(self, h):
        with patch.dict(os.environ, {'OMP_PROFILE': 'personal', 'PI_CODING_AGENT_DIR': str(self.root / 'personal')}), \
             patch('bench.sessions.collect', return_value={'session_files': []}):
            return run_one(self.task, h, self.root / 'results')

    def test_run_uses_fresh_state_copy_without_profile_and_never_persists_secret(self):
        row = self.run_isolated(self.harness())
        seen = json.loads(self.seen.read_text())
        self.assertNotEqual(Path(seen['state']), self.root / 'personal')
        self.assertEqual(seen['files'], ['config.yml'])
        self.assertIsNone(seen['profile'])
        self.assertEqual(seen['secret'], 's3cret-token')
        self.assertFalse(Path(seen['state']).exists(), 'per-run state must be deleted')
        self.assertTrue(row['isolated_state'])
        self.assertEqual(list(row['context_hashes']), ['{state}/config.yml'])
        for path in Path(row['artifact_dir']).rglob('*'):
            if path.is_file():
                self.assertNotIn('s3cret-token', path.read_text(encoding='utf-8', errors='replace'))

    def test_failed_env_command_fails_run_without_echoing_output(self):
        h = self.harness({'SECRET_X': [sys.executable, '-c', "print('leaky'); raise SystemExit(1)"]})
        row = self.run_isolated(h)
        self.assertFalse(row['passed'])
        self.assertIn('ValueError: env_commands.SECRET_X failed (exit 1)', row['errors'])
        self.assertNotIn('leaky', json.dumps(row))
        self.assertFalse(self.seen.exists(), 'agent must not start without its environment')

    def test_config_validation(self):
        config = self.root / 'h.toml'
        config.write_text(f'[harnesses.x]\nkind="none"\ncommand=["x"]\nstate_template={json.dumps(str(self.template))}\n')
        with self.assertRaisesRegex(ValueError, 'not supported'):
            load_harnesses(config)
        config.write_text('[harnesses.x]\nkind="omp"\ncommand=["x"]\nstate_template="missing-dir"\n')
        with self.assertRaisesRegex(ValueError, 'not a directory'):
            load_harnesses(config)

    def test_manifest_records_template_files_and_env_command_argv_only(self):
        with patch('bench.runner.runtime_values', return_value={'benchmark_dir': str(self.root), 'python': sys.executable}):
            record_invocation(self.root / 'res', [self.harness()], [self.task], trials=1, jobs=1,
                              alternate_order=False, timeout=None, versions={'iso': 'v'})
        entry = load_manifest(self.root / 'res')['invocations'][0]['harnesses']['iso']
        self.assertEqual(entry['files']['template/config.yml']['contents'], 'memory:\n  backend: "off"\n')
        self.assertEqual(entry['env_commands']['SECRET_X'][0], sys.executable)
        self.assertNotIn('s3cret-token', json.dumps(entry))

    def test_ancestor_context_ignores_empty_dirs_and_home(self):
        work = self.root / 'a' / 'b' / 'work'
        work.mkdir(parents=True)
        (self.root / 'a' / '.omp').mkdir()
        root = self.root.resolve()  # the function reports resolved paths (macOS /private/var, Windows long names)

        def inside(found):  # the temp root itself sits under real directories of this machine
            return [p for p in found if Path(p).is_relative_to(root)]
        self.assertEqual(inside(ancestor_context(work, home=self.root / 'nohome')), [])
        (self.root / 'a' / 'AGENTS.md').write_text('x')
        self.assertEqual(inside(ancestor_context(work, home=self.root / 'nohome')), [str(root / 'a' / 'AGENTS.md')])
        self.assertEqual(inside(ancestor_context(work, home=self.root / 'a')), [])


class IsolationWarningTests(unittest.TestCase):
    def test_compare_warns_about_shared_operator_state_and_ancestor_context(self):
        rows = arm('base') + arm('cand')
        warnings = report.compare(rows, 'base', 'cand')['warnings']
        self.assertIn("operator state not isolated for 18 runs: the harness may have read the operator's "
                      "personal instructions, settings and MCP servers", warnings)
        for r in rows:
            r['isolated_state'] = True
        rows[0]['ancestor_context'] = ['C:/x/AGENTS.md']
        warnings = report.compare(rows, 'base', 'cand')['warnings']
        self.assertFalse(any('not isolated' in w for w in warnings))
        self.assertIn('project context files above the workdir for 1 runs', warnings)


if __name__ == '__main__':
    unittest.main()
