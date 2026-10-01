# Smallest useful thing: branch versus parent

Baseline: `79808c3bf` (v18.4.5), checkout `omp-baseline`.
Candidate: `27cdf191b`, branch `prompts/smallest-useful-thing`, checkout `oh-my-pi`.
Both source CLIs report 18.4.5; manifest versions record git describe.

Hypothesis: scope-bounded workflow instructions reduce unnecessary work and tokens without lowering correctness. Not an established result.

Both arms run Bun source CLIs, isolated per-run state, GPT-6.1 Sol/high, medium verbosity, intent tracing on, native tool descriptors, read/bash/edit/write. Same task inputs and overlay. No personal instructions, extensions, skills, rules, or prewalk. Only checkout differs. This measures the normal coding workflow, not plan, orchestrator, web-search, agent-creation, vibe, or subagent modes also changed by the branch.

Separate bugfix-duration preflight: one run per arm, both must pass with token metrics. Confirmation: four hard tasks × two arms × three trials = 24 measured runs, jobs=8. No screening or pooling with earlier experiments. Retain all measured failures/timeouts; no selective retries. Parallel time reflects shared provider load/cache contention, not isolated latency. Worktree files are unchanged by this experiment.

Commands:

```sh
python -m bench --config benchmark-omp-smallest-useful-thing.toml --results results/omp-smallest-useful-thing-preflight run --harness omp-baseline omp-smallest --task bugfix-duration --trials 1 --jobs 2
python -m bench --config benchmark-omp-smallest-useful-thing.toml --results results/omp-smallest-useful-thing run --harness omp-baseline omp-smallest --task hard-dep-resolver hard-expr-eval hard-line-diff hard-segment-tree --trials 3 --jobs 8
python -m bench --results results/omp-smallest-useful-thing compare --baseline omp-baseline --candidate omp-smallest
python -m bench --results results/omp-smallest-useful-thing export --baseline omp-baseline --candidate omp-smallest --out published/omp-smallest-useful-thing-2026-10
```

Use existing exact correctness/safety gates, 10% efficiency margin and three-trial minimum. Report correctness, total/uncached/output tokens, median/p90 runtime, regressions, verification and timeouts. All-pass results cannot establish correctness superiority. Unknown metrics remain unknown.

## Observed result

Both preflights passed with attributable token usage. All 24 unique measured cells passed full visible and hidden grading, with matching task/prompt hashes across arms, isolated state, no ancestor context, no timeouts, no regressions, and post-edit verification in every run. All 14 source prompt fingerprints remained unchanged through execution.

Existing-rule verdict: **better**, driven by candidate p90 wall time being 11.0% lower (269.3 versus 302.5 seconds). Median time was 2.8% lower (195.7 versus 201.3 seconds). Total tokens per correct solution were 0.2% higher; uncached tokens were 5.7% higher, both within the 10% band. This does not demonstrate the hypothesized token savings. Correctness remains at ceiling; parallel timing is descriptive, not a general speed guarantee.

Portable report and charts: `published/omp-smallest-useful-thing-2026-10/REPORT.md`. Local raw sessions and preflight evidence remain under the separate `results/` roots. `source-provenance.json` records both commits and all changed prompt hashes. Modes disabled by this protocol were not exercised.

## Three fresh repeats

User requested three additional repetitions after the first result. Run three sequential 24-cell grids, each retaining jobs=8 and the original configuration/task list. Keep each grid separate in `results/omp-smallest-useful-thing-repeat-{1,2,3}`; do not run grids concurrently or retry measured cells. Commits and all changed prompt fingerprints matched the first experiment before starting.

Report each repeat under the unchanged comparison rule. Pool only the three new grids (72 runs, nine trials per task per arm); preserve source repeat/trial identifiers and remap pooled trials to 1–9. Keep the original 24-run observation separate because it motivated repetition. These are repeated measurements, not independent provider/cache environments. No formal significance claim; agreement across repeats is evidence of stability only on these four tasks and this configuration.

### Completed repeats

All three fresh grids completed: 72 unique cells, all full visible/hidden suites passing, 36/36 per arm. Matched task/prompt hashes, isolated state, unchanged source fingerprints; no measured retries, regressions, timeouts, prohibited edits, or missing final-edit verification.

Repeat verdicts: **equivalent**, **worse**, **better**. Pooled verdict: **worse**, driven by candidate uncached tokens per correct solution increasing 13.4%. Total tokens decreased 1.0%, median time decreased 7.8%, and p90 decreased 2.9%, all within the rule's 10% band. The initial speed win was not stable across repeats.

Reliability assessment, separate reports, pooled charts and exact scorecards: `published/omp-smallest-useful-thing-repeats-2026-10/README.md`. Original observation remains separate. No statistical significance or general correctness superiority is claimed.
