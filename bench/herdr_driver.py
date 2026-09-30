"""Run one OMP turn in an exclusively owned, foreground Herdr session."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bench.process import group_options, kill_tree


class DriverError(RuntimeError):
    pass


_SECRET_KEYS = {'token', 'auth_token', 'access_token', 'refresh_token', 'api_key',
                'apikey', 'authorization', 'password', 'secret', 'credential'}


def _safe(value):
    if isinstance(value, dict):
        return {key: ('[redacted]' if key.lower().replace('-', '_') in _SECRET_KEYS
                      else _safe(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [_safe(item) for item in value]
    return value


def _event(event, **fields):
    print(json.dumps(_safe({'event': event, **fields}), ensure_ascii=True), flush=True)


def _diagnostic(event, text):
    if not text.strip():
        return
    try:
        print(json.dumps(_safe(json.loads(text))), file=sys.stderr, flush=True)
    except ValueError:
        print(f'{event}: Herdr emitted non-JSON CLI diagnostics', file=sys.stderr, flush=True)


def _running(text):
    # Herdr 0.9.3 status server prints text, not an API JSON envelope.
    return any(re.fullmatch(r'status:\s*running', line.strip()) for line in text.splitlines())


def _stopped(text):
    return any(re.fullmatch(r'status:\s*(?:not running|stopped)', line.strip())
               for line in text.splitlines())


def session_name(value):
    if not re.fullmatch(r'(?:[0-9a-fA-F]{32}|[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})', value):
        raise argparse.ArgumentTypeError('run-id must be a UUID (hex digits and canonical dashes only)')
    return 'hb-' + str(uuid.UUID(value))


def positive_timeout(value):
    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError('timeout-sec must be a positive finite number') from exc
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError('timeout-sec must be a positive finite number')
    return number


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('--herdr', required=True)
    result.add_argument('--workdir', required=True, type=Path)
    result.add_argument('--session-dir', required=True, type=Path)
    result.add_argument('--run-id', required=True, type=session_name, dest='session_name')
    result.add_argument('--timeout-sec', required=True, type=positive_timeout)
    result.add_argument('--kind', choices=['omp'], required=True)
    result.add_argument('--prompt', required=True)
    result.add_argument('agent_args', nargs=argparse.REMAINDER)
    return result


def _json_response(text, label):
    try:
        response = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise DriverError(f'{label}: expected a JSON response') from exc
    if not isinstance(response, dict) or response.get('error') is not None:
        raise DriverError(f'{label}: invalid or error response')
    return response


def workspace_ids(response):
    try:
        result = response['result']
        workspace = result['workspace']['workspace_id']
        pane = result['root_pane']['pane_id']
    except (KeyError, TypeError) as exc:
        raise DriverError('workspace create did not return workspace and root pane IDs') from exc
    if not all(isinstance(value, str) and value for value in (workspace, pane)):
        raise DriverError('workspace create returned invalid IDs')
    return workspace, pane


def agent_status(response):
    try:
        status = response['result']['agent']['agent_status']
    except (KeyError, TypeError) as exc:
        raise DriverError('agent response did not return a lifecycle status') from exc
    if status not in ('idle', 'done'):
        raise DriverError(f'agent did not settle successfully (status {status!r})')
    return status


class Driver:
    STARTUP_SEC = 15.0
    COMMAND_SEC = 5.0
    POLL_SEC = 0.1

    def __init__(self, args):
        self.args = args
        self.prefix = [args.herdr, '--session', args.session_name]
        self.deadline = time.monotonic() + args.timeout_sec
        self.server = None
        self.ready_owned = False
        self.env = os.environ.copy()
        for key in list(self.env):
            if key.upper() in ('HERDR_PANE_ID', 'HERDR_SESSION'):
                del self.env[key]
        self.args.workdir = args.workdir.resolve()
        self.args.session_dir = args.session_dir.resolve()

    def remaining(self, deadline=None):
        remaining = min(self.deadline, deadline or self.deadline) - time.monotonic()
        if remaining <= 0:
            raise DriverError('Herdr run budget exhausted; prompt will not be retried')
        return remaining

    def alive(self):
        if self.server is not None and self.server.poll() is not None:
            raise DriverError('owned foreground Herdr server exited; daemonized/unowned servers are unsupported')

    def command(self, arguments, *, limit=None, deadline=None):
        self.alive()
        stop = min(self.deadline, deadline or self.deadline,
                   time.monotonic() + (limit if limit is not None else self.COMMAND_SEC))
        self.remaining(stop)
        proc = subprocess.Popen(self.prefix + arguments, cwd=self.args.workdir,
                                env=self.env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, encoding='utf-8', errors='replace', **group_options())
        try:
            while True:
                self.alive()
                try:
                    stdout, stderr = proc.communicate(timeout=min(0.25, self.remaining(stop)))
                    self.alive()
                    return proc.returncode, stdout, stderr
                except subprocess.TimeoutExpired:
                    self.remaining(stop)
        finally:
            if proc.poll() is None:
                kill_tree(proc)

    def response(self, event, arguments, *, limit=None):
        code, stdout, stderr = self.command(arguments, limit=limit)
        # Do not copy arbitrary malformed CLI output, which could contain
        # environment/credential details.
        _diagnostic(event, stderr)
        if code:
            if stdout.strip():
                try:
                    _event(event, response=json.loads(stdout), exit_code=code)
                except ValueError:
                    pass
            raise DriverError(f'{event}: Herdr CLI exited with status {code}')
        response = _json_response(stdout, event)
        _event(event, response=response)
        return response

    def ready(self):
        stop = min(self.deadline, time.monotonic() + self.STARTUP_SEC)
        while True:
            self.alive()
            code, stdout, _ = self.command(['status', 'server'], deadline=stop)
            if code == 0 and _running(stdout):
                _event('server.ready', session=self.args.session_name)
                self.ready_owned = True
                self.alive()
                return
            time.sleep(min(self.POLL_SEC, self.remaining(stop)))

    def cleanup(self):
        if self.server is None:
            return
        try:
            if self.ready_owned and self.server.poll() is None:
                # Graceful named stop lets Herdr close ConPTY panes itself.
                # Use both the exact prefix and explicit newly owned name.
                proc = subprocess.Popen(
                    self.prefix + ['session', 'stop', self.args.session_name, '--json'],
                    cwd=self.args.workdir, env=self.env, stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, encoding='utf-8', errors='replace', **group_options())
                try:
                    stdout, stderr = proc.communicate(timeout=3.0)
                    _diagnostic('server.cleanup', stderr)
                    if stdout.strip():
                        try:
                            _event('server.cleanup', response=json.loads(stdout), exit_code=proc.returncode)
                        except ValueError:
                            pass
                finally:
                    if proc.poll() is None:
                        kill_tree(proc)
        except (OSError, subprocess.SubprocessError):
            print('Herdr named cleanup failed; terminating owned process tree', file=sys.stderr, flush=True)
        finally:
            if self.server.poll() is None:
                kill_tree(self.server)
            else:
                self.server.wait(timeout=3.0)

    def run(self):
        if not self.args.workdir.is_dir():
            raise DriverError('workdir must be an existing directory')
        self.args.session_dir.mkdir(parents=True, exist_ok=True)
        artifacts = self.args.session_dir.parent
        config = artifacts / f'{self.args.session_name}.config.toml'
        self.env['HERDR_CONFIG_PATH'] = str(config)
        # Exclusive creation prevents a repeated run from attaching to prior
        # state or overwriting any earlier run artifacts.
        with config.open('x', encoding='utf-8'):
            pass
        stdout_path = artifacts / f'{self.args.session_name}.server.stdout.log'
        stderr_path = artifacts / f'{self.args.session_name}.server.stderr.log'
        with stdout_path.open('xb') as stdout_log, stderr_path.open('xb') as stderr_log:
            # The UUID is isolated, but additionally refuse an existing server
            # before starting one. Never stop or attach to that existing server.
            code, text, _ = self.command(['status', 'server'])
            if code == 0 and _running(text):
                raise DriverError('named Herdr session already has a server; refusing to attach')
            if code != 0 or not _stopped(text):
                raise DriverError('named Herdr session status is ambiguous; refusing to attach')
            try:
                self.remaining()
                self.server = subprocess.Popen(self.prefix + ['server'], cwd=self.args.workdir,
                                               env=self.env, stdin=subprocess.DEVNULL,
                                               stdout=stdout_log, stderr=stderr_log, **group_options())
                self.ready()
                response = self.response('workspace.create', ['workspace', 'create', '--cwd',
                                         str(self.args.workdir), '--label', self.args.session_name, '--no-focus'])
                workspace, pane = workspace_ids(response)
                _event('workspace.ids', workspace_id=workspace, pane_id=pane)
                agent_args = self.args.agent_args
                if agent_args[:1] == ['--']:
                    agent_args = agent_args[1:]
                start = ['agent', 'start', 'bench', '--kind', self.args.kind, '--pane', pane,
                         '--timeout', '30000', '--', '--no-title', '--no-prewalk',
                         '--session-dir', str(self.args.session_dir), *agent_args]
                agent_status(self.response('agent.start', start, limit=35.0))
                remaining_ms = max(1, int(self.remaining() * 1000))
                prompt = ['agent', 'prompt', 'bench', self.args.prompt, '--wait',
                          '--timeout', str(remaining_ms)]
                # A timed out submission may already have reached the model.
                # Submit exactly once, with no retry of any agent command.
                agent_status(self.response('agent.prompt', prompt, limit=self.remaining()))
                code, text, stderr = self.command(['agent', 'read', 'bench', '--source',
                                                  'recent-unwrapped', '--lines', '120'])
                _diagnostic('agent.read', stderr)
                if code:
                    raise DriverError(f'agent.read: Herdr CLI exited with status {code}')
                _event('agent.read', text=text)
            finally:
                self.cleanup()
        return 0


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        return Driver(args).run()
    except (DriverError, OSError, subprocess.SubprocessError) as exc:
        print(f'herdr driver: {exc}', file=sys.stderr, flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
