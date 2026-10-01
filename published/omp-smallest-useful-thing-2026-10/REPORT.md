# omp-smallest vs omp-baseline

Verdict: better (omp-smallest vs baseline omp-baseline, margin 10%, min trials 3)

**Winner: omp-smallest (candidate). Compared with omp-baseline (baseline) it runs faster; correctness, tokens and safety are the same.**

| Dimension | omp-smallest vs omp-baseline | omp-baseline (baseline) | omp-smallest (candidate) |
|---|---|---|---|
| correctness | same | 12/12 passed, 0 regression runs, 0 unfinished | 12/12 passed, 0 regression runs, 0 unfinished |
| tokens | same | 74157 total / 24323 uncached per correct, 0 aux calls | 74274 total / 25719 uncached per correct, 0 aux calls |
| time | better | median 201.3 s, p90 302.5 s | median 195.7 s, p90 269.3 s |
| safety | same | 0 timeouts, 0 tampered, verification 12/12 | 0 timeouts, 0 tampered, verification 12/12 |

## Charts

![Summary](charts/summary.svg)
![Tokens per task](charts/tokens-per-task.svg)
![Wall time per task](charts/wall-time-per-task.svg)

## Per-task results

| Task | Arm | Passed/runs | Median wall s | Median total tokens | Median uncached tokens |
|---|---|---:|---:|---:|---:|
| hard-dep-resolver | omp-baseline | 3/3 | 302.5 | 125736 | 35175 |
| hard-dep-resolver | omp-smallest | 3/3 | 240.9 | 57535 | 23950 |
| hard-expr-eval | omp-baseline | 3/3 | 162.5 | 67384 | 20778 |
| hard-expr-eval | omp-smallest | 3/3 | 158.6 | 99539 | 21610 |
| hard-line-diff | omp-baseline | 3/3 | 247.8 | 55650 | 19426 |
| hard-line-diff | omp-smallest | 3/3 | 269.3 | 52161 | 27713 |
| hard-segment-tree | omp-baseline | 3/3 | 154.6 | 59080 | 18149 |
| hard-segment-tree | omp-smallest | 3/3 | 136.3 | 71594 | 21921 |

## Setup

### Invocation 2026-09-30T21:16:23.598136+00:00

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
- Eight concurrent runs share provider load/cache conditions; timing is descriptive, not an isolated-latency guarantee.
- Total tokens per correct solution increased 0.2%; uncached tokens increased 5.7%, both within the rule's 10% band. No demonstrated token savings.
- This exercises the normal read/bash/edit/write workflow only. Plan, prewalk, subagent, orchestrator, agent-creation, web-search and vibe-mode changes were not exercised.
- Source prompt hashes and exact commits are recorded in `source-provenance.json`; the preregistered protocol and completed observations are in `experiments/omp-smallest-useful-thing/PLAN.md`.

## Reproduce

```console
python -m bench --config benchmark-omp-smallest-useful-thing.toml --results results/omp-smallest-useful-thing-2026-10-rerun run --harness omp-baseline omp-smallest --trials 3 --jobs 8 --task hard-dep-resolver hard-expr-eval hard-line-diff hard-segment-tree
python -m bench --config benchmark-omp-smallest-useful-thing.toml --results published/omp-smallest-useful-thing-2026-10 compare --baseline omp-baseline --candidate omp-smallest --margin 0.1 --min-trials 3 --format markdown
```

Run from the benchmark directory with the recorded config and tasks. The first command collects new trials in a fresh directory (compare it by pointing --results there); the second re-scores the runs in this report, and works on an exported bundle without model access.

## How to read this

Correctness and safety require non-inferiority (no extra failures or safety regressions). Tokens and time use a 10% relative margin. Unknown ≠ 0; medians use known runs only. Tokens per correct solution include failed attempts.
