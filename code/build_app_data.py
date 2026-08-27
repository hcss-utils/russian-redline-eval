#!/usr/bin/env python3
"""Generate the app's MODELS[] and PASSAGES[] from measured results. Nothing typed."""
import json, io, os, collections, statistics, re

# PAYLOAD KEYS ARE NEUTRAL AND CANONICAL: "flagged" (per passage) and "flag_rate" (per
# model). They mean naive-substring-flagged, which is NOT fabricated -- all 283 flagged
# spans were read and 0 were inventions. The deployed view still uses the historical
# short names; that spelling is confined to ONE named adapter in the app (adaptLegacyKeys).
# The "fabricated" INPUT key is still accepted as a read fallback for older score files.
# Passage text comes from the PUBLISHED benchmark file. It was previously read from an
# unreleased reference set, which made this script unrunnable for anyone outside the
# project -- and, when that file went missing locally, unrunnable for us too. The
# private set is now only an optional override for the wider 298-item pool.
GOLD_DIR = os.environ.get("GOLD_DIR", "./gold_certification")

HERE=os.path.dirname(os.path.abspath(__file__))
_REPO=os.path.dirname(HERE)
# published layout: code/ holds scripts, results/ holds data
def _data(name):
    for c in (os.path.join(_REPO,"results",name), os.path.join(_REPO,"data",name), os.path.join(HERE,name)):
        if os.path.exists(c): return c
    return os.path.join(_REPO,"results",name)
RES=_data("results_sweep.jsonl")
SCO=json.load(io.open(_data("scores.json"),encoding="utf-8"))
SAMP={r["chunk_id"]:r for r in json.load(io.open(_data("sample_representative_100.json"),encoding="utf-8"))}
_BENCH=json.load(io.open(_data("benchmark_100.json"),encoding="utf-8"))
_BENCH=_BENCH if isinstance(_BENCH,list) else _BENCH.get("items",_BENCH.get("passages",[]))
TXT={r["chunk_id"]:(r.get("text") or r.get("content") or "") for r in _BENCH}
_priv=os.path.join(GOLD_DIR,"scripts","gold298_rows.json")   # optional: the wider 298 pool
if os.path.exists(_priv):
    _raw=io.open(_priv,encoding="utf-8").read()
    for r in json.loads(_raw[_raw.index("["):]): TXT.setdefault(r["chunk_id"],r["content"])
_missing=[c for c in SAMP if c not in TXT]
if _missing:
    raise SystemExit(f"passage text missing for {len(_missing)} chunk_ids, e.g. {_missing[:3]}")

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
# Confusion matrix, false nuclear alerts and missed nuclear signals, DERIVED from every
# decision record. These were previously invented in the app from fixed ratios
# (fa*0.65, rest*0.6) with a remainder cell that could go negative, and `fa` was wrongly
# set to the `missed` count, so False Alerts equalled Missed Nuclear for every model.
_L=["None","RLS","NTS"]
def _ref(r):  return "NTS" if r["gold_nts"]=="Y" else ("RLS" if r["gold_rls"]=="Y" else "None")
def _pred(r):
    v=r.get("verdict")
    if not r.get("parsed") or not v: return None
    return "NTS" if v.get("nts")=="Y" else ("RLS" if v.get("rls")=="Y" else "None")
CM=collections.defaultdict(lambda: {a:{b:0 for b in _L} for a in _L})
# A matrix over PARSED verdicts has a smaller denominator than the attempted run whenever
# a configuration failed to return a usable answer. Five did (qwen3.7-max 11, opus-5-nothink
# and glm-5.2 2 each, opus-5-think and kimi-k3 1 each; 17 of 2,800 overall). Carry both
# counts so the page can state the denominator it is actually using instead of asserting 200.
ATT=collections.Counter(); PARS=collections.Counter()
for r in rows:
    k=r.get("model_key"); ATT[k]+=1
    pr=_pred(r)
    if pr is not None:
        PARS[k]+=1
        CM[k][_ref(r)][pr]+=1
def _cm(k):  return [[CM[k][a][b] for b in _L] for a in _L]
def _fa(k):  return CM[k]["None"]["NTS"]+CM[k]["RLS"]["NTS"]   # nuclear alert, reference is not NTS
def _mn(k):  return CM[k]["NTS"]["None"]+CM[k]["NTS"]["RLS"]   # real nuclear signal not called NTS

# TWO RATES SHARE THE NAME "naive-flag rate" and differ by DENOMINATOR: scores.json's
# naive_flagged is per RECORD (a decision carrying at least one flagged span, 2.5-45.8%),
# while the leaderboard and Findings text quote per SPAN (1.7-42.2%). Emitting the record
# rate into a column the page labels with the span rate put the producer and the page in
# disagreement -- invisible until the two were compared. Emit the SPAN rate; the record
# rate stays available in scores.json under its own name.
try:
    _CIT = json.load(io.open(_data("citation_check_summary.json"), encoding="utf-8"))["per_model"]
