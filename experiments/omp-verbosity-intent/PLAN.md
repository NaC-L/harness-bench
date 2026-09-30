# OMP response verbosity and tool-intent tracing

Protocol created before measured runs, 2026-09-30.
Config: `benchmark-omp-verbosity-intent.toml`.

## Arms and hypothesis

| Arm | `textVerbosity` | `tools.intentTracing` |
| --- | --- | --- |
| `omp-baseline` | medium | true |
| `omp-low-verbosity` | low | true |
| `omp-no-intent` | medium | false |
| `omp-low-no-intent` | low | false |

Hypothesis: lower response verbosity and/or removing requested tool-intent descriptions reduces output tokens and wall time without lowering task correctness. These are hypotheses, not established results. Low verbosity controls provider response verbosity, not reasoning effort. Disabling intent tracing changes the tool-call intent instruction, not tool availability.

The 2x2 design separates individual changes from their combination. All arms explicitly keep `inlineToolDescriptors: "off"`, use `openai-codex/gpt-6.1-sol`, high thinking, read/bash/edit/write, and identical CLI flags except their overlay paths. The baseline pins the two installed defaults rather than inheriting the operator's low-verbosity preference. Fresh copies of `experiments/omp-isolated/agent` disable memory and isolate operator state. Authentication uses the existing per-run token command; credentials are not saved in the config.

## Grid and execution

Separate four-run `bugfix-duration` preflight; then four hard tasks x four arms x three trials = 48 measured runs. No pooling with earlier benchmark results or preflight. Use fresh result directories if rerunning. Serial forward/reverse arm order reduces concurrent load, but does not balance central versus outer positions; latency remains sensitive to provider load and cache state.

Both commands below consume model usage. Configuration creation and startup verification do not start these runs.

```sh
python -m bench --config benchmark-omp-verbosity-intent.toml --results results/omp-verbosity-intent-preflight run --harness omp-baseline omp-low-verbosity omp-no-intent omp-low-no-intent --task bugfix-duration --trials 1 --jobs 1
python -m bench --config benchmark-omp-verbosity-intent.toml --results results/omp-verbosity-intent run --harness omp-baseline omp-low-verbosity omp-no-intent omp-low-no-intent --task hard-dep-resolver hard-expr-eval hard-line-diff hard-segment-tree --trials 3 --jobs 1 --alternate-order
```

Before the measured grid, require each preflight arm to finish, pass hidden grading and record attributable token metrics. Diagnose infrastructure failures rather than retrying successful cells. Keep measured failures/timeouts; no exclusions or retries based on correctness or efficiency. Preserve task prompts, checks and default 30-minute hard-task timeouts.

### User-approved parallel execution

The user requested parallel execution before any measured runs. Execute four concurrent workers, one per arm, each with `--jobs 1`; omit `--alternate-order`. Each worker runs one preflight into `results/omp-verbosity-intent-parallel-preflight/<arm>`. Start the measured workers only after all four preflights pass with token metrics. Each measured worker runs the four hard task IDs above with `--trials 3` into `results/omp-verbosity-intent-parallel/<arm>`.

Retain each worker's manifest and raw artifacts. Merge the 48 measured rows into `results/omp-verbosity-intent-parallel/runs.jsonl` after checking unique cells, and use that parent result root for all three comparisons. Preflight rows are excluded. Latency measures concurrent shared-account/provider load, not serial isolated latency; do not pool with serial experiments. The commands above remain the serial alternative, not the schedule used for this execution.

### Future eight-worker workflow

This is for a new experiment, not a change to the active four-worker grid. Use one runner with `--jobs 8`, a global cap of eight concurrent cells; no fixed two-per-arm quota is enforced. The runner handles workspace isolation, manifest capture and index writes. Keep the same schedule across screening and confirmation, with fresh result roots.

After a separate passing preflight for any new settings, screen all four arms on all four hard tasks once (16 runs). Report all screening results as exploratory, not a winner. Freeze candidates and acceptance criteria before confirmation; these commands retain all four arms for three fresh trials (48 runs). Do not pool screening with confirmation or with this experiment's original four-worker results.

