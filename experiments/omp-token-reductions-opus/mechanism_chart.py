"""Paired-bar SVG of tool-use mechanism totals per arm, from analyze.py mechanisms.jsonl.

Usage: python experiments/omp-token-reductions-opus/mechanism_chart.py MECHANISMS.jsonl OUT.svg
Each row has its own zero-based scale (row maximum); exact counts are printed beside the bars.
"""
from __future__ import annotations
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from bench.charts import (CYAN, LEFT, PRIMARY, RIGHT, TERTIARY, _finish, _line, _square,  # noqa: E402
                          _text)

BASELINE, CANDIDATE = 'omp-token-baseline', 'omp-token-candidate'
ROWS = [('Bare read calls', 'bare_reads'),
        ('Ranged read calls', 'ranged_reads'),
        ('Bash calls', 'bash_calls'),
        ('Bash file-dump commands', 'shell_file_dump_candidates'),
        ('Edit errors', 'edit_errors'),
        ('Folded (summarized) reads', 'folded_reads')]
BAR_LEFT, BAR_RIGHT, VALUE_X = 262, 640, RIGHT


def totals(path):
    sums, runs = {BASELINE: Counter(), CANDIDATE: Counter()}, Counter()
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        record = json.loads(line)
        if record['harness'] in sums and record.get('mechanisms') is not None:
            sums[record['harness']].update(record['mechanisms'])
            runs[record['harness']] += 1
    return sums, runs


def bar(y, value, scale, color):
    width = 0 if scale == 0 else math.floor((BAR_RIGHT - BAR_LEFT) * value / scale)
    return (f'<rect x="{BAR_LEFT}" y="{math.floor(y)}" width="{max(width, 1) if value else 0}" height="8" '
            f'fill="{color}" shape-rendering="crispEdges" data-value="{value}"/>')


def render(sums, runs):
    title = 'OPUS 5.5: COMBINED CANDIDATE SWAPS READ FOR BASH, EDIT ERRORS RISE'
    body = [_text(LEFT, 32, title, size=16, color=PRIMARY, sans=True)]
    x = RIGHT - 400
    for label, color in ((f'{BASELINE.upper()} (BASELINE)', TERTIARY), (f'{CANDIDATE.upper()} (CANDIDATE)', CYAN)):
        body += [_square(x + 3.5, 57, color, size=7), _text(x + 13, 61, label, size=10, color=TERTIARY, caps=True)]
        x += 13 + len(label) * 6.6 + 20
    body += [_text(LEFT, 86, f'TOTALS OVER {runs[BASELINE]} + {runs[CANDIDATE]} RUNS', size=10, color=TERTIARY, caps=True),
             _text(RIGHT, 86, 'EACH ROW: OWN ZERO-BASED SCALE', size=10, anchor='end', color=TERTIARY, caps=True)]
    desc = [title + '.']
    top = 112
    for i, (label, key) in enumerate(ROWS):
        y = top + i * 44
        base, cand = sums[BASELINE][key], sums[CANDIDATE][key]
        scale = max(base, cand)
        body += [f'<g class="metric-row" data-metric="{key}">',
                 _text(LEFT, y + 14, label, size=12, color=PRIMARY, sans=True),
                 bar(y + 2, base, scale, TERTIARY), bar(y + 16, cand, scale, CYAN),
                 _text(VALUE_X, y + 10, f'{base:,}', anchor='end', color=TERTIARY),
                 _text(VALUE_X, y + 24, f'{cand:,}', anchor='end', color=CYAN),
                 _line(LEFT, y + 34, RIGHT, y + 34), '</g>']
        desc.append(f'{label}: baseline {base}, candidate {cand}.')
    bottom = top + len(ROWS) * 44 - 6
    caption = ('Counts from session tool calls/results (analyze.py). File-dump is a regex proxy '
               '(cat/type/Get-Content); transcripts show candidate dumps sources, baseline mostly package.json. '
               'Descriptive, not causal attribution.')
    desc.append(caption)
    return _finish(title, ' '.join(desc), body, bottom, caption)


if __name__ == '__main__':
    source, out = sys.argv[1:3]
    Path(out).write_text(render(*totals(source)), encoding='utf-8', newline='\n')
