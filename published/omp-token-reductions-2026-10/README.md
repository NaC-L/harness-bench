# OMP token-reduction bundle: inconclusive

[Measured report and charts](REPORT.md) · [Paired readable/raw transcripts](SESSIONS.md) · [Offline explorer](EXPLORER.html) · [Mechanism records](mechanisms.jsonl)

All **100 attempts passed**, 50/50 per arm across 10 tasks × 5 trials. No attempts were retried or excluded; no missing metrics or infrastructure failures were reported. Correctness is at ceiling on this grid, not evidence of general correctness or superiority.

## Measured effects

| Metric | Baseline | Candidate | Qualification |
| --- | ---: | ---: | --- |
| Total tokens/correct | 79,636 | 72,859 | −8.5% point estimate; candidate/baseline 95% CI 0.82–1.02 |
| Uncached tokens/correct | 20,920 | 20,062 | −4.1% point estimate; 95% CI 0.86–1.07 |
| Median wall time | 154.4 s | 149.4 s | Descriptive point estimates |
| P90 wall time | 281.1 s | 296.7 s | Ratio 95% CI 0.91–1.23 |
| Check after final edit | 33/50 | 37/50 | Recorded lifecycle proxy, not general correctness proof |

**The verdict remains inconclusive:** P90's interval cannot exclude more than 10% slowdown. Both token intervals include 1.0 (no improvement), so the point reductions are not demonstrated savings. The report's automatic “safety: better” label reflects the lifecycle proxy above, not independently proven safety.

## Mechanisms and counterexamples

These are descriptive aggregates from [mechanisms.jsonl](mechanisms.jsonl), not causal attribution:

| Observation | Baseline | Candidate |
| --- | ---: | ---: |
| Mean initial input tokens | 4,120.1 | 4,275.1 (+3.8%) |
| Requests | 397 | 405 |
| Follow-up reads | 2 | 8 |
| Edit errors | 2 | 2 |
| Unseen-line errors | 1 | 2 |
| Aggregate edit-output characters | 46,783 | 48,396 |
| Bash null fields | 509 | 0 |
| Bash optional fields | 810 | 32 |
| Shell-file-dump regex candidates | 0 | 0 |

The shell-dump detector is a regex proxy, not proof of absence. Lean schemas reduced emitted Bash fields, but neither initial-input size nor edit-output volume fell in this sample. **Proportional verification was not established:** candidate trial 1 still wrote a 5,471-byte `.csv-smoke.cjs`, and wrote a 5,180-byte `.diff-smoke.cjs`, then rewrote it to 1,239 bytes after a failure. Inspect [CSV trial 1](runs/omp-token-candidate/feature-csv-stream/trial-1/session.jsonl) and [diff trial 1](runs/omp-token-candidate/hard-line-diff/trial-1/session.jsonl), or their readable links in the paired index.

## Setup and attribution

Both arms used OMP 18.4.5, `openai-codex/gpt-6.1-sol`, high thinking, isolated state, and the same task grid. Baseline source: `a7e593859487c26a6507005503329b8ea00c481a`. The measured candidate bundled inline concise native descriptors explicitly enabled, read-summary minimum 300 lines (baseline 100), the proportional-verification prompt, and lean Bash/edit output. Existing provider `auto` policy stayed unchanged: inline descriptors were not made OpenAI-on by default.

The candidate's 21 frozen source-file hashes match the subsequently published [source commit 94fc3d8](https://github.com/NaC-L/oh-my-pi/commit/94fc3d8b97dc040a1ddfc4018f5598cc5e0c0616). This bundled comparison cannot attribute an effect to any individual change. Execution used four concurrent jobs for this grid, concurrently with the four-worker threshold grid (eight total workers), taking approximately 68 minutes; this is not a serial, alternating-order experiment.

## Inspect all attempts

[SESSIONS.md](SESSIONS.md) pairs the same task/trial across arms. **Readable** links open the existing offline explorer's role/tool timeline at that run; **raw** links retain the sanitized native `session.jsonl`. Each run also retains `stdout.jsonl`, stderr, patch, and checks under `runs/<arm>/<task>/trial-N`. Open [EXPLORER.html](EXPLORER.html) locally to filter and inspect all 100 runs. [REPORT.md](REPORT.md) embeds all three SVG charts and the comparison method; [runs.jsonl](runs.jsonl) and [manifest.json](manifest.json) retain portable metrics and setup. Local benchmark, home and temporary-directory roots are sanitized; original raw results remain unchanged.
