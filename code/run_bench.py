#!/usr/bin/env python3
"""RedLineBench runner. Resume-capable, append-only, token-accounting.

Modes
  probe : one trivial call per model config -> verifies key + model id, prints the
          provider's literal error. Model ids for several providers are unverified
          guesses; a failure here means FIND THE REAL ID, never substitute another model.
  pilot : N items x langs x 1 rep -> measures REAL prompt/completion/reasoning tokens.
  run   : the full sweep.

Resume contract (rule 6b): output opened 'a', never 'w'; a skip-set is built from the
existing file keyed on (model_key, chunk_id, lang, rep); one flush per record.
"""
import argparse, io, json, os, re, sys, time, hashlib, threading
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench_models as REG

PRICE = {  # $/MTok (in, out) list price; batch not used for sync run
 "fable-5":(10,50), "opus-5-think":(5,25), "opus-5-nothink":(5,25), "sonnet-5":(3,15),
 "haiku-4.5":(1,5), "gpt-5.6-sol":(4,20), "gpt-5.6-terra":(2,12), "gpt-5.6-luna":(0.2,1.2),
 "gemini-3.6-flash":(0.75,3.75), "deepseek-v4-pro":(0.66,1.98), "deepseek-v4-flash":(0.22,0.66),
 "qwen3.7-max":(1.2,6.0), "glm-5.2":(0.6,2.2), "kimi-k3":(1.0,3.0), "minimax-m3":(1.0,3.0),
}
def rec_cost(mk, u, provider):
    pi, po = PRICE.get(mk, (2.0, 8.0))
    cr = u.get("cache_read") or 0
    fresh = (u.get("prompt") or 0) if provider == "anthropic" else max(0, (u.get("prompt") or 0) - cr)
    out = (u.get("completion") or 0) + ((u.get("reasoning") or 0) if mk == "gemini-3.6-flash" else 0)
    return (fresh*pi + cr*pi*0.10 + (u.get("cache_write") or 0)*pi*1.25)/1e6 + out*po/1e6

SYSTEM = io.open(os.path.join(HERE, "prompt", "system_v2.md"), encoding="utf-8").read()
USER_T = io.open(os.path.join(HERE, "prompt", "user_template_v2.md"), encoding="utf-8").read()

def load_env():
    env = {}
    # Provider keys are read from a dotenv file. Point CREDENTIALS_ENV at your own;
    # no key material is contained in or committed to this repository.
    path = os.environ.get("CREDENTIALS_ENV", os.path.expanduser("~/.rubicon.env"))
    for line in io.open(path, encoding="utf-8", errors="replace"):
        line = line.rstrip("\r\n").strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1); env[k.strip()] = v.strip().strip('"').strip("'")
    return env
ENV = load_env()

def key_for(cfg):
    return {"anthropic":"ANTHROPIC_API_KEY","openai":"OPENAI_API_KEY","gemini":"GEMINI_API_KEY"}.get(
        cfg["provider"], cfg.get("key_env"))

# ---------------------------------------------------------------- adapters
def call_anthropic(cfg, system, user, max_tokens):
    import anthropic
    c = anthropic.Anthropic(api_key=ENV[key_for(cfg)])
    kw = dict(model=cfg["model"], max_tokens=max_tokens,
              system=[{"type":"text","text":system,"cache_control":{"type":"ephemeral"}}],
              messages=[{"role":"user","content":user}])
    if cfg["model"] != "claude-fable-5":                    # fable: thinking always on, param rejected
        kw["thinking"] = {"type":"adaptive"} if cfg["reasoning"] else {"type":"disabled"}
    r = c.messages.create(**kw)
    text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
    u = r.usage
    return text, dict(prompt=u.input_tokens, completion=u.output_tokens,
                      cache_read=getattr(u,"cache_read_input_tokens",0) or 0,
                      cache_write=getattr(u,"cache_creation_input_tokens",0) or 0,
                      reasoning=None, stop=r.stop_reason)

