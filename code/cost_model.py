#!/usr/bin/env python3
"""Cost projection from MEASURED pilot tokens and published list prices."""
import json, io, collections, statistics, sys

# $/MTok (input, output). Batch halves both where available (marked B).
PRICE = {
 "fable-5":        (10.00, 50.00, True),
 "opus-5-think":   ( 5.00, 25.00, True),
 "opus-5-nothink": ( 5.00, 25.00, True),
 "sonnet-5":       ( 3.00, 15.00, True),
 "haiku-4.5":      ( 1.00,  5.00, True),
 "gpt-5.6-sol":    ( 4.00, 20.00, True),
 "gpt-5.6-terra":  ( 2.00, 12.00, True),
 "gpt-5.6-luna":   ( 0.20,  1.20, True),
 "gemini-3.6-flash":(0.75,  3.75, True),
 "deepseek-v4-pro": (0.66,  1.98, False),
 "deepseek-v4-flash":(0.22, 0.66, False),
 "qwen3.7-max":    ( 1.20,  6.00, False),
 "glm-5.2":        ( 0.60,  2.20, False),
 "kimi-k3":        ( 1.00,  3.00, False),
}
GEMINI_SPLIT = {"gemini-3.6-flash"}   # thoughts billed separately from candidates

def load(*paths):
    by=collections.defaultdict(list)
    for p in paths:
        for l in io.open(p,encoding="utf-8"):
            r=json.loads(l)
            if "usage" in r: by[r["model_key"]].append(r)
    return by

def main(n_items=100, langs=2, reps=1, batch=True):
    by=load("/tmp/pilot3.jsonl","/tmp/pilot_anth.jsonl")
    calls = n_items*langs*reps
    print(f"design: {n_items} items x {langs} lang x {reps} rep = {calls} calls/config   batch={batch}\n")
    print(f"{'config':18s} {'in':>6s} {'cache':>6s} {'out':>6s} {'$/config':>9s}  {'note'}")
    total=0.0; measured=[]
    for k,v in sorted(by.items()):
        if k not in PRICE: continue
        mean=lambda f: statistics.mean([(x['usage'].get(f) or 0) for x in v])
        p_in, p_out, has_batch = PRICE[k]
        if batch and has_batch: p_in, p_out = p_in/2, p_out/2
        prov = v[0].get('provider','')
        # SEMANTICS DIFFER: Anthropic input_tokens EXCLUDES cache; OpenAI prompt_tokens INCLUDES it.
        if prov == 'anthropic':
            fresh  = mean('prompt')
            cached = mean('cache_read')
            write  = mean('cache_write')
        else:
            fresh  = max(0.0, mean('prompt') - mean('cache_read'))
            cached = mean('cache_read')
            write  = 0.0
        out = mean('completion') + (mean('reasoning') if k in GEMINI_SPLIT else 0)
        # cache read ~0.1x list; Anthropic cache write ~1.25x list
        cost = calls*((fresh*p_in + cached*p_in*0.10 + write*p_in*1.25)/1e6 + out*p_out/1e6)
        total += cost; measured.append(k)
        print(f"{k:18s} {mean('prompt'):6.0f} {cached:6.0f} {out:6.0f} {cost:9.2f}"
              f"  {'batch' if (batch and has_batch) else 'list'}")
    print(f"\nMEASURED SUBTOTAL ({len(measured)} configs): ${total:.2f}")
    unmeasured=[k for k in PRICE if k not in measured]
    if unmeasured:
        proxy = total/len(measured)
        print(f"UNMEASURED ({len(unmeasured)}): {', '.join(unmeasured)}")
        print(f"  at per-config mean ${proxy:.2f} -> +${proxy*len(unmeasured):.2f}")
        print(f"\nPROJECTED TOTAL ({len(PRICE)} configs): ${total+proxy*len(unmeasured):.2f}")

if __name__=="__main__":
    n=int(sys.argv[1]) if len(sys.argv)>1 else 100
    main(n_items=n)
