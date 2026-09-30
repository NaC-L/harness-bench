"""Deterministic, self-contained SVG comparison charts (standard library only)."""
from __future__ import annotations
import math
import statistics
import textwrap
from html import escape


MONO = "'Berkeley Mono','JetBrains Mono','Geist Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
SANS = "'Geist',Inter,system-ui,-apple-system,'Segoe UI',sans-serif"
PRIMARY, SECONDARY, TERTIARY = '#ededed', '#a1a1a1', '#757575'
CYAN, SUCCESS, DANGER = '#44cfff', '#4ade80', '#f4644a'
HAIRLINE, LINK = 'rgba(255,255,255,.06)', 'rgba(255,255,255,.14)'
WIDTH, LEFT, RIGHT = 760, 24, 736
TRACK_LEFT, TRACK_RIGHT = 242, 506
BASE_X, CAND_X, DELTA_X = 580, 658, 736


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _text(x, y, value, *, size=11, anchor='start', color=SECONDARY, sans=False, caps=False, extra=''):
    family = f' font-family="{escape(SANS)}"' if sans else ''
    tracking = ' letter-spacing=".06em"' if caps else ''
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" text-anchor="{anchor}" '
            f'fill="{color}"{family}{tracking} {extra}>{escape(str(value))}</text>')


def _line(x1, y1, x2, y2, *, color=HAIRLINE, dashed=False, extra=''):
    dash = ' stroke-dasharray="2,4"' if dashed else ''
    return (f'<line x1="{math.floor(x1) + .5:.1f}" y1="{math.floor(y1) + .5:.1f}" '
            f'x2="{math.floor(x2) + .5:.1f}" y2="{math.floor(y2) + .5:.1f}" '
            f'stroke="{color}" stroke-width="1" shape-rendering="crispEdges"{dash} {extra}/>')


def _square(x, y, color, *, size=8, failed=False, halo=False, opacity=1, extra=''):
    left, top = math.floor(x - size / 2), math.floor(y - size / 2)
    body = ''
    if halo:
        body = (f'<rect x="{left - 2}" y="{top - 2}" width="{size + 4}" height="{size + 4}" '
                f'fill="{color}" fill-opacity=".2" shape-rendering="crispEdges" class="hero-halo"/>')
    # Black interiors keep failed squares hollow even where a gridline crosses them.
    return body + (f'<rect x="{left}" y="{top}" width="{size}" height="{size}" '
                   f'fill="{"#000" if failed else color}" stroke="{color}" '
                   f'stroke-width="{1 if failed else 0}" opacity="{opacity:g}" '
                   f'shape-rendering="crispEdges" {extra}/>')


def _raw(value):
    return str(value) if _number(value) else 'unknown'


def _compact(value, unit):
    if not _number(value):
        return 'UNKNOWN'
    if unit == 'cost':
        return f'${value:.4f}' if abs(value) < .01 and value != 0 else f'${value:.3f}'
    suffix = 's' if unit == 'seconds' else ''
    if abs(value) >= 1_000_000:
        return f'{value / 1_000_000:.1f}m{suffix}'
    if abs(value) >= 1000:
        return f'{value / 1000:.1f}k{suffix}'
    return f'{value:.2f}'.rstrip('0').rstrip('.') + suffix


def _change(baseline, candidate):
    if not _number(baseline) or not _number(candidate) or baseline == 0:
        return None
    return (candidate / baseline - 1) * 100


def _signed(value):
    if value is None:
        return 'UNKNOWN'
    return ('−' if value < 0 else '+') + f'{abs(value):.1f}%'


def _delta_color(baseline, candidate, margin):
    if _change(baseline, candidate) is None:
        return SECONDARY
    if candidate < baseline * (1 - margin):
        return SUCCESS
    if candidate > baseline * (1 + margin):
        return DANGER
    return SECONDARY


def _caption_lines(caption):
    return textwrap.wrap(caption.upper(), width=106, break_long_words=False, break_on_hyphens=False)


def _finish(title, desc, body, bottom, caption):
    lines = _caption_lines(caption)
    for i, line in enumerate(lines):
        body.append(_text(LEFT, bottom + 26 + 14 * i, line, size=10, color=TERTIARY, caps=True,
                          extra='class="caption"'))
    height = bottom + 48 + 14 * (len(lines) - 1)
    return '\n'.join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" role="img" aria-labelledby="chart-title chart-desc">',
        f'<title id="chart-title">{escape(title)}</title>',
        f'<desc id="chart-desc">{escape(desc)}</desc>',
        f'<rect width="{WIDTH}" height="{height}" fill="#000" class="panel-background"/>',
        f'<rect x=".5" y=".5" width="{WIDTH - 1}" height="{height - 1}" fill="none" '
        f'stroke="{HAIRLINE}" stroke-width="1" shape-rendering="crispEdges"/>',
        f'<g font-family="{escape(MONO)}" style="font-variant-numeric:tabular-nums">',
        *body, '</g>', '</svg>', ''])


