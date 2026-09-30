"""Deterministic, self-contained SVG comparison charts (standard library only)."""
from __future__ import annotations
import math
import statistics
import textwrap
from html import escape


COLORS = ('#0072B2', '#E69F00')


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _text(x, y, value, *, size=14, anchor='start', color='#222222'):
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" text-anchor="{anchor}" '
            f'fill="{color}">{escape(str(value))}</text>')


def _line(x1, y1, x2, y2, *, color='#D5D9DE', width=1, extra=''):
    return (f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{color}" stroke-width="{width}" {extra}/>')


def _circle(x, y, color, *, failed=False, extra=''):
    return (f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4.5" fill="{"#FFFFFF" if failed else color}" '
            f'stroke="{color}" stroke-width="2" {extra}/>')


def _svg(width, height, title, desc, body):
    return '\n'.join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="chart-title chart-desc">',
        f'<title id="chart-title">{escape(title)}</title>',
        f'<desc id="chart-desc">{escape(desc)}</desc>',
        f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>',
        '<g font-family="Arial, Helvetica, sans-serif">', *body, '</g>', '</svg>', ''])


def _nice_step(span, intervals=5):
    raw = max(span, 1e-12) / intervals
    power = 10 ** math.floor(math.log10(raw))
    for factor in (1, 2, 2.5, 5, 10):
        if raw <= factor * power:
            return factor * power


def _label(value, step):
    decimals = max(0, -math.floor(math.log10(step)))
    if step != round(step, decimals):
        decimals += 1
    return f'{value:,.{decimals}f}'


def _legend(arms, *, runs):
    body = []
    for i, name in enumerate(arms):
        y = 84 + i * 24
        body += [_circle(30, y - 4, COLORS[i]), _text(44, y, name)]
    if runs:
        body += [_circle(30, 132, '#444444', failed=True),
                 _text(44, 136, 'Failed run (hollow); filled = passed'),
                 _line(430, 132, 450, 132, color='#444444', width=3),
                 _text(458, 136, 'Median of known runs')]
    return body


def _summary(result):
    arms = (result['baseline'], result['candidate'])
    metrics = [('Tokens per correct (total)', 'tokens_per_correct'),
               ('Tokens per correct (uncached)', 'uncached_tokens_per_correct'),
               ('Cost per correct', 'cost_per_correct'),
               ('Median wall time', 'median_wall_time_sec'),
               ('P90 wall time', 'p90_wall_time_sec')]
    cards = [result['scorecards'][name] for name in arms]
    changes = []
    for _, key in metrics:
        b, c = (card.get(key) for card in cards)
        changes.append((c / b - 1) * 100 if _number(b) and _number(c) and b != 0 else None)
    margin = result['margin'] * 100
    known = [v for v in changes if v is not None]
    low, high = min([-margin, 0, *known]), max([margin, 0, *known])
    padding = max((high - low) * 0.15, 5)
    step = _nice_step(high - low + 2 * padding)
    low = math.floor((low - padding) / step) * step
    high = math.ceil((high + padding) / step) * step
    left, right, top, bottom = 300, 676, 160, 402
    x = lambda value: left + (value - low) / (high - low) * (right - left)
    title = f"Efficiency summary — verdict: {result['verdict']}"
    body = [_text(24, 32, title, size=22),
            _text(24, 56, 'Candidate relative to baseline (%); lower = better.'), *_legend(arms, runs=False),
            f'<rect x="{x(-margin):.2f}" y="{top}" width="{x(margin) - x(-margin):.2f}" '
            f'height="{bottom - top}" fill="#EEF0F3"/>']
    for i in range(round((high - low) / step) + 1):
        tick = low + i * step
        body += [_line(x(tick), top, x(tick), bottom),
                 _text(x(tick), 430, _label(tick, step) + '%', anchor='middle', size=12)]
    body.append(_line(x(0), top, x(0), bottom, color=COLORS[0], width=2))
    for i, ((name, _), value) in enumerate(zip(metrics, changes)):
        y = 184 + i * 48
        body.append(_text(24, y + 5, name, size=13))
        if value is not None:
            body += [_line(x(0), y, x(value), y, color=COLORS[1], width=2),
                     _circle(x(value), y, COLORS[1], extra='class="summary-marker"')]
        body.append(_text(776, y + 5, 'unknown' if value is None else f'{value:+,.1f}%', anchor='end'))
    body += [_text(488, 459, 'Relative change (%)', anchor='middle'),
             _text(24, 489, f'Shaded band: ±{margin:g}% margin. Unknown includes an undefined zero-baseline ratio.', size=12)]
    return _svg(800, 512, title,
                f'{arms[1]} relative to {arms[0]}. Lower is better. Shading marks the comparison margin. '
                'Unknown metrics are not plotted.', body)


