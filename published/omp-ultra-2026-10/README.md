# OMP ultra-combined changes on Opus 5.5: no measurable win

[Report](REPORT.md) · [Sessions](SESSIONS.md) · [Offline explorer](EXPLORER.html) · [Serial latency bundle](../omp-ultra-latency-2026-10/REPORT.md) · [Protocol and screens](../../experiments/omp-ultra/PLAN.md)

Baseline: OMP source a7e593859, inline descriptors off, read threshold 100. Candidate: [79c4c1313](https://github.com/NaC-L/oh-my-pi/commit/79c4c1313) = 94fc3d8 bundle (inline descriptors, threshold 300, lean bash/edit payloads, verification wording) + `read` glob support. Claude Opus 5.5 high, isolated state, every attempt kept.

| | Baseline | Ultra |
| --- | ---: | ---: |
| Throughput grid (14 tasks x 5, 12 workers): passed | 64/70 | 64/70 |
| Total tokens/correct | 117,398 | 107,982 (x0.92, CI 0.84-1.01) |
| Uncached tokens/correct | 19,225 | 18,623 (x0.97, CI 0.91-1.03) |
| Edit errors | 4 | 5 (94fc3d8 bundle alone: 25) |
| Serial latency grid (10 tasks x 2): passed | 20/20 | 20/20 |
| Median / p90 wall (serial) | 51.9 / 165.5 s | 57.5 / 128.2 s (x1.11 CI 0.97-1.23 / x0.77 CI 0.74-0.86) |

Verdicts: throughput `inconclusive`, serial `worse` (only from the verification-after-final-edit proxy, 17/20 vs 16/20). Tokens are non-inferior; nothing cleared the 10% margin.

Why: inline descriptors make Opus batch-read sources through bash (`cat src/*.js`), which carries no edit anchors, so first edits failed. `read` now accepts globs, which removes that regression but does not add savings; the source baseline was already read-efficient. `challenge-safety` failed 5/5 in both arms on one hidden test: a task-difficulty signal, not an arm difference.
