import json
import sys
import tempfile
import unittest
from pathlib import Path

from bench.capture import DUMMY_ANTHROPIC, breakdown, capture, render
from bench.runner import Harness
from bench.tasks import load_task

# Minimal Anthropic client: finds its endpoint the way OMP (env) or Pi (models.json) does,
# sends one request carrying what it was launched with, and consumes the streamed reply.
CLIENT = r'''
import json, os, pathlib, sys, urllib.request
state = os.environ.get('PI_CODING_AGENT_DIR')
models = pathlib.Path(state, 'models.json') if state else None
if sys.argv[1] == 'pi':
    base = json.loads(models.read_text())['providers']['anthropic']['baseUrl']
else:
    base = os.environ['ANTHROPIC_BASE_URL']
body = {'system': [{'type': 'text', 'text': '# Role\nbe brief\n# Tools\nuse read'}],
        'tools': [{'name': 'read', 'description': 'Read a file.', 'input_schema': {'type': 'object'}}],
        'messages': [{'role': 'user', 'content': [{'type': 'text', 'text': sys.argv[2]}]}],
        'token': os.environ.get('ANTHROPIC_OAUTH_TOKEN'),
        'models_json': json.loads(models.read_text()) if models and models.is_file() else None}
req = urllib.request.Request(base + '/v1/messages', json.dumps(body).encode(), {'content-type': 'application/json'})
assert b'message_stop' in urllib.request.urlopen(req, timeout=30).read()
'''


class CaptureTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        d = self.root / 'tiny'
        for p in ('repo/src', 'hidden_tests', 'solution'):
            (d / p).mkdir(parents=True)
        (d / 'task.toml').write_text('id="tiny"\ntimeout_sec=30\ncheck=["node","--test"]\n')
        (d / 'prompt.md').write_text('Fix value.')
        (d / 'repo/src/value.js').write_text('module.exports = 0;\n')
        self.task = load_task(d)
        self.template = self.root / 'template'
        self.template.mkdir()
        (self.template / 'models.json').write_text('{"providers": {"other": {"baseUrl": "x"}}}')
        self.ran = self.root / 'env-command-ran'

    def harness(self, kind, mode, state=True):
        marker = [sys.executable, '-c', f"open({str(self.ran)!r}, 'w').write('ran'); print('real-token')"]
        return Harness('arm', kind, [sys.executable, '-c', CLIENT, mode, '{prompt}'], [sys.executable, '--version'],
                       {}, 'hash', str(self.template) if state else None, {'ANTHROPIC_OAUTH_TOKEN': marker})

    def test_records_first_request_with_dummy_credential_and_never_runs_env_commands(self):
        result = capture(self.task, self.harness('omp', 'env'), timeout=60)
        body = result['body']
        self.assertEqual(body['messages'][0]['content'][0]['text'], 'Fix value.')
        self.assertEqual(body['token'], DUMMY_ANTHROPIC)
        self.assertFalse(self.ran.exists())
        self.assertEqual(result['requests_seen'], 1)

    def test_pi_is_routed_through_its_state_models_json_without_dropping_entries(self):
        body = capture(self.task, self.harness('pi', 'pi'), timeout=60)['body']
        self.assertEqual(body['models_json']['providers']['other'], {'baseUrl': 'x'})
        self.assertTrue(body['models_json']['providers']['anthropic']['baseUrl'].startswith('http://127.0.0.1:'))
        self.assertEqual(json.loads((self.template / 'models.json').read_text())['providers'].keys(), {'other'})

    def test_pi_without_isolated_state_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'state_template'):
            capture(self.task, self.harness('pi', 'pi', state=False), timeout=60)

    def test_arm_that_never_calls_the_model_is_an_error(self):
        h = Harness('silent', 'omp', [sys.executable, '-c', 'pass'], [sys.executable, '--version'], {}, 'hash')
        with self.assertRaisesRegex(RuntimeError, 'no model request'):
            capture(self.task, h, timeout=60)

    def test_breakdown_names_sections_tools_and_messages(self):
        body = {'system': [{'type': 'text', 'text': 'intro\n# A\naa\n<critical>\nx\n# B\nb\n<critical>\ny'}],
                'tools': [{'name': 'read', 'description': 'abc', 'input_schema': {'type': 'object'}}],
                'messages': [{'role': 'user', 'content': 'hello'}]}
        parts = dict(breakdown(body))
        self.assertEqual(parts['system[0] (preamble)'], len('intro'))
        self.assertEqual(parts['system[0] # A'], len('# A\naa'))
        self.assertIn('system[0] <critical> (2)', parts)
        self.assertEqual(parts['tool read description'], 3)
        self.assertEqual(parts['tool read schema'], len('{"type":"object"}'))
        self.assertEqual(parts['message[0] user'], 5)
        self.assertEqual(sum(parts.values()), sum(n for _, n in breakdown(body)))

    def test_render_reports_totals_relative_to_first_arm(self):
        small = {'system': 'ab', 'messages': []}
        large = {'system': 'abcd', 'messages': []}
        table = render([{'harness': 'a', 'body': small}, {'harness': 'b', 'body': large}])
        self.assertIn('+100.0%', table)
        self.assertIn('Characters, not tokens', table)


if __name__ == '__main__':
    unittest.main()
