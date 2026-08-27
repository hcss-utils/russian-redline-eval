# RUBICON — stratified pilot results (2026-08-25)

**20 items × 6 configs × RU × 1 rep = 120 calls, 119 parsed, 0 errors.**
Sample: `pilot/pilot20_stratified.json` (13 RLS-positive, 8 NTS-positive, 5 pure negatives), drawn
seeded from `sample_representative_100.json`. Prompt: `prompt/system_v2.md`. Raw: `pilot/pilot20_v2.jsonl`.

## Headline

| model | RLS inclusive | RLS derived-strict | NTS inclusive | NTS derived-strict |
|---|---:|---:|---:|---:|
| gemini-3.6-flash | **0.90** | 0.65 | **1.00** | 0.90 |
| haiku-4.5 | **0.90** | 0.70 | **1.00** | 0.80 |
| opus-5-nothink | 0.89 | 0.68 | **1.00** | 0.84 |
| opus-5-think | **0.90** | 0.70 | 0.95 | 0.80 |
| gpt-5.6-sol | **0.90** | 0.60 | 0.95 | 0.85 |
| glm-5.2 | **0.90** | 0.65 | 0.95 | 0.75 |

**RLS recall is 1.00 for every model under the inclusive criterion**; under derived-strict it falls to
0.46–0.62.

## What this establishes

1. **The inclusive verdict is the scoring axis.** Derived-strict is a secondary diagnostic.
2. ***`gold_v2` is nominally STRICT but its positives are effectively INCLUSIVE.*** Adjudicators were
   already coding wider than the strict prompt demanded, so Amendment 1 codified existing practice rather
   than loosening the construct.
3. **Accuracy is compressed at ~0.90 RLS / 0.95–1.00 NTS across a 40× price range.** Haiku 4.5 matches
   GPT-5.6-sol and Gemini 3.6 Flash. On this evidence **price and capability do not predict performance
   on this task** — which is a more interesting result for a situation-room audience than a ranking, and
   it is the axis the full sweep should be powered to test.

## Naive-flag rate: 18 of 119 records (15%)

> 🟥 **Superseded reading.** These are spans a naive substring check did not locate. On the full run all 283 such spans were read individually and **none was an invention**; the flags are overwhelmingly source-channel markup.

Models quoting an "evidence" span that is **not a verbatim substring of the passage**. Designed as an
automatic-disqualification check; firing far above the assumed rate. Mechanically verified, not judged —
`run_bench.py::evidence_is_verbatim`. Likely the entry's second substantive finding, and it needs a
per-model breakdown in the full run.

**Tana record:** node `ntKKqlU2hUnO`. **Renamed:** the project is **RUBICON** (repo `rubicon`).

## Limits

- **n=20 items, 6 of 15 configs, Russian only, 1 repetition.** No English leg (translations do not exist
  yet), so nothing here speaks to language instability.
- Accuracy is against `gold_v2`, whose own status is documented in `CODEBOOK_VERSION_FINDING.md`:
  provisional, single-adjudicator, and coded before Amendment 1.
- The ~0.90 compression may be a ceiling artifact of a 20-item set; the 100-item sweep has the resolution
  to separate models if a real difference exists.
