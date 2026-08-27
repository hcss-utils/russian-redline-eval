#!/usr/bin/env python3
"""Acceptance test for verify_app_numbers.py.

A checker is not evidence until it has been shown to FAIL on a bad input. This
feeds it the six defects that were actually found on this project's dashboard,
each reconstructed by tampering with a copy of the live page, and asserts that
each one is caught. Run: python3 code/test_verify_app_numbers.py <app/index.html>
"""
import io, re, sys, subprocess, os, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.join(HERE, "verify_app_numbers.py")

# Each case is (label, regex, replacement). REGEX, not an exact string: the deployed page
# serialises its payloads as JSON ("cm": [[...]]) while the injector emits JS literals
# (cm:[[...]]), so exact anchors matched one and silently SKIPPED on the other -- nine of
# seventeen cases, which made a rebuilt page report 8/17 and look like a checker failure.
# A skip is still reported as a stale test, never as a pass.
CASES = [
    ("stale SEQ decision count",   r'(n_decisions"?\s*:\s*)816',        r'\g<1>624'),
    ("stale SEQ catch count",      r'("?caught"?\s*:\s*)14\b',          r'\g<1>13'),
    ("invented / negative matrix", r'("?cm"?\s*:\s*)\[\[124,.*?\]\]',
                                   r'\g<1>[[63,2,1],[1,15,0],[3,-3,18]]'),
    ("false alerts = missed nuclear", r'("?fa"?\s*:\s*)1(,\s*"?mn"?\s*:\s*)0', r'\g<1>0\g<2>0'),
    ("stale citation totals",      r'("?A"?\s*:\s*)238(,\s*"?B"?\s*:\s*)33', r'\g<1>239\g<2>32'),
    ("fabricated error-table cell",
     r'(<tr><td style="text-align:left">False NTS alert</td><td[^>]*>)1(\s*<span)', r'\g<1>18\g<2>'),
    ("stale leaderboard accuracy", r'("?rls"?\s*:\s*)0\.9\b',          r'\g<1>0.87'),
    ("stale per-span flag rate",   r'("?flag_rate"?\s*:\s*)0\.422',     r'\g<1>0.402'),
    ("cm total disagrees with parsed", r'("?parsed"?\s*:\s*)189',        r'\g<1>200'),
    ("static cost headline",       r'Measured cost: \$22\.38',           'Measured cost: $99.99'),
    ("static total-cost tile",     r'\$22\.38(</div><div class="kpi-label">total cost)', r'$99.99\g<1>'),
    ("static decisions tile",      r'2,800(</div><div class="kpi-label">scored decisions)', r'9,999\g<1>'),
    ("FABX payload deleted",       r'FABX\s*=',                          'FABX_REMOVED='),
    ("MODELS payload deleted",     r'const MODELS\s*=',                  'const MODELS_REMOVED='),
    ("passage #001 reference tampered", r'(P\("#001",")NTS(")',          r'\g<1>None\g<2>'),
    ("passage flag mappings dropped",   r'\{"[a-z0-9_.]+"\s*:\s*true\}', '{}'),
    ("PASSAGES payload deleted",   r'const PASSAGES\s*=',                'const PASSAGES_REMOVED='),
]

def run(path):
    return subprocess.run([sys.executable, CHECKER, path], capture_output=True, text=True).returncode

def main(app):
    src = io.open(app, encoding="utf-8").read()
    if run(app) != 0:
        print("FAIL: the checker does not pass on the CURRENT app; fix the app first")
        return 1
    print("ok    clean app passes")
    bad = 0
    for label, find, repl in CASES:
        if not re.search(find, src):
            print(f"SKIP  {label}: anchor absent (serialisation changed?) -- test is stale, not the app")
            bad += 1
            continue
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as fh:
            fh.write(re.sub(find, repl, src, count=1)); tmp = fh.name
        rc = run(tmp); os.unlink(tmp)
        if rc == 0:
            print(f"FAIL  {label}: checker did NOT catch it"); bad += 1
        else:
            print(f"ok    {label}: caught")
    print(("FAIL" if bad else "PASS") + f" — {len(CASES)-bad}/{len(CASES)} defects caught")
    return 1 if bad else 0

if __name__ == "__main__":
    if len(sys.argv) < 2: raise SystemExit("usage: test_verify_app_numbers.py <app/index.html>")
    sys.exit(main(sys.argv[1]))