def call_openai_like(cfg, system, user, max_tokens, base_url=None):
    import openai
    c = openai.OpenAI(api_key=ENV[key_for(cfg)], base_url=base_url or cfg.get("base_url"))
    kw = dict(model=cfg["model"],
              messages=[{"role":"system","content":system},{"role":"user","content":user}])
    try:
        r = c.chat.completions.create(max_completion_tokens=max_tokens, **kw)
    except Exception:
        r = c.chat.completions.create(max_tokens=max_tokens, **kw)
    text = r.choices[0].message.content or ""
    u = r.usage
    det = getattr(u, "completion_tokens_details", None)
    return text, dict(prompt=u.prompt_tokens, completion=u.completion_tokens,
                      cache_read=getattr(getattr(u,"prompt_tokens_details",None),"cached_tokens",0) or 0,
                      cache_write=0,
                      reasoning=getattr(det,"reasoning_tokens",None) if det else None,
                      stop=r.choices[0].finish_reason)

def call_gemini(cfg, system, user, max_tokens):
    from google import genai
    from google.genai import types
    c = genai.Client(api_key=ENV[key_for(cfg)])
    r = c.models.generate_content(model=cfg["model"], contents=user,
        config=types.GenerateContentConfig(system_instruction=system, max_output_tokens=max_tokens))
    u = r.usage_metadata
    return (r.text or ""), dict(prompt=u.prompt_token_count, completion=u.candidates_token_count,
        cache_read=getattr(u,"cached_content_token_count",0) or 0, cache_write=0,
        reasoning=getattr(u,"thoughts_token_count",None), stop="stop")

def dispatch(cfg, system, user, max_tokens):
    p = cfg["provider"]
    if p == "anthropic": return call_anthropic(cfg, system, user, max_tokens)
    if p == "openai":    return call_openai_like(cfg, system, user, max_tokens, base_url=None)
    if p == "gemini":    return call_gemini(cfg, system, user, max_tokens)
    return call_openai_like(cfg, system, user, max_tokens)

# ---------------------------------------------------------------- parsing
def parse_verdict(text):
    """Strip <think> blocks and fences, then take the last JSON object."""
    t = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    t = re.sub(r"^```(?:json)?|```$", "", t.strip(), flags=re.M).strip()
    objs = re.findall(r"\{.*\}", t, flags=re.S)
    if not objs: return None
    for cand in reversed(objs):
        try: return json.loads(cand)
        except Exception: continue
    return None

def evidence_is_verbatim(span, passage):
    if span in (None, "", "null"): return None      # not claimed
    return span.strip() in passage