def _tokens(row):
    metrics = row.get('metrics') or {}
    if not _number(metrics.get('input_tokens')) or not _number(metrics.get('output_tokens')):
        return None
    return sum(metrics.get(key) if _number(metrics.get(key)) else 0
               for key in ('input_tokens', 'cache_read_tokens', 'cache_write_tokens', 'output_tokens'))


def _strip(result, rows, *, tokens):
    arms = (result['baseline'], result['candidate'])
    selected = [r for r in rows if r.get('harness') in arms]
    tasks = sorted({r['task'] for r in selected})
    groups = {(task, arm): [] for task in tasks for arm in arms}
    unknown = 0
    for row in selected:
        value = _tokens(row) if tokens else row.get('wall_time_sec')
        if not _number(value):
            unknown += 1
            continue
        groups[row['task'], row['harness']].append((value, bool(row.get('passed'))))
    values = [value for group in groups.values() for value, _ in group]
    step = _nice_step(max(values, default=1) * 1.08)
    ceiling = max(step, math.ceil(max(values, default=1) * 1.08 / step) * step)
    width = max(800, 120 + 110 * len(tasks))
    left, right, top, bottom = 92, width - 24, 170, 470
    column = (right - left) / max(1, len(tasks))
    wrap_width = max(10, int(column / 7))
    labels = [textwrap.wrap(task, width=wrap_width, break_long_words=True, break_on_hyphens=True)
              for task in tasks]
    label_lines = max((len(label) for label in labels), default=1)
    foot_y = bottom + 40 + 18 * label_lines
    height = foot_y + 32
    title = 'Total tokens per task' if tokens else 'Wall time per task'
    unit = 'tokens' if tokens else 'seconds'
    y = lambda value: bottom - value / ceiling * (bottom - top)
    body = [_text(24, 32, title, size=22),
            _text(24, 56, 'Every known run, including failures; horizontal jitter is for visibility only.'),
            *_legend(arms, runs=True)]
    for i in range(round(ceiling / step) + 1):
        tick = i * step
        body += [_line(left, y(tick), right, y(tick)),
                 _text(left - 12, y(tick) + 4, _label(tick, step) + ('' if tokens else ' s'),
                       anchor='end', size=12)]
    body.append(_text(left, top - 10, unit, size=12))
    for i, task in enumerate(tasks):
        center = left + column * (i + 0.5)
        if i:
            body.append(_line(left + column * i, top, left + column * i, bottom, color='#EEF0F3'))
        for arm_index, arm in enumerate(arms):
            group = sorted(groups[task, arm])
            arm_x = center + (arm_index - 0.5) * column * 0.38
            for j, (value, passed) in enumerate(group):
                jitter = ((j * 0.6180339887498949 + 0.5) % 1 - 0.5) * min(column * 0.20, 22)
                body.append(_circle(arm_x + jitter, y(value), COLORS[arm_index], failed=not passed,
                                    extra=f'class="run-marker" data-passed="{str(passed).lower()}"'))
            if group:
                median_y = y(statistics.median(value for value, _ in group))
                body.append(_line(arm_x - 12, median_y, arm_x + 12, median_y,
                                  color=COLORS[arm_index], width=3, extra='class="median-tick"'))
        for j, label in enumerate(labels[i]):
            body.append(_text(center, bottom + 24 + j * 18, label, anchor='middle', size=12))
    body.append(_text(24, foot_y, f'{unknown} runs omitted: unknown {unit}. Medians use known runs, including failures.', size=12))
    return _svg(width, height, title,
                f'Per-task {unit} for {arms[0]} and {arms[1]}. Filled dots are passed runs; hollow dots are failed runs. '
                f'Short ticks show medians. {unknown} runs omitted for unknown {unit}.', body)


def render_charts(result: dict, rows: list[dict]) -> dict[str, str]:
    """Return the three SVG files used by comparison reports and export bundles."""
    return {'summary.svg': _summary(result),
            'tokens-per-task.svg': _strip(result, rows, tokens=True),
            'wall-time-per-task.svg': _strip(result, rows, tokens=False)}