def _legend(arms):
    labels = [f'{arm.upper()} ({role})' for arm, role in zip(arms, ('BASELINE', 'CANDIDATE'))]
    widths = [13 + len(label) * 6.6 for label in labels]
    x = RIGHT - sum(widths) - 20
    body = []
    for label, width, color in zip(labels, widths, (TERTIARY, CYAN)):
        body += [_square(x + 3.5, 57, color, size=7),
                 _text(x + 13, 61, label, size=10, color=TERTIARY, caps=True)]
        x += width + 20
    return body


def _header(label):
    return [_text(LEFT, 120, label, size=10, color=TERTIARY, caps=True),
            *[_text(x, 120, name, size=10, anchor='end', color=TERTIARY, caps=True)
              for x, name in ((BASE_X, 'BASE'), (CAND_X, 'CAND'), (DELTA_X, 'Δ'))]]


def _columns(y, baseline, candidate, unit, margin):
    return [_text(BASE_X, y + 4, _compact(baseline, unit), anchor='end'),
            _text(CAND_X, y + 4, _compact(candidate, unit), anchor='end', color=CYAN),
            _text(DELTA_X, y + 4, _signed(_change(baseline, candidate)), anchor='end',
                  color=_delta_color(baseline, candidate, margin))]


def _summary(result):
    arms = (result['baseline'], result['candidate'])
    metrics = [('Tokens / correct · total', 'tokens_per_correct', 'tokens'),
               ('Tokens / correct · uncached', 'uncached_tokens_per_correct', 'tokens'),
               ('Cost / correct', 'cost_per_correct', 'cost'),
               ('Median wall', 'median_wall_time_sec', 'seconds'),
               ('P90 wall', 'p90_wall_time_sec', 'seconds')]
    cards = [result['scorecards'][arm] for arm in arms]
    pairs = [tuple(card.get(key) for card in cards) for _, key, _ in metrics]
    changes = [_change(b, c) for b, c in pairs]
    margin = result['margin'] * 100
    extent = max([margin, 1, *(abs(value) for value in changes if value is not None)]) * 1.3
    x = lambda value: TRACK_LEFT + (value + extent) / (2 * extent) * (TRACK_RIGHT - TRACK_LEFT)
    verdict = result['verdict'].upper()
    relation = {'better': 'BEATS', 'worse': 'LOSES TO', 'tradeoff': 'TRADES OFF WITH',
                'equivalent': 'MATCHES', 'inconclusive': 'VS'}[result['verdict']]
    title = f'VERDICT: {verdict} — {arms[1].upper()} {relation} {arms[0].upper()}'
    top, bottom = 132, 332
    body = [_text(LEFT, 32, title, size=16, color=PRIMARY, sans=True), *_legend(arms),
            _text(LEFT, 86, f'DITHER = ±{margin:g}% MARGIN', size=10, color=TERTIARY, caps=True),
            _text(RIGHT, 86, '← LOWER IS BETTER', size=10, anchor='end', color=TERTIARY, caps=True),
            *_header('METRIC'),
            '<defs><pattern id="margin-dither" width="2" height="2" patternUnits="userSpaceOnUse" '
            'shape-rendering="crispEdges">'
            f'<rect width="1" height="1" fill="{TERTIARY}" fill-opacity=".25"/>'
            f'<rect x="1" y="1" width="1" height="1" fill="{TERTIARY}" fill-opacity=".25"/>'
            '</pattern></defs>',
            f'<rect x="{x(-margin):.2f}" y="{top}" width="{x(margin) - x(-margin):.2f}" '
            f'height="{bottom - top}" fill="url(#margin-dither)" class="margin-band" '
            f'data-margin="{result["margin"]}" shape-rendering="crispEdges"/>']
    for i in range(5):
        tick = -extent + i * extent / 2
        body += [_line(x(tick), top, x(tick), bottom, dashed=True, extra='class="gridline"'),
                 _text(x(tick), 120, ('−' if tick < 0 else '+' if tick > 0 else '') + f'{abs(tick):.1f}%',
                       anchor='middle', color=TERTIARY, extra=f'class="scale-tick" data-value="{tick}"')]
    desc = [title + '. Candidate relative changes; lower is better.',
            f'Ordered-dither band: ±{margin:g}% margin. Undefined zero-baseline ratios and missing metrics are unknown.']
    for i, ((label, key, unit), (baseline, candidate), change) in enumerate(zip(metrics, pairs, changes)):
        y = top + 20 + i * 40
        body += [f'<g class="metric-row" data-metric="{key}" data-change="{_raw(change)}">',
                 _line(LEFT, y + 20, RIGHT, y + 20),
                 _text(LEFT, y + 4, label, size=12, color=PRIMARY, sans=True)]
        if change is None:
            body.append(_text(x(0), y + 4, 'UNKNOWN', anchor='middle', color=TERTIARY))
        else:
            color = _delta_color(baseline, candidate, result['margin'])
            tip = x(change)
            direction = -1 if change < 0 else 1
            end = math.floor(tip - direction * 7) + .5
            mid_y = math.floor(y) + .5
            body.append(_line(x(0), y, end, y, color=color,
                              extra='class="delta-arrow" stroke-dasharray="2,2"'))
            if change != 0:
                body.append(f'<path d="M {end - direction * 3:.1f} {mid_y - 3:.1f} '
                            f'L {end:.1f} {mid_y:.1f} L {end - direction * 3:.1f} {mid_y + 3:.1f}" '
                            f'fill="none" stroke="{color}" stroke-width="1" shape-rendering="crispEdges"/>')
            body += [_square(tip, y, color, halo=True, extra='class="summary-marker"'),
                     _text(tip - direction * 9, y - 8, _signed(change), color=color,
                           anchor='start' if direction < 0 else 'end')]
        body += [*_columns(y, baseline, candidate, unit, result['margin']), '</g>']
        desc.append(f'{label}: {arms[0]} baseline={_raw(baseline)} {unit}; '
                    f'{arms[1]} candidate={_raw(candidate)} {unit}; delta={_raw(change)}%, {_signed(change)}.')
    better = sum(_delta_color(b, c, result['margin']) == SUCCESS for b, c in pairs)
    worse = sum(_delta_color(b, c, result['margin']) == DANGER for b, c in pairs)
    known = sum(change is not None for change in changes)
    finding = f'{arms[1]} IMPROVES {better}/{known} KNOWN EFFICIENCY METRICS'
    if worse:
        finding += f'; WORSENS {worse}/{known}'
    if not known:
        finding = f'{arms[1]} HAS NO KNOWN RELATIVE EFFICIENCY METRICS'
    caption = (f'{finding} · ±{margin:g}% MARGIN · SPEND / CORRECT INCLUDES FAILED ATTEMPTS '
               f'· WALL = MEDIAN / P90 OF KNOWN RUNS · {5 - known} UNKNOWN METRICS').upper()
    desc += [f'{arms[0]}: {cards[0]["passed"]}/{cards[0]["runs"]} correct runs; '
             f'{arms[1]}: {cards[1]["passed"]}/{cards[1]["runs"]} correct runs.', caption]
    return _finish(title, ' '.join(desc), body, bottom, caption)


