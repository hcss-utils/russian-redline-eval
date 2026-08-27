#!/usr/bin/env bash
# The complete active build route, in the ONLY order that composes.
#
# WHY THIS FILE EXISTS. patch_app.py and inject_app.py BOTH rebuild from
# app/index.deployed.backup.html, so running them in either order silently discarded the
# other's work: patch-then-inject lost every structural repair, inject-then-patch collapsed
# a 979 KB page to 182 KB. Nothing failed; the page was simply wrong, which is how the
# deployed page came to be patched past its own producer. inject_app.py honours INJECT_SRC,
# so it can compose ON TOP of the patched page instead of restarting from the backup.
#
# Run from the directory that contains bench/ and app/. Verified end to end on a clean copy:
# the resulting page passes code/verify_app_numbers.py.
set -euo pipefail

# Stage the published inputs where the injectors look for them. Several of them hardcode
# bench/<name>; a public checkout keeps the same files under results/ and data/, so without
# this the route dies on the first one and the "anyone can run it" claim is false.
mkdir -p bench/bench
for f in results_sweep.jsonl results_sequential.jsonl results_sequential_all.jsonl \
         scores.json scores_sequential.json flagged_span_categories.json \
         citation_check_summary.json benchmark_100.json sample_representative_100.json \
         translations.jsonl sequences.json; do
  for d in results data ../results ../data; do
    [ -f "bench/$f" ] || { [ -f "$d/$f" ] && cp "$d/$f" bench/; }
  done
done
cp bench/citation_check_summary.json bench/flagged_span_categories.json bench/bench/ 2>/dev/null || true
python3 bench/build_app_data.py
mkdir -p bench/bench && cp bench/app_data.json bench/bench/ 2>/dev/null || true
python3 bench/patch_app.py                      # structural rebuild from the backup
INJECT_SRC=app/index.html python3 bench/inject_app.py   # data payload ON TOP of it
python3 bench/inject_sequential.py
python3 bench/inject_fabx.py

# A rebuild that prints "complete" without checking anything is how a page that had lost
# all 102 flag mappings passed for correct. Every gate runs, and any failure stops the script.
echo "--- gates ---"
python3 bench/audit_app.py
python3 bench/verify_app_numbers.py app/index.html
python3 bench/test_verify_app_numbers.py app/index.html

# The rendered gates too: a page can carry a correct payload and DRAW it wrongly -- correct
# values under transposed headers is exactly what shipped. Skipped only where no browser
# is installed, and that is reported rather than silently passed.
if python3 -c "import playwright" 2>/dev/null; then
  python3 bench/test_verify_rendered_page.py app/index.html
else
  echo "!! playwright absent: RENDERED gates NOT run (this is a gap, not a pass)"
fi

# The route must reproduce the page that is actually SERVED, not merely a page that passes.
# For weeks it did not: the deployed page had been hand-finished and the rebuild produced a
# different, worse one -- with an inferred confusion matrix and an empty evidence payload --
# while every non-rendered gate reported green. Compare the bytes, or the gates certify a
# page nobody ships.
DEPLOYED="${DEPLOYED_PAGE:-}"
if [ -n "$DEPLOYED" ] && [ -f "$DEPLOYED" ]; then
  if cmp -s app/index.html "$DEPLOYED"; then
    echo "byte-identical to the deployed page"
  else
    echo "!! REBUILD DIFFERS FROM THE DEPLOYED PAGE"
    echo "   rebuilt : $(wc -c < app/index.html) bytes  $(sha256sum app/index.html | cut -c1-16)"
    echo "   deployed: $(wc -c < "$DEPLOYED") bytes  $(sha256sum "$DEPLOYED" | cut -c1-16)"
    exit 1
  fi
else
  echo "!! DEPLOYED_PAGE not set: byte comparison NOT run (this is a gap, not a pass)"
fi
echo "rebuild complete AND verified -> app/index.html"
