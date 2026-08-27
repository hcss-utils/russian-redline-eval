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
    # published layout keeps inputs in results/ and data/; the active bench/ route keeps them
    # beside the scripts. Search both, so the same checker runs on either.
    for c in (os.path.join(REPO, "results", name), os.path.join(REPO, "data", name),
              os.path.join(HERE, name), os.path.join(REPO, "bench", name),
              os.path.join(os.getcwd(), "bench", name), name):
        if os.path.exists(c): return c
    raise SystemExit(f"cannot find {name}")

def jload(p): return json.load(io.open(p, encoding="utf-8"))

def _parse_js_array(lit):
    """Parse a JS array literal that may use unquoted keys and single-quoted strings."""
    try: return json.loads(lit)
    except Exception: pass
    t = re.sub(r"([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', lit)
    t = re.sub(r":\s*'((?:[^'\\]|\\.)*)'", lambda m: ": " + json.dumps(m.group(1).replace("\\'", "'")), t)
    t = re.sub(r",\s*([}\]])", r"\1", t)
    try: return json.loads(t)
    except Exception: return None


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
    if not mm: fails.append("MODELS payload not found in the app")
    if mm:
        # The payload is JSON on the hand-finished page and a JS OBJECT LITERAL from the
        # injector (unquoted keys, single-quoted strings). Swallowing the parse error made
        # every MODELS check -- cm, fa/mn, the leaderboard scalars -- silently SKIP on a
        # rebuilt page, so the checker passed the exact rebuild it was meant to police.
        models = _parse_js_array(mm.group(1))
        if models is None:
            fails.append("MODELS payload could not be parsed; refusing to skip its checks")
            models = []
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

    # --- 2b. every model-level scalar the leaderboard prints ---------------
    # The leaderboard renders rls/nts/rlsrec/ntsrec/consis/cost/schema straight off
    # MODELS. cm/fa/mn were checked above; these were not, and a stale one looks
    # exactly like a fresh one.
    if mm:
        FIELDS = {"rls": lambda m: m["rls_incl"]["acc"], "nts": lambda m: m["nts_incl"]["acc"],
                  "rlsrec": lambda m: m["rls_incl"]["recall"], "ntsrec": lambda m: m["nts_incl"]["recall"],
                  "consis": lambda m: m["rep_consistency"], "cost": lambda m: m["est_cost"],
                  "refus": lambda m: m["refusals"]}
        # NOT flag_rate. Two different rates share that name and differ by DENOMINATOR:
        # scores.json's naive_flagged is per RECORD (a scored decision carrying at least one
        # flagged span, 2.5%-45.8%); the leaderboard shows per SPAN (1.7%-42.2%). Comparing
        # them looks like a 14-model defect and is a units error in the checker. The
        # per-span rate is verified below against citation_check_summary.json.
        for mo in models:
            src = next((k for k in scores["models"] if k.replace("-", "_").replace(".", "_") == mo.get("k")), None)
            if not src: continue
            sm = scores["models"][src]
            for f, fn in FIELDS.items():
                if f in mo:
                    want = fn(sm)
                    if isinstance(want, float) and isinstance(mo[f], (int, float)):
                        if abs(want - mo[f]) > 5e-4:
                            fails.append(f"MODELS[{src}].{f}: app {mo[f]}, data {want}")
                    else:
                        check(f"MODELS[{src}].{f}", want, mo[f])
            # the leaderboard's per-SPAN flag rate, against its own denominator
            cs = jload(data("citation_check_summary.json"))["per_model"].get(src)
            if cs and "flag_rate" in mo and cs.get("spans"):
                want = round(cs["flagged"] / cs["spans"], 4)
                if abs(want - mo["flag_rate"]) > 5e-4:
                    fails.append(f"MODELS[{src}].flag_rate (per span): app {mo['flag_rate']}, data {want}")
            # a schema-OK percentage must reconcile with its own parse counts
            if "parsed" in mo and "attempted" in mo:
                if mo["parsed"] > mo["attempted"]:
                    fails.append(f"MODELS[{src}]: parsed {mo['parsed']} exceeds attempted {mo['attempted']}")
                if mo.get("cm") and sum(sum(r) for r in mo["cm"]) != mo["parsed"]:
                    fails.append(f"MODELS[{src}]: cm totals {sum(sum(r) for r in mo['cm'])} "
                                 f"but parsed is {mo['parsed']}")

    # --- 2c. the PASSAGES payload itself ------------------------------------
    # This was NOT checked at all. Changing passage #001's reference label from NTS to
    # None -- which alters what the Cases table and the Situation Room show a reader --
    # left this verifier printing OK. Fourteen historical tamper cases proved fourteen
    # anchors, not the property. Reconcile the whole payload against the producer's output.
    app_data = None
    for c in (os.path.join(REPO, "app_data.json"), os.path.join(HERE, "app_data.json"),
              os.path.join(REPO, "bench", "app_data.json"), "bench/app_data.json"):
        if os.path.exists(c): app_data = jload(c); break
    pm = re.search(r"const PASSAGES=(.*?);\s*\n", app, re.S)
    if not pm:
        fails.append("PASSAGES payload not found in the app")
    else:
        lit = pm.group(1)
        # the payload is emitted through P(...) helpers, so reconcile field by field on the
        # literal rather than trying to evaluate it: id, ref and the per-model verdicts.
        ids = re.findall(r'P\("(#\d+)","([A-Za-z/]+)"', lit)
        if not ids:
            fails.append("PASSAGES literal present but no P(id,ref,...) entries could be read")
        elif app_data:
            want = {p_["id"]: p_["ref"] for p_ in app_data["passages"]}
            if len(ids) != len(want):
                fails.append(f"PASSAGES has {len(ids)} entries, producer emitted {len(want)}")
            for pid, ref in ids:
                if pid not in want:
                    fails.append(f"PASSAGES {pid} is not in the producer output")
                elif want[pid] != ref:
                    fails.append(f"PASSAGES {pid}.ref: page {ref!r}, producer {want[pid]!r}")
            # the flag maps must survive injection: the rebuilt page once dropped all of them
            # count the individual model:true mappings, not the maps. The serialisation
            # writes '"haiku_4_5": true' WITH a space; a ':true' pattern silently counted 0
            # and would have reported a correct page as having lost every flag.
            shown_flags = len(re.findall(r'"[a-z0-9_.]+"\s*:\s*true', lit))
            want_flags = sum(len(p_.get("flagged") or {}) for p_ in app_data["passages"])
            if shown_flags != want_flags:
                fails.append(f"PASSAGES carries {shown_flags} flag mappings; "
                             f"the producer emitted {want_flags}")
        else:
            fails.append("app_data.json not found, so PASSAGES could not be reconciled "
                         "(run build_app_data.py first)")

    # --- 2d. the evidence-span payload -------------------------------------
    # A rebuild once emptied EV -- 183 KB of cited spans down to 60 bytes -- and every gate
    # stayed green, because nothing checked that it had any content.
    em = re.search(r"const EV=(\{.*?\});\s*\n", app, re.S)
    if not em:
        fails.append("EV payload not found in the app")
    elif app_data:
        want = sum(len(sum((p_.get("ev") or {}).values(), [])) for p_ in app_data["passages"])
        shown = len(re.findall(r'"layer"\s*:', em.group(1)))
        if want and shown == 0:
            fails.append(f"EV payload is empty; the producer emitted {want} evidence spans")
        elif want and shown != want:
            fails.append(f"EV carries {shown} evidence spans; the producer emitted {want}")

    # --- 3. the citation decomposition ------------------------------------
    per = collections.defaultdict(collections.Counter)
    for r in cats["records"]: per[r["model"]][r["tier"]] += 1
    f = re.search(r"FABX\s*=\s*(\{.*?\});\s*\n", app, re.S)
    if not f: fails.append("FABX payload not found in the app")
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
    # Use the resolver, not a hardcoded path. This was os.path.join(REPO, "data", ...),
    # so under the bench/ layout the file was "absent" and BOTH the error-pattern and
    # composition checks silently skipped -- the checker passed a page still carrying the
    # fabricated 18/24/12 table. An input it cannot find is a failure, not a pass.
    try:
        samp_p = data("sample_representative_100.json")
    except SystemExit:
        samp_p = None
        fails.append("sample_representative_100.json not found; refusing to skip the "
                     "error-pattern and composition checks")
    if samp_p:
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
            if not row:
                fails.append(f"error-pattern row {label!r} is absent from the page")
                continue
            shown = [int(x) for x in re.findall(r"<td[^>]*>(\d+)\s*<span", row.group(1))]
            if not shown:  # the pre-repair table had bare <td>18</td> cells with no rate
                shown = [int(x) for x in re.findall(r"<td[^>]*>(\d+)</td>", row.group(1))][:3]
            want = [c["Telegram"], c["Kremlin"], c["Duma/FC"]]
            if not shown:
                fails.append(f"error-pattern row {label!r}: cells unreadable, refusing to skip")
            elif shown != want:
                fails.append(f"error-pattern row {label!r}: app shows {shown}, data gives {want}")

    # --- 3c. sample composition by source arm ------------------------------
    # This table showed its class counts TRANSPOSED under their own headers (RLS/NTS/None
    # where the headers said No alert/Red line/Nuclear signal) and percentages summing
    # to 102% (92+7+3+0). Both were visible on the page and neither was checked.
    if samp_p:
        comp = collections.defaultdict(collections.Counter)
        for r in samp.values():
            lab = "NTS" if r["gold_nts"] == "Y" else ("RLS" if r["gold_rls"] == "Y" else "None")
            comp[r["database"]][lab] += 1
            comp[r["database"]]["n"] += 1
        N = len(samp)
        pct_sum = 0
        for a, c in comp.items():
            row = re.search(r"<tr><td[^>]*>" + re.escape(a) + r"</td><td>(\d+)</td><td>(\d+)</td>"
                            r"<td>(\d+)</td><td>(\d+)</td><td>(\d+)%</td></tr>", app)
            if not row:
                fails.append(f"sample-composition row {a!r} is absent from the page")
                continue
            got = [int(x) for x in row.groups()]
            want = [c["n"], c["None"], c["RLS"], c["NTS"], c["n"] * 100 // N]
            if got != want:
                fails.append(f"sample composition {a}: page {got}, data {want}")
            pct_sum += got[4]
        if comp and not (99 <= pct_sum <= 101):
            fails.append(f"sample-composition percentages sum to {pct_sum}%, not 100%")

    # --- 4. headline KPI tiles --------------------------------------------
    missed = sum(1 for r in rows if ref_of(r) == "NTS" and pred_of(r) not in (None, "NTS"))
    false_nts = sum(1 for r in rows if ref_of(r) != "NTS" and pred_of(r) == "NTS")
    refus = sum(m["refusals"] for m in scores["models"].values())
    for label, val in (("missed nuclear signals", missed), ("false strategic alerts", false_nts),
                       ("provider refusals", refus), ("spans flagged by a naive check", len(cats["records"]))):
        mt = re.search(r'kpi-num[^>]*>([\d,]+)</div><div class="kpi-label">' + re.escape(label), app)
        if not mt:
            fails.append(f"KPI tile {label!r} is absent from the page")
        else:
            check(f"KPI {label}", val, int(mt.group(1).replace(",", "")))

    # --- 5. static figures written into the prose -------------------------
    # Sol's counterexample: changing the visible "Measured cost: $22.38" headline to
    # $99.99 left this checker printing OK, because it covered payloads and four KPI
    # tiles and nothing else. A number a reader sees is a number that must reconcile,
    # whether it arrives through a payload or is typed into a heading.
    spend = round(scores["spend_usd"], 2)
    n_rec = scores["n_records"]
    n_models = len(scores["models"])
    n_pass = len({r["chunk_id"] for r in rows})
    STATIC = [
        (r"Measured cost:\s*\$([\d,.]+)",              f"{spend:.2f}",  "cost headline"),
        (r"\$([\d,.]+)</div><div class=\"kpi-label\">total cost", f"{spend:.2f}", "total-cost tile"),
        (r"([\d,]+)</div><div class=\"kpi-label\">scored decisions", f"{n_rec:,}", "scored-decisions tile"),
        (r"([\d,]+)</div><div class=\"kpi-label\">real passages",    f"{n_pass:,}", "real-passages tile"),
        (r"([\d,]+)</div><div class=\"kpi-label\">models, native APIs", f"{n_models:,}", "models tile"),
        (r"([\d,]+)</div><div class=\"kpi-label\">spans flagged by a naive check", f"{len(cats['records']):,}", "flagged tile"),
    ]
    for pat, want, what in STATIC:
        hits = re.findall(pat, app)
        if not hits:
            fails.append(f"static figure {what!r} not found on the page (anchor moved?)")
            continue
        for h in hits:
            if h.replace(",", "") != want.replace(",", ""):
                fails.append(f"static {what}: page shows {h!r}, data gives {want!r}")

    # every per-model cost printed in the leaderboard must match its measured cost
    for k, sm in scores["models"].items():
        pat = re.escape(k.replace("-", "_").replace(".", "_"))
        # the price appears in MODELS; the prose may repeat it as $x.xx beside the model name
        want = f"{sm['est_cost']:.2f}"
        for mo in (models if mm else []):
            if mo.get("k") == k.replace("-", "_").replace(".", "_"):
                if f"{mo.get('cost', -1):.2f}" != want:
                    fails.append(f"MODELS[{k}].cost: app {mo.get('cost')}, data {sm['est_cost']}")

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
