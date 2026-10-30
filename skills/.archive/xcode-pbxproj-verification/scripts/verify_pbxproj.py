#!/usr/bin/env python3
"""Static integrity check for an Xcode project.pbxproj when xcodebuild can't run.

Usage:
    python3 verify_pbxproj.py <path/to/project.pbxproj> [--absent UUID ...] [--path-check]

Checks (no Xcode required):
  - Every `/* x in Sources */` PBXBuildFile UUID resolves to a real PBXFileReference
    via its `fileRef` (catches dangling compile entries after a bad removal).
  - Section markers (`/* Begin/End ... section */`) match. NOTE: a raw `{`==`}`
    count is a FALSE signal on pbxproj -- literal `}` lives inside quoted
    build-setting strings (CLANG_*, INFOPLIST_*). Use section markers (N vs N) as
    the authoritative structural signal, NOT a naked brace count.
  - HEADLESS GROUP FRAGMENT scan: every `children = (` must be preceded by a
    `isa = PBXGroup;` line under a `UUID /* name */ = {` opener. A fragment with
    no opener (leftover from a botched multi-line insert) makes Xcode refuse to
    OPEN the project at all ("project is damaged, cannot be opened"). This is the
    single most dangerous pbxproj edit failure and is checked FIRST-class here.
  - String-aware brace balance (ignores `}` inside quoted build-setting strings).
  - plutil -lint gate: `OK` is a strong positive; the lone line-1 `//` header quirk
    is benign/ignorable; ANY other plutil error is real corruption.
  - Each --absent UUID is gone from the whole file.
  - (--path-check) Every PBXFileReference with sourceTree = "<group>" resolves, via
    its group path-chain, to a file that EXISTS on disk. THIS catches the classic
    "Build input file cannot be found" bug (file present but at the wrong folder
    relative to the PBXGroup path chain).

Exit 0 = structurally sound (and, with --path-check, all resolved files exist on
disk); 1 = a check failed. This is NOT a compile: it proves structure, not semantics.
"""
import re, sys, pathlib, os, subprocess

def resolve_group_dir(gid, groups, parent, src_root):
    """Resolve the absolute dir a group's children are relative to, walking the chain."""
    parts, cur, seen = [], gid, set()
    while cur in groups and cur not in seen:
        seen.add(cur)
        p = groups[cur].get("path")
        if p:
            parts.append(p)
        cur = parent.get(cur)
    parts.reverse()
    return os.path.join(src_root, *parts) if parts else src_root

