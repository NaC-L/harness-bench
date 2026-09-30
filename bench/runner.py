"""Headless harness runner. Workspaces are isolated directories, NOT security sandboxes."""
from __future__ import annotations
import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from .tasks import Task, overlay, protected_hashes, tampered, run_check, rmtree, baseline_results, tap_results
from .process import group_options, kill_tree
from .environment import STATE_ENV, CONTEXT_FILES, ancestor_context, isolate, state_dir
from .manifest import record_invocation


@dataclass
class Harness:
    name: str
    kind: str
    command: list[str]
    version_command: list[str]
    env: dict[str, str]
    config_hash: str
    # Directory copied into a fresh per-run state root (see bench/environment.py).
    state_template: str | None = None
    # Environment values computed per run by a command, e.g. a short-lived auth token.
    # Values are never written to records, manifests or artifacts.
    env_commands: dict[str, list[str]] = field(default_factory=dict)


def load_harnesses(path: Path) -> dict[str, Harness]:
    raw = path.read_bytes()
    config = tomllib.loads(raw.decode('utf-8'))
    out = {}
    for name, spec in config.get('harnesses', {}).items():
        kind = spec.get('kind', 'none')
        if spec.get('state_template') and kind not in STATE_ENV:
            raise ValueError(f'{name}: state_template is not supported for kind {kind!r}')
        if spec.get('state_template') and not repo_path(spec['state_template']).is_dir():
            raise ValueError(f'{name}: state_template is not a directory: {spec["state_template"]}')
        out[name] = Harness(name, kind, spec['command'],
                            spec.get('version_command', [spec['command'][0], '--version']),
                            spec.get('env', {}), hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest(),
                            spec.get('state_template'), spec.get('env_commands', {}))
    return out


def repo_path(value: str) -> Path:
    """Resolve a config path: `{benchmark_dir}` placeholder or relative to the benchmark dir."""
    root = Path(runtime_values()['benchmark_dir'])
    path = Path(value.replace('{benchmark_dir}', str(root)))
    return (path if path.is_absolute() else root / path).resolve()


