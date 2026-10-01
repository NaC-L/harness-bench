# Three-repeat reliability check

Three fresh grids: four hard tasks × three trials × two arms each. 72 new runs; original 24-run observation excluded. Same pinned commits, isolated state, model/settings and eight concurrent jobs. Each grid ran sequentially; no measured retries.

Percentages below are candidate relative to baseline; negative is lower.

| Grid | Rule verdict | Total tokens/correct | Uncached tokens/correct | Median time | p90 time |
|---|---|---:|---:|---:|---:|
| 1 | equivalent | +4.2% | +10.0% | +2.8% | +5.7% |
| 2 | worse | +16.4% | +32.4% | +1.3% | +4.2% |
| 3 | better | -20.5% | +0.5% | -6.4% | -6.6% |
| pooled | worse | -1.0% | +13.4% | -7.8% | -2.9% |

## Interpretation

The original candidate speed win did not reproduce consistently. Repeat verdicts are equivalent, worse, and better. The pooled rule favors baseline because candidate uncached tokens per correct solution increased 13.4%, exceeding the 10% threshold. Total tokens decreased 1.0%; median time decreased 7.8% and p90 decreased 2.9%, all within the rule margin.

Both arms passed 36/36 full visible and hidden suites, with no regressions, timeouts, prohibited edits, or missing final-edit verification. Exact task/prompt hashes matched across all grids; all changed prompt fingerprints remained unchanged. This supports correctness on these tasks only, not general reliability or complete safety.

Repeated grids share the same account/provider/cache environment; trials are not independent environments. The 10% rule is not a statistical significance test or confidence interval. Four fixed tasks and disabled plan/subagent/orchestrator/web-search/vibe modes limit generalization. Verdict instability is evidence against treating the initial winner as robust.

## Evidence

- [Pooled report and charts](REPORT.md)
- [Repeat 1](../omp-smallest-useful-thing-repeat-1-2026-10/REPORT.md)
- [Repeat 2](../omp-smallest-useful-thing-repeat-2-2026-10/REPORT.md)
- [Repeat 3](../omp-smallest-useful-thing-repeat-3-2026-10/REPORT.md)
- [Exact commits and prompt fingerprints](source-provenance.json)

Pooled trials are 1–9 per task/arm, with `source_repeat` and `source_trial` retained in run records. Manifest retains all three invocations. Raw local sessions remain in their original result roots; published exports omit private transcripts.
