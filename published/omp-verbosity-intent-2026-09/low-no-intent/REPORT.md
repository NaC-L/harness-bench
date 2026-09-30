# omp-low-no-intent vs omp-baseline

Verdict: worse (omp-low-no-intent vs baseline omp-baseline, margin 10%, min trials 3)

**Winner: omp-baseline (baseline). omp-low-no-intent (candidate) runs slower.**

| Dimension | omp-low-no-intent vs omp-baseline | omp-baseline (baseline) | omp-low-no-intent (candidate) |
|---|---|---|---|
| correctness | same | 12/12 passed, 0 regression runs, 0 unfinished | 12/12 passed, 0 regression runs, 0 unfinished |
| tokens | same | 66037 total / 21994 uncached per correct, 0 aux calls | 72217 total / 23108 uncached per correct, 0 aux calls |
| time | worse | median 227.5 s, p90 291.7 s | median 210.4 s, p90 325.8 s |
| safety | same | 0 timeouts, 0 tampered, verification 12/12 | 0 timeouts, 0 tampered, verification 12/12 |

## Charts

![Summary](charts/summary.svg)
![Tokens per task](charts/tokens-per-task.svg)
![Wall time per task](charts/wall-time-per-task.svg)

## Per-task results

| Task | Arm | Passed/runs | Median wall s | Median total tokens | Median uncached tokens |
|---|---|---:|---:|---:|---:|
| hard-dep-resolver | omp-baseline | 3/3 | 291.7 | 58907 | 32718 |
| hard-dep-resolver | omp-low-no-intent | 3/3 | 247.8 | 68989 | 27261 |
| hard-expr-eval | omp-baseline | 3/3 | 187.5 | 63303 | 17479 |
| hard-expr-eval | omp-low-no-intent | 3/3 | 164.8 | 74805 | 20447 |
| hard-line-diff | omp-baseline | 3/3 | 269.2 | 51614 | 21219 |
| hard-line-diff | omp-low-no-intent | 3/3 | 259.7 | 53085 | 25737 |
| hard-segment-tree | omp-baseline | 3/3 | 137.7 | 72338 | 17482 |
| hard-segment-tree | omp-low-no-intent | 3/3 | 115.2 | 44069 | 17661 |

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

### Invocation 2026-09-30T20:06:26.604098+00:00

- Config: benchmark-omp-verbosity-intent.toml
- Trials/jobs: 3/1
- Alternate order: False; timeout: None
- Platform: Windows-11-10.0.26200-SP0
- Python: 3.14.3; Node: v22.20.0
- omp-low-no-intent: kind omp, version omp/18.4.4, config hash 181bac166bbebe29cbb960228be136ab0aa3e5908eef0af3d6971d69d103c320, state isolated from experiments/omp-isolated/agent

Task ids and hashes:
- hard-dep-resolver: c5041eab8ad4
- hard-expr-eval: 7e651a4872ef
- hard-line-diff: d140d53f0099
- hard-segment-tree: 51474f0d7d5a


## Warnings

- correctness at ceiling: every run passed, so these tasks cannot distinguish correctness

## Reproduce

```console
python -m bench --config benchmark-omp-verbosity-intent.toml --results results/low-no-intent-rerun run --harness omp-baseline omp-low-no-intent --trials 3 --jobs 1 --task hard-dep-resolver hard-expr-eval hard-line-diff hard-segment-tree
python -m bench --config benchmark-omp-verbosity-intent.toml --results published/omp-verbosity-intent-2026-09/low-no-intent compare --baseline omp-baseline --candidate omp-low-no-intent --margin 0.1 --min-trials 3 --format markdown
```

Run from the benchmark directory with the recorded config and tasks. The first command collects new trials in a fresh directory (compare it by pointing --results there); the second re-scores the runs in this report, and works on an exported bundle without model access.

## How to read this

Correctness and safety require non-inferiority (no extra failures or safety regressions). Tokens and time use a 10% relative margin. Unknown ≠ 0; medians use known runs only. Tokens per correct solution include failed attempts.
