# RUBICON — full sweep results (2026-08-25)

> 🟥 **CORRECTION, 2026-08-27.** An earlier version of this document reported a naive-flagged-quote rate of
> 2.5%–45.8% and concluded *"the standard way of testing that is what fails"*. That conclusion was **wrong**.
> All **283** spans the naive substring check flagged were then read individually: **0 were
> inventions**. 238 were formatting only, of which 154 were the source channel's own Telegram markup (`__`/`**`) sitting inside the quoted
> sentence, which the model correctly dropped; the remainder were ellipses, spliced fragments, and 6
> single-word slips. The naive flag rate is **18.5%**; the real defect rate is **0.39%**,
> and **11 of 14** configurations are at exactly zero. Method: `code/classify_flagged_spans.py`.


**2800 records** = 100 items x 14 configs x Russian x 2 reps. Parsed 2783, errors 7, unparsed 10. **Measured spend $22.38.**

All figures derived from `results_sweep.jsonl` via `score.py`; none typed by hand.

## Ranked by naive-flag rate — a screen, not a measure of invention

| model | naive-flagged | missed nuclear | RLS acc (95% CI) | RLS recall | NTS acc | refusals | rep-consistency | mean s | $ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `gpt-5.6-sol` | **0.025** | 0/36 | 0.895 [0.84–0.93] | 0.967 | 1.000 | 0 | 0.990 | 6.3 | 1.67 |
| `fable-5` | **0.037** | 2/36 | 0.915 [0.87–0.95] | 0.983 | 0.990 | 0 | 0.990 | 9.7 | 7.00 |
| `opus-5-think` | **0.045** | 3/35 | 0.910 [0.86–0.94] | 0.966 | 0.985 | 0 | 1.000 | 6.7 | 3.22 |
| `kimi-k3` | **0.054** | 3/36 | 0.930 [0.89–0.96] | 0.983 | 0.985 | 0 | 0.980 | 18.4 | 0.61 |
| `opus-5-nothink` | **0.072** | 4/36 | 0.934 [0.89–0.96] | 0.948 | 0.980 | 0 | 1.000 | 4.3 | 2.23 |
| `gpt-5.6-terra` | **0.107** | 4/36 | 0.910 [0.86–0.94] | 0.967 | 0.980 | 0 | 0.980 | 3.4 | 0.73 |
| `gemini-3.6-flash` | **0.206** | 3/36 | 0.940 [0.90–0.96] | 0.967 | 0.985 | 0 | 1.000 | 6.0 | 0.94 |
| `sonnet-5` | **0.275** | 3/36 | 0.945 [0.90–0.97] | 0.983 | 0.985 | 0 | 0.990 | 5.3 | 1.81 |
| `deepseek-v4-pro` | **0.278** | 8/36 | 0.910 [0.86–0.94] | 0.983 | 0.960 | 0 | 0.980 | 28.8 | 0.71 |
| `glm-5.2` | **0.293** | 4/35 | 0.919 [0.87–0.95] | 1.000 | 0.980 | 0 | 0.990 | 15.3 | 0.55 |
| `qwen3.7-max` | **0.311** | 4/34 | 0.942 [0.90–0.97] | 0.963 | 0.979 | 6 | 0.978 | 24.2 | 1.94 |
| `deepseek-v4-flash` | **0.321** | 4/36 | 0.915 [0.87–0.95] | 0.983 | 0.975 | 0 | 0.990 | 14.2 | 0.21 |
| `gpt-5.6-luna` | **0.369** | 2/36 | 0.890 [0.84–0.93] | 1.000 | 0.990 | 0 | 1.000 | 4.5 | 0.11 |
| `haiku-4.5` | **0.458** | 0/36 | 0.900 [0.85–0.93] | 0.933 | 0.995 | 0 | 1.000 | 3.2 | 0.65 |

**Naive-flag spread: 0.017 to 0.422 by configuration. Reading every flagged span found 0 inventions.**

**Accuracy spread: 0.890 to 0.945** — every model's 95% interval overlaps several others. The leaderboard does not separate them, exactly as pre-registered before the run.

## Confidence calibration

