"""Build GitHub Pages from reviewed published bundles, never private results."""
from __future__ import annotations

import argparse
from html import escape
from pathlib import Path
from urllib.parse import quote

from .explorer import collect, render


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
    for directory in bundles:
        relative = directory.relative_to(root)
        label = relative.as_posix()
        data = collect(directory)
        data['title'] = label
        target = out / relative / 'EXPLORER.html'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render(data), encoding='utf-8')
        arms = sorted({str(run['row'].get('harness', 'unknown')) for run in data['runs']})
        source = f'{REPOSITORY}/tree/main/published/{quote(label, safe="/")}'
        cards.append(f'<article><h2><a href="{quote(label, safe="/")}/EXPLORER.html">'
                     f'{escape(label)}</a></h2><p>{len(data["runs"])} runs · '
                     f'{escape(", ".join(arms))}</p><a class="source" href="{source}">'
                     'Source bundle on GitHub</a></article>')
    # Historical CSV-only reports remain accessible without inventing session records.
    for directory in sorted(root.iterdir()):
        if directory.is_dir() and directory.resolve().is_relative_to(root) and not any(
                p.is_relative_to(directory) for p in bundles):
            label = directory.name
            source = f'{REPOSITORY}/tree/main/published/{quote(label, safe="")}'
            cards.append(f'<article><h2><a href="{source}">{escape(label)}</a></h2>'
                         '<p>Legacy report · no JSONL session explorer</p></article>')
    content = '\n'.join(cards) or '<p>No published run bundles yet.</p>'
    (out / 'index.html').write_text(INDEX.replace('__EXPERIMENTS__', content), encoding='utf-8')
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
<title>Harness Bench · Experiments</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#10151d;color:#edf2fa;font:16px/1.6 system-ui,sans-serif}main{max-width:1100px;margin:auto;padding:32px 24px}h1{font-size:32px;margin:0}h2{font-size:19px;margin:0;overflow-wrap:anywhere}p{color:#b4c2d6}a{color:#7ed6ed;text-underline-offset:4px}a:hover{color:#edf2fa}:focus-visible{outline:3px solid #7ed6ed;outline-offset:4px}.experiments{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:16px;margin-top:28px}article{background:#19212d;border:1px solid #3c4a60;border-radius:10px;padding:20px}article p{overflow-wrap:anywhere;margin:10px 0}.source{font-size:14px}footer{margin-top:32px;color:#b4c2d6}@media(max-width:500px){main{padding:24px 16px}h1{font-size:27px}}
</style></head><body><main><h1>Harness Bench</h1><p>Published coding-agent experiments. Select an experiment, then click a run to inspect messages, tool calls, checks, and patches.</p><p>Reviewed repository snapshots only. Missing data stays unknown; saved reports are not re-scored.</p><div class="experiments">__EXPERIMENTS__</div><footer><a href="https://github.com/NaC-L/harness-bench">Repository and reproduction instructions</a> · Explorers also work offline when saved.</footer></main></body></html>'''


if __name__ == '__main__':
    main()
