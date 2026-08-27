#!/usr/bin/env python3
"""Check every number the dashboard DISPLAYS against the published results.

WHY THIS EXISTS. Over three review rounds the dashboard was found to be
displaying figures that no longer matched, or never matched, the data:

  * its sequential payload was pre-repair -- 624 decisions against a measured
    816, with four of six catch counts wrong, so the landing chart asserted a
    ranking the write-up had already corrected;
  * its confusion matrix was INVENTED from fixed ratios (fa*0.65, rest*0.6)
    with a remainder cell that rendered NEGATIVE counts;
  * `fa` was assigned the `missed` count, so False Alerts equalled Missed
    Nuclear for all fourteen configurations;
  * the citation decomposition sat at 239/32 where the records give 238/33;
  * "Error patterns by source type" claimed 54 false nuclear alerts when the
    measured total across every source is 2.

Every one of those was invisible to grep, to a JS syntax check and to a DOM
probe, because each wrong number was internally consistent and individually
plausible. The only thing that caught them was recomputing from the source.
That is what this script does, so nobody has to notice by eye again.

Exit 0 if every checked figure reconciles; exit 1 listing those that do not.
"""
import json, io, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

def data(name):
    for c in (os.path.join(REPO, "results", name), os.path.join(REPO, "data", name)):
        if os.path.exists(c): return c
    raise SystemExit(f"cannot find {name}")

def jload(p): return json.load(io.open(p, encoding="utf-8"))
def jlines(p): return [json.loads(l) for l in io.open(p, encoding="utf-8") if l.strip()]

def ref_of(r):  return "NTS" if r["gold_nts"] == "Y" else ("RLS" if r["gold_rls"] == "Y" else "None")
def pred_of(r):
    v = r.get("verdict")
    if not r.get("parsed") or not v: return None
    return "NTS" if v.get("nts") == "Y" else ("RLS" if v.get("rls") == "Y" else "None")

