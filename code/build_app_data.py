#!/usr/bin/env python3
"""Generate the app's MODELS[] and PASSAGES[] from measured results. Nothing typed."""
import json, io, os, collections, statistics, re
import os
# Local corpus paths are machine-specific and are read from the environment.
# GOLD_DIR should point at the reference-set directory; the published data/
# files in this repo are the outputs, so nothing here is needed to re-score.
GOLD_DIR = os.environ.get("GOLD_DIR", "./gold_certification")

HERE=os.path.dirname(os.path.abspath(__file__))
RES=os.path.join(HERE,"results_sweep.jsonl")
SCO=json.load(io.open(os.path.join(HERE,"scores.json"),encoding="utf-8"))
SAMP={r["chunk_id"]:r for r in json.load(io.open(os.path.join(HERE,"sample_representative_100.json"),encoding="utf-8"))}
raw=io.open("" + GOLD_DIR + "/scripts/gold298_rows.json",encoding="utf-8").read()
TXT={r["chunk_id"]:r["content"] for r in json.loads(raw[raw.index("["):])}

DISPLAY={ "fable-5":("Claude Fable 5","Anthropic","claude-fable-5"),
 "opus-5-think":("Claude Opus 5 (thinking)","Anthropic","claude-opus-5"),
 "opus-5-nothink":("Claude Opus 5 (no thinking)","Anthropic","claude-opus-5"),
 "sonnet-5":("Claude Sonnet 5","Anthropic","claude-sonnet-5"),
 "haiku-4.5":("Claude Haiku 4.5","Anthropic","claude-haiku-4-5"),
 "gpt-5.6-sol":("GPT-5.6 Sol","OpenAI","gpt-5.6-sol"),
 "gpt-5.6-terra":("GPT-5.6 Terra","OpenAI","gpt-5.6-terra"),
 "gpt-5.6-luna":("GPT-5.6 Luna","OpenAI","gpt-5.6-luna"),
 "gemini-3.6-flash":("Gemini 3.6 Flash","Google","gemini-3.6-flash"),
 "deepseek-v4-pro":("DeepSeek V4 Pro","DeepSeek","deepseek-v4-pro"),
 "deepseek-v4-flash":("DeepSeek V4 Flash","DeepSeek","deepseek-v4-flash"),
 "qwen3.7-max":("Qwen3.7-Max","Alibaba","qwen3.7-max"),
 "glm-5.2":("GLM-5.2","Zhipu AI","glm-5.2"),
 "kimi-k3":("Kimi K3","Moonshot","kimi-k3")}
LIST={"fable-5":"$10 / $50","opus-5-think":"$5 / $25","opus-5-nothink":"$5 / $25","sonnet-5":"$3 / $15",
 "haiku-4.5":"$1 / $5","gpt-5.6-sol":"$4 / $20","gpt-5.6-terra":"$2 / $12","gpt-5.6-luna":"$0.20 / $1.20",
 "gemini-3.6-flash":"$0.75 / $3.75","deepseek-v4-pro":"$0.66 / $1.98","deepseek-v4-flash":"$0.22 / $0.66",
 "qwen3.7-max":"$1.20 / $6.00","glm-5.2":"$0.60 / $2.20","kimi-k3":"$1.00 / $3.00"}
SAFE=lambda k: re.sub(r'[^a-z0-9]','_',k)

rows=[json.loads(l) for l in io.open(RES,encoding="utf-8")]
ok=[r for r in rows if r.get("parsed")]
keys=[k for k in DISPLAY if k in SCO["models"]]

def f1(mk, layer):
    v=[r for r in ok if r["model_key"]==mk]
    tp=sum(1 for r in v if r["verdict"].get(layer)=="Y" and r["gold_"+layer]=="Y")
    fp=sum(1 for r in v if r["verdict"].get(layer)=="Y" and r["gold_"+layer]=="N")
    fn=sum(1 for r in v if r["verdict"].get(layer)!="Y" and r["gold_"+layer]=="Y")
    p=tp/(tp+fp) if tp+fp else 0; rc=tp/(tp+fn) if tp+fn else 0
    return round(2*p*rc/(p+rc),3) if p+rc else 0.0

models=[]
for k in keys:
    m=SCO["models"][k]; n,prov,slug=DISPLAY[k]
    models.append(dict(k=SAFE(k), n=n, short=n.split()[0], prov=prov, slug=slug,
        price=LIST[k], f1=f1(k,"rls"), rls=m["rls_incl"]["acc"], nts=m["nts_incl"]["acc"],
        rlsrec=m["rls_incl"]["recall"], ntsrec=m["nts_incl"]["recall"],
        fa=m["nts_incl"]["missed"], mn=m["nts_incl"]["missed"],
        fabr=m["fabricated"]["rate"], refus=m["refusals"], schema=round(100*(m["n"]/(m["n"]+m["unparsed"]+m["errors"])),1),
        consis=m["rep_consistency"], secs=m["mean_secs"], cost=m["est_cost"], flip=None))

# passages: first rep only, per model verdict
byitem=collections.defaultdict(dict)
for r in ok:
    if r["rep"]==1: byitem[r["chunk_id"]][r["model_key"]]=r
passages=[]
for i,(cid,per) in enumerate(sorted(byitem.items()), 1):
    s=SAMP[cid]
    ref = "NTS" if s["gold_nts"]=="Y" else ("RLS" if s["gold_rls"]=="Y" else "None")
    verd={}; just={}; fab={}
    for k in keys:
        r=per.get(k)
        if not r: verd[SAFE(k)]="n/a"; continue
        v=r["verdict"]
        verd[SAFE(k)] = "NTS" if v.get("nts")=="Y" else ("RLS" if v.get("rls")=="Y" else "None")
        rat=v.get("nts_rationale") if v.get("nts")=="Y" else v.get("rls_rationale")
        if rat: just[SAFE(k)]=rat
        if r.get("rls_ev_verbatim") is False or r.get("nts_ev_verbatim") is False:
            fab[SAFE(k)]=True
    agree=sum(1 for k in keys if verd.get(SAFE(k))==ref)
    passages.append(dict(id=f"#{i:03d}", cid=cid, ref=ref, sp=s.get("src") or "n/a",
        yr=(s.get("date") or "")[:4] or "n/a", ru=TXT[cid], en=None,
        cue=(s.get("database") or ""), agree=agree, n_models=len(keys),
        v=verd, j=just, fab=fab, tokens=s["tokens"]))

out=dict(generated_from=os.path.basename(RES), n_records=SCO["n_records"], spend=SCO["spend_usd"],
         n_items=len(passages), n_models=len(keys), models=models, passages=passages)
io.open(os.path.join(HERE,"app_data.json"),"w",encoding="utf-8").write(json.dumps(out,ensure_ascii=False))
print(f"models={len(models)} passages={len(passages)} "
      f"fab_marks={sum(len(p['fab']) for p in passages)} "
      f"justifications={sum(len(p['j']) for p in passages)}")
print("wrote app_data.json", os.path.getsize(os.path.join(HERE,"app_data.json")), "bytes")
