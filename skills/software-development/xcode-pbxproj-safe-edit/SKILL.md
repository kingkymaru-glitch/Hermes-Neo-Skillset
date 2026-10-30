---
name: xcode-pbxproj-safe-edit
description: Safely edit an Xcode .pbxproj project file from a non-macOS/iOS-build CLI. Use whenever you must add, move, rename, or remove a Swift file's wiring in a .xcodeproj/project.pbxproj (e.g. registering a new screen/manager file so Cmd+B stays green). Covers the corruption failure mode, detection, and a safe edit+verify workflow.
---

# Safely editing Xcode .pbxproj from a CLI

This macOS CLI cannot compile iOS/SwiftUI (no UIKit/SwiftUI/iOS SDK). The deliverable for
iOS tasks is build-green, commit-ready code — INCLUDING correct Xcode pbxproj registration
for every new .swift file — but verification here is ad-hoc static only.

## NEVER hand-edit pbxproj with fragile string writes
The single biggest way to brick the project: editing project.pbxproj with a `sed`/Python
string-replace or line-insertion that reorders or duplicates text. This reliably produces an
**orphaned / headless group fragment**: a `children = ( ... ); path = X; sourceTree = "<group>"; };`
block left over with NO opening `UUID /* name */ = { isa = PBXGroup;`. Xcode then refuses to
open the project: "The project is damaged and cannot be opened due to a parse error."

A plain brace counter will NOT catch this — the dangling `}` still balances against the
project's final close brace, so depth ends at 0. The corruption is structural, not bracket-level.

## If a user reports "project is damaged / cannot be opened"
1. Don't guess. Find the parse error:
   - `plutil -lint AnglerGO.xcodeproj/project.pbxproj` — `OK` means parseable.
     (plutil normally warns "Unexpected character / at line 1" about the `// !$*UTF8*$!`
     header even on HEALTHY files — ignore that; it is not corruption.)
   - Check for leftover conflict markers: `grep -n '<<<<<<<\|=======\|>>>>>>>' project.pbxproj`
   - Scan for headless fragments (the real tell). IMPORTANT: a normal PBXGroup has
     `isa = PBXGroup;` on the line before `children = (`, which does NOT end in `{`, so a
     naive "prev line must end in {" check will flag EVERY ordinary group as "headless" — that
     is a FALSE POSITIVE. The correct signal is: `children = (` whose immediately-preceding
     NON-BLANK line is NOT `... = { isa = PBXGroup;` (i.e. no group open at all). Use:
     ```python
     lines = open(path).read().split("\n")
     for i,l in enumerate(lines):
         if l.strip() == "children = (":
             j=i-1
             while j>=0 and lines[j].strip()=="": j-=1
             prev = lines[j].strip() if j>=0 else ""
             # legit group open looks like:  NAME /* x */ = {   (and next-ish has isa = PBXGroup)
             if not (prev.rstrip().endswith("{") or "isa = PBXGroup" in (lines[j] if j>=0 else "")):
                 # only suspicious if the prev group-open is missing entirely
                 print("SUSPECT headless children at line", i+1, "prev:", prev)
     ```
     In practice, the authoritative corruption signal is `plutil -lint` -> NOT OK. Trust that
     over the headless heuristic; use the heuristic only to LOCATE the orphan once plutil fails.
   - Confirm the real group still exists before deleting anything: `grep -n 'UUIDHERE' project.pbxproj`
2. Fix by DELETING only the orphan block (exact-line removal via Python indexing, never regex
   on braces). Do NOT try to "re-add" the opening — the real group is elsewhere; the fragment is
   a duplicate.
3. Re-verify: plutil OK + brace depth 0 + headless scan clean.

## Safe workflow for adding a new .swift file's wiring
To register a new file (e.g. ThemeManager.swift) you need 4 consistent wires, all using the
SAME invented UUID prefix (e.g. `F3B0TEM...` for the file, `F3B0THEME...` for its group):
  - `PBXBuildFile` section:  `XX...B1 /* Name.swift in Sources */ = {isa = PBXBuildFile; fileRef = XX...0A /* Name.swift */; };`
  - `PBXFileReference` section: `XX...0A /* Name.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = Name.swift; sourceTree = "<group>"; };`
  - group `children` entry: `XX...0A /* Name.swift */,`  (inside the correct parent group)
  - `PBXSourcesBuildPhase` (or `Sources`): `XX...B1 /* Name.swift in Sources */,`
  - Parent group must exist with a matching `path =` that resolves to the on-disk location.

Preferred, safe edit methods (pick one, never raw sed):
  - **Best:** do the edit in Xcode via a heredoc that writes the WHOLE file atomically after
    building it in Python with explicit section inserts at known line numbers, then plutil -lint.
  - Use `patch` tool (fuzzy match) for small targeted insertions rather than line-indexed writes.
  - After ANY pbxproj change, run the verify block (plutil + brace scan + wiring grep + on-disk
    path check) and report it as ad-hoc static verification, NOT a green build.

## Verification checklist (ad-hoc, script cleaned up after running)
Put the script under `$TMPDIR` with a `hermes-verify-` prefix, run, then `rm` it.
  - plutil -lint => OK
  - string-aware brace scan => depth 0
  - headless `children = (` scan => none
  - all 4 UUID wires present (grep each)
  - file physically on disk at the resolved group path
  - section markers: `/* Begin ... section */` count == `/* End ... section */` count
