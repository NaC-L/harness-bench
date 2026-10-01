# omp-read-300 vs omp-read-100

Verdict: better (omp-read-300 vs baseline omp-read-100, margin 10%, min trials 5)

**Winner: omp-read-300 (candidate). Compared with omp-read-100 (baseline) it is safer; correctness is the same; tokens and time are not measurably worse.**

| Dimension | omp-read-300 vs omp-read-100 | omp-read-100 (baseline) | omp-read-300 (candidate) |
|---|---|---|---|
| correctness | same | 50/50 passed, 0 regression runs, 0 unfinished | 50/50 passed, 0 regression runs, 0 unfinished |
| tokens | non-inferior | 83736 total / 22475 uncached per correct, 0 aux calls | 80052 total / 20227 uncached per correct, 0 aux calls |
| time | non-inferior | median 160.3 s, p90 289.9 s | median 154.2 s, p90 286.0 s |
| safety | better | 0 timeouts, 0 tampered, verification 35/50 | 0 timeouts, 0 tampered, verification 36/50 |

## Efficiency ratios

Candidate/baseline, 95% bootstrap CI from 2000 resamples of runs within each task:

- total tokens per correct: ×0.96 (95% CI 0.85–1.08)
- uncached tokens per correct: ×0.90 (95% CI 0.81–1.00)
- median wall time: ×0.96 (95% CI 0.89–1.07)
- p90 wall time: ×0.99 (95% CI 0.86–1.09)

## Run classifications

| Arm | Success | Solution failure | Infrastructure failure | Unknown |
|---|---:|---:|---:|---:|
| omp-read-100 | 50 | 0 | 0 | 0 |
| omp-read-300 | 50 | 0 | 0 | 0 |

## Charts

![Summary](charts/summary.svg)
![Tokens per task](charts/tokens-per-task.svg)
![Wall time per task](charts/wall-time-per-task.svg)

## Per-task results

| Task | Arm | Passed/runs | Median wall s | Median total tokens | Median uncached tokens |
|---|---|---:|---:|---:|---:|
| bugfix-duration | omp-read-100 | 5/5 | 49.9 | 31935 | 7991 |
| bugfix-duration | omp-read-300 | 5/5 | 48.3 | 31938 | 7594 |
| bugfix-invoice | omp-read-100 | 5/5 | 150.1 | 99842 | 22100 |
| bugfix-invoice | omp-read-300 | 5/5 | 141.1 | 73726 | 20574 |
| debug-cache-race | omp-read-100 | 5/5 | 183.7 | 85177 | 26302 |
| debug-cache-race | omp-read-300 | 5/5 | 165.3 | 73614 | 17934 |
| debug-limiter | omp-read-100 | 5/5 | 60.2 | 32562 | 11270 |
| debug-limiter | omp-read-300 | 5/5 | 66.1 | 32676 | 7137 |
| feature-csv-stream | omp-read-100 | 5/5 | 171.7 | 77337 | 20465 |
| feature-csv-stream | omp-read-300 | 5/5 | 173.5 | 102763 | 24299 |
| feature-lru | omp-read-100 | 5/5 | 68.0 | 35264 | 12096 |
| feature-lru | omp-read-300 | 5/5 | 76.3 | 36045 | 9933 |
| hard-dep-resolver | omp-read-100 | 5/5 | 289.9 | 182530 | 51531 |
| hard-dep-resolver | omp-read-300 | 5/5 | 251.1 | 157723 | 33345 |
| hard-expr-eval | omp-read-100 | 5/5 | 189.1 | 86367 | 21851 |
| hard-expr-eval | omp-read-300 | 5/5 | 192.6 | 120628 | 27855 |
| hard-line-diff | omp-read-100 | 5/5 | 291.1 | 89411 | 28505 |
| hard-line-diff | omp-read-300 | 5/5 | 322.5 | 93811 | 30560 |
| hard-segment-tree | omp-read-100 | 5/5 | 130.5 | 67695 | 20079 |
| hard-segment-tree | omp-read-300 | 5/5 | 122.5 | 69313 | 18195 |

Per-task scorecards (all attempts retained):

