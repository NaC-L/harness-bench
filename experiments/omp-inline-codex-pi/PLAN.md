# OMP inline vs OMP baseline vs Codex vs Pi

Protocol fixed before measured runs, 2026-09-30.

## Arms and controls

Config: `benchmark-omp-inline-baseline-codex-pi.toml`.
Arms: `omp-inline`, `omp-baseline`, `codex`, `pi`.
All use `gpt-6.1-sol`, high reasoning effort, the ChatGPT/Codex backend and
fresh access tokens from the same OMP login. Versions are captured in manifests;
local Codex is pinned to 0.159.2 and Pi is the existing 0.99.1 installation.
Each run receives a new task workspace and benchmark-owned state template.
No operator instructions, MCP config or refresh tokens are copied. The OAuth
adapter creates temporary access-only credentials for native Pi/Codex.

OMP commands are identical to the existing isolated descriptor experiment.
Only their inline descriptor overlay differs. OMP and Pi expose read/bash/edit/write;
Codex uses its native tools and workspace-write sandbox without permission bypass.
On Windows, the runner restores inherited ACLs on the disposable Codex workspace
because Python 3.14's owner-only temporary-directory ACL blocks sandbox reads.
Credential-state ACLs are not changed. Codex warns that helper PATH aliases cannot
be created under the OS temp directory; its native `exec` tool still read, edited
and verified the preflight task. Record this limitation when interpreting tool usage.
Cross-harness comparisons therefore measure the native harness packages, including
prompts, tools, transport, recovery and sandbox policy, not descriptor placement alone.
The Pi arm deliberately uses `openai-codex`, unlike the older non-isolated
`pi-sol` arm's `openai` provider; old rows are not pooled into this experiment.

## Grid and execution

Six repository tasks, three trials per task per arm: 72 measured runs.
Separate four-run `bugfix-duration` preflight, excluded from analysis. Each preflight
must launch, complete, pass hidden grading and produce attributable token metrics.
Infrastructure failures block the measured grid until diagnosed; preflight attempts
remain recorded separately. Measured failures/timeouts remain in the dataset.
No retries or exclusions based on correctness or token results.

Serial execution with alternating forward/reverse arm order (`--jobs 1
--alternate-order`) reduces shared-load contention. This is not a fully balanced
Latin square: central versus outer arm positions remain a latency confound.
Use default per-task timeouts, unchanged prompts, visible/hidden tests and graders.
New result roots prevent pooling with previous experiments.

```sh
python -m bench --config benchmark-omp-inline-baseline-codex-pi.toml --results results/omp-inline-codex-pi-preflight run --harness omp-inline omp-baseline codex pi --task bugfix-duration --trials 1 --jobs 1
python -m bench --config benchmark-omp-inline-baseline-codex-pi.toml --results results/omp-inline-codex-pi run --harness omp-inline omp-baseline codex pi --trials 3 --jobs 1 --alternate-order
python -m bench --results results/omp-inline-codex-pi report
```

For a new throughput rerun, use a fresh results directory and one consistent
four-job schedule throughout (do not use `--alternate-order` with parallel jobs):

```sh
python -m bench --config benchmark-omp-inline-baseline-codex-pi.toml --results results/omp-inline-codex-pi-rerun run --harness omp-inline omp-baseline codex pi --trials 3 --jobs 4
python -m bench --results results/omp-inline-codex-pi-rerun report
```

This rerun uses the same model/task grid but a different execution schedule from
the original amended study. Its latency must not be pooled with the original.


### User-approved execution amendment

After 30 completed serial rows, the user requested faster parallel completion.
The serial process was stopped and its completed rows retained unchanged.
`results/omp-inline-codex-pi/continuation-plan.json` freezes those run IDs and the
42 remaining exact cells. Four concurrent workers, one per arm, complete only
missing cells into separate `parallel/<arm>/` roots; the parent merges their rows.
An interrupted attempt is not a completed cell and is retained as an artifact.
No completed cell is retried or excluded based on its result.

Correctness/token reports cover the full grid and label the execution amendment.
Latency is reported separately by execution phase and task, never as a pooled
serial/parallel speed ranking. The generic `bench report` command above would
pool latency; use the phase-aware `analysis/REPORT.md` for this amended study.


## Hypotheses and analysis

Primary: omp-inline is correctness-noninferior to omp-baseline with lower token
usage. Secondary: compare Codex and Pi against omp-baseline using the same existing
comparison algorithm. No invented four-way score or post-hoc best baseline.
Report all four arms' overall/per-task pass rates and all three baseline comparisons.
Use existing 10% margin and minimum three trials per task. Treat secondary comparisons
as descriptive; no multiple-comparison-adjusted significance claim.

Report visible/hidden failures, regressions, tampering, timeouts, total/input/output/
cached tokens, wall time, requests/tool calls and unknown metric coverage.
Provider input totals include cache hits; the session collector normalizes input
to uncached input. Existing reports add uncached input, cache read/write and output
once to calculate total tokens.
Codex cost/model time and edit/verification signals may remain unknown. Zero is not
substituted for missing metrics. Native provider request accounting is not assumed
to be comparable. Correctness at ceiling cannot establish superiority.

## Acceptance and outputs

Exactly 72 unique `(arm, task, trial)` rows, no missing/duplicate cells; all rows
have captured versions, isolated state, expected model and attributable sessions.
Audit ancestor context and metric errors before interpreting outcomes.
Produce an overall report and three pairwise markdown/chart bundles under
`results/omp-inline-codex-pi/analysis/`. Preserve failed rows and their evidence.
The original run protocol did not include publication. The user subsequently
authorized committing/pushing the reproducible setup and a curated publication:
`published/omp-inline-baseline-codex-pi-2026-09/REPORT.md`, `combined.svg`, and
`runs.csv`. Raw sessions, credentials, account IDs and local paths remain excluded.
