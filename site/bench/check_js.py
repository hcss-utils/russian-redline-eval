#!/usr/bin/env python3
"""Extract the page's script blocks and syntax-check them with node. Catches quoting
errors that a text audit cannot see and that otherwise only surface in a browser."""
import io, re, subprocess, sys, os, tempfile
p=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"app","index.html")
s=io.open(p,encoding="utf-8").read()
blocks=re.findall(r'<script>(.*?)</script>', s, re.S)
bad=0
for i,b in enumerate(blocks):
    with tempfile.NamedTemporaryFile("w",suffix=".js",delete=False,encoding="utf-8") as f:
        f.write(b); tmp=f.name
    r=subprocess.run(["node","--check",tmp],capture_output=True,text=True)
    if r.returncode!=0:
        bad+=1; print(f"  SYNTAX ERROR in script block {i}:"); print("   ", r.stderr.strip().split("\n")[-3:])
    os.unlink(tmp)
print(f"{len(blocks)} script block(s) checked — {'ALL VALID' if not bad else str(bad)+' INVALID'}")
sys.exit(1 if bad else 0)
