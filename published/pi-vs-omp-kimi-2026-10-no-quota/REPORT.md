# pi-kimi vs omp-kimi

**Quota-filtered analysis:** excluded exactly 14 runs whose captured provider output reports the Kimi five-hour usage limit (OMP 6, Pi 8). Original 60-run evidence is unchanged. All tokens, times, scores, charts, and transcripts below use only the remaining 46 runs. The authentication rejection, timeout, and six task-check failures remain. Excluded run IDs and source hash are recorded in `manifest.json` under `filter`.

OMP passed 20/24 (83.3%); Pi passed 18/22 (81.8%). This is a post-hoc, unequal-count comparison with 22 matched task/trial pairs and incomplete three-trial coverage; aggregate efficiency differences are descriptive of retained attempts. Eight-worker latency includes provider contention.

Verdict: inconclusive (pi-kimi vs baseline omp-kimi, margin 10%, min trials 3)

**No winner yet (inconclusive): omp-kimi/feature-csv-stream: 2 trials < 3 (and 11 more).**

| Dimension | pi-kimi vs omp-kimi | omp-kimi (baseline) | pi-kimi (candidate) |
|---|---|---|---|
| correctness | worse | 20/24 passed, 0 regression runs, 1 unfinished | 18/22 passed, 0 regression runs, 1 unfinished |
| tokens | better | 156255 total / 22354 uncached per correct, 0 aux calls | 92755 total / 19439 uncached per correct, 0 aux calls |
| time | uncertain | median 134.4 s, p90 455.0 s | median 118.4 s, p90 321.9 s |
| safety | worse | 0 timeouts, 0 tampered, verification 23/24 | 1 timeouts, 0 tampered, verification 22/22 |

## Efficiency ratios

Candidate/baseline, 95% bootstrap CI from 2000 resamples of runs within each task:

- total tokens per correct: ×0.59 (95% CI 0.52–0.68)
- uncached tokens per correct: ×0.87 (95% CI 0.78–0.97)
- median wall time: ×0.88 (95% CI 0.74–1.06)
- p90 wall time: ×0.71 (95% CI 0.56–1.76)

## Run classifications

| Arm | Success | Solution failure | Infrastructure failure | Unknown |
|---|---:|---:|---:|---:|
| omp-kimi | 20 | 4 | 0 | 0 |
| pi-kimi | 18 | 4 | 0 | 0 |

## Charts

![Summary](charts/summary.svg)
![Tokens per task](charts/tokens-per-task.svg)
![Wall time per task](charts/wall-time-per-task.svg)

## Per-task results

| Task | Arm | Passed/runs | Median wall s | Median total tokens | Median uncached tokens |
|---|---|---:|---:|---:|---:|
| bugfix-duration | omp-kimi | 3/3 | 38.6 | 19428 | 3044 |
| bugfix-duration | pi-kimi | 3/3 | 30.2 | 9215 | 2248 |
| bugfix-invoice | omp-kimi | 3/3 | 140.9 | 112472 | 16996 |
| bugfix-invoice | pi-kimi | 3/3 | 98.3 | 56908 | 13420 |
| debug-cache-race | omp-kimi | 3/3 | 160.4 | 115601 | 17627 |
| debug-cache-race | pi-kimi | 2/2 | 200.6 | 79435 | 17099 |
| debug-limiter | omp-kimi | 0/3 | 54.6 | 30287 | 4388 |
| debug-limiter | pi-kimi | 0/3 | 22.3 | 12675 | 3081 |
| feature-csv-stream | omp-kimi | 1/2 | 376.7 | 139590 | 19910 |
| feature-csv-stream | pi-kimi | 2/2 | 221.9 | 56180 | 17524 |
| feature-lru | omp-kimi | 3/3 | 51.2 | 20569 | 4185 |
| feature-lru | pi-kimi | 2/2 | 49.9 | 16211 | 3923 |
| hard-dep-resolver | omp-kimi | 2/2 | 397.8 | 231250 | 34642 |
| hard-dep-resolver | pi-kimi | 1/2 | 1028.5 | 115690 | 31722 |
| hard-expr-eval | omp-kimi | 2/2 | 412.8 | 475994 | 36186 |
| hard-expr-eval | pi-kimi | 2/2 | 281.2 | 112772 | 26116 |
| hard-line-diff | omp-kimi | 1/1 | 787.6 | 441620 | 95508 |
| hard-line-diff | pi-kimi | 1/1 | 650.4 | 566443 | 72107 |
| hard-segment-tree | omp-kimi | 2/2 | 121.5 | 72858 | 13722 |
| hard-segment-tree | pi-kimi | 2/2 | 153.7 | 44742 | 12102 |

Per-task scorecards (all attempts retained):

