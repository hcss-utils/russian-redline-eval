# Codebook — what counts as a red line, and what counts as a nuclear signal

This is the operative construct definition used for the reference labels and given, verbatim in substance,
to every model. It is a **speech-act** construct: we code the utterance, not the speaker's intention. We
make no claim about whether Russian decision-makers actually hold red lines, whether they mean them, or
whether they are credible. Those are not answerable from text.

## The governing principle

The RLS/NTS decision is a **gate**, followed by a feature layer that grades nuance. **The gate therefore
errs toward inclusion**: anything the feature layer could characterise — vague, oblique, reciprocal,
retrospective — must not be excluded at the gate. Precision is recorded in flags, not by refusing the item.

*Breadth is not recoverable from a strict base: excluded items are never labelled at all, whereas a strict
construct can always be derived from an inclusive one by filtering.*

## RLS — Red-Line Statement

**RLS = Y** when a Russian official or official-adjacent statement articulates a **boundary** (behaviour
sought from or denied to a foreign party) together with **some adverse consequence** for non-compliance,
aimed at a plausibly identifiable **foreign, policy-capable actor**, so as to coerce or deter.

The consequence may be vague, oblique, reciprocal, unspecified as to domain, or retrospective-but-forward-
signalling. **None of those disqualify it.** Either limb suffices:

- **(a) Sender-side.** The speaker indicates, however imprecisely, some behaviour they seek to elicit from
  or deny to a foreign party, and attaches some adverse consequence to non-compliance.
- **(b) Receiver-side.** A reasonable recipient could plausibly read the statement as doing (a), even if
  the sender's formulation is too vague to establish it directly.

*Rationale for (b): a red line functions through interpretation. If Kyiv or Washington could reasonably
read a statement as a threat-bearing boundary, it operates as one whatever its drafting quality. Excluding
such items imports the analyst's standard of clarity into a phenomenon defined by its effect on the
recipient. This is the most contestable clause in the construct and is stated here explicitly rather than
buried.*

### Only two hard exclusions

1. **Quoted speech.** The text merely reports another party's threat — that is reporting a red line, not
   stating one. If the Russian source endorses or adopts the quoted line as its own, it **counts**.
2. **Domestic or non-policy-capable target.** The addressee must be a foreign policy-capable actor: a
   state, leadership, alliance, international organisation or external coalition. Domestic targets,
   individual companies and battlefield combatants are out. Where the target is vague, **attribute
   generously** — exclude only when no foreign actor can be attributed at all.

### Explicitly included

Mirror-parity ("if you do X, we will do X"); vague reaction ("we will respond by all necessary /
military-technical means"); open-ended conditionals; retrospective accounts functioning as a forward
signal; official-adjacent commentary and op-eds, judged by the author's standing rather than by format.

## NTS — Nuclear Threat Statement

**NTS = Y** when an RLS-type statement's consequence invokes or **obliquely includes** nuclear use,
nuclear capability, nuclear testing, or arms-control withdrawal, linked to a foreign actor's behaviour.

Euphemisms count where the context is strategic or existential — *всеми имеющимися средствами*,
*любыми средствами*, *военно-техническими средствами*. Reciprocal nuclear counts ("you test, we test";
"you use tactical nuclear weapons, we use them").

**RLS and NTS are assessed independently.** A passage may be neither, either, or both. A statement can be
a nuclear signal without being a red line: a warning that defeat *may provoke* nuclear war names no
boundary the target must not cross and attaches no punitive consequence to their conduct.

## Precision flags

Recorded independently of the Y/N gate, so a stricter construct can be derived by filtering:

- `line_explicit` — is the boundary stated explicitly, rather than implied or inferable only by a
  reasonable recipient?
- `threat_explicit` — is the adverse consequence stated explicitly, with a named action or domain?

`strict = inclusive AND line_explicit AND threat_explicit`

## Status and provenance

This construct supersedes an earlier **strict** definition requiring an explicit boundary *and* an explicit
threat on every item. That earlier criterion measured the subset of red lines that happen to be well
drafted — a construct-validity failure that biases the series toward formal ministry language and away
from the oblique register in which much coercive signalling actually occurs.

🟥 **The inclusive construct is not formally ratified by all project annotators**, and the reference labels
in this benchmark were adjudicated under the earlier strict definition, by a single adjudicator, before the
change. This is why no inter-rater reliability figure is quoted anywhere, and why measured accuracy against
these labels should be read as agreement with a provisional reference rather than as correctness.
See `CODEBOOK_VERSION_FINDING.md`.

The exact text given to models is `prompt/system_v2.md` (sha256 in `prompt/FROZEN.txt`).
