# Challenge-tier calibration and confirmation

## Frozen calibration protocol

Freeze this protocol before the first model run. Existing ten tasks remain unchanged efficiency controls, not evidence of correctness equivalence.

- Development fixtures: `challenge-routing` (multi-module navigation) and `challenge-journal` (interacting persistence/replay bugs).
- Held-out fixtures: `challenge-recovery` (interrupted local work) and `challenge-safety` (implementation safety boundaries).
- Arms/config: `omp-baseline` and `omp-inline` from `benchmark-omp-descriptors-opus.toml`; identical Claude Opus 5.5 high, credentials, tools, isolated state, recovery settings. Only descriptor placement differs.
- Calibration: exactly three trials per development task per arm, 12 runs total, `--jobs 4`. No held-out model runs. This is throughput calibration; concurrent provider load, cache state and another operator experiment can affect wall time. Do not interpret it as isolated latency.
- Use a fresh result directory `results/challenge-calibration-2026-10-01`. Never replace rows or selectively rerun failures. Preserve infrastructure failures and their usage; an infrastructure-contaminated comparison does not establish a harness win.
- No post-hoc trial extension to clear a confidence interval. A later run is a separately declared experiment with a fresh result root.
- Fixtures are candidates until measured. A useful development-task screening band is 40–80% pooled success (3–4 successes among six runs), with at least one success per arm. Both arms at ceiling or floor means the fixture did not discriminate here, not a harness win. Do not manufacture a failure by changing grading after seeing a run.

```sh
python -m bench.validate_tasks
python -m bench --config benchmark-omp-descriptors-opus.toml --results results/challenge-calibration-2026-10-01 run --harness omp-baseline omp-inline --task challenge-routing challenge-journal --trials 3 --jobs 4
python -m bench --results results/challenge-calibration-2026-10-01 compare --baseline omp-baseline --candidate omp-inline --format markdown
```

## Hold-out and confirmation policy

The `heldout` task tag excludes fixtures from default `run` and `run --task all`. Explicit task names are required to access them. Listing and zero-model reference validation still include them. This is a local experimental split, not a secret evaluation: source and reference solutions are public, so contamination across published runs remains possible.

Do not use recovery/safety transcripts to tune prompts, task acceptance criteria, candidate selection or overrides. Freeze candidate/config/task hashes before confirmation. Once a held-out fixture has been inspected through model-run results for tuning, mark it consumed and use new held-out fixtures for a future optimization claim.

Confirmation is a separate fixed grid: six trials per task per arm on `bugfix-duration`, `debug-cache-race`, and all four challenge tasks (72 runs), four workers, same pinned arms. Keep controls and challenges separately reported. Six is a fixed design choice, not a power guarantee: report `inconclusive` if bootstrap intervals cannot establish non-inferiority. The existing aggregate 95% bootstrap, 10% efficiency margin and correctness/safety gates remain unchanged. Also report each task's pass-rate difference and token/time point ratios; these are descriptive, not small-sample per-task winner claims.

```sh
python -m bench --config benchmark-omp-descriptors-opus.toml --results results/challenge-confirmation-FRESH run --harness omp-baseline omp-inline --task bugfix-duration debug-cache-race challenge-routing challenge-journal challenge-recovery challenge-safety --trials 6 --jobs 4
python -m bench --results results/challenge-confirmation-FRESH compare --baseline omp-baseline --candidate omp-inline --format markdown
```

## What the fixtures establish

Recovery covers deterministic injected IO/interruption and resumption in the implemented program. Safety covers local data preservation, denied operations and path boundaries. Neither establishes harness approval enforcement, prevention of real external actions, model context compaction or long-context recovery. Workdirs are disposable copies, not security sandboxes; no fixture may use real secrets, network endpoints or user data.

Infrastructure and solution failures remain in denominators and efficiency numerators. Unknown historical failure evidence must stay unknown. Calibration artifacts record exact task, prompt, configuration and context hashes, runtime versions and all runs. Never pool calibration rows with confirmation. No defaults, commits, pushes or deployment changes follow from this protocol.
