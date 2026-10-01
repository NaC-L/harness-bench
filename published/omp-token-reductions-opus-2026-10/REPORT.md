# omp-token-candidate vs omp-token-baseline

Verdict: inconclusive (omp-token-candidate vs baseline omp-token-baseline, margin 10%, min trials 5)

**No winner yet (inconclusive): total tokens per correct ×1.09 (95% CI 0.95–1.26) may be more than 10% worse; more trials needed (and 2 more).**

| Dimension | omp-token-candidate vs omp-token-baseline | omp-token-baseline (baseline) | omp-token-candidate (candidate) |
|---|---|---|---|
| correctness | same | 50/50 passed, 0 regression runs, 0 unfinished | 50/50 passed, 0 regression runs, 0 unfinished |
| tokens | uncertain | 107875 total / 17451 uncached per correct, 0 aux calls | 117734 total / 17100 uncached per correct, 0 aux calls |
| time | uncertain | median 61.8 s, p90 142.1 s | median 54.3 s, p90 151.6 s |
| safety | better | 0 timeouts, 0 tampered, verification 41/50 | 0 timeouts, 0 tampered, verification 49/50 |

## Efficiency ratios

Candidate/baseline, 95% bootstrap CI from 2000 resamples of runs within each task:

- total tokens per correct: ×1.09 (95% CI 0.95–1.26)
- uncached tokens per correct: ×0.98 (95% CI 0.90–1.06)
- median wall time: ×0.88 (95% CI 0.70–1.15)
- p90 wall time: ×1.07 (95% CI 0.66–1.27)

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
| bugfix-duration | omp-token-baseline | 5/5 | 25.9 | 34159 | 4656 |
| bugfix-duration | omp-token-candidate | 5/5 | 22.4 | 44268 | 4705 |
| bugfix-invoice | omp-token-baseline | 5/5 | 55.8 | 92165 | 16566 |
| bugfix-invoice | omp-token-candidate | 5/5 | 48.7 | 122255 | 16331 |
| debug-cache-race | omp-token-baseline | 5/5 | 63.4 | 100131 | 15449 |
| debug-cache-race | omp-token-candidate | 5/5 | 59.4 | 85528 | 13275 |
| debug-limiter | omp-token-baseline | 5/5 | 23.4 | 42995 | 4577 |
| debug-limiter | omp-token-candidate | 5/5 | 25.4 | 45125 | 4919 |
| feature-csv-stream | omp-token-baseline | 5/5 | 80.4 | 114862 | 20172 |
| feature-csv-stream | omp-token-candidate | 5/5 | 85.0 | 152602 | 21074 |
| feature-lru | omp-token-baseline | 5/5 | 26.1 | 42768 | 5488 |
| feature-lru | omp-token-candidate | 5/5 | 26.7 | 43681 | 5041 |
| hard-dep-resolver | omp-token-baseline | 5/5 | 78.9 | 107366 | 19853 |
| hard-dep-resolver | omp-token-candidate | 5/5 | 82.7 | 138235 | 21601 |
| hard-expr-eval | omp-token-baseline | 5/5 | 142.8 | 277170 | 36038 |
| hard-expr-eval | omp-token-candidate | 5/5 | 154.4 | 289154 | 35085 |
| hard-line-diff | omp-token-baseline | 5/5 | 142.1 | 172335 | 31420 |
| hard-line-diff | omp-token-candidate | 5/5 | 151.6 | 143249 | 32021 |
| hard-segment-tree | omp-token-baseline | 5/5 | 49.3 | 88492 | 12754 |
| hard-segment-tree | omp-token-candidate | 5/5 | 46.4 | 93344 | 12394 |

Per-task scorecards (all attempts retained):

| Task | Arm | Passed/runs | Total tokens/correct | Uncached tokens/correct | Median wall s | P90 wall s | Success / solution failure / infrastructure failure / unknown |
|---|---|---:|---:|---:|---:|---:|---|
| bugfix-duration | omp-token-baseline | 5/5 | 37289 | 4518 | 25.9 | 28.2 | 5 / 0 / 0 / 0 |
| bugfix-duration | omp-token-candidate | 5/5 | 42364 | 4755 | 22.4 | 27.0 | 5 / 0 / 0 / 0 |
| bugfix-invoice | omp-token-baseline | 5/5 | 96366 | 17402 | 55.8 | 98.0 | 5 / 0 / 0 / 0 |
| bugfix-invoice | omp-token-candidate | 5/5 | 119960 | 16630 | 48.7 | 53.3 | 5 / 0 / 0 / 0 |
| debug-cache-race | omp-token-baseline | 5/5 | 99163 | 14821 | 63.4 | 79.9 | 5 / 0 / 0 / 0 |
| debug-cache-race | omp-token-candidate | 5/5 | 111904 | 14858 | 59.4 | 83.7 | 5 / 0 / 0 / 0 |
| debug-limiter | omp-token-baseline | 5/5 | 45165 | 4764 | 23.4 | 32.4 | 5 / 0 / 0 / 0 |
| debug-limiter | omp-token-candidate | 5/5 | 45388 | 5007 | 25.4 | 26.2 | 5 / 0 / 0 / 0 |
| feature-csv-stream | omp-token-baseline | 5/5 | 122269 | 19826 | 80.4 | 94.9 | 5 / 0 / 0 / 0 |
| feature-csv-stream | omp-token-candidate | 5/5 | 143978 | 20408 | 85.0 | 91.7 | 5 / 0 / 0 / 0 |
| feature-lru | omp-token-baseline | 5/5 | 42941 | 5394 | 26.1 | 27.3 | 5 / 0 / 0 / 0 |
| feature-lru | omp-token-candidate | 5/5 | 48853 | 5566 | 26.7 | 33.8 | 5 / 0 / 0 / 0 |
| hard-dep-resolver | omp-token-baseline | 5/5 | 119019 | 21269 | 78.9 | 114.3 | 5 / 0 / 0 / 0 |
| hard-dep-resolver | omp-token-candidate | 5/5 | 147418 | 21705 | 82.7 | 99.6 | 5 / 0 / 0 / 0 |
| hard-expr-eval | omp-token-baseline | 5/5 | 238591 | 34655 | 142.8 | 243.0 | 5 / 0 / 0 / 0 |
| hard-expr-eval | omp-token-candidate | 5/5 | 259276 | 35452 | 154.4 | 182.5 | 5 / 0 / 0 / 0 |
| hard-line-diff | omp-token-baseline | 5/5 | 188909 | 38994 | 142.1 | 248.1 | 5 / 0 / 0 / 0 |
| hard-line-diff | omp-token-candidate | 5/5 | 162771 | 33244 | 151.6 | 186.7 | 5 / 0 / 0 / 0 |
| hard-segment-tree | omp-token-baseline | 5/5 | 89036 | 12868 | 49.3 | 52.9 | 5 / 0 / 0 / 0 |
| hard-segment-tree | omp-token-candidate | 5/5 | 95426 | 13375 | 46.4 | 79.3 | 5 / 0 / 0 / 0 |

