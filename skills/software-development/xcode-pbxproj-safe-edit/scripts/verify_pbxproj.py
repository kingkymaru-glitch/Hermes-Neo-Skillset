#!/usr/bin/env python3
"""Static verifier for an Xcode .pbxproj from a non-iOS CLI.

Re-runnable replacement for the hand-typed plutil/brace/headless checks. NOT a build -
Xcode Cmd+B is authoritative. Run:

    python3 verify_pbxproj.py <path-to/project.pbxproj> [--expect-missing "substr"]

Exit code 0 = static checks pass; 1 = a check failed.
"""
import subprocess, sys


def main():
    if len(sys.argv) < 2:
        print("usage: verify_pbxproj.py <project.pbxproj> [--expect-missing 'substr']")
        return 2
    pbx = sys.argv[1]
    expect_missing = sys.argv[sys.argv.index("--expect-missing") + 1] if "--expect-missing" in sys.argv else None

    s = open(pbx, encoding="utf-8", errors="ignore").read()
    ok = True

    r = subprocess.run(["plutil", "-lint", pbx], capture_output=True, text=True)
    plutil_ok = "OK" in r.stdout
    print(f"[verify] plutil -lint: {'OK' if plutil_ok else 'FAIL'} -> {r.stdout.strip()}")
    ok &= plutil_ok

    d = 0; ins = False; esc = False
    for ch in s:
        if ins:
            if esc: esc = False
            elif ch == '\\': esc = True
            elif ch == '"': ins = False
            continue
        if ch == '"': ins = True; continue
        if ch == '{': d += 1
        elif ch == '}': d -= 1
    print(f"[verify] brace depth: {d} -> {'BALANCED' if d == 0 else 'IMBALANCED'}")
    ok &= (d == 0)

    lines = s.split("\n")
    bad = []
    for i, l in enumerate(lines):
        if l.strip() == "children = (":
            j = i - 1
            while j >= 0 and lines[j].strip() == "":
                j -= 1
            prev = lines[j].strip() if j >= 0 else ""
            opens_group = prev.rstrip().endswith("{") or "isa = PBXGroup" in (lines[j] if j >= 0 else "")
            if not opens_group:
                bad.append(i + 1)
    print(f"[verify] headless children blocks: {bad if bad else 'none'}")
    ok &= (not bad)

    begins = s.count("/* Begin "); ends = s.count("/* End ")
    print(f"[verify] section Begin/End: {begins}/{ends} -> {'OK' if begins == ends else 'MISMATCH'}")
    ok &= (begins == ends)

    if expect_missing is not None:
        n = s.count(expect_missing)
        print(f"[verify] expect-missing {expect_missing!r}: found {n} -> {'OK' if n == 0 else 'STILL PRESENT'}")
        ok &= (n == 0)

    print("[verify] STATIC ONLY - authoritative gate is Cmd+B in Xcode (no iOS SDK here).")
    print(f"[verify] RESULT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
