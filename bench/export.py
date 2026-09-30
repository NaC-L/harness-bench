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


def sanitize(value, *, benchmark_dir, home, temp):
    """Replace local roots in strings, including dictionary keys and escaped paths."""
    flags = re.IGNORECASE if os.name == 'nt' else 0

    def replace(text, root, replacement):
        root = str(root).rstrip('/\\')
        if not root:
            return text
        pattern = r'[\\/]+'.join(re.escape(part) for part in re.split(r'[\\/]+', root))
        return re.sub(pattern, lambda match: replacement, text, flags=flags)

    def text(value):
        value = replace(value, benchmark_dir, '{benchmark_dir}')
        value = replace(value, home, '~')
        value = replace(value, temp, '{temp}')
        # On Windows TEMP is usually inside HOME, so HOME's replacement changed it.
        portable_temp = replace(replace(str(temp), benchmark_dir, '{benchmark_dir}'), home, '~')
        return replace(value, portable_temp, '{temp}')

    def visit(value):
        if isinstance(value, str):
            return text(value)
        if isinstance(value, list):
            return [visit(item) for item in value]
        if isinstance(value, dict):
            return {visit(key): visit(item) for key, item in value.items()}
        return value

    return visit(value)


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
    sanitized_rows = []
    for row in selected:
        clean = sanitize(row, **roots)
        clean['artifact_dir'] = f"runs/{row['run_id']}"
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
    (out / 'runs.jsonl').write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n'
                                         for row in sanitized_rows), encoding='utf-8')
    if manifest is not None:
        (out / 'manifest.json').write_text(json.dumps(sanitized_manifest, indent=2, ensure_ascii=False) + '\n',
                                           encoding='utf-8')

    def copy(source, target):
        data = source.read_bytes()
        try:
            data = sanitize(data.decode('utf-8'), **roots).encode('utf-8')
        except UnicodeDecodeError:
            pass
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    for row in selected:
        artifact = Path(row['artifact_dir'])
        if not artifact.is_absolute():
            artifact = results / artifact
        target = out / 'runs' / row['run_id']
        files = ['patch.diff', 'check.txt', 'check-visible.txt']
        if include_transcripts:
            files += ['stdout.jsonl', 'stderr.txt']
        for name in files:
            source = artifact / name
            if source.is_file():
                copy(source, target / name)
        if include_transcripts and (artifact / 'sessions').is_dir():
            (target / 'sessions').mkdir(parents=True, exist_ok=True)
            for source in (artifact / 'sessions').rglob('*'):
                destination = target / 'sessions' / source.relative_to(artifact / 'sessions')
                if source.is_file():
                    copy(source, destination)
                elif source.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
