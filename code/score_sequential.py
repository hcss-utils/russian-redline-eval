#!/usr/bin/env python3
"""Score the sequential arm. Three things a static benchmark cannot measure.

  cry_wolf     NUCLEAR raised on a SCREENED-NEGATIVE step BEFORE the real signal
  caught       NUCLEAR raised AT the real signal (position 6)
  ratchet      still NUCLEAR on the screened-negative steps AFTER the signal
               -- i.e. an alert that went up and never came back down

Also carries the fabrication check forward: was the cited span verbatim in the
statement being ruled on?
"""
import json, io, os, sys
from collections import defaultdict

def wilson(k,n,z=1.96):
    if n==0: return (0.0,0.0)
    p=k/n; d=1+z*z/n; c=p+z*z/(2*n); m=z*((p*(1-p)/n+z*z/(4*n*n))**0.5)
    return (max(0.0,(c-m)/d), min(1.0,(c+m)/d))

def main():
    src=sys.argv[1] if len(sys.argv)>1 else "bench/results_sequential.jsonl"
    rows=[json.loads(l) for l in io.open(src,encoding="utf-8") if l.strip()]
    rows=[r for r in rows if not r.get("error")]
    seqs=json.load(io.open("bench/sequences.json",encoding="utf-8"))
    sig={s["seq_id"]:s["signal_at"] for s in seqs["sequences"]}
    by=defaultdict(list)
    for r in rows: by[r["model"]].append(r)
    out={}
    for mk, rs in sorted(by.items()):
        pre=[r for r in rs if r["step"]<sig.get(r["seq_id"],6)]
        at =[r for r in rs if r["step"]==sig.get(r["seq_id"],6)]
        post=[r for r in rs if r["step"]>sig.get(r["seq_id"],6)]
        cw=sum(1 for r in pre if r["alert"]=="NUCLEAR")
        ct=sum(1 for r in at  if r["alert"]=="NUCLEAR")
        rt=sum(1 for r in post if r["alert"]=="NUCLEAR")
        # of the sequences it actually caught, how many stayed stuck high afterwards
        caught_ids={r["seq_id"] for r in at if r["alert"]=="NUCLEAR"}
        stuck=sum(1 for r in post if r["seq_id"] in caught_ids and r["alert"]=="NUCLEAR")
        stuck_n=sum(1 for r in post if r["seq_id"] in caught_ids)
        spans=[r for r in rs if r.get("span")]
        fab=sum(1 for r in spans if r.get("span_verbatim") is False)
        out[mk]={
          "decisions":len(rs),
          "cry_wolf":{"k":cw,"n":len(pre),"rate":cw/max(len(pre),1),"ci":wilson(cw,len(pre))},
          "caught":  {"k":ct,"n":len(at), "rate":ct/max(len(at),1), "ci":wilson(ct,len(at))},
          "ratchet_after_signal":{"k":rt,"n":len(post),"rate":rt/max(len(post),1)},
          "stuck_high_after_catching":{"k":stuck,"n":stuck_n,"rate":stuck/max(stuck_n,1)},
          "fabricated_span":{"k":fab,"n":len(spans),"rate":fab/max(len(spans),1)},
          "cost":round(sum(r.get("cost",0) for r in rs),4),
        }
    io.open("bench/scores_sequential.json","w",encoding="utf-8").write(json.dumps(out,indent=1,ensure_ascii=False))
    print(f"{'model':22s} {'caught':>10s} {'cry-wolf':>10s} {'stuck-high':>12s} {'fabricated':>11s} {'cost':>7s}")
    for mk,s in out.items():
        print(f"{mk:22s} {s['caught']['k']:>4d}/{s['caught']['n']:<5d} "
              f"{s['cry_wolf']['rate']*100:>9.1f}% {s['stuck_high_after_catching']['rate']*100:>11.1f}% "
              f"{s['fabricated_span']['rate']*100:>10.1f}% ${s['cost']:>6.2f}")
if __name__=="__main__": main()
