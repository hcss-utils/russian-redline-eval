#!/usr/bin/env python3
"""Exhaustive mockup audit. Works from the DATA, not from a memory of stale strings."""
import io, re, json, os, sys
B=os.path.dirname(os.path.abspath(__file__))
s=io.open(os.path.join(os.path.dirname(B),"app","index.html"),encoding="utf-8").read()
D=json.load(io.open(os.path.join(B,"app_data.json"),encoding="utf-8"))
fails=[]
def chk(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"   {detail}" if not ok and detail else ""))
    if not ok: fails.append(name)

HONEST=("Not reached","Absent rather than substituted","token-plan quota","Korea and Russia")
ill=0; ctxs=[]
for pat in ('GigaChat','Solar Pro','MiniMax','YandexGPT','HyperCLOVA'):
    for m in re.finditer(pat,s):
        c=' '.join(re.sub(r'<[^>]+>',' ',s[max(0,m.start()-140):m.start()+90]).split())
        if not any(t in c for t in HONEST): ill+=1; ctxs.append(c[:110])
chk("no retired-model mentions outside the honest note", ill==0, "; ".join(ctxs[:2]))

chk("data anchors intact", all(a in s for a in ("const MODELS=[","const PBYID","const EV=")))
# the payload may be written as a JS literal (k:"x") or as strict JSON ("k": "x"),
# depending on whether it was last emitted or re-serialised. Accept both, or this
# check silently compares an EMPTY set and reports the whole slate as a mismatch.
emitted=set(re.findall(r'"?k"?\s*:\s*"([a-z0-9_.]+)"', s)); real={m['k'] for m in D['models']}
chk("emitted slate == measured slate", emitted==real, str(emitted ^ real))

code=s[s.index('const PBYID'):]
# 'flagged' is the CANONICAL neutral key; 'fab' is its historical spelling, still
# accepted because adaptLegacyInput lifts an older payload up to canonical.
allowed={'id','ref','sp','yr','ru','en','cue','why','v','j','flagged','fab'}
pf={x for x in re.findall(r'\bp\.([a-z_]+)\b', code)} - {'map','forEach','filter','length','join','toFixed','slice','indexOf','replace','split','style','id'}
chk("all p.<field> refs exist in data", pf<=allowed, str(pf-allowed))
mf={x for x in re.findall(r'\bm\.([a-z_0-9]+)\b', code)} - {'map','forEach','filter','length','join','toFixed','slice','indexOf','replace','split','start','group','k','i','j','layer','t','ok'}
mfields=set(D['models'][0].keys())|{'ctx','style','flip','short'}
# the sequential arm binds `m` to SEQ.models inside sqSlope/sqRender, so its fields are
# legitimate too -- read them from the injected SEQ payload rather than whitelisting names
import re as _re2
for _nm in ('SEQ','FABX'):
    _m=_re2.search(r'const '+_nm+r'=(\{.*?\});', s, _re2.S)
    if _m:
        try: mfields |= set(json.loads(_m.group(1))['models'][0].keys())
        except Exception: pass
_seq=_re2.search(r'const SEQ=(\{.*?\});', s, _re2.S)
if _seq:
    try: mfields |= set(json.loads(_seq.group(1))['models'][0].keys())
    except Exception: pass
chk("all m.<field> refs exist in data", mf<=mfields, str(mf-mfields))

for bad in ('17,880','of 10 models','103 of 189','$101.54','1,847','264,266','challenge-enriched',
            'notional','illustrative','mockup','placeholder','lorem','dummy','TBD','coming soon',
            'not yet run','has not been dispatched','298 passages','298-item','298 labels'):
    chk(f"no '{bad}'", bad.lower() not in s.lower())

chk("no dead-field method calls (m.flip)", 'm.flip' not in s)
chk("no empty hidden paragraphs", '<p style="display:none">' not in s)
print()
print(("AUDIT CLEAN" if not fails else f"AUDIT FAILED: {len(fails)}"))
sys.exit(0 if not fails else 1)
