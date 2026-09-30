# omp-low-verbosity vs omp-baseline

Verdict: worse (omp-low-verbosity vs baseline omp-baseline, margin 10%, min trials 3)

**Winner: omp-baseline (baseline). omp-low-verbosity (candidate) uses more tokens.**

| Dimension | omp-low-verbosity vs omp-baseline | omp-baseline (baseline) | omp-low-verbosity (candidate) |
|---|---|---|---|
| correctness | same | 12/12 passed, 0 regression runs, 0 unfinished | 12/12 passed, 0 regression runs, 0 unfinished |
| tokens | worse | 66037 total / 21994 uncached per correct, 0 aux calls | 64965 total / 24538 uncached per correct, 0 aux calls |
| time | same | median 227.5 s, p90 291.7 s | median 216.0 s, p90 313.7 s |
| safety | same | 0 timeouts, 0 tampered, verification 12/12 | 0 timeouts, 0 tampered, verification 12/12 |

## Charts

![Summary](charts/summary.svg)
![Tokens per task](charts/tokens-per-task.svg)
![Wall time per task](charts/wall-time-per-task.svg)

## Per-task results

| Task | Arm | Passed/runs | Median wall s | Median total tokens | Median uncached tokens |
|---|---|---:|---:|---:|---:|
| hard-dep-resolver | omp-baseline | 3/3 | 291.7 | 58907 | 32718 |
| hard-dep-resolver | omp-low-verbosity | 3/3 | 274.2 | 76216 | 26808 |
| hard-expr-eval | omp-baseline | 3/3 | 187.5 | 63303 | 17479 |
| hard-expr-eval | omp-low-verbosity | 3/3 | 157.1 | 59461 | 19284 |
| hard-line-diff | omp-baseline | 3/3 | 269.2 | 51614 | 21219 |
| hard-line-diff | omp-low-verbosity | 3/3 | 258.2 | 52271 | 18863 |
| hard-segment-tree | omp-baseline | 3/3 | 137.7 | 72338 | 17482 |
| hard-segment-tree | omp-low-verbosity | 3/3 | 135.0 | 59687 | 25771 |

## Setup

### Invocation 2026-09-30T20:06:25.403860+00:00

- Config: benchmark-omp-verbosity-intent.toml
- Trials/jobs: 3/1
- Alternate order: False; timeout: None
- Platform: Windows-11-10.0.26200-SP0
- Python: 3.14.3; Node: v22.20.0
- omp-baseline: kind omp, version omp/18.4.4, config hash 33ee1313017e5035c3a6077c81cee0ea88ad56e22afc675571a036752a685106, state isolated from experiments/omp-isolated/agent

Task ids and hashes:
- hard-dep-resolver: c5041eab8ad4
- hard-expr-eval: 7e651a4872ef
- hard-line-diff: d140d53f0099
- hard-segment-tree: 51474f0d7d5a

### Invocation 2026-09-30T20:06:25.706257+00:00

- Config: benchmark-omp-verbosity-intent.toml
- Trials/jobs: 3/1
- Alternate order: False; timeout: None
- Platform: Windows-11-10.0.26200-SP0
- Python: 3.14.3; Node: v22.20.0
- omp-low-verbosity: kind omp, version omp/18.4.4, config hash 512bca04e5d3f82079e365f161d09c4c42e9027ecec6955cfdae16208597d779, state isolated from experiments/omp-isolated/agent

Task ids and hashes:
- hard-dep-resolver: c5041eab8ad4
- hard-expr-eval: 7e651a4872ef
- hard-line-diff: d140d53f0099
- hard-segment-tree: 51474f0d7d5a


## Warnings

- correctness at ceiling: every run passed, so these tasks cannot distinguish correctness

## Reproduce

```console
python -m bench --config benchmark-omp-verbosity-intent.toml --results results/low-verbosity-rerun run --harness omp-baseline omp-low-verbosity --trials 3 --jobs 1 --task hard-dep-resolver hard-expr-eval hard-line-diff hard-segment-tree
python -m bench --config benchmark-omp-verbosity-intent.toml --results published/omp-verbosity-intent-2026-09/low-verbosity compare --baseline omp-baseline --candidate omp-low-verbosity --margin 0.1 --min-trials 3 --format markdown
```

Run from the benchmark directory with the recorded config and tasks. The first command collects new trials in a fresh directory (compare it by pointing --results there); the second re-scores the runs in this report, and works on an exported bundle without model access.

## How to read this

Correctness and safety require non-inferiority (no extra failures or safety regressions). Tokens and time use a 10% relative margin. Unknown ≠ 0; medians use known runs only. Tokens per correct solution include failed attempts.
