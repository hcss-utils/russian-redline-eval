#!/usr/bin/env python3
"""Inject the CORRECTED fabrication analysis. Every figure is read from
citation_check_summary.json / flagged_span_categories.json -- nothing typed in.

The old page reported a naive substring flag as 'fabricated quotes'. Reading all
283 flagged spans showed 0 inventions; this payload carries the decomposition so
the page can show what the flags actually were.
"""
import json, io, re
APP="app/index.html"
c=json.load(io.open("bench/citation_check_summary.json",encoding="utf-8"))
cats=json.load(io.open("bench/flagged_span_categories.json",encoding="utf-8"))
names={m["k"].replace("-","_").replace(".","_"):m["short"]
       for m in json.load(io.open("bench/app_data.json",encoding="utf-8"))["models"]}
nz=lambda k:k.replace("-","_").replace(".","_")
T=c["totals"]
payload={
 "spans":T["spans"], "flagged":T["flagged"],
 "naive_rate":round(T["flagged"]/T["spans"],4),
 "A":T["A"],"B":T["B"],"C":T["C"],"D":T["D"],"E":T["E"],
 "real_rate":round(T["D"]/T["spans"],5),
 "invented_rate":round(T["E"]/T["spans"],5),
 "zero_models":sum(1 for v in c["per_model"].values() if v["D"]+v["E"]==0),
 "n_models":len(c["per_model"]),
 "cats":cats["counts"],
 "models":[{"k":k,"n":names.get(nz(k),k),"spans":v["spans"],"flagged":v["flagged"],
            "naive":round(v["flagged"]/max(v["spans"],1),4),
            "real":round((v["D"]+v["E"])/max(v["spans"],1),5),
            "A":v["A"],"B":v["B"],"C":v["C"],"D":v["D"],"E":v["E"]}
           for k,v in sorted(c["per_model"].items(), key=lambda x:-x[1]["flagged"]/max(x[1]["spans"],1))],
}
s=io.open(APP,encoding="utf-8").read()
blob="const FABX="+json.dumps(payload,ensure_ascii=False,separators=(",",":"))+";"
if "const FABX=" in s: s=re.sub(r"const FABX=\{.*?\};", blob, s, count=1, flags=re.S)
else: s=s.replace("const SEQ=", blob+"\nconst SEQ=",1)
io.open(APP,"w",encoding="utf-8").write(s)
print(f"injected FABX: {payload['flagged']} flagged of {payload['spans']} spans; "
      f"invented {payload['E']}; {payload['zero_models']}/{payload['n_models']} models clean")

