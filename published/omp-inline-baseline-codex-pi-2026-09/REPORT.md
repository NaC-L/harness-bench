# OMP-inline vs OMP-baseline vs Codex vs Pi

72 measured runs: six tasks × three trials × four arms, all passed. Model: `gpt-6.1-sol`, high effort, same ChatGPT account/backend.
OMP 18.4.4; Codex 0.159.2; Pi 0.99.1. Run dates and grouping are the September 2026 experiment.

![Combined four-arm token usage](combined.svg)

| Arm | Passed | Total tokens | Uncached input + output | Total vs baseline |
|---|---:|---:|---:|---:|
| omp-inline | 18/18 | 670,440 | 307,944 | -22.4% |
| omp-baseline | 18/18 | 864,349 | 350,429 | +0.0% |
| codex | 18/18 | 2,350,499 | 366,115 | +171.9% |
| pi | 18/18 | 420,220 | 254,460 | -51.4% |

Total tokens include cache read/write once. Uncached input + output excludes cache hits; Codex’s high total is largely cached input.
All arms passed 18/18, so this study does not identify a correctness winner. Native prompts, tools, recovery and sandbox policies differ.
Preflights and one cancelled partial attempt are excluded from measured totals.

## Execution phases and latency

The first 30 runs were serial. At the user’s request, four concurrent workers completed the remaining 42 cells. No completed cell was retried or excluded.
Do not pool phase latency or compare a serial arm against a parallel arm. Phase/task/trial composition differs.
The [sanitized per-run data](runs.csv) retains phase, task, trial and elapsed time for phase-aware analysis. Empty CSV metric cells mean unknown, not zero.
The full raw sessions, local paths, account identifiers, auth files and credentials are deliberately not published.

## Try it again

See the [experiment protocol](../../experiments/omp-inline-codex-pi/PLAN.md) and [setup instructions](../../README.md#four-arm-omp--codex--pi-experiment).
Install the pinned Pi/Codex versions and use your own OMP `openai-codex` login; no credentials are provided. Requires Node, Python 3.12+, OMP and access to the pinned model.
Use a fresh results directory and one consistent schedule for the whole rerun:

```sh
python -m bench --config benchmark-omp-inline-baseline-codex-pi.toml --results results/omp-inline-codex-pi-rerun run --harness omp-inline omp-baseline codex pi --trials 3 --jobs 4
python -m bench --results results/omp-inline-codex-pi-rerun report
```

This makes real model calls. Disposable workspaces are not security sandboxes; run only trusted tasks. Codex uses workspace-write without approval-bypass flags.
OMP/Pi/Codex state is isolated; temporary OAuth credentials have no refresh tokens. Windows Codex restores inherited workspace ACLs, never credential-state ACLs.
Codex warns that helper PATH aliases cannot be created under OS temp state; its exec tool completed every measured task.
A four-job rerun’s latency must not be pooled with this mixed-phase study. For a latency-focused study, use `--jobs 1 --alternate-order` throughout instead.
