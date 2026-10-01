# Pi versus OMP: findings and optimization direction

## Goal

Optimize the tool across three jointly evaluated dimensions, with no priority order:

1. **Correctness:** successful solutions, hidden-test coverage, regressions, and reliable completion.
2. **Token usage:** total and uncached tokens per correct solution, including failed attempts, retries, and auxiliary model calls.
3. **Time and safety:** completion time, hangs, recovery, prohibited edits, and preservation of verification and approval safeguards.

Lower token usage or shorter runtime alone is not a successful optimization. Additional work is not automatically beneficial either: its correctness or safety value must be demonstrated.

## Experiment and evidence

GPT-6.1 Sol at high thinking; three tasks, three trials per task, nine runs per harness. Both arms used read, bash, edit, and write tools, with extensions disabled. OMP model switching and secondary judging were disabled for this comparison. Recorded sessions confirmed Sol-only execution and no secondary model calls.

- [Comparison summary](published/pi-vs-omp-sol-2026-09/evidence/comparison-summary.json)
- [Detailed efficiency analysis](published/pi-vs-omp-sol-2026-09/evidence/efficiency-analysis.json)
- [Run index and artifact references](published/pi-vs-omp-sol-2026-09/runs.jsonl)
- [Sol comparison configuration](benchmark-pi-omp-sol.toml)
- Run-local OMP configuration: `.tools/sol-comparison.yml` (local ignored artifact; disables unexpected-stop detection and advisor for these measurements).

Identical task and prompt hashes, unique session sources, token-total accounting, and identical reported unit prices were checked. Costs are token-based estimates, not actual subscription charges.

| Measurement | Pi | OMP |
| --- | ---: | ---: |
| Passed trials | 9/9 | 9/9 |
| Total input tokens, including cached input | 119,278 | 282,325 |
| Uncached input tokens | 59,630 | 116,693 |
| Output tokens | 9,157 | 12,375 |
| Cached share of input tokens | 50.0% | 58.7% |
| Median first-request input tokens | 1,423 | 4,034 |
| Model-issued tool calls | 61 | 79 |
| Assistant usage messages containing multiple tool calls | 8 | 23 |
| Median end-to-end runtime | 74.8 s | 84.9 s |
| Estimated total cost | $0.2168 | $0.3737 |

## What the measurements establish

**Pi achieved the same measured correctness with fewer tokens on these tasks. It did not demonstrate better correctness.** Its lower input/output footprint and observed runtime make it a useful reference for investigating OMP overhead.

OMP's median initial input was approximately 2.8 times Pi's. This is a candidate overhead lever, not proof of redundant content: first-request input includes instructions, tool schemas, task content, and other harness context. Exact attribution requires a separate inspection or ablation.

OMP batched multiple tool calls more often and achieved a higher cached-input share. These strengths did not offset its larger input footprint in this sample. Batching counts are not independent measurements of HTTP requests, and batchable work depends on task dependencies.

OMP also reproduced the duration bug before fixing it in all three trials; Pi did not. That is evidence of additional verification behavior, not evidence that the final solutions were more reliable. Fewer calls should not be rewarded if they remove valuable verification.

Both harnesses made seven failing Git-status probes in non-Git fixture directories. These are avoidable probes, but failed baseline tests are expected diagnostic work and must not be counted as tool misuse.

## What the measurements do not establish

- General superiority of either harness: the sample contains only three small tasks and three trials each.
- Whether OMP's extra verification improves correctness or safety on harder tasks.
- Cache-prefix stability, cache-key quality, or warm-cache readiness. Observed cache-hit share alone cannot establish these.
- Comparable model-only latency: Pi sessions lack the duration/TTFT telemetry available in OMP sessions.
- Long-context reliability, compaction quality, recovery from failures, or approval-boundary safety.
- A pure harness-only effect: native prompts, tool implementations, provider labels, authentication paths, and transport configuration differ.
- That output-token differences represent only visible verbosity; provider generation accounting may include reasoning.

All runs passed under the benchmark's checks, but passing checks are not a comprehensive safety assessment. The stripped-down OMP configuration is a measurement arm, not a recommendation for normal use; disabling recovery features can itself change reliability.

## Optimization decision

The current analysis is **diagnostic evidence**, not justification for changing OMP defaults. The defensible conclusion is that OMP's larger prompt/tool footprint deserves investigation while preserving useful verification and safety behavior.

Pi is a reference, not the acceptance baseline. The next optimization experiment should compare **OMP baseline against one targeted OMP change**.

## Next experiment

1. Attribute OMP initial overhead to instructions, tool schemas, and other context. Identify demonstrably redundant material rather than removing safeguards or verification requirements.
2. Make one bounded, run-local change. Preserve the baseline configuration and record the exact candidate difference.
3. Use identical model, thinking, account/transport, tasks, tool availability, and recovery/approval settings between OMP arms. Alternate or randomize run order; distinguish cold and warm cache conditions.
4. Include harder tasks with regression traps, dependent and parallel tool work, larger outputs, and bounded long-context/recovery scenarios.
5. Evaluate correctness, tokens, and time/safety together. Retain a change only when its efficiency benefit is reproducible and correctness/safety do not regress. Report tradeoffs explicitly rather than selecting a winner by one metric.

