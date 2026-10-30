#!/usr/bin/env python3
"""Ad-hoc static verification for a Swift/SwiftUI file.
String-aware brace/quote balance + corruption greps. Run from the Xcode project root.

Usage: python3 verify_swift.py <path-to-file.swift>
Prints: brace depth (0 = balanced), any NEGATIVE dips (syntax corruption),
        count of .alert( calls, and common corruption greps.
"""
import sys, re

path = sys.argv[1]
src = open(path, encoding="utf-8").read()

depth = 0
instr = False
esc = False
neg = []
for i, ch in enumerate(src):
    if instr:
        if esc:
            esc = False
        elif ch == "\\":
            esc = True
        elif ch == '"':
            instr = False
    else:
        if ch == '"':
            instr = True
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth < 0:
                neg.append((i, ch))
print("brace_depth:", depth, "| balanced:", depth == 0)
print("negative_dips (syntax corruption if any):", neg[:5])
print("alert_calls:", src.count(".alert("))
# known corruption: modifier lost its opening paren
for ln, line in enumerate(src.splitlines(), 1):
    if re.search(r"\.(aler|alet|ale)[^t(]", line):
        print("SUSPECT line", ln, ":", line.strip())
