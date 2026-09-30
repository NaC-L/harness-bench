import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest


DRIVER = Path(__file__).resolve().parents[1] / 'bench/oauth_driver.py'


class OAuthDriverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hb-state-')
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name)

    def launch(self, state=None, expires=None, command=None, kind='pi'):
        claims = {'exp': expires if expires is not None else time.time() + 3600,
                  'https://api.openai.com/auth': {'chatgpt_account_id': 'test-account'}}
        payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip('=')
        token = 'header.' + payload + '.secret-signature'
        state_key = 'CODEX_HOME' if kind == 'codex' else 'PI_CODING_AGENT_DIR'
        env = {**os.environ, state_key: str(state or self.state),
               'OPENAI_CODEX_OAUTH_TOKEN': token}
        result = subprocess.run([sys.executable, str(DRIVER), '--kind', kind, '--',
                                 *(command or [sys.executable, '-c', 'raise SystemExit(7)'])],
                                env=env, capture_output=True, text=True, timeout=20)
        self.assertNotIn(token, result.stdout + result.stderr)
        return result

    def test_operator_state_is_never_written(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            result = self.launch(state)
            self.assertEqual(result.returncode, 2)
            self.assertFalse((state / 'auth.json').exists())

    def test_existing_credentials_are_not_overwritten_or_deleted(self):
        auth = self.state / 'auth.json'
        auth.write_text('operator credential')
        result = self.launch()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(auth.read_text(), 'operator credential')

    def test_expired_token_does_not_launch_or_persist(self):
        marker = self.state / 'launched'
        result = self.launch(expires=time.time() - 60, command=[sys.executable, '-c',
                            f'from pathlib import Path; Path({str(marker)!r}).touch()'])
        self.assertEqual(result.returncode, 2)
        self.assertFalse(marker.exists())
        self.assertFalse((self.state / 'auth.json').exists())

    def test_failed_child_preserves_exit_and_removes_credentials(self):
        for kind in ('pi', 'codex'):
            with self.subTest(kind=kind):
                result = self.launch(kind=kind)
                self.assertEqual(result.returncode, 7)
                self.assertFalse((self.state / 'auth.json').exists())


if __name__ == '__main__':
    unittest.main()
