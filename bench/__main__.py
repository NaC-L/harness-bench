from __future__ import annotations
import argparse
import json
from pathlib import Path
from .tasks import load_tasks
from .runner import load_harnesses, run_matrix
from . import report
from .manifest import load_manifest
from .export import export
from .charts import render_charts

ROOT = Path(__file__).resolve().parents[1]


def positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError('must be positive')
    return number


def fraction(value):
    number = float(value)
    if not 0 <= number < 1:
        raise argparse.ArgumentTypeError('must be in [0, 1)')
    return number


def main():
    parser = argparse.ArgumentParser(description='Local coding-agent harness benchmark')
    parser.add_argument('--config', type=Path, default=ROOT / 'harnesses.toml')
    parser.add_argument('--tasks-dir', type=Path, default=ROOT / 'tasks')
    parser.add_argument('--results', type=Path, default=ROOT / 'results')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('list')
    run = sub.add_parser('run')
    run.add_argument('--harness', nargs='+', required=True)
    run.add_argument('--task', nargs='+', default=['all'])
    run.add_argument('--trials', type=positive, default=1)
    run.add_argument('--jobs', type=positive, default=1)
    run.add_argument('--alternate-order', action='store_true')
    run.add_argument('--timeout', type=positive)
    run.add_argument('--keep-workdir', action='store_true')
    rep = sub.add_parser('report')
    rep.add_argument('--k', type=positive, default=1)
    rep.add_argument('--json', action='store_true')
    cmp = sub.add_parser('compare', help='goal-aligned verdict for a candidate arm vs a baseline arm')
    cmp.add_argument('--baseline', required=True)
    cmp.add_argument('--candidate', required=True)
    cmp.add_argument('--margin', type=fraction, default=0.10)
    cmp.add_argument('--min-trials', type=positive, default=3)
    cmp.add_argument('--format', choices=('text', 'markdown', 'json'), default='text')
    cmp.add_argument('--json', action='store_true', help='deprecated alias for --format json')
    cmp.add_argument('--charts-dir', help='write SVG charts and embed DIR/<file> in markdown output')
    exp = sub.add_parser('export', help='write a sanitized shareable comparison bundle')
    exp.add_argument('--baseline', required=True)
    exp.add_argument('--candidate', required=True)
    exp.add_argument('--out', type=Path, required=True)
    exp.add_argument('--margin', type=fraction, default=0.10)
    exp.add_argument('--min-trials', type=positive, default=3)
    exp.add_argument('--include-transcripts', action='store_true')
    args = parser.parse_args()
    if args.command == 'run' and args.alternate_order and args.jobs != 1:
        parser.error('--alternate-order requires --jobs 1')
    if args.command == 'report':
        rows = report.load(args.results / 'runs.jsonl')
        print(json.dumps(report.summarize(rows, args.k), indent=2) if args.json else report.render(rows, args.k))
        return 0
    if args.command == 'export':
        if args.out.exists():
            parser.error(f'output directory already exists: {args.out}')
        rows = report.load(args.results / 'runs.jsonl')
        try:
            export(rows, args.results, args.out, args.baseline, args.candidate,
                   margin=args.margin, min_trials=args.min_trials,
                   include_transcripts=args.include_transcripts)
        except ValueError as exc:
            parser.error(str(exc))
        return 0
    if args.command == 'compare':
        rows = report.load(args.results / 'runs.jsonl')
        try:
            result = report.compare(rows, args.baseline, args.candidate,
                                    margin=args.margin, min_trials=args.min_trials)
        except ValueError as exc:
            parser.error(str(exc))
        output_format = 'json' if args.json else args.format
        if output_format == 'json':
            print(json.dumps(result, indent=2))
        elif output_format == 'markdown':
            chart_options = {}
            if args.charts_dir:
                directory = Path(args.charts_dir)
                directory.mkdir(parents=True, exist_ok=True)
                svgs = render_charts(result, rows)
                for name, svg in svgs.items():
                    (directory / name).write_text(svg, encoding='utf-8')
                prefix = args.charts_dir.replace('\\', '/').rstrip('/')
                chart_options['charts'] = [
                    (name.removesuffix('.svg').replace('-', ' ').capitalize(), f'{prefix}/{name}')
                    for name in svgs]
            print(report.render_markdown(result, rows, load_manifest(args.results),
                                         results_label=str(args.results), **chart_options), end='')
        else:
            print(report.render_comparison(result))
        return 0
    tasks = load_tasks(args.tasks_dir, getattr(args, 'task', None))
    # Held-out fixtures require explicit task names; routine "all" runs must not tune on them.
    if args.command == 'run' and args.task == ['all']:
        tasks = [task for task in tasks if 'heldout' not in task.tags]
    harnesses = load_harnesses(args.config)
    if args.command == 'list':
        for t in tasks:
            print(f'{t.id}: {t.title} ({t.category})')
        for h in harnesses.values():
            print(f'{h.name}: {h.kind} -> {h.command[0]}')
        return 0
    missing = [h for h in args.harness if h not in harnesses]
    if missing:
        parser.error('unknown harness: ' + ', '.join(missing))
    rows = run_matrix(tasks, [harnesses[h] for h in args.harness], args.results, trials=args.trials,
                      jobs=args.jobs, timeout=args.timeout, keep_workdir=args.keep_workdir,
                      alternate_order=args.alternate_order, config=args.config)
    return 0 if all(r['passed'] for r in rows) else 1


if __name__ == '__main__':
    raise SystemExit(main())