def resolve_env_commands(h: Harness, operator_env: dict[str, str], env: dict[str, str]) -> None:
    """Compute env values with the operator's environment; failures never echo output."""
    for key, argv in h.env_commands.items():
        proc = subprocess.run(executable(expand(argv, runtime_values()), operator_env), env=operator_env,
                              capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
        value = proc.stdout.strip()
        if proc.returncode != 0 or not value:
            raise ValueError(f'env_commands.{key} failed (exit {proc.returncode})')
        env[key] = value


def fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    files = [path] if path.is_file() else sorted(p for p in path.rglob('*') if p.is_file())
    for file in files:
        digest.update((file.name if path.is_file() else file.relative_to(path).as_posix()).encode())
        digest.update(b'\0')
        digest.update(file.read_bytes())
    return digest.hexdigest()


def context_hashes(kind: str, env: dict[str, str], isolated: bool = False) -> dict[str, str]:
    # Hash, never copy, potentially credential-bearing config. This is an audit
    # aid, not proof of isolation: environment, hooks and extensions may differ.
    if kind not in CONTEXT_FILES:
        return {}
    root = state_dir(kind, env, Path.home())
    # Isolated roots are per-run temp copies; key them stably so arms stay comparable.
    return {(f'{{state}}/{name}' if isolated else str(root / name)): fingerprint(root / name)
            for name in CONTEXT_FILES[kind] if (root / name).is_file()}


def expand(argv: list[str], values: dict[str, str]) -> list[str]:
    # Single substitution pass: braces in the user prompt remain literal.
    pattern = re.compile(r'\{(' + '|'.join(re.escape(k) for k in values) + r')\}')
    return [pattern.sub(lambda m: values[m.group(1)], a) for a in argv]


def executable(argv: list[str], env: dict[str, str]) -> list[str]:
    path = shutil.which(argv[0], path=env.get('PATH', os.defpath))
    if not path:
        raise FileNotFoundError(f'CLI not found: {argv[0]}')
    return [path, *argv[1:]]




def execute(argv: list[str], *, cwd: Path, env: dict[str, str], stdout: Path,
            stderr: Path, timeout: int) -> tuple[int | None, bool, float]:
    start = time.monotonic()
    kwargs = group_options()
    with stdout.open('wb') as out, stderr.open('wb') as err:
        proc = subprocess.Popen(executable(argv, env), cwd=cwd, env=env, stdout=out, stderr=err,
                                stdin=subprocess.DEVNULL, **kwargs)
        try:
            code = proc.wait(timeout=timeout)
            timed_out = False
        except subprocess.TimeoutExpired:
            kill_tree(proc)
            code, timed_out = None, True
    return code, timed_out, time.monotonic() - start


def runtime_values() -> dict[str, str]:
    return {'benchmark_dir': str(Path(__file__).resolve().parents[1]), 'python': sys.executable}


def version(h: Harness) -> str:
    env = {**os.environ, **h.env}
    try:
        argv = expand(h.version_command, runtime_values())
        result = subprocess.run(executable(argv, env), env=env, capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=30)
        return (result.stdout or result.stderr).strip()[:1000]
    except (OSError, subprocess.SubprocessError) as exc:
        return f'unavailable: {exc}'


_baseline_cache: dict[str, dict[str, bool]] = {}
_baseline_lock = threading.Lock()


def _cached_baseline(task: Task, task_hash: str) -> dict[str, bool]:
    """Per-test results of the untouched task, computed once per task content hash."""
    with _baseline_lock:
        if task_hash not in _baseline_cache:
            _baseline_cache[task_hash] = baseline_results(task)
        return _baseline_cache[task_hash]


def _omp_json(command: list[str]) -> bool:
    return any(a == '--mode' and b == 'json' for a, b in zip(command, command[1:]))


def _difference(total: int | None, visible: int | None) -> int | None:
    return None if total is None or visible is None else total - visible


def run_one(task: Task, h: Harness, results: Path, trial: int = 1,
            timeout: int | None = None, keep_workdir: bool = False,
            harness_version: str | None = None) -> dict:
    from . import sessions
    run_id = uuid.uuid4().hex
    artifact = results / run_id
    artifact.mkdir(parents=True)
    workdir = Path(tempfile.mkdtemp(prefix=f'hb-{run_id[:8]}-')).resolve()
    session_dir = artifact / 'sessions'
    session_dir.mkdir()
    session_id = str(uuid.uuid4())
    values = {**runtime_values(), 'prompt': task.prompt, 'workdir': str(workdir),
              'session_dir': str(session_dir.resolve()), 'session_id': session_id,
              'task_dir': str(task.dir.resolve()), 'run_id': run_id,
              'timeout_sec': str(timeout or task.timeout_sec)}
    command = expand(h.command, values)
    env = {**os.environ, **h.env}
    operator_env = dict(env)  # env commands (e.g. auth tokens) read the operator's own state
    state = None
    if h.state_template:
        state = Path(tempfile.mkdtemp(prefix=f'hb-state-{run_id[:8]}-')).resolve()
        shutil.copytree(repo_path(h.state_template), state, dirs_exist_ok=True)
        isolate(h.kind, env, state)
    record = {'schema_version': 1, 'run_id': run_id, 'task': task.id, 'category': task.category,
              'harness': h.name, 'harness_kind': h.kind, 'harness_version': harness_version or version(h),
              'config_hash': h.config_hash, 'prompt_hash': hashlib.sha256(task.prompt.encode()).hexdigest(),
              'task_hash': fingerprint(task.dir), 'context_hashes': context_hashes(h.kind, env, state is not None),
              'isolated_state': state is not None, 'ancestor_context': ancestor_context(workdir, Path.home()),
              'trial': trial, 'workdir': str(workdir), 'artifact_dir': str(artifact.resolve()),
              'passed': False, 'agent_exit_code': None, 'timed_out': False, 'tampered_files': [],
              'wall_time_sec': None, 'errors': [], 'command': command, 'metrics': None,
              'agent_completion': None, 'agent_retries': None, 'visible_passed': None,
              'visible_tests_pass': None, 'visible_tests_fail': None, 'hidden_tests_pass': None,
              'hidden_tests_fail': None, 'baseline_passing_tests': None, 'regressions': None}
    started = time.time()
    record['started'] = started
    try:
        resolve_env_commands(h, operator_env, env)
        if h.kind == 'codex' and os.name == 'nt':
            # Python 3.14 mkdtemp's owner-only ACL prevents the Windows sandbox
            # from reading the workspace. Restore the parent sandbox ACLs here,
            # never on the separate state directory containing credentials.
            subprocess.run(['icacls', str(workdir), '/inheritance:e'],
                           capture_output=True, check=True, timeout=30)
        overlay(task.repo, workdir)
        # No commits: diff against an empty index then exclude original files by no-index comparison.
        before = protected_hashes(workdir)
        code, timed_out, elapsed = execute(command, cwd=workdir, env=env,
                                            stdout=artifact / 'stdout.jsonl', stderr=artifact / 'stderr.txt',
                                            timeout=timeout or task.timeout_sec)
        record.update(agent_exit_code=code, timed_out=timed_out, wall_time_sec=elapsed)
        agent_completed = True
        completion = (sessions.pi_completion if h.kind == 'pi' else
                      sessions.omp_completion if h.kind == 'omp' and _omp_json(h.command) else None)
        if completion is not None:
            status, errors = completion(artifact / 'stdout.jsonl')
            record['agent_completion'] = status
            record['errors'].extend(errors)
            agent_completed = status == 'completed'
            record['agent_retries'] = sessions.stream_retries(artifact / 'stdout.jsonl')
        record['tampered_files'] = tampered(before, protected_hashes(workdir))
        # Preserve changed source before grading modifies the workdir.
        diff = subprocess.run(['git', 'diff', '--no-index', '--no-prefix', '--', str(task.repo.resolve()), str(workdir)],
                              capture_output=True, timeout=30)
        (artifact / 'patch.diff').write_bytes(diff.stdout)
        # Restore protected inputs, including deleted tests, and remove newly added tests.
        rmtree(workdir / 'test')
        overlay(task.repo / 'test', workdir / 'test')
        if (task.repo / 'package.json').exists():
            shutil.copy2(task.repo / 'package.json', workdir / 'package.json')
        visible = run_check(task, workdir, include_hidden=False)
        (artifact / 'check-visible.txt').write_text(visible.output, encoding='utf-8')
        check = run_check(task, workdir)
        (artifact / 'check.txt').write_text(check.output, encoding='utf-8')
        record.update(check_exit_code=check.exit_code, check_timed_out=check.timed_out,
                      tests_pass=check.tests_pass, tests_fail=check.tests_fail,
                      passed=check.passed and code == 0 and agent_completed and not timed_out and not record['tampered_files'])
        record.update(visible_passed=visible.passed, visible_tests_pass=visible.tests_pass,
                      visible_tests_fail=visible.tests_fail,
                      hidden_tests_pass=_difference(check.tests_pass, visible.tests_pass),
                      hidden_tests_fail=_difference(check.tests_fail, visible.tests_fail))
        baseline = _cached_baseline(task, record['task_hash'])
        record['baseline_passing_tests'] = sum(baseline.values()) if baseline else None
        if baseline and not check.timed_out:
            final = tap_results(check.output)
            record['regressions'] = sorted(n for n, ok in baseline.items() if ok and final.get(n) is not True)
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        record['errors'].append(f'{type(exc).__name__}: {exc}')
    finally:
        ended = time.time()
        record['ended'] = ended
        # OMP and Pi receive redirected sessions. Claude/Codex persist under their
        # home roots; passing our empty artifact directory would hide them.
        record['metrics'] = sessions.collect(h.kind, workdir=workdir,
                                            session_dir=session_dir if h.kind in ('omp', 'pi') else None,
                                            session_id=session_id, stdout_path=artifact / 'stdout.jsonl',
                                            started=started, ended=ended, env=env,
                                            check_command=task.check)
        for i, source in enumerate(record['metrics'].get('session_files', [])):
            src = Path(source)
            if src.is_file() and session_dir not in src.parents:
                shutil.copy2(src, session_dir / f'captured-{i}-{src.name}')
        (artifact / 'run.json').write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding='utf-8')
        if not keep_workdir:
            rmtree(workdir)
            if state is not None:
                rmtree(state)
    return record


