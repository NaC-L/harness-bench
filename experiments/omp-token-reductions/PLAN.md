# Integrated OMP token reductions

## Arms and authority

- Baseline: detached `../omp-token-baseline`, revision `a7e593859`, OMP 18.4.5.
- Candidate: local `../oh-my-pi` at that revision plus the requested changes.
- Both invoke the source CLI with Bun 1.3.14, not installed OMP 18.4.8.
- Identical native addon SHA-256: `cdd80824b5c8276be7430af57a9348e666a63c021a661ff522b738ec43b394d6`.
- Baseline dependency install uses frozen lockfile, and tool-view assets are generated from baseline source. No workspace-package symlink points into candidate.
- Model/provider: `openai-codex/gpt-6.1-sol`; thinking high; verbosity medium; intent tracing enabled; tools read/bash/edit/write.
- Isolated state, memory off, no extensions/skills/rules/prewalk, unchanged task fixtures.
- Each arm explicitly renders its own source system-prompt template, preventing a home-level project prompt from masking the changed verification guidance in temporary workspaces.
- AST edit is explicitly disabled in both overlays: the source auto-adds it alongside edit even when the four named tools are requested.
- Baseline native descriptors, threshold 100. Candidate inline catalog with concise native descriptions, threshold 300, proportional verification policy, lean bash and edit payloads.
- This comparison measures the integrated bundle, not attribution to individual settings. The separate installed-binary read-threshold comparison isolates the size gate.
- Keep line prefixes and snapshot tags: they are edit authority, not expendable presentation.

## Procedure

Run targeted consumer tests and actual tool smoke before model confirmation. Run a separate one-pair hard-expr-eval preflight; keep every attempt outside confirmation. At the user's explicit request, confirmation uses jobs4 concurrently with the threshold jobs4 grid (eight total workers); parallel latency includes shared provider contention and is not pooled with serial results.

```sh
python -m bench --config benchmark-omp-token-reductions.toml --results results/omp-token-reductions-preflight run --harness omp-token-baseline omp-token-candidate --task hard-expr-eval --trials 1 --jobs 1 --alternate-order
python -m bench --config benchmark-omp-token-reductions.toml --results results/omp-token-reductions-parallel run --harness omp-token-baseline omp-token-candidate --task bugfix-duration bugfix-invoice debug-cache-race debug-limiter feature-csv-stream feature-lru hard-dep-resolver hard-expr-eval hard-line-diff hard-segment-tree --trials 5 --jobs 4
python -m bench --results results/omp-token-reductions-parallel compare --baseline omp-token-baseline --candidate omp-token-candidate --margin 0.1 --min-trials 5
python experiments/omp-read-threshold/analyze.py results/omp-token-reductions-parallel
```

Report correctness/safety before efficiency; use existing comparison gates and 10% noise margin. Include failures, unknown measurements, requests, total and uncached tokens, follow-up reads, ranged/bare and folded reads, edit errors and unseen-line errors, output characters, shell-file-dump candidates, and elapsed time. Shell candidates require transcript inspection before claiming full-file drift. Follow-up counts match the selector-stripped requested path, not canonical filesystem identity. No favorable-trajectory retries or mid-grid edits. Frozen task/prompt hashes and complete coverage are prerequisites to interpretation.

Measurement did not authorize an installed-binary update, personal configuration mutation, commit, push, or publication. The user separately authorized source commits and findings publication after the completed grid.

## Exercised source contracts and preflight

- Small-file source CLI: baseline folds the 121-line evaluator; candidate exposes
  all 121 rows. Candidate boundary smoke reads 299 lines completely, folds at 300,
  and preserves explicit ranges at the boundary.
- Descriptor, prefix-cache and prompt inventory consumers: 103 passing tests.
  Read/seen-line consumers: 19 passing tests. Payload/ACP/seen-line consumers:
  23 passing tests; the subsequently simplified bash wire regression also passes
  all five cases. These groups overlap; do not sum them as unique coverage.
- Both affected package type checks and changed-file oxlint pass. Oxfmt identified
  two added test blocks, which were formatted. Eight unrelated bash ACP tests
  require `/bin/bash` and cannot execute on this Windows host; they were not changed.
- Actual bash calls accept command-only arguments and explicit false/zero options.
  OpenAI Responses omission validation rejects command-only calls in all four
  baseline feature combinations and accepts them in all four candidate cases.
- Paired actual read/edit smoke trims known leading context only, preserves the
  complete TUI diff and fresh header, permits a second edit with that header, and
  rejects unseen-line modification in both arms without changing that line.
- Snapshot tags and line prefixes remain unchanged as edit authority.

Four-tool OpenAI Responses serialization smoke (GPT-5 Mini, not a Sol token
estimate): baseline native schema + rendered prompt is 6,352 + 8,800 characters;
candidate inline is 1,649 + 14,136. Native schema shrinks 74%, but combined
characters grow 4.2%. Relocating descriptions does not prove payload savings.

Source model preflight passed both attempts, using Sol high with matching
task/prompt hashes, source version 18.4.5, isolated state and empty recorded ancestor
context. Observed results, outside confirmation:

| Arm | Initial input tokens including cache | Requests | Uncached tokens | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| Baseline | 4,054 | 11 | 18,882 | 117,442 |
| Candidate | 4,212 | 7 | 27,600 | 67,792 |