Always state: "static check only; Xcode Cmd+B is authoritative."

## Support files in this skill
- `references/firebase-package-products.md` — verified firebase-ios-sdk product list + the
  `FirebaseFirestoreSwift` removal gotcha (≥v11). Consult before touching any Firebase import.
- `scripts/verify_pbxproj.py` — re-runnable static verifier: plutil lint, string-aware brace
  scan, headless `children = (` scan (false-positive-safe), section Begin/End balance, and an
  optional `expect_missing` arg to assert a product/string is gone. Run it instead of
  hand-typing the checks each time.

## Adding / removing a Swift PACKAGE PRODUCT (not a file)
Registering a Swift package *product* (e.g. a framework from firebase-ios-sdk) is a
DIFFERENT operation from wiring a `.swift` file. It touches 4 sites, all pointing at the
`XCRemoteSwiftPackageReference` for the package (NOT a file on disk):
  - `PBXBuildFile` section: `XX...P1 /* ProductName in Frameworks */ = {isa = PBXBuildFile; productRef = XX...P2 /* ProductName */; };`
  - `PBXFrameworksBuildPhase` `files = ( ... )`: `XX...P1 /* ProductName in Frameworks */,`
  - `XCSwiftPackageProductDependency` section: `XX...P2 /* ProductName */ = {isa = XCSwiftPackageProductDependency; package = <pkg-ref-UUID> /* ... */; productName = ProductName; };`
  - Native target `packageProductDependencies = ( ... )`: `XX...P2 /* ProductName */,`
Remove all 4 when deleting a product.

### CRITICAL: verify the product ACTUALLY EXISTS before registering it
A package product you "know" exists may have been REMOVED in the version the project is
pinned to. If it doesn't exist, Xcode reports `missing package product 'X'` no matter how
perfectly you wire the pbxproj — because Xcode resolves products from the package's
`Package.swift`, not from your pbxproj.
  - Read the pinned revision from `AnglerGO.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved` (look for the `identity`/`revision`/`version` of the package).
  - Fetch the manifest at that exact revision and grep for the product name:
    `curl -fsSL "https://raw.githubusercontent.com/<org>/<repo>/<revision>/Package.swift" -o /tmp/pkg.swift`
    `grep -n 'name: "ProductName"' /tmp/pkg.swift`
  - If the product is absent from `Package.swift`, DO NOT register it. Instead fix the code:
    change the `import ProductName` to the module that now exposes the API (see Firebase case below).

### Firebase-specific gotcha (cost this project a wasted cycle)
- firebase-ios-sdk **removed the `FirebaseFirestoreSwift` product around v11**. Its
  `Codable` helpers `DocumentSnapshot.data(as:)` and `Query.setData(from:)` were folded into
  the main **`FirebaseFirestore`** module. In Firebase ≥11: `import FirebaseFirestore`
  (NOT `FirebaseFirestoreSwift`), and link only `FirebaseAuth` / `FirebaseFirestore` /
  `FirebaseStorage`. Registering `FirebaseFirestoreSwift` as a product is impossible and
  will keep failing with `missing package product 'FirebaseFirestoreSwift'`.
- See `references/firebase-package-products.md` for the verified product list at 12.15.0.

## Pitfalls
- Removing a dependency/group block by line-substring (`[l for l in lines if "ProductName" not in l]`)
  ORPHANS its braces: the line containing `= {` (the opener) and the `productName` line both
  contain the substring, so they're deleted, but the trailing `};` closer is left behind →
  plutil FAILS and brace depth goes negative. Either (a) remove the WHOLE block as one
  multi-line substring (opener + body + closer) so it matches exactly once, or (b) after any
  line-drop, re-run the brace scan and delete the dangling `};`. Always assert the removal
  substring matches exactly once before writing.
- Off-by-one in grep patterns (extra/missing hex digit in a UUID) gives false "MISSING" —
  confirm with a direct `grep -n` of the exact string before declaring something gone.
- plutil "Unexpected character / at line 1" is a HEADER quirk, not corruption.
- This CLI has no git backup of the user's working tree in many cases — editing the pbxproj is high-risk; verify before returning it.
- **"Cannot find 'XService' in scope" (N identical errors) = MISSING pbxproj registration, not corruption.** A Swift file created via CLI `write_file`/`execute_code` is NOT auto-registered; it needs the 4 wires (see above). Symptom: N copies of the same error (one per file referencing it), exactly one file absent from pbxproj. Fix = add the 4 wires; verify with `grep -c "XService" project.pbxproj` >=4. (Inverse of the corruption failure mode.)
- **"PIF transfer session (operation in progress?)" = wedged build service, not code.** Xcode hasn't re-read the .xcodeproj (your pbxproj edits are invisible to it). Fix: Cmd+. stop -> Cmd+Shift+K clean -> if still stuck, fully quit Xcode (Cmd+Q) + reopen the .xcodeproj to force a fresh PIF transfer. Clear this BEFORE re-evaluating other errors.
- **Wrong SPM dialog: "package collection URL" error.** Pasting a GitHub repo URL into **Add Package Collection** (JSON-index feeds) fails. Use **File -> Add Package Dependencies...** for a repo URL. See `references/xcode-build-failure-triage.md`.
  high-risk; verify before returning it.