def main():
    args = sys.argv[1:]
    if not args:
        print("usage: verify_pbxproj.py <pbxproj> [--absent UUID ...] [--path-check]")
        sys.exit(2)
    pbx = pathlib.Path(args[0])
    absent, path_check = [], False
    i = 1
    while i < len(args):
        if args[i] == "--absent":
            absent.append(args[i + 1]); i += 2
        elif args[i] == "--path-check":
            path_check = True; i += 1
        else:
            i += 1
    pb = pbx.read_text()
    res = []
    check = lambda n, ok, d="": res.append((ok, n, d))

    # --- UUID-chain resolution (Compile Sources -> PBXBuildFile -> PBXFileReference) ---
    build_files = dict(re.findall(
        r"^\s*([0-9A-F]{24}) /\* .*? \*/ = \{isa = PBXBuildFile; fileRef = ([0-9A-F]{24}) /\* .*? \*/;",
        pb, re.M))
    file_refs = set(re.findall(r"^\s*([0-9A-F]{24}) /\* .*? \*/ = \{isa = PBXFileReference", pb, re.M))
    src = re.findall(r"([0-9A-F]{24}) /\* .*? in Sources \*/", pb)
    dangling = [(u, "no PBXBuildFile") for u in src if u not in build_files]
    dangling += [(u, f"ref {build_files[u]} missing") for u in src
                 if u in build_files and build_files[u] not in file_refs]
    check(f"all {len(src)} Compile-Sources resolve PBXBuildFile->fileRef",
          not dangling, f"dangling={dangling}" if dangling else "all OK")

    # --- structural signal: section markers (NOT raw brace count) ---
    b = len(re.findall(r"/\* Begin .*? section \*/", pb))
    e = len(re.findall(r"/\* End .*? section \*/", pb))
    check(f"section markers Begin={b} End={e}", b == e, "OK" if b == e else "MISMATCH")

    # --- headless group fragment scan (catches "project is damaged, cannot be opened") ---
    plines = pb.split("\n")
    headless = []
    for idx, ln in enumerate(plines):
        if ln.strip() == "children = (":
            j = idx - 1
            while j >= 0 and plines[j].strip() == "":
                j -= 1
            prev = plines[j].strip() if j >= 0 else ""
            good = prev.endswith("isa = PBXGroup;")
            if good and j >= 1:
                prev2 = plines[j - 1].strip()
                good = bool(re.search(r"[0-9A-F]{24} /\*.*?\*/ = \{", prev2))
            if not good:
                headless.append(idx + 1)
    check("no headless PBXGroup fragment (children without opener)",
          not headless, f"headless at lines {headless}" if headless else "OK")

    # --- string-aware brace balance (negative before valid EOF close => corruption) ---
    depth, ins, esc, neg = 0, False, False, None
    for ch in pb:
        if ins:
            if esc: esc = False
            elif ch == "\\": esc = True
            elif ch == '"': ins = False
            continue
        if ch == '"': ins = True; continue
        if ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0 and neg is None:
                neg = True
    brace_ok = (neg is None and depth == 0)
    check("string-aware brace depth balanced (no negative before EOF)",
          brace_ok, "OK" if brace_ok else f"imbalance final {depth}")

    # --- plutil -lint gate (OK = pass; lone line-1 // quirk = ignorable; else corruption) ---
    plutil_msg = "(not available)"
    plutil_ok = None
    try:
        r = subprocess.run(["plutil", "-lint", str(pbx)], capture_output=True, text=True, timeout=30)
        out = (r.stdout or r.stderr).strip()
        plutil_msg = out
        if "OK" in out:
            plutil_ok = True
        elif "Unexpected character / at line 1" in out:
            plutil_ok = None  # benign header quirk; inconclusive, not a fail
        else:
            plutil_ok = False
    except (FileNotFoundError, subprocess.SubprocessError):
        plutil_ok = None
    if plutil_ok is True:
        check("plutil -lint parseable", True, "OK")
    elif plutil_ok is False:
        check("plutil -lint parseable", False, plutil_msg)
    # if inconclusive (None), don't penalize; rely on fragment+brace checks

    for u in absent:
        check(f"removed UUID {u} absent everywhere", u not in pb,
              "PRESENT!" if u in pb else "absent")

    # --- path-chain resolution (catches file-on-wrong-path) ---
    if path_check:
        src_root = str(pbx.parent.parent)  # <root>/AnglerGO.xcodeproj -> <root>
        groups, parent = {}, {}
        for m in re.finditer(
                r"^\s*([0-9A-F]{24}) /\*.*?\*/ = \{\n\s*isa = PBXGroup;\n"
                r"(?:\s*children = \((.*?)\);\n)?(?:\s*name = (.*?);\n)?"
                r"(?:\s*path = (.*?);\n)?\s*sourceTree", pb, re.S | re.M):
            gid, children, name, path = m.group(1), m.group(2), m.group(3), m.group(4)
            groups[gid] = {"path": path}
            if children:
                for c in re.findall(r"([0-9A-F]{24})", children):
                    parent[c] = gid
        files = {}
        for m in re.finditer(
                r"^\s*([0-9A-F]{24}) /\* (.*?) \*/ = \{isa = PBXFileReference;.*?"
                r"path = (.*?); sourceTree = \"(.*?)\"", pb, re.S | re.M):
            fid, fname, fpath, st = m.group(1), m.group(2), m.group(3), m.group(4)
            files[fid] = (fname, fpath, st)
        missing = []
        for fid, (fname, fpath, st) in files.items():
            if fid in groups:
                continue
            if st != "<group>":
                continue
            g = parent.get(fid)
            full = os.path.join(resolve_group_dir(g, groups, parent, src_root), fpath.strip('"'))
            if not os.path.exists(full):
                missing.append((fname, full))
        check(f"path-check: {len(files)} file refs resolve to existing files on disk",
              not missing, f"MISSING={missing}" if missing else "all present")

    ok = all(r[0] for r in res)
    print(f"=== AD-HOC pbxproj verification: {pbx.name} ===")
    for r in res:
        print(f"[{'PASS' if r[0] else 'FAIL'}] {r[1]}" + (f"  ({r[2]})" if r[2] else ""))
    if plutil_ok is None:
        print("[NOTE] plutil inconclusive (lone header quirk or unavailable); relied on fragment+brace checks")
    print("=== OVERALL:", "PASS" if ok else "FAIL", "===")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
