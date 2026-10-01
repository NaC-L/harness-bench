"""Comparable cohorts separate harness/version/config/task/context/model.

pass@k is the unbiased estimator 1 - C(n-c,k)/C(n,k), computed per task.
These tiny seed tasks are pipeline checks, not evidence of general coding capability.
"""
from __future__ import annotations
import difflib
import json
import math
import random
import re
import shlex
import statistics
from collections import defaultdict
from pathlib import Path
from .environment import STATE_ENV


def pass_at_k(n: int, c: int, k: int) -> float | None:
    if k < 1 or n < k:
        return None
    return 1 - math.comb(n - c, k) / math.comb(n, k) if n - c >= k else 1.0


def median(values):
    known = [v for v in values if isinstance(v, (float, int)) and not isinstance(v, bool)]
    return statistics.median(known) if known else None


def summarize(rows: list[dict], k: int = 1) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        key = (row['harness'], row.get('harness_version'), row.get('config_hash'),
               row['task'], row.get('prompt_hash'), row.get('task_hash'),
               json.dumps(row.get('context_hashes', {}), sort_keys=True),
               tuple(sorted((row.get('metrics') or {}).get('models', []))))
        groups[key].append(row)
    summaries = []
    for (h, version, config, task, prompt, task_hash, context, models), records in sorted(groups.items(), key=lambda kv: str(kv[0])):
        metrics = [r.get('metrics') or {} for r in records]
        successes = sum(bool(r.get('passed')) for r in records)
        summary = {'harness': h, 'version': version, 'config_hash': config, 'task': task,
                   'prompt_hash': prompt, 'runs': len(records), 'passed': successes,
                   'task_hash': task_hash, 'context_hashes': json.loads(context), 'models': list(models),
                   f'pass@{k}': pass_at_k(len(records), successes, k),
                   'timeouts': sum(bool(r.get('timed_out')) for r in records),
                   'tampered': sum(bool(r.get('tampered_files')) for r in records),
                   'wall_time_median_sec': median(r.get('wall_time_sec') for r in records),
                   'wall_time_stdev_sec': statistics.stdev([r['wall_time_sec'] for r in records if r.get('wall_time_sec') is not None])
                        if sum(r.get('wall_time_sec') is not None for r in records) > 1 else None,
                   'cost_known_runs': sum(m.get('cost_usd') is not None for m in metrics)}
        for field in ('cost_usd', 'input_tokens', 'output_tokens', 'cache_read_tokens', 'cache_write_tokens',
                      'requests', 'tool_calls', 'tool_calls_per_request'):
            summary[field + '_median'] = median(m.get(field) for m in metrics)
        summaries.append(summary)
    return summaries


