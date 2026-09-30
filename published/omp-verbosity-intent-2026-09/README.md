# OMP response verbosity and tool-intent tracing

**The existing comparison rule favors baseline over all three candidates. All 48 measured runs passed.** This experiment found no efficiency benefit strong enough to recommend either setting change; it does not establish a general performance winner.

Four hard tasks × three trials × four arms, using `openai-codex/gpt-6.1-sol`, high thinking, identical tools and isolated state. Run date: 2026-09-30. Four concurrent workers, one per arm; measured grid elapsed approximately 52.5 minutes. A separate 4/4 passing preflight is excluded.

## Results

| Arm | Verbosity | Intent tracing | Pass | Total tokens / correct | Uncached tokens / correct | Median / p90 seconds |
| --- | --- | --- | --- | ---: | ---: | ---: |
| Baseline | medium | on | 12/12 | 66,037 | 21,994 | 227.5 / 291.7 |
| Low verbosity | low | on | 12/12 | 64,965 | 24,538 | 216.0 / 313.7 |
| No intent | medium | off | 12/12 | 72,427 | 24,747 | 228.5 / 326.1 |
| Both | low | off | 12/12 | 72,217 | 23,108 | 210.4 / 325.8 |

Token figures include all measured attempts divided by correct solutions. Total tokens include uncached input, cache reads/writes and output. Uncached tokens exclude cache reads. Timing is agent-process elapsed time; median and p90 are across each arm's 12 runs, not grading time. Values are rounded; exact values are in the reports and dataset.

### Low verbosity vs baseline

![Low verbosity vs baseline: relative efficiency changes and exact metric values](low-verbosity/charts/summary.svg)

Low verbosity has slightly fewer total tokens, but **11.6% more uncached tokens per correct solution**. Median/p90 timing is within the comparison rule's 10% band. [Full report](low-verbosity/REPORT.md) · [Full-size summary](low-verbosity/charts/summary.svg) · [Tokens by task](low-verbosity/charts/tokens-per-task.svg) · [Time by task](low-verbosity/charts/wall-time-per-task.svg).

### Intent tracing off vs baseline

![Intent tracing off vs baseline: relative efficiency changes and exact metric values](no-intent/charts/summary.svg)

Intent tracing off uses **12.5% more uncached tokens per correct solution** and has **11.8% higher p90 time**. [Full report](no-intent/REPORT.md) · [Full-size summary](no-intent/charts/summary.svg) · [Tokens by task](no-intent/charts/tokens-per-task.svg) · [Time by task](no-intent/charts/wall-time-per-task.svg).

### Both changes vs baseline

![Both setting changes vs baseline: relative efficiency changes and exact metric values](low-no-intent/charts/summary.svg)

Both changes have a lower median time, but **11.7% higher p90 time**; token changes stay within the 10% band. [Full report](low-no-intent/REPORT.md) · [Full-size summary](low-no-intent/charts/summary.svg) · [Tokens by task](low-no-intent/charts/tokens-per-task.svg) · [Time by task](low-no-intent/charts/wall-time-per-task.svg).

Charts use neutral baseline and cyan candidate marks. Summary charts plot relative changes with a ±10% margin band; task charts start at zero, show all individual runs and paired medians. Open the full-size SVG links for readable labels on narrow screens; the table and reports provide text equivalents.

## Interpretation and limits

- The existing rule uses a 10% efficiency margin and at least three trials per task. A candidate can lose on uncached tokens or p90 time despite a lower total-token count or median time.
- All runs passed: correctness remains at ceiling, even on the hard tier. No correctness superiority is established.
- No measured retries, timeouts, regressions or tampering were recorded. These signals are not comprehensive safety proof.
- Same account/provider and concurrent execution leave cache and provider load uncontrolled. Faster arms finish earlier, so concurrency falls near the end; latency is not an isolated comparison.
- Report all three comparisons. No multiple-comparison-adjusted statistical significance is claimed; the combined arm does not by itself prove a factorial interaction.

## Data and reproducibility

- [48 unique measured rows](runs.jsonl) and [sanitized invocation manifest](manifest.json).
- [Experiment configuration](../../benchmark-omp-verbosity-intent.toml) and [protocol](../../experiments/omp-verbosity-intent/PLAN.md).
- Each comparison directory is also a standalone 24-row export with graphs, its own index/manifest and sanitized grading/patch artifacts. Its baseline rows duplicate the other comparisons; **do not concatenate those indexes**. The root index above already deduplicates to 48 rows and resolves artifacts into those directories.

Re-score this portable bundle from the repository root without model calls:

```sh
python -m bench --results published/omp-verbosity-intent-2026-09 compare --baseline omp-baseline --candidate omp-low-verbosity
python -m bench --results published/omp-verbosity-intent-2026-09 compare --baseline omp-baseline --candidate omp-no-intent
python -m bench --results published/omp-verbosity-intent-2026-09 compare --baseline omp-baseline --candidate omp-low-no-intent
```

Raw sessions, stdout/stderr streams and authentication files are not included. Local raw evidence remains under the gitignored `results/omp-verbosity-intent-parallel/<arm>/` directories. Local path roots are replaced in exported artifacts. Disposable benchmark workspaces are not security sandboxes; run only trusted tasks.

## Next benchmarks

The [eight-worker workflow](../../experiments/omp-verbosity-intent/PLAN.md#future-eight-worker-workflow) uses one runner with `--jobs 8`: 16 exploratory screening cells, then a fresh three-trial confirmation grid. Do not pool phases or announce a winner from screening. Eight-worker reference scheduling passed 8/8 cells without model calls; real-provider speedup is not yet measured.