| Task | Arm | Passed/runs | Total tokens/correct | Uncached tokens/correct | Median wall s | P90 wall s | Success / solution failure / infrastructure failure / unknown |
|---|---|---:|---:|---:|---:|---:|---|
| bugfix-duration | omp-kimi | 3/3 | 20127 | 3402 | 38.6 | 41.8 | 3 / 0 / 0 / 0 |
| bugfix-duration | pi-kimi | 3/3 | 14001 | 3420 | 30.2 | 76.5 | 3 / 0 / 0 / 0 |
| bugfix-invoice | omp-kimi | 3/3 | 109353 | 18217 | 140.9 | 174.0 | 3 / 0 / 0 / 0 |
| bugfix-invoice | pi-kimi | 3/3 | 57723 | 13776 | 98.3 | 114.8 | 3 / 0 / 0 / 0 |
| debug-cache-race | omp-kimi | 3/3 | 101946 | 16527 | 160.4 | 176.1 | 3 / 0 / 0 / 0 |
| debug-cache-race | pi-kimi | 2/2 | 79435 | 17099 | 200.6 | 231.8 | 2 / 0 / 0 / 0 |
| debug-limiter | omp-kimi | 0/3 | unknown | unknown | 54.6 | 57.4 | 0 / 3 / 0 / 0 |
| debug-limiter | pi-kimi | 0/3 | unknown | unknown | 22.3 | 40.9 | 0 / 3 / 0 / 0 |
| feature-csv-stream | omp-kimi | 1/2 | 279180 | 39820 | 376.7 | 446.8 | 1 / 1 / 0 / 0 |
| feature-csv-stream | pi-kimi | 2/2 | 56180 | 17524 | 221.9 | 321.9 | 2 / 0 / 0 / 0 |
| feature-lru | omp-kimi | 3/3 | 23170 | 5336 | 51.2 | 113.9 | 3 / 0 / 0 / 0 |
| feature-lru | pi-kimi | 2/2 | 16211 | 3923 | 49.9 | 63.8 | 2 / 0 / 0 / 0 |
| hard-dep-resolver | omp-kimi | 2/2 | 231250 | 34642 | 397.8 | 457.9 | 2 / 0 / 0 / 0 |
| hard-dep-resolver | pi-kimi | 1/2 | 231379 | 63443 | 1028.5 | 1800.1 | 1 / 1 / 0 / 0 |
| hard-expr-eval | omp-kimi | 2/2 | 475994 | 36186 | 412.8 | 455.0 | 2 / 0 / 0 / 0 |
| hard-expr-eval | pi-kimi | 2/2 | 112772 | 26116 | 281.2 | 314.2 | 2 / 0 / 0 / 0 |
| hard-line-diff | omp-kimi | 1/1 | 441620 | 95508 | 787.6 | 787.6 | 1 / 0 / 0 / 0 |
| hard-line-diff | pi-kimi | 1/1 | 566443 | 72107 | 650.4 | 650.4 | 1 / 0 / 0 / 0 |
| hard-segment-tree | omp-kimi | 2/2 | 72858 | 13722 | 121.5 | 144.7 | 2 / 0 / 0 / 0 |
| hard-segment-tree | pi-kimi | 2/2 | 44742 | 12102 | 153.7 | 172.5 | 2 / 0 / 0 / 0 |

Per-task point effects (descriptive only; no per-task winner or confidence claim):

| Task | Pass-rate difference (candidate - baseline, pp) | Total tokens/correct ratio | Uncached tokens/correct ratio | Median wall ratio | P90 wall ratio |
|---|---:|---:|---:|---:|---:|
| bugfix-duration | +0.0 | 0.70 | 1.01 | 0.78 | 1.83 |
| bugfix-invoice | +0.0 | 0.53 | 0.76 | 0.70 | 0.66 |
| debug-cache-race | +0.0 | 0.78 | 1.03 | 1.25 | 1.32 |
| debug-limiter | +0.0 | unknown | unknown | 0.41 | 0.71 |
| feature-csv-stream | +50.0 | 0.20 | 0.44 | 0.59 | 0.72 |
| feature-lru | +0.0 | 0.70 | 0.74 | 0.97 | 0.56 |
| hard-dep-resolver | -50.0 | 1.00 | 1.83 | 2.59 | 3.93 |
| hard-expr-eval | +0.0 | 0.24 | 0.72 | 0.68 | 0.69 |
| hard-line-diff | +0.0 | 1.28 | 0.75 | 0.83 | 0.83 |
| hard-segment-tree | +0.0 | 0.61 | 0.88 | 1.27 | 1.19 |

## Setup

### Invocation 2026-10-01T13:27:01.190039+00:00

- Config: benchmark-pi-omp-kimi.toml
- Trials/jobs: 3/8
- Alternate order: False; timeout: None
- Platform: Windows-11-10.0.26200-SP0
- Python: 3.14.3; Node: v22.20.0
- omp-kimi: kind omp, version omp/18.4.8, config hash 5e66a398ab527a0d9291d8bcf021832941807d53fe4a74f5f5373435911d9571, state isolated from experiments/pi-omp-kimi/omp
- pi-kimi: kind pi, version 0.99.1, config hash 70426fc7887a3b4fea16cad47f31cf8c1d4babcd86b16e4e13e8512aea5489a8, state isolated from experiments/omp-inline-codex-pi/pi

