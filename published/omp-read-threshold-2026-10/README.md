# OMP read-fold threshold: 100 vs 300 lines

A complete 100-attempt grid: 10 tasks × 5 trials × 2 arms. Baseline `omp-read-100` and candidate `omp-read-300` both passed **50/50**. All attempts, native transcripts, checks and patches are retained; nothing was retried or selectively excluded.

- [Measured report and charts](REPORT.md)
- [Paired readable and raw transcripts](SESSIONS.md)
- [Offline session explorer](EXPLORER.html): readable role/tool timelines, checks, patches and all three charts; the per-run links in SESSIONS.md select the matching attempt.
- [Portable run records](runs.jsonl), [recorded setup](manifest.json), and [sanitized mechanism evidence](mechanisms.jsonl)

`session.jsonl` links are native raw records; `EXPLORER.html#run=N` links are the existing readable transcript renderer. Files are paired under `runs/<arm>/<task>/trial-N/`. Open EXPLORER.html locally in a browser; it needs no network services.

## What was measured

| Measure | 100-line baseline | 300-line candidate |
| --- | ---: | ---: |
| Passed attempts | 50/50 | 50/50 |
| Verified after final edit (proxy) | 35/50 | 36/50 |
| Total tokens per correct solution | 83,736 | 80,052 |
| Uncached tokens per correct solution | 22,475 | 20,227 |
| Requests | 412 | 418 |
| Follow-up reads | 5 | 5 |
| Folded reads | 1 | 0 |
| Edit errors / unseen-line errors | 0 / 0 | 1 / 1 |
| Median wall time (seconds) | 160.3 | 154.2 |
| P90 wall time (seconds) | 289.9 | 286.0 |

Total tokens/correct decreased **4.4% as a point estimate**; the candidate/baseline 95% bootstrap ratio interval is **0.85–1.08**. Uncached tokens/correct decreased **10.0% as a point estimate**, with interval **0.81–1.00** (rounded). These are not definitive savings. Intervals resample runs within task, with 2,000 bootstrap resamples; the comparator uses a 10% margin and five-trial minimum.

The generated REPORT.md calls the candidate “better” and “safer” because its verification-after-final-edit proxy increased from 35/50 to 36/50. This is **not proven safety or correctness superiority**. Correctness is at ceiling, and a one-run proxy difference does not establish general superiority.

Only one baseline read folded (`hard-dep-resolver`, trial 2), so changed-mechanism coverage is weak. The candidate unseen-line error (`hard-expr-eval`, trial 3) followed a new partial edit snapshot, **not an initial structural fold**. A reread and later edit succeeded, and the attempt passed. [Inspect its readable/raw transcripts](SESSIONS.md).

## Scope and limitations

Installed OMP **18.4.8**, `openai-codex/gpt-6.1-sol`, high reasoning, isolated per-run state. The changed setting was `read.summarize.minTotalLines: 100 → 300`; native inline tool descriptors were **off** in both arms. The recorded commands and configuration hashes are in manifest.json.

This grid ran with **four concurrent jobs**, while the integrated grid also ran with four: **eight total concurrent jobs**, approximately **68 minutes** for both grids. These are parallel-run latency measurements; **never compare their latency with serial data**. No missing metrics, infrastructure failures or retries were observed. The results describe this task set and execution regime, not a universal performance or safety win.

Related publication: [OMP source commit a05f8a3](https://github.com/NaC-L/oh-my-pi/commit/a05f8a3bb405928feff7df20bc923050017fba1f) belongs to the separately measured integrated-change experiment. **This threshold experiment used installed OMP 18.4.8; its measurements are not attributed to that new source commit.**