Both initial requests reported zero cache reads/writes. Candidate initial payload
was larger, not smaller. Later baseline cache reuse was higher; this pair cannot
establish an uncached-token winner. Candidate bash calls contained only `i` and
`command`, versus 24 optional fields and 12 null values across baseline calls.
Neither preflight used shell-file-dump candidates.

Baseline created a 4,307-character `.contract-check.cjs`, ran it and deleted it.
Candidate extended existing `evaluator.test.js` and used `node --test`, with no
separate checker in this trajectory. Both reproduced edge behavior before editing.
The baseline's `verified_after_final_edit=false` reflects checker cleanup after its
verification command; the candidate's flag is true. Inspect lifecycle before
interpreting that metric as a correctness failure.

[provenance.json](provenance.json) freezes the candidate source hashes before
confirmation. Do not tune these files during the grid.

Direct paired runtime and provider records: [verification.json](verification.json).

Independent static reviews found no patch-introduced defects. A separate smoke
against the actually loaded addon confirms unchanged same-position rows before
`firstChangedLine` for replacement, before/after insertion, range deletion,
multiple anchors, register movement, BOF, EOF and CRLF. This exercises the
compaction safety boundary; it does not assert whole-binary/source-build parity.


## Completed parallel confirmation

All 100 attempts completed: ten tasks, two arms, five trials per cell; 50/50
passed in each arm. No missing/duplicate cells, selective retries, timeouts,
infrastructure failures, or metric gaps. Task/prompt/context hashes matched,
with 100 distinct isolated workdirs. All 21 frozen candidate files, six
configuration/overlay files across both studies, the installed binary, common
threshold prompt and both native addons still match their recorded hashes
(31/31 checks).

| Measure | Baseline | Candidate |
| --- | ---: | ---: |
| Total tokens per correct solution | 79,636 | 72,859 |
| Uncached tokens per correct solution | 20,920 | 20,062 |
| Requests, all attempts | 397 | 405 |
| Mean initial input tokens including cache | 4,120.1 | 4,275.1 |
| Bare / ranged reads | 68 / 237 | 50 / 258 |
| Repeated-path reads | 2 | 8 |
| Folded reads | 1 | 0 |
| Edit errors / unseen-line errors | 2 / 1 | 2 / 2 |
| Read / edit output characters | 397,735 / 46,783 | 407,289 / 48,396 |
| Bash calls | 135 | 133 |
| Bash null / optional fields | 509 / 810 | 0 / 32 |
| Detected shell-file-dump candidates | 0 | 0 |
| Written content characters | 218,173 | 203,282 |
| Verification after final edit | 33/50 | 37/50 |
| Median / p90 elapsed seconds | 154.4 / 281.1 | 149.4 / 296.7 |

Point estimates: 8.5% fewer total tokens and 4.1% fewer uncached tokens.
Candidate/baseline 95% bootstrap intervals are 0.82–1.02 and 0.86–1.07:
both include no improvement. Tokens satisfy the existing 10% non-inferiority
margin, but the overall comparator verdict is `inconclusive`: p90 latency's
interval, 0.91–1.23, cannot exclude more than 10% slowdown. All-pass correctness
is a ceiling, not evidence of superiority. Verification flags are lifecycle
proxies, not independent correctness proofs.

The bash payload mechanism is observed: zero null fields and substantially fewer
optional fields. Inline descriptions increase mean initial input by 3.8%;
do not enable them for OpenAI by default or claim moving descriptions reduces
the initial payload. Existing auto-provider policy is unchanged.
Repeated-path reads and requests increased, and aggregate edit output grew,
despite the paired runtime smoke proving safe trimming for the same edit.
Different trajectories prevent attribution of aggregate savings to echo trimming.

Verification guidance did not eliminate standalone checkers. Inspected candidate
trial-1 sessions successfully created and ran `.csv-smoke.cjs` (5,471 bytes) and
`.diff-smoke.cjs` (5,180 bytes); the latter was rewritten to 1,239 bytes after a
smoke failure. These are retained measured behaviors, not proof that the
proportional-verification objective was achieved. No favorable retries or
post-result source tuning were performed.

Artifacts: `results/omp-token-reductions-parallel/{runs.jsonl,manifest.json,comparison.json,mechanisms.jsonl}`.
Component totals (input/output/cache-read/cache-write): baseline
858,805 / 187,196 / 2,935,808 / 0; candidate
820,486 / 182,592 / 2,639,872 / 0.
Final integrity and aggregate evidence is recorded in [verification.json](verification.json).
Both grids completed in about 68 minutes with four workers each; shared provider
contention limits latency interpretation. During measurement, no installed update,
commit, push, publication or personal configuration change was performed.

## Authorized publication

The measured source snapshot is committed as
[`94fc3d8b97dc040a1ddfc4018f5598cc5e0c0616`](https://github.com/NaC-L/oh-my-pi/commit/94fc3d8b97dc040a1ddfc4018f5598cc5e0c0616)
on the user's fork branch `prompts/smallest-useful-thing`; all 21 frozen file hashes
match. [Published findings](../../published/omp-token-reductions-2026-10/README.md)
include all 100 attempts, charts, sanitized native sessions and readable paired
explorer links. Portable data re-scoring preserves the inconclusive verdict.
The existing Pages builder and real desktop/narrow transcript surfaces were
exercised. Installed OMP and personal configuration remain unchanged.

