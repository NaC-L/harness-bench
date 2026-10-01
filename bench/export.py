"""Portable comparison bundles; transcripts are opt-in and may contain secrets."""
from __future__ import annotations
import json
import os
import re
import tempfile
from pathlib import Path
from . import report
from .charts import render_charts
from .manifest import load_manifest
from .runner import runtime_values
from .explorer import compile_explorer


def _spellings(root) -> list[str]:
    """A root as given and fully resolved, longest first.

    The same directory can appear under two names: Windows 8.3 short paths
    (C:\\Users\\RUNNER~1) vs long ones, or macOS /var vs /private/var.
    Longest first, so /private/var/x is not partly rewritten via /var/x.
    """
    root = str(root).rstrip('/\\')
    if not root:
        return []
    return sorted({root, os.path.realpath(root).rstrip('/\\')}, key=len, reverse=True)


def sanitize(value, *, benchmark_dir, home, temp):
    """Replace local roots in strings, including dictionary keys and escaped paths."""
    flags = re.IGNORECASE if os.name == 'nt' else 0

    def replace(text, root, replacement):
        pattern = r'[\\/]+'.join(re.escape(part) for part in re.split(r'[\\/]+', root))
        return re.sub(pattern, lambda match: replacement, text, flags=flags)

    roots = [(form, rep) for root, rep in ((benchmark_dir, '{benchmark_dir}'), (home, '~'), (temp, '{temp}'))
             for form in _spellings(root)]
    # On Windows TEMP is usually inside HOME, so HOME's replacement may already have changed it.
    for form in _spellings(temp):
        portable = form
        for root, rep in roots[:-len(_spellings(temp))]:
            portable = replace(portable, root, rep)
        roots.append((portable, '{temp}'))

    def text(value):
        for root, rep in roots:
            value = replace(value, root, rep)
        return value

    def visit(value):
        if isinstance(value, str):
            return text(value)
        if isinstance(value, list):
            return [visit(item) for item in value]
        if isinstance(value, dict):
            return {visit(key): visit(item) for key, item in value.items()}
        return value

    return visit(value)


def _segment(value) -> str:
    """One safe path component from a harness or task name."""
    return re.sub(r'[^A-Za-z0-9._-]+', '-', str(value)).strip('.-') or '_'


def bundle_dirs(rows) -> dict[str, str]:
    """Bundle-relative run directories, runs/<harness>/<task>/trial-<n>, keyed by run id.

    Matching trials of two arms sit side by side, so sessions compare with a plain diff.
    """
    dirs, used = {}, set()
    for row in rows:
        leaf = _segment(f"trial-{row['trial']}" if row.get('trial') is not None else row['run_id'])
        path = f"runs/{_segment(row['harness'])}/{_segment(row['task'])}/{leaf}"
        if path in used:
            path += f"-{_segment(row['run_id'])}"
        used.add(path)
        dirs[row['run_id']] = path
    return dirs


def copy_run(artifact, target, roots, *, include_transcripts=False):
    """Copy one run's shareable files, sanitizing text.

    A single harness session log becomes session.jsonl and its companion directory session/;
    several logs keep their native names under sessions/.
    """
    artifact, target = Path(artifact), Path(target)

    def copy(source, destination):
        data = source.read_bytes()
        try:
            data = sanitize(data.decode('utf-8'), **roots).encode('utf-8')
        except UnicodeDecodeError:
            pass
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)

    files = ['patch.diff', 'check.txt', 'check-visible.txt']
    if include_transcripts:
        files += ['stdout.jsonl', 'stderr.txt']
    for name in files:
        if (artifact / name).is_file():
            copy(artifact / name, target / name)
    sessions = artifact / 'sessions'
    if not (include_transcripts and sessions.is_dir()):
        return
    logs = [path for path in sessions.glob('*.jsonl') if path.is_file()]
    if len(logs) == 1:
        base, renames = target, {logs[0].name: 'session.jsonl', logs[0].stem: 'session'}
    else:
        base, renames = target / 'sessions', {}
    for source in sessions.rglob('*'):
        if source.is_file():
            head, *rest = source.relative_to(sessions).parts
            copy(source, base.joinpath(renames.get(head, head), *rest))