except Exception:
    _CIT = {}
def _span_rate(k, m):
    e = _CIT.get(k)
    if e and e.get("spans"):
        return round(e["flagged"] / e["spans"], 4)
    return (m.get("naive_flagged") or m.get("fabricated"))["rate"]

# SHORT names are the column headers on the Cases tab, so they must be UNIQUE. The rule
# was n.split()[0], which gave 'Claude' to five configurations and collapsed fourteen
# columns to seven names -- every rebuilt page then mapped Cases cells to the wrong
# model. These are the curated reader-facing names.
SHORT={
 "fable_5": "Fable 5",
 "opus_5_think": "Opus 5 +think",
 "opus_5_nothink": "Opus 5 −think",
 "sonnet_5": "Sonnet 5",
 "haiku_4_5": "Haiku 4.5",
 "gpt_5_6_sol": "GPT Sol",
 "gpt_5_6_terra": "GPT Terra",
 "gpt_5_6_luna": "GPT Luna",
 "gemini_3_6_flash": "Gemini Flash",
 "deepseek_v4_pro": "DS V4 Pro",
 "deepseek_v4_flash": "DS V4 Flash",
 "qwen3_7_max": "Qwen3.7",
 "glm_5_2": "GLM-5.2",
 "kimi_k3": "Kimi K3"
}

for k in keys:
    m=SCO["models"][k]; n,prov,slug=DISPLAY[k]
    models.append(dict(k=SAFE(k), n=n, short=SHORT.get(SAFE(k), n.split()[0]), prov=prov, slug=slug,
        price=LIST[k], f1=f1(k,"rls"), rls=m["rls_incl"]["acc"], nts=m["nts_incl"]["acc"],
        rlsrec=m["rls_incl"]["recall"], ntsrec=m["nts_incl"]["recall"],
        fa=_fa(k), mn=_mn(k), cm=_cm(k), attempted=ATT[k], parsed=PARS[k], no_answer=ATT[k]-PARS[k],
        flag_rate=_span_rate(k, m), refus=m["refusals"], schema=round(100*(m["n"]/(m["n"]+m["unparsed"]+m["errors"])),1),
        consis=m["rep_consistency"], secs=m["mean_secs"], cost=m["est_cost"], flip=None))

# passages: first rep only, per model verdict
byitem=collections.defaultdict(dict)
for r in ok:
    if r["rep"]==1: byitem[r["chunk_id"]][r["model_key"]]=r
passages=[]
for i,(cid,per) in enumerate(sorted(byitem.items()), 1):
    s=SAMP[cid]
    ref = "NTS" if s["gold_nts"]=="Y" else ("RLS" if s["gold_rls"]=="Y" else "None")
    verd={}; just={}; flagged={}
    for k in keys:
        r=per.get(k)
        if not r: verd[SAFE(k)]="n/a"; continue
        v=r["verdict"]
        verd[SAFE(k)] = "NTS" if v.get("nts")=="Y" else ("RLS" if v.get("rls")=="Y" else "None")
        rat=v.get("nts_rationale") if v.get("nts")=="Y" else v.get("rls_rationale")
        if rat: just[SAFE(k)]=rat
        if r.get("rls_ev_verbatim") is False or r.get("nts_ev_verbatim") is False:
            flagged[SAFE(k)]=True
    agree=sum(1 for k in keys if verd.get(SAFE(k))==ref)
    passages.append(dict(id=f"#{i:03d}", cid=cid, ref=ref, sp=s.get("src") or "n/a",
        yr=(s.get("date") or "")[:4] or "n/a", ru=TXT[cid], en=None,
        cue=(s.get("database") or ""), agree=agree, n_models=len(keys),
        v=verd, j=just, flagged=flagged, tokens=s["tokens"]))

out=dict(generated_from=os.path.basename(RES), n_records=SCO["n_records"], spend=SCO["spend_usd"],
         n_items=len(passages), n_models=len(keys), models=models, passages=passages)
io.open(os.path.join(HERE,"app_data.json"),"w",encoding="utf-8").write(json.dumps(out,ensure_ascii=False))
print(f"models={len(models)} passages={len(passages)} "
      f"flagged_spans={sum(len(p['flagged']) for p in passages)} "
      f"justifications={sum(len(p['j']) for p in passages)}")
print("wrote app_data.json", os.path.getsize(os.path.join(HERE,"app_data.json")), "bytes")
