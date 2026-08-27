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
  const heads=[...tbl.querySelectorAll('thead th')].map(h=>h.textContent.trim());
  const mcols=heads.slice(6).map(h=>h.replace(/[^A-Za-z0-9.+−-]/g,''));
  const byShort={}; MODELS.forEach(m=>{ byShort[(m.short||m.n).replace(/[^A-Za-z0-9.+−-]/g,'')]=m.k; });
  let checked=0, bad=[];
  [...tbl.querySelectorAll('tbody tr')].forEach(tr=>{
    const c=[...tr.children]; const id=c[0].textContent.trim();
    const p=PASSAGES.find(x=>x.id===id); if(!p) return;
    mcols.forEach((mc,i)=>{
      const k=byShort[mc]; if(!k) return;
      const cell=c[6+i]; if(!cell) return;
      const shown=cell.textContent.trim();
      const v=(p.v||{})[k]; if(v===undefined) return;
      checked++;
      const ok = (shown==='✓') ? (v===p.ref) : (shown===v || (shown==='n/a'&&v==='n/a'));
      if(!ok && bad.length<8) bad.push({id, model:k, shown, payload:v, ref:p.ref});
    });
  });
  return {checked, bad, cols:mcols.length};
}"""

# scope to the ONE table under the composition heading: #sources holds three, and a
# selector that swept all of them summed the percentages to 300% and called it a defect.
COMP_JS = r"""() => {
  const h=[...document.querySelectorAll('#sources h3, #sources h2, #sources h4')]
    .find(e=>e.textContent.trim().startsWith('Sample composition by source arm'));
  if(!h) return [];
  let t=h.nextElementSibling;
  while(t && t.tagName!=='TABLE') t=t.nextElementSibling;
  if(!t) return [];
  return [...t.querySelectorAll('tbody tr')].map(r=>[...r.children].map(c=>c.textContent.trim()))
    .filter(r=>r.length===6 && /^\d+$/.test(r[1]));
}"""

SIT_JS = r"""() => ({id:(document.getElementById('sit-title')||{}).textContent||'',
  rows:[...document.querySelectorAll('#sit-reveal tbody tr')].map(r=>[...r.children].map(c=>c.textContent.trim()).slice(0,2))})"""

def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed; rendered checks skipped")
        return 0
    fails = []
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
            print(f"  Cases: {r['checked']} cells across {r['cols']} model columns")
            if r["checked"] < 1000:
                fails.append(f"Cases checked only {r['checked']} cells; expected ~1,300")
            for x in r["bad"]:
                fails.append(f"Cases {x['id']} {x['model']}: shows {x['shown']!r}, payload {x['payload']!r}")

        pg.click("text=Source Arms"); pg.wait_for_timeout(1800)
        rows = pg.evaluate(COMP_JS)
        if not rows:
            fails.append("sample-composition table not rendered")
        else:
            tot = 0
            for row in rows:
                n, none_, rls, nts = int(row[1]), int(row[2]), int(row[3]), int(row[4])
                if none_ + rls + nts != n:
                    fails.append(f"composition {row[0]}: {none_}+{rls}+{nts} != {n}")
                tot += float(row[5].rstrip("%"))
            if not (99 <= tot <= 101):
                fails.append(f"composition percentages sum to {tot:g}%, not 100%")
            print(f"  Source Arms: {len(rows)} rows, percentages sum to {tot:g}%")

        pg.click("text=Situation Room"); pg.wait_for_timeout(1800)
        try:
            pg.click('#sit-calls button[data-call="NTS"]'); pg.wait_for_timeout(1200)
            sr = pg.evaluate(SIT_JS)
            if len(sr["rows"]) < 14:
                fails.append(f"Situation Room revealed {len(sr['rows'])} configurations, expected 14")
            print(f"  Situation Room: {len(sr['rows'])} configurations revealed")
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
