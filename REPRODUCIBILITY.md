# Reproducing this, and what cannot be reproduced

## What is here

Everything needed to re-run the evaluation: the frozen prompt with hashes, both datasets **with passage
text and per-item SHA-256**, the model registry, the runner, the scorer, and all 3,500 per-decision
records with usage, rationales, evidence spans and verbatim checks.

```
export CREDENTIALS_ENV=~/.rubicon.env
pip install -r requirements.txt
python code/run_bench.py probe
python code/run_bench.py run --reps 2 --langs ru --workers 14 --budget 90
python code/score.py
```

Append-only and resume-capable: re-running skips completed `(model, chunk, lang, rep)` work, so an
interrupted run costs nothing already spent.


## Reproducing the dashboard itself

The page at <https://rubase.org/redline-eval/> is generated from `results/` and `data/`. Nothing on
it is typed by hand, and the route is published:

```
git archive HEAD | tar -x -C /tmp/x
cd /tmp/x/site && DEPLOYED_PAGE=app/index.html bash bench/rebuild.sh
```

It runs five gates and **refuses to finish** if any fails:

| gate | establishes |
|---|---|
| `bench/audit_app.py` | no placeholder text, no dead fields, the emitted slate matches the data |
| `bench/verify_app_numbers.py` | every figure in the page **source** reconciles with `results/` |
| `bench/test_verify_app_numbers.py` | that checker **fails** on 20 defects actually found here |
| `bench/verify_rendered_page.py` | every figure a reader **sees** matches the payload the page loads (needs a browser) |
| `bench/test_verify_rendered_page.py` | that checker **fails** on 14 bad renders |
| byte comparison | the rebuilt page is byte-identical to the deployed one |

**Why two checkers and two adversarial suites.** Reading the page source catches a stale or invented
payload; it cannot catch a renderer that draws a correct payload wrongly. This dashboard shipped
exactly that — a table whose class counts were correct values printed under transposed headers, so
59 no-alert passages displayed as red lines. It also shipped a confusion matrix invented from fixed
ratios that rendered negative cells, and an error table claiming 54 false nuclear alerts where the
measured total is 2.

Each of those passed the checks that existed at the time. So every checker here ships with a suite
that reconstructs real defects from this project's history and requires each to be **caught**: a
skipped case is reported as a stale test and never as a pass, a missing input is a failure and never
a pass, and a missing browser fails rather than exiting 0.

**The honest claim** is not that the dashboard is correct because we were careful. It is that every
figure on it is mechanically reconciled to the published results by two independent checkers, each of
which has been shown to fail on inputs it should reject.

## 🟥 What cannot be reproduced exactly, and why

**Model aliases are not snapshots.** The run recorded `claude-opus-5`, `gpt-5.6-sol`, `gemini-3.6-flash`
and so on — the identifiers we sent. Providers move those aliases to new weights without notice. **A
re-run at a later date may be a different model behind the same name, and nothing in our output
distinguishes the two.** This is a real limitation of the recorded run, not of the design: a future run
should pin dated snapshots where the provider exposes them, and record any version returned in the
response.

**No per-record timestamps.** The records carry latency but not wall-clock time. The run window is
established only by file modification times, not by the data itself. Future runs should stamp each record.

**Non-determinism.** These models are not deterministic and several do not honour a temperature setting.
This is why the design uses two repetitions; observed repeat-consistency was 0.978–1.000. Expect small
differences on re-run even against identical weights.

**Provider-side refusals and throttling.** One provider's content filter declined six records; two
providers slowed markedly under sustained load (28.8 s and 24.2 s mean latency against 3.2 s for the
fastest). Both are properties of the provider on the day, not of the benchmark.

## Excluded items

`data/excluded_contested_15.json` lists the fifteen reference positives excluded before sampling, where
the project's revised screening pipeline no longer treats the passage as a candidate. They are published
so the exclusion can be checked rather than taken on trust. See `CODEBOOK_VERSION_FINDING.md`.

## Provenance of the passages

Each item carries channel, date and source arm. **Nine of the hundred carry a source URL** — the items
originating from official web publications. Telegram-sourced items are identified by channel and date;
the corpus does not store a per-post URL for them. This is stated rather than papered over: for those
items a reader can locate the channel and date but not a canonical link.
