# omp-token-candidate vs omp-token-baseline

Verdict: inconclusive (omp-token-candidate vs baseline omp-token-baseline, margin 10%, min trials 5)

**No winner yet (inconclusive): p90 wall time ×1.06 (95% CI 0.91–1.23) may be more than 10% worse; more trials needed.**

| Dimension | omp-token-candidate vs omp-token-baseline | omp-token-baseline (baseline) | omp-token-candidate (candidate) |
|---|---|---|---|
| correctness | same | 50/50 passed, 0 regression runs, 0 unfinished | 50/50 passed, 0 regression runs, 0 unfinished |
| tokens | non-inferior | 79636 total / 20920 uncached per correct, 0 aux calls | 72859 total / 20062 uncached per correct, 0 aux calls |
| time | uncertain | median 154.4 s, p90 281.1 s | median 149.4 s, p90 296.7 s |
| safety | better | 0 timeouts, 0 tampered, verification 33/50 | 0 timeouts, 0 tampered, verification 37/50 |

## Efficiency ratios

Candidate/baseline, 95% bootstrap CI from 2000 resamples of runs within each task:

- total tokens per correct: ×0.91 (95% CI 0.82–1.02)
- uncached tokens per correct: ×0.96 (95% CI 0.86–1.07)
- median wall time: ×0.97 (95% CI 0.90–1.05)
- p90 wall time: ×1.06 (95% CI 0.91–1.23)

## Run classifications

| Arm | Success | Solution failure | Infrastructure failure | Unknown |
|---|---:|---:|---:|---:|
| omp-token-baseline | 50 | 0 | 0 | 0 |
| omp-token-candidate | 50 | 0 | 0 | 0 |

## Charts

![Summary](charts/summary.svg)
![Tokens per task](charts/tokens-per-task.svg)
![Wall time per task](charts/wall-time-per-task.svg)

## Per-task results

| Task | Arm | Passed/runs | Median wall s | Median total tokens | Median uncached tokens |
|---|---|---:|---:|---:|---:|
| bugfix-duration | omp-token-baseline | 5/5 | 49.7 | 31943 | 6487 |
| bugfix-duration | omp-token-candidate | 5/5 | 47.0 | 32512 | 11673 |
| bugfix-invoice | omp-token-baseline | 5/5 | 147.1 | 86347 | 25215 |
| bugfix-invoice | omp-token-candidate | 5/5 | 108.8 | 60630 | 16897 |
| debug-cache-race | omp-token-baseline | 5/5 | 160.1 | 68751 | 15843 |
| debug-cache-race | omp-token-candidate | 5/5 | 166.5 | 57410 | 21653 |
| debug-limiter | omp-token-baseline | 5/5 | 63.2 | 32124 | 6745 |
| debug-limiter | omp-token-candidate | 5/5 | 66.5 | 34058 | 13825 |
| feature-csv-stream | omp-token-baseline | 5/5 | 163.9 | 76234 | 23882 |
| feature-csv-stream | omp-token-candidate | 5/5 | 162.5 | 69416 | 20269 |
| feature-lru | omp-token-baseline | 5/5 | 73.8 | 35449 | 9721 |
| feature-lru | omp-token-candidate | 5/5 | 76.4 | 36332 | 10755 |
| hard-dep-resolver | omp-token-baseline | 5/5 | 254.7 | 165613 | 47507 |
| hard-dep-resolver | omp-token-candidate | 5/5 | 292.0 | 111968 | 28000 |
| hard-expr-eval | omp-token-baseline | 5/5 | 193.5 | 95913 | 21570 |
| hard-expr-eval | omp-token-candidate | 5/5 | 184.3 | 108051 | 25235 |
| hard-line-diff | omp-token-baseline | 5/5 | 320.4 | 82861 | 31533 |
| hard-line-diff | omp-token-candidate | 5/5 | 311.3 | 98266 | 28506 |
| hard-segment-tree | omp-token-baseline | 5/5 | 147.1 | 84882 | 20299 |
| hard-segment-tree | omp-token-candidate | 5/5 | 142.0 | 79564 | 18301 |

Per-task scorecards (all attempts retained):

