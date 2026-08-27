# RedLineBench — red-line & nuclear-signal detection on real Russian official statements

> 🟥 **CORRECTION, 2026-08-27.** An earlier version of this document reported a naive-flagged-quote rate of
> 2.5%–45.8% and concluded *"the standard way of testing that is what fails"*. That conclusion was **wrong**.
> All **283** spans the naive substring check flagged were then read individually: **0 were
> inventions**. 238 were formatting only, of which 154 were the source channel's own Telegram markup (`__`/`**`) sitting inside the quoted
> sentence, which the model correctly dropped; the remainder were ellipses, spliced fragments, and 6
> single-word slips. The naive flag rate is **18.5%**; the real defect rate is **0.39%**,
> and **11 of 14** configurations are at exactly zero. Method: `code/classify_flagged_spans.py`.


**What should a decision-maker trust a model to do here, and what should they not?**

***The models do not invent quotations. A naive check says they do.***

Fourteen frontier configurations judged 100 real Russian official statements, twice each — 2,800 scored
decisions for $22.38. On the judgement itself they are **statistically indistinguishable**: every model
lands between 0.890 and 0.945 red-line accuracy, across a 64× price range. But each model must also quote
the span of text justifying its call, and we check mechanically whether that quote exists in the passage.

> **Two denominators, one name.** The table below reports the naive-flag rate **per record** (2.5%–45.8%): the share of scored decisions carrying at least one flagged span. Elsewhere in this repository the same check is reported **per span** (18.5% overall, 1.7%–42.2% by configuration): the share of the 1,532 individually cited spans that the substring test did not locate. Both are correct; they range over different things. **Neither is a rate of invention — that rate is zero.**

| | naive-flag rate | missed nuclear | cost |
|---|---:|---:|---:|
| GPT-5.6 Sol | **2.5%** | 0/36 | $1.67 |
| Claude Fable 5 | 3.7% | 2/36 | $7.00 |
| DeepSeek V4 Pro | 27.8% | **8/36** | $0.71 |
| GPT-5.6 Luna | 36.9% | 2/36 | **$0.11** |
| Claude Haiku 4.5 | **45.8%** | **0/36** | $0.65 |

**A wide spread in how much source markup each model strips when it quotes — and, on inspection, no spread at all in whether it invents.** Claude Haiku 4.5 misses no
nuclear signal at all, for 65 cents, and has the highest naive-flag rate in the slate; reading every flagged span found no invention.

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
| `results/` | **all 3,500 per-decision records** (2,800 benchmark + 700 control) with rationales, confidences, evidence spans and verbatim checks; plus derived scores |
| `RESULTS.md` | the measured findings |
| `REPRESENTATIVENESS.md` | how the sample matches the corpus, and where it does not |
| `CODEBOOK_VERSION_FINDING.md` | how the benchmark was nearly run on a superseded codebook |

## Reproducing

> **All three scripts run from a clean checkout.** `code/score.py` and `code/score_sequential.py` regenerate the published scores byte-identically, and `code/build_app_data.py` rebuilds the dashboard payload from `data/benchmark_100.json`. It formerly read passage text from an unreleased reference file and so could not run outside the project; it now reads the published benchmark, and the private set is an optional override for the wider 298-item pool only.

```
export CREDENTIALS_ENV=~/.rubicon.env     # your own provider keys; none are in this repo
python code/run_bench.py probe            # verify reachability and model ids
python code/run_bench.py run --reps 2 --langs ru --workers 14 --budget 90
python code/score.py
```
Append-only and resume-capable: re-running skips completed `(model, chunk, lang, rep)` work.

### Rebuilding the dashboard

The page at <https://rubase.org/redline-eval/> is generated from `results/` and `data/` — nothing on
it is typed by hand — and the route is published:

```
git archive HEAD | tar -x -C /tmp/x
cd /tmp/x/site && DEPLOYED_PAGE=app/index.html bash bench/rebuild.sh
```

