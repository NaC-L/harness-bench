# Ultra-combined OMP change set on Opus 5.5

## Why

The [Opus bundle grid](../omp-token-reductions-opus/PLAN.md) (source a05f8a3: inline
descriptors + read threshold 300 + lean bash/edit payloads + verification wording) lost
the -49% inline-only Opus token win. In 49/50 candidate runs Opus dumped sources with
bash `cat`, so first edits lacked snapshot tags and were rejected (edit errors 2 -> 25).

Leading hypothesis (H1): a05f8a3 ships one-line native tool summaries (bash: "Run
commands in a persistent shell.") when the catalog is inlined; before, native
descriptions were empty. Alternatives: H2 the source build / pinned template itself
(not the bundle) causes it; H3 another bundle change (bash `strict=false`, lean edit
payload, threshold, verification wording).

## Arms (benchmark-omp-ultra.toml)

All: Opus 5.5 high, isolated state, pinned per-arm system-prompt template, tools
read/bash/edit/write, AST edit off, no prewalk/extensions/skills/rules.

| Arm | Checkout | Overlay |
| --- | --- | --- |
| `omp-base` | `../omp-token-baseline` @ 27cdf191b | inline off, threshold 100 |
| `omp-base-inline` | `../omp-token-baseline` @ 27cdf191b | inline on, threshold 100 |
| `omp-bundle` | `../oh-my-pi` @ a05f8a3bb | inline on, threshold 300 |
| `omp-ultra` | `../omp-ultra` (branch `perf/ultra-combined`) | inline on, threshold 300 |

## Phase 1: screen (exploratory, never pooled)

10 original tasks x 1 trial x 4 arms, 12 workers. `omp-ultra` = a05f8a3 with empty
native descriptions when inlined (commit 9af2757b3). Discriminating signal is the
bash file-dump rate (runs with any dump) and edit errors, from
`experiments/omp-read-threshold/analyze.py`:

- `omp-base-inline` dumps -> H2 (build/template), not the bundle.
- `omp-bundle` dumps and `omp-ultra` does not -> H1 confirmed; fix = no wire summaries.
- both bundle arms dump -> H3; bisect the remaining bundle changes.

## Phase 2: ultra-combined vs baseline (confirmation)

`omp-ultra` = every change not measured harmful: inline descriptors, root-cause fix
from phase 1, threshold 300, lean bash/edit payloads, proportional-verification
wording. Excluded: low verbosity and intent tracing off (baseline favoured in all
three comparisons).

- Throughput grid: `omp-base` vs `omp-ultra`, 10 original tasks + 4 never-run hard
  tasks (`challenge-recovery`, `challenge-safety`, `tb-wal-recovery`,
  `tb-mvcc-compaction`) x 5 trials, 12 workers. Hard tasks are used for confirmation
  only; nothing is tuned on them.
- Latency grid (separate, after): `--alternate-order --jobs 1`, 10 original tasks x 2
  trials. Only this grid supports latency claims.
- Rule: `compare --margin 0.1 --min-trials 5` (latency grid: `--min-trials 2`). Keep
  every attempt; no retries or mid-grid edits.

Launch detached: `experiments/omp-ultra/launch.ps1` (tool-managed jobs get killed).

## Results

### Phase 1 screen (2026-10-02)

`results/omp-ultra-screen` (base, base-inline, bundle; 12 workers) and
`results/omp-ultra-screen-ultra` (the no-wire-summary arm, rerun alone after its first
launch failed 10/10 on infrastructure: the fresh worktree lacked the prebuilt
`pi_natives` binary; that failed batch is kept in `omp-ultra-screen`). The screen
variant commit is tagged `screen/no-wire-summaries` (9af2757b3). All 40 completed
attempts passed.

| Arm | Runs with bash dump | Edit errors (runs) | Bare reads | Total tokens | Uncached |
| --- | ---: | ---: | ---: | ---: | ---: |
| `omp-base` (inline off) | 2/10 | 0 (0) | 51 | 1,080,282 | 178,328 |
| `omp-base-inline` | 10/10 | 4 (4) | 11 | 1,026,467 | 182,029 |
| `omp-bundle` | 10/10 | 4 (4) | 10 | 854,791 | 176,621 |
| screen: bundle without wire summaries | 9/10 | 4 (2) | 12 | 1,096,587 | 232,197 |

**H1 is falsified**: dropping the wire summaries does not stop the dumps, and inline
descriptors alone on the unchanged baseline source dump 10/10. Installed builds show
the same habit in *both* arms (`results/omp-descriptors-opus`: 24/24 and 24/24;
`results/opus-vs-sol`: Opus 29/30, Sol 1/30), so the bash dump is Opus's default on
OMP and the inline-off source build is the outlier. The -49% inline win was measured
with dumps in both arms.

Dumped commands batch orientation into one call (`ls -R src test; cat package.json;
cat src/*.js; cat test/*`). `read` already fans out `;`-separated lists with a
snapshot header per file, but this was undocumented, and globs (`src/*.js`) failed
with "not found". Revised root cause: `read` cannot serve the batched orientation
Opus wants, so it falls back to `cat` and loses edit anchors.

Fix for phase 2: `read` expands globs (files only, gitignore-aware, capped) with a
snapshot header per file, and the read/bash docs say so. Before the confirmation grid,
a 10-task x 1 screen of the fixed arm must show the dump rate falling.

### Fix screen

`results/omp-ultra-screen-fix`: `omp-ultra` @ 9106531f6 (a05f8a3 + read globs/docs),
10 tasks x 1, 10/10 passed. Opus now opens with `read src/*.js` or `;` lists; runs
dumping any file through bash 6/10, mostly `cat package.json` beside `ls -R`.

### Phase 2 throughput grid

`results/omp-ultra-grid`: `omp-base` @ 27cdf191b vs `omp-ultra` @ 9106531f6, 14 tasks
x 5 trials, 12 workers, 140/140 attempts kept, about 13 minutes. Comparator verdict
`inconclusive` (only p90 time is undecided).

| Measure | `omp-base` | `omp-ultra` |
| --- | ---: | ---: |
| Passed | 64/70 | 64/70 |
| Total tokens/correct | 117,398 | 107,982 (x0.92, CI 0.84-1.01) |
| Uncached tokens/correct | 19,225 | 18,623 (x0.97, CI 0.91-1.03) |
| Median / p90 wall s (12 workers) | 62.0 / 119.2 | 60.8 / 119.9 |
| Verification after final edit | 51/70 | 56/70 |
| Runs reading globs or `;` lists | 0/70 | 45/70 |
| Runs dumping non-`package.json` files via bash | 11/70 | 23/70 |
| Edit errors (runs) | 4 (3) | 5 (5) |
| Requests | 507 | 472 |

The a05f8a3 bundle on the same baseline had 41/50 source-dump runs and 25 edit errors;
the fix brings edit errors back to baseline level and keeps the bundle's token cut
non-inferior. Correctness finally left the ceiling, but not between arms:
`challenge-safety` failed 5/5 in both arms on the same hidden test ("absent and
regular-file roots are rejected without creating anything") and `challenge-recovery`
failed 1/5 in each. Those are task-difficulty signals, not arm differences.

### Phase 2 latency grid

`results/omp-ultra-latency`: serial `--alternate-order --jobs 1`, 10 original tasks x 2
trials, 40/40 passed, 48.5 minutes. Rule verdict `worse`, driven only by the
verification-after-final-edit proxy (17/20 -> 16/20, one run). Median wall x1.11
(CI 0.97-1.23), p90 x0.77 (CI 0.74-0.86), total tokens x1.00 (CI 0.90-1.11),
uncached x0.97 (CI 0.89-1.05).

### Decision

No demonstrated win. The read-glob fix removes the bundle's edit-error regression
(25 -> 5) and the ultra set is token non-inferior, but neither grid shows a token or
latency improvement beyond the 10% margin. Keep `read` globs/`;`-list docs as a
correctness/ergonomics fix; do not claim a token reduction. Dropped: wire-summary
hypothesis, low verbosity, intent tracing off, smallest-useful-thing as an
efficiency change; read threshold 300 stays unproven.