```sh
python -m bench --config benchmark-omp-verbosity-intent.toml --results results/omp-verbosity-intent-next-preflight run --harness omp-baseline omp-low-verbosity omp-no-intent omp-low-no-intent --task bugfix-duration --trials 1 --jobs 8
python -m bench --config benchmark-omp-verbosity-intent.toml --results results/omp-verbosity-intent-next-screen run --harness omp-baseline omp-low-verbosity omp-no-intent omp-low-no-intent --task hard-dep-resolver hard-expr-eval hard-line-diff hard-segment-tree --trials 1 --jobs 8
python -m bench --results results/omp-verbosity-intent-next-screen report
python -m bench --config benchmark-omp-verbosity-intent.toml --results results/omp-verbosity-intent-next-confirm run --harness omp-baseline omp-low-verbosity omp-no-intent omp-low-no-intent --task hard-dep-resolver hard-expr-eval hard-line-diff hard-segment-tree --trials 3 --jobs 8
python -m bench --results results/omp-verbosity-intent-next-confirm compare --baseline omp-baseline --candidate omp-low-verbosity
python -m bench --results results/omp-verbosity-intent-next-confirm compare --baseline omp-baseline --candidate omp-no-intent
python -m bench --results results/omp-verbosity-intent-next-confirm compare --baseline omp-baseline --candidate omp-low-no-intent
```

These commands consume model usage and are prepared, not automatically launched. For other settings, substitute the frozen config and arm IDs and rename every result root. Shared-account throttling and cache contention can limit speedup; parallel timing is a loaded-throughput observation, not proof of isolated model latency. Three-trial confirmation remains the minimum used by the existing comparison rule.


## Analysis and acceptance

Report all three comparisons against the same baseline, with the existing 10% noise margin and minimum three trials. Do not select only the best candidate or claim multiple-comparison-adjusted statistical significance. The combined arm is a package comparison; existing pairwise verdicts alone do not establish a factorial interaction.

```sh
python -m bench --results results/omp-verbosity-intent report
python -m bench --results results/omp-verbosity-intent compare --baseline omp-baseline --candidate omp-low-verbosity
python -m bench --results results/omp-verbosity-intent compare --baseline omp-baseline --candidate omp-no-intent
python -m bench --results results/omp-verbosity-intent compare --baseline omp-baseline --candidate omp-low-no-intent
```

Acceptance: exactly 48 unique `(arm, task, trial)` measured rows; versions, overlays and task hashes recorded in the manifest; all three comparisons reported. Include per-task correctness, regressions, timeouts, total/uncached/output tokens, cache coverage and wall time. Unknown metrics remain unknown. If every arm passes every task, efficiency may be compared but correctness superiority is not established.

## Local verification

On installed OMP 18.4.4, the benchmark CLI loaded all four arms and all ten available tasks. Each isolated arm started in RPC mode with its actual overlay and resolved the requested model/high thinking without submitting an inference prompt. The installed settings parser accepted all four intended value combinations in disposable state copies. Standalone `omp config` and `omp read` commands ignore the main CLI's `--config` overlay, so they were not used as evidence of overlay activation. Paid task behavior and provider-level verbosity effects still require the preflight above. No measured results exist from this setup verification.

## Completed parallel run

All four preflights passed visible/hidden grading with token coverage. The original four-worker measured schedule completed 48/48 distinct cells, all passing, without measured retries, timeouts, regressions or tampering. The merged manifest retains four worker invocations. All three existing-rule comparisons favor baseline; correctness remains at ceiling. Full local evidence: `results/omp-verbosity-intent-parallel/analysis/REPORT.md`, its three pairwise reports and `comparisons.json`.

Future eight-worker scheduling was exercised separately with two reference arms, two tasks and two trials: 8/8 distinct cells passed, manifest `jobs=8`, no model calls. This proves the existing runner accepts and executes that schedule, not real-provider speedup.