Command template argv difference (differing elements only):
```json
{
  "omp-kimi": [
    "omp"
  ],
  "pi-kimi": [
    "node",
    "{benchmark_dir}/.tools/pi/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js"
  ]
}
```
```json
{
  "omp-kimi": [
    "--no-title",
    "--config",
    "{benchmark_dir}/experiments/pi-omp-sol/omp.yml",
    "--no-prewalk"
  ],
  "pi-kimi": []
}
```
```json
{
  "omp-kimi": [
    "--no-rules"
  ],
  "pi-kimi": [
    "--no-prompt-templates",
    "--no-context-files"
  ]
}
```
```json
{
  "omp-kimi": [
    "kimi-code/k3"
  ],
  "pi-kimi": [
    "kimi-coding/k3"
  ]
}
```
```json
{
  "omp-kimi": [],
  "pi-kimi": [
    "--session-id",
    "{session_id}"
  ]
}
```

Overlay pi-kimi: .tools/pi/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js (sha256 e79626f2dd6f94aa45d30f3fa63cd84319a6eefcd150b353cfaf274366926774)
```
#!/usr/bin/env node
import { createRequire, enableCompileCache } from "node:module";

enableCompileCache();
createRequire(import.meta.url)("./cli-runtime.js");

```

Overlay pi-kimi: experiments/omp-inline-codex-pi/pi/settings.json (sha256 ca3d163bab055381827226140568f3bef7eaac187cebd76878e0b63e9e442356)
```
{}

```

Overlay omp-kimi: experiments/pi-omp-kimi/omp/config.yml (sha256 4ff0d63a3c0a4d8a968b8e20c889edf08140e796738543b85377d76e3a29a49d)
```
# Benchmark-owned state; all unspecified settings use OMP defaults.
memory:
  backend: "off"

```

Overlay omp-kimi: experiments/pi-omp-kimi/omp/models.yml (sha256 7ed25a3f5ceee346d1737e154962ef95079966d39a9186e911c7645b833bf5e8)
```
# Resolve the runner-exported credential; no secret is stored in this template.
providers:
  kimi-code:
    apiKey: KIMI_API_KEY

```

Overlay omp-kimi: experiments/pi-omp-sol/omp.yml (sha256 8f0758882fdc929d170bad036a9cb909d3d7cf8613e931349291534af12a83d8)
```
features:

  unexpectedStopDetection: off

advisor:

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

- omp-kimi/feature-csv-stream: 2 trials < 3
- omp-kimi/hard-dep-resolver: 2 trials < 3
- omp-kimi/hard-expr-eval: 2 trials < 3
- omp-kimi/hard-line-diff: 1 trials < 3
- omp-kimi/hard-segment-tree: 2 trials < 3
- pi-kimi/debug-cache-race: 2 trials < 3
- pi-kimi/feature-csv-stream: 2 trials < 3
- pi-kimi/feature-lru: 2 trials < 3
- pi-kimi/hard-dep-resolver: 2 trials < 3
- pi-kimi/hard-expr-eval: 2 trials < 3
- pi-kimi/hard-line-diff: 1 trials < 3
- pi-kimi/hard-segment-tree: 2 trials < 3

## Warnings

- harness versions differ: omp/18.4.8 vs 0.99.1

## Reproduce

```console
python -m bench --config benchmark-pi-omp-kimi.toml --results results/pi-vs-omp-kimi-2026-10-no-quota-rerun run --harness omp-kimi pi-kimi --trials 3 --jobs 8 --task bugfix-duration bugfix-invoice debug-cache-race debug-limiter feature-csv-stream feature-lru hard-dep-resolver hard-expr-eval hard-line-diff hard-segment-tree
python -m bench --config benchmark-pi-omp-kimi.toml --results published/pi-vs-omp-kimi-2026-10-no-quota compare --baseline omp-kimi --candidate pi-kimi --margin 0.1 --min-trials 3 --format markdown
```

Run from the benchmark directory with the recorded config and tasks. The first command collects new trials in a fresh directory (compare it by pointing --results there); the second re-scores the runs in this report, and works on an exported bundle without model access.

## How to read this

Correctness and safety require non-inferiority (no extra failures or safety regressions). Tokens and time compare the 95% bootstrap interval of the candidate/baseline ratio with the 10% margin: worse if the whole interval is above it, better if an interval is wholly below it and no loss beyond it is possible, the same if it lies inside the band; otherwise the verdict is inconclusive. Infrastructure contamination makes a comparison inconclusive unless correctness or safety is measurably worse. Run classifications use explicit recorded evidence; missing legacy evidence is unknown, not infrastructure. Unknown ≠ 0; medians use known runs only. Tokens per correct solution include failed attempts. Per-task ratios and pass-rate differences are descriptive point effects, not per-task winners; aggregate bootstrap resampling is unchanged.
