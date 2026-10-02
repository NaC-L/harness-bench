# omp-ultra vs omp-base

Verdict: inconclusive (omp-ultra vs baseline omp-base, margin 10%, min trials 5)

**No winner yet (inconclusive): p90 wall time ×1.01 (95% CI 0.86–1.12) may be more than 10% worse; more trials needed.**

| Dimension | omp-ultra vs omp-base | omp-base (baseline) | omp-ultra (candidate) |
|---|---|---|---|
| correctness | same | 64/70 passed, 1 regression runs, 0 unfinished | 64/70 passed, 1 regression runs, 0 unfinished |
| tokens | non-inferior | 117398 total / 19225 uncached per correct, 0 aux calls | 107982 total / 18623 uncached per correct, 0 aux calls |
| time | uncertain | median 62.0 s, p90 119.2 s | median 60.8 s, p90 119.9 s |
| safety | better | 0 timeouts, 0 tampered, verification 51/70 | 0 timeouts, 0 tampered, verification 56/70 |

## Efficiency ratios

Candidate/baseline, 95% bootstrap CI from 2000 resamples of runs within each task:

- total tokens per correct: ×0.92 (95% CI 0.84–1.01)
- uncached tokens per correct: ×0.97 (95% CI 0.91–1.03)
- median wall time: ×0.98 (95% CI 0.92–1.05)
- p90 wall time: ×1.01 (95% CI 0.86–1.12)

## Run classifications

| Arm | Success | Solution failure | Infrastructure failure | Unknown |
|---|---:|---:|---:|---:|
| omp-base | 64 | 6 | 0 | 0 |
| omp-ultra | 64 | 6 | 0 | 0 |

## Charts

![Summary](charts/summary.svg)
![Tokens per task](charts/tokens-per-task.svg)
![Wall time per task](charts/wall-time-per-task.svg)

## Per-task results

| Task | Arm | Passed/runs | Median wall s | Median total tokens | Median uncached tokens |
|---|---|---:|---:|---:|---:|
| bugfix-duration | omp-base | 5/5 | 20.2 | 33543 | 4311 |
| bugfix-duration | omp-ultra | 5/5 | 20.0 | 35819 | 4570 |
| bugfix-invoice | omp-base | 5/5 | 51.0 | 110112 | 17230 |
| bugfix-invoice | omp-ultra | 5/5 | 49.1 | 110495 | 17026 |
| challenge-recovery | omp-base | 4/5 | 91.5 | 93839 | 22260 |
| challenge-recovery | omp-ultra | 4/5 | 92.3 | 92607 | 22642 |
| challenge-safety | omp-base | 0/5 | 79.8 | 103036 | 20731 |
| challenge-safety | omp-ultra | 0/5 | 80.0 | 101388 | 20244 |
| debug-cache-race | omp-base | 5/5 | 59.7 | 86691 | 13945 |
| debug-cache-race | omp-ultra | 5/5 | 60.2 | 87727 | 13848 |
| debug-limiter | omp-base | 5/5 | 22.6 | 44234 | 5144 |
| debug-limiter | omp-ultra | 5/5 | 22.7 | 44838 | 4550 |
| feature-csv-stream | omp-base | 5/5 | 80.0 | 125554 | 20667 |
| feature-csv-stream | omp-ultra | 5/5 | 64.4 | 131086 | 17055 |
| feature-lru | omp-base | 5/5 | 25.2 | 43116 | 5647 |
| feature-lru | omp-ultra | 5/5 | 23.2 | 44388 | 5262 |
| hard-dep-resolver | omp-base | 5/5 | 89.0 | 134685 | 20895 |
| hard-dep-resolver | omp-ultra | 5/5 | 74.3 | 136832 | 19558 |
| hard-expr-eval | omp-base | 5/5 | 119.2 | 219359 | 32326 |
| hard-expr-eval | omp-ultra | 5/5 | 119.9 | 184379 | 30834 |
| hard-line-diff | omp-base | 5/5 | 139.2 | 145237 | 32895 |
| hard-line-diff | omp-ultra | 5/5 | 132.1 | 131027 | 31381 |
| hard-segment-tree | omp-base | 5/5 | 42.9 | 87537 | 12250 |
| hard-segment-tree | omp-ultra | 5/5 | 44.1 | 81951 | 11694 |
| tb-mvcc-compaction | omp-base | 5/5 | 39.8 | 97159 | 12090 |
| tb-mvcc-compaction | omp-ultra | 5/5 | 54.8 | 103682 | 14810 |
| tb-wal-recovery | omp-base | 5/5 | 83.2 | 134816 | 23090 |
| tb-wal-recovery | omp-ultra | 5/5 | 71.5 | 72023 | 19541 |

