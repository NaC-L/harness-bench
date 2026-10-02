# OMP first-request attribution

## Why

Pi uses ×0.44–0.59 of OMP's total tokens per correct solution in every head-to-head
(Sol, Kimi, four-arm). OMP's first request is the most consistent difference
(Sol: median 4,034 vs 1,423 input tokens). Bundled payload changes never shrank it.
Attribute it first, then cut only what is provably dead for the session.

## Step 1: capture (done, zero model usage)

`python -m bench --config <toml> capture --harness <arms> --task bugfix-duration --out results/<dir>`
(see README). Tables: [breakdown-ultra.txt](breakdown-ultra.txt),
[breakdown-pi-omp-opus.txt](breakdown-pi-omp-opus.txt). 2026-10-02, Opus 5.5 arms.

OMP source baseline (`omp-base`, 27cdf191b, pinned template, inline off): 15,906 chars.
Real runs of this arm had a median first-request input of 6,963 tokens, so roughly
2.3 chars/token here (includes provider tool framing; rough, not a tokenizer).

| Component | chars | Notes |
| --- | ---: | --- |
| Tool descriptions + schemas | 5,625 | read 1,753, edit 2,119, bash 1,264, write 489 |
| `# 5. Verify` | 1,336 | load-bearing; keep |
| `# Internal URLs` | 1,068 | lists `agent://`, `proc://`, `ssh://`, `issue://`/`pr://`, `mcp://`, `omp://` with no task tool, MCP server or SSH host mounted |
| `<contract>` + `<completeness>` + `<yielding>` + 3× `<critical>` | ~2,130 | policy; overlapping wording, not dead |
| `# Engineering` | 800 | |
| User message (task + system reminder) | 1,265 | same across arms |

`read`'s description documents SQLite, archives, executables, PDFs and video
(~800 chars) for a four-tool coding session. Pi's whole request was 6,760 chars
(system ~2,800, tools ~2,800).

Inline descriptors do not shrink the first request: they move ~5.1k chars of tool docs
from schemas into the system prompt (+2.0%). Their earlier token win is behavioural,
not size.

Leak found: the unpinned `omp-opus` arm (installed OMP) sent the operator's
`~/.omp/SYSTEM.md` instead of OMP's default prompt (11,073 chars total). Published
unpinned OMP arms' median first-request tokens match that (opus-vs-sol `omp-opus`
4,614 vs pinned `omp-base` 6,963). Treat every unpinned OMP arm as "OMP + operator
SYSTEM.md" until re-captured.

## Step 2 outcome (2026-10-02): little dead text

Source inspection (upstream main 3b003d878) falsified the "~1.7k dead chars" estimate.
Internal URLs already gate on session facts via `promptDoc(host)`: skills, rules,
memory, security, `cfg://` on config; `ssh://` and `issue://`/`pr://` on `ssh`/`gh`
being on PATH (both are on this machine). `read`'s SQLite/archive/PDF/video lines
describe handlers that are always mounted; executables already gate on
`ida.available`. Truly unmounted text is `mcp://` without MCP servers and `agent://`/
`history://` in a top-level session with no task tool: ~250 chars, under 1% of total
tokens/correct. Not worth a source change or a grid.

Progressive disclosure prototype (branch `perf/read-mode-disclosure`, worktree
`../omp-read-modes`, from origin/main 3b003d878, uncommitted): `read`'s description
names SQLite/archives/video in one line; the selector syntax moves into the bare
read's output (header line on SQLite table lists and archive root listings, so head
truncation keeps it; footer on the video preview grid). Capture: `read` description
1,522 -> 1,327 chars, request 15,261 -> 15,066 (-1.3%); nothing else changed. ~85
tokens/request, under 1% of total tokens/correct. Not worth a grid; keep only if the
shorter description is wanted for clarity. Bottom line: OMP's first-request gap to Pi
is mostly load-bearing policy and tool docs, not dead text.

Note: the prompt varies by machine (`ida.available`, `ssh`/`gh` on PATH). Capture on
the machine that runs the grid.

## Step 3: non-inferiority grid (for any future size cut)

Expected saving per cut is below the comparator's 10% margin (prefix ~43% of total
tokens/correct at ~7.2 requests/run), so a grid only checks for harm:
baseline vs candidate source, Opus 5.5 high, pinned template, isolated state,
14 tasks × 5 trials, `compare --margin 0.1 --min-trials 5`; correctness/safety
non-inferior, edit errors, follow-up reads and requests not higher. Report the saving
from capture, the harm check from the grid.

## OMP bug: home `.omp` loaded as project config

`findNearestProjectConfigDir` (discovery/builtin.ts) walks from cwd to the repo root,
or to the filesystem root outside a repo, and accepts `~/.omp`. Any non-repo cwd under
home (all Windows `%TEMP%` workdirs) then loads `~/.omp/SYSTEM.md`, `RULES.md` and
`AGENTS.md` as *project* config, bypassing `PI_CODING_AGENT_DIR` and profiles. The
`.agent[s]` walk-up in discovery/agents.ts already skips home (issue #1116).

Fix: branch `fix/builtin-walkup-skips-home` (worktree `../omp-home-walkup`, from
origin/main 3b003d878, uncommitted): skip home and stop there, like agents.ts.
Regression test `test/discovery/builtin-home-walkup.test.ts` fails before, passes
after. Capture check: unpinned installed `omp` sent the operator prompt (11,073
chars); the fixed source sent OMP's default prompt (15,261 chars).

## Reruns without the operator SYSTEM.md (2026-10-02)

Same tasks, trials, flags and isolated state as the originals; only the OMP binary
changed to source with the walk-up fix (`benchmark-*-walkup.toml`, results under
`results/walkup-*`, local only). Capture preflight confirmed OMP's default prompt for
the Anthropic arms; Sol/Kimi preflights passed with token metrics. Different worker
counts than the originals; latency is not comparable across them.

| Comparison | Original (with operator SYSTEM.md) | Rerun (stock OMP prompt) |
| --- | --- | --- |
| Inline descriptors on Opus, 6 tasks × 4 | `better`: tokens ×0.51 (0.44–0.61) | `inconclusive`: tokens ×1.05 (0.94–1.16), uncached ×1.12 (1.02–1.22); 24/24 each |
| Sol → Opus on OMP, 10 × 3 | tokens ×2.02, median time ×0.37 | tokens ×1.25 (1.03–1.53), uncached ×0.78 (0.71–0.85), median time ×0.33 (0.30–0.44); 30/30 each |
| OMP → Pi on Kimi, 10 × 3 | tokens ×0.59 (quota-filtered) | tokens ×0.44 (0.36–0.52), uncached ×0.83 (0.73–0.95); OMP 21/30, Pi 23/30 |

The Opus inline-descriptor win does not survive: it was a property of the operator
prompt, not of inline descriptors. Kimi: all six `hard-line-diff` attempts (3 per arm)
ended with provider HTTP 401 mid-run (per-run token expired); the comparator counted
them as solution failures. Excluding them, OMP 21/27, Pi 23/27; the other failures are
hidden-test failures (`debug-limiter` in both arms, `hard-dep-resolver` OMP 2/3).
