#!/usr/bin/env python3
"""Splice measured data into the app. Every value derived; nothing typed."""
import json, io, os, re, hashlib
B=os.path.dirname(os.path.abspath(__file__))
APP=os.path.join(os.path.dirname(B),"app","index.html")
BAK=os.path.join(os.path.dirname(B),"app","index.deployed.backup.html")
D=json.load(io.open(os.path.join(B,"app_data.json"),encoding="utf-8"))
TR={}
tp=os.path.join(B,"translations.jsonl")
if os.path.exists(tp):
    for l in io.open(tp,encoding="utf-8"):
        r=json.loads(l)
        if r.get("en"): TR[r["cid"]]=r["en"]

js=lambda s: json.dumps(s if s is not None else "", ensure_ascii=False)
MODELS=D["models"]
mk_order=[m["k"] for m in MODELS]

lines=["const MODELS=["]
# CANONICAL SCHEMA. `flag_rate` (not `fabr`) is the per-model key and `flagged` (not
# `fab`) the per-passage one; `cm` carries the measured confusion matrix and
# attempted/parsed/no_answer its real denominator. This injector used to read m["fabr"]
# and emit no matrix at all, so re-running it against canonical data raised
# KeyError: 'fabr' -- the active build route could not reproduce the page it serves.
for m in MODELS:
    lines.append(" {k:%s, n:%s, short:%s, prov:%s, slug:%s, ctx:'—', price:%s, f1:%s, rls:%s, nts:%s, "
                 "rlsrec:%s, ntsrec:%s, fa:%s, mn:%s, cm:%s, attempted:%s, parsed:%s, no_answer:%s, "
                 "flag_rate:%s, refus:%s, schema:%s, consis:%s, secs:%s, "
                 "cost:%s, flip:null, style:'measured'},"
        % (js(m["k"]),js(m["n"]),js(m["short"]),js(m["prov"]),js(m["slug"]),js(m["price"]),
           m["f1"],m["rls"],m["nts"],m["rlsrec"],m["ntsrec"],m["fa"],m["mn"],
           json.dumps(m["cm"]), m["attempted"], m["parsed"], m["no_answer"],
           m["flag_rate"],m["refus"],
           m["schema"],m["consis"],m["secs"],m["cost"]))
lines.append("];")
lines.append("const MK=MODELS.map(m=>m.k)")
lines.append("const MNAME=Object.fromEntries(MODELS.map(m=>[m.k,m.n]))")
refn={"None":0,"RLS":0,"NTS":0}
for p in D["passages"]: refn[p["ref"]]+=1
# NOTE: REF_N is declared AFTER PBYID in the original file, outside the replaced block.
# Emitting it here would duplicate the declaration and kill the script. Patch it in place below.
lines.append("const P=(id,ref,sp,yr,ru,en,cue,why,v,j,flagged)=>({id,ref,sp,yr,ru,en,cue,why,v,j:j||{},flagged:flagged||{}})")
lines.append("const V=(...a)=>Object.fromEntries(MK.map((k,i)=>[k,a[i]]))")
lines.append("const PASSAGES=[")
for p in D["passages"]:
    fabs=[k for k in p["flagged"]]
    why=("Reference label: %s. Source: %s, %s. %d of %d models agreed with the reference."
          % (p["ref"], p["sp"] or "n/a", p["yr"], p["agree"], p["n_models"]))
    if fabs:
        names={m["k"]:m["n"] for m in MODELS}
        why += (" ⚠ %d model(s) cited a quote that is NOT verbatim in this passage: %s."
                % (len(fabs), ", ".join(sorted(names.get(k,k) for k in fabs))))
    v=", ".join(js(p["v"].get(k,"n/a")) for k in mk_order)
    j=json.dumps({k:val for k,val in p["j"].items()}, ensure_ascii=False)
    # `flagged` is the canonical per-passage key; `fab` is only a fallback for an older
    # app_data.json. Reading p.get("fab") alone against canonical data silently emitted {}
    # for every passage, dropping all 102 flag mappings from the rebuilt page -- with no error.
    _flagged = json.dumps(p.get("flagged", p.get("fab", {})))
    lines.append(" P(%s,%s,%s,%s,\n  %s,\n  %s,\n  %s,\n  %s,\n  V(%s), %s, %s),"
        % (js(p["id"]),js(p["ref"]),js(p["sp"]),js(p["yr"]),
           js(p["ru"]), js(TR.get(p["cid"]) or "[English rendering not available]"),
           js(p["cue"]), js(why), v, j, _flagged))
           # only a fallback for an older app_data.json. Reading p.get("fab") alone against
           # canonical data silently emitted {} for every passage, dropping all 102 flag
           # mappings from the rebuilt page while nothing errored.))
lines.append("];")
# evidence spans: passage id -> model key -> [{layer,t,ok}]
EV={p["id"]:p.get("ev",{}) for p in D["passages"] if p.get("ev")}
lines.append("const EV=%s" % json.dumps(EV, ensure_ascii=False))
block="\n".join(lines)+"\n"

SRC=os.environ.get("INJECT_SRC", BAK)
s=io.open(SRC,encoding="utf-8").read()
i=s.index("const MODELS=["); k=s.index("const PBYID")
s=s[:i]+block+s[k:]

# --- render patches (3) ---
import re as _re
s=_re.sub(r"const REF_N=\{[^}]*\}", "const REF_N=%s" % json.dumps(refn), s, count=1)
# Situation Room hardcodes a passage id from the mockup set that no longer exists.
# Repoint it at the Medvedev Ramstein passage (chunk 105309) if present, else the first item.
_sit=next((q["id"] for q in D["passages"] if q["cid"]=="105309"), D["passages"][0]["id"])
s=s.replace("PBYID['#142']", "PBYID[%s]" % json.dumps(_sit))
s=s.replace("openPassage(\\'#142\\')", "openPassage(\\'%s\\')" % _sit)
s=s.replace("m.flip.toFixed(1)+'%'", "'<span title=\"English leg not run\" style=\"opacity:.5\">n/m</span>'")
# --- banner + titles ---
n_rec=D["n_records"]; spend=D["spend"]
banner=("<div class=\"mockup-banner\" style=\"background:#14532d;color:#d1fae5\">MEASURED RUN — %d scored decisions, "
        "%d passages x %d models x 2 reps, $%.2f — reference labels PROVISIONAL · Russian only · "
        "language-flip column NOT MEASURED (n/m)</div>" % (n_rec, D["n_items"], D["n_models"], spend))
s=s.replace("<div class=\"mockup-banner\">MOCKUP — NOT REAL DATA — FOR LAYOUT AND CONCEPT REVIEW ONLY</div>", banner)
s=s.replace("<h1>RedLineBench <span class=\"badge\">Mockup</span></h1>",
            "<h1>RedLineBench <span class=\"badge\">Measured</span></h1>")
s=s.replace("<title>RedLineBench — MOCKUP","<title>RedLineBench — measured run")
io.open(APP,"w",encoding="utf-8").write(s)
print("data block %d chars -> app %d chars" % (len(block), len(s)))
print("translations used: %d/%d" % (len(TR), len(D["passages"])))
print("md5", hashlib.md5(s.encode()).hexdigest())