def _tokens(row):
    metrics = row.get('metrics') or {}
    if not _number(metrics.get('input_tokens')) or not _number(metrics.get('output_tokens')):
        return None
    return sum(metrics.get(key) if _number(metrics.get(key)) else 0
               for key in ('input_tokens', 'cache_read_tokens', 'cache_write_tokens', 'output_tokens'))


def _task_label(task):
    # Conservative widths for the system sans fallback; keep full names in the data description.
    def width(label):
        return sum(.28 if c in 'ilI.,:!| ' else .9 if c in 'MWmw@' else .58 for c in label) * 13
    if width(task) <= TRACK_LEFT - LEFT - 20:
        return task
    label = task
    while label and width(label + '…') > TRACK_LEFT - LEFT - 20:
        label = label[:-1]
    return label + '…'


def _strip(result, rows, *, tokens):
    arms = (result['baseline'], result['candidate'])
    selected = [row for row in rows if row.get('harness') in arms]
    tasks = sorted({row['task'] for row in selected})
    groups = {(task, arm): [] for task in tasks for arm in arms}
    unknown = 0
    for row in selected:
        value = _tokens(row) if tokens else row.get('wall_time_sec')
        if not _number(value):
            unknown += 1
            continue
        groups[row['task'], row['harness']].append((value, bool(row.get('passed'))))
    values = [value for group in groups.values() for value, _ in group]
    low, high = min([0, *values]), max(values, default=1)
    if low == high:
        high = low + 1
    x = lambda value: TRACK_LEFT + (value - low) / (high - low) * (TRACK_RIGHT - TRACK_LEFT)
    top, bottom = 132, 132 + 40 * len(tasks)
    title = 'Total tokens per task' if tokens else 'Wall time per task'
    unit = 'tokens' if tokens else 'seconds'
    body = [_text(LEFT, 32, title, size=17, color=PRIMARY, sans=True), *_legend(arms),
            _square(LEFT + 3.5, 82, TERTIARY, size=7, failed=True),
            _text(LEFT + 14, 86, 'HOLLOW = FAILED RUN', size=10, color=TERTIARY, caps=True),
            _square(LEFT + 171, 82, TERTIARY, size=4, opacity=.35),
            _text(LEFT + 182, 86, 'FAINT = EACH RUN', size=10, color=TERTIARY, caps=True),
            _text(RIGHT, 86, '← FEWER IS BETTER' if tokens else '← FASTER IS BETTER', size=10, anchor='end',
                  color=TERTIARY, caps=True),
            *_header('TASK')]
    for i in range(5):
        tick = low + i * (high - low) / 4
        body += [_line(x(tick), top, x(tick), bottom, dashed=True, extra='class="gridline"'),
                 _text(x(tick), 120, _compact(tick, unit), anchor='middle', color=TERTIARY,
                       extra=f'class="scale-tick" data-value="{tick}"')]
    desc = [f'Per-task {unit}: candidate {arms[1]} vs baseline {arms[0]}. Lower is better. '
            'Faint squares show each known run; hollow squares are failed runs. Large squares show medians '
            'of known runs, including failures; candidate medians have a two-pixel halo.']
    fewer, more, comparable = 0, 0, 0
    for i, task in enumerate(tasks):
        y = top + 20 + i * 40
        medians = [statistics.median(value for value, _ in groups[task, arm]) if groups[task, arm] else None
                   for arm in arms]
        baseline, candidate = medians
        if all(_number(value) for value in medians):
            comparable += 1
            fewer += candidate < baseline
            more += candidate > baseline
        body += [f'<g class="task-row" data-task="{escape(task)}">', f'<title>{escape(task)}</title>',
                 _line(LEFT, y + 20, RIGHT, y + 20),
                 _text(LEFT, y + 4, _task_label(task), size=13, color=PRIMARY, sans=True)]
        if all(_number(value) for value in medians):
            body.append(_line(x(baseline), y, x(candidate), y, color=LINK, extra='class="median-link"'))
        for arm_index, (arm, median, color) in enumerate(zip(arms, medians, (TERTIARY, CYAN))):
            group = sorted(groups[task, arm])
            desc.append(f'{task}, {arm}: runs [' + ', '.join(f'{_raw(value)} {unit} ({"passed" if passed else "failed"})'
                                                            for value, passed in group) +
                        f']; median={_raw(median)} {unit}.')
            for j, (value, passed) in enumerate(group):
                run_y = y + (-8 if arm_index == 0 else 8) + (j % 3 - 1)
                body.append(_square(x(value), run_y, color, size=4, failed=not passed, opacity=.35,
                                    extra=f'class="run-marker" data-arm="{escape(arm)}" '
                                    f'data-passed="{str(passed).lower()}" data-value="{value}"'))
            if median is not None:
                body.append(_square(x(median), y, color, halo=arm_index == 1,
                                    extra=f'class="median-marker" data-arm="{escape(arm)}" data-value="{median}"'))
        body += [*_columns(y, baseline, candidate, unit, result['margin']), '</g>']
        desc.append(f'{task}: delta={_raw(_change(baseline, candidate))}%, {_signed(_change(baseline, candidate))}.')
    if not comparable:
        finding = f'{arms[1]} HAS NO COMPARABLE {unit} MEDIANS'
    elif not fewer and not more:
        finding = f'{arms[1]} MATCHES {arms[0]} ON {comparable}/{len(tasks)} TASKS'
    elif more > fewer:
        finding = (f'{arms[1]} USES MORE TOKENS' if tokens else f'{arms[1]} RUNS SLOWER') + f' ON {more}/{comparable} TASKS'
    else:
        finding = (f'{arms[1]} USES FEWER TOKENS' if tokens else f'{arms[1]} RUNS FASTER') + f' ON {fewer}/{comparable} TASKS'
    counts = [len(group) for group in groups.values()]
    trials = (f'MEDIAN OF {counts[0]} RUNS PER ARM' if counts and len(set(counts)) == 1
              else f'MEDIAN OF KNOWN RUNS ({min(counts, default=0)}–{max(counts, default=0)} PER ARM/TASK)')
    equation = 'TOKENS = INPUT + CACHE READ + CACHE WRITE + OUTPUT' if tokens else 'WALL = ELAPSED SECONDS'
    caption = f'{finding} · {trials} · {equation} · {unknown} RUNS OMITTED: UNKNOWN {unit}'.upper()
    if comparable != len(tasks):
        caption += f' · {len(tasks) - comparable} TASKS WITHOUT PAIRED MEDIANS'
    desc.append(caption)
    return _finish(title, ' '.join([finding + '.', *desc]), body, bottom, caption)


def render_charts(result: dict, rows: list[dict]) -> dict[str, str]:
    """Return the three SVG files used by comparison reports and export bundles."""
    return {'summary.svg': _summary(result),
            'tokens-per-task.svg': _strip(result, rows, tokens=True),
            'wall-time-per-task.svg': _strip(result, rows, tokens=False)}
