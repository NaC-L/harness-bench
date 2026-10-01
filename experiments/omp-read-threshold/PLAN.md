# OMP read-summary threshold: 100 versus 300 lines

## Hypothesis and scope

Reading small source files completely avoids follow-up range reads and unseen-line
edit rejections, reducing requests and tokens without reducing correctness.
This is a hypothesis, not a measured efficiency result. Full reads initially send
more text; the experiment must establish whether avoiding later turns outweighs it.

Only `read.summarize.minTotalLines` changes: baseline 100, candidate 300. Files
below the threshold are read verbatim; files at or above it remain eligible for
structural summaries. Explicit range reads are unchanged. Do not disable edit
safety checks, change verification guidance, or combine this with inline descriptors.

Configuration: [benchmark-omp-read-threshold.toml](../../benchmark-omp-read-threshold.toml).
Overlays: [baseline.yml](baseline.yml), [candidate.yml](candidate.yml).

## Frozen setup

- Both arms: installed OMP 18.4.8; do not update or swap the binary between phases.
  Recheck `omp --version` before preflight and confirmation. A different version
  requires a separately identified experiment; record the executable hash as well.
  Preparation executable SHA-256:
  `59b379b53354da72d2c5262119fe70c44b4e473826ebbaa94d47a2d58a359b1a`.
- Model/provider: `openai-codex/gpt-6.1-sol`, high thinking, same account/transport.
- Native tool descriptors (`inlineToolDescriptors: "off"`), medium response
  verbosity, intent tracing on, read/bash/edit/write only.
- Identical fresh per-run state copied from `experiments/omp-isolated/agent`;
  memory off, no personal instructions or stored credentials in the template.
- OAuth exported per run by the existing runner, never printed or checked in.
- No prewalk, extensions, skills, rules, or title generation. All other behavior
  stays at the same OMP defaults in both arms, including verification/recovery.
- Controlled runs pin the same frozen source template from
  `../omp-token-baseline/packages/coding-agent/src/prompts/system/system-prompt.md`
  in both installed-binary arms; this avoids automatic home-level `SYSTEM.md`
  discovery masking the intended prompt. AST edit is explicitly disabled in both
  overlays because the source automatically adds it alongside edit.
- User-requested parallel confirmation: `--jobs 4`, concurrent with the integrated
  jobs4 grid (eight total workers). Report shared provider load/cache contention;
  do not pool these latency measurements with serial attempts.
- Confirmation: the ten original efficiency fixtures, five trials per task per
  arm, 100 measured attempts. Do not include development or held-out challenges.
- Fresh results roots for local smoke, model preflight, and confirmation. Retain
  all measured failures, timeouts, and usage-limit errors; no selective retries,
  exclusions, or pooling with preflight. If infrastructure prevents completion,
  report the incomplete grid rather than replacing individual cells.

## Preparation checks (no model calls)

```sh
omp --version
python -m bench --config benchmark-omp-read-threshold.toml list
```

The arm commands must differ only in their `--config` argument. Parsed YAML
settings must differ only at `read.summarize.minTotalLines`; state templates,
credentials, tools, model, and effort must match. The existing runner records
versions, overlay contents/hashes, state fingerprints, and task/prompt hashes in
its manifest and index. Compare the executable hash before and after the grid.

Installed OMP 18.4.8 was exercised directly through `omp read`, with each overlay
copied to a separate temporary `PI_CODING_AGENT_DIR/config.yml` and a context-free
temporary working directory. No model requests or credentials were needed:

| Read | Baseline 100 | Candidate 300 |
| --- | --- | --- |
| Original `hard-expr-eval` evaluator, 121 lines | 48 visible rows, 69 elided lines, 1,735 output characters | All 121 rows, 4,306 output characters |
| Short tokenizer | Verbatim | Identical output |
| Large TypeScript source (>300 lines) | Structurally summarized | Identical output |
| Evaluator explicit range `:18-26` | Ranged output | Identical output |

