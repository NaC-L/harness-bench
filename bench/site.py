"""Build GitHub Pages from reviewed published bundles, never private results."""
from __future__ import annotations

import argparse
from html import escape
from pathlib import Path
from urllib.parse import quote

from .explorer import STYLE, collect, render


REPOSITORY = 'https://github.com/NaC-L/harness-bench'
PUBLISHED = Path(__file__).resolve().parents[1] / 'published'


def build(published: Path, out: Path) -> int:
    root = published.resolve()
    if not root.is_dir():
        raise ValueError(f'published directory does not exist: {published}')
    if out.exists():
        raise ValueError(f'output directory already exists: {out}')
    if out.resolve().is_relative_to(root):
        raise ValueError('site output must be outside the published input directory')
    bundles = sorted((p.parent for p in root.rglob('runs.jsonl')
                      if p.resolve().is_relative_to(root)),
                     key=lambda p: p.relative_to(root).as_posix(), reverse=True)
    out.mkdir(parents=True)
    cards = []
    graph_count = 0
    for directory in bundles:
        relative = directory.relative_to(root)
        label = relative.as_posix()
        data = collect(directory)
        data['title'] = label
        data['index_href'] = '../' * len(relative.parts) + 'index.html'
        graph_count += len(data['charts'])
        target = out / relative / 'EXPLORER.html'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render(data), encoding='utf-8', newline='\n')
        arms = sorted({str(run['row'].get('harness', 'unknown')) for run in data['runs']})
        source = f'{REPOSITORY}/tree/main/published/{quote(label, safe="/")}'
        kind = 'Graphs + sessions' if data['charts'] else 'Run explorer'
        cards.append(f'<article class="experiment"><span class="experiment-mark" aria-hidden="true"></span>'
                     f'<div><h2><a href="{quote(label, safe="/")}/EXPLORER.html">'
                     f'{escape(label)}</a></h2><p>{len(data["runs"])} runs · '
                     f'{escape(", ".join(arms))}</p><a class="source" href="{source}">'
                     'Source bundle on GitHub</a></div><span class="experiment-kind">'
                     f'{kind}<br>{len(data["charts"])} saved plots</span></article>')
    # Historical CSV-only reports remain accessible without inventing session records.
    for directory in sorted(root.iterdir()):
        if directory.is_dir() and directory.resolve().is_relative_to(root) and not any(
                p.is_relative_to(directory) for p in bundles):
            label = directory.name
            source = f'{REPOSITORY}/tree/main/published/{quote(label, safe="")}'
            cards.append(f'<article class="experiment"><span class="experiment-mark" aria-hidden="true"></span>'
                         f'<div><h2><a href="{source}">{escape(label)}</a></h2>'
                         '<p>Legacy report · no JSONL session explorer</p></div>'
                         '<span class="experiment-kind">Source report</span></article>')
    content = '\n'.join(cards) or '<p>No published run bundles yet.</p>'
    index = (INDEX.replace('__BENCH_STYLE__', STYLE)
             .replace('__BUNDLE_COUNT__', str(len(bundles)))
             .replace('__GRAPH_COUNT__', str(graph_count))
             .replace('__EXPERIMENTS__', content))
    (out / 'index.html').write_text(index, encoding='utf-8', newline='\n')
    (out / '.nojekyll').write_text('', encoding='utf-8')
    return len(bundles)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--published', type=Path, default=PUBLISHED)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        count = build(args.published, args.out)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(f'Built {count} explorers and experiment index in {args.out}')


INDEX = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Harness Bench · Experiments</title><style>__BENCH_STYLE__</style></head><body>
<div class="topbar"><nav class="topbar-inner" aria-label="Site"><a class="brand" href="https://github.com/NaC-L/harness-bench">Harness Bench</a><a href="#experiments">Research</a></nav></div>
<header class="page-header"><p class="eyebrow">Research / Coding-agent experiments</p><h1>Measure the harness.</h1>
<p class="lede">Published experiments on coding agents. Follow the comparison graphs, then inspect the messages, tool calls, checks, and patches behind each run.</p>
<div class="stats"><div class="stat"><small>Run bundles</small><strong>__BUNDLE_COUNT__</strong></div><div class="stat"><small>Saved graphs</small><strong>__GRAPH_COUNT__</strong></div><div class="stat"><small>Portable explorers</small><strong>HTML</strong></div><div class="stat"><small>Comparison reports</small><strong>Frozen</strong></div></div>
<p class="micro muted">Reviewed snapshots only · Missing stays unknown · Reports are not re-scored</p></header>
<main><div class="section-heading" id="experiments"><h2>Experiments</h2><span class="micro muted">Source / Evidence</span></div>
<div class="experiments">__EXPERIMENTS__</div>
<footer><a href="https://github.com/NaC-L/harness-bench">Repository and reproduction instructions</a><br>Explorers also work offline when saved. No external fonts or scripts.</footer></main></body></html>'''


if __name__ == '__main__':
    main()
