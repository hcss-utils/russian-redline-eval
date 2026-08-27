#!/usr/bin/env python3
"""Check the RENDERED page against the payload it claims to render.

verify_app_numbers.py reads the HTML source. That catches a stale or invented
payload, but not a renderer that draws the right payload wrongly -- the Source
Arms table proved the difference: its class counts were correct values printed
under the WRONG HEADERS, invisible to any check that reads the payload and
invisible to grep, because every number on the page was real.

So this one opens the page in a browser and compares what a reader actually sees
against MODELS/PASSAGES as loaded by that same page:

  * every cell of the Cases table (~1,300) against PASSAGES[].v and .ref;
  * the Situation Room reveal;
  * the Source Arms composition table, incl. that its percentages sum to 100;
  * zero console errors, and no horizontal overflow at four widths.

Usage: python3 code/verify_rendered_page.py [url]
"""
import sys

URL = sys.argv[1] if len(sys.argv) > 1 else "https://rubase.org/redline-eval/"
WIDTHS = (1280, 1366, 1440, 1600)

CASES_JS = r"""() => {
  const tbl=[...document.querySelectorAll('#cases table')][0];
  if(!tbl) return {err:'cases table not found'};
  const norm=t=>t.replace(/[^A-Za-z0-9.+−-]/g,'');
  const heads=[...tbl.querySelectorAll('thead th')].map(h=>norm(h.textContent));
  const byShort={}; MODELS.forEach(m=>{ byShort[norm(m.short||m.n)]=m.k; });
  // locate the model columns by NAME, not by a hardcoded offset. slice(6) skipped the first
  // model column entirely -- 1,300 of 1,400 cells -- and the Correct column with it.
  const cols=[]; heads.forEach((h,i)=>{ if(byShort[h]!==undefined) cols.push({i, k:byShort[h]}); });
  const correctCol=heads.length-1;
  const rows=[...tbl.querySelectorAll('tbody tr')];
  let checked=0, bad=[], ids=[];
  rows.forEach(tr=>{
    const c=[...tr.children]; const id=c[0].textContent.trim(); ids.push(id);
    const p=PASSAGES.find(x=>x.id===id);
    if(!p){ bad.push({id, err:'row id not in PASSAGES'}); return; }
    let ok_n=0;
    cols.forEach(function(col){
      const cell=c[col.i]; if(!cell) return;
      const shown=cell.textContent.trim();
      const v=(p.v||{})[col.k]; if(v===undefined) return;
      checked++;
      const match = (shown==='✓') ? (v===p.ref) : (shown===v || (shown==='n/a'&&v==='n/a'));
      if(v===p.ref) ok_n++;
      if(!match && bad.length<8) bad.push({id, model:col.k, shown:shown, payload:v, ref:p.ref});
    });
    const cc=((c[correctCol]||{}).textContent||'').trim();
    const m=cc.match(/^([0-9]+)\s*\/\s*([0-9]+)$/);
    if(!m){ if(bad.length<8) bad.push({id, err:'Correct cell unreadable: '+cc}); }
    else if(+m[1]!==ok_n || +m[2]!==cols.length){
      if(bad.length<8) bad.push({id, err:'Correct cell '+m[1]+'/'+m[2]+', payload gives '+ok_n+'/'+cols.length});
    }
  });
  return {checked:checked, bad:bad, cols:cols.length, rows:rows.length, ids:ids};
}"""

# read the HEADERS too. A table can carry correct values under wrong labels -- 59 no-alert
# passages were displayed as red lines -- and a body-only check cannot see it.
COMP_JS = r"""() => {
  const out=[];
  [...document.querySelectorAll('#sources table')].forEach(t=>{
    const heads=[...t.querySelectorAll('thead th')].map(h=>h.textContent.trim().toLowerCase());
    const rows=[...t.querySelectorAll('tbody tr')].map(r=>[...r.children].map(c=>c.textContent.trim()));
    const looks = heads.some(h=>h.indexOf('no alert')>=0) && heads.some(h=>h.indexOf('red line')>=0)
               && heads.some(h=>h.indexOf('nuclear')>=0);
    if(looks && rows.length) out.push({heads:heads, rows:rows});
  });
  return out;
}"""

SIT_JS = r"""() => {
  const sel=document.getElementById('sit-pick');
  const idx=sel? +sel.value : 0;
  const p=PASSAGES[idx];
  const norm=x=>x.replace(/[^A-Za-z0-9.+−-]/g,'');
  const byShort={}; MODELS.forEach(m=>{ byShort[norm(m.short||m.n)]=m.k; });
  const LBL={None:'No alert', RLS:'Red line', NTS:'Nuclear signal', 'n/a':'unparsed'};
  const rows=[...document.querySelectorAll('#sit-reveal tbody tr')].map(r=>[...r.children].map(c=>c.textContent.trim()));
  const bad=[];
  rows.forEach(r=>{
    const k=byShort[norm(r[0])];
    if(k===undefined){ bad.push('unknown configuration row: '+r[0]); return; }
    const want=LBL[(p.v||{})[k]] || (p.v||{})[k];
    if(r[1]!==want) bad.push(r[0]+': shows '+r[1]+', payload '+want);
  });
  const head=((document.querySelector('#sit-reveal div')||{}).textContent||'');
  return {id:p.id, n:rows.length, bad:bad, refOK:head.indexOf(LBL[p.ref]||p.ref)>=0};
}"""

