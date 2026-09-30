"""Invocation provenance, recorded before any runs start."""
from __future__ import annotations
import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def load_manifest(results: Path) -> dict | None:
    path = results / 'manifest.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def _file_entry(path: Path) -> dict:
    data = path.read_bytes()
    contents = None
    if len(data) <= 64 * 1024:
        try:
            text = data.decode('utf-8')
            if '\0' not in text:
                contents = text
        except UnicodeDecodeError:
            pass
    return {'sha256': hashlib.sha256(data).hexdigest(), 'contents': contents}


def record_invocation(results, harnesses, tasks, *, trials, jobs, alternate_order, timeout,
                      versions, config: Path | None = None):
    from .runner import fingerprint, repo_path, runtime_values

    benchmark_dir = Path(runtime_values()['benchmark_dir']).resolve()
    recorded_harnesses = {}
    for h in harnesses:
        paths = []
        for arg in h.command:
            if '{benchmark_dir}' in arg:
                paths.append(Path(arg.replace('{benchmark_dir}', str(benchmark_dir))).resolve())
        if h.state_template:
            paths += sorted(p for p in repo_path(h.state_template).rglob('*') if p.is_file())
        files = {path.relative_to(benchmark_dir).as_posix(): _file_entry(path)
                 for path in paths if path.is_relative_to(benchmark_dir) and path.is_file()}
        recorded_harnesses[h.name] = {'kind': h.kind, 'command': list(h.command),
                                      'config_hash': h.config_hash, 'version': versions[h.name],
                                      'state_template': h.state_template,
                                      # Command argv only; the computed values are never recorded.
                                      'env_commands': dict(h.env_commands),
                                      'files': files}
    try:
        node = subprocess.run(['node', '--version'], capture_output=True, text=True,
                              timeout=30, check=True).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        node = None
    config_path = None
    if config is not None:
        path = Path(config).resolve()
        config_path = path.relative_to(benchmark_dir).as_posix() if path.is_relative_to(benchmark_dir) else str(path)
    invocation = {'started': datetime.now(timezone.utc).isoformat(), 'trials': trials,
                  'jobs': jobs, 'alternate_order': alternate_order, 'timeout': timeout,
                  'platform': platform.platform(), 'python': platform.python_version(), 'node': node,
                  'config': config_path, 'harnesses': recorded_harnesses,
                  'tasks': {task.id: fingerprint(task.dir) for task in tasks}}
    manifest = load_manifest(results) or {'schema_version': 1, 'invocations': []}
    manifest['invocations'].append(invocation)
    results.mkdir(parents=True, exist_ok=True)
    (results / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
