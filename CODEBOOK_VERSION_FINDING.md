# 🟥 The benchmark was nearly run on a superseded codebook

**Established 2026-08-25.** the project lead challenged a rationale I had given for a gold label. The challenge was
correct, and following it exposed a defect that would have invalidated the whole entry.

## What happened

The benchmark prompt (`prompt/system_v1.md`) was assembled from
`gold_certification/PRODUCTION_PROMPTS_gpt5mini_260725.txt` — the literal system prompt that produced
the model key. It is dated **25 July 2026**. It **predates both current codebook documents**:

| Document | Date | Status |
|---|---|---|
| `PRODUCTION_PROMPTS_gpt5mini_260725.txt` | 25 Jul | what v1 was built from — **superseded** |
| `RLS_NTS_CODEBOOK_SDS_260727.md` | 27 Jul | the project lead construct definition; positions on the eight exclusions |
| `CODEBOOK_AMENDMENT_1_INCLUSIVE_260729.md` | 29 Jul | INCLUSIVE construct + receiver-side limb |

The production prompt enforces eight exclusions. **The 27 July codebook drops or relaxes six of them**
and keeps only two hard exclusions — quoted speech, and domestic/non-policy-capable targets. Mirror-parity,
vague reaction ("all military-technical means"), open-ended conditionals, retrospective-but-forward-signalling,
and official-adjacent op-eds are all explicitly **included**: *"vagueness is a feature, not a disqualifier."*

Amendment 1 then adds the **receiver-side limb**: a statement is an RLS if a reasonable recipient could
plausibly read it as one, *"even if the sender's formulation is too vague to establish it directly."*
The amendment calls this *"the substantive move"* and warns it *"should be defended explicitly in the
paper, not smuggled in."*

## Two further errors this exposed

1. **An invented coding criterion.** I justified a gold label with "Medvedev has no operational
   authority." That appears in **no codebook**. It was lifted from the prose of the 12 August letter to
   an external contact and a second independent coder and restated as if it were a rule. The 27 July codebook says the
   opposite in principle: ***"We code the utterance, not the intention."*** Authority/seriousness is
   explicitly ruled **out of scope** (§0, and §2 rows 2-5, 8).
2. **`gold_v3_inclusive_260729` DOES NOT EXIST.** Amendment 1 §5 specifies a four-step plan — code the
   gold once to INCLUSIVE, freeze as `gold_v3_inclusive_260729`, derive `gold_v3_strict_260729` by
   filter, certify both. **None of it was executed.** Only `gold_v2_260726.csv` exists, which is the
   STRICT freeze the amendment designates as the prior state. So the reference labels are strict while
   the governing criterion has been inclusive since 29 July.

## The fix, and why it is better than reverting

`prompt/system_v2.md` is built from the 27 + 29 July documents. Rather than choosing between the two
constructs, it asks the **inclusive** question and requires the model to record precision flags
(`line_explicit`, `threat_explicit`) so that the **strict verdict is derived**:

```
strict = inclusive AND line_explicit AND threat_explicit
```

This follows the amendment's own architecture (§4): *"strictness is recoverable as a filter over an
inclusive base, whereas breadth is not recoverable from a strict base."* It lets us score against the
strict `gold_v2` while also reporting the inclusive signal.

## 🟥 SUPERSEDED CONCLUSION — corrected 2026-08-25 by a stratified pilot

**The section below reported that derived-strict beat the strict prompt 22/24 vs 19/24, and drew from it
the lesson that "a distinction placed at the GATE destroys information; the same distinction placed in a
FLAG keeps it and scores better." That conclusion was measured on THREE ITEMS, ALL OF THEM GOLD-N, and
it REVERSES once positives are included.** The caveat printed at the bottom of that section was correct
and should have blocked the conclusion rather than merely accompanying it.

**Corrected result** — 20 stratified items (13 RLS-positive, 8 NTS-positive, 5 pure negatives) x 6
configs, 119/120 parsed:

| model | RLS inclusive | RLS derived-strict | NTS inclusive | NTS derived-strict |
|---|---:|---:|---:|---:|
| gemini-3.6-flash | **0.90** | 0.65 | **1.00** | 0.90 |
| haiku-4.5 | **0.90** | 0.70 | **1.00** | 0.80 |
| opus-5-nothink | 0.89 | 0.68 | **1.00** | 0.84 |
| opus-5-think | **0.90** | 0.70 | 0.95 | 0.80 |
| gpt-5.6-sol | **0.90** | 0.60 | 0.95 | 0.85 |
| glm-5.2 | **0.90** | 0.65 | 0.95 | 0.75 |

**RLS recall under the inclusive criterion is 1.00 for EVERY model.** Under derived-strict it collapses
to **0.46-0.62**. Accuracy ~0.90 inclusive against ~0.65 derived-strict.

***The substantive finding: `gold_v2` is nominally the STRICT freeze, but its positives largely do NOT
satisfy explicit-boundary AND explicit-threat.*** The human adjudicators were already coding closer to
INCLUSIVE than the strict prompt demanded. Amendment 1 was therefore not loosening the construct — it was
**codifying what the coders were already doing**. the project lead's position is confirmed against the labels themselves.

**Consequence for the benchmark:** the **inclusive verdict is the headline metric**. Derived-strict is
retained as a secondary diagnostic (`opus-5-think` leads it at 0.70 / 0.62 recall), not as the scoring axis.

**The real lesson, replacing the one drawn above:** ***a metric computed on one class only is not a
metric.*** Accuracy over negatives measures false-positive avoidance and nothing else; it cannot rank
designs whose difference is mostly in recall. Do not draw a design conclusion from a sample that contains
no positives, however clearly the caveat is stated.

## Original (superseded) section — retained for provenance

24 comparable model×item pairs (8 configs × 3 items), scored against `gold_v2` (strict-coded):

| Prompt | Agreement |
|---|---:|
| v1 — strict, six exclusions | 19/24 |
| v2 — inclusive, raw verdict | 16/24 |
| **v2 → strict derived from flags** | **22/24** |

On the Medvedev Ramstein passage (`105309`, 19 Jan 2023) all 8 models return RLS=Y under the inclusive
criterion — correctly, on the receiver-side limb — and six then flag it as neither line- nor
threat-explicit, so derived-strict returns N and matches gold. The strict prompt discarded the item at
the gate and was wrong more often.

***The six exclusions encoded real distinctions. Placing them at the gate destroyed information and cost
accuracy; placing the same distinctions in flags kept the information and gained accuracy.***

Side effect: v2 is **4,654 chars against v1's 21,702** — a 78% reduction, because the strict codebook
was mostly exclusion text. Input cost falls accordingly.

🟥 **Binding caveat: all three pilot items are gold-N.** The comparison measures false-positive
avoidance only and says nothing about recall — the direction where the inclusive criterion should matter
most and might do worse. 24 pairs on three negatives is a hint, not a finding. The 100-item sweep carries
59 positives and settles it.

## The generalisable lesson

***A frozen prompt is a codebook snapshot, and a codebook has a version.*** The production prompt was the
right file for reproducing the model key and the wrong file for asking the current question. Nothing in
the pipeline asserted a codebook date, so a two-month-old construct was about to be presented publicly as
the project's definition. Candidate gate: any frozen prompt must name its source codebook files and fail
if a newer codebook document exists in the same directory.

**Recorded as:** gate catalogue `#141` (candidate) in `claude-hooks/RULES_AS_GATES.md`; Tana node `Vh7O-bKXPEj5`.

## Evidence

`pilot/pilot_v1_strict_openweight.jsonl`, `pilot/pilot_v1_strict_anthropic.jsonl`,
`pilot/pilot_v2_inclusive.jsonl` — raw records with usage, verdicts, rationales and verbatim-evidence checks.