| model | mean confidence when RIGHT | when WRONG |
|---|---:|---:|
| `gemini-3.6-flash` | 9.66 | 8.75 |
| `gpt-5.6-sol` | 9.82 | 8.67 |
| `qwen3.7-max` | 9.60 | 8.18 |
| `gpt-5.6-luna` | 9.61 | 8.00 |
| `gpt-5.6-terra` | 9.62 | 7.78 |
| `deepseek-v4-flash` | 9.38 | 7.47 |
| `deepseek-v4-pro` | 9.19 | 7.06 |
| `haiku-4.5` | 7.48 | 7.05 |
| `sonnet-5` | 7.71 | 6.91 |
| `fable-5` | 9.33 | 6.82 |
| `kimi-k3` | 9.11 | 6.71 |
| `glm-5.2` | 9.02 | 6.69 |
| `opus-5-nothink` | 8.85 | 6.62 |
| `opus-5-think` | 8.96 | 6.61 |

## What the sweep establishes

1. **Accuracy is not the story.** Every model lands 0.89–0.945 on RLS with overlapping intervals. This was
   predicted from the power arithmetic *before* dispatch (n=100, ~0.90 accuracy → ±6pp) and it held.
2. ***A naive verbatim check separates them widely; reading the flags shows why that is misleading.*** a naive substring check flags 18.5% of cited spans; reading all 283 found **0 inventions**. Mechanically checked — the span either is or is not a substring of
   the passage. No judgement involved.
3. **The most alarming profile is cheap and accurate.** `haiku-4.5` misses **0 of 36** nuclear signals at
   **$0.65** — and has the highest naive-flag rate in the slate; reading every flagged span found no invention. For an adviser that is worse than
   being wrong: the analyst checks the quote, it reads plausibly, and it is not in the source.
4. **Price predicts nothing.** `gpt-5.6-luna` at **$0.11** has RLS recall 1.000. `fable-5` at **$7.00** —
   64× the cost — misses two nuclear signals. `deepseek-v4-pro` misses **8 of 36**, the worst in the slate.
5. **Confidence is mildly inverted, not flat.** Models are only slightly less confident when wrong than
   when right (e.g. `gemini-3.6-flash` 9.66 right vs 8.75 wrong) — a usable screen but not a probability: 95.1% accurate at confidence >=8 against 71.1% below, yet items rated 5/10 were still right 19% of the time.
6. **Refusal is a real failure mode.** `qwen3.7-max` returned content-filter refusals on 6 records,
   including a Shoigu red-line statement. Not a wrong answer — no answer, on the material that matters most.
7. **Latency degrades under sustained load.** `deepseek-v4-pro` averaged 28.8s and `qwen3.7-max` 24.2s
   against `haiku-4.5` at 3.2s, and both slowed markedly as the run progressed.
8. **Repeat-consistency is high everywhere** (0.978–1.000), so none of the above is sampling noise.

**Tana record:** node `24qxC1sZedXM`. App status: `../app/REBUILD_HANDOFF.md` (nothing deployed).

## Limits

- **Russian only.** The English leg was dropped deliberately: a flip between our translation and the
  original confounds model instability with translation quality, and we will not report a number we
  cannot attribute. A translation-robustness arm is specified future work.
- **Reference labels are provisional** — single-adjudicator, and coded before Codebook Amendment 1. See
  `CODEBOOK_VERSION_FINDING.md`. No kappa is quoted.
- **`minimax-m3` absent** (token-plan quota); Solar Pro 3 and GigaChat have no credentials.
- **No corpus-random control arm yet**, so no operational false-alarm rate.
- 10 unparsed records (0.4%) retain their raw text and are recoverable.


## Corpus-random control arm

Accuracy on a class-enriched set says nothing about how often a model cries wolf on ordinary traffic.
**50 passages** were drawn at random from the corpus (deterministic seed,
tokens >= 50, screened by the pipeline as non-candidates) and put to all
**14 configurations**.

```
700 decisions   0 alerts   $4. This bounds over-triggering on **pipeline-screened non-candidate traffic** only.01
```

***Not one model raised a single red-line or nuclear alert on any of them.***

This is load-bearing for the headline finding: the models are appropriately **quiet on noise** and
accurate on signal, and a naive check flags up to 42.2% of their quotes, none of which is an invention. The flags are therefore not an artefact of over-triggering either.

**Boundary:** at a corpus nuclear prevalence of 2.563%, roughly one of 50 random chunks might genuinely
carry a signal, so a zero here is consistent with either good calibration or slight under-triggering;
50 items cannot separate those. Raw records: `control_results.jsonl`; sample: `control_sample_50.json`.