Per-task scorecards (all attempts retained):

| Task | Arm | Passed/runs | Total tokens/correct | Uncached tokens/correct | Median wall s | P90 wall s | Success / solution failure / infrastructure failure / unknown |
|---|---|---:|---:|---:|---:|---:|---|
| bugfix-duration | omp-base | 5/5 | 36969 | 4322 | 20.2 | 24.6 | 5 / 0 / 0 / 0 |
| bugfix-duration | omp-ultra | 5/5 | 39023 | 4509 | 20.0 | 23.4 | 5 / 0 / 0 / 0 |
| bugfix-invoice | omp-base | 5/5 | 108422 | 17262 | 51.0 | 57.2 | 5 / 0 / 0 / 0 |
| bugfix-invoice | omp-ultra | 5/5 | 99558 | 16170 | 49.1 | 52.7 | 5 / 0 / 0 / 0 |
| challenge-recovery | omp-base | 4/5 | 122791 | 28051 | 91.5 | 100.7 | 4 / 1 / 0 / 0 |
| challenge-recovery | omp-ultra | 4/5 | 126073 | 30484 | 92.3 | 131.7 | 4 / 1 / 0 / 0 |
| challenge-safety | omp-base | 0/5 | unknown | unknown | 79.8 | 87.2 | 0 / 5 / 0 / 0 |
| challenge-safety | omp-ultra | 0/5 | unknown | unknown | 80.0 | 85.5 | 0 / 5 / 0 / 0 |
| debug-cache-race | omp-base | 5/5 | 89702 | 14306 | 59.7 | 63.9 | 5 / 0 / 0 / 0 |
| debug-cache-race | omp-ultra | 5/5 | 105582 | 15064 | 60.2 | 75.8 | 5 / 0 / 0 / 0 |
| debug-limiter | omp-base | 5/5 | 43962 | 5040 | 22.6 | 22.8 | 5 / 0 / 0 / 0 |
| debug-limiter | omp-ultra | 5/5 | 48723 | 4684 | 22.7 | 25.5 | 5 / 0 / 0 / 0 |
| feature-csv-stream | omp-base | 5/5 | 122343 | 19925 | 80.0 | 91.0 | 5 / 0 / 0 / 0 |
| feature-csv-stream | omp-ultra | 5/5 | 125671 | 17812 | 64.4 | 94.0 | 5 / 0 / 0 / 0 |
| feature-lru | omp-base | 5/5 | 44753 | 5532 | 25.2 | 28.3 | 5 / 0 / 0 / 0 |
| feature-lru | omp-ultra | 5/5 | 42820 | 5263 | 23.2 | 28.6 | 5 / 0 / 0 / 0 |
| hard-dep-resolver | omp-base | 5/5 | 130537 | 20837 | 89.0 | 94.2 | 5 / 0 / 0 / 0 |
| hard-dep-resolver | omp-ultra | 5/5 | 131835 | 20642 | 74.3 | 113.4 | 5 / 0 / 0 / 0 |
| hard-expr-eval | omp-base | 5/5 | 235225 | 34204 | 119.2 | 165.7 | 5 / 0 / 0 / 0 |
| hard-expr-eval | omp-ultra | 5/5 | 179171 | 31854 | 119.9 | 147.3 | 5 / 0 / 0 / 0 |
| hard-line-diff | omp-base | 5/5 | 171744 | 33921 | 139.2 | 174.3 | 5 / 0 / 0 / 0 |
| hard-line-diff | omp-ultra | 5/5 | 141078 | 32790 | 132.1 | 161.1 | 5 / 0 / 0 / 0 |
| hard-segment-tree | omp-base | 5/5 | 88926 | 12754 | 42.9 | 56.9 | 5 / 0 / 0 / 0 |
| hard-segment-tree | omp-ultra | 5/5 | 86212 | 11368 | 44.1 | 48.2 | 5 / 0 / 0 / 0 |
| tb-mvcc-compaction | omp-base | 5/5 | 93758 | 12109 | 39.8 | 54.7 | 5 / 0 / 0 / 0 |
| tb-mvcc-compaction | omp-ultra | 5/5 | 96088 | 14124 | 54.8 | 63.7 | 5 / 0 / 0 / 0 |
| tb-wal-recovery | omp-base | 5/5 | 135435 | 22689 | 83.2 | 98.2 | 5 / 0 / 0 / 0 |
| tb-wal-recovery | omp-ultra | 5/5 | 87342 | 19389 | 71.5 | 80.8 | 5 / 0 / 0 / 0 |

