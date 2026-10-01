# Challenge-tier calibration — 2026-10-01

## Decision

**Routing and journal failed the discrimination screen: all 12 model runs passed.** They are complete, validated fixtures, but this calibration does not qualify them as harder correctness tests. Preserve their results; do not change their grading retrospectively or extend the trial count until a preferred verdict appears. Recovery and safety remain held out from model runs. Do not launch the proposed confirmation grid on the assumption that development difficulty was established.

The comparison verdict is **inconclusive**. Correctness and measured safety are the same; total tokens are lower for inline, but uncertainty does not rule out a >10% loss in uncached tokens or wall time. No harness-default change is supported.

## Frozen run

[Protocol](PLAN.md) declared two development tasks × two arms × three trials = 12 runs, four workers. Actual runner: `omp/18.4.8`, Claude Opus 5.5 high, both arms isolated; reported model names include canonical and provider spellings of the same model. Aggregate estimated token cost: **$2.7095456**, not an actual subscription charge. Elapsed runner command: **223.77 seconds**. Parallel timing includes shared provider load/cache and concurrent operator activity; it is not isolated latency.

Local raw evidence: `results/challenge-calibration-2026-10-01/runs.jsonl`, `manifest.json`, and per-run artifacts. This ignored result directory is not a published portable transcript bundle. Checked-in [CLI report](REPORT.md) and [comparison JSON](COMPARISON.json) preserve measured scorecards, intervals and per-task effects.

| Task | Baseline passed | Inline passed | Total tokens/correct ratio | Uncached tokens/correct ratio | Median wall ratio | P90 wall ratio |
|---|---:|---:|---:|---:|---:|---:|
| challenge-routing | 3/3 | 3/3 | 0.691 | 1.081 | 1.226 | 1.000 |
| challenge-journal | 3/3 | 3/3 | 0.862 | 1.160 | 1.086 | 1.050 |

Ratios are inline/baseline point estimates, descriptive only. Pass-rate differences are zero. Both arms passed all 21 hidden routing tests and all 22 hidden journal tests in each run; no infrastructure failures, unknown classifications, regressions or timeouts were recorded.

Task hashes at calibration:

- routing: `8eee47a9f386e722e0b93ab425622600bc1f217d70a2566af215c52b822206d4`
- journal: `260621cfdaec188b7ac49154d73606eb1258350a6c6f78656181b87fb51324bb`

## Local verification

- `python -m unittest discover -s tests`: **173 tests passed**. Includes the complete changed CLI/report modules and existing export consumers.
- `python -m bench.validate_tasks`: **all 14 fixtures validated**. Every visible starting repo and hidden starting repo failed, every reference solution passed. Recovery/safety initially lacked a visible failing symptom; one observable regression was added to each before successful validation. No checks were weakened.
- Actual default reference CLI grid: **24/24 passed**, 12 tasks, one trial per reference arm. Neither held-out task appeared in the default run manifest/index.
- Actual explicit held-out reference grid: **4/4 passed**, two tasks, one trial per reference arm. This uses reference solutions, not models, and does not consume the experimental hold-out.
- Actual comparison CLI exercised JSON, text and markdown: all exposed classification counts and 12 task-local effects; missing reference model tokens stayed unknown.
- Actual missing-executable smoke through `run` and `compare`: three failed launch attempts classified as infrastructure and retained. Correctness deterioration still produced `worse`, with contamination named. Throwaway fixtures/config/result files were removed automatically.
- Trial-paired bootstrap was not introduced; aggregate resampling remains unchanged. Generic failed automatic retries are not proof of provider faults.

Historical scans of multiple result directories can include pooled copies of earlier rows; row totals are not necessarily independent trials. Generic assistant errors and nonzero exits alone also cannot prove that old failures were infrastructure failures. The new conservative classification avoids those earlier overclaims.

## Interpretation

These fixtures add coverage and reproducible evaluation structure, not demonstrated harder model discrimination. Any new difficulty iteration needs a new task revision and a separately frozen calibration protocol/result directory; never rewrite this result or tune on held-out transcripts. Keep efficiency controls and challenge calibration separately identified in reports.