def run_matrix(tasks: list[Task], harnesses: list[Harness], results: Path, *, trials: int = 1,
               jobs: int = 1, timeout: int | None = None, keep_workdir: bool = False,
               alternate_order: bool = False, config: Path | None = None) -> list[dict]:
    if alternate_order and jobs != 1:
        raise ValueError('alternate_order requires jobs=1')
    results.mkdir(parents=True, exist_ok=True)
    versions = {h.name: version(h) for h in harnesses}
    record_invocation(results, harnesses, tasks, trials=trials, jobs=jobs,
                      alternate_order=alternate_order, timeout=timeout, versions=versions,
                      config=config)
    lock = threading.Lock()
    def work(t, h, trial):
        row = run_one(t, h, results, trial, timeout, keep_workdir, versions[h.name])
        with lock:
            with (results / 'runs.jsonl').open('a', encoding='utf-8') as f:
                f.write(json.dumps(row, ensure_ascii=False) + '\n')
            print(f"{h.name} / {t.id} / {trial}: {'PASS' if row['passed'] else 'FAIL'} ({row['wall_time_sec']}s)", flush=True)
        return row
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        pending = []
        for trial in range(1, trials + 1):
            for index, t in enumerate(tasks):
                ordered = harnesses[::-1] if alternate_order and ((trial - 1) * len(tasks) + index) % 2 else harnesses
                pending.extend(pool.submit(work, t, h, trial) for h in ordered)
        return [f.result() for f in pending]
