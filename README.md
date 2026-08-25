# Red-line & nuclear-signal detection — a benchmark on real Russian official statements

**What should a decision-maker trust a model to do here, and what should they not?**

***You can trust the verdict. You cannot trust the reason given for it.***

Fourteen frontier configurations judged 100 real Russian official statements, twice each — 2,800 scored
decisions for $22.38. On the judgement itself they are **statistically indistinguishable**: every model
lands between 0.890 and 0.945 red-line accuracy, across a 64× price range. But each model must also quote
the span of text justifying its call, and we check mechanically whether that quote exists in the passage.

| | fabricated quote | missed nuclear | cost |
|---|---:|---:|---:|
| GPT-5.6 Sol | **2.5%** | 0/36 | $1.67 |
| Claude Fable 5 | 3.7% | 2/36 | $7.00 |
| DeepSeek V4 Pro | 27.8% | **8/36** | $0.71 |
| GPT-5.6 Luna | 36.9% | 2/36 | **$0.11** |
| Claude Haiku 4.5 | **45.8%** | **0/36** | $0.65 |

**An 18-fold spread in whether the justification is real, at equal accuracy.** Claude Haiku 4.5 misses no
nuclear signal at all, for 65 cents, and invents its supporting quote nearly half the time — for an
adviser that is worse than being wrong, because the analyst checks the citation, it reads plausibly, and
it was never said.

## Why real statements rather than scenarios

Diplomacy self-play, CSIS's 400 constructed scenarios, WarAgent's counterfactual 1914 and CivBench all
test models on **invented** situations. This tests them on things Russian officials actually said, in
Russian, at a known date, from an identified channel — Kremlin transcripts, Ministry of Defence and MFA
channels, State Duma and Federation Council records. The ambiguity is real rather than authored, and the
traps are real: Medvedev predicting that a nuclear power's defeat "may provoke" nuclear war is not the
same speech act as a red line, and the models split on it.

## What is here

| document | what |
|---|---|
| `CODEBOOK.md` | **what counts as a red line and a nuclear signal** — the operative construct given to every model |
| `REPRODUCIBILITY.md` | how to re-run, and what cannot be reproduced exactly |
| `INTENDED_USE.md` | what this measures, what it does not, and cautions for deployment |
| `LICENSE.md` | MIT for code, CC BY 4.0 for annotations and outputs, quoted public statements for the passages |
| `CODEBOOK_VERSION_FINDING.md` | how the benchmark was nearly run on a superseded construct |

| path | contents |
|---|---|
| `prompt/` | the frozen system prompt and user template, with hashes |
| `data/` | **`benchmark_100.json`** and **`control_50.json`** — passages WITH text, per-item SHA-256, channel, date, source arm and URL where the publisher exposes one; the 15 excluded contested items; corpus marginals; English reading aids |
| `code/` | sampler, model registry, runner, scorer, cost model |
| `results/` | **all 3,496 per-decision records** (2,800 benchmark + 696 control) with rationales, confidences, evidence spans and verbatim checks; plus derived scores |
| `RESULTS.md` | the measured findings |
| `REPRESENTATIVENESS.md` | how the sample matches the corpus, and where it does not |
| `CODEBOOK_VERSION_FINDING.md` | how the benchmark was nearly run on a superseded codebook |

## Reproducing

```
export CREDENTIALS_ENV=~/.rubicon.env     # your own provider keys; none are in this repo
python code/run_bench.py probe            # verify reachability and model ids
python code/run_bench.py run --reps 2 --langs ru --workers 14 --budget 90
python code/score.py
```
Append-only and resume-capable: re-running skips completed `(model, chunk, lang, rep)` work.

## What we did not measure, and do not claim

- **Russian only.** A verdict that flips between our translation and the original cannot be attributed to
  the model rather than the translation, so no language-robustness arm was run. English in `data/` is a
  reading aid; **no model ever saw it**.
- **Reference labels are provisional** — single-adjudicator, coded before the project's codebook amendment,
  no independent blind second pass returned. **No inter-rater kappa is quoted anywhere.**
- **Accuracy differences are not significant.** At 100 items the standard error is ≈±3 points. That the
  leaderboard would fail to separate the models was predicted from the power arithmetic *before* dispatch;
  it is reported as a null result, not a ranking.
- **Not prevalence-representative.** Corpus nuclear-signal prevalence is 2.563%; this sample is enriched
  ~7× so the rare class is measurable at all. Inverse-probability weights are given in
  `REPRESENTATIVENESS.md`.
- All models were called on **native APIs**, never an aggregating router — for open-weight models a router
  may silently serve a quantised or stale host, which would make the numbers unattributable.
