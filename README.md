# Coding-agent harness benchmark

## What it measures

- **Correctness:** successful solutions, hidden-test coverage, regressions, and reliable completion.
- **Tokens:** total and uncached tokens per correct solution, including failed attempts, retries, and auxiliary calls.
- **Time/safety:** median and tail wall time, timeouts, prohibited edits, and post-edit verification.
- Correctness and safety use exact non-inferiority gates: a measured regression makes the candidate `worse`.
- Tokens and time compare the candidate/baseline ratio's 95% bootstrap interval (runs resampled within each task, 2,000 resamples) with a 10% margin. `worse` needs the whole interval above +10%. `better` needs an interval wholly below −10% with no possible loss beyond +10%. `same` needs the interval inside the band. An interval that could still exceed +10%, or that rules out a loss without proving a gain or equivalence (`non-inferior`), makes the verdict `inconclusive` and names the measure that needs more trials.
- Mismatched tasks/inputs, fewer than three trials per task per arm, or unknown token/runtime data make the comparison `inconclusive`; unknown is not zero.
- Scorecards distinguish success, solution failure, infrastructure failure and unknown evidence. Explicit infrastructure contamination blocks a positive or equivalent verdict; measured correctness/safety deterioration still reports `worse`. No failed attempts are excluded.
- JSON, text and markdown comparisons include per-task pass-rate differences and token/time point ratios alongside the aggregate verdict. Per-task effects are descriptive, not additional winner claims.
- Report headers support redirected Windows output using `cp1252`; task and harness names still need to be representable in the output encoding.
- See [BENCHMARK_ANALYSIS.md](BENCHMARK_ANALYSIS.md#automated-scoring) for the full rule and past findings.

## Published results

Each row compares a **baseline** arm with a **candidate** arm on the same tasks; harness/settings comparisons also hold the model fixed, while the explicitly labeled model comparison holds the harness fixed. The "Winner" column is the arm the current interval-based rule favors when the bundle is re-scored with `compare`, or states that there is none. Older bundle `REPORT.md` files are dated snapshots scored with the earlier point-estimate rule; under that rule, four repeats of the same smallest-useful-thing comparison gave `better`, `equivalent`, `worse` and `better`.

| Comparison (baseline → candidate) | Winner | By how much | Trust it? |
| --- | --- | --- | --- |
| **OMP read threshold:** 100 → 300 lines, GPT-6.1 Sol high, 10 tasks × 5 trials. [Findings and sessions](published/omp-read-threshold-2026-10/README.md) | **300 by the rule**, not a proven token winner | Total tokens/correct ×0.96 (95% CI 0.85–1.08); uncached ×0.90 (0.81–1.00); both 50/50 passed; verification proxy 35→36/50 | Only one baseline fold; follow-up reads unchanged; correctness at ceiling; eight shared concurrent workers |
| **OMP integrated payload changes:** frozen source baseline → concise inline descriptions, threshold 300, verification guidance and lean bash/edit payloads. [Findings and sessions](published/omp-token-reductions-2026-10/README.md) | **None** (inconclusive) | Total tokens/correct −8.5% (ratio CI 0.82–1.02); uncached −4.1% (0.86–1.07); both 50/50 passed; p90 ratio CI 0.91–1.23 | No definitive savings; initial input +3.8%; follow-up reads increased; standalone checkers persisted; no per-change attribution |
| **OMP integrated payload changes on Opus 5.5:** same frozen baseline → combined inline descriptors, threshold 300, verification guidance and lean bash/edit payloads, Claude Opus 5.5 high. [Findings and sessions](published/omp-token-reductions-opus-2026-10/README.md) | **None** (inconclusive) | Total tokens/correct +9.1% (ratio CI 0.95–1.26); uncached −2.0% (0.90–1.06); both 50/50 passed; verification proxy 41→49/50 | Opus swaps `read` for bash file dumps (bare reads 255→49, edit errors 2→25), so the inline-only Opus win does not carry over; correctness at ceiling; no per-change attribution |
| **Model comparison on OMP:** GPT-6.1 Sol → Claude Opus 5.5, both high, isolated state, 10 tasks × 3 trials. [Results, graphs and sessions](published/opus-vs-sol-2026-10/README.md) | **None** (tradeoff) | Opus median time 57.2s vs 155.4s (×0.37, 95% CI 0.32–0.39); estimated API cost ×3.49; total tokens ×2.02; both 30/30 passed | This task set only: correctness at ceiling, different tokenizers/providers, 12 concurrent workers, uncontrolled cache/load; high thinking is not an equal compute budget |
| **Where OMP puts tool descriptions:** native tool schemas (`omp-baseline`) → descriptions inlined in the system prompt (`omp-inline`). GPT-6.1 Sol high, isolated state, 6 tasks × 4 trials. [Report](published/omp-inline-descriptors-isolated-2026-09/REPORT.md) | **Inline descriptions** (`omp-inline`) | Total tokens per correct ×0.65 (95% CI 0.56–0.78); time not measurably worse (median ×0.83, CI 0.80–0.91); 24/24 passed in both arms. The Opus 5.5 repeat ([data](published/omp-inline-descriptors-opus-2026-10/README.md)) also re-scores `better`: tokens ×0.51 (CI 0.44–0.61) | Yes for tokens. A time gain is likely but its interval reaches the margin. Correctness is at ceiling (both arms pass every run). The "safer" part rests on one baseline run that skipped its final test |
| **Same question, early pilot:** 3 tasks × 1 trial. [Report](published/omp-inline-descriptors-pilot-2026-09/REPORT.md) | **None** (inconclusive) | Too few trials to decide | No: superseded by the row above; ran with the operator's personal OMP state |
| **Pi vs OMP**, both GPT-6.1 Sol high: `omp-sol` → `pi-sol`. 3 tasks × 3 trials. [Report](published/pi-vs-omp-sol-2026-09/REPORT.md) | **None** (inconclusive) | Tokens per correct ×0.44 (95% CI 0.39–0.49), clearly fewer; median time ×0.88 (CI 0.79–1.20) could still be more than 10% slower | Partly: ran with the operator's personal state, and the two are different harnesses and versions |
| **OMP verbosity:** medium → low, intent tracing on. GPT-6.1 Sol high, isolated state, 4 hard tasks × 3 trials. [Graphs/report](published/omp-verbosity-intent-2026-09/low-verbosity/REPORT.md) | **None** (inconclusive) | Total tokens per correct ×0.98 (CI 0.84–1.16); 12/12 passed in each arm | Too noisy at 3 trials to rule out a 10% loss; four concurrent workers, cache/load uncontrolled; correctness at ceiling |
| **OMP tool-intent tracing:** on → off, medium verbosity. [Graphs/report](published/omp-verbosity-intent-2026-09/no-intent/REPORT.md) | **None** (inconclusive) | Total tokens per correct ×1.10 (CI 0.90–1.32) | Same matched-model hard-task grid and parallel limitations |
| **OMP combined settings:** medium/on → low/off. [Graphs/report](published/omp-verbosity-intent-2026-09/low-no-intent/REPORT.md) | **None** (inconclusive) | Total tokens per correct ×1.09 (CI 0.85–1.38) | Same grid; all 48 runs passed. [Overview and portable data](published/omp-verbosity-intent-2026-09/README.md) |

![Where OMP puts tool descriptions: inline uses fewer tokens than native schemas](published/omp-inline-descriptors-isolated-2026-09/charts/summary.svg)

![OMP combined settings: lower median time but worse p90 time than baseline](published/omp-verbosity-intent-2026-09/low-no-intent/charts/summary.svg)

Every `REPORT.md` opens with the same kind of sentence, for example: *"Winner: omp-inline (candidate). Compared with omp-baseline (baseline) it uses fewer tokens, runs faster and is safer; correctness is the same."*

Re-score any bundle without model access: `python -m bench --results <bundle> compare --baseline <a> --candidate <b>`. Add charts to your own report with `compare --format markdown --charts-dir <dir>`; `export` includes them automatically.

## Challenge tier and held-out evaluation

The original ten fixtures remain efficiency controls. Four new challenge fixtures cover repository navigation (`challenge-routing`), interacting persistence bugs (`challenge-journal`), interrupted local work (`challenge-recovery`) and implementation safety boundaries (`challenge-safety`). [Development calibration](experiments/challenge-tier/CALIBRATION.md) passed **12/12**, so routing and journal did **not** qualify as harder correctness tests. Recovery/safety difficulty remains unmeasured; task names do not establish difficulty.

Routing and journal are development fixtures. Recovery and safety carry the `heldout` tag: default `run` and `run --task all` exclude them; running them requires explicit task names. Listing and zero-model validation include all fixtures. Do not tune prompts or candidates on held-out model transcripts.

The [fixed calibration/confirmation protocol](experiments/challenge-tier/PLAN.md) declares three development trials per arm before measurement, a separate six-trial confirmation grid, task acceptance criteria and contamination rules. Calibration and confirmation are never pooled. Program-level recovery/safety tasks do not prove harness approval enforcement or context-compaction reliability.

## Requirements

- Python 3.12+; Python standard library only, no packages to install. CI covers 3.12 and 3.14 on Linux, Windows and macOS.
- Node 22+ for the supplied JavaScript tasks.
- The harness CLIs you want to test, installed and authenticated with **your own model account**. Real harness runs spend model usage; the reference run below does not.
- The Pi arms in `harnesses.toml` and `benchmark-pi-omp*.toml` expect a pinned local install: `npm install --prefix .tools/pi @earendil-works/pi-coding-agent@0.99.1`. The `herdr-omp` example expects `.tools/herdr/herdr.exe`. `.tools/` is gitignored.

Run commands from this repository's root. Workdirs are disposable copies, **not security sandboxes**: only run trusted tasks and harness commands. Configure approvals and any real sandbox in the harness itself.

## Quick start: zero model spend

```sh
python -m unittest discover -s tests
python -m bench.validate_tasks
python -m bench --config benchmark-reference.toml --results results/reference run --harness reference-a reference-b --trials 3 --jobs 12
python -m bench --results results/reference compare --baseline reference-a --candidate reference-b
```

The reference arms copy each task's `solution/` into the workdir. Expect **72 PASS runs** (ten controls plus two development challenges × two arms × three trials); the two held-out tasks require explicit names. Then expect `Verdict: inconclusive` with the reason `token usage unknown`. This is intentional: `kind = "none"` has no model token data, so the run verifies the pipeline, not harness efficiency. Task validation checks failing starting repos and passing reference solutions for all fourteen tasks without model calls.

Use a fresh results directory for each experiment: runs and invocation manifests are appended, not replaced.

## Compare two harness configurations

Define two named arms in a TOML config, each with `kind`, an argv-list `command`, and `version_command`; optional `env` supplies environment overrides. Start from [harnesses.toml](harnesses.toml), but pin **model/provider, thinking effort, tools, account/transport, and recovery/approval settings identically**. Change exactly one experimental variable.

Worked example: [benchmark-omp-descriptors.toml](benchmark-omp-descriptors.toml) defines `omp-baseline` and `omp-inline`. Their command templates differ only in the OMP `--config` overlay path:

- [experiments/omp-descriptors/baseline.yml](experiments/omp-descriptors/baseline.yml): `inlineToolDescriptors: "off"`.
- [experiments/omp-descriptors/inline.yml](experiments/omp-descriptors/inline.yml): `inlineToolDescriptors: "on"`.

The benchmark's global `--config` selects the TOML arm definitions; the OMP `--config` **inside each arm's argv** selects a run-local YAML overlay. An overlay alone does not isolate a run: OMP still reads the operator's `~/.omp/agent` (global `AGENTS.md`, settings, `models.yml`, MCP servers, memories). That is why both arms also set `state_template` and `env_commands`, described below.

New settings experiment: [benchmark-omp-verbosity-intent.toml](benchmark-omp-verbosity-intent.toml) compares the isolated baseline with low response verbosity, disabled tool-intent tracing, and both together. The [2x2 protocol and commands](experiments/omp-verbosity-intent/PLAN.md) pin four hard tasks × four arms × three trials (48 measured runs), with a separate preflight. The four-worker grid passed 48/48; the existing comparison rule favors baseline in all three comparisons. [Graphs, interpretation and portable data](published/omp-verbosity-intent-2026-09/README.md). Correctness remains at ceiling; parallel latency includes shared provider load.

Read-summary experiment: [benchmark-omp-read-threshold.toml](benchmark-omp-read-threshold.toml) compares 100- versus 300-line thresholds with isolated OMP state, a pinned common prompt template, GPT-6.1 Sol high, native descriptors, and four tools. The [protocol and evidence](experiments/omp-read-threshold/PLAN.md) retain ten tasks × two arms × five trials. Confirmation passed 100/100 with four workers, concurrently with the integrated grid; earlier partial serial/exploratory grids remain separate. [Published findings, charts and sessions](published/omp-read-threshold-2026-10/README.md) distinguish non-inferiority from a proven savings result.

Integrated source experiment: [benchmark-omp-token-reductions.toml](benchmark-omp-token-reductions.toml) compares the frozen source baseline with all four requested token reductions. The [controls and commands](experiments/omp-token-reductions/PLAN.md) retain concise native tool descriptions and read/edit authority; results measure the bundle, not individual attribution. Confirmation passed 100/100. [Published findings, charts and sessions](published/omp-token-reductions-2026-10/README.md) report lower token point estimates but an inconclusive verdict. Both grids ran concurrently with four workers each; latency includes shared provider load.

Opus repeat of the integrated experiment: [benchmark-omp-token-reductions-opus.toml](benchmark-omp-token-reductions-opus.toml) changes only the model and credential. The [protocol and results](experiments/omp-token-reductions-opus/PLAN.md) record 100/100 passing attempts at eight workers, an inconclusive verdict, and a shift from `read` to bash file dumps that causes snapshot-tag edit rejections. [Published findings, charts and sessions](published/omp-token-reductions-opus-2026-10/README.md).

### Isolating harness state

Without isolation, a result measures the harness **plus the operator's personal setup**. A canary check confirmed this for OMP: a non-isolated run quoted the operator's global `AGENTS.md` back, tried to connect to the operator's MCP servers, and sent about 970 more input tokens on its first request.

- `state_template = "experiments/omp-isolated/agent"` copies that checked-in directory into a fresh per-run state root. For omp and pi the root is set through `PI_CODING_AGENT_DIR`, for Claude through `CLAUDE_CONFIG_DIR`, and for Codex through `CODEX_HOME`. `OMP_PROFILE`/`PI_PROFILE` are removed so a profile cannot override it. The copy is deleted after the run.
- `env_commands = { OPENAI_CODEX_OAUTH_TOKEN = ["omp", "token", "openai-codex"] }` computes credentials per run from **your** login, so an isolated state root needs no stored credentials. Values are never written to records, manifests, artifacts or error messages.
- The template's files are recorded in `manifest.json` and shown in `REPORT.md`, so readers see the exact state the agent ran with. `context_hashes` fingerprint the files OMP actually reads.
- Each run also records `ancestor_context`: non-empty `AGENTS.md`, `.omp`, `.mcp.json` and similar entries in folders above the workdir, which harnesses discover as project context.
- `compare` warns when a stateful arm was not isolated or had ancestor context.
- An isolated agent directory does not fence project prompt discovery. Source tests observed a home-level `.omp/SYSTEM.md` through Windows temporary-workspace ancestry; `ancestor_context` skips home, so an empty list alone is not proof of prompt isolation. The new threshold and integrated grids pin explicit `--system-prompt-template` files; template/source hashes must be checked separately.

This command makes model calls; check your account and pinned model first:

```sh
python -m bench --config benchmark-omp-descriptors.toml --results results/descriptors run --harness omp-baseline omp-inline --trials 3 --jobs 12
```

To repeat the published six-task, four-trial descriptor experiment with **Claude Opus 5.5 high**, use [benchmark-omp-descriptors-opus.toml](benchmark-omp-descriptors-opus.toml). It preserves both overlays and isolated state, obtaining `ANTHROPIC_OAUTH_TOKEN` per run from `omp token anthropic`:

```sh
python -m bench --config benchmark-omp-descriptors-opus.toml --results results/omp-descriptors-opus run --harness omp-baseline omp-inline --trials 4 --jobs 12 --task bugfix-duration bugfix-invoice debug-cache-race debug-limiter feature-csv-stream feature-lru
python -m bench --results results/omp-descriptors-opus compare --baseline omp-baseline --candidate omp-inline
```

For **Pi vs OMP on Claude Opus 5.5 high**, use [benchmark-pi-omp-opus.toml](benchmark-pi-omp-opus.toml). Both arms use fresh isolated state, the same four tools, and Anthropic OAuth from `omp token anthropic`; the OMP overlay disables advisor and unexpected-stop detection. Require a passing separate preflight with nonzero token usage before collecting measured runs:

```sh
python -m bench --config benchmark-pi-omp-opus.toml --results results/pi-omp-opus-preflight-rerun run --harness omp-opus pi-opus --task bugfix-duration --trials 1 --jobs 1 --alternate-order
python -m bench --config benchmark-pi-omp-opus.toml --results results/pi-omp-opus run --harness omp-opus pi-opus --task bugfix-duration bugfix-invoice debug-cache-race debug-limiter feature-csv-stream feature-lru hard-dep-resolver hard-expr-eval hard-line-diff hard-segment-tree --trials 3 --jobs 1 --alternate-order
python -m bench --results results/pi-omp-opus compare --baseline omp-opus --candidate pi-opus
```

The initial 2026-10-01 preflight in `results/pi-omp-opus-preflight` was blocked: OMP passed, but Pi's first request returned Anthropic HTTP 400, “You're out of extra usage,” with zero generated tokens. This was not subscription quota exhaustion: the account usage endpoint showed 0% five-hour and 43% weekly utilization, with extra usage disabled. Differential request probes using the same token showed HTTP 400 with Pi's native system instruction and HTTP 200 after changing only that instruction's text to a short neutral instruction. The provider's internal routing reason is unknown; evidence is recorded in `results/pi-omp-opus-diagnosis.json`. No measured comparison was launched, and no native system prompt was replaced. Resolve the native-request rejection or explicitly choose a shared-system-prompt experiment before rerunning; this is not evidence of a harness winner.

For **Pi vs OMP on Kimi K3 high**, use [benchmark-pi-omp-kimi.toml](benchmark-pi-omp-kimi.toml). OMP calls the provider `kimi-code`; Pi calls it `kimi-coding`. Both use model `k3`, native system prompts, the same four tools, isolated state, and a Kimi credential exported per run by `omp token kimi-code`. OMP's benchmark-owned `models.yml` explicitly maps that provider to `KIMI_API_KEY`; Pi reads the variable natively. No secret is checked into the state template.

```sh
python -m bench --config benchmark-pi-omp-kimi.toml --results results/pi-omp-kimi-preflight-rerun run --harness omp-kimi pi-kimi --task bugfix-duration --trials 1 --jobs 1 --alternate-order
python -m bench --config benchmark-pi-omp-kimi.toml --results results/pi-omp-kimi-parallel-rerun run --harness omp-kimi pi-kimi --task bugfix-duration bugfix-invoice debug-cache-race debug-limiter feature-csv-stream feature-lru hard-dep-resolver hard-expr-eval hard-line-diff hard-segment-tree --trials 3 --jobs 8
python -m bench --results results/pi-omp-kimi-parallel-rerun compare --baseline omp-kimi --candidate pi-kimi
```

Require a passing preflight with nonzero token usage from both arms before running the measured grid. Keep all preflight and credential-configuration failures outside the measured results. This eight-worker schedule is a throughput comparison: per-run latency includes concurrency and provider contention. For isolated latency, use a separate results directory and replace `--jobs 8` with `--jobs 1 --alternate-order`; do not mix rows from different schedules.

The 2026-10-01 eight-worker run retained all 60 attempts: OMP passed 20/30 and Pi 18/30, but 14 provider usage-limit rejections, one authentication rejection, and one timeout prevent a clean winner conclusion. See the [qualified local report](published/pi-vs-omp-kimi-2026-10/REPORT.md) and [offline session explorer](published/pi-vs-omp-kimi-2026-10/EXPLORER.html); the earlier partial serial batch is separate.

The [quota-filtered report](published/pi-vs-omp-kimi-2026-10-no-quota/REPORT.md) excludes only those 14 usage-limit rejections: OMP passed 20/24 (83.3%), Pi 18/22 (81.8%). Authentication, timeout, and task-check failures remain. Raw evidence is preserved; exclusion IDs and source hash are in the filtered manifest. Missing trials keep the overall verdict inconclusive.

Use **at least three trials per task per arm**. `--jobs` limits concurrent runs and defaults to **16 total**, not 16 per arm. Baseline and candidate for each task/trial are submitted adjacently to help share conditions, not guarantee identical provider load. For latency-sensitive studies, use `--alternate-order` (defaults to one worker) or explicitly `--alternate-order --jobs 1` to run serial pairs with alternating arm order; parallel execution is not compatible with `--alternate-order`.

### Faster future experiments: screen, then confirm

Use one runner with `--jobs 16` (sixteen concurrent runs total, not sixteen per arm). It already isolates each workspace/state and writes one manifest/index; no manual worker merge is needed. Keep model, thinking effort, task IDs and concurrency identical across arms. This is a throughput schedule, not an isolated-latency comparison; do not use `--alternate-order`.

For four arms and four hard tasks, screen with one trial per cell (16 runs), then run a fresh confirmation grid with three trials (48 runs). Screening is exploratory: report every arm and do not lower `compare`'s three-trial minimum to announce a winner. Before confirmation, freeze the candidate set and acceptance criteria. If dropping candidates, include the baseline and disclose the screening selection; never pool screening rows with confirmation. New configurations still require a separate passing preflight with token metrics.

The [settings experiment's earlier eight-worker workflow](experiments/omp-verbosity-intent/PLAN.md#future-eight-worker-workflow) remains reproducible with explicit `--jobs 8`; for new sixteen-worker grids, use `--jobs 16` and fresh result roots. If rate limits make sixteen workers unreliable, diagnose and choose a lower fixed concurrency for a new run rather than changing an active grid or selectively retrying cells. Sixteen workers reduce potential elapsed time, not the model usage of the same grid; actual model-run speedup is unmeasured.


Command placeholders (from the `harnesses.toml` header):

```text
{prompt}, {workdir}, {session_dir}, {session_id}, {task_dir}, {run_id},
{benchmark_dir}, {python}, {timeout_sec}
```

These expand without a shell; runtime paths also work in `version_command`. Use `--task` to select task IDs and `--timeout` to override the per-task agent timeout.

### Four-arm OMP / Codex / Pi experiment

[benchmark-omp-inline-baseline-codex-pi.toml](benchmark-omp-inline-baseline-codex-pi.toml)
defines isolated `omp-inline`, `omp-baseline`, `codex` and `pi` arms using the same
ChatGPT account/backend, `gpt-6.1-sol` and high effort. Install local Codex with
`npm install --prefix .tools/codex @openai/codex@0.159.2` and Pi as above; authenticate
OMP to `openai-codex`. Pi/Codex receive temporary access-only credentials from
`omp token openai-codex`, never operator auth files or refresh tokens.

See [the preregistered protocol](experiments/omp-inline-codex-pi/PLAN.md) for the
four-run preflight, 72-run measured grid and three baseline comparisons. Windows
Codex workspaces inherit parent sandbox ACLs; credential state remains private.
Cross-harness results include native prompt/tool/sandbox differences, not just
OMP descriptor placement. [Published results and combined graph](published/omp-inline-baseline-codex-pi-2026-09/REPORT.md)
include sanitized per-run data; credentials and raw session artifacts are excluded.


## Read and share results

After the quick start, these examples use the reference arms. For a model experiment, substitute its results directory and arm names.

```sh
python -m bench --results results/reference compare --baseline reference-a --candidate reference-b
python -m bench --results results/reference compare --baseline reference-a --candidate reference-b --format markdown > REPORT.md
python -m bench --results results/reference export --baseline reference-a --candidate reference-b --out published/reference
```

Text is the default; `compare --format json` is also available (`--json` is a deprecated alias). `--margin` changes the efficiency noise band, and `--min-trials` changes the minimum evidence threshold.

`export` refuses an existing output directory. It produces a sanitized, shareable bundle:

- `REPORT.md`: verdict, dimension and per-task tables, setup, caveats, and reproduction commands.
- `runs.jsonl`: only the selected arms; workdirs cleared and artifact paths made bundle-relative.
- `manifest.json`: recorded provenance, when available.
- `SESSIONS.md`: task/trial-ordered links to captured sessions, with `--include-transcripts`.
- `EXPLORER.html`: offline, clickable run/session explorer, generated automatically for every export.
- `runs/<harness>/<task>/trial-<n>/`: available `patch.diff`, `check.txt`, and `check-visible.txt` files.

Repository, home, and temporary paths are replaced with placeholders. **Transcripts are excluded by default**: they can contain your private system prompt/config. Add `--include-transcripts` after reviewing them to include `session.jsonl` alongside each trial's patch/check files, plus `stdout.jsonl` and `stderr.txt`. A session's companion files live in `session/`; multiple native session logs retain their names under `sessions/`. Path sanitization does not remove arbitrary secrets. Review patches and overlay contents for secrets too.

To compare sessions, open the same task/trial under each harness, e.g. `runs/pi-sol/debug-limiter/trial-1/session.jsonl` and `runs/omp-sol/debug-limiter/trial-1/session.jsonl`. These are the original harness session records, not a lossy reconstruction from stdout. The bundles under `published/` include them; no manual `/dump` or lookup by run UUID is needed.

### Offline HTML session explorer

```sh
python -m bench --results published/opus-vs-sol-2026-10 explore --out opus-vs-sol.html
```

For future published runs, use `export --include-transcripts` after secret review:
it generates `EXPLORER.html` automatically from the sanitized bundle. Open that file
as the primary session-review view; the JSONL remains the machine-readable source.

Open the generated file directly in a browser; no server, dependencies, or network access needed.
Filter by harness, task, result, or run ID, then click a run to inspect its metrics,
chronological session records, tool arguments/results, captured reasoning (optional),
checks, patch, and complete metadata. Session search and browser back/forward are supported.
OMP/Pi messages are rendered as conversation cards; other native event formats remain
inspectable as expandable raw records. Missing artifacts and measurements are labeled,
not reconstructed. A saved `REPORT.md` is included as a snapshot, not re-scored.

Existing `charts/*.svg` comparison graphs are embedded as self-contained images with
canonical LF line endings. An overview, per-task tokens, and per-task wall-time selector
are available where saved charts exist. Captions, original
comparison scope, and text values/methodology are preserved. Run filters affect the
run list, not these frozen plots. Bundles without saved charts say so explicitly.
Narrow screens scroll charts horizontally rather than shrinking their labels.

`explore` refuses to overwrite an existing file and only reads artifacts inside the
supplied results directory. It embeds available transcripts and stderr **without further
sanitization**: use a reviewed exported bundle for sharing, and review the HTML for secrets.
The generated [Opus vs Sol explorer](published/opus-vs-sol-2026-10/EXPLORER.html)
contains all 60 runs; download it and open locally (GitHub's file view does not execute HTML).

### Browser-hosted experiment index

Open [the experiment website](https://nac-l.github.io/harness-bench/) and select a
bundle to inspect its runs without downloading HTML. The `pages` GitHub Actions
workflow rebuilds the index and explorers when `published/`, `bench/`, or its
workflow changes on `main`; it can also be run manually. Pages must use the
**GitHub Actions** publishing source.

Only committed `published/` data is deployed, never private `results/`. Review
bundles for secrets before committing: publishing makes their captured content
browser-accessible. JSONL bundles get explorers; CSV-only historical reports link
to their original GitHub bundle. The build does not re-score old reports.
The index and explorer use an Instrument-style black/cyan theme: hairlines, mono
labels and tabular numbers, square marks, and restrained dither accents. They share
one stylesheet; no external scripts or fonts are needed.
Experiments are ordered newest first by their earliest recorded run start, shown
in UTC. Without a usable run timestamp, the index uses the bundle's labeled date
or month. Month-only dates sort at the beginning of that month and remain labeled
as month-only; unknown dates appear last. Filesystem modification times are not used.

To preview the same site locally, choose a new output directory:

```sh
python -m bench.site --out results/site-preview
```

Open `results/site-preview/index.html` directly in a browser.
Generated HTML uses UTF-8 with LF line endings, so the same inputs produce the
same bytes on Windows and Linux for deployment checksum verification.

`results/` is gitignored on purpose; `published/` is intended for reviewed bundles you choose to commit. Anyone can re-run `compare` directly on a bundle by setting the global `--results` to its exported directory; no original workdirs or model account are needed to inspect its verdict.

`run` automatically appends an invocation to `manifest.json` before scheduling runs. It records command templates, harness versions/config hashes, referenced repository overlay files, task hashes, trial/job settings, and platform/Python/Node versions. Keep this provenance with the run index.

## What a result can and cannot claim

- **Correctness ceiling:** if both arms pass every run, the warning says the tasks cannot distinguish correctness. Equal passing checks do not establish general reliability or comprehensive safety.
- **Inherited context:** use `state_template` (above) for every stateful arm. Otherwise `compare` warns `operator state not isolated`, and the result partly reflects the operator's personal instructions, settings and MCP servers. Isolation still leaves provider-side state (account, rate limits, server-side caching) and anything the harness reads outside its state root.
- **Cache and provider load are not controlled.** Concurrency, account limits, warm prefixes, and remote load can change token/time observations. Report conditions and repeat experiments rather than treating a small sample as universal superiority.
- Unknown regression/verification fields are reported as warnings, not filled with zero. Verification detection is a tool-sequence signal, not proof of all safety properties. Edits are `edit`/`write` calls plus repository writes made through `bash`: redirects, `tee`, `cp`/`mv`, `sed -i`, `patch`/`git apply`, and heredoc or inline scripts that call file-writing APIs. Writes outside the workdir and scratch files the same command deletes are ignored; shell writes to absolute paths inside the workdir are missed. Metrics stored in `runs.jsonl` keep the signal recorded at run time; bundles published before this change show `bash`-only runs as unknown.

## Hard task tier

The original six tasks reached a correctness ceiling in published experiments. Four original `hard-*` tasks add algorithmic constraints, interacting defects, seeded differential checks, and regression traps. They are not copied LeetCode exercises: they test repository debugging and implementation as well as algorithms, without intentionally reusing public problem statements.

| Task | Challenge |
| --- | --- |
| `hard-segment-tree` | Compose lazy assignment/addition correctly; preserve logarithmic range queries and threshold search |
| `hard-expr-eval` | Repair precedence, chained comparisons, floored arithmetic, and positioned errors across parser modules |
| `hard-line-diff` | Produce minimal edits, unified hunks, and applicable patches; avoid quadratic work on sparse large diffs |
| `hard-dep-resolver` | Resolve version constraints with deterministic backtracking, rollback, and legal dependency cycles |
| `tb-wal-recovery` | Preserve acknowledgment and replay frontiers across out-of-order flushes, segment rotation, gaps and duplicate LSNs |
| `tb-mvcc-compaction` | Reclaim obsolete versions without losing published reads, live snapshots or tombstones while prepared writes await publication |

The four original tasks carry `tags = ["hard"]`; the two `tb-*` tasks additionally carry `terminal-bench-adapted`. All have a 30-minute agent timeout. Select task IDs explicitly to pin a tier. `run` without `--task` includes six controls, four original hard tasks, the two adaptations and two development challenges, but excludes tasks tagged `heldout`. Existing task files and published bundles are unchanged; pin the original six IDs when reproducing an older experiment.

Run just the hard tier without model calls:

```sh
python -m bench --config benchmark-reference.toml --results results/hard-reference run --harness reference-a reference-b --task hard-segment-tree hard-expr-eval hard-line-diff hard-dep-resolver tb-wal-recovery tb-mvcc-compaction --trials 3 --jobs 16
```

For an actual harness comparison, use your matched-model config and arm names with the same explicit task list. Those runs spend model usage. Use serial alternating pairs for latency comparisons.

Calibration established that every starting repo fails and every reference passes. Visible-only bug fixes still fail hidden checks; naive alternatives fail performance guards. Seeded solution suites passed three repeated runs, and the full ten-task reference pipeline passed 60/60 runs at `--jobs 12`. Performance limits allow substantial local reference headroom but remain machine-dependent. **Model difficulty is not yet measured**: paid trials must establish whether these tasks reduce the correctness ceiling. Original tasks do not guarantee absence from future model training.

The two `tb-*` fixtures are newly authored, offline JavaScript adaptations inspired by Terminal-Bench v4.0.0's [WAL recovery](https://github.com/harbor-framework/terminal-bench/tree/v4.0.0/tasks/wal-recovery-ordering) and [MVCC compaction](https://github.com/harbor-framework/terminal-bench/tree/v4.0.0/tasks/mvcc-lsm-compaction) tasks. Attribution, the upstream canary and Apache-2.0 license accompany each fixture. They model durability/publication in memory: they do not exercise real filesystem crashes, Python/C++ implementations or the original verifier, and their results are **not Terminal-Bench scores**. Both starting repos fail visible/full checks; references pass 11 WAL and 18 MVCC checks. A two-arm, four-trial reference grid passed 16/16 runs with `--jobs 16`, with no regressions. These checks establish fixture correctness, not difficulty for a model.

## Adding a task

Create a directory under `tasks/` with this layout:

```text
tasks/<id>/
  task.toml       # id, title, category, timeout_sec, check argv list
  prompt.md       # task given to the agent
  repo/          # starting source and visible tests
  hidden_tests/  # behavioral tests added only for grading
  solution/      # reference files overlaid on repo/
```

Rules:

- Hidden tests must check only behavior stated in the prompt or source documentation; do not demand undisclosed features.
- Include regression traps that already pass on the starting repo, alongside tests for the requested change. The starting repo must fail overall; the reference solution must pass visible and hidden checks.
- Keep tests deterministic, self-contained, and bounded; avoid live services, model calls, or network dependencies.
- Give tests unique **top-level** names so TAP-based regression attribution is unambiguous.

Then validate all tasks without agents:

```sh
python -m bench.validate_tasks
```

Current tasks:

| Task ID | Category | Title |
| --- | --- | --- |
| `bugfix-duration` | bugfix | Parse complete compound durations |
| `bugfix-invoice` | bugfix | Repair cent rounding and ordered invoice discounts |
| `debug-cache-race` | debug | Diagnose stale writes and poisoned cache flights |
| `debug-limiter` | debug | Diagnose hanging asynchronous limiter tests |
| `feature-csv-stream` | feature | Implement an incremental CSV parser |
| `feature-lru` | feature | Implement a bounded least-recently-used cache |
| `hard-segment-tree` | debug | Repair lazy range updates in a segment tree |
| `hard-expr-eval` | bugfix | Fix Python-compatible arithmetic in a multi-module evaluator |
| `hard-line-diff` | feature | Implement minimal line diff with unified hunks and patching |
| `hard-dep-resolver` | debug | Diagnose missed solutions in a dependency resolver |
| `tb-wal-recovery` | debug | Repair asynchronous WAL durability, acknowledgment and recovery ordering (adapted) |
| `tb-mvcc-compaction` | debug | Preserve published and snapshot visibility during MVCC compaction (adapted) |
| `challenge-routing` | debug | Repository navigation across request routing and authorization modules (development) |
| `challenge-journal` | debug | Interacting persistence and replay defects (development) |
| `challenge-recovery` | recovery | Interrupted local work and resumption (held-out) |
| `challenge-safety` | safety | Local data preservation and denied operations (held-out) |

## Adding a harness

Add an arm under `[harnesses.<name>]` in your TOML config. `command` and `version_command` are argument lists, not shell strings. Pass the task using `{prompt}` and direct session output to `{session_dir}` where the CLI supports it; see the existing templates before choosing flags.

Every kind receives benchmark wall time, exit/timeout tracking, visible/hidden grading, regression checks, and prohibited-edit detection. Session adapters in [bench/sessions.py](bench/sessions.py) supply these additional metrics when their source records exist:

| Kind | Session metrics |
| --- | --- |
| `omp` | Input/output/cache tokens, cost, requests/tool counts, compactions, model time, subagent and auxiliary usage, edit/verification signals; completion/retries for direct `--mode json` commands. |
| `pi` | Input/output/cache tokens, cost, requests/tool counts, compactions, auxiliary usage, edit/verification signals, stream completion/retries; no model-time telemetry. |
| `claude` | Input/output/cache tokens, tool/request counts, compactions and subagent count from sessions; cost/API time and final result from stdout. Auxiliary and edit/verification signals are unknown. |
| `codex` | Input/output/cached tokens, approximate turn counts, tool counts, compactions and final message from sessions. Cost, model time, auxiliary usage and edit/verification signals are unknown. |
| `none` | No session/model metrics; useful for deterministic pipeline checks. |

Missing metrics remain unknown. Ensure the CLI emits the expected records and that sessions can be attributed to the run; do not mistake a missing usage stream for a free or zero-token solution.