def session_index(rows, out) -> str:
    """Link captured sessions in task/trial order and make their metric paths portable."""
    out = Path(out)
    lines = ['# Sessions', '', 'Native harness records; local paths are sanitized.',
             'Compare the same task/trial across harnesses.', '',
             '| Task | Trial | Harness | Session |',
             '| --- | --- | --- | --- |']
    for row in sorted(rows, key=lambda r: (r['task'], str(r.get('trial', '')), r['harness'], r['run_id'])):
        artifact = out / row['artifact_dir']
        logs = sorted([p for p in artifact.rglob('*.jsonl') if p.name != 'stdout.jsonl'])
        paths = [p.relative_to(out).as_posix() for p in logs]
        if isinstance(row.get('metrics'), dict):
            row['metrics']['session_files'] = paths
        links = ', '.join(f'[{Path(p).name}]({p})' for p in paths) or 'Not captured'
        task = str(row['task']).replace('|', r'\|')
        harness = str(row['harness']).replace('|', r'\|')
        lines.append(f"| {task} | {row.get('trial', '—')} | {harness} | {links} |")
    return '\n'.join(lines) + '\n'



def export(rows, results, out, baseline, candidate, *, margin=0.10, min_trials=3,
           include_transcripts=False):
    """Write a comparison bundle without full event streams or sessions by default."""
    results, out = Path(results), Path(out)
    if out.exists():
        raise ValueError(f'output directory already exists: {out}')
    selected = [row for row in rows if row.get('harness') in (baseline, candidate)]
    result = report.compare(selected, baseline, candidate, margin=margin, min_trials=min_trials)
    manifest = load_manifest(results)
    roots = {'benchmark_dir': runtime_values()['benchmark_dir'], 'home': Path.home(),
             'temp': tempfile.gettempdir()}
    dirs = bundle_dirs(selected)
    sanitized_rows = []
    for row in selected:
        clean = sanitize(row, **roots)
        clean['artifact_dir'] = dirs[row['run_id']]
        clean['workdir'] = None
        sanitized_rows.append(clean)
    sanitized_manifest = sanitize(manifest, **roots)
    try:
        label = out.resolve().relative_to(Path(roots['benchmark_dir']).resolve()).as_posix()
    except ValueError:
        label = f'<path-to>/{out.name}'  # the reader decides where the bundle lives
    svgs = render_charts(result, selected)
    charts = [(name.removesuffix('.svg').replace('-', ' ').capitalize(), f'charts/{name}')
              for name in svgs]
    markdown = report.render_markdown(result, selected, manifest, results_label=label, charts=charts)
    out.mkdir(parents=True)
    (out / 'charts').mkdir()
    for name, svg in svgs.items():
        (out / 'charts' / name).write_text(sanitize(svg, **roots), encoding='utf-8')
    (out / 'REPORT.md').write_text(sanitize(markdown, **roots), encoding='utf-8')
    if manifest is not None:
        (out / 'manifest.json').write_text(json.dumps(sanitized_manifest, indent=2, ensure_ascii=False) + '\n',
                                           encoding='utf-8')

    for row in selected:
        artifact = Path(row['artifact_dir'])
        if not artifact.is_absolute():
            artifact = results / artifact
        copy_run(artifact, out / dirs[row['run_id']], roots, include_transcripts=include_transcripts)
    if include_transcripts:
        (out / 'SESSIONS.md').write_text(session_index(sanitized_rows, out), encoding='utf-8')
    (out / 'runs.jsonl').write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n'
                                         for row in sanitized_rows), encoding='utf-8')
    compile_explorer(out, out / 'EXPLORER.html')