def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed; rendered checks skipped")
        return 0
    fails = []
    import json, io as _io, os, collections
    _here = os.path.dirname(os.path.abspath(__file__)); _repo = os.path.dirname(_here)
    comp_want = {}
    for c in (os.path.join(_repo, "data", "sample_representative_100.json"),
              os.path.join(_here, "sample_representative_100.json"),
              os.path.join(os.getcwd(), "bench", "sample_representative_100.json")):
        if os.path.exists(c):
            for _r in json.load(_io.open(c, encoding="utf-8")):
                lab = "NTS" if _r["gold_nts"] == "Y" else ("RLS" if _r["gold_rls"] == "Y" else "None")
                d = comp_want.setdefault(_r["database"], {"None": 0, "RLS": 0, "NTS": 0, "n": 0})
                d[lab] += 1; d["n"] += 1
            break
    if not comp_want:
        fails.append("sample_representative_100.json not found; refusing to skip the composition check")
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1600, "height": 1000})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.goto(URL, wait_until="networkidle", timeout=90000)
        pg.wait_for_timeout(2500)

        pg.click("text=Cases"); pg.wait_for_timeout(2500)
        r = pg.evaluate(CASES_JS)
        if r.get("err"):
            fails.append(r["err"])
        else:
            print(f"  Cases: {r['checked']} cells across {r['cols']} model columns, {r['rows']} rows")
            # exact counts, not a floor: a floor let a 1,300-of-1,400 probe look complete
            if r["rows"] != 100:
                fails.append(f"Cases has {r['rows']} rows; expected exactly 100")
            if r["cols"] != 14:
                fails.append(f"Cases exposes {r['cols']} model columns; expected exactly 14")
            if r["checked"] != r["rows"] * r["cols"]:
                fails.append(f"Cases compared {r['checked']} cells; expected {r['rows'] * r['cols']}")
            if len(set(r["ids"])) != len(r["ids"]):
                fails.append("Cases contains duplicate passage ids")
            for x in r["bad"]:
                fails.append("Cases " + (x.get("err") or
                    f"{x['id']} {x['model']}: shows {x['shown']!r}, payload {x['payload']!r}"))

        pg.click("text=Source Arms"); pg.wait_for_timeout(1800)
        tables = pg.evaluate(COMP_JS)
        if not tables:
            fails.append("no sample-composition table rendered")
        for t in tables:
            heads = t["heads"]
            # map each class column by its HEADER, then compare against the canonical sample
            def col(name):
                for i, h in enumerate(heads):
                    if name in h: return i
                return -1
            iN, iR, iX = col("no alert"), col("red line"), col("nuclear")
            if min(iN, iR, iX) < 0:
                fails.append(f"composition headers unreadable: {heads}")
                continue
            tot = 0.0
            for row in t["rows"]:
                arm = row[0].strip().lower().replace(" ", "_")
                key = next((k for k in comp_want if k.lower().replace(" ", "_") == arm), None)
                if key is None:
                    if arm in ("total", "all", ""):   # a summary row is not an arm
                        continue
                    fails.append(f"composition row {row[0]!r} is not a known source arm")
                    continue
                w = comp_want[key]
                got = {"None": int(row[iN]), "RLS": int(row[iR]), "NTS": int(row[iX])}
                # the row's own total must equal both its parts and the canonical count
                try: shown_n = int(row[1])
                except ValueError: shown_n = None
                if shown_n is not None:
                    if shown_n != sum(got.values()):
                        fails.append(f"composition {row[0]}: total {shown_n} != {'+'.join(str(v) for v in got.values())}")
                    if shown_n != w["n"]:
                        fails.append(f"composition {row[0]}: total {shown_n}, canonical {w['n']}")
                if got != {"None": w["None"], "RLS": w["RLS"], "NTS": w["NTS"]}:
                    fails.append(f"composition {row[0]}: page {got} under headers {heads[1:5]}, "
                                 f"canonical {{'None': {w['None']}, 'RLS': {w['RLS']}, 'NTS': {w['NTS']}}}")
                pcts = [c for c in row if c.strip().endswith("%")]
                if pcts: tot += float(pcts[-1].rstrip("%"))
            if tot and not (99 <= tot <= 101):
                fails.append(f"composition percentages sum to {tot:g}%, not 100%")
            print(f"  Source Arms: {len(t['rows'])} rows checked against canonical data (headers OK)")

        pg.click("text=Situation Room"); pg.wait_for_timeout(1800)
        try:
            pg.click('#sit-calls button[data-call="NTS"]'); pg.wait_for_timeout(1200)
            sr = pg.evaluate(SIT_JS)
            if sr["n"] != 14:
                fails.append(f"Situation Room revealed {sr['n']} configurations, expected exactly 14")
            if not sr["refOK"]:
                fails.append(f"Situation Room does not state the reference label for {sr['id']}")
            for x in sr["bad"]:
                fails.append("Situation Room " + x)
            print(f"  Situation Room: {sr['n']} configurations, all calls compared against PASSAGES")
        except Exception as e:
            fails.append(f"Situation Room controls not usable: {str(e)[:90]}")

        if errs:
            fails.append(f"console errors: {errs[:3]}")
        pg.close()

        for w in WIDTHS:
            p2 = b.new_page(viewport={"width": w, "height": 1000})
            p2.goto(URL, wait_until="networkidle", timeout=90000); p2.wait_for_timeout(1600)
            if p2.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth"):
                fails.append(f"page scrolls horizontally at {w}px")
            p2.close()
        if not any("scrolls" in f for f in fails):
            print(f"  widths {'/'.join(map(str, WIDTHS))}: no horizontal overflow")
        b.close()

    if fails:
        print(f"FAIL — {len(fails)} rendering problem(s):")
        for f in fails: print("  -", f)
        return 1
    print("OK — the rendered page is faithful to the payload it loads.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
