# omp-inline vs omp-baseline

Verdict: inconclusive (omp-inline vs baseline omp-baseline, margin 10%, min trials 3)

**No winner yet (inconclusive): uncached tokens per correct ×1.12 (95% CI 0.99–1.25) may be more than 10% worse; more trials needed (and 2 more).**

| Dimension | omp-inline vs omp-baseline | omp-baseline (baseline) | omp-inline (candidate) |
|---|---|---|---|
| correctness | same | 6/6 passed, 0 regression runs, 0 unfinished | 6/6 passed, 0 regression runs, 0 unfinished |
| tokens | uncertain | 58660 total / 16050 uncached per correct, 0 aux calls | 45048 total / 17986 uncached per correct, 0 aux calls |
| time | uncertain | median 65.0 s, p90 82.3 s | median 73.2 s, p90 82.3 s |
| safety | same | 0 timeouts, 0 tampered, verification 5/6 | 0 timeouts, 0 tampered, verification 5/6 |

## Efficiency ratios

Candidate/baseline, 95% bootstrap CI from 2000 resamples of runs within each task:

- total tokens per correct: ×0.77 (95% CI 0.67–0.88)
- uncached tokens per correct: ×1.12 (95% CI 0.99–1.25)
- median wall time: ×1.13 (95% CI 0.95–1.21)
- p90 wall time: ×1.00 (95% CI 0.90–1.23)

## Run classifications

| Arm | Success | Solution failure | Infrastructure failure | Unknown |
|---|---:|---:|---:|---:|
| omp-baseline | 6 | 0 | 0 | 0 |
| omp-inline | 6 | 0 | 0 | 0 |

## Per-task results

| Task | Arm | Passed/runs | Median wall s | Median total tokens | Median uncached tokens |
|---|---|---:|---:|---:|---:|
| challenge-journal | omp-baseline | 3/3 | 67.0 | 56834 | 16027 |
| challenge-journal | omp-inline | 3/3 | 72.8 | 45713 | 18663 |
| challenge-routing | omp-baseline | 3/3 | 62.9 | 64118 | 14884 |
| challenge-routing | omp-inline | 3/3 | 77.1 | 42915 | 18861 |

Per-task scorecards (all attempts retained):

| Task | Arm | Passed/runs | Total tokens/correct | Uncached tokens/correct | Median wall s | P90 wall s | Success / solution failure / infrastructure failure / unknown |
|---|---|---:|---:|---:|---:|---:|---|
| challenge-journal | omp-baseline | 3/3 | 52740 | 15945 | 67.0 | 70.2 | 3 / 0 / 0 / 0 |
| challenge-journal | omp-inline | 3/3 | 45454 | 18502 | 72.8 | 73.7 | 3 / 0 / 0 / 0 |
| challenge-routing | omp-baseline | 3/3 | 64580 | 16155 | 62.9 | 82.3 | 3 / 0 / 0 / 0 |
| challenge-routing | omp-inline | 3/3 | 44643 | 17471 | 77.1 | 82.3 | 3 / 0 / 0 / 0 |

Per-task point effects (descriptive only; no per-task winner or confidence claim):

| Task | Pass-rate difference (candidate − baseline, pp) | Total tokens/correct ratio | Uncached tokens/correct ratio | Median wall ratio | P90 wall ratio |
|---|---:|---:|---:|---:|---:|
| challenge-journal | +0.0 | 0.86 | 1.16 | 1.09 | 1.05 |
| challenge-routing | +0.0 | 0.69 | 1.08 | 1.23 | 1.00 |

## Setup

### Invocation 2026-10-01T07:24:17.596044+00:00

- Config: benchmark-omp-descriptors-opus.toml
- Trials/jobs: 3/4
- Alternate order: False; timeout: None
- Platform: Windows-11-10.0.26200-SP0
- Python: 3.14.3; Node: v22.20.0
- omp-baseline: kind omp, version omp/18.4.8, config hash dc74a41ef9ffdaf69634f60dd5cbaa2338c5a2c8bcfa1f7e3186ad7538caba82, state isolated from experiments/omp-isolated/agent
- omp-inline: kind omp, version omp/18.4.8, config hash b8c262832816126f8ba71b468c39878230459cc3f4fd164820ff4d24deaa1210, state isolated from experiments/omp-isolated/agent

Command template argv difference (differing elements only):
```json
{
  "omp-baseline": [
    "{benchmark_dir}/experiments/omp-descriptors/baseline.yml"
  ],
  "omp-inline": [
    "{benchmark_dir}/experiments/omp-descriptors/inline.yml"
  ]
}
```

Overlay omp-baseline: experiments/omp-descriptors/baseline.yml (sha256 f59dbc87108224ee8f4804ab9f3ed6a642d91b1053cd233095f270d7bfb541fd)
```
inlineToolDescriptors: "off"

```

Overlay omp-inline: experiments/omp-descriptors/inline.yml (sha256 9b2826130a7d102ce1eea20d822ce0b09a3d4bd3d020c9e15b8a4197a4da8264)
```
inlineToolDescriptors: "on"

```

Task ids and hashes:
- challenge-journal: 260621cfdaec
- challenge-routing: 8eee47a9f386


## Reasons

- uncached tokens per correct ×1.12 (95% CI 0.99–1.25) may be more than 10% worse; more trials needed
- median wall time ×1.13 (95% CI 0.95–1.21) may be more than 10% worse; more trials needed
- p90 wall time ×1.00 (95% CI 0.90–1.23) may be more than 10% worse; more trials needed

## Warnings

- correctness at ceiling: every run passed, so these tasks cannot distinguish correctness

## Reproduce

```console
python -m bench --config benchmark-omp-descriptors-opus.toml --results results/challenge-calibration-2026-10-01-rerun run --harness omp-baseline omp-inline --trials 3 --jobs 4 --task challenge-routing challenge-journal
python -m bench --config benchmark-omp-descriptors-opus.toml --results 'results\challenge-calibration-2026-10-01' compare --baseline omp-baseline --candidate omp-inline --margin 0.1 --min-trials 3 --format markdown
```

Run from the benchmark directory with the recorded config and tasks. The first command collects new trials in a fresh directory (compare it by pointing --results there); the second re-scores the runs in this report, and works on an exported bundle without model access.

## How to read this

Correctness and safety require non-inferiority (no extra failures or safety regressions). Tokens and time compare the 95% bootstrap interval of the candidate/baseline ratio with the 10% margin: worse if the whole interval is above it, better if an interval is wholly below it and no loss beyond it is possible, the same if it lies inside the band; otherwise the verdict is inconclusive. Infrastructure contamination makes a comparison inconclusive unless correctness or safety is measurably worse. Run classifications use explicit recorded evidence; missing legacy evidence is unknown, not infrastructure. Unknown ≠ 0; medians use known runs only. Tokens per correct solution include failed attempts. Per-task ratios and pass-rate differences are descriptive point effects, not per-task winners; aggregate bootstrap resampling is unchanged.