Both evaluator outputs had the same snapshot tag. Temporary smoke files were
removed. This proves installed read behavior, not end-to-end token savings.

## Model preflight

Requested and run. Both attempts passed with isolated state and attributable usage:

| Arm | Requests | Uncached tokens | Follow-up reads | Folded reads | Edit errors |
| --- | ---: | ---: | ---: | ---: | ---: |
| 100 | 8 | 26,219 | 1 | 1 | 0 |
| 300 | 6 | 15,971 | 0 | 0 | 0 |

Candidate ran first because the initial CLI invocation mistakenly repeated
`--harness`; argparse retained the last value. The retained baseline attempt was
then run separately in the same preflight directory. No attempt was discarded.
This pair is activation/preflight evidence, not a savings verdict.

The first confirmation invocation was cancelled after five completed attempts
when source consumer tests demonstrated home-level project prompt discovery from
temporary workspaces, despite an isolated agent directory. Installed-binary
discovery was not separately observed; avoiding that risk is a control correction,
not a claim that those installed runs demonstrably loaded the home prompt.
Those five rows remain in `results/omp-read-threshold` as exploratory data and are
not pooled with confirmation. The original preflight is retained separately.
Controlled preflight and confirmation use fresh directories below.

Use a new suffix if repeating preflight for a genuinely changed prerequisite.

```sh
python -m bench --config benchmark-omp-read-threshold.toml --results results/omp-read-threshold-controlled-preflight run --harness omp-read-100 omp-read-300 --task hard-expr-eval --trials 1 --jobs 1 --alternate-order
```

Require both attempts to pass with attributable, nonzero token usage, isolated
state and no ancestor context. Inspect raw sessions: a bare evaluator read should
fold under baseline and expose the complete file under candidate. If the agents
do not perform that read, the installed-tool smoke above remains the activation
proof; do not force tool choices or retry until a favorable trajectory appears.
Resolve any preflight credential/configuration failure before collecting measured
runs, and keep every preflight attempt outside confirmation.

## Confirmation and analysis

```sh
python -m bench --config benchmark-omp-read-threshold.toml --results results/omp-read-threshold-parallel run --harness omp-read-100 omp-read-300 --task bugfix-duration bugfix-invoice debug-cache-race debug-limiter feature-csv-stream feature-lru hard-dep-resolver hard-expr-eval hard-line-diff hard-segment-tree --trials 5 --jobs 4
python -m bench --results results/omp-read-threshold-parallel compare --baseline omp-read-100 --candidate omp-read-300 --margin 0.1 --min-trials 5
```

Use the existing comparison rule: exact correctness/safety non-inferiority gates,
10% efficiency margin, and task-stratified bootstrap intervals. Do not lower the
trial minimum, change the acceptance rule, or tune the candidate mid-grid.
All-pass results cannot establish correctness superiority.

Report total and uncached tokens per correct solution (including failed attempts),
input/output/cache components, requests, tool calls, median/p90 elapsed time,
verification, regressions, tampering, timeouts, and missing metrics. Uncached
usage includes input, output, and cache writes; total also includes cache reads.
Neither token measure alone is monetary cost.

From the bounded raw sessions, also report per-task bare/ranged read counts,
folded reads, read-output characters, and edit errors containing `never displayed`.
Use explicit error evidence rather than calling every rejected edit a retry.
These mechanism counts explain the result; they are not additional winner tests
or token-savings estimates. Larger initial reads with unchanged requests may lose.

Confirm matched task/prompt hashes, unchanged binary/overlays/state template,
complete trial coverage, and no state/context leakage before interpreting results.
Review secrets before any local transcript export. Preparation does not authorize
publication, commits, pushes, or changing the user's personal OMP configuration.

## Controlled preflight evidence

