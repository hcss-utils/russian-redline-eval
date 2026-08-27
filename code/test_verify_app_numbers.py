#!/usr/bin/env python3
"""Acceptance test for verify_app_numbers.py.

A checker is not evidence until it has been shown to FAIL on a bad input. This
feeds it the six defects that were actually found on this project's dashboard,
each reconstructed by tampering with a copy of the live page, and asserts that
each one is caught. Run: python3 code/test_verify_app_numbers.py <app/index.html>
"""
import io, sys, subprocess, os, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.join(HERE, "verify_app_numbers.py")

CASES = [
    ("stale SEQ decision count",      '"n_decisions": 816', '"n_decisions": 624'),
    ("stale SEQ catch count",         '"caught": 14',       '"caught": 13'),
    ("invented / negative matrix",    '"cm":[[124,8,0],[1,31,0],[0,2,34]]',
                                      '"cm":[[63,2,1],[1,15,0],[3,-3,18]]'),
    ("false alerts = missed nuclear", '"fa":0,"mn":2',      '"fa":2,"mn":2'),
    ("stale citation totals",         '"A": 238, "B": 33',  '"A": 239, "B": 32'),
    ("fabricated error-table cell",
     '<tr><td style="text-align:left">False NTS alert</td><td>1 <span',
     '<tr><td style="text-align:left">False NTS alert</td><td>18 <span'),
    # added after extending the checker to the leaderboard scalars
    ("stale leaderboard accuracy",     '"rls":0.9,',        '"rls":0.87,'),
    ("stale per-span flag rate",       '"flag_rate":0.422', '"flag_rate":0.402'),
    ("cm total disagrees with parsed", '"parsed":189',      '"parsed":200'),
    # Sol's round-16 counterexample: a STATIC displayed figure, in prose rather than a payload
    ("static cost headline",           'Measured cost: $22.38', 'Measured cost: $99.99'),
    ("static total-cost tile",         '$22.38</div><div class="kpi-label">total cost',
                                       '$99.99</div><div class="kpi-label">total cost'),
    ("static decisions tile",          '2,800</div><div class="kpi-label">scored decisions',
                                       '9,999</div><div class="kpi-label">scored decisions'),
    # fail-closed: deleting a payload must FAIL, not silently skip
    ("FABX payload deleted",           'FABX=',              'FABX_REMOVED='),
    ("MODELS payload deleted",         'const MODELS=',      'const MODELS_REMOVED='),
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
        if find not in src:
            print(f"SKIP  {label}: anchor absent (serialisation changed?) -- test is stale, not the app")
            bad += 1
            continue
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as fh:
            fh.write(src.replace(find, repl, 1)); tmp = fh.name
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
