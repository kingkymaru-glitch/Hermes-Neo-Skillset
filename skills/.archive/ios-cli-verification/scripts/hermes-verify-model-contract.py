#!/usr/bin/env python3
"""
hermes-verify-model-contract.py — ad-hoc static gate for Swift model/enum/view
contracts when no Xcode build is possible. Asserts:
  * delimiter balance ({ } ( ) [ ]) per file
  * no duplicate TOP-LEVEL type declarations across files (invalid redeclaration)
  * requested protocol conformances present on named types (Codable, Identifiable,
    CaseIterable, ObservableObject, Equatable, Hashable, ...)
  * exhaustiveness of a `switch self` inside an enum's computed property
    (every declared `case foo =` must be covered by `case .foo:` in the body)
  * a constructor call's args are all exposed by the target struct's `init`

Uses a real brace-matcher (not `.*?` regex) so nested `{}` inside enums/props
don't truncate the scan. This is NOT a compile — label results "ad-hoc static".

Run:
  python3 hermes-verify-model-contract.py FILE [FILE ...] \
      [--require-conf Type:Conf,Conf ...] \
      [--exhaustive-enum EnumName] \
      [--ctor-call 'Type(arg1,arg2)' --ctor-init-file FILE]

Example (this AnglerGO session):
  python3 hermes-verify-model-contract.py \
      Features/Calendar/CalendarScreenView.swift \
      --require-conf TripProposal:Codable,Identifiable \
      --require-conf CalendarMode:CaseIterable,Identifiable \
      --exhaustive-enum QuoteStatus
"""
import re, sys

def delims(s):
    out = {}
    for label, op, cl in [("braces", "{", "}"), ("parens", "(", ")"), ("brackets", "[", "]")]:
        out[label] = (s.count(op), s.count(cl))
    return out

def match_brace(s, open_idx):
    """Return index of matching '}' for s[open_idx]=='{', skipping strings/comments."""
    depth = 0
    i = open_idx
    while i < len(s):
        c = s[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return i
        elif c == '"' or c == "'":
            q = c; i += 1
            while i < len(s):
                if s[i] == '\\':
                    i += 2; continue
                if s[i] == q:
                    break
                i += 1
        elif c == '/' and i + 1 < len(s) and s[i+1] == '*':
            j = s.find('*/', i + 2)
            i = j + 2 if j != -1 else len(s)
            continue
        i += 1
    return -1

def top_level_types(text):
    types = {}
    for m in re.finditer(r"^(?:struct|enum|class|protocol)\s+(\w+)", text, re.M):
        types[m.group(1)] = types.get(m.group(1), 0) + 1
    return types

def main():
    args = sys.argv[1:]
    reqs, exhaust, ctor, ctor_file, files = [], None, None, None, []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--require-conf":
            reqs.append(args[i+1]); i += 2
        elif a == "--exhaustive-enum":
            exhaust = args[i+1]; i += 2
        elif a == "--ctor-call":
            ctor = args[i+1]; i += 2
        elif a == "--ctor-init-file":
            ctor_file = args[i+1]; i += 2
        else:
            files.append(a); i += 1

    problems = []
    texts = {f: open(f).read() for f in files}

    # 1. delimiter balance
    for f, s in texts.items():
        for lab, (o, c) in delims(s).items():
            if o != c:
                problems.append(f"{f} {lab} {o}/{c}")

    # 2. duplicate top-level types
    agg = {}
    for f, s in texts.items():
        for t, n in top_level_types(s).items():
            agg.setdefault(t, []).append(f)
    for t, occ in agg.items():
        if len(occ) > 1:
            problems.append(f"DUPLICATE top-level type '{t}' in {occ}")

    # 3. required conformances
    for r in reqs:
        name, confs = r.split(":", 1)
        confs = [c.strip() for c in confs.split(",")]
        header = None
        for s in texts.values():
            m = re.search(rf"^(?:struct|enum|class|protocol)\s+{re.escape(name)}\s*:\s*([^\n{{]+)", s, re.M)
            if m:
                header = m.group(1); break
        if header is None:
            problems.append(f"type '{name}' not found for conformance check")
        else:
            for c in confs:
                if c not in header:
                    problems.append(f"{name} missing conformance {c}")

    # 4. exhaustive enum switch
    if exhaust:
        alltext = "\n".join(texts.values())
        m = re.search(rf"enum {re.escape(exhaust)}\b[^{{\n]*\{{\s*\n", alltext)
        if not m:
            problems.append(f"enum '{exhaust}' header not found")
        else:
            end = match_brace(alltext, m.end() - 1)
            body = alltext[m.end():end]
            declared = set(re.findall(r"case\s+(\w+)\s*=", body))
            sw = re.search(r"switch self\s*\{", body)
            if not sw:
                problems.append(f"no 'switch self' inside {exhaust}")
            else:
                send = match_brace(body, sw.end() - 1)
                covered = set(re.findall(r"case\s+\.(\w+):", body[sw.end():send]))
                missing = declared - covered
                if missing:
                    problems.append(f"{exhaust} switch missing cases {missing}")

    # 5. ctor <-> init contract
    if ctor and ctor_file:
        s = texts.get(ctor_file) or open(ctor_file).read()
        cm = re.match(r"(\w+)\((.*)\)", ctor)
        if not cm:
            problems.append(f"bad --ctor-call shape: {ctor}")
        else:
            typ, argstr = cm.group(1), cm.group(2)
            call_args = [a.split(":")[0].strip() for a in argstr.split(",") if a.strip()]
            initm = re.search(rf"struct {re.escape(typ)}\b.*?init\((.*?)\)\s*\{{\s*\n", s, re.S)
            if not initm:
                problems.append(f"{typ}.init not found in {ctor_file}")
            else:
                params = [p.split(":")[0].strip() for p in initm.group(1).split(",") if p.strip()]
                for a in call_args:
                    if a not in params:
                        problems.append(f"{typ}.init missing param '{a}' (called with it)")

    print("RESULT:", "PASS (ad-hoc static)" if not problems else f"FAIL: {problems}")
    sys.exit(0 if not problems else 1)

if __name__ == "__main__":
    main()
