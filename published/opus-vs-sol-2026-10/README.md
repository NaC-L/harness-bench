# Claude Opus 5.5 vs GPT-6.1 Sol on OMP

**Tradeoff: Opus was faster; Sol was cheaper. Both passed every run.**

10 tasks (six original plus four hard tasks) × 3 trials × 2 models = 60 measured runs. A separate one-task preflight is excluded. Both used OMP 18.4.8, fresh benchmark-owned state, the same tools/prompt/flags, no config overlay, and `--thinking high`. Only model and authentication provider differ. Twelve workers ran concurrently; the measured batch took 851.3 seconds.

| Metric | GPT-6.1 Sol | Claude Opus 5.5 |
| --- | ---: | ---: |
| Passed runs | 30/30 | 30/30 |
| Hidden checks passed across trials | 507 | 507 |
| Median wall time | 155.4s | 57.2s |
| P90 wall time | 270.4s | 203.9s |
| Total tokens per correct solution | 60,650 | 122,504 |
| Uncached tokens per correct solution | 21,550 | 20,786 |
| Estimated API cost, measured runs | $2.4234 | $8.4502 |
| Estimated API cost per correct solution | $0.0808 | $0.2817 |
| Timeouts / tampered runs | 0 / 0 | 0 / 0 |
| Recorded verification after final edit | 30/30 | 30/30 |
| Recorded reproduction before first edit | 21/30 | 1/30 |

![Summary](charts/summary.svg)

## Interpretation and limitations

- Opus's median wall time was 63.2% lower (ratio 0.368; 95% within-task bootstrap CI 0.325–0.391). Its estimated API cost was 3.49× Sol's. These are provider-priced estimates from session usage, not subscription charges or invoices.
- Opus used 2.02× total tokens (95% CI 1.66–2.42). Uncached tokens were similar: ratio 0.965 (CI 0.847–1.091). Total includes cache reads and writes; cache state was not controlled. Different tokenizers mean these are provider-native usage counts, not an equal unit of computation.
- Both models passed all tasks, including the hard tier: this experiment cannot establish a correctness winner or general coding superiority.
- Parallel scheduling and separate providers confound latency with provider load/rate limits. `high` is a named effort setting, not a matched compute budget. This is a model-plus-provider comparison on one harness.
- Recorded reproduction differs sharply (Sol 21 runs, Opus 1). This is the existing session detector's observation, not an independent audit of debugging quality; the scorer does not make reproduction a safety gate.
- The existing interval-based scorer reports **tradeoff**: faster Opus, more total tokens, same observed correctness/safety. Estimated cost is shown separately, not used by that verdict.

## Evidence

- [Full report, per-task results, confidence intervals and provenance](REPORT.md)
- [Native sessions by task/trial/model](SESSIONS.md)
- [Portable run records](runs.jsonl)
- [Invocation manifest](manifest.json)
- [Matched-arm config](../../benchmark-opus-vs-sol.toml)

All 60 native session records are included with local paths sanitized. A credential-pattern scan found no matches; that is not a guarantee against every possible secret format.

## Reproduce

From the repository root, with both providers authenticated in OMP. Task IDs are pinned because the repository's default task selection can grow.

```console
python -m bench --config benchmark-opus-vs-sol.toml --results results/opus-vs-sol-rerun run --harness omp-sol omp-opus --trials 3 --jobs 12 --task bugfix-duration bugfix-invoice debug-cache-race debug-limiter feature-csv-stream feature-lru hard-dep-resolver hard-expr-eval hard-line-diff hard-segment-tree
python -m bench --results results/opus-vs-sol-rerun compare --baseline omp-sol --candidate omp-opus
```

Re-score this bundle without model access:

```console
python -m bench --results published/opus-vs-sol-2026-10 compare --baseline omp-sol --candidate omp-opus
```

For a latency-sensitive rerun, replace `--jobs 12` with `--jobs 1 --alternate-order`; it is a different scheduling protocol, not an exact reproduction of this batch.