def load(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    for n, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except ValueError as exc:
                raise ValueError(f'{path}:{n}: invalid JSON') from exc
    return rows


def render(rows: list[dict], k: int = 1) -> str:
    def fmt(v, digits=2):
        return 'unknown' if v is None else f'{v:.{digits}f}'
    lines = ['| Harness | Task | Cohort | Pass/runs | pass@' + str(k) + ' | Median s | Median $ (known runs) | Tools/request |',
             '|---|---|---|---:|---:|---:|---:|---:|']
    for s in summarize(rows, k):
        lines.append(f"| {s['harness']} | {s['task']} | {(s['config_hash'] or 'unknown')[:8]} | {s['passed']}/{s['runs']} | "
                     f"{fmt(s[f'pass@{k}'])} | {fmt(s['wall_time_median_sec'])} | "
                     f"{fmt(s['cost_usd_median'], 4)} ({s['cost_known_runs']}) | {fmt(s['tool_calls_per_request_median'])} |")
    lines += ['', 'Unknown values are not zero. Cohorts also separate version and prompt hash; use --json for full keys.',
              'Seed tasks validate the pipeline only. Keep the model/provider/effort fixed to compare harnesses,',
              'and use multiple tasks and repeated trials before drawing conclusions.']
    return '\n'.join(lines)


# --- Goal-aligned arm comparison -------------------------------------------------
# Correctness and safety are non-inferiority gates (exact, no margin): a single extra
# failure, regression, timeout or tampered run makes the candidate worse. Tokens and
# time are efficiency dimensions judged with a relative noise margin. Unknown data is
# never treated as zero; it either skips a component (with a warning) or makes the
# verdict inconclusive.

def _known(values):
    return [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]


def _count(m: dict, key: str) -> float:
    value = m.get(key)
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else 0


_RUNNER_EXCEPTION = re.compile(
    r'^(?:OSError|FileNotFoundError|PermissionError|NotADirectoryError|IsADirectoryError|'
    r'FileExistsError|CalledProcessError|SubprocessError|TimeoutExpired|ValueError):')
_PROVIDER_ERROR = re.compile(
    r'^(?:(?:AuthenticationError|PermissionDeniedError|RateLimitError|APIConnectionError|'
    r'APITimeoutError|InternalServerError|APIError):|'
    r'(?:provider|API) (?:error|authentication failed|rate limit|unavailable)\b)', re.I)


def _classification(row: dict) -> str:
    """Classify recorded evidence, not exit codes or missing legacy fields as infrastructure."""
    if row.get('passed') is True:
        return 'success'
    if row.get('timed_out') or row.get('check_timed_out') or row.get('tampered_files') \
            or row.get('regressions'):
        return 'solution_failure'
    errors = row.get('errors') or []
    if any(isinstance(error, str) and (_RUNNER_EXCEPTION.match(error) or _PROVIDER_ERROR.match(error))
           for error in errors):
        return 'infrastructure_failure'
    if any(_count(row, key) > 0 for key in ('tests_fail', 'visible_tests_fail', 'hidden_tests_fail')) \
            or row.get('check_exit_code') not in (None, 0) \
            or row.get('agent_completion') in ('incomplete', 'error'):
        return 'solution_failure'
    return 'unknown'


def scorecard(rows: list[dict]) -> dict:
    """Correctness, token and time/safety totals for one harness's rows."""
    runs = len(rows)
    passed = sum(bool(r.get('passed')) for r in rows)
    classifications = dict.fromkeys(('success', 'solution_failure', 'infrastructure_failure', 'unknown'), 0)
    for row in rows:
        classifications[_classification(row)] += 1
    metrics = [r.get('metrics') or {} for r in rows]

    def total(key):
        known = _known(r.get(key) for r in rows)
        return sum(known) if known else None

    token_unknown = sum(m.get('input_tokens') is None or m.get('output_tokens') is None for m in metrics)
    tokens = {'total_tokens': None, 'uncached_tokens': None, 'auxiliary_calls': None,
              'auxiliary_tokens': None, 'cost_usd': None, 'tokens_per_correct': None,
              'uncached_tokens_per_correct': None, 'cost_per_correct': None}
    if runs and not token_unknown:
        uncached = sum(_count(m, 'input_tokens') + _count(m, 'cache_write_tokens') + _count(m, 'output_tokens')
                       for m in metrics)
        all_tokens = uncached + sum(_count(m, 'cache_read_tokens') for m in metrics)
        costs = [m.get('cost_usd') for m in metrics]
        cost = None if any(c is None for c in costs) else sum(costs)
        tokens.update(total_tokens=all_tokens, uncached_tokens=uncached,
                      auxiliary_calls=sum(_count(m, 'auxiliary_calls') for m in metrics),
                      auxiliary_tokens=sum(_count(m, 'auxiliary_tokens') for m in metrics),
                      cost_usd=cost)
        if passed:
            tokens.update(tokens_per_correct=all_tokens / passed, uncached_tokens_per_correct=uncached / passed,
                          cost_per_correct=None if cost is None else cost / passed)
    walls = sorted(_known(r.get('wall_time_sec') for r in rows))
    verification = [m.get('verified_after_final_edit') for m in metrics]
    verification_known = sum(v is not None for v in verification)
    verified = sum(v is True for v in verification)
    return {
        'runs': runs, 'passed': passed, 'pass_rate': passed / runs if runs else None,
        'classification_counts': classifications,
        'visible_passed': sum(r.get('visible_passed') is True for r in rows),
        'hidden_tests_pass': total('hidden_tests_pass'), 'hidden_tests_fail': total('hidden_tests_fail'),
        'regression_runs': sum(bool(r.get('regressions')) for r in rows),
        'regression_unknown_runs': sum(r.get('regressions') is None for r in rows),
        'unfinished_runs': sum(r.get('agent_exit_code') not in (None, 0) or bool(r.get('timed_out'))
                               or r.get('agent_completion') in ('incomplete', 'error') for r in rows),
        'token_unknown_runs': token_unknown, **tokens,
        'retries': total('agent_retries'),
        'median_wall_time_sec': statistics.median(walls) if walls else None,
        'p90_wall_time_sec': walls[math.ceil(0.9 * len(walls)) - 1] if walls else None,
        'max_wall_time_sec': walls[-1] if walls else None,
        'timeouts': sum(bool(r.get('timed_out') or r.get('check_timed_out')) for r in rows),
        'tampered_runs': sum(bool(r.get('tampered_files')) for r in rows),
        'verification_known_runs': verification_known, 'verified_runs': verified,
        'verification_rate': verified / verification_known if verification_known else None,
        'reproduced_runs': sum(m.get('reproduced_before_first_edit') is True for m in metrics),
    }


def _exact(b, c, higher_better: bool) -> str:
    if b == c:
        return 'same'
    return 'better' if (c > b) == higher_better else 'worse'


def _combine(results: list[str]) -> str:
    if 'worse' in results:
        return 'worse'
    return 'better' if 'better' in results else 'same'


# Efficiency effects are candidate/baseline ratios with a percentile bootstrap that resamples
# runs within each (arm, task) cell, so task mix stays fixed. Non-inferiority design: a loss
# is ruled out only if the interval stays under 1 + margin, and a gain or an equivalence is
# claimed only if the interval clears 1 - margin or sits inside the band.
CONFIDENCE = 0.95
RESAMPLES = 2000
_EFFICIENCY = {'tokens': ('tokens_per_correct', 'uncached_tokens_per_correct'),
               'time': ('median_wall_time_sec', 'p90_wall_time_sec')}
_LABELS = {'tokens_per_correct': 'total tokens per correct', 'uncached_tokens_per_correct': 'uncached tokens per correct',
           'median_wall_time_sec': 'median wall time', 'p90_wall_time_sec': 'p90 wall time'}


def _ratio(b: dict, c: dict, key: str) -> float | None:
    if b[key] is None or c[key] is None or b[key] <= 0:
        return None
    return c[key] / b[key]


def ratio_intervals(b_rows: list[dict], c_rows: list[dict], keys: tuple[str, ...], *,
                    resamples: int = RESAMPLES, confidence: float = CONFIDENCE, seed: int = 0) -> dict:
    """Point ratio and bootstrap interval per key; interval bounds are None when undefined."""
    b, c = scorecard(b_rows), scorecard(c_rows)
    out = {key: {'ratio': _ratio(b, c, key), 'low': None, 'high': None} for key in keys}
    if any(v['ratio'] is None for v in out.values()):
        return out
    cells = [defaultdict(list), defaultdict(list)]
    for cell, rows in zip(cells, (b_rows, c_rows)):
        for r in rows:
            cell[r['task']].append(r)
    rng = random.Random(seed)
    samples = {key: [] for key in keys}
    for _ in range(resamples):
        b_s, c_s = (scorecard([rng.choice(runs) for runs in cell.values() for _ in runs]) for cell in cells)
        for key in keys:
            value = _ratio(b_s, c_s, key)
            if value is not None:
                samples[key].append(value)
    tail = (1 - confidence) / 2
    for key, values in samples.items():
        # Undefined resamples (e.g. no correct run drawn) leave the interval unknown, not narrower.
        if len(values) < resamples * (1 - tail):
            continue
        values.sort()
        n = len(values)
        out[key].update(low=values[int(tail * n)], high=values[math.ceil((1 - tail) * n) - 1])
    return out


def _efficiency(intervals: dict, keys: tuple[str, ...], margin: float) -> str:
    """Lower is better: worse | uncertain (a material loss is not ruled out) | better | same | non-inferior."""
    if any(intervals[k]['ratio'] is None for k in keys):
        return 'unknown'
    bounds = [(intervals[k]['low'], intervals[k]['high']) for k in keys]
    if any(low is None for low, _ in bounds):
        return 'uncertain'
    if any(low > 1 + margin for low, _ in bounds):
        return 'worse'
    if any(high > 1 + margin for _, high in bounds):
        return 'uncertain'
    if any(high < 1 - margin for _, high in bounds):
        return 'better'
    return 'same' if all(low >= 1 - margin for low, _ in bounds) else 'non-inferior'


def _interval_text(item: dict, confidence: float) -> str:
    if item['ratio'] is None:
        return 'unknown'
    bounds = (f"{item['low']:.2f}–{item['high']:.2f}" if item['low'] is not None else 'undefined')
    return f"×{item['ratio']:.2f} ({confidence:.0%} CI {bounds})"


def interval_lines(result: dict) -> list[str]:
    """Candidate/baseline ratios with their bootstrap intervals, one bullet per efficiency measure."""
    return [f"- {_LABELS[key]}: {_interval_text(result['intervals'][key], result['confidence'])}"
            for keys in _EFFICIENCY.values() for key in keys]


def compare(rows: list[dict], baseline: str, candidate: str, *, margin: float = 0.10,
            min_trials: int = 3) -> dict:
    """Rule-based verdict for candidate vs baseline: better|worse|tradeoff|equivalent|inconclusive."""
    if baseline == candidate:
        raise ValueError('baseline and candidate must differ')
    arms = {name: [r for r in rows if r.get('harness') == name] for name in (baseline, candidate)}
    for name, arm_rows in arms.items():
        if not arm_rows:
            raise ValueError(f'no runs for harness: {name}')
    reasons, warnings = [], []
    tasks = {name: {r['task'] for r in arm_rows} for name, arm_rows in arms.items()}
    b_tasks, c_tasks = tasks[baseline], tasks[candidate]
    if b_tasks != c_tasks:
        reasons.append(f'task sets differ: {sorted(b_tasks)} vs {sorted(c_tasks)}')
    for name, arm_rows in arms.items():
        for task in sorted(tasks[name]):
            n = sum(r['task'] == task for r in arm_rows)
            if n < min_trials:
                reasons.append(f'{name}/{task}: {n} trials < {min_trials}')
    for task in sorted(b_tasks & c_tasks):
        task_rows = [r for arm_rows in arms.values() for r in arm_rows if r['task'] == task]
        if len({r.get('prompt_hash') for r in task_rows}) != 1 or len({r.get('task_hash') for r in task_rows}) != 1:
            reasons.append(f'task inputs differ for {task}')

    def distinct(name, key):
        return {json.dumps(r.get(key), sort_keys=True) for r in arms[name]}
    if distinct(baseline, 'harness_kind') == distinct(candidate, 'harness_kind') \
            and distinct(baseline, 'context_hashes') != distinct(candidate, 'context_hashes'):
        warnings.append('inherited harness context differs')
    versions = {name: sorted({str(r.get('harness_version')) for r in arm_rows}) for name, arm_rows in arms.items()}
    if versions[baseline] != versions[candidate]:
        warnings.append(f"harness versions differ: {', '.join(versions[baseline])} vs {', '.join(versions[candidate])}")
    all_rows = arms[baseline] + arms[candidate]
    shared = sum(r.get('isolated_state') is not True for r in all_rows if r.get('harness_kind') in STATE_ENV)
    if shared:
        warnings.append(f"operator state not isolated for {shared} runs: the harness may have read the "
                        "operator's personal instructions, settings and MCP servers")
    above = sum(bool(r.get('ancestor_context')) for r in all_rows)
    if above:
        warnings.append(f'project context files above the workdir for {above} runs')

    b, c = scorecard(arms[baseline]), scorecard(arms[candidate])
    if b['pass_rate'] == c['pass_rate'] == 1.0:
        warnings.append('correctness at ceiling: every run passed, so these tasks cannot distinguish correctness')
    elif b['pass_rate'] == c['pass_rate'] == 0.0:
        warnings.append('correctness at floor: no run passed')

    def rate(card, key):
        return card[key] / card['runs']
    correctness = [_exact(b['pass_rate'], c['pass_rate'], True),
                   _exact(rate(b, 'unfinished_runs'), rate(c, 'unfinished_runs'), False)]
    unknown_regressions = b['regression_unknown_runs'] + c['regression_unknown_runs']
    if unknown_regressions:
        warnings.append(f'regression data unknown for {unknown_regressions} runs; regression comparison skipped')
    else:
        correctness.append(_exact(rate(b, 'regression_runs'), rate(c, 'regression_runs'), False))
    safety = [_exact(rate(b, 'timeouts'), rate(c, 'timeouts'), False),
              _exact(rate(b, 'tampered_runs'), rate(c, 'tampered_runs'), False)]
    if b['verification_rate'] is None or c['verification_rate'] is None:
        warnings.append('verification unknown; verification comparison skipped')
    else:
        safety.append(_exact(b['verification_rate'], c['verification_rate'], True))
    intervals = ratio_intervals(arms[baseline], arms[candidate], tuple(k for ks in _EFFICIENCY.values() for k in ks))
    dimensions = {'correctness': _combine(correctness),
                  'tokens': _efficiency(intervals, _EFFICIENCY['tokens'], margin),
                  'time': _efficiency(intervals, _EFFICIENCY['time'], margin),
                  'safety': _combine(safety)}
    per_task = {}
    for task in sorted(b_tasks | c_tasks):
        cards = {name: scorecard([r for r in arm_rows if r['task'] == task])
                 for name, arm_rows in arms.items()}
        tb, tc = cards[baseline], cards[candidate]
        per_task[task] = {
            'scorecards': cards,
            'ratios': {key: _ratio(tb, tc, key) for keys in _EFFICIENCY.values() for key in keys},
            'pass_rate_difference': (tc['pass_rate'] - tb['pass_rate']
                                     if tb['pass_rate'] is not None and tc['pass_rate'] is not None else None),
        }
    infrastructure = sum(card['classification_counts']['infrastructure_failure'] for card in (b, c))
    infrastructure_reason = (f"infrastructure contamination: {baseline} "
                             f"{b['classification_counts']['infrastructure_failure']}/{b['runs']} runs; "
                             f"{candidate} {c['classification_counts']['infrastructure_failure']}/{c['runs']} runs; "
                             "all failed attempts retained")

    values = dimensions.values()
    efficiency = (dimensions['tokens'], dimensions['time'])
    if reasons:
        verdict = 'inconclusive'
    elif 'worse' in (dimensions['correctness'], dimensions['safety']):
        verdict = 'worse'
    elif infrastructure:
        verdict = 'inconclusive'
        reasons.append(infrastructure_reason)
    elif 'unknown' in efficiency:
        verdict = 'inconclusive'
        if dimensions['tokens'] == 'unknown':
            reasons.append('token usage unknown')
        if dimensions['time'] == 'unknown':
            reasons.append('runtime unknown')
    elif 'uncertain' in efficiency:
        verdict = 'inconclusive'
        for name, keys in _EFFICIENCY.items():
            if dimensions[name] == 'uncertain':
                reasons += [f"{_LABELS[k]} {_interval_text(intervals[k], CONFIDENCE)} may be more than "
                            f"{margin:.0%} worse; more trials needed" for k in keys
                            if _efficiency(intervals, (k,), margin) == 'uncertain']
    elif 'worse' in efficiency and 'better' in values:
        verdict = 'tradeoff'
    elif 'worse' in values:
        verdict = 'worse'
    elif 'better' in values:
        verdict = 'better'
    elif 'non-inferior' in efficiency:
        verdict = 'inconclusive'
        reasons += [f"{name}: no loss beyond {margin:.0%}, but neither a gain nor equivalence is established"
                    for name in _EFFICIENCY if dimensions[name] == 'non-inferior']
    else:
        verdict = 'equivalent'
    if infrastructure and infrastructure_reason not in reasons:
        reasons.append(infrastructure_reason)
    return {'baseline': baseline, 'candidate': candidate, 'margin': margin, 'min_trials': min_trials,
            'confidence': CONFIDENCE, 'resamples': RESAMPLES, 'intervals': intervals,
            'verdict': verdict, 'dimensions': dimensions, 'reasons': reasons, 'warnings': warnings,
            'scorecards': {baseline: b, candidate: c}, 'per_task': per_task}


def _classification_lines(result: dict) -> list[str]:
    lines = ['| Arm | Success | Solution failure | Infrastructure failure | Unknown |',
             '|---|---:|---:|---:|---:|']
    for name in (result['baseline'], result['candidate']):
        counts = result['scorecards'][name]['classification_counts']
        lines.append(f"| {name} | {counts['success']} | {counts['solution_failure']} | "
                     f"{counts['infrastructure_failure']} | {counts['unknown']} |")
    return lines


def _per_task_lines(result: dict) -> list[str]:
    def fmt(value, spec='.0f'):
        return 'unknown' if value is None else format(value, spec)

    lines = ['Per-task scorecards (all attempts retained):', '',
             '| Task | Arm | Passed/runs | Total tokens/correct | Uncached tokens/correct | Median wall s | '
             'P90 wall s | Success / solution failure / infrastructure failure / unknown |',
             '|---|---|---:|---:|---:|---:|---:|---|']
    for task, item in result['per_task'].items():
        for name in (result['baseline'], result['candidate']):
            card = item['scorecards'][name]
            counts = card['classification_counts']
            lines.append(f"| {task} | {name} | {card['passed']}/{card['runs']} | "
                         f"{fmt(card['tokens_per_correct'])} | {fmt(card['uncached_tokens_per_correct'])} | "
                         f"{fmt(card['median_wall_time_sec'], '.1f')} | {fmt(card['p90_wall_time_sec'], '.1f')} | "
                         f"{counts['success']} / {counts['solution_failure']} / "
                         f"{counts['infrastructure_failure']} / {counts['unknown']} |")
    lines += ['', 'Per-task point effects (descriptive only; no per-task winner or confidence claim):', '',
              '| Task | Pass-rate difference (candidate - baseline, pp) | Total tokens/correct ratio | '
              'Uncached tokens/correct ratio | Median wall ratio | P90 wall ratio |',
              '|---|---:|---:|---:|---:|---:|']
    for task, item in result['per_task'].items():
        difference = item['pass_rate_difference']
        ratios = [fmt(item['ratios'][key], '.2f') for keys in _EFFICIENCY.values() for key in keys]
        lines.append(f"| {task} | {fmt(None if difference is None else difference * 100, '+.1f')} | "
                     + ' | '.join(ratios) + ' |')
    return lines


def render_comparison(result: dict) -> str:
    def f(value, spec=''):
        return 'unknown' if value is None else format(value, spec)

    cells = {
        'correctness': lambda s: f"{f(s['passed'])}/{f(s['runs'])} passed, {f(s['regression_runs'])} regression runs, "
                                 f"{f(s['unfinished_runs'])} unfinished",
        'tokens': lambda s: f"{f(s['tokens_per_correct'], '.0f')} total / {f(s['uncached_tokens_per_correct'], '.0f')} "
                            f"uncached per correct, {f(s['auxiliary_calls'])} aux calls",
        'time': lambda s: f"median {f(s['median_wall_time_sec'], '.1f')} s, p90 {f(s['p90_wall_time_sec'], '.1f')} s",
        'safety': lambda s: f"{f(s['timeouts'])} timeouts, {f(s['tampered_runs'])} tampered, "
                            f"verification {f(s['verified_runs'])}/{f(s['verification_known_runs'])}",
    }
    b, c = (result['scorecards'][result[k]] for k in ('baseline', 'candidate'))
    lines = [f"Verdict: {result['verdict']} ({result['candidate']} vs baseline {result['baseline']}, "
             f"margin {result['margin']:.0%}, min trials {result['min_trials']})", headline(result), '',
             f"| Dimension | {result['candidate']} vs {result['baseline']} | {result['baseline']} (baseline) "
             f"| {result['candidate']} (candidate) |", '|---|---|---|---|']
    for name, cell in cells.items():
        lines.append(f"| {name} | {result['dimensions'][name]} | {cell(b)} | {cell(c)} |")
    lines += ['', f"Candidate/baseline ratios ({result['confidence']:.0%} bootstrap CI, runs resampled within "
                  f"task):", *interval_lines(result)]
    lines += ['', 'Run classifications:', '', *_classification_lines(result),
              '', *_per_task_lines(result)]
    for title, items in (('Reasons', result['reasons']), ('Warnings', result['warnings'])):
        if items:
            lines += ['', f'{title}:', *(f'- {item}' for item in items)]
    return '\n'.join(lines)


_BETTER = {'correctness': 'passes more runs', 'tokens': 'uses fewer tokens', 'time': 'runs faster', 'safety': 'is safer'}
_WORSE = {'correctness': 'passes fewer runs', 'tokens': 'uses more tokens', 'time': 'runs slower', 'safety': 'is less safe'}


def _series(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ', '.join(items[:-1]) + ' and ' + items[-1]


def headline(result: dict) -> str:
    """One sentence naming the winner, so a verdict word never has to be interpreted."""
    b, c, dims = result['baseline'], result['candidate'], result['dimensions']
    better = [_BETTER[k] for k, v in dims.items() if v == 'better']
    worse = [_WORSE[k] for k, v in dims.items() if v == 'worse']
    same = [k for k, v in dims.items() if v == 'same']
    not_worse = [k for k, v in dims.items() if v == 'non-inferior']
    tail = f"; {_series(same)} {'is' if len(same) == 1 else 'are'} the same" if same else ''
    if not_worse:
        tail += f"; {_series(not_worse)} {'is' if len(not_worse) == 1 else 'are'} not measurably worse"
    verdict = result['verdict']
    if verdict == 'better':
        return f"Winner: {c} (candidate). Compared with {b} (baseline) it {_series(better)}{tail}."
    if verdict == 'worse':
        despite = f", although it {_series(better)}" if better else ''
        return f"Winner: {b} (baseline). {c} (candidate) {_series(worse)}{despite}."
    if verdict == 'tradeoff':
        return (f"No overall winner (tradeoff): {c} (candidate) {_series(better)} "
                f"but {_series(worse)} than {b} (baseline).")
    if verdict == 'equivalent':
        return (f"No winner: {c} (candidate) and {b} (baseline) are equivalent "
                f"within the {result['margin']:.0%} margin.")
    reasons = result['reasons']
    more = f" (and {len(reasons) - 1} more)" if len(reasons) > 1 else ''
    return f"No winner yet (inconclusive): {reasons[0] if reasons else 'insufficient data'}{more}."


def _fenced(text: str, language: str = '') -> list[str]:
    fence = '`' * max(3, 1 + max((len(m.group()) for m in re.finditer(r'`+', text)), default=0))
    return [fence + language, text, fence]


def render_markdown(result, rows, manifest=None, *, results_label: str,
                    charts: list[tuple[str, str]] | None = None) -> str:
    """A shareable comparison with per-task measurements and recorded setup."""
    baseline, candidate = result['baseline'], result['candidate']
    comparison = render_comparison(result).splitlines()
    table_end = next((i for i, line in enumerate(comparison[3:], 3) if not line), len(comparison))
    lines = [f'# {candidate} vs {baseline}', '', comparison[0], '', f'**{comparison[1]}**', '',
             *comparison[3:table_end], '', '## Efficiency ratios', '',
             f"Candidate/baseline, {result['confidence']:.0%} bootstrap CI from {result['resamples']} "
             'resamples of runs within each task:', '', *interval_lines(result)]
    lines += ['', '## Run classifications', '', *_classification_lines(result)]
    if charts:
        lines += ['', '## Charts', '']
        lines += [f'![{alt}]({path})' for alt, path in charts]
    lines += ['', '## Per-task results', '',
              '| Task | Arm | Passed/runs | Median wall s | Median total tokens | Median uncached tokens |',
              '|---|---|---:|---:|---:|---:|']

    def fmt(value, spec='.0f'):
        return 'unknown' if value is None else format(value, spec)

    def tokens(row, cached):
        metrics = row.get('metrics') or {}
        if metrics.get('input_tokens') is None or metrics.get('output_tokens') is None:
            return None
        return (_count(metrics, 'input_tokens') + _count(metrics, 'output_tokens')
                + _count(metrics, 'cache_write_tokens')
                + (_count(metrics, 'cache_read_tokens') if cached else 0))

    arm_rows = [r for r in rows if r.get('harness') in (baseline, candidate)]
    for task in sorted({r['task'] for r in arm_rows}):
        for name in (baseline, candidate):
            records = [r for r in arm_rows if r['task'] == task and r['harness'] == name]
            lines.append(f"| {task} | {name} | {sum(bool(r.get('passed')) for r in records)}/{len(records)} | "
                         f"{fmt(median(r.get('wall_time_sec') for r in records), '.1f')} | "
                         f"{fmt(median(tokens(r, True) for r in records))} | "
                         f"{fmt(median(tokens(r, False) for r in records))} |")
    lines += ['', *_per_task_lines(result)]
    lines += ['', '## Setup', '']
    invocations = [inv for inv in (manifest or {}).get('invocations', [])
                   if any(name in inv.get('harnesses', {}) for name in (baseline, candidate))]
    for inv in invocations:
        harnesses = inv.get('harnesses', {})
        lines += [f"### Invocation {inv.get('started', 'unknown')}", '',
                  f"- Config: {inv.get('config') or 'config path not recorded'}",
                  f"- Trials/jobs: {inv.get('trials', 'unknown')}/{inv.get('jobs', 'unknown')}",
                  f"- Alternate order: {inv.get('alternate_order', 'unknown')}; timeout: {inv.get('timeout')}",
                  f"- Platform: {inv.get('platform', 'unknown')}",
                  f"- Python: {inv.get('python', 'unknown')}; Node: {inv.get('node') or 'unknown'}"]
        if inv.get('reconstructed'):
            lines.append(f"- Provenance note: {inv['reconstructed']}")
        for name in (baseline, candidate):
            h = harnesses.get(name)
            if h is not None:
                lines.append(f"- {name}: kind {h.get('kind', 'unknown')}, version {h.get('version') or 'unknown'}, "
                             f"config hash {h.get('config_hash', 'unknown')}, state "
                             + (f"isolated from {h['state_template']}" if h.get('state_template')
                                else "not isolated (operator's own)"))
        if baseline in harnesses and candidate in harnesses:
            b_command, c_command = (harnesses[name].get('command', []) for name in (baseline, candidate))
            changes = [op for op in difflib.SequenceMatcher(a=b_command, b=c_command, autojunk=False).get_opcodes()
                       if op[0] != 'equal']
            lines += ['', 'Command template argv difference (differing elements only):']
            if not changes:
                lines.append('No differing argv elements.')
            for _, bi, bj, ci, cj in changes:
                lines += _fenced(json.dumps({baseline: b_command[bi:bj], candidate: c_command[ci:cj]},
                                            indent=2, ensure_ascii=False), 'json')
            b_files, c_files = (harnesses[name].get('files', {}) for name in (baseline, candidate))
            for path in sorted(b_files.keys() | c_files.keys()):
                if path in b_files and path in c_files and b_files[path]['sha256'] == c_files[path]['sha256']:
                    continue
                for name, files in ((baseline, b_files), (candidate, c_files)):
                    if path not in files:
                        continue
                    file = files[path]
                    lines += ['', f"Overlay {name}: {path} (sha256 {file['sha256']})"]
                    if file.get('contents') is None:
                        lines.append('Contents not recorded (binary or over 64 KiB).')
                    else:
                        lines += _fenced(file['contents'])
        lines += ['', 'Task ids and hashes:']
        lines += [f"- {task}: {task_hash[:12]}" for task, task_hash in sorted(inv.get('tasks', {}).items())]
        lines.append('')
    if manifest is None:
        lines.append('No manifest.json; setup not recorded.')
    elif not invocations:
        lines.append('No recorded invocation for these arms.')
    for title, items in (('Reasons', result['reasons']), ('Warnings', result['warnings'])):
        if items:
            lines += ['', f'## {title}', '', *(f'- {item}' for item in items)]

    invocation = invocations[-1] if invocations else {}
    config = invocation.get('config') or 'CONFIG'
    trials = invocation.get('trials', result['min_trials'])
    jobs = invocation.get('jobs', 1)
    # New trials go to a fresh directory; compare reads the directory holding these rows.
    rerun = f"results/{Path(results_label).name or 'experiment'}-rerun"
    run = ['python', '-m', 'bench', '--config', config, '--results', rerun, 'run',
           '--harness', baseline, candidate, '--trials', str(trials), '--jobs', str(jobs)]
    if invocation.get('tasks'):
        run += ['--task', *invocation['tasks']]
    if invocation.get('alternate_order'):
        run.append('--alternate-order')
    if invocation.get('timeout') is not None:
        run += ['--timeout', str(invocation['timeout'])]
    compare_command = ['python', '-m', 'bench', '--config', config, '--results', results_label, 'compare',
                       '--baseline', baseline, '--candidate', candidate, '--margin', str(result['margin']),
                       '--min-trials', str(result['min_trials']), '--format', 'markdown']
    lines += ['', '## Reproduce', '']
    if not invocation.get('config'):
        lines.append('config path not recorded; replace CONFIG with the harness configuration.')
    lines += _fenced(shlex.join(run) + '\n' + shlex.join(compare_command), 'console')
    lines += ['', 'Run from the benchmark directory with the recorded config and tasks. The first command '
              'collects new trials in a fresh directory (compare it by pointing --results there); the '
              'second re-scores the runs in this report, and works on an exported bundle without '
              'model access.',
              '', '## How to read this', '',
              f"Correctness and safety require non-inferiority (no extra failures or safety regressions). "
              f"Tokens and time compare the {result['confidence']:.0%} bootstrap interval of the "
              f"candidate/baseline ratio with the {result['margin']:.0%} margin: worse if the whole interval "
              'is above it, better if an interval is wholly below it and no loss beyond it is possible, the '
              'same if it lies inside the band; otherwise the verdict is inconclusive. Infrastructure '
              'contamination makes a comparison inconclusive unless correctness or safety is measurably '
              'worse. Run classifications use explicit recorded evidence; missing legacy evidence is '
              'unknown, not infrastructure. Unknown ≠ 0; medians use known runs only. Tokens per correct '
              'solution include failed attempts. Per-task ratios and pass-rate differences are descriptive '
              'point effects, not per-task winners; aggregate bootstrap resampling is unchanged.']
    return '\n'.join(lines) + '\n'
