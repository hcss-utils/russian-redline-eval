#!/usr/bin/env python3
"""Select the ~100-item subset of the clean pool that best matches the RED LINES
corpus on observable strata.

Population represented: corpus chunks with tokens >= FLOOR (92.5% of all chunks).
The same floor is applied to BOTH the corpus targets and the candidate pool --
truncating only the sample would reintroduce the bias we are removing.

Matched marginals: database (source), token-length quartile, year era.
NOT matched: language (corpus is 100% RU -- no stratum exists) and LABEL
(corpus NTS prevalence is 2.563%; a prevalence-faithful 100 would hold ~3
nuclear items and measure nothing). Labels are therefore a DELIBERATE
oversample; enrichment factors and inverse-probability weights are emitted so
metrics can be reported both conditionally and reweighted to corpus prevalence.

Deterministic: fixed seed, sorted inputs, seeded local search.
"""
import csv, io, json, math, hashlib, random, os, collections

HERE   = os.path.dirname(os.path.abspath(__file__))
ATTRS  = "/tmp/gold298_attrs.csv"
OUT    = os.environ.get("OUT_JSON", os.path.join(HERE, "sample_representative_100.json"))
REPORT = os.environ.get("OUT_MD", os.path.join(HERE, "REPRESENTATIVENESS.md"))
FLOOR, SEED = 50, 20260901
N_TARGET = int(os.environ.get("N_TARGET", 100))
MIN_NTS = int(os.environ.get("MIN_NTS", 18))
MIN_RLS = int(os.environ.get("MIN_RLS", 30))
Q1, Q2, Q3 = 142, 256, 433

CORPUS_DB = {"telegram_official":244691, "kremlin":12119, "state_duma":10544, "federation_council":6882}
CORPUS_YR = {"<2014":5043,"2014":618,"2015":528,"2016":1532,"2017":5124,"2018":3917,"2019":5384,
             "2020":8893,"2021":16739,"2022":41213,"2023":49583,"2024":56870,"2025":53529,"2026":25263}
CORPUS_TOK_SHARE = {"Q1":0.25,"Q2":0.25,"Q3":0.25,"Q4":0.25}   # quartiles by construction
CORPUS_SRC = {r["source"]: int(r["n"]) for r in csv.DictReader(
    io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "corpus_source_targets.csv"), encoding="utf-8"))}
CORPUS_NTS_RATE = 0.02563

def era(y):
    y = str(y)
    if y in ("NA", ""): return "NA"
    if not y.isdigit(): return y          # already-collapsed bucket label, pass through
    y = int(y)
    if y < 2014: return "<2014"
    if y <= 2019: return "2014-2019"
    if y <= 2021: return "2020-2021"
    return str(y)

def tokbin(t):
    return "Q1" if t <= Q1 else "Q2" if t <= Q2 else "Q3" if t <= Q3 else "Q4"

def norm(d):
    s = sum(d.values()) or 1
    return {k: v/s for k, v in d.items()}

def collapse_years(dist):
    out = collections.Counter()
    for k, v in dist.items(): out[era(k)] += v
    return dict(out)

def tvd(sample_counts, target_props, keys):
    sp = norm({k: sample_counts.get(k, 0) for k in keys})
    return 0.5 * sum(abs(sp.get(k, 0) - target_props.get(k, 0)) for k in keys)

def score(sel, T):
    db = collections.Counter(r["database"] for r in sel)
    tb = collections.Counter(tokbin(int(r["tokens"])) for r in sel)
    yr = collections.Counter(era(r["yr"] or "NA") for r in sel)
    sc = collections.Counter(r["src"] for r in sel)
    return (1.0*tvd(db, T["db"], T["db"].keys())
            + 1.0*tvd(tb, T["tok"], T["tok"].keys())
            + 1.0*tvd(yr, T["yr"], T["yr"].keys())
            + float(os.environ.get("W_SRC","3.0"))*tvd(sc, T["src"], T["src"].keys()))   # channel = the substantive stratum

def feasible(sel):
    return (sum(1 for r in sel if r["gold_nts"] == "Y") >= MIN_NTS
            and sum(1 for r in sel if r["gold_rls"] == "Y") >= MIN_RLS)