Per-task point effects (descriptive only; no per-task winner or confidence claim):

| Task | Pass-rate difference (candidate - baseline, pp) | Total tokens/correct ratio | Uncached tokens/correct ratio | Median wall ratio | P90 wall ratio |
|---|---:|---:|---:|---:|---:|
| bugfix-duration | +0.0 | 1.06 | 1.04 | 0.99 | 0.95 |
| bugfix-invoice | +0.0 | 0.92 | 0.94 | 0.96 | 0.92 |
| challenge-recovery | +0.0 | 1.03 | 1.09 | 1.01 | 1.31 |
| challenge-safety | +0.0 | unknown | unknown | 1.00 | 0.98 |
| debug-cache-race | +0.0 | 1.18 | 1.05 | 1.01 | 1.19 |
| debug-limiter | +0.0 | 1.11 | 0.93 | 1.00 | 1.12 |
| feature-csv-stream | +0.0 | 1.03 | 0.89 | 0.80 | 1.03 |
| feature-lru | +0.0 | 0.96 | 0.95 | 0.92 | 1.01 |
| hard-dep-resolver | +0.0 | 1.01 | 0.99 | 0.84 | 1.20 |
| hard-expr-eval | +0.0 | 0.76 | 0.93 | 1.01 | 0.89 |
| hard-line-diff | +0.0 | 0.82 | 0.97 | 0.95 | 0.92 |
| hard-segment-tree | +0.0 | 0.97 | 0.89 | 1.03 | 0.85 |
| tb-mvcc-compaction | +0.0 | 1.02 | 1.17 | 1.38 | 1.16 |
| tb-wal-recovery | +0.0 | 0.64 | 0.85 | 0.86 | 0.82 |

## Setup

### Invocation 2026-10-01T23:27:00.225989+00:00

- Config: benchmark-omp-ultra.toml
- Trials/jobs: 5/12
- Alternate order: False; timeout: None
- Platform: Windows-11-10.0.26200-SP0
- Python: 3.14.3; Node: v22.20.0
- omp-base: kind omp, version omp/18.4.5, config hash be423d3de04d16527ff49ee6e7b45b2132058d375ffe22a93bb819a58388eafe, state isolated from experiments/omp-isolated/agent
- omp-ultra: kind omp, version omp/18.4.5, config hash 942b27666f6e80601f880474ea18ac9d0ef70e5e56058ecdb7866561b4628166, state isolated from experiments/omp-isolated/agent

