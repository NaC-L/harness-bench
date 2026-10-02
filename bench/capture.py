"""Capture an arm's first model request without spending model usage.

The arm's own command runs against a local Anthropic Messages stub (`ANTHROPIC_BASE_URL`).
The stub records the first request body and replies with a one-line final answer, so
the harness ends after one turn. `env_commands` are never executed: each of their keys
receives a dummy value, so no credential reaches the stub or the output.

`breakdown` splits the request into named components (system blocks, markdown sections
of the system prompt, each tool's description and schema, messages) by character count.
Characters are a size proxy for attribution, not provider tokens.
"""
from __future__ import annotations

import http.server
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from .environment import isolate
from .runner import Harness, executable, expand, repo_path, runtime_values
from .tasks import Task, overlay, rmtree
from .process import group_options, kill_tree

DUMMY_ANTHROPIC = 'sk-ant-oat01-capture-not-a-credential'
DUMMY = 'capture-not-a-credential'


def _sse(events: list[tuple[str, dict]]) -> bytes:
    return b''.join(f'event: {name}\ndata: {json.dumps(data)}\n\n'.encode() for name, data in events)


FINAL_ANSWER = _sse([
    ('message_start', {'type': 'message_start', 'message': {
        'id': 'msg_capture', 'type': 'message', 'role': 'assistant', 'model': 'capture', 'content': [],
        'stop_reason': None, 'stop_sequence': None, 'usage': {'input_tokens': 0, 'output_tokens': 0}}}),
    ('content_block_start', {'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}}),
    ('content_block_delta', {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': 'Done.'}}),
    ('content_block_stop', {'type': 'content_block_stop', 'index': 0}),
    ('message_delta', {'type': 'message_delta', 'delta': {'stop_reason': 'end_turn', 'stop_sequence': None},
                       'usage': {'output_tokens': 1}}),
    ('message_stop', {'type': 'message_stop'}),
])


class _Stub(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self):
        super().__init__(('127.0.0.1', 0), _Handler)
        self.requests: list[dict] = []
        self.first = threading.Event()


class _Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get('content-length') or 0))
        self.server.requests.append({'path': self.path, 'body': body})
        self.server.first.set()
        self.send_response(200)
        self.send_header('content-type', 'text/event-stream')
        self.send_header('content-length', str(len(FINAL_ANSWER)))
        self.end_headers()
        self.wfile.write(FINAL_ANSWER)

    def do_GET(self):
        self.send_response(404)
        self.send_header('content-length', '0')
        self.end_headers()

    def log_message(self, *_args):
        pass

    def handle(self):
        try:
            super().handle()
        except ConnectionError:  # clients may drop keep-alive sockets after the stream
            pass


def _route_pi(state: Path, base_url: str) -> None:
    """Point Pi's built-in anthropic provider at the stub in the disposable state root."""
    path = state / 'models.json'
    config = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
    config.setdefault('providers', {}).setdefault('anthropic', {})['baseUrl'] = base_url
    path.write_text(json.dumps(config, indent=1), encoding='utf-8')


def capture(task: Task, h: Harness, *, timeout: int = 120) -> dict:
    """Run one arm until its first model request; return that request and run facts."""
    stub = _Stub()
    threading.Thread(target=stub.serve_forever, daemon=True).start()
    workdir = Path(tempfile.mkdtemp(prefix='hb-capture-')).resolve()
    session_dir = Path(tempfile.mkdtemp(prefix='hb-capture-session-')).resolve()
    state = None
    env = {**os.environ, **h.env}
    try:
        if h.state_template:
            state = Path(tempfile.mkdtemp(prefix='hb-capture-state-')).resolve()
            shutil.copytree(repo_path(h.state_template), state, dirs_exist_ok=True)
            isolate(h.kind, env, state)
        for key in h.env_commands:
            env[key] = DUMMY_ANTHROPIC if 'ANTHROPIC' in key else DUMMY
        base_url = f'http://127.0.0.1:{stub.server_address[1]}'
        env['ANTHROPIC_BASE_URL'] = base_url  # OMP honors this; Pi needs its models.json
        if h.kind == 'pi':
            if state is None:
                raise ValueError(f'{h.name}: capture needs state_template for Pi (routing via models.json)')
            _route_pi(state, base_url)
        overlay(task.repo, workdir)
        values = {**runtime_values(), 'prompt': task.prompt, 'workdir': str(workdir),
                  'session_dir': str(session_dir), 'session_id': 'capture', 'task_dir': str(task.dir.resolve()),
                  'run_id': 'capture', 'timeout_sec': str(timeout)}
        stderr_path = session_dir / 'capture-stderr.txt'
        with stderr_path.open('wb') as stderr_file:
            proc = subprocess.Popen(executable(expand(h.command, values), env), cwd=workdir, env=env,
                                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=stderr_file,
                                    **group_options())
            deadline = time.monotonic() + timeout
            while not stub.first.is_set() and proc.poll() is None and time.monotonic() < deadline:
                stub.first.wait(0.2)
            try:  # the stub's final answer normally ends the run; never wait long for it
                proc.wait(timeout=20 if stub.first.is_set() else max(0.0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                kill_tree(proc)
                proc.wait(timeout=30)
        stderr = stderr_path.read_text(encoding='utf-8', errors='replace')
        if not stub.requests:
            raise RuntimeError(f'{h.name}: no model request reached the stub (exit {proc.returncode}); '
                               f'stderr tail: {stderr[-400:]!r}')
        first = stub.requests[0]
        return {'harness': h.name, 'task': task.id, 'path': first['path'],
                'requests_seen': len(stub.requests), 'body': json.loads(first['body'])}
    finally:
        stub.shutdown()
        stub.server_close()
        rmtree(workdir)
        rmtree(session_dir)
        if state is not None:
            rmtree(state)


_SECTION = re.compile(r'^(?:§ .+|#{1,2} .+|<[a-z][a-z0-9_-]*>)$')


def _sections(prefix: str, text: str) -> list[tuple[str, int]]:
    """Split prompt text at markdown headings, `§` dividers and bare opening XML tags."""
    out, name, lines = [], '(preamble)', []
    for line in text.split('\n'):
        if _SECTION.match(line):
            if lines:
                out.append((f'{prefix} {name}', len('\n'.join(lines))))
            name, lines = line[:70], []
        lines.append(line)
    if lines:
        out.append((f'{prefix} {name}', len('\n'.join(lines))))
    # Repeated headings (e.g. several <critical> blocks) stay distinguishable.
    seen: dict[str, int] = {}
    unique = []
    for label, size in out:
        seen[label] = seen.get(label, 0) + 1
        unique.append((label if seen[label] == 1 else f'{label} ({seen[label]})', size))
    return unique


def _text(content) -> str:
    if isinstance(content, str):
        return content
    return '\n'.join(block.get('text', '') if block.get('type') == 'text' else json.dumps(block)
                     for block in content or [])


def breakdown(body: dict) -> list[tuple[str, int]]:
    """Named components of an Anthropic Messages request with their character sizes."""
    parts: list[tuple[str, int]] = []
    system = body.get('system') or []
    if isinstance(system, str):
        system = [{'type': 'text', 'text': system}]
    for i, block in enumerate(system):
        parts.extend(_sections(f'system[{i}]', block.get('text', '')))
    for tool in body.get('tools') or []:
        name = tool.get('name', '?')
        parts.append((f'tool {name} description', len(tool.get('description') or '')))
        parts.append((f'tool {name} schema', len(json.dumps(tool.get('input_schema') or {}, separators=(',', ':')))))
    for i, message in enumerate(body.get('messages') or []):
        parts.append((f'message[{i}] {message.get("role")}', len(_text(message.get('content')))))
    return parts


def render(captures: list[dict]) -> str:
    """Side-by-side component table; the first capture is the reference column."""
    tables = [dict(breakdown(c['body'])) for c in captures]
    labels = list(dict.fromkeys(label for table in tables for label in table))
    names = [c['harness'] for c in captures]
    width = max([len(label) for label in labels] + [9])
    lines = [f'{"component":<{width}}  ' + '  '.join(f'{n:>12}' for n in names)]
    for label in labels:
        lines.append(f'{label:<{width}}  ' + '  '.join(f'{t.get(label, 0):>12,}' for t in tables))
    totals = [sum(t.values()) for t in tables]
    lines.append(f'{"TOTAL chars":<{width}}  ' + '  '.join(f'{n:>12,}' for n in totals))
    if len(totals) > 1 and totals[0]:
        lines.append(f'{"vs first":<{width}}  ' + '  '.join(f'{n / totals[0] - 1:>+12.1%}' for n in totals))
    lines.append('Characters, not tokens. Bodies are written beside this table for exact inspection.')
    return '\n'.join(lines)
