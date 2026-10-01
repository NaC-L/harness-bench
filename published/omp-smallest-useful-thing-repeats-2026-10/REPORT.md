# omp-smallest vs omp-baseline

Verdict: worse (omp-smallest vs baseline omp-baseline, margin 10%, min trials 3)

**Winner: omp-baseline (baseline). omp-smallest (candidate) uses more tokens.**

| Dimension | omp-smallest vs omp-baseline | omp-baseline (baseline) | omp-smallest (candidate) |
|---|---|---|---|
| correctness | same | 36/36 passed, 0 regression runs, 0 unfinished | 36/36 passed, 0 regression runs, 0 unfinished |
| tokens | worse | 78122 total / 22879 uncached per correct, 0 aux calls | 77340 total / 25944 uncached per correct, 0 aux calls |
| time | same | median 210.6 s, p90 290.8 s | median 194.1 s, p90 282.4 s |
| safety | same | 0 timeouts, 0 tampered, verification 36/36 | 0 timeouts, 0 tampered, verification 36/36 |

## Charts

![Summary](charts/summary.svg)
![Tokens per task](charts/tokens-per-task.svg)
![Wall time per task](charts/wall-time-per-task.svg)

## Per-task results

| Task | Arm | Passed/runs | Median wall s | Median total tokens | Median uncached tokens |
|---|---|---:|---:|---:|---:|
| hard-dep-resolver | omp-baseline | 9/9 | 257.3 | 81249 | 28050 |
| hard-dep-resolver | omp-smallest | 9/9 | 244.9 | 76335 | 30374 |
| hard-expr-eval | omp-baseline | 9/9 | 144.1 | 65901 | 17347 |
| hard-expr-eval | omp-smallest | 9/9 | 150.0 | 63789 | 22465 |
| hard-line-diff | omp-baseline | 9/9 | 262.4 | 54785 | 21386 |
| hard-line-diff | omp-smallest | 9/9 | 271.9 | 78010 | 32717 |
| hard-segment-tree | omp-baseline | 9/9 | 127.5 | 52627 | 17014 |
| hard-segment-tree | omp-smallest | 9/9 | 126.4 | 60878 | 16843 |

## Setup

### Invocation 2026-09-30T21:31:48.620840+00:00

- Config: benchmark-omp-smallest-useful-thing.toml
- Trials/jobs: 3/8
- Alternate order: False; timeout: None
- Platform: Windows-11-10.0.26200-SP0
- Python: 3.14.3; Node: v22.20.0
- omp-baseline: kind omp, version v18.4.5-0-g79808c3bf, config hash b586f5dd36ebb68f720129d1cfc95e59343bd35bff881ddf763c6027ed958c17, state isolated from experiments/omp-isolated/agent
- omp-smallest: kind omp, version v18.4.5-1-g27cdf191b, config hash c011a4c2b093a86029dce073b515f85880bdb7749a5404a248fd2410d05288ae, state isolated from experiments/omp-isolated/agent

Command template argv difference (differing elements only):
```json
{
  "omp-baseline": [
    "~/Desktop/omp-baseline/packages/coding-agent/src/cli.ts"
  ],
  "omp-smallest": [
    "~/Desktop/oh-my-pi/packages/coding-agent/src/cli.ts"
  ]
}
```

Task ids and hashes:
- hard-dep-resolver: c5041eab8ad4
- hard-expr-eval: 7e651a4872ef
- hard-line-diff: d140d53f0099
- hard-segment-tree: 51474f0d7d5a

### Invocation 2026-09-30T21:43:35.410851+00:00

- Config: benchmark-omp-smallest-useful-thing.toml
- Trials/jobs: 3/8
- Alternate order: False; timeout: None
- Platform: Windows-11-10.0.26200-SP0
- Python: 3.14.3; Node: v22.20.0
- omp-baseline: kind omp, version v18.4.5-0-g79808c3bf, config hash b586f5dd36ebb68f720129d1cfc95e59343bd35bff881ddf763c6027ed958c17, state isolated from experiments/omp-isolated/agent
- omp-smallest: kind omp, version v18.4.5-1-g27cdf191b, config hash c011a4c2b093a86029dce073b515f85880bdb7749a5404a248fd2410d05288ae, state isolated from experiments/omp-isolated/agent

Command template argv difference (differing elements only):
```json
{
  "omp-baseline": [
    "~/Desktop/omp-baseline/packages/coding-agent/src/cli.ts"
  ],
  "omp-smallest": [
    "~/Desktop/oh-my-pi/packages/coding-agent/src/cli.ts"
  ]
}
```

Task ids and hashes:
- hard-dep-resolver: c5041eab8ad4
- hard-expr-eval: 7e651a4872ef
- hard-line-diff: d140d53f0099
- hard-segment-tree: 51474f0d7d5a

### Invocation 2026-09-30T21:55:37.757622+00:00

- Config: benchmark-omp-smallest-useful-thing.toml
- Trials/jobs: 3/8
- Alternate order: False; timeout: None
- Platform: Windows-11-10.0.26200-SP0
- Python: 3.14.3; Node: v22.20.0
- omp-baseline: kind omp, version v18.4.5-0-g79808c3bf, config hash b586f5dd36ebb68f720129d1cfc95e59343bd35bff881ddf763c6027ed958c17, state isolated from experiments/omp-isolated/agent
- omp-smallest: kind omp, version v18.4.5-1-g27cdf191b, config hash c011a4c2b093a86029dce073b515f85880bdb7749a5404a248fd2410d05288ae, state isolated from experiments/omp-isolated/agent

Command template argv difference (differing elements only):
```json
{
  "omp-baseline": [
    "~/Desktop/omp-baseline/packages/coding-agent/src/cli.ts"
  ],
  "omp-smallest": [
    "~/Desktop/oh-my-pi/packages/coding-agent/src/cli.ts"
  ]
}
```

Task ids and hashes:
- hard-dep-resolver: c5041eab8ad4
- hard-expr-eval: 7e651a4872ef
- hard-line-diff: d140d53f0099
- hard-segment-tree: 51474f0d7d5a


## Warnings

- harness versions differ: v18.4.5-0-g79808c3bf vs v18.4.5-1-g27cdf191b
- correctness at ceiling: every run passed, so these tasks cannot distinguish correctness

## Reproduce

```console
python -m bench --config benchmark-omp-smallest-useful-thing.toml --results results/omp-smallest-useful-thing-repeats-2026-10-rerun run --harness omp-baseline omp-smallest --trials 3 --jobs 8 --task hard-dep-resolver hard-expr-eval hard-line-diff hard-segment-tree
python -m bench --config benchmark-omp-smallest-useful-thing.toml --results published/omp-smallest-useful-thing-repeats-2026-10 compare --baseline omp-baseline --candidate omp-smallest --margin 0.1 --min-trials 3 --format markdown
```

Run from the benchmark directory with the recorded config and tasks. The first command collects new trials in a fresh directory (compare it by pointing --results there); the second re-scores the runs in this report, and works on an exported bundle without model access.

## How to read this

Correctness and safety require non-inferiority (no extra failures or safety regressions). Tokens and time use a 10% relative margin. Unknown ≠ 0; medians use known runs only. Tokens per correct solution include failed attempts.
