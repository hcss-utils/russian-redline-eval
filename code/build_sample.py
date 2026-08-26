#!/usr/bin/env python3
"""Build the deterministic stratified demo sample from the 298-item gold set.

Design rationale (see README):
  * ALL nuclear-signal items are taken (the class is too small to sample).
  * Negatives are HARD-MINED, not random: a negative is interesting only if it
    fooled the annotating model. Random negatives are Telegram channel chaff
    ("thanks for 30k subscribers") that every model trivially rejects and that
    inflate accuracy without measuring discrimination.
Deterministic: fixed seed, sorted inputs. Same input -> same sample, always.
"""
import csv, io, json, hashlib, random, statistics, sys, os
import os
# Local corpus paths are machine-specific and are read from the environment.
# GOLD_DIR should point at the reference-set directory; the published data/
# files in this repo are the outputs, so nothing here is needed to re-score.
GOLD_DIR = os.environ.get("GOLD_DIR", "./gold_certification")

BASE = GOLD_DIR
GOLD = os.path.join(BASE, "gold_v2_260726.csv")
TEXT = os.path.join(BASE, "scripts", "gold298_rows.json")
OUT  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_100.json")
SEED = 20260901
N_RLS_ONLY, N_NEG = 36, 36

def load():
    raw = io.open(TEXT, encoding="utf-8").read()
    txt = {r["chunk_id"]: r["content"] for r in json.loads(raw[raw.index("["):])}
    gold = list(csv.DictReader(io.open(GOLD, encoding="utf-8")))
    return txt, gold

def main():
    txt, gold = load()
    for r in gold:
        r["content"] = txt[r["chunk_id"]]
        r["n_chars"] = len(r["content"])

    nts_pos   = [r for r in gold if r["gold_nts"] == "Y"]
    rls_only  = [r for r in gold if r["gold_rls"] == "Y" and r["gold_nts"] == "N"]
    negatives = [r for r in gold if r["gold_rls"] == "N" and r["gold_nts"] == "N"]

    # Hard negatives: the model said Y, the humans said N -> it fooled a frontier model.
    fooled = [r for r in negatives if r["model_rls"] == "Y" or r["model_nts"] == "Y"]
    # Substantive but not model-fooling, as filler; never the trivial chaff.
    rest   = sorted([r for r in negatives if r not in fooled and r["n_chars"] >= 300],
                    key=lambda r: -r["n_chars"])

    rng = random.Random(SEED)
    fooled_sorted = sorted(fooled, key=lambda r: r["chunk_id"])
    chosen_neg = fooled_sorted[:N_NEG]
    if len(chosen_neg) < N_NEG:
        pad = rest[: N_NEG - len(chosen_neg)]
        chosen_neg += pad

    rls_sorted = sorted(rls_only, key=lambda r: r["chunk_id"])
    chosen_rls = rng.sample(rls_sorted, min(N_RLS_ONLY, len(rls_sorted)))

    sample = sorted(nts_pos + chosen_rls + chosen_neg, key=lambda r: r["chunk_id"])

    print(f"POOL       nts_pos={len(nts_pos)}  rls_only={len(rls_only)}  negatives={len(negatives)}")
    print(f"HARD NEG   model-fooling negatives available = {len(fooled)}  (used {len([r for r in chosen_neg if r in fooled])})")
    print(f"           substantive filler used = {len([r for r in chosen_neg if r not in fooled])}")
    print(f"SAMPLE     n={len(sample)}  "
          f"nts_Y={sum(1 for r in sample if r['gold_nts']=='Y')}  "
          f"rls_Y={sum(1 for r in sample if r['gold_rls']=='Y')}  "
          f"both={sum(1 for r in sample if r['gold_rls']=='Y' and r['gold_nts']=='Y')}")
    lens = [r["n_chars"] for r in sample]
    print(f"CHARS      min={min(lens)} median={int(statistics.median(lens))} "
          f"max={max(lens)} total={sum(lens):,}")
    print(f"SRC        " + str({k: sum(1 for r in sample if r['src_rls']==k)
                                for k in sorted({r['src_rls'] for r in sample})}))
    payload = json.dumps(sample, ensure_ascii=False, indent=1, sort_keys=True)
    io.open(OUT, "w", encoding="utf-8").write(payload)
    print(f"SHA256     {hashlib.sha256(payload.encode()).hexdigest()[:32]}")
    print(f"WROTE      {OUT}")

if __name__ == "__main__":
    main()
