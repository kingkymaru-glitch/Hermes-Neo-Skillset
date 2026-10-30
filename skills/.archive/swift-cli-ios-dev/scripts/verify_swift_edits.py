#!/usr/bin/env python3
"""Generic, re-runnable consistency + syntax checker for Swift edit verification.

Why: On a CLI host without a usable Xcode build, swiftc -parse gives real syntax
checking and a small consistency script proves the intended behavior landed.
Run from the project dir, then delete this file (it should not be committed).

Usage:
  python3 verify_swift_edits.py FILE1.swift [FILE2.swift ...] \
      --must-contain "text that must be present" \
      --must-not-contain "text that must be gone" \
      --swiftc            # also run `swiftc -parse` on each file

Multiple --must-contain / --must-not-contain allowed (repeat the flag).
Exits non-zero if any check fails.
"""
import argparse
import pathlib
import re
import shutil
import subprocess
import sys

# Bare-reference guard: flags a word used in code (not inside a UI string literal)
# while excluding the safe call-site names. Reuse the pattern from the trips refactor.
BARE_REF = re.compile(
    r"\b{trips}\b(?!For|\.filter|\.contains\( |\.map|\.isEmpty|Listener)"
)
SAFE_NAMES = ("myTrips", "personalTrips", "tripsFor")


def check(name, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    line = f"[{status}] {name}"
    if detail:
        line += f"  ({detail})"
    print(line)
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--must-contain", action="append", default=[])
    ap.add_argument("--must-not-contain", action="append", default=[])
    ap.add_argument("--swiftc", action="store_true", help="also run swiftc -parse")
    args = ap.parse_args()

    results = []
    for f in args.files:
        p = pathlib.Path(f)
        src = p.read_text()
        for needle in args.must_contain:
            results.append(check(f"contains: {needle[:60]}", needle in src,
                                 "" if needle in src else "MISSING"))
        for needle in args.must_not_contain:
            present = needle in src
            results.append(check(f"absent: {needle[:60]}", not present,
                                 "" if not present else "STILL PRESENT"))
        # brace / paren balance
        results.append(check(f"{p.name} brace balance",
                             src.count("{") == src.count("}"),
                             f"{src.count('{')}/{src.count('}')}"))
        results.append(check(f"{p.name} paren balance",
                             src.count("(") == src.count(")"),
                             f"{src.count('(')}/{src.count(')')}"))
        if args.swiftc:
            if shutil.which("swiftc"):
                r = subprocess.run(
                    ["swiftc", "-parse", "-suppress-warnings", f],
                    capture_output=True, text=True)
                ok = r.returncode == 0
                tail = (r.stdout or r.stderr).strip().splitlines()[-3:]
                results.append(check(f"{p.name} swiftc -parse",
                                     ok, "; ".join(tail) if not ok else "exit 0"))
            else:
                results.append(check(f"{p.name} swiftc -parse", False, "swiftc missing"))

    ok = all(results)
    print("=== OVERALL:", "PASS" if ok else "FAIL", "===")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
