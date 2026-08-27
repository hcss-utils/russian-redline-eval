#!/usr/bin/env python3
"""Inject the sequential arm's MEASURED results into the app.

Every figure is read from scores_sequential.json / results_sequential.jsonl and
interpolated. Nothing is typed in: a hardcoded number renders exactly as
convincingly as a measured one, which is why gate #76 exists.
"""
import json, io, os, sys

APP="app/index.html"
def main():
    if not os.path.exists("bench/scores_sequential.json"):
        raise SystemExit("no scores_sequential.json yet -- run score_sequential.py first")
    sc=json.load(io.open("bench/scores_sequential.json",encoding="utf-8"))
    seqs=json.load(io.open("bench/sequences.json",encoding="utf-8"))
    rows=[json.loads(l) for l in io.open("bench/results_sequential_all.jsonl",encoding="utf-8") if l.strip()]
    rows=[r for r in rows if not r.get("error")]
    _am=json.load(io.open("bench/app_data.json",encoding="utf-8"))["models"]
    _nz=lambda x: x.replace("-","_").replace(".","_")
    names={_nz(m["k"]):m["short"] for m in _am}
    stat ={_nz(m["k"]):m.get("rls") for m in _am}
    payload={
      "n_sequences": seqs["n_sequences"],
      "steps": seqs["steps_per_sequence"],
      "signal_at": seqs["signal_position"],
      "n_decisions": len(rows),
      "spend": round(sum(r.get("cost",0) for r in rows),2),
      "models": [
        {"k":k, "n":names.get(_nz(k),k), "acc":stat.get(_nz(k)),
         "caught":s["caught"]["k"], "caught_n":s["caught"]["n"],
         "cry":round(s["cry_wolf"]["rate"],4), "cry_k":s["cry_wolf"]["k"], "cry_n":s["cry_wolf"]["n"],
         "stuck":round(s["stuck_high_after_catching"]["rate"],4),
         "stuck_k":s["stuck_high_after_catching"]["k"], "stuck_n":s["stuck_high_after_catching"]["n"],
         # canonical key. The scorer emits `naive_flagged_span`; this read `fabricated_span`,
         # a name the scorer stopped using, so the active route died with KeyError before it
         # could refresh the sequential payload -- which is how that payload went stale.
         "flag_rate":round((s.get("naive_flagged_span") or s["fabricated_span"])["rate"],4),
         "cost":s["cost"]}
        for k,s in sc.items()],
      "tracks": [
        {"seq":sid, "speaker":sp,
         "m":{mk:[a for _,a in sorted(v)] for mk,v in tr.items()}}
        for sid,sp,tr in _tracks(rows, seqs)],
    }
    s=io.open(APP,encoding="utf-8").read()
    blob="const SEQ="+json.dumps(payload,ensure_ascii=False,separators=(",",":"))+";"
    import re
    if "const SEQ=" in s:
        s=re.sub(r"const SEQ=\{.*?\};", blob, s, count=1, flags=re.S)
    else:
        s=s.replace("const EV=", blob+"\nconst EV=",1)
    io.open(APP,"w",encoding="utf-8").write(s)
    print(f"injected SEQ: {payload['n_sequences']} sequences, {payload['n_decisions']} decisions, ${payload['spend']}")

def _tracks(rows, seqs):
    from collections import defaultdict
    bysq=defaultdict(lambda: defaultdict(list))
    spk={s["seq_id"]:s["speaker"] for s in seqs["sequences"]}
    for r in rows: bysq[r["seq_id"]][r["model"]].append((r["step"], r["alert"]))
    return [(sid, spk.get(sid,"?"), bysq[sid]) for sid in sorted(bysq)]
if __name__=="__main__": main()
