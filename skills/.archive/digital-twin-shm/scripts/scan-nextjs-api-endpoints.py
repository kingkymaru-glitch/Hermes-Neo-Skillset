#!/usr/bin/env python3
"""Scan a Next.js app's API routes and extract every external endpoint + local /api call.

Used to build the OSIRIS API catalog (see references/osiris-api-catalog.md). Point it
at the repo root; it walks src/app/api + any extra src dirs, skips build caches
(.next, node_modules, .git), and prints each file's EXTERNAL (https://...) and
LOCAL (/api/...) calls so you can refresh the catalog after an upstream change.

Usage:
    python3 scan-nextjs-api-endpoints.py <repo-root> [extra-src-dirs...]

Example:
    python3 scan-nextjs-api-endpoints.py ~/Downloads/osiris-master ~/Downloads/osiris-master/src/lib
"""
import os
import re
import sys

URL_RE = re.compile(r'https?://[A-Za-z0-9_.\-]+(?::\d+)?(?:/[^\s\'"`\n\)]+)?')
LOCAL_RE = re.compile(r"fetch\(\s*[`'](/api/[^\s'`\"]+)")

# Hosts that are docs/branding, not real data sources — drop from the catalog.
SKIP_HOSTS = ('schema.org', 'osirisai.live', 'simplifaisoul',
              'fonts.google', 'fonts.gstatic')

# Build-cache / vendored dirs to skip so search doesn't flood.
SKIP_DIRS = ('.next', 'node_modules', '.git', 'dist', 'build')


def scan(root: str) -> int:
    rows = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if not f.endswith(('.ts', '.tsx', '.js', '.jsx', '.mjs')):
                continue
            if f.startswith('.'):
                continue
            full = os.path.join(dirpath, f)
            rel = os.path.relpath(full, root)
            try:
                with open(full, encoding='utf-8', errors='replace') as fh:
                    txt = fh.read()
            except Exception:
                continue
            ext = sorted(set(URL_RE.findall(txt)))
            ext = [u for u in ext if not any(h in u for h in SKIP_HOSTS)]
            loc = sorted(set(LOCAL_RE.findall(txt)))
            if ext or loc:
                rows.append((rel, ext, loc))
    rows.sort(key=lambda r: r[0])
    for rel, ext, loc in rows:
        print(f"\n📄 {rel}")
        for u in ext:
            print(f"    EXTERNAL -> {u}")
        for l in loc:
            print(f"    LOCAL    -> {l}")
    return len(rows)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    total = 0
    for target in sys.argv[1:]:
        if not os.path.isdir(target):
            print(f"# skip (not a dir): {target}")
            continue
        total += scan(target)
    print(f"\n# scanned {total} files with hits")
