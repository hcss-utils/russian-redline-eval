#!/usr/bin/env python3
"""RUBICON scorer. Every number derived from results_sweep.jsonl -- nothing hardcoded."""
import json, io, collections, statistics, math, sys, os
HERE=os.path.dirname(os.path.abspath(__file__))
_REPO=os.path.dirname(HERE)
# published layout: code/ holds scripts, results/ holds data
def _data(name):
    for c in (os.path.join(_REPO,"results",name), os.path.join(_REPO,"data",name), os.path.join(HERE,name)):
        if os.path.exists(c): return c
    return os.path.join(_REPO,"results",name)
RES=_data("results_sweep.jsonl")

def strict(v,l):
    return 'Y' if (v.get(l)=='Y' and v.get(l+'_line_explicit')=='Y' and v.get(l+'_threat_explicit')=='Y') else 'N'
def wilson(k,n,z=1.96):
    if n==0: return (0.0,0.0)
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d
    h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return (max(0,c-h), min(1,c+h))

def main():
    rows=[json.loads(l) for l in io.open(RES,encoding="utf-8")]
    ok=[r for r in rows if r.get("parsed")]
    errs=[r for r in rows if "error" in r]
    unp=[r for r in rows if r.get("parsed") is False]
    models=sorted({r["model_key"] for r in rows})
    items=sorted({r["chunk_id"] for r in ok})
    out={"n_records":len(rows),"n_parsed":len(ok),"n_errors":len(errs),"n_unparsed":len(unp),
         "n_items":len(items),"n_models":len(models),
         "spend_usd":round(sum(r.get("est_cost",0) or 0 for r in rows),2),"models":{}}

    for mk in models:
        v=[r for r in ok if r["model_key"]==mk]
        me=[r for r in rows if r["model_key"]==mk]
        d={"n":len(v),"errors":sum(1 for r in me if "error" in r),
           "refusals":sum(1 for r in me if "inappropriate" in (r.get("error") or "")),
           "unparsed":sum(1 for r in me if r.get("parsed") is False)}
        for layer in ("rls","nts"):
            pos=[r for r in v if r["gold_"+layer]=="Y"]; neg=[r for r in v if r["gold_"+layer]=="N"]
            for mode,pred in (("incl",lambda r:r["verdict"].get(layer)),("strict",lambda r:strict(r["verdict"],layer))):
                acc=sum(1 for r in v if pred(r)==r["gold_"+layer])/len(v) if v else 0
                rec=sum(1 for r in pos if pred(r)=="Y")/len(pos) if pos else None
                fpr=sum(1 for r in neg if pred(r)=="Y")/len(neg) if neg else None
                lo,hi=wilson(sum(1 for r in v if pred(r)==r["gold_"+layer]),len(v))
                d[f"{layer}_{mode}"]={"acc":round(acc,3),"acc_ci":[round(lo,3),round(hi,3)],
                                      "recall":round(rec,3) if rec is not None else None,
                                      "fpr":round(fpr,3) if fpr is not None else None,
                                      "missed":sum(1 for r in pos if pred(r)!="Y"),"n_pos":len(pos)}
        # naive_flagged evidence
        fab=sum(1 for r in v if r.get("rls_ev_verbatim") is False or r.get("nts_ev_verbatim") is False)
        claimed=sum(1 for r in v if r.get("rls_ev_verbatim") is not None or r.get("nts_ev_verbatim") is not None)
        d["naive_flagged"]={"n":fab,"of_claimed":claimed,"rate":round(fab/claimed,3) if claimed else None}
        # confidence calibration
        cc=[(r["verdict"].get("rls_confidence"), r["verdict"].get("rls")==r["gold_rls"]) for r in v
            if isinstance(r["verdict"].get("rls_confidence"),(int,float))]
        if cc:
            hi_=[c for c,_ in cc if c>=8]; d["conf"]={
                "mean_when_right":round(statistics.mean([c for c,ok_ in cc if ok_]),2) if any(o for _,o in cc) else None,
                "mean_when_wrong":round(statistics.mean([c for c,ok_ in cc if not ok_]),2) if any(not o for _,o in cc) else None,
                "acc_at_conf_ge8":round(sum(1 for c,o in cc if c>=8 and o)/len(hi_),3) if hi_ else None}
        # cross-rep consistency
        byitem=collections.defaultdict(list)
        for r in v: byitem[r["chunk_id"]].append(r["verdict"].get("rls"))
        pairs=[x for x in byitem.values() if len(x)>=2]
        d["rep_consistency"]=round(sum(1 for x in pairs if len(set(x[:2]))==1)/len(pairs),3) if pairs else None
        d["mean_secs"]=round(statistics.mean([r["secs"] for r in v]),1) if v else None
        d["est_cost"]=round(sum(r.get("est_cost",0) or 0 for r in me),2)
        out["models"][mk]=d
    json.dump(out, io.open(_data("scores.json"),"w",encoding="utf-8"), indent=1, ensure_ascii=False)

    print(f"records {out['n_records']}  parsed {out['n_parsed']}  errors {out['n_errors']}  "
          f"unparsed {out['n_unparsed']}  items {out['n_items']}  spend ${out['spend_usd']}\n")
    print(f"{'model':18s} {'RLSacc':>7s} {'RLSrec':>7s} {'NTSacc':>7s} {'NTSmiss':>8s} "
          f"{'flag%':>6s} {'refus':>6s} {'consis':>7s} {'$':>6s}")
    for mk in sorted(models, key=lambda m: -(out["models"][m]["nts_incl"]["acc"])):
        d=out["models"][mk]
        print(f"{mk:18s} {d['rls_incl']['acc']:7.3f} {(d['rls_incl']['recall'] or 0):7.3f} "
              f"{d['nts_incl']['acc']:7.3f} {d['nts_incl']['missed']:4d}/{d['nts_incl']['n_pos']:<3d} "
              f"{(d['naive_flagged']['rate'] or 0):6.3f} {d['refusals']:6d} "
              f"{(d['rep_consistency'] or 0):7.3f} {d['est_cost']:6.2f}")
    print("\nwrote scores.json")

if __name__=="__main__": main()
