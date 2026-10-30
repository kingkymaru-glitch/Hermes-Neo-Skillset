#!/usr/bin/env python3
"""Drive the live Reverse Engineer endpoint across a spread of real binaries.

Why: the RE tab advertises no limits, so the only honest answer to "can it handle X?"
is a timed run. This posts each target to POST /api/re/analyze exactly as the UI does,
prints one row per target, and appends JSONL so a later session can diff the numbers.

Usage:
    python3 re_target_practice.py                       # auto-pick a size spread
    python3 re_target_practice.py /path/to/app /bin/ls  # explicit targets

Read the result as a size threshold, not a pass/fail: small launcher stubs return in
seconds with a readable tree, while multi-MB native apps return thousands of nodes and a
hundreds-of-thousands-of-pixels-tall SVG, and the largest simply time out with nothing
written.
"""
import json
import os
import re
import subprocess
import sys
import time

DASHBOARD = os.environ.get("INTEL_RE_DASHBOARD", "http://127.0.0.1:8765")
REPORTS = os.environ.get("INTEL_RE_REPORTS", "~/re-reports")
OUT = os.environ.get("INTEL_RE_RESULTS", "~/.hermes/cache/scratch/re_target_practice.jsonl")
CURL_MAX_S = "420"  # the server itself gives up at 300 s; allow for the round trip


def discover(limit=7):
    """A size spread of real app binaries, smallest launcher to biggest app."""
    found = []
    for app in sorted(os.listdir("/Applications")):
        if not app.endswith(".app"):
            continue
        path = os.path.join("/Applications", app, "Contents", "MacOS", app[:-4])
        if os.path.isfile(path):
            found.append((os.path.getsize(path), path))
    found.sort()
    if not found:
        return []
    # Even spread across the size range rather than the N smallest.
    step = max(1, len(found) // limit)
    return [p for _s, p in found[::step]][:limit]


def probe(path):
    slug = re.sub(r"[^0-9A-Za-z._-]+", "-", os.path.basename(path)).strip("-").lower() or "target"
    rec = {"slug": slug, "path": path, "size_bytes": os.path.getsize(path)}
    t0 = time.time()
    proc = subprocess.run(
        ["curl", "-s", "-X", "POST", f"{DASHBOARD}/api/re/analyze",
         "-F", f"file=@{path}", "-F", f"place={REPORTS}", "-F", f"name={slug}-tree",
         "-m", CURL_MAX_S],
        capture_output=True, text=True,
    )
    rec["elapsed_s"] = round(time.time() - t0, 1)
    try:
        d = json.loads(proc.stdout)
    except Exception as exc:
        rec.update(success=False, error=f"unparseable response ({exc}): {proc.stdout[:200]}")
        return rec

    rec["success"] = bool(d.get("success"))
    if not rec["success"]:
        rec["error"] = d.get("error")
        return rec

    a = d.get("analysis") or {}
    m = a.get("metadata") or {}
    svg = d.get("pipeline_svg") or ""
    dim = re.search(r'width="(\d+)" height="(\d+)"', svg)
    rec.update(
        language=(a.get("program_info") or {}).get("language"),
        slice=m.get("slice_analyzed"),
        functions=len(a.get("functions") or []),
        edges=len(a.get("call_graph") or []),
        nodes=svg.count("<g><title>"),
        svg_dim=(dim.group(1) + "x" + dim.group(2)) if dim else None,
        svg_bytes=len(svg),
    )
    # A non-native language on Apple Silicon means slice selection regressed.
    if rec.get("language") and not rec["language"].startswith("AARCH64"):
        rec["warning"] = "analyzed a non-native slice"
    return rec


def main():
    targets = sys.argv[1:] or discover()
    if not targets:
        print("no targets found")
        return 1
    out_path = os.path.expanduser(OUT)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w"):
        pass

    print(f"{'target':<34} {'MB':>7} {'time':>7}  result")
    for path in targets:
        try:
            rec = probe(path)
        except Exception as exc:
            rec = {"slug": os.path.basename(path), "path": path, "success": False, "error": str(exc)}
        with open(out_path, "a") as fh:
            fh.write(json.dumps(rec) + "\n")
        label = os.path.basename(rec.get("path", "?"))[:33]
        mb = (rec.get("size_bytes") or 0) / 1048576.0
        if rec.get("success"):
            result = "%s nodes, %s edges, %s" % (rec.get("nodes"), rec.get("edges"), rec.get("svg_dim"))
            if rec.get("warning"):
                result += "  !! " + rec["warning"]
        else:
            result = "FAILED: " + str(rec.get("error"))[:70]
        print(f"{label:<34} {mb:>7.2f} {rec.get('elapsed_s', 0):>6}s  {result}", flush=True)

    print(f"\nJSONL: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