Both corrected attempts passed with installed OMP 18.4.8, matching task/prompt
hashes, isolated state, pinned common template and nonzero attributed Sol usage.
Recorded ancestor context is empty; explicit template precedence, not that empty
inventory alone, controls project system-prompt discovery.

| Threshold | Initial input tokens including cache | Requests | Uncached tokens | Repeated-path reads | Elided reads | Edit errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 4,055 | 9 | 18,001 | 0 | 0 | 0 |
| 300 | 4,056 | 11 | 35,130 | 1 | 0 | 0 |

Both trajectories predominantly used explicit ranges, so neither observed a
structural fold. The installed/source read smoke remains the size-gate activation
proof. Do not retry to force bare reads or infer savings from this pair.
Full-grid confirmation now uses `results/omp-read-threshold-parallel`. The user
requested parallel execution after 35 observed passing serial attempts; the
serial invocation was stopped and `results/omp-read-threshold-controlled` retained
separately. Keep all final recorded serial rows, including any cancellation-time
completion, outside parallel confirmation; no cell-level cherry-picking.


## Completed parallel confirmation

All 100 attempts completed: ten tasks, two arms, five trials per cell; 50/50
passed in each arm. No missing/duplicate cells, selective retries, timeouts,
infrastructure failures, or metric gaps. Task/prompt/context hashes matched,
and all 100 workdirs were distinct with isolated state. Frozen binary, prompt,
overlays and benchmark configuration still match their recorded hashes.

| Measure | Threshold 100 | Threshold 300 |
| --- | ---: | ---: |
| Total tokens per correct solution | 83,736 | 80,052 |
| Uncached tokens per correct solution | 22,475 | 20,227 |
| Requests, all attempts | 412 | 418 |
| Bare / ranged reads | 57 / 246 | 55 / 253 |
| Repeated-path reads | 5 | 5 |
| Folded reads | 1 | 0 |
| Edit errors / unseen-line errors | 0 / 0 | 1 / 1 |
| Read / edit output characters | 395,920 / 48,096 | 398,563 / 50,805 |
| Detected shell-file-dump candidates | 0 | 0 |
| Verification after final edit | 35/50 | 36/50 |
| Median / p90 elapsed seconds | 160.3 / 289.9 | 154.2 / 286.0 |

Point estimates are 4.4% fewer total tokens and 10.0% fewer uncached tokens.
Candidate/baseline 95% bootstrap intervals are 0.85–1.08 and 0.81–1.00,
respectively; do not call this a definitive token-saving result. The existing
comparator reports `better` because verification increases by one run while
correctness is equal and tokens/time pass its 10% non-inferiority margin.
That label does not establish correctness superiority or a causal safety gain.

The follow-up-read hypothesis was not demonstrated: counts stayed 5/5 and
requests increased. Only one baseline read folded, so these trajectories barely
exercise the changed size gate. The candidate unseen-line rejection in
`hard-expr-eval`, trial 3, follows an edit that produced a new partial snapshot;
the next edit tried line 30, absent from that new snapshot. A reread and subsequent
edit succeeded, and the attempt passed. It was not a small-file structural fold.

Artifacts: `results/omp-read-threshold-parallel/{runs.jsonl,comparison.txt,mechanisms.jsonl,coverage-audit.json}`.
Component totals (input/output/cache-read/cache-write): baseline
935,828 / 187,928 / 3,063,040 / 0; candidate
826,490 / 184,881 / 2,991,232 / 0.
Both grids ran concurrently for about 68 minutes; parallel timings include shared
provider contention and must not be compared with retained serial data.

## Authorized publication

After measurement, the user separately authorized commit, push and publication.
[Published findings](../../published/omp-read-threshold-2026-10/README.md) retain
all 100 attempts, charts, sanitized native sessions and paired readable explorer
links. Portable data re-scoring reproduces the comparator verdict and intervals.
Publication does not attribute this installed-OMP 18.4.8 grid to the separate
source-change commit; earlier serial and preflight attempts remain outside it.

