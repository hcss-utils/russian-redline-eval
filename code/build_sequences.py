#!/usr/bin/env python3
"""Build chronological per-speaker sequences for the SEQUENTIAL arm.

Design. Each sequence is 8 statements by ONE speaker in real chronological order:

    positions 1-5  verified-negative run-up   (nts_annotation_signaling.is_relevant = false)
    position  6    a gold NTS-positive        (the real escalation)
    positions 7-8  verified-negative aftermath

That yields three measurements a static benchmark cannot make:
  * false alarms BEFORE the signal (5 chances to cry wolf)
  * detection AT the signal
  * de-escalation AFTER it -- does a raised alert ever come down?

Negatives are screened, not assumed: is_relevant=false comes from the NTS screening
pass that covers all 296,381 chunks. Deterministic: seed 20260901, sorted inputs.
"""
import json, io, os, subprocess, random, sys

SEED=20260901; STEPS=8; POS_AT=6; MINTOK=50
# Connection comes from the environment; no host, path or credential is baked in.
#   REDLINES_PGHOST / REDLINES_PGPORT / REDLINES_PGUSER / REDLINES_PGDATABASE / PGPASSWORD
DB   = os.environ.get("REDLINES_PGDATABASE","redlines")
HOST = os.environ.get("REDLINES_PGHOST","127.0.0.1")
PORT = os.environ.get("REDLINES_PGPORT","5432")
USER = os.environ.get("REDLINES_PGUSER","postgres")

def sql(q):
    """Run one query against the corpus and return raw stdout.

    The corpus is the project's own Postgres instance; it is not public. The
    sequences this produces ARE published (data/sequences.json), so the arm is
    reproducible from the data even without database access.
    """
    cmd=["psql","-h",HOST,"-p",PORT,"-U",USER,"-d",DB,"-tAc",q]
    r=subprocess.run(cmd,capture_output=True,text=True,timeout=600)
    if r.returncode!=0: raise SystemExit("SQL failed: "+r.stderr[:400])
    return r.stdout

def main():
    b=json.load(io.open("bench/sample_representative_100.json",encoding="utf-8"))
    items=b["items"] if isinstance(b,dict) and "items" in b else b
    pos=sorted([str(i["chunk_id"]) for i in items
                if str(i.get("gold_nts","")).upper() in ("Y","YES","TRUE","1")])
    ids=",".join(pos)
    q=(f"select json_agg(row_to_json(t)) from (with p as ("
       f" select c.id cid, d.author au, d.date dt from document_chunk c join document d on d.id=c.document_id"
       f" where c.id in ({ids}) and d.author is not null)"
       f" select p.cid, p.au, p.dt::text,"
       f"  (select json_agg(x) from (select c2.id, d2.date::text dd, left(c2.content,4000) txt"
       f"     from document_chunk c2 join document d2 on d2.id=c2.document_id"
       f"     left join nts_annotation_signaling s on s.chunk_id=c2.id"
       f"    where d2.author=p.au and d2.date < p.dt and coalesce(s.is_relevant,false)=false"
       f"      and c2.tokens >= {MINTOK} order by d2.date desc, c2.id desc limit {POS_AT-1}) x) as before,"
       f"  (select json_agg(y) from (select c3.id, d3.date::text dd, left(c3.content,4000) txt"
       f"     from document_chunk c3 join document d3 on d3.id=c3.document_id"
       f"     left join nts_annotation_signaling s3 on s3.chunk_id=c3.id"
       f"    where d3.author=p.au and d3.date > p.dt and coalesce(s3.is_relevant,false)=false"
       f"      and c3.tokens >= {MINTOK} order by d3.date asc, c3.id asc limit {STEPS-POS_AT}) y) as after,"
       f"  (select left(content,4000) from document_chunk where id=p.cid) as postxt"
       f" from p) t;")
    rows=json.loads(sql(q).strip() or "[]")
    random.Random(SEED).shuffle(rows)
    seqs=[]; skipped=[]
    for r in sorted(rows, key=lambda z: str(z["cid"])):
        bef=r.get("before") or []; aft=r.get("after") or []
        if len(bef)<POS_AT-1 or len(aft)<STEPS-POS_AT:
            skipped.append({"chunk_id":r["cid"],"speaker":r["au"],
                            "before":len(bef),"after":len(aft)}); continue
        steps=[{"pos":i+1,"chunk_id":str(s["id"]),"date":s["dd"],"text":s["txt"],"gold_nts":"N"}
               for i,s in enumerate(reversed(bef))]
        steps.append({"pos":POS_AT,"chunk_id":str(r["cid"]),"date":r["dt"],"text":r["postxt"],"gold_nts":"Y"})
        steps+= [{"pos":POS_AT+1+i,"chunk_id":str(s["id"]),"date":s["dd"],"text":s["txt"],"gold_nts":"N"}
                 for i,s in enumerate(aft)]
        seqs.append({"seq_id":f"S{len(seqs)+1:03d}","speaker":r["au"],
                     "signal_at":POS_AT,"signal_chunk_id":str(r["cid"]),"steps":steps})
    out={"seed":SEED,"steps_per_sequence":STEPS,"signal_position":POS_AT,
         "min_tokens":MINTOK,"n_sequences":len(seqs),
         "negatives_are":"screened is_relevant=false, not assumed",
         "skipped_for_insufficient_history":skipped,"sequences":seqs}
    io.open("bench/sequences.json","w",encoding="utf-8").write(json.dumps(out,ensure_ascii=False,indent=1))
    print(f"sequences built: {len(seqs)}  (skipped {len(skipped)} for thin history)")
    for s in seqs[:3]:
        print(f"  {s['seq_id']} {s['speaker'][:28]:28s} {s['steps'][0]['date']} -> {s['steps'][-1]['date']}")
if __name__=="__main__": main()
