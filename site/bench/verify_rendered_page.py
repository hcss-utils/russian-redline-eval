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
  return {checked:checked, bad:bad, cols:cols.length, rows:rows.length, ids:ids, colKeys:cols.map(c=>c.k)};
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


# The leaderboard renders 14 rows x 9 measured values straight off MODELS. Verified as a
# payload, never as rendered -- and "correct payload drawn wrongly" is this file's whole
# reason to exist.
LB_JS = r"""() => {
  const t=[...document.querySelectorAll('#findings table')][0];
  if(!t) return {err:'leaderboard table not found'};
  const norm=x=>x.replace(/[^A-Za-z0-9.+−-]/g,'');
  const byName={}; MODELS.forEach(m=>{ byName[norm(m.n)]=m; byName[norm(m.short||m.n)]=m; });
  const heads=[...t.querySelectorAll('thead th')].map(h=>h.textContent.trim().toLowerCase());
  const col=n=>heads.findIndex(h=>h.indexOf(n)>=0);
  const iFlag=col('naive-flag'), iMiss=col('missed nuclear'), iRls=col('rls acc'),
        iNts=col('nts acc'), iCons=col('consistency'), iCost=col('cost');
  const rows=[...t.querySelectorAll('tbody tr')];
  const bad=[]; let checked=0;
  rows.forEach(tr=>{
    const c=[...tr.children].map(x=>x.textContent.trim());
    const m=byName[norm(c[1])];
    if(!m){ bad.push('row not matched to a configuration: '+c[1]); return; }
    const near=(a,b,tol)=>Math.abs(a-b)<=tol;
    const num=x=>parseFloat(String(x).replace(/[^0-9.]/g,''));
    if(iFlag>=0){ checked++; if(!near(num(c[iFlag]), m.flag_rate*100, 0.1))
      bad.push(m.k+' naive-flag: shows '+c[iFlag]+', payload '+(m.flag_rate*100).toFixed(1)+'%'); }
    if(iMiss>=0){ checked++; const mm=c[iMiss].match(/^(\d+)\s*\/\s*(\d+)$/);
      if(!mm || +mm[1]!==m.mn) bad.push(m.k+' missed nuclear: shows '+c[iMiss]+', payload '+m.mn); }
    if(iRls>=0){ checked++; if(!near(num(c[iRls].split('[')[0]), m.rls, 0.0006))
      bad.push(m.k+' rls acc: shows '+c[iRls]+', payload '+m.rls); }
    if(iNts>=0){ checked++; if(!near(num(c[iNts]), m.nts, 0.0006))
      bad.push(m.k+' nts acc: shows '+c[iNts]+', payload '+m.nts); }
    if(iCons>=0){ checked++; if(!near(num(c[iCons]), m.consis, 0.0006))
      bad.push(m.k+' consistency: shows '+c[iCons]+', payload '+m.consis); }
    if(iCost>=0){ checked++; if(!near(num(c[iCost]), m.cost, 0.006))
      bad.push(m.k+' cost: shows '+c[iCost]+', payload '+m.cost); }
  });
  return {rows:rows.length, checked:checked, bad:bad.slice(0,8)};
}"""

