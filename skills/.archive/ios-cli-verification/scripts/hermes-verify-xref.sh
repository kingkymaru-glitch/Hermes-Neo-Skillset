#!/usr/bin/env bash
# hermes-verify-xref.sh — static CROSS-REFERENCE check for an Xcode-less SwiftUI project.
#
# What it catches that brace/grep checks MISS (all are real compile errors):
#   1. USED-BUT-UNDECLARED members on a shared service (e.g. `appState.savePoster`
#      when the method is actually `pushPoster`, or `appState.myTrips` that was
#      never declared) -> "Value of type AppState has no member X" / "Cannot find in scope".
#   2. DUPLICATE top-level type declarations (e.g. `enum ThemeManager` defined in
#      two files) -> "invalid redeclaration of 'ThemeManager'".
#   3. Brace / paren / bracket imbalance across all .swift files.
#
# NOT a real compile. Run: bash hermes-verify-xref.sh <project-root>
# Optional env overrides: SERVICE=AppState  SERVICE_FILE=Core/Services/AppState.swift
set -u
ROOT="${1:-.}"
SERVICE="${SERVICE:-AppState}"
SERVICE_FILE="${SERVICE_FILE:-Core/Services/AppState.swift}"

files=()
while IFS= read -r -d '' f; do files+=("$f"); done < <(find "$ROOT" -name '*.swift' -not -path '*/xcodeproj/*' -print0)

python3 - "$ROOT" "$SERVICE" "$SERVICE_FILE" <<'PYEOF'
import re, os, sys
root, service, svcfile = sys.argv[1], sys.argv[2], sys.argv[3]
files=[]
for dp,_,fs in os.walk(root):
    if 'xcodeproj' in dp: continue
    for f in fs:
        if f.endswith('.swift'): files.append(os.path.join(dp,f))
allsrc={os.path.basename(p):open(p,encoding='utf-8',errors='ignore').read() for p in files}
joined="\n".join(allsrc.values())

# 1) declarations of the service type
sp = svcfile if os.path.isabs(svcfile) else os.path.join(root, svcfile)
ast = allsrc.get(os.path.basename(sp), joined)
decls=set(re.findall(r'(?:@Published )?(?:private |fileprivate |internal |public )?(?:var|let|func)\s+([A-Za-z_][A-Za-z0-9_]*)', ast))
for m in re.finditer(r'(?:var|let)\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*[A-Za-z]', ast):
    decls.add(m.group(1))

used=set(re.findall(r'%s\.([A-Za-z_][A-Za-z0-9_]*)' % re.escape(service), joined))
miss=sorted(u for u in used if u not in decls)
print("[%s.<x> undeclared]:" % service, miss if miss else "NONE")
if miss:
    print("   -> each of these is a real 'has no member' compile error.")
    print("      grep -rn '%s.<x>' to confirm, then DECLARE the member (or fix the call)." % service)

# 2) duplicate top-level types (struct/class/enum/protocol at column 0)
tops=[]
for p,s in allsrc.items():
    for m in re.finditer(r'^(?:struct|class|enum|protocol)\s+([A-Za-z_][A-Za-z0-9_]*)\b', s, re.M):
        tops.append(m.group(1))
dups=[k for k in set(tops) if tops.count(k)>1]
print("[dup top-level types]:", dups if dups else "NONE")
if dups:
    print("   -> duplicate type = 'invalid redeclaration' error. Keep ONE definition (prefer the standalone file).")

# 3) brace / paren / bracket balance
bad=[]
for p,s in allsrc.items():
    for op,cl,n in [('{','}','b'),('(',')','p'),('[',']','k')]:
        if s.count(op)!=s.count(cl): bad.append(os.path.basename(p)+":"+n)
print("[balance]:", "PASS" if not bad else bad)

print("\nAD-HOC cross-reference only. Real compile / Xcode Cmd+B is the gate.")
PYEOF
