#!/usr/bin/env python3
"""Categorise every non-verbatim span. The binary substring test says only
'not found'; it cannot tell an ellipsis from an invention.

The ladder runs benign-first, so each span gets the mildest category that
explains it. Anything that survives every mechanical test is a candidate real
fabrication and is printed for human reading -- the classifier proposes, the
eye disposes.
"""
import json, io, re, unicodedata, difflib, sys

def nfkc(x): return unicodedata.normalize("NFKC", x or "")
def ws(x):   return re.sub(r"\s+", " ", nfkc(x)).strip()
def lo(x):   return ws(x).lower().replace("ё","е")
def nopunct(x):
    # collapse whitespace AFTER stripping punctuation: "**word**" -> "  word  " -> "word".
    # Without this a bolded word never matches its clean counterpart.
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", lo(x))).strip()
def nomark(x):
    x=re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", x or "")   # flatten [text](url) as a reader would
    return re.sub(r"__|\*\*", "", x)
CYR=re.compile(r"[а-яА-ЯёЁ]")

def longest_common(a,b):
    m=difflib.SequenceMatcher(None,a,b).find_longest_match(0,len(a),0,len(b))
    return m.size

def classify(span, passage, others):
    s_raw, p_raw = span, passage
    if ws(s_raw) in ws(p_raw):                       return "whitespace_only","present once whitespace is normalised"
    if lo(s_raw) in lo(p_raw):                       return "case_or_yo","present once case / ё-е is normalised"
    if ws(nomark(s_raw)) in ws(nomark(p_raw)):       return "source_markup","present once the source's own __/** markup is removed"
    if nopunct(s_raw) and nopunct(s_raw) in nopunct(p_raw): return "punctuation_only","present once punctuation is normalised"
    # ellipsis / multi-fragment joins
    if re.search(r"\.\.\.|…|\[\.\.\.\]|\[…\]", s_raw):
        parts=[p for p in re.split(r"\s*(?:\.\.\.|…|\[\.\.\.\]|\[…\])\s*", s_raw) if len(nopunct(p))>3]
        if parts and all(nopunct(p) in nopunct(p_raw) for p in parts):
            return "ellipsis_join","fragments joined by an ellipsis, every fragment genuine"
        if parts and any(nopunct(p) in nopunct(p_raw) for p in parts):
            return "ellipsis_partial","ellipsis join where at least one fragment is NOT in the passage"
    # trimmed edges
    t=nopunct(s_raw)
    if len(t)>12:
        for cut in (1,2,3,4,5):
            if t[cut:] in nopunct(p_raw) or t[:-cut] in nopunct(p_raw):
                return "edge_trim","genuine text with a few characters over- or under-run at an edge"
    # quoted in a different language
    if s_raw and not CYR.search(s_raw) and CYR.search(p_raw):
        return "translation","the model quoted a translation instead of the Russian"
    # borrowed from another passage in the benchmark
    for oid,otxt in others.items():
        if len(nopunct(s_raw))>15 and nopunct(s_raw) in nopunct(otxt):
            return "other_passage","verbatim, but from a DIFFERENT passage (context bleed)"
    # quote-splicing: several genuine fragments joined without an ellipsis.
    # Greedy longest-prefix decomposition against the passage.
    def splice_parts(a, b, minlen=18):
        rest, parts = a, []
        while len(rest) >= minlen and len(parts) < 8:
            hi = len(rest); best = 0
            while hi >= minlen:
                if rest[:hi] in b: best = hi; break
                hi -= 1
            if best < minlen: return None
            parts.append(rest[:best]); rest = rest[best:].strip()
        return parts if len(rest) < minlen else None
    sp = splice_parts(nopunct(s_raw), nopunct(p_raw))
    if sp and len(sp) >= 2:
        return "spliced", f"{len(sp)} genuine fragments joined without an ellipsis"

    # partial overlap => paraphrase / inflection change
    a,b=nopunct(s_raw),nopunct(p_raw)
    if a:
        frac=longest_common(a,b)/len(a)
        if frac>=0.60: return "paraphrase_major","most of the span is real; wording or inflection altered"
        if frac>=0.30: return "paraphrase_partial","only part of the span traces to the passage"
    return "invented","no substantial overlap with the passage"

def main():
    rec=json.load(io.open("/tmp/fab_all.json",encoding="utf-8"))
    bytxt={}
    for r in rec: bytxt[r["chunk_id"]]=r["passage"]
    from collections import Counter, defaultdict
    cats=Counter(); ex=defaultdict(list)
    for r in rec:
        others={k:v for k,v in bytxt.items() if k!=r["chunk_id"]}
        c,why=classify(r["span"], r["passage"], others)
        r["category"], r["why"] = c, why
        cats[c]+=1; ex[c].append(r)
    io.open("bench/fabrication_categories.json","w",encoding="utf-8").write(
        json.dumps({"n":len(rec),"counts":dict(cats),"records":rec},ensure_ascii=False,indent=1))
    ORDER=["whitespace_only","case_or_yo","source_markup","punctuation_only","ellipsis_join","spliced","edge_trim",
           "translation","paraphrase_major","ellipsis_partial","other_passage","paraphrase_partial","invented"]
    print(f"{'category':20s} {'n':>4s}  {'%':>6s}")
    for c in ORDER:
        if cats.get(c): print(f"{c:20s} {cats[c]:>4d}  {cats[c]/len(rec)*100:>5.1f}%")
    print(f"{'TOTAL':20s} {len(rec):>4d}")
    io.open("/tmp/fab_examples.json","w",encoding="utf-8").write(
        json.dumps({c:[{"model":x["model"],"chunk":x["chunk_id"],"span":x["span"][:300]} for x in v[:6]]
                    for c,v in ex.items()},ensure_ascii=False,indent=1))
if __name__=="__main__": main()