### Measurements to retain

- Correctness: visible/hidden checks, completion, regressions, prohibited-file edits, and failure reasons.
- Tokens: uncached/cached input, output, auxiliary calls, and tokens per correct solution including retries. Report failures separately so efficient-looking failures are not rewarded.
- Time/safety: median and tail runtime, timeout/hang rates, recovery behavior, verification retained, and approval-boundary violations.
- Cache: per-request cached tokens and input totals, first-request hits, repeated-prefix stability, and explicit cold/warm conditions.
- Tools: semantic work completed, unnecessary probes, repeated reads, returned text volume, batching opportunities, and pre-/post-fix verification. Do not equate fewer calls with better work.

### Automated scoring

`python -m bench --results <dir> compare --baseline <arm> --candidate <arm> [--margin 0.10] [--min-trials 3] [--json]` turns these measurements into per-arm scorecards and a rule-based verdict (`better | worse | tradeoff | equivalent | inconclusive`):

- Correctness (pass rate, unfinished runs, hidden-test regressions) and safety (timeouts, tampering, post-edit verification rate) are non-inferiority gates. They use exact comparison, so one extra failure makes the candidate `worse`.
- Tokens (total and uncached tokens per correct solution, with failed attempts counted in the numerator) and time (median and p90 wall time) are candidate/baseline ratios with a 95% percentile bootstrap interval. Each resample redraws runs within every (arm, task) cell, so the task mix is fixed; the seed is fixed, so re-scoring is reproducible. A dimension is `worse` if any interval lies wholly above 1 + margin, `uncertain` if any interval still reaches above it, `better` if any interval lies wholly below 1 − margin, `same` if every interval sits inside the band, and otherwise `non-inferior`.
- The verdict is `inconclusive` if the task sets or task inputs differ between arms, if any task has fewer than `--min-trials` runs per arm, if token or runtime data is unknown, if an efficiency dimension is `uncertain`, or if it is only `non-inferior` with no other gain. Unknown data is never treated as zero. Reasons name the interval that needs more trials.
- Why intervals: run-to-run variation within one task and arm is 14–30% for uncached tokens and 9–16% for wall time on the hard tier (pooled smallest-useful-thing runs, 9 per cell), larger than the margin. Point estimates against a fixed margin gave `better`, `equivalent`, `worse`, `better` for four repeats of one unchanged comparison. Re-scored, those repeats are `inconclusive` (one has tokens `worse`, but time is uncertain). The inline-descriptor results remain `better`.
- Pre-fix reproduction is reported but does not affect the verdict.
- `classification_counts` separates `success`, `solution_failure`, `infrastructure_failure` and `unknown` in every arm scorecard. Explicit runner/provider failure evidence identifies infrastructure failures; a nonzero agent exit or generic final-assistant error alone does not prove an infrastructure fault. Timeouts, tampering and regressions retain safety/correctness significance. All attempts remain in denominators, token numerators and time measurements. Infrastructure contamination blocks positive/equivalent and efficiency-only verdicts; a measured correctness/safety loss still yields `worse`.
- `per_task` contains both arm scorecards, candidate-minus-baseline `pass_rate_difference`, and candidate/baseline point `ratios` for total/uncached tokens per correct solution and median/p90 wall time. The text and markdown reports show these effects beside the aggregate verdict; they do not assign per-task winners or pretend the sample supports per-task statistical significance.
- The [challenge-tier protocol](experiments/challenge-tier/PLAN.md) keeps controls, development calibration and held-out confirmation separate. Calibration uses fixed trial counts and reports floor/ceiling outcomes rather than changing checks to manufacture discrimination.

Each run records `visible_passed`, visible and hidden test counts, `baseline_passing_tests`, `regressions`, `agent_completion` and `agent_retries`. `agent_completion` and `agent_retries` are filled for Pi runs and for OMP `--mode json` runs. The run metrics also include auxiliary model usage and verification signals. Rows recorded before these fields existed have regression and verification data marked unknown.

No production/default configuration changes have been justified by this analysis. Any candidate should remain reversible through removal of its run-local override.

## Controlled OMP pilot: tool-description placement

A six-run screening pilot compared OMP 18.4.4 with `inlineToolDescriptors: "off"` (native-schema baseline) against `"on"` (inline candidate). This existing setting relocates tool descriptions into the system prompt and strips them from native tool schemas; it does not remove tool availability or replace the assistant's instructions.

Both arms used GPT-6.1 Sol high, the same provider/auth configuration, tools, task prompts, and inherited recovery/approval settings. Each of the three fixtures ran once per arm, serially, with alternating pair order. Unlike the earlier Pi comparison, this pilot retained unexpected-stop detection: one same-model auxiliary check ran per trial, included in the totals. Context hashes remained unchanged throughout.