| Task | Arm | Passed/runs | Total tokens/correct | Uncached tokens/correct | Median wall s | P90 wall s | Success / solution failure / infrastructure failure / unknown |
|---|---|---:|---:|---:|---:|---:|---|
| bugfix-duration | omp-read-100 | 5/5 | 31972 | 8727 | 49.9 | 51.0 | 5 / 0 / 0 / 0 |
| bugfix-duration | omp-read-300 | 5/5 | 31989 | 9052 | 48.3 | 53.9 | 5 / 0 / 0 / 0 |
| bugfix-invoice | omp-read-100 | 5/5 | 101261 | 24052 | 150.1 | 170.9 | 5 / 0 / 0 / 0 |
| bugfix-invoice | omp-read-300 | 5/5 | 85130 | 22486 | 141.1 | 172.8 | 5 / 0 / 0 / 0 |
| debug-cache-race | omp-read-100 | 5/5 | 86606 | 26446 | 183.7 | 211.1 | 5 / 0 / 0 / 0 |
| debug-cache-race | omp-read-300 | 5/5 | 68435 | 19360 | 165.3 | 172.8 | 5 / 0 / 0 / 0 |
| debug-limiter | omp-read-100 | 5/5 | 33807 | 9666 | 60.2 | 80.6 | 5 / 0 / 0 / 0 |
| debug-limiter | omp-read-300 | 5/5 | 35174 | 8959 | 66.1 | 73.7 | 5 / 0 / 0 / 0 |
| feature-csv-stream | omp-read-100 | 5/5 | 90926 | 24315 | 171.7 | 201.6 | 5 / 0 / 0 / 0 |
| feature-csv-stream | omp-read-300 | 5/5 | 93704 | 23407 | 173.5 | 196.0 | 5 / 0 / 0 / 0 |
| feature-lru | omp-read-100 | 5/5 | 35473 | 12049 | 68.0 | 95.2 | 5 / 0 / 0 / 0 |
| feature-lru | omp-read-300 | 5/5 | 38907 | 12180 | 76.3 | 98.1 | 5 / 0 / 0 / 0 |
| hard-dep-resolver | omp-read-100 | 5/5 | 190689 | 46535 | 289.9 | 301.9 | 5 / 0 / 0 / 0 |
| hard-dep-resolver | omp-read-300 | 5/5 | 143911 | 33805 | 251.1 | 299.2 | 5 / 0 / 0 / 0 |
| hard-expr-eval | omp-read-100 | 5/5 | 94106 | 23399 | 189.1 | 242.0 | 5 / 0 / 0 / 0 |
| hard-expr-eval | omp-read-300 | 5/5 | 131263 | 26918 | 192.6 | 251.4 | 5 / 0 / 0 / 0 |
| hard-line-diff | omp-read-100 | 5/5 | 93626 | 28269 | 291.1 | 332.0 | 5 / 0 / 0 / 0 |
| hard-line-diff | omp-read-300 | 5/5 | 96272 | 29840 | 322.5 | 393.1 | 5 / 0 / 0 / 0 |
| hard-segment-tree | omp-read-100 | 5/5 | 78894 | 21294 | 130.5 | 147.3 | 5 / 0 / 0 / 0 |
| hard-segment-tree | omp-read-300 | 5/5 | 75735 | 16266 | 122.5 | 135.9 | 5 / 0 / 0 / 0 |

Per-task point effects (descriptive only; no per-task winner or confidence claim):

| Task | Pass-rate difference (candidate - baseline, pp) | Total tokens/correct ratio | Uncached tokens/correct ratio | Median wall ratio | P90 wall ratio |
|---|---:|---:|---:|---:|---:|
| bugfix-duration | +0.0 | 1.00 | 1.04 | 0.97 | 1.06 |
| bugfix-invoice | +0.0 | 0.84 | 0.93 | 0.94 | 1.01 |
| debug-cache-race | +0.0 | 0.79 | 0.73 | 0.90 | 0.82 |
| debug-limiter | +0.0 | 1.04 | 0.93 | 1.10 | 0.91 |
| feature-csv-stream | +0.0 | 1.03 | 0.96 | 1.01 | 0.97 |
| feature-lru | +0.0 | 1.10 | 1.01 | 1.12 | 1.03 |
| hard-dep-resolver | +0.0 | 0.75 | 0.73 | 0.87 | 0.99 |
| hard-expr-eval | +0.0 | 1.39 | 1.15 | 1.02 | 1.04 |
| hard-line-diff | +0.0 | 1.03 | 1.06 | 1.11 | 1.18 |
| hard-segment-tree | +0.0 | 0.96 | 0.76 | 0.94 | 0.92 |