Per-task point effects (descriptive only; no per-task winner or confidence claim):

| Task | Pass-rate difference (candidate - baseline, pp) | Total tokens/correct ratio | Uncached tokens/correct ratio | Median wall ratio | P90 wall ratio |
|---|---:|---:|---:|---:|---:|
| bugfix-duration | +0.0 | 1.14 | 1.05 | 0.87 | 0.96 |
| bugfix-invoice | +0.0 | 1.24 | 0.96 | 0.87 | 0.54 |
| debug-cache-race | +0.0 | 1.13 | 1.00 | 0.94 | 1.05 |
| debug-limiter | +0.0 | 1.00 | 1.05 | 1.09 | 0.81 |
| feature-csv-stream | +0.0 | 1.18 | 1.03 | 1.06 | 0.97 |
| feature-lru | +0.0 | 1.14 | 1.03 | 1.02 | 1.24 |
| hard-dep-resolver | +0.0 | 1.24 | 1.02 | 1.05 | 0.87 |
| hard-expr-eval | +0.0 | 1.09 | 1.02 | 1.08 | 0.75 |
| hard-line-diff | +0.0 | 0.86 | 0.85 | 1.07 | 0.75 |
| hard-segment-tree | +0.0 | 1.07 | 1.04 | 0.94 | 1.50 |

## Setup

### Invocation 2026-10-01T20:04:27.425372+00:00

- Config: benchmark-omp-token-reductions-opus.toml
- Trials/jobs: 5/8
- Alternate order: False; timeout: None
- Platform: Windows-11-10.0.26200-SP0
- Python: 3.14.3; Node: v22.20.0
- omp-token-baseline: kind omp, version omp/18.4.5, config hash be423d3de04d16527ff49ee6e7b45b2132058d375ffe22a93bb819a58388eafe, state isolated from experiments/omp-isolated/agent
- omp-token-candidate: kind omp, version omp/18.4.5, config hash f3f0b34a0b969051e88086790be1669795bb3829098da4696e83faea280cbf9d, state isolated from experiments/omp-isolated/agent

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

- total tokens per correct ×1.09 (95% CI 0.95–1.26) may be more than 10% worse; more trials needed
- median wall time ×0.88 (95% CI 0.70–1.15) may be more than 10% worse; more trials needed
- p90 wall time ×1.07 (95% CI 0.66–1.27) may be more than 10% worse; more trials needed

## Warnings

- correctness at ceiling: every run passed, so these tasks cannot distinguish correctness

## Reproduce

```console
python -m bench --config benchmark-omp-token-reductions-opus.toml --results results/omp-token-reductions-opus-2026-10-rerun run --harness omp-token-baseline omp-token-candidate --trials 5 --jobs 8 --task bugfix-duration bugfix-invoice debug-cache-race debug-limiter feature-csv-stream feature-lru hard-dep-resolver hard-expr-eval hard-line-diff hard-segment-tree
python -m bench --config benchmark-omp-token-reductions-opus.toml --results published/omp-token-reductions-opus-2026-10 compare --baseline omp-token-baseline --candidate omp-token-candidate --margin 0.1 --min-trials 5 --format markdown
```

Run from the benchmark directory with the recorded config and tasks. The first command collects new trials in a fresh directory (compare it by pointing --results there); the second re-scores the runs in this report, and works on an exported bundle without model access.

## How to read this

Correctness and safety require non-inferiority (no extra failures or safety regressions). Tokens and time compare the 95% bootstrap interval of the candidate/baseline ratio with the 10% margin: worse if the whole interval is above it, better if an interval is wholly below it and no loss beyond it is possible, the same if it lies inside the band; otherwise the verdict is inconclusive. Infrastructure contamination makes a comparison inconclusive unless correctness or safety is measurably worse. Run classifications use explicit recorded evidence; missing legacy evidence is unknown, not infrastructure. Unknown ≠ 0; medians use known runs only. Tokens per correct solution include failed attempts. Per-task ratios and pass-rate differences are descriptive point effects, not per-task winners; aggregate bootstrap resampling is unchanged.
