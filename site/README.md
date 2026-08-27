# Rebuilding the dashboard

The page served at <https://rubase.org/redline-eval/> is generated from the published
`results/` and `data/` in this repository. Nothing on it is typed by hand.

    DEPLOYED_PAGE=site/app/index.html bash site/bench/rebuild.sh

Run from the repository root. The script runs five gates and **refuses to finish** if any
fails:

| gate | what it establishes |
|---|---|
| `audit_app.py` | no placeholder text, no dead fields, the emitted slate matches the data |
| `verify_app_numbers.py` | every figure in the page's **source** reconciles with `results/` |
| `test_verify_app_numbers.py` | that checker is shown to FAIL on 20 defects actually found here |
| `verify_rendered_page.py` | every figure a reader **sees** reconciles with the payload the page loads (needs a browser) |
| `test_verify_rendered_page.py` | that checker is shown to FAIL on 14 bad renders |
| byte comparison | the rebuilt page is **byte-identical** to the deployed one |

## Why the two acceptance suites exist

Over an adversarial review of this dashboard, **every** gate was at some point reporting success
while doing nothing: a checker that skipped a payload it could not parse, an audit whose regex
compared an empty set, a test whose anchors matched one serialisation and silently skipped on the
other, and a build script that printed "complete" without running any of them.

So each checker ships with a suite that reconstructs real defects from this project's history and
requires that each one is **caught**. A skipped case is reported as a stale test, never as a pass;
a missing input is a failure, never a pass; and a missing browser fails rather than exiting 0.

## Order matters

`patch_app.py` and `inject_app.py` both rebuild from `app/index.deployed.backup.html`. Run in
either order they discard each other's work — silently. `rebuild.sh` records the one order that
composes and why.