| Measurement | Native baseline | Inline candidate |
| --- | ---: | ---: |
| Passed trials | 3/3 | 3/3 |
| Total input tokens, including cached input | 83,440 | 73,682 |
| Uncached input tokens | 32,624 | 26,962 |
| Output tokens | 3,375 | 4,118 |
| Median first-request input tokens | 4,035 | 2,716 |
| Median end-to-end runtime | 65.9 s | 94.1 s |
| Estimated total cost | $0.1041 | $0.0998 |

The inline candidate reduced first-request input by approximately 1,320 tokens on every task. Aggregate input fell 11.7%, output rose 22.0%, and estimated cost fell 4.1%. Its median runtime was 42.8% higher; one trial per task cannot establish a reliable latency effect. Paired runtime changes were -2.7% (duration), +29.0% (limiter), and +43.1% (LRU).

All six runs performed post-edit tests and passed visible/hidden grading, with no observed prohibited-file edits or timeouts. The inline duration run skipped pre-fix reproduction while the baseline performed it; both limiter runs reproduced before editing. Equal passing checks do not establish equivalent debugging reliability or comprehensive safety.

**Decision: retain the native baseline; no default change.** This pilot confirms a smaller initial footprint, not a reproducible joint efficiency win. Cache conditions were naturally observed, not forced cold/warm (all first requests reported zero cached tokens); actual auth-account selection and remote provider load were not independently controlled. Harder/recovery scenarios and repeated trials remain untested.

Reproduce with `python -m bench --config benchmark-omp-descriptors.toml --results results/omp-descriptors-repeat run --harness omp-baseline omp-inline --trials 1 --jobs 1 --alternate-order`, choosing a fresh result directory. [Exact overlays and schedule](published/omp-inline-descriptors-pilot-2026-09/evidence/experiment.json), [audited measurements and verification commands](published/omp-inline-descriptors-pilot-2026-09/evidence/comparison-summary.json), and [run artifacts](published/omp-inline-descriptors-pilot-2026-09/runs.jsonl) preserve the evidence.

## Follow-up: repeated trials and harder tasks

Three new tasks were added: `bugfix-invoice`, `debug-cache-race` and `feature-csv-stream`. Each contains regression traps (tests that already pass on the starting repo). The same two arms then ran 4 trials on all 6 tasks, 12 runs at a time; each trial's baseline and inline runs were submitted together. Verdict: **`better`**. Correctness and safety were the same: 24/24 runs passed, with no regressions, no timeouts and verification in every run. Tokens per correct solution fell 14% total and 13% uncached, and cost fell 10%. p90 wall time fell 11%. The median fell 6%, which is inside the noise margin.

The earlier median slowdown held only on the short tasks. On the long tasks inline was faster, and it used fewer tokens on 5 of 6 tasks; `bugfix-invoice` was the exception, with more tokens and more requests. An earlier 3-trial repeat on the original three tasks alone gave `tradeoff` (tokens −22%, median time +25%, total wall time +7%).

**Limit:** correctness is at ceiling, because every run of both arms passed. These tasks cannot yet show a correctness difference.

## Isolated re-run: removing the operator's personal context

Every OMP run above, including the Pi comparison and the pilot, used the operator's own `~/.omp/agent`. A canary check confirmed the leak. Asked to quote any Turkish phrase in its instructions, a non-isolated run returned one from the operator's global `AGENTS.md`. It also tried to connect to the operator's MCP servers, and its first request carried about 970 more input tokens. It also ran one auxiliary model call per run from the operator's settings. The isolated run saw only the benchmark's canary. Those earlier results therefore measured OMP plus a personal setup; their raw data stays in `results/` and `compare` now flags such runs as `operator state not isolated`.

Both arms now run against a fresh copy of `experiments/omp-isolated/agent` (OMP defaults, memory off). They authenticate with a token computed per run, which is never stored. The same 6 tasks × 4 trials were re-run in parallel. Verdict: **`better`** ([report](published/omp-inline-descriptors-isolated-2026-09/REPORT.md)):

| | Native schemas | Inline descriptions |
|---|---:|---:|
| Passed | 24/24 | 24/24 |
| Tokens per correct, total / uncached | 49,057 / 19,148 | 32,090 / 16,016 (−35% / −16%) |
| Wall time, median / p90 | 179.5 s / 290.8 s | 148.8 s / 239.1 s (−17% / −18%) |
| Cost (24 runs) | $1.59 | $1.34 (−16%) |
| Verified after final edit | 23/24 | 23/23 known |

Without the personal context, inline's advantage is larger on both tokens and time. The safety `better` rests on a single baseline run that edited after its last test. One inline run wrote files only through `bash`, which the verification signal cannot see, so its verification is unknown. Correctness is still at ceiling. The data supports inline on efficiency with no measured cost, but it cannot show a correctness effect.