## Setup

### Invocation 2026-10-01T17:25:04.264147+00:00

- Config: benchmark-omp-read-threshold.toml
- Trials/jobs: 5/4
- Alternate order: False; timeout: None
- Platform: Windows-11-10.0.26200-SP0
- Python: 3.12.12; Node: v22.20.0
- omp-read-100: kind omp, version omp/18.4.8, config hash 6ddff74cc261e718363cd061924810e834b129a2be2e7383f2c1a011e1796853, state isolated from experiments/omp-isolated/agent
- omp-read-300: kind omp, version omp/18.4.8, config hash 38cfb7d90b21eaf0ee73eeeca77cb65efd08efdfd1084b68e187f5a9bde09ddf, state isolated from experiments/omp-isolated/agent

Command template argv difference (differing elements only):
```json
{
  "omp-read-100": [
    "{benchmark_dir}/experiments/omp-read-threshold/baseline.yml"
  ],
  "omp-read-300": [
    "{benchmark_dir}/experiments/omp-read-threshold/candidate.yml"
  ]
}
```

Overlay omp-read-100: experiments/omp-read-threshold/baseline.yml (sha256 487fef3ed87d9596d46d8daa8f058a1a39b7daf419ec2526232a0400bdf9aa28)
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

Overlay omp-read-300: experiments/omp-read-threshold/candidate.yml (sha256 58821b8f033a3e79acf14495f58251449eee8beee4ad6c1852fc38d925035a10)
```
inlineToolDescriptors: "off"
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
- debug-cache-race: 223c66c5d3ac
- debug-limiter: 1d2a7f085811
- feature-csv-stream: 4f8c748564da
- feature-lru: 7d8ff3b71568
- hard-dep-resolver: c5041eab8ad4
- hard-expr-eval: 7e651a4872ef
- hard-line-diff: d140d53f0099
- hard-segment-tree: 51474f0d7d5a


## Warnings

- correctness at ceiling: every run passed, so these tasks cannot distinguish correctness

## Reproduce

```console
python -m bench --config benchmark-omp-read-threshold.toml --results results/omp-read-threshold-2026-10-rerun run --harness omp-read-100 omp-read-300 --trials 5 --jobs 4 --task bugfix-duration bugfix-invoice debug-cache-race debug-limiter feature-csv-stream feature-lru hard-dep-resolver hard-expr-eval hard-line-diff hard-segment-tree
python -m bench --config benchmark-omp-read-threshold.toml --results published/omp-read-threshold-2026-10 compare --baseline omp-read-100 --candidate omp-read-300 --margin 0.1 --min-trials 5 --format markdown
```

Run from the benchmark directory with the recorded config and tasks. The first command collects new trials in a fresh directory (compare it by pointing --results there); the second re-scores the runs in this report, and works on an exported bundle without model access.

## How to read this

Correctness and safety require non-inferiority (no extra failures or safety regressions). Tokens and time compare the 95% bootstrap interval of the candidate/baseline ratio with the 10% margin: worse if the whole interval is above it, better if an interval is wholly below it and no loss beyond it is possible, the same if it lies inside the band; otherwise the verdict is inconclusive. Infrastructure contamination makes a comparison inconclusive unless correctness or safety is measurably worse. Run classifications use explicit recorded evidence; missing legacy evidence is unknown, not infrastructure. Unknown ≠ 0; medians use known runs only. Tokens per correct solution include failed attempts. Per-task ratios and pass-rate differences are descriptive point effects, not per-task winners; aggregate bootstrap resampling is unchanged.