It runs five gates and **refuses to finish** if any fails: the app audit; a numeric reconciliation of
every figure in the page source against `results/`; a rendered reconciliation in a real browser of
every figure a reader *sees* against the payload the page loads; an adversarial acceptance suite for
each checker (**20** and **14** reconstructed defects, each of which must be caught); and a byte
comparison against the deployed page. See [`site/README.md`](site/README.md) for why the two
acceptance suites exist — every gate here was, at some point, reporting success while doing nothing.

## The sequential arm

> 🟥 **Corrected 2026-08-27.** An earlier version of this arm cut passages to 4,000 characters, which removed the nuclear signal from three of the seventeen timelines; the models correctly reported no nuclear content and were scored as misses. The sampler now passes passages whole and the affected decisions were re-run. Figures below are post-repair.
 — does a raised alert ever come down?

A static benchmark asks *is this passage a nuclear signal?* It cannot ask the question a
decision-maker actually faces: **this speaker has been talking for weeks — is what they just said
different?**

So we built a second arm. Each of **17 sequences** is **8
real statements by one speaker in chronological order**, with a gold nuclear signal at position
**6** and *screened* negatives either side (`is_relevant = false` from the pass
covering all 296,381 corpus chunks — the negatives are verified, not assumed). At each step the model
sees the timeline so far **including its own earlier calls**, and sets an alert level: NONE, WATCH or
NUCLEAR. It may raise or lower it freely.

**816 decisions, $6.59.**

| configuration | caught | cry-wolf before the signal | stuck high after catching | naive-flagged span |
|---|---|---|---|---|
| gpt-5.6-sol | 14/17 | 3.5% | 3.6% | 0.0% |
| haiku-4.5 | 14/17 | 3.5% | 17.9% | 36.4% |
| deepseek-v4-pro | 13/17 | 2.4% | 7.7% | 7.5% |
| opus-5-think | 13/17 | 2.4% | 3.8% | 2.8% |
| fable-5 | 10/17 | 2.4% | 5.0% | 5.8% |
| gemini-3.6-flash | 8/17 | 1.2% | 0.0% | 26.1% |

### The finding

**Static accuracy separates these six configurations by 4.5 points. Catch rate separates them by 35.3
— 7.8× wider — and the ranking inverts.** The most accurate model on the static task catches the
fewest live signals. Some raise an alert and never stand down.

That is a result about *evaluation design*, not only about models: the conventional framing was
hiding the differences that matter when a model is watching a situation develop.

### Honest shape

Conversation history is carried **in the prompt** rather than as multi-turn API messages. The model
conditions on its own prior commitments, which is the property under test, but this is not a
true multi-turn or agentic harness and should not be described as one.

### Reproducing

`data/sequences.json` contains the full sequences including passage text, so the arm is reproducible
without database access. `code/build_sequences.py` regenerates them from the corpus if you have one.

```
python code/run_sequential.py --budget 35
python code/score_sequential.py results/results_sequential.jsonl
```


## The correction that matters most

This benchmark originally reported a **naive-flagged-quote rate of 2.5%–45.8%** and concluded that model justifications could not be trusted. **That was wrong, and the error was ours, not the models'.**

The check was a substring test: is the cited span present in the passage? It is a reasonable *screen*. It is not a verdict. We went back and read **every one of the 283 flagged spans**:

| what the flag actually was | n | share |
|---|---:|---:|
| Formatting only — our checker's fault | 238 | 84.5% |
| Ellipsis joins and spliced fragments | 33 | 11.3% |
| Sloppy edges, still traceable | 6 | 2.1% |
| Real text error, meaning intact | 6 | 2.1% |
| **Invented content** | **0** | **0.0%** |

The dominant category is the source channel's own Telegram markup (`__bold__`, `**bold**`) sitting *inside* the sentence the model quoted. The model dropped it, as any careful reader would. Our checker called that an invention.

**The usable finding is methodological:** a naive verbatim check flags **18.5%** of cited spans on this corpus, and the invention rate among them is **0**. If you are building a citation-faithfulness eval, normalise source markup and whitespace, allow ellipses and splices, and **read your positives before you publish a rate**.

Reproduce: `python code/classify_flagged_spans.py` against `results/flagged_span_categories.json`, which carries the category and the reason for every flagged span.

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