def main():
    rows = list(csv.DictReader(io.open(ATTRS, encoding="utf-8")))
    clean = [r for r in rows if not ((r["gold_rls"]=="Y" and r["rls_ok"]=="f")
                                  or (r["gold_nts"]=="Y" and r["nts_ok"]=="f"))]
    pool = sorted([r for r in clean if int(r["tokens"]) >= FLOOR], key=lambda r: r["chunk_id"])
    T = {"db": norm(CORPUS_DB), "tok": CORPUS_TOK_SHARE, "yr": norm(collapse_years(CORPUS_YR)),
         "src": norm(CORPUS_SRC)}

    rng = random.Random(SEED)
    # seed with a feasible selection: take required positives first, then fill
    nts = [r for r in pool if r["gold_nts"]=="Y"]
    rls = [r for r in pool if r["gold_rls"]=="Y" and r["gold_nts"]!="Y"]
    rest= [r for r in pool if r["gold_nts"]!="Y" and r["gold_rls"]!="Y"]
    sel = nts[:MIN_NTS] + rls[:MIN_RLS]
    sel += [r for r in rest][:N_TARGET-len(sel)]
    sel = sel[:N_TARGET]
    cur = score(sel, T)

    best, best_s = list(sel), cur
    for restart in range(int(os.environ.get("RESTARTS","6"))):
        if restart:                                   # re-seed from best with a shuffle
            sel = list(best); rng.shuffle(sel)
        selset = {r["chunk_id"] for r in sel}
        outside = [r for r in pool if r["chunk_id"] not in selset]
        cur = score(sel, T)
        ITERS = int(os.environ.get("ITERS","120000"))
        for it in range(ITERS):
            T_temp = 0.05 * (1.0 - it / ITERS) + 1e-6      # annealing schedule
            i = rng.randrange(len(sel)); j = rng.randrange(len(outside))
            cand = sel[:i] + sel[i+1:] + [outside[j]]
            if not feasible(cand): continue
            sc_ = score(cand, T)
            d = sc_ - cur
            if d < 0 or rng.random() < math.exp(-d / T_temp):
                dropped = sel[i]; sel = cand; cur = sc_
                outside[j] = dropped
                if cur < best_s - 1e-12:
                    best_s, best = cur, list(sel)
    sel = sorted(best, key=lambda r: r["chunk_id"]); cur = best_s

    def table(name, counts, target, keys):
        lines = [f"\n**{name}**\n", "| stratum | corpus % | sample n | sample % | diff |", "|---|---:|---:|---:|---:|"]
        total = sum(counts.values()) or 1
        sp = {k: counts.get(k, 0)/total for k in keys}
        for k in keys:
            lines.append(f"| {k} | {100*target.get(k,0):.2f} | {counts.get(k,0)} | "
                         f"{100*sp.get(k,0):.2f} | {100*(sp.get(k,0)-target.get(k,0)):+.2f} |")
        return "\n".join(lines)

    db = collections.Counter(r["database"] for r in sel)
    tb = collections.Counter(tokbin(int(r["tokens"])) for r in sel)
    yr = collections.Counter(era(r["yr"] or "NA") for r in sel)
    n_nts = sum(1 for r in sel if r["gold_nts"]=="Y")
    n_rls = sum(1 for r in sel if r["gold_rls"]=="Y")
    enrich = (n_nts/len(sel))/CORPUS_NTS_RATE

    print(f"pool(clean,>={FLOOR}tok) = {len(pool)}   selected = {len(sel)}")
    print(f"objective (weighted TVD) = {cur:.4f}")
    print(f"  TVD database = {tvd(db,T['db'],T['db'].keys()):.4f}")
    print(f"  TVD tokenbin = {tvd(tb,T['tok'],T['tok'].keys()):.4f}")
    print(f"  TVD year-era = {tvd(yr,T['yr'],T['yr'].keys()):.4f}")
    sc = collections.Counter(r["src"] for r in sel)
    print(f"  TVD channel  = {tvd(sc,T['src'],T['src'].keys()):.4f}   (pool floor 0.0621)")
    print(f"labels: NTS={n_nts} RLS={n_rls}  NTS enrichment vs corpus = {enrich:.1f}x")
    print("\ndatabase:", dict(db)); print("tokenbin:", dict(tb)); print("year:", dict(yr))

    payload = json.dumps(sel, ensure_ascii=False, indent=1, sort_keys=True)
    io.open(OUT,"w",encoding="utf-8").write(payload)
    md = [f"# Representativeness of the {len(sel)}-item sample",
          "",
          f"Population represented: **corpus chunks with >= {FLOOR} tokens** "
          f"(274,236 of 296,381 chunks = 92.5% of the corpus).",
          "",
          f"Selected from the **{len(pool)}** clean pool items (283 uncontested, minus those under the floor).",
          "",
          "Matched marginals below. Language is **not** a stratum: the corpus is 100% Russian.",
          table("Source (database)", db, T["db"], list(CORPUS_DB)),
          table("Chunk length (corpus token quartiles)", tb, T["tok"], ["Q1","Q2","Q3","Q4"]),
          table("Year era", yr, T["yr"], sorted(T["yr"])),
          table("Source identity (channel)", collections.Counter(r["src"] for r in sel), T["src"],
                [k for k,_ in sorted(CORPUS_SRC.items(), key=lambda kv:-kv[1])][:20]),
          "",
          "## Labels are deliberately over-sampled",
          "",
          f"Corpus NTS prevalence is **{100*CORPUS_NTS_RATE:.3f}%**. This sample carries "
          f"**{n_nts} NTS-positive of {len(sel)}** = {100*n_nts/len(sel):.1f}%, an enrichment of "
          f"**{enrich:.1f}x**. A prevalence-faithful sample of 100 would contain about 3 nuclear "
          "items and could not measure a miss rate. Report metrics twice: conditional on this "
          "challenge set, and reweighted to corpus prevalence using inverse-probability weights "
          f"(NTS-positive weight = {CORPUS_NTS_RATE/(n_nts/len(sel)):.4f}).",
          "",
          f"Deterministic: seed {SEED}, sorted inputs. sha256 `{hashlib.sha256(payload.encode()).hexdigest()[:32]}`."]
    io.open(REPORT,"w",encoding="utf-8").write("\n".join(md))
    print(f"\nsha256 {hashlib.sha256(payload.encode()).hexdigest()[:32]}")
    print("wrote", OUT); print("wrote", REPORT)

if __name__ == "__main__":
    main()
