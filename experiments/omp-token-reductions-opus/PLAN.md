# Combined token reductions on Opus 5.5

## Why this grid

The three earlier studies each changed one axis or ran on one model:

- Read threshold 100 -> 300 (Sol, installed 18.4.8): comparator `better`,
  -4.4% total / -10.0% uncached tokens, intervals touch 1.0.
- Inline tool descriptors (Opus 5.5, installed 18.4.6): comparator `better`,
  -49% total / -10% uncached tokens per correct solution.
- Integrated bundle (Sol, source 94fc3d8): inline + threshold 300 + lean
  bash/edit payloads + proportional verification. `inconclusive`; inline
  increased Sol's initial input by 3.8%.

The bundle already combines all three changes, but only on Sol, where inline is
the weak component. This grid runs the same bundle on Opus 5.5, where inline
measured a large win. It measures the integrated bundle, not attribution.

## Arms

Identical to [../omp-token-reductions/PLAN.md](../omp-token-reductions/PLAN.md)
except `--model anthropic/claude-opus-5-5` and the per-run `ANTHROPIC_OAUTH_TOKEN`:

- Baseline: `../omp-token-baseline` @ `a7e593859`, overlay inline off / threshold 100.
- Candidate: `../oh-my-pi` @ `94fc3d8b9`, overlay inline on / threshold 300.
- Same overlays, pinned per-arm system-prompt templates, isolated state, no
  prewalk/extensions/skills/rules, AST edit off, thinking high.
- Before the grid all 21 frozen candidate files matched
  `../omp-token-reductions/provenance.json`; both checkouts were clean.

Config: [benchmark-omp-token-reductions-opus.toml](../../benchmark-omp-token-reductions-opus.toml).

## Procedure

```sh
python -m bench --config benchmark-omp-token-reductions-opus.toml --results results/omp-token-reductions-opus-preflight run --harness omp-token-baseline omp-token-candidate --task hard-expr-eval --trials 1 --jobs 1 --alternate-order
python -m bench --config benchmark-omp-token-reductions-opus.toml --results results/omp-token-reductions-opus-grid run --harness omp-token-baseline omp-token-candidate --task bugfix-duration bugfix-invoice debug-cache-race debug-limiter feature-csv-stream feature-lru hard-dep-resolver hard-expr-eval hard-line-diff hard-segment-tree --trials 5 --jobs 8
python -m bench --results results/omp-token-reductions-opus-grid compare --baseline omp-token-baseline --candidate omp-token-candidate --margin 0.1 --min-trials 5
python experiments/omp-read-threshold/analyze.py results/omp-token-reductions-opus-grid
```

Same rules as the Sol grid: ten original fixtures, five trials per cell, keep
every attempt, no selective retries or mid-grid edits, preflight kept separate,
10% margin. Latency at jobs 8 is not comparable with the Sol jobs 4 grid.

## Results

### Run history (all retained, none pooled)

- `results/omp-token-reductions-opus-preflight`: one pair, both passed, Opus usage
  attributed (baseline 13 req / 303k total; candidate 13 req / 259k total).
- `results/omp-token-reductions-opus-interrupted`: 30 attempts (all passed) before
  the agent tool's 300 s command cap killed the runner. Exploratory only.
- `results/omp-token-reductions-opus-aborted{,-2,-3,-4,-5}`: relaunches killed within
  seconds for the same tool-timeout reason (at most one completed row each).
- `results/omp-token-reductions-opus-grid`: the confirmation grid, run detached
  (`Start-Process`) so no tool timeout applied. About 16.5 minutes at jobs 8.

Lesson: launch long grids detached with a log file, not as a tool-managed job.

### Confirmation grid

100/100 attempts, 50/50 passed per arm. No duplicates, timeouts, tampering,
errors or retries. Task/prompt hashes match, 100 distinct workdirs, isolated
state, empty ancestor context, every session `anthropic/claude-opus-5-5`.
All 21 frozen candidate files matched provenance before the grid.

Comparator verdict: `inconclusive`.

| Measure | Baseline | Candidate |
| --- | ---: | ---: |
| Total tokens per correct solution | 107,875 | 117,734 (x1.09, CI 0.95-1.26) |
| Uncached tokens per correct solution | 17,451 | 17,100 (x0.98, CI 0.90-1.06) |
| Median / p90 wall s | 61.8 / 142.1 | 54.3 / 151.6 |
| Verification after final edit | 41/50 | 49/50 |
| Requests | 356 | 385 |
| Mean initial input tokens incl. cache | 6,903 | 7,165 (+3.8%) |
| Bare / ranged reads | 255 / 18 | 49 / 45 |
| Folded reads | 15 | 0 |
| Read output characters | 385,923 | 189,774 |
| Bash calls | 114 | 177 |
| Shell-file-dump commands (runs) | 11 (11) | 64 (49) |
| Edit errors / unseen-line errors | 2 / 2 | 25 / 5 |
| Cache read / cache write tokens | 4,521,182 / 542,265 | 5,031,695 / 535,078 |

Transcripts confirm the shift. In 49/50 candidate runs Opus starts by dumping
sources through bash (`ls -R src test; cat package.json src/*.js test/*`) instead
of `read`. Those files then have no snapshot tag, so first edits are rejected:
`hash #0000 is not from this session` (17), invented tags such as `#R1` (3), and
unseen-line anchors (5); 21 of 50 candidate runs hit at least one. Each rejection adds a request that re-reads a larger
cached prefix, which is where the higher total (cache-read) tokens come from.
Baseline `cat` use is almost entirely `package.json`.

This does not reproduce the installed 18.4.6 inline-only Opus win (-49% total).
The bundle differs from that run in several ways: source build 18.4.5 with pinned
template, concise summaries kept in tool schemas (`*-summary.md`), lean
bash/edit payloads, threshold 300 and the verification wording. This grid cannot
attribute the bash-dump habit. Leading hypothesis: the one-line schema summaries
(bash: "Run commands in a persistent shell.") displace the native read-over-cat
guidance Opus relied on. Next discriminating arm: baseline source with only
`inlineToolDescriptors: "on"`.

The verification gain (41 -> 49) is a lifecycle proxy, not a correctness gain;
correctness is at ceiling.

Artifacts: `results/omp-token-reductions-opus-grid/{runs.jsonl,manifest.json,comparison.txt,comparison.json,mechanisms.jsonl}`.

## Publication bundle

[published/omp-token-reductions-opus-2026-10](../../published/omp-token-reductions-opus-2026-10/README.md)
was produced locally with `python -m bench --results results/omp-token-reductions-opus-grid export
--baseline omp-token-baseline --candidate omp-token-candidate --out published/omp-token-reductions-opus-2026-10
--margin 0.1 --min-trials 5 --include-transcripts`, plus sanitized `mechanisms.jsonl`, a paired
`SESSIONS.md` and `charts/mechanisms.svg` from [mechanism_chart.py](mechanism_chart.py).
Not committed or pushed.