SIT_JS = r"""() => {
  // Identity must come from what the READER sees, not from the selector's value. This used to
  // read #sit-pick, index PASSAGES by it, and compare the reveal against that -- so a render
  // showing the wrong title and body passed as long as the reveal matched the payload.
  const sel=document.getElementById('sit-pick');
  const idx=sel? +sel.value : 0;
  const p=PASSAGES[idx];
  const title=((document.getElementById('sit-title')||{}).textContent||'').trim();
  const body =((document.getElementById('sit-text') ||{}).textContent||'').trim();
  const norm=x=>x.replace(/[^A-Za-z0-9.+−-]/g,'');
  const byShort={}; MODELS.forEach(m=>{ byShort[norm(m.short||m.n)]=m.k; });
  const LBL={None:'No alert', RLS:'Red line', NTS:'Nuclear signal', 'n/a':'unparsed'};
  const rows=[...document.querySelectorAll('#sit-reveal tbody tr')].map(r=>[...r.children].map(c=>c.textContent.trim()));
  const bad=[], keys=[];
  rows.forEach(r=>{
    const k=byShort[norm(r[0])];
    if(k===undefined){ bad.push('unknown configuration row: '+r[0]); return; }
    keys.push(k);
    const want=LBL[(p.v||{})[k]] || (p.v||{})[k];
    if(r[1]!==want) bad.push(r[0]+': shows '+r[1]+', payload '+want);
  });
  // the reference is read from its own sentence and compared EXACTLY, not as a substring
  const head=((document.querySelector('#sit-reveal div')||{}).textContent||'');
  const rm=head.match(/Reference label:\s*([^.]+)\./);
  const shownRef=rm? rm[1].trim() : null;
  return {
    idFromTitle: (title.match(/#\d+/)||[null])[0],
    payloadId: p.id,
    titleHasSpeaker: p.sp? title.indexOf(p.sp)>=0 : true,
    // EQUALITY after whitespace normalisation, not containment: a containment test is
    // satisfied by a single character that happens to occur in the passage.
    bodyMatches: (function(){ const n=x=>x.replace(/\s+/g,' ').trim();
                              return n(body)===n(p.ru||''); })(),
    bodyLen: body.length, wantLen: (p.ru||'').length,
    shownRef: shownRef,
    wantRef: LBL[p.ref]||p.ref,
    n: rows.length, keys: keys, bad: bad
  };
}"""

def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        # Exiting 0 here would report SUCCESS for a run that checked nothing -- the exact
        # shape of failure this project has found five times. A checker that cannot run
        # says so and fails.
        print("FAIL — playwright is not installed, so NOTHING was checked. "
              "Install it or run this where a browser exists; a skipped check is not a pass.")
        return 1
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
        model_keys = set(pg.evaluate("MODELS.map(m=>m.k)"))

        pg.click("text=Findings"); pg.wait_for_timeout(2000)
        lb = pg.evaluate(LB_JS)
        if lb.get("err"):
            fails.append(lb["err"])
        else:
            if lb["rows"] != 14:
                fails.append(f"leaderboard has {lb['rows']} rows; expected 14")
            if lb["checked"] < lb["rows"] * 6:
                fails.append(f"leaderboard compared {lb['checked']} values; expected {lb['rows']*6}")
            for x in lb["bad"]: fails.append("leaderboard " + x)
            print(f"  Findings leaderboard: {lb['checked']} values across {lb['rows']} rows")

        pg.click("text=Cases"); pg.wait_for_timeout(2500)
        r = pg.evaluate(CASES_JS)
        if r.get("err"):
            fails.append(r["err"])
        else:
            print(f"  Cases: {r['checked']} cells across {r['cols']} model columns, {r['rows']} rows")
            # exact counts, not a floor: a floor let a 1,300-of-1,400 probe look complete
            if r["rows"] != 100:
                fails.append(f"Cases has {r['rows']} rows; expected exactly 100")
            ckeys = r.get("colKeys") or []
            if len(set(ckeys)) != len(ckeys):
                fails.append("Cases repeats a model column")
            if set(ckeys) != model_keys:
                miss = sorted(model_keys - set(ckeys)); extra = sorted(set(ckeys) - model_keys)
                fails.append(f"Cases model columns differ from MODELS; missing {miss}, unexpected {extra}")
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
            if sr["idFromTitle"] != sr["payloadId"]:
                fails.append(f"Situation Room title shows {sr['idFromTitle']!r}, payload {sr['payloadId']!r}")
            if not sr["titleHasSpeaker"]:
                fails.append("Situation Room title does not name the passage's speaker")
            if not sr["bodyMatches"]:
                fails.append(f"Situation Room body is not the passage text "
                             f"({sr['bodyLen']} chars shown, {sr['wantLen']} expected)")
            if sr["shownRef"] != sr["wantRef"]:
                fails.append(f"Situation Room reference: shows {sr['shownRef']!r}, payload {sr['wantRef']!r}")
            # exact unique key SET, not a row count: 14 copies of one configuration passed before
            keys = sr["keys"]
            if len(set(keys)) != len(keys):
                fails.append("Situation Room repeats a configuration")
            if set(keys) != model_keys:
                miss = sorted(model_keys - set(keys)); extra = sorted(set(keys) - model_keys)
                fails.append(f"Situation Room key set differs; missing {miss}, unexpected {extra}")
            for x in sr["bad"]:
                fails.append("Situation Room " + x)
            print(f"  Situation Room: {sr['n']} configurations, identity + reference + all calls checked")
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