def main(app_path):
    app = io.open(app_path, encoding="utf-8").read()
    rows = [r for r in jlines(data("results_sweep.jsonl")) if "gold_nts" in r]
    scores = jload(data("scores.json"))
    seq = jload(data("scores_sequential.json"))
    cats = jload(data("flagged_span_categories.json"))
    fails = []

    def check(label, expected, found):
        if str(expected) != str(found):
            fails.append(f"{label}: app shows {found!r}, data gives {expected!r}")

    # --- 1. the SEQ payload ------------------------------------------------
    m = re.search(r"const SEQ=(\{.*?\});\s*\n", app, re.S)
    if not m: fails.append("SEQ payload not found in the app")
    else:
        S = json.loads(m.group(1))
        check("SEQ.n_decisions", sum(seq[k]["decisions"] for k in seq), S.get("n_decisions"))
        check("SEQ.tracks length", len({r["seq_id"] for r in jlines(data("results_sequential.jsonl"))}),
              len(S.get("tracks", [])))
        for mo in S.get("models", []):
            k = mo["k"]
            if k in seq: check(f"SEQ caught[{k}]", seq[k]["caught"]["k"], mo.get("caught"))

    # --- 2. per-model confusion matrix, false alerts, missed nuclear -------
    L = ["None", "RLS", "NTS"]
    cm = collections.defaultdict(lambda: {a: {b: 0 for b in L} for a in L})
    for r in rows:
        p = pred_of(r)
        if p is not None: cm[r["model_key"]][ref_of(r)][p] += 1
    mm = re.search(r"const MODELS=(\[.*?\]);\s*\n", app, re.S)
    if mm:
        try: models = json.loads(mm.group(1))
        except Exception: models = []
        for mo in models:
            key = mo.get("slug") or mo.get("k", "").replace("_", "-")
            src = next((k for k in cm if k.replace("-", "_").replace(".", "_") == mo.get("k")), None)
            if not src: continue
            C = cm[src]
            check(f"cm[{src}]", [[C[a][b] for b in L] for a in L], mo.get("cm"))
            check(f"fa[{src}]", C["None"]["NTS"] + C["RLS"]["NTS"], mo.get("fa"))
            check(f"mn[{src}]", C["NTS"]["None"] + C["NTS"]["RLS"], mo.get("mn"))
            # no cell may be negative, ever
            for a in L:
                for b in L:
                    if C[a][b] < 0: fails.append(f"cm[{src}][{a}][{b}] negative")

    # --- 3. the citation decomposition ------------------------------------
    per = collections.defaultdict(collections.Counter)
    for r in cats["records"]: per[r["model"]][r["tier"]] += 1
    f = re.search(r"FABX\s*=\s*(\{.*?\});\s*\n", app, re.S)
    if f:
        F = json.loads(f.group(1))
        for t in "ABCD":
            check(f"FABX.{t}", sum(per[k][t] for k in per), F.get(t))
        check("FABX.flagged", len(cats["records"]), F.get("flagged"))
        for mo in F.get("models", []):
            c = per.get(mo["k"])
            if c:
                for t in "AB": check(f"FABX[{mo['k']}].{t}", c[t], mo.get(t))

    # --- 3b. "Error patterns by source type" -------------------------------
    # This table once claimed 54 false nuclear alerts against a measured total of 2.
    samp_p = os.path.join(REPO, "data", "sample_representative_100.json")
    if os.path.exists(samp_p):
        samp = {str(r["chunk_id"]): r for r in jload(samp_p)}
        def arm(db): return "Telegram" if db == "telegram_official" else ("Kremlin" if db == "kremlin" else "Duma/FC")
        pat = collections.defaultdict(collections.Counter)
        for r in rows:
            p_ = pred_of(r)
            if p_ is None: continue
            sm = samp.get(str(r["chunk_id"]))
            if not sm: continue
            a, R_ = arm(sm["database"]), ref_of(r)
            if R_ != "NTS" and p_ == "NTS": pat["False NTS alert"][a] += 1
            if R_ == "None" and p_ == "RLS": pat["False RLS alert"][a] += 1
            if R_ == "RLS" and p_ != "RLS": pat["Missed RLS"][a] += 1
            if R_ == "NTS" and p_ != "NTS": pat["Missed NTS"][a] += 1
        for label, c in pat.items():
            row = re.search(r'<tr><td style="text-align:left">' + re.escape(label) + r'</td>(.*?)</tr>', app, re.S)
            if not row: continue
            shown = [int(x) for x in re.findall(r"<td[^>]*>(\d+)\s*<span", row.group(1))]
            want = [c["Telegram"], c["Kremlin"], c["Duma/FC"]]
            if shown and shown != want:
                fails.append(f"error-pattern row {label!r}: app shows {shown}, data gives {want}")

    # --- 4. headline KPI tiles --------------------------------------------
    missed = sum(1 for r in rows if ref_of(r) == "NTS" and pred_of(r) not in (None, "NTS"))
    false_nts = sum(1 for r in rows if ref_of(r) != "NTS" and pred_of(r) == "NTS")
    refus = sum(m["refusals"] for m in scores["models"].values())
    for label, val in (("missed nuclear signals", missed), ("false strategic alerts", false_nts),
                       ("provider refusals", refus), ("spans flagged by a naive check", len(cats["records"]))):
        mt = re.search(r'kpi-num[^>]*>([\d,]+)</div><div class="kpi-label">' + re.escape(label), app)
        if mt: check(f"KPI {label}", val, int(mt.group(1).replace(",", "")))

    # --- report ------------------------------------------------------------
    if fails:
        print(f"FAIL — {len(fails)} displayed figure(s) do not reconcile:")
        for x in fails: print("  -", x)
        return 1
    print("OK — every checked figure in the app reconciles with the published results.")
    return 0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: verify_app_numbers.py <path to app/index.html>")
    sys.exit(main(sys.argv[1]))
