# Intended use, and what this must not be used for

## What this measures

Whether a language model, shown a single passage of Russian official communication, correctly identifies
it as containing a red-line statement or a nuclear signal — **and whether the quotation it offers as
justification is actually present in the passage.**

## What it does not measure

- **Not escalation forecasting.** Nothing here predicts what any state will do.
- **Not intent or credibility.** The construct is a speech act. A statement can be coded a red line while
  being empty bluster; that is out of scope by design.
- **Not operational readiness.** A model scoring well here is not thereby fit to sit in a decision loop.

## The result most relevant to deployment

Accuracy does not separate these models, and **neither does faithfulness**. A naive substring check
flags their supporting quotations at rates from 1.7% to 42.2%, which looks like an order-of-magnitude
difference in honesty — but reading all 283 flagged spans found **zero inventions**. The spread measures
how much source-channel markup each model strips when it quotes, not whether it invents. What does
separate them, measurably, is behaviour over time: tracked across real speaker timelines the same
configurations separate 7.8x more widely than static accuracy, and the ranking inverts.

## Cautions

- **Do not use single-model output as a basis for escalation judgements.** The measured value of these
  systems here is triage and recall, not adjudication.
- **Verify every quotation programmatically.** This is a substring check and costs nothing. On this
  benchmark it changes the ranking entirely.
- **The reference labels are provisional** — single-adjudicator, and coded under a construct that has since
  been widened. Treat measured accuracy as agreement with a provisional reference, not as correctness.
- **The sample is not prevalence-representative.** Rare classes are deliberately over-sampled so they are
  measurable at all; alert rates computed here do not transfer to a live feed without reweighting.

## Dual use

This benchmark uses public statements to test whether AI systems read coercive signalling accurately. It
contains no operational, targeting or capability information. Its foreseeable misuse is the opposite of
its purpose: citing a model's score here as warrant for automating a judgement that should remain human.
