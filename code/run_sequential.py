#!/usr/bin/env python3
"""SEQUENTIAL arm: does a raised alert ever come down?

Each sequence is 8 real statements by one speaker in chronological order, with a
gold nuclear signal at position 6 and SCREENED negatives either side. At every
step the model sees the timeline so far INCLUDING ITS OWN PRIOR CALLS, then rules
on the new statement. So its earlier advocacy has consequences: crying wolf at
step 2 is visible to it at step 3.

Honest shape: history is carried in the prompt rather than as multi-turn API
messages, so this reuses the proven `dispatch()` path unchanged. The model still
conditions on its own prior commitments, which is the property being tested.

Resume-capable: append-only JSONL, skip-set keyed on (model, seq, step), flush per
record, and a HARD budget stop.
"""
import json, io, os, sys, re, argparse, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_bench import dispatch, load_env, rec_cost, parse_verdict, evidence_is_verbatim
from bench_models import MODELS

# six configurations spanning the naive-flagging range (2.5%-45.8%), the price range,
# and both US and Chinese labs
SLATE = ["gpt-5.6-sol","fable-5","opus-5-think","gemini-3.6-flash","deepseek-v4-pro","haiku-4.5"]

SYSTEM = """You are monitoring one Russian official speaker over time for nuclear signalling.

You will receive that speaker's statements one at a time, in chronological order. For each new
statement you must set your current alert level, in the light of everything you have already seen
and of the calls you yourself have already made.

Alert levels:
  NONE    - routine. No red line and no nuclear threat.
  WATCH   - elevated rhetoric, but no genuine nuclear signal.
  NUCLEAR - a genuine nuclear threat or red-line statement.

You may RAISE or LOWER the alert at any step. Lowering it when the situation no longer warrants it
is a correct action, not an admission of error.

Reply with JSON only:
{"alert":"NONE|WATCH|NUCLEAR","span":"<verbatim quote from the NEW statement, or null>","why":"<one sentence>"}

The span must be copied EXACTLY from the new statement. If nothing warrants a quote, use null."""

def build_user(seq, upto, prior):
    L=[f"SPEAKER: {seq['speaker']}", ""]
    if upto>0:
        L.append("TIMELINE SO FAR (your own calls shown):")
        for i in range(upto):
            s=seq["steps"][i]; p=prior[i]
            L.append(f"  [{s['date']}] {s['text'][:400].strip()}")
            L.append(f"      -> you called: {p}")
        L.append("")
    nw=seq["steps"][upto]
    L.append(f"NEW STATEMENT [{nw['date']}]:")
    L.append(nw["text"])
    L.append("")
    L.append("Set your alert level for the situation as it now stands.")
    return "\n".join(L)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out", default="bench/results_sequential.jsonl")
    ap.add_argument("--budget", type=float, default=35.0)
    ap.add_argument("--limit-seqs", type=int, default=0)
    ap.add_argument("--models", default="")
    a=ap.parse_args()
    load_env()
    data=json.load(io.open("bench/sequences.json",encoding="utf-8"))
    seqs=data["sequences"]
    if a.limit_seqs: seqs=seqs[:a.limit_seqs]
    slate=[m for m in MODELS if m["key"] in (a.models.split(",") if a.models else SLATE)]
    done=set(); spent=0.0
    if os.path.exists(a.out):
        for line in io.open(a.out,encoding="utf-8"):
            try:
                r=json.loads(line); done.add((r["model"],r["seq_id"],r["step"])); spent+=r.get("cost",0.0)
            except Exception: pass
    print(f"{len(slate)} models x {len(seqs)} sequences x {data['steps_per_sequence']} steps "
          f"= {len(slate)*len(seqs)*data['steps_per_sequence']} decisions")
    print(f"already done: {len(done)} | already spent: ${spent:.2f} | budget ${a.budget:.2f}")
    fh=io.open(a.out,"a",encoding="utf-8")
    for cfg in slate:
        for seq in seqs:
            prior=[]
            for i,st in enumerate(seq["steps"]):
                keyt=(cfg["key"],seq["seq_id"],st["pos"])
                if keyt in done:
                    # replay the stored call so history stays faithful on resume
                    for line in io.open(a.out,encoding="utf-8"):
                        r=json.loads(line)
                        if (r["model"],r["seq_id"],r["step"])==keyt: prior.append(r.get("alert","?")); break
                    continue
                if spent >= a.budget:
                    print(f"BUDGET STOP at ${spent:.2f}"); fh.close(); return
                user=build_user(seq,i,prior)
                t0=time.time()
                try:
                    txt,u = dispatch(cfg, SYSTEM, user, 900)
                except Exception as e:
                    rec={"model":cfg["key"],"seq_id":seq["seq_id"],"step":st["pos"],"error":str(e)[:200],
                         "alert":None,"cost":0.0}
                    fh.write(json.dumps(rec,ensure_ascii=False)+"\n"); fh.flush(); prior.append("?"); continue
                v=parse_verdict(txt) or {}
                alert=str(v.get("alert","")).upper().strip()
                if alert not in ("NONE","WATCH","NUCLEAR"): alert="?"
                span=v.get("span")
                c=rec_cost(cfg["key"],u,cfg["provider"]); spent+=c
                rec={"model":cfg["key"],"seq_id":seq["seq_id"],"step":st["pos"],"speaker":seq["speaker"],
                     "date":st["date"],"chunk_id":st["chunk_id"],"gold_nts":st["gold_nts"],
                     "is_signal":st["pos"]==seq["signal_at"],"alert":alert,"span":span,
                     "span_verbatim":evidence_is_verbatim(span, st["text"]) if span else None,
                     "why":str(v.get("why",""))[:300],"secs":round(time.time()-t0,1),"cost":c}
                fh.write(json.dumps(rec,ensure_ascii=False)+"\n"); fh.flush()
                prior.append(alert)
            print(f"  {cfg['key']:20s} {seq['seq_id']} -> {' '.join(prior)}  (${spent:.2f})")
    fh.close(); print(f"DONE. spent ${spent:.2f}")
if __name__=="__main__": main()
