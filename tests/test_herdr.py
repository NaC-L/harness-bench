import argparse
from contextlib import ExitStack, redirect_stdout, redirect_stderr
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from bench import herdr_driver as herdr


RUN_ID = 'fedcba98-7654-3210-fedc-ba9876543210'
SESSION = 'hb-' + RUN_ID


class Clock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class FakeProcess:
    def __init__(self, factory, command, options, *, output='', error='', code=0,
                 server=False, hanging=False):
        self.factory = factory
        self.command = command
        self.options = options
        self.output = output
        self.error = error
        self.returncode = None
        self.exit_code = code
        self.server = server
        self.hanging = hanging
        self.pid = len(factory.processes) + 1000
        self.wait_timeouts = []
        self.communicate_timeouts = []

    def poll(self):
        return self.returncode

    def communicate(self, timeout):
        self.communicate_timeouts.append(timeout)
        if self.hanging:
            self.factory.clock.advance(timeout)
            raise subprocess.TimeoutExpired(self.command, timeout)
        self.factory.clock.advance(0.01)
        self.returncode = self.exit_code
        return self.output, self.error

    def wait(self, timeout):
        self.wait_timeouts.append(timeout)
        return self.returncode


class ProcessFactory:
    def __init__(self, clock):
        self.clock = clock
        self.processes = []
        self.killed = []
        self.server = None
        self.existing = False
        self.server_exits = False
        self.startup_checks = 0
        self.ready_after = 0
        self.ready_text = 'status: running\nversion: 0.9.3\n'
        self.stopped_text = 'status: not running\nsocket: path\n'
        self.prompt_status = 'done'
        self.start_status = 'idle'
        self.prompt_hangs = False
        self.cleanup_hangs = False
        self.cleanup_raises = False
        self.prompt_error = None
        self.workspace = {'result': {'workspace': {'workspace_id': 'w47'},
                                     'root_pane': {'pane_id': 'w47:p9'}}}

    def __call__(self, command, **options):
        self.clock.advance(0.01)
        tail = command[3:]
        output, error, code, server, hanging = '', '', 0, False, False
        if tail == ['server']:
            server = True
        elif tail == ['status', 'server']:
            if self.server is None:
                code = 0
                output = self.ready_text if self.existing else self.stopped_text
            else:
                self.startup_checks += 1
                code = 0 if self.startup_checks > self.ready_after else 1
                output = self.ready_text if code == 0 else ''
        elif tail[:2] == ['workspace', 'create']:
            output = json.dumps(self.workspace)
        elif tail[:2] == ['agent', 'start']:
            output = json.dumps({'result': {'agent': {'agent_status': self.start_status}}})
        elif tail[:2] == ['agent', 'prompt']:
            output = json.dumps({'result': {'agent': {'agent_status': self.prompt_status}}})
            hanging = self.prompt_hangs
            if self.prompt_error:
                error = json.dumps(self.prompt_error)
                code = 1
        elif tail[:2] == ['agent', 'read']:
            output = 'answer line one\nanswer line two\n'
        elif tail[:2] == ['session', 'stop']:
            if self.cleanup_raises:
                raise OSError('mock cleanup unavailable')
            output = json.dumps({'result': {'session': SESSION, 'stopped': True}})
            hanging = self.cleanup_hangs
        else:
            raise AssertionError(f'unexpected command: {command}')
        proc = FakeProcess(self, command, options, output=output, error=error,
                           code=code, server=server, hanging=hanging)
        self.processes.append(proc)
        if server:
            self.server = proc
            if self.server_exits:
                proc.returncode = 0
        return proc

    def kill(self, proc):
        self.killed.append(proc)
        proc.returncode = -9

    def commands(self, prefix):
        return [proc.command for proc in self.processes if proc.command[3:5] == prefix]


class HerdrDriverTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.temp = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.root = Path(self.temp)
        self.workdir = self.root / 'work'
        self.workdir.mkdir()
        self.session_dir = self.root / 'artifacts' / 'sessions'
        self.clock = Clock()
        self.factory = ProcessFactory(self.clock)
        self.stack.enter_context(patch.object(herdr.subprocess, 'Popen', self.factory))
        self.stack.enter_context(patch.object(herdr, 'kill_tree', self.factory.kill))
        self.stack.enter_context(patch.object(herdr, 'group_options', return_value={'creationflags': 512}))
        self.stack.enter_context(patch.object(herdr.time, 'monotonic', self.clock.monotonic))
        self.stack.enter_context(patch.object(herdr.time, 'sleep', self.clock.advance))

    def arguments(self, timeout='60', extras=None):
        return ['--herdr', 'mock-herdr.exe', '--workdir', str(self.workdir),
                '--session-dir', str(self.session_dir), '--run-id', RUN_ID,
                '--timeout-sec', timeout, '--kind', 'omp', '--prompt', 'solve exactly once',
                '--', *(extras or ['--model', 'test-model', '--thinking', 'high'])]

    def invoke(self, timeout='60'):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = herdr.main(self.arguments(timeout))
        events = [json.loads(line) for line in stdout.getvalue().splitlines()]
        return code, events, stderr.getvalue()

    def test_driver_treats_documented_not_running_as_stopped(self):
        self.factory.stopped_text = 'status: not running\nsocket: path\n'
        code, _, stderr = self.invoke()
        self.assertEqual(code, 0, stderr)

    def test_driver_refuses_ambiguous_existing_named_session(self):
        self.factory.existing = True
        self.factory.ready_text = 'status: unknown\nsocket: path\n'
        code, _, stderr = self.invoke()
        self.assertEqual(code, 1)
        self.assertIn('ambiguous', stderr)
        self.assertFalse(any(proc.server for proc in self.factory.processes))


    def test_direct_script_parser_and_strict_uuid(self):
        args = herdr.parser().parse_args(self.arguments())
        self.assertEqual(args.session_name, SESSION)
        self.assertEqual(args.agent_args, ['--', '--model', 'test-model', '--thinking', 'high'])
        self.assertEqual(herdr.session_name(RUN_ID.upper()), SESSION)
        self.assertEqual(herdr.session_name(RUN_ID.replace('-', '')), SESSION)
        for value in ('default', '../default', RUN_ID + '\n', '{' + RUN_ID + '}', 'abc-def', '--current'):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                herdr.session_name(value)

    def test_positive_finite_budget_required(self):
        for value in ('0', '-1', 'nan', 'inf', 'invalid'):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                herdr.positive_timeout(value)
        self.assertEqual(herdr.positive_timeout('0.5'), 0.5)

    def test_exact_command_generation_and_prefix_isolation(self):
        code, events, stderr = self.invoke()
        self.assertEqual(code, 0, stderr)
        for proc in self.factory.processes:
            self.assertEqual(proc.command[:3], ['mock-herdr.exe', '--session', SESSION])
            self.assertNotIn('--current', proc.command)
            self.assertEqual(proc.options['cwd'], self.workdir.resolve())
            self.assertEqual(proc.options['creationflags'], 512)
            self.assertEqual(proc.options['stdin'], subprocess.DEVNULL)
        self.assertEqual(self.factory.server.command[3:], ['server'])
        workspace = self.factory.commands(['workspace', 'create'])[0]
        self.assertEqual(workspace[3:], ['workspace', 'create', '--cwd', str(self.workdir.resolve()),
                                       '--label', SESSION, '--no-focus'])
        start = self.factory.commands(['agent', 'start'])[0]
        self.assertEqual(start[3:], ['agent', 'start', 'bench', '--kind', 'omp', '--pane', 'w47:p9',
                                   '--timeout', '30000', '--', '--no-title', '--no-prewalk',
                                   '--session-dir', str(self.session_dir.resolve()),
                                   '--model', 'test-model', '--thinking', 'high'])
        prompt = self.factory.commands(['agent', 'prompt'])[0]
        self.assertEqual(prompt[3:8], ['agent', 'prompt', 'bench', 'solve exactly once', '--wait'])
        self.assertEqual(prompt[8], '--timeout')
        self.assertGreater(int(prompt[9]), 0)
        self.assertLess(int(prompt[9]), 60000)
        read = self.factory.commands(['agent', 'read'])[0]
        self.assertEqual(read[3:], ['agent', 'read', 'bench', '--source', 'recent-unwrapped', '--lines', '120'])
        stop = self.factory.commands(['session', 'stop'])[0]
        self.assertEqual(stop[3:], ['session', 'stop', SESSION, '--json'])
        ids = next(event for event in events if event['event'] == 'workspace.ids')
        self.assertEqual(ids['workspace_id'], 'w47')
        self.assertEqual(ids['pane_id'], 'w47:p9')
        self.assertIn(self.factory.server, self.factory.killed)

    def test_run_owned_empty_config_logs_and_inherited_selector_clear(self):
        inherited = {'HERDR_PANE_ID': 'user:pane', 'HERDR_SESSION': 'default'}
        original = {key: os.environ.get(key) for key in inherited}
        with patch.dict(os.environ, inherited):
            code, _, stderr = self.invoke()
        self.assertEqual(code, 0, stderr)
        expected = self.session_dir.parent / f'{SESSION}.config.toml'
        self.assertEqual(expected.read_text(encoding='utf-8'), '')
        self.assertTrue((self.session_dir.parent / f'{SESSION}.server.stdout.log').is_file())
        self.assertTrue((self.session_dir.parent / f'{SESSION}.server.stderr.log').is_file())
        self.assertEqual(list(self.session_dir.iterdir()), [])
        for proc in self.factory.processes:
            env = proc.options['env']
            self.assertEqual(env['HERDR_CONFIG_PATH'], str(expected.resolve()))
            self.assertNotIn('HERDR_PANE_ID', env)
            self.assertNotIn('HERDR_SESSION', env)
        self.assertEqual({key: os.environ.get(key) for key in inherited}, original)

    def test_workspace_response_id_parsing_and_missing_ids(self):
        self.assertEqual(herdr.workspace_ids(self.factory.workspace), ('w47', 'w47:p9'))
        for response in ({}, {'result': {}}, {'result': {'workspace': None}},
                         {'result': {'workspace': {'workspace_id': ''}, 'root_pane': {'pane_id': 'x'}}}):
            with self.subTest(response=response), self.assertRaises(herdr.DriverError):
                herdr.workspace_ids(response)

    def test_missing_pane_does_not_launch_agent_and_cleans_server(self):
        self.factory.workspace = {'result': {'workspace': {'workspace_id': 'w47'}}}
        code, _, stderr = self.invoke()
        self.assertEqual(code, 1)
        self.assertIn('root pane IDs', stderr)
        self.assertFalse(self.factory.commands(['agent', 'start']))
        self.assertIn(self.factory.server, self.factory.killed)

    def test_blocked_unknown_and_working_turns_fail_without_retry(self):
        for status in ('blocked', 'unknown', 'working'):
            with self.subTest(status=status):
                # Each run gets fresh artifacts and subprocess state.
                self.session_dir = self.root / status / 'sessions'
                self.factory.server = None
                self.factory.processes.clear()
                self.factory.prompt_status = status
                code, _, stderr = self.invoke()
                self.assertEqual(code, 1)
                self.assertIn(status, stderr)
                self.assertEqual(len(self.factory.commands(['agent', 'prompt'])), 1)
                self.assertFalse(self.factory.commands(['agent', 'read']))
                self.assertIn(self.factory.server, self.factory.killed)

    def test_blocked_start_does_not_submit_prompt(self):
        self.factory.start_status = 'blocked'
        code, _, stderr = self.invoke()
        self.assertEqual(code, 1)
        self.assertIn('blocked', stderr)
        self.assertFalse(self.factory.commands(['agent', 'prompt']))
        self.assertIn(self.factory.server, self.factory.killed)

    def test_idle_turn_is_accepted_and_read_preserved(self):
        self.factory.prompt_status = 'idle'
        code, events, stderr = self.invoke()
        self.assertEqual(code, 0, stderr)
        read = next(event for event in events if event['event'] == 'agent.read')
        self.assertEqual(read['text'], 'answer line one\nanswer line two\n')
        raw = next(event for event in events if event['event'] == 'workspace.create')
        self.assertEqual(raw['response'], self.factory.workspace)

    def test_startup_retries_only_before_prompt(self):
        self.factory.ready_after = 2
        code, _, stderr = self.invoke()
        self.assertEqual(code, 0, stderr)
        self.assertEqual(self.factory.startup_checks, 3)
        self.assertEqual(len(self.factory.commands(['agent', 'prompt'])), 1)

    def test_startup_is_bounded_and_never_launches_agents(self):
        self.factory.ready_after = 10000
        code, _, stderr = self.invoke('0.3')
        self.assertEqual(code, 1)
        self.assertIn('budget exhausted', stderr)
        self.assertLessEqual(self.clock.now, 0.31)
        self.assertFalse(self.factory.commands(['agent', 'start']))
        self.assertIn(self.factory.server, self.factory.killed)
        self.assertFalse(self.factory.commands(['session', 'stop']))

    def test_successful_status_exit_without_running_text_is_not_ready(self):
        self.factory.ready_text = 'status: starting\n'
        code, _, _ = self.invoke('0.3')
        self.assertEqual(code, 1)
        self.assertFalse(self.factory.commands(['agent', 'start']))
        self.assertIn(self.factory.server, self.factory.killed)

    def test_existing_session_is_not_started_or_stopped(self):
        self.factory.existing = True
        code, _, stderr = self.invoke()
        self.assertEqual(code, 1)
        self.assertIn('refusing to attach', stderr)
        self.assertIsNone(self.factory.server)
        self.assertFalse(self.factory.commands(['session', 'stop']))
        self.assertFalse(self.factory.killed)

    def test_daemonized_foreground_exit_fails_closed(self):
        self.factory.server_exits = True
        code, _, stderr = self.invoke()
        self.assertEqual(code, 1)
        self.assertIn('daemonized/unowned', stderr)
        self.assertFalse(self.factory.commands(['agent', 'start']))
        self.assertFalse(self.factory.commands(['session', 'stop']))

    def test_prompt_timeout_never_submits_twice_and_cleans_tree(self):
        self.factory.prompt_hangs = True
        code, _, stderr = self.invoke('0.5')
        self.assertEqual(code, 1)
        self.assertIn('prompt will not be retried', stderr)
        self.assertEqual(len(self.factory.commands(['agent', 'prompt'])), 1)
        self.assertFalse(self.factory.commands(['agent', 'read']))
        prompt_proc = next(proc for proc in self.factory.processes if proc.command[3:5] == ['agent', 'prompt'])
        self.assertIn(prompt_proc, self.factory.killed)
        self.assertIn(self.factory.server, self.factory.killed)
        self.assertTrue(all(timeout > 0 for timeout in prompt_proc.communicate_timeouts))
        self.assertLess(self.clock.now, 0.6)

    def test_cli_prompt_error_never_retried_and_diagnostics_redact_tokens(self):
        self.factory.prompt_error = {'error': {'code': 'agent_prompt_stalled',
                                             'auth_token': 'mock-sensitive-value'}}
        code, events, stderr = self.invoke()
        self.assertEqual(code, 1)
        self.assertIn('agent_prompt_stalled', stderr)
        self.assertNotIn('mock-sensitive-value', stderr)
        self.assertNotIn('mock-sensitive-value', json.dumps(events))
        self.assertEqual(len(self.factory.commands(['agent', 'prompt'])), 1)
        self.assertIn(self.factory.server, self.factory.killed)

    def test_cleanup_timeout_kills_cleanup_child_and_owned_server(self):
        self.factory.cleanup_hangs = True
        code, _, stderr = self.invoke()
        self.assertEqual(code, 0, stderr)
        cleanup = next(proc for proc in self.factory.processes if proc.command[3:5] == ['session', 'stop'])
        self.assertEqual(cleanup.communicate_timeouts, [3.0])
        self.assertIn(cleanup, self.factory.killed)
        self.assertIn(self.factory.server, self.factory.killed)

    def test_cleanup_spawn_error_still_kills_owned_server(self):
        self.factory.cleanup_raises = True
        code, _, stderr = self.invoke()
        self.assertEqual(code, 0, stderr)
        self.assertIn('terminating owned process tree', stderr)
        self.assertIn(self.factory.server, self.factory.killed)

    def test_reused_artifact_path_is_not_overwritten(self):
        self.session_dir.parent.mkdir(parents=True)
        config = self.session_dir.parent / f'{SESSION}.config.toml'
        config.write_text('preserve this run-owned fixture', encoding='utf-8')
        code, _, _ = self.invoke()
        self.assertEqual(code, 1)
        self.assertEqual(config.read_text(encoding='utf-8'), 'preserve this run-owned fixture')
        self.assertFalse(self.factory.processes)

    def test_missing_workdir_has_no_server_side_effects(self):
        self.workdir.rmdir()
        code, _, stderr = self.invoke()
        self.assertEqual(code, 1)
        self.assertIn('existing directory', stderr)
        self.assertFalse(self.factory.processes)


if __name__ == '__main__':
    unittest.main()