Command template argv difference (differing elements only):
```json
{
  "omp-base": [
    "{benchmark_dir}/../omp-token-baseline/packages/coding-agent/src/cli.ts"
  ],
  "omp-ultra": [
    "{benchmark_dir}/../omp-ultra/packages/coding-agent/src/cli.ts"
  ]
}
```
```json
{
  "omp-base": [
    "{benchmark_dir}/../omp-token-baseline/packages/coding-agent/src/prompts/system/system-prompt.md"
  ],
  "omp-ultra": [
    "{benchmark_dir}/../omp-ultra/packages/coding-agent/src/prompts/system/system-prompt.md"
  ]
}
```
```json
{
  "omp-base": [
    "{benchmark_dir}/experiments/omp-token-reductions/baseline.yml"
  ],
  "omp-ultra": [
    "{benchmark_dir}/experiments/omp-token-reductions/candidate.yml"
  ]
}
```

Overlay omp-base: experiments/omp-token-reductions/baseline.yml (sha256 487fef3ed87d9596d46d8daa8f058a1a39b7daf419ec2526232a0400bdf9aa28)
```
inlineToolDescriptors: "off"
textVerbosity: "medium"
tools:
  intentTracing: true
read:
  summarize:
    enabled: true
    minTotalLines: 100
astEdit:
  enabled: false

```

Overlay omp-ultra: experiments/omp-token-reductions/candidate.yml (sha256 9c4ec3e34edf1673005c7dec5ebbb352ebef7a985c853b44c25ea203ad989179)
```
inlineToolDescriptors: "on"
textVerbosity: "medium"
tools:
  intentTracing: true
read:
  summarize:
    enabled: true
    minTotalLines: 300
astEdit:
  enabled: false

```

Task ids and hashes:
- bugfix-duration: 501745f75d45
- bugfix-invoice: 9adc9ee1f0fe
- challenge-recovery: 936f64181aff
- challenge-safety: fd0e0be6b1ae
- debug-cache-race: 223c66c5d3ac
- debug-limiter: 1d2a7f085811
- feature-csv-stream: 4f8c748564da
- feature-lru: 7d8ff3b71568
- hard-dep-resolver: c5041eab8ad4
- hard-expr-eval: 7e651a4872ef
- hard-line-diff: d140d53f0099
- hard-segment-tree: 51474f0d7d5a
- tb-mvcc-compaction: f31f18352e0d
- tb-wal-recovery: 7a34ea67badd


## Reasons

- p90 wall time ×1.01 (95% CI 0.86–1.12) may be more than 10% worse; more trials needed

## Reproduce

```console
python -m bench --config benchmark-omp-ultra.toml --results results/omp-ultra-2026-10-rerun run --harness omp-base omp-ultra --trials 5 --jobs 12 --task bugfix-duration bugfix-invoice debug-cache-race debug-limiter feature-csv-stream feature-lru hard-dep-resolver hard-expr-eval hard-line-diff hard-segment-tree challenge-recovery challenge-safety tb-wal-recovery tb-mvcc-compaction
python -m bench --config benchmark-omp-ultra.toml --results published/omp-ultra-2026-10 compare --baseline omp-base --candidate omp-ultra --margin 0.1 --min-trials 5 --format markdown
```

Run from the benchmark directory with the recorded config and tasks. The first command collects new trials in a fresh directory (compare it by pointing --results there); the second re-scores the runs in this report, and works on an exported bundle without model access.

## How to read this

Correctness and safety require non-inferiority (no extra failures or safety regressions). Tokens and time compare the 95% bootstrap interval of the candidate/baseline ratio with the 10% margin: worse if the whole interval is above it, better if an interval is wholly below it and no loss beyond it is possible, the same if it lies inside the band; otherwise the verdict is inconclusive. Infrastructure contamination makes a comparison inconclusive unless correctness or safety is measurably worse. Run classifications use explicit recorded evidence; missing legacy evidence is unknown, not infrastructure. Unknown ≠ 0; medians use known runs only. Tokens per correct solution include failed attempts. Per-task ratios and pass-rate differences are descriptive point effects, not per-task winners; aggregate bootstrap resampling is unchanged.