| Task | Arm | Passed/runs | Total tokens/correct | Uncached tokens/correct | Median wall s | P90 wall s | Success / solution failure / infrastructure failure / unknown |
|---|---|---:|---:|---:|---:|---:|---|
| bugfix-duration | omp-token-baseline | 5/5 | 32066 | 10690 | 49.7 | 56.8 | 5 / 0 / 0 / 0 |
| bugfix-duration | omp-token-candidate | 5/5 | 33782 | 11971 | 47.0 | 60.8 | 5 / 0 / 0 / 0 |
| bugfix-invoice | omp-token-baseline | 5/5 | 91392 | 23245 | 147.1 | 164.2 | 5 / 0 / 0 / 0 |
| bugfix-invoice | omp-token-candidate | 5/5 | 66614 | 17078 | 108.8 | 119.6 | 5 / 0 / 0 / 0 |
| debug-cache-race | omp-token-baseline | 5/5 | 67420 | 17603 | 160.1 | 176.9 | 5 / 0 / 0 / 0 |
| debug-cache-race | omp-token-candidate | 5/5 | 71804 | 20860 | 166.5 | 213.2 | 5 / 0 / 0 / 0 |
| debug-limiter | omp-token-baseline | 5/5 | 32437 | 7707 | 63.2 | 86.2 | 5 / 0 / 0 / 0 |
| debug-limiter | omp-token-candidate | 5/5 | 35416 | 13784 | 66.5 | 76.0 | 5 / 0 / 0 / 0 |
| feature-csv-stream | omp-token-baseline | 5/5 | 84091 | 21474 | 163.9 | 194.9 | 5 / 0 / 0 / 0 |
| feature-csv-stream | omp-token-candidate | 5/5 | 70405 | 21048 | 162.5 | 182.6 | 5 / 0 / 0 / 0 |
| feature-lru | omp-token-baseline | 5/5 | 33866 | 9956 | 73.8 | 77.4 | 5 / 0 / 0 / 0 |
| feature-lru | omp-token-candidate | 5/5 | 40332 | 13605 | 76.4 | 113.0 | 5 / 0 / 0 / 0 |
| hard-dep-resolver | omp-token-baseline | 5/5 | 167812 | 46136 | 254.7 | 322.2 | 5 / 0 / 0 / 0 |
| hard-dep-resolver | omp-token-candidate | 5/5 | 108208 | 29667 | 292.0 | 313.6 | 5 / 0 / 0 / 0 |
| hard-expr-eval | omp-token-baseline | 5/5 | 102574 | 22548 | 193.5 | 255.9 | 5 / 0 / 0 / 0 |
| hard-expr-eval | omp-token-candidate | 5/5 | 110642 | 27186 | 184.3 | 220.9 | 5 / 0 / 0 / 0 |
| hard-line-diff | omp-token-baseline | 5/5 | 94052 | 29821 | 320.4 | 331.8 | 5 / 0 / 0 / 0 |
| hard-line-diff | omp-token-candidate | 5/5 | 109033 | 26242 | 311.3 | 354.6 | 5 / 0 / 0 / 0 |
| hard-segment-tree | omp-token-baseline | 5/5 | 90651 | 20020 | 147.1 | 172.3 | 5 / 0 / 0 / 0 |
| hard-segment-tree | omp-token-candidate | 5/5 | 82355 | 19174 | 142.0 | 158.4 | 5 / 0 / 0 / 0 |

Per-task point effects (descriptive only; no per-task winner or confidence claim):

| Task | Pass-rate difference (candidate - baseline, pp) | Total tokens/correct ratio | Uncached tokens/correct ratio | Median wall ratio | P90 wall ratio |
|---|---:|---:|---:|---:|---:|
| bugfix-duration | +0.0 | 1.05 | 1.12 | 0.95 | 1.07 |
| bugfix-invoice | +0.0 | 0.73 | 0.73 | 0.74 | 0.73 |
| debug-cache-race | +0.0 | 1.07 | 1.19 | 1.04 | 1.20 |
| debug-limiter | +0.0 | 1.09 | 1.79 | 1.05 | 0.88 |
| feature-csv-stream | +0.0 | 0.84 | 0.98 | 0.99 | 0.94 |
| feature-lru | +0.0 | 1.19 | 1.37 | 1.03 | 1.46 |
| hard-dep-resolver | +0.0 | 0.64 | 0.64 | 1.15 | 0.97 |
| hard-expr-eval | +0.0 | 1.08 | 1.21 | 0.95 | 0.86 |
| hard-line-diff | +0.0 | 1.16 | 0.88 | 0.97 | 1.07 |
| hard-segment-tree | +0.0 | 0.91 | 0.96 | 0.97 | 0.92 |

