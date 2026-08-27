#!/usr/bin/env python3
"""Acceptance test for verify_rendered_page.py.

Same rule as the numeric checker: a checker is not evidence until it has been
shown to FAIL on a bad input. The rendered checker had none, so it was a comment.

This serves a LOCAL copy of the page over http (the checker needs a real browser,
and file:// would not exercise the same load path), tampering the copy each time,
and asserts the checker rejects each broken render:

  * a Cases cell that disagrees with the payload it claims to render;
  * a composition row whose parts do not sum to its own total;
  * composition percentages that do not sum to 100;
  * the Situation Room's call buttons removed, so its reveal cannot be produced;
  * a thrown console error.

Usage: python3 code/test_verify_rendered_page.py <path to app/index.html>
"""
import io, os, re, sys, subprocess, tempfile, threading, http.server, socketserver, functools

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.join(HERE, "verify_rendered_page.py")

CASES = [
    # invert the CELL renderer, not the Correct column: the checker compares each rendered
    # cell against PASSAGES, so only a cell-level lie exercises it
    ("Cases cell disagrees with payload",
     r"(function vCell\(p,k\)\{\s*const got=p\.v\[k\], ok=got)===(p\.ref;)",
     r"\g<1>!==\g<2>"),
    ("composition row does not sum",
     r"(<tr><td[^>]*>telegram_official</td><td>)88(</td>)",
     r"\g<1>99\g<2>"),
    ("composition percentages do not total 100",
     r"(telegram_official</td><td>88</td><td>59</td><td>15</td><td>14</td><td>)88(%</td>)",
     r"\g<1>60\g<2>"),
    ("Situation Room controls removed",
     r'<div id="sit-calls"',
     r'<div id="sit-calls-REMOVED"'),
    ("a console error is thrown",
     r"(<script>\s*document\.addEventListener\('DOMContentLoaded')",
     r"<script>window.addEventListener('load',function(){null.x});</script>\g<1>"),
]

class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

def serve(directory):
    handler = functools.partial(_Quiet, directory=directory)
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]

def run(url):
    return subprocess.run([sys.executable, CHECKER, url], capture_output=True, text=True).returncode

def main(app):
    src = io.open(app, encoding="utf-8").read()
    tmp = tempfile.mkdtemp()
    # copy the sibling assets too: serving the HTML alone 404s every logo, and a page
    # that cannot load its own images is not the page under test.
    import shutil
    appdir = os.path.dirname(os.path.abspath(app))
    for f in os.listdir(appdir):
        if f.lower().endswith((".svg", ".png", ".jpg", ".webp", ".ico", ".woff2")):
            shutil.copy(os.path.join(appdir, f), tmp)
    io.open(os.path.join(tmp, "index.html"), "w", encoding="utf-8").write(src)
    httpd, port = serve(tmp)
    url = f"http://127.0.0.1:{port}/index.html"
    try:
        if run(url) != 0:
            print("FAIL: the checker rejects the UNMODIFIED page; fix the page first")
            return 1
        print("ok    clean page passes")
        bad = 0
        for label, find, repl in CASES:
            if not re.search(find, src):
                print(f"SKIP  {label}: anchor absent -- test is stale, not the page"); bad += 1; continue
            io.open(os.path.join(tmp, "index.html"), "w", encoding="utf-8").write(re.sub(find, repl, src, count=1))
            rc = run(url)
            if rc == 0:
                print(f"FAIL  {label}: checker did NOT catch it"); bad += 1
            else:
                print(f"ok    {label}: caught")
            io.open(os.path.join(tmp, "index.html"), "w", encoding="utf-8").write(src)
        print(("FAIL" if bad else "PASS") + f" — {len(CASES)-bad}/{len(CASES)} bad renders caught")
        return 1 if bad else 0
    finally:
        httpd.shutdown()

if __name__ == "__main__":
    if len(sys.argv) < 2: raise SystemExit("usage: test_verify_rendered_page.py <app/index.html>")
    sys.exit(main(sys.argv[1]))