# ---------------------------------------------------------------- runner
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["probe","pilot","run"])
    ap.add_argument("--sample", default=os.path.join(HERE,"sample_representative_100.json"))
    ap.add_argument("--out",    default=os.path.join(HERE,"results.jsonl"))
    ap.add_argument("--models", default="")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--langs", default="ru")
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--workers", type=int, default=1, help="parallel across model configs")
    ap.add_argument("--budget", type=float, default=90.0, help="hard USD stop")
    a = ap.parse_args()

    cfgs = [m for m in REG.MODELS if not a.models or m["key"] in a.models.split(",")]

    if a.mode == "probe":
        print(f"probing {len(cfgs)} configs\n")
        ok = 0
        for cfg in cfgs:
            kenv = key_for(cfg)
            if not kenv or kenv not in ENV:
                print(f"  {cfg['key']:18s} NO KEY ({kenv})", flush=True); continue
            try:
                t0=time.time()
                txt,u = dispatch(cfg, "Reply with the single word: ok", "Say ok.", 64)
                print(f"  {cfg['key']:18s} OK   {time.time()-t0:5.1f}s  "
                      f"in={u['prompt']} out={u['completion']} reas={u['reasoning']} "
                      f"-> {(txt or '')[:40]!r}", flush=True); ok+=1
            except Exception as e:
                print(f"  {cfg['key']:18s} FAIL {type(e).__name__}: {str(e)[:150]}", flush=True)
        print(f"\n{ok}/{len(cfgs)} reachable")
        return

    sample = json.load(io.open(a.sample, encoding="utf-8"))
    G = "/mnt/g/My Drive/Red lines".replace("/Red lines","")  # placeholder, text loaded below
    raw = io.open("/mnt/g/My Drive/RuBase/Red lines/gold_certification/scripts/gold298_rows.json",
                  encoding="utf-8").read()
    TXT = {r["chunk_id"]: r["content"] for r in json.loads(raw[raw.index("["):])}
    items = sample[:a.n] if a.mode == "pilot" else sample

    done = set()
    if os.path.exists(a.out):
        for line in io.open(a.out, encoding="utf-8"):
            try:
                r = json.loads(line); done.add((r["model_key"], r["chunk_id"], r["lang"], r["rep"]))
            except Exception: pass
    print(f"{a.mode}: {len(items)} items x {len(cfgs)} configs x {len(a.langs.split(','))} lang x {a.reps} rep"
          f"  |  {len(done)} already done", flush=True)

    fh = io.open(a.out, "a", encoding="utf-8")      # APPEND, never truncate
    lock = threading.Lock()
    state = dict(n=0, spent=0.0, stop=False)

    def work(cfg):
        for lang in a.langs.split(","):
            for rep in range(1, a.reps+1):
                for it in items:
                    if state["stop"]: return
                    ck = (cfg["key"], it["chunk_id"], lang, rep)
                    if ck in done: continue
                    passage = it.get("content") or TXT[it["chunk_id"]]
                    user = USER_T.format(chunk_id=it["chunk_id"], lang=lang.upper(), content=passage)
                    t0=time.time()
                    try:
                        txt,u = dispatch(cfg, SYSTEM, user, a.max_tokens)
                        v = parse_verdict(txt)
                        c = rec_cost(cfg["key"], u, cfg["provider"])
                        rec = dict(model_key=cfg["key"], model=cfg["model"], provider=cfg["provider"],
                                   chunk_id=it["chunk_id"], lang=lang, rep=rep,
                                   gold_rls=it["gold_rls"], gold_nts=it["gold_nts"],
                                   verdict=v, parsed=bool(v), usage=u, est_cost=round(c,6),
                                   secs=round(time.time()-t0,2),
                                   rls_ev_verbatim=evidence_is_verbatim((v or {}).get("rls_evidence"), passage),
                                   nts_ev_verbatim=evidence_is_verbatim((v or {}).get("nts_evidence"), passage),
                                   raw=None if v else (txt or "")[:2000])
                    except Exception as e:
                        c = 0.0
                        rec = dict(model_key=cfg["key"], chunk_id=it["chunk_id"], lang=lang, rep=rep,
                                   error=f"{type(e).__name__}: {str(e)[:300]}", secs=round(time.time()-t0,2))
                    with lock:
                        fh.write(json.dumps(rec, ensure_ascii=False)+"\n"); fh.flush()
                        state["n"] += 1; state["spent"] += c
                        if state["spent"] >= a.budget:
                            state["stop"] = True
                            print(f"!! BUDGET STOP at ${state['spent']:.2f} >= ${a.budget}", flush=True)
                        if state["n"] % 25 == 0 or "error" in rec:
                            tag = "ERR" if "error" in rec else ("ok" if rec.get("parsed") else "unparsed")
                            print(f"  [{state['n']:5d}] {cfg['key']:17s} {tag:8s} "
                                  f"${state['spent']:.2f} spent", flush=True)

    with ThreadPoolExecutor(max_workers=max(1, a.workers)) as ex:
        futs = {ex.submit(work, c): c["key"] for c in cfgs}
        for f in as_completed(futs):
            try: f.result()
            except Exception as e: print(f"  worker {futs[f]} died: {e}", flush=True)

    fh.close()
    print(f"\nwrote {state['n']} new records, est ${state['spent']:.2f} -> {a.out}", flush=True)

if __name__ == "__main__":
    main()
