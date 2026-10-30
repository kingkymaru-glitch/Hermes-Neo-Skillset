#!/usr/bin/env python3
"""Statically verify a single-file HTML web app whose JS lives in an inline
<script type="module">. No browser required.

1. Extracts the inline module script via regex.
2. Runs `node --check` for syntax validity.
3. AUTO-DETECTS dangling DOM references: every literal id passed to
   getElementById('X') / querySelector('#X') in the JS is cross-checked against
   the set of ids defined in the HTML markup. Any referenced-but-undefined id is
   reported. This is the #1 cause of a module that silently aborts at LOAD and
   kills every listener defined after the bad line (e.g. removing a <select> but
   leaving getElementById('select').addEventListener at top level throws null and
   aborts the whole <script type="module">).
4. Also scans for explicit --refs tokens you pass manually.

Usage:
    python3 verify_inline_js.py <file.html> [--refs tok1 tok2 ...]

Exit codes: 0 = SYNTAX_OK (findings reported to stdout), 1 = SYNTAX_FAIL,
2 = no module script found.
"""
import re
import sys
import os
import subprocess
import tempfile


def main():
    args = sys.argv[1:]
    if not args:
        print("usage: verify_inline_js.py <file.html> [--refs tok1 tok2 ...]")
        sys.exit(2)

    path = args[0]
    refs = [a for a in args[1:] if not a.startswith("--")]

    with open(path, encoding="utf-8") as f:
        s = f.read()

    m = re.search(r'<script type="module">(.*?)</script>', s, re.S)
    if not m:
        print("NO_MODULE_SCRIPT")
        sys.exit(2)

    js = m.group(1)
    fd, tmp = tempfile.mkstemp(suffix=".mjs")
    with os.fdopen(fd, "w") as f:
        f.write(js)

    r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
    os.unlink(tmp)

    if r.returncode != 0:
        print("SYNTAX_FAIL")
        print(r.stderr)
        sys.exit(1)

    print("SYNTAX_OK")

    # --- Auto DOM-id cross check (literal ids only; dynamic ids skipped) ---
    html_ids = set(re.findall(r'id="([^"]+)"', s))
    gebi = set(re.findall(r"getElementById\(['\"]([^'\"]+)['\"]\)", s))
    qs = set(re.findall(r"querySelector(?:All)?\(['\"]#([A-Za-z0-9_-]+)['\"]", s))
    referenced = gebi | qs
    missing = sorted(referenced - html_ids)
    if missing:
        print("DANGLING_DOM_IDS (referenced in JS, NOT defined in HTML):")
        for mid in missing:
            print(f"  - {mid}")
    else:
        print("clean   all getElementById/querySelector ids resolve to HTML ids")

    # --- Manual token scan ---
    for tok in refs:
        c = s.count(tok)
        if c:
            print(f"DANGLING {tok} -> {c}")
        else:
            print(f"clean   {tok}")


if __name__ == "__main__":
    main()