## Setup

### Invocation 2026-10-01T17:25:11.057276+00:00

- Config: benchmark-omp-token-reductions.toml
- Trials/jobs: 5/4
- Alternate order: False; timeout: None
- Platform: Windows-11-10.0.26200-SP0
- Python: 3.12.12; Node: v22.20.0
- omp-token-baseline: kind omp, version omp/18.4.5, config hash 9ffd206e4b5b396bc445e9460c1b5c86afb06da11abca83284711d8a1475ad0b, state isolated from experiments/omp-isolated/agent
- omp-token-candidate: kind omp, version omp/18.4.5, config hash 6b246e9b71238af5a1210de74cb9c9764e870415114e33c3b75bf5ba88319328, state isolated from experiments/omp-isolated/agent

Command template argv difference (differing elements only):
```json
{
  "omp-token-baseline": [
    "{benchmark_dir}/../omp-token-baseline/packages/coding-agent/src/cli.ts"
  ],
  "omp-token-candidate": [
    "{benchmark_dir}/../oh-my-pi/packages/coding-agent/src/cli.ts"
  ]
}
```
```json
{
  "omp-token-baseline": [
    "{benchmark_dir}/../omp-token-baseline/packages/coding-agent/src/prompts/system/system-prompt.md"
  ],
  "omp-token-candidate": [
    "{benchmark_dir}/../oh-my-pi/packages/coding-agent/src/prompts/system/system-prompt.md"
  ]
}
```
```json
{
  "omp-token-baseline": [
    "{benchmark_dir}/experiments/omp-token-reductions/baseline.yml"
  ],
  "omp-token-candidate": [
    "{benchmark_dir}/experiments/omp-token-reductions/candidate.yml"
  ]
}
```

Overlay omp-token-baseline: experiments/omp-token-reductions/baseline.yml (sha256 487fef3ed87d9596d46d8daa8f058a1a39b7daf419ec2526232a0400bdf9aa28)
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

Overlay omp-token-candidate: experiments/omp-token-reductions/candidate.yml (sha256 9c4ec3e34edf1673005c7dec5ebbb352ebef7a985c853b44c25ea203ad989179)
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
- debug-cache-race: 223c66c5d3ac
- debug-limiter: 1d2a7f085811
- feature-csv-stream: 4f8c748564da
- feature-lru: 7d8ff3b71568
- hard-dep-resolver: c5041eab8ad4
- hard-expr-eval: 7e651a4872ef
- hard-line-diff: d140d53f0099
- hard-segment-tree: 51474f0d7d5a


## Reasons

- p90 wall time ×1.06 (95% CI 0.91–1.23) may be more than 10% worse; more trials needed

## Warnings

- correctness at ceiling: every run passed, so these tasks cannot distinguish correctness

## Reproduce

```console
python -m bench --config benchmark-omp-token-reductions.toml --results results/omp-token-reductions-2026-10-rerun run --harness omp-token-baseline omp-token-candidate --trials 5 --jobs 4 --task bugfix-duration bugfix-invoice debug-cache-race debug-limiter feature-csv-stream feature-lru hard-dep-resolver hard-expr-eval hard-line-diff hard-segment-tree
python -m bench --config benchmark-omp-token-reductions.toml --results published/omp-token-reductions-2026-10 compare --baseline omp-token-baseline --candidate omp-token-candidate --margin 0.1 --min-trials 5 --format markdown
```

Run from the benchmark directory with the recorded config and tasks. The first command collects new trials in a fresh directory (compare it by pointing --results there); the second re-scores the runs in this report, and works on an exported bundle without model access.

## How to read this

Correctness and safety require non-inferiority (no extra failures or safety regressions). Tokens and time compare the 95% bootstrap interval of the candidate/baseline ratio with the 10% margin: worse if the whole interval is above it, better if an interval is wholly below it and no loss beyond it is possible, the same if it lies inside the band; otherwise the verdict is inconclusive. Infrastructure contamination makes a comparison inconclusive unless correctness or safety is measurably worse. Run classifications use explicit recorded evidence; missing legacy evidence is unknown, not infrastructure. Unknown ≠ 0; medians use known runs only. Tokens per correct solution include failed attempts. Per-task ratios and pass-rate differences are descriptive point effects, not per-task winners; aggregate bootstrap resampling is unchanged.
