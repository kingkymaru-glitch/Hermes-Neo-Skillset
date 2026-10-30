---
name: xcode-pbxproj-verification
description: Statically verify and edit Xcode .pbxproj project files when Xcode/xcodebuild cannot run (CI, Linux, mac-less host). Covers integrity checks, safely removing a file from a target, and the UUID-layer gotchas that bite hand-edits.
triggers:
  - editing or removing entries from an Xcode pbxproj
  - removing or unlinking a Swift Package (SPM) dependency from a target
  - build GREEN needed but no Xcode on the host
  - verifying a file was correctly added or removed from an Xcode target
  - static sanity check of an Xcode project after a text edit
---

# xcode-pbxproj-verification

Use this when you must touch an Xcode project's `project.pbxproj` (add or remove a source file, fix a target) but cannot run `xcodebuild` to confirm. It gives you a static-integrity check strong enough to catch the usual breakage, plus the exact set of places a removal must hit.

## When to use
- Host has no Xcode or xcodebuild (Linux CI, mac-less agent host). You can only read or text-edit the pbxproj.
- You removed a Swift file from a target and must prove the project is still structurally sound.
- The harness demands verification evidence but there is no canonical build command.

## pbxproj anatomy (3 UUID layers)
A source file appears in THREE independent places, each keyed by a 24-hex UUID:
1. PBXBuildFile — the compile entry: `UUID /* Foo.swift in Sources */ = {isa = PBXBuildFile; fileRef = REFUUID /* Foo.swift */; };`. Lives in the Compile Sources build phase. Its UUID differs from the fileRef UUID.
2. PBXFileReference — `REFUUID /* Foo.swift */ = {isa = PBXFileReference; ... path = Foo.swift; ...};`. The actual file on disk.
3. PBXGroup — navigator folder: `GRPUUID /* SomeGroup */ = {isa = PBXGroup; children = ( REFUUID /* Foo.swift */, ... ); path = ...; };`.

To remove a file cleanly delete its line in all of: the Compile Sources phase (PBXBuildFile), the PBXFileReference section, the PBXGroup children list (and the group itself if it becomes empty), and any stray comment string.

## How to verify statically
Run the bundled checker: `scripts/verify_pbxproj.py <path/to/project.pbxproj> [--absent UUID ...] [--path-check]`. (Re-runnable, dependency-free script shipped as `scripts/verify_pbxproj.py` in this skill — copy it next to the pbxproj and run with Python 3.)
It checks (no Xcode required):
- Every `/* x in Sources */` UUID has a matching PBXBuildFile whose fileRef resolves to a real PBXFileReference (catches dangling compile entries).
- Structural integrity via **section markers** (`/* Begin/End ... section */`) — N vs N must match. NOTE: do NOT use a raw `{`==`}` count as the balance signal; pbxproj build-settings carry literal `}` inside quoted strings (CLANG_*, INFOPLIST_*), so `{` and `}` will almost never be equal. Section markers are the correct signal.
- Optional `--absent UUIDs` are gone from the whole file (assert a removed file left no trace in any layer).
- `--path-check`: resolves every `PBXFileReference` with `sourceTree = "<group>"` through its PBXGroup path-chain and asserts the file EXISTS on disk. THIS is the check that catches the "Build input file cannot be found" bug — the file is present but sits at the WRONG folder relative to where the group says it should be (e.g. registered under `Features/Theme` but physically at `Core/Theme`). Run it whenever you move a file on disk or rewire its group.

## How to ADD a file to a target (the 4 edits, mirror of removal)
**RULE — register in the SAME turn you create the file.** When you add a NEW `.swift` via
`write_file` (or any file-write tool), the file lands on disk but is NOT added to the Xcode
target — the writer never touches `.pbxproj`. If you hand the user a build with the new file
unregistered, Cmd+B fails with a STORM of identical `Cannot find 'X' in scope` errors — one at
EVERY call site (this session: 19 identical errors for `SupabaseService`, vs 1 isolated real
error elsewhere). So: in the same turn as the `write_file`, perform all 4 pbxproj insertions
below. If the build later shows that "Cannot find X" pattern (many identical, one per file),
first `search_files target=files pattern='<X>.swift'` to confirm the file EXISTS, then grep
pbxproj for `X` — 0 hits in the 4 sections = unregistered; do the 4 edits.
The skill above documents REMOVAL. Adding a source file needs the inverse — and a
missing registration means it quietly fails to compile on the user's Mac. Mirror an
existing file (e.g. `AppState.swift`) and apply 4 insertions with ONE new 24-hex
UUID set (fileRef `..B1`, buildFile `..C1`):
1. Insert a **PBXBuildFile** in the Compile Sources phase:
   `AA..00C1 /* NewFile.swift in Sources */ = {isa = PBXBuildFile; fileRef = AA..00B1 /* NewFile.swift */; };`
2. Insert a **PBXFileReference**:
   `AA..00B1 /* NewFile.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = NewFile.swift; sourceTree = "<group>"; };`
3. Insert `AA..00B1 /* NewFile.swift */,` into the relevant **PBXGroup** children list.
4. Insert `AA..00C1 /* NewFile.swift in Sources */,` into the Compile Sources **build phase list**.
The non-negotiable correctness check: the buildFile's `fileRef =` UUID MUST equal
the PBXFileReference UUID (the `..B1` appears in both). Run `scripts/verify_pbxproj.py`
afterwards — every `/* NewFile.swift in Sources */` must resolve to a real FileReference.
INDENT CHECK (after each fuzzy patch): every inserted line must carry the SAME leading-tab
count as its sibling. Verify with `awk -F'\t' '{print NF-1}'` on both line numbers; if they
differ, the patch tool over-indented the new line — re-patch it down to match. (See Pitfalls:
stray-tab over-indentation.)
(For the Swift-source side of this — what `swiftc -parse` + ad-hoc checks to run — use the
sibling skill `ios-cli-verification`, which also documents the same-turn registration rule and
the "Cannot find X" storm diagnostic.)

## How to remove a file from a target (the 4 edits)
1. Delete the `PBXBuildFile ... in Sources` line in the Compile Sources build phase.
2. Delete the `PBXFileReference` line.
3. Delete the UUID from its `PBXGroup` children list; delete the group too if it ends up empty.
4. Optionally delete the now-unused `.swift` file on disk.

After edits, run the script. PASS means the project is structurally sound — but that is NOT a compile. The only true "build GREEN" comes from Xcode on a Mac.

## How to remove an SPM PACKAGE dependency (6 places, not 3)
Removing a *package* (e.g. GoogleSignIn-iOS) is a different shape from removing a *source file* (which hits PBXBuildFile/PBXFileReference/PBXGroup). A package leaves references in SIX places, keyed by its product UUID(s):

1. **PBXBuildFile** — `UUID /* GoogleSignIn in Frameworks */ = {isa = PBXBuildFile; fileRef = REFUUID /* GoogleSignIn */; };` (one per exported product: GoogleSignIn, GoogleSignInSwift).
2. **PBXFrameworksBuildPhase** `files = (` — the `UUID /* GoogleSignIn in Frameworks */,` entries.
3. **XCSwiftPackageProductDependency** section — `UUID /* GoogleSignIn */ = {isa = XCSwiftPackageProductDependency; package = PKGUUID /* XCRemoteSwiftPackageReference "GoogleSignIn-iOS" */; productName = GoogleSignIn; };` (one block per product).
4. **PBXNativeTarget.packageProductDependencies = (** — remove the product UUIDs listed there.
5. **XCRemoteSwiftPackageReference** section — the `PKGUUID /* XCRemoteSwiftPackageReference "GoogleSignIn-iOS" */ = { … };` block.
6. **PBXProject.packageReferences = (** — remove that PKGUUID from the list.

The `PKGUUID` (layers 5/6) is the parent; each product UUID (layers 1–4) points at it via `package =`. Remove all six or Xcode reports a dangling reference / "cannot resolve package".
**Technique:** anchor every removal on the FULL `UUID /* comment */` token (24-hex + comment), not a bare substring. Use the fuzzy `patch` tool with the complete line as old_string, or a Python `str.replace` on the exact line. NEVER `re.sub` on a bare substring — see Pitfalls (broad-removal corruption).
**Also clean `Package.resolved`** (see Pitfalls) and **assert** with `grep -q GoogleSignIn project.pbxproj` → must be empty, plus section-marker balance.
Worked example (exact UUIDs + diff): `references/spm-package-removal.md`.

- Regex anchor bug: pbxproj lines start with TAB indentation. Anchoring the PBXBuildFile regex with `^` (no `\s*`) matches NOTHING, so every source reports "no PBXBuildFile" — a false FAIL. Always use `^\s*([0-9A-F]{24})`.
- UUID-layer conflation: the Compile-Sources entry UUID is NOT the PBXFileReference UUID. A naive check that greps `/* Foo.swift in Sources */` and expects that same UUID as a PBXFileReference false-positives. Follow the chain: Sources UUID -> PBXBuildFile.fileRef -> PBXFileReference UUID.
- Brace/paren balance is a cheap global sanity check; an unclosed brace usually means a botched multi-line delete. BUT the raw `{`==`}` count is a RED HERRING on pbxproj — literal `}` appears inside quoted build-setting strings (e.g. CLANG_ENABLE_OBJC_ARC = YES; followed by `};`). Trust the **section-marker count** (`/* Begin/End ... section */` = N vs N) as the real structural signal instead.
- **File-at-wrong-path = "Build input file cannot be found".** The pbxproj can be 100% structurally valid (all 3 UUID layers wired) yet Xcode still fails because the on-disk file is NOT where the group chain says. A `PBXFileReference` under `path = ThemeManager.swift` inside a `PBXGroup` with `path = Theme` nested under a `Features` group resolves to `<root>/Features/Theme/ThemeManager.swift`. If you `mv` the file elsewhere or register it under the wrong group, Xcode reports the missing input, NOT a pbxproj error. FIX: before declaring done, run `verify_pbxproj.py ... --path-check` to confirm every `<group>`-sourceTree file reference resolves to an existing file. This is the single most common real bug; structure-only checks miss it.
- **plutil: read it correctly, not as a blanket oracle.** `plutil -lint project.pbxproj` prints "Unexpected character / at line 1" for the benign `// !$*UTF8*$!` header on MANY healthy files — ignore THAT specific quirk. BUT when plutil prints **OK**, the file genuinely parses as a plist (strong positive). And when the file is truly corrupted, plutil usually prints a DIFFERENT error (or the line-1 quirk PLUS the bundled headless-fragment scan catches the real damage). Net rule: `OK` = pass; the lone line-1 `/` quirk = ignorable; ANY OTHER plutil error = real corruption. Do NOT rely on plutil alone to FIND corruption — pair it with the headless-fragment scan below.
- **HEADLESS GROUP FRAGMENT = "project is damaged, cannot be opened".** A multi-line insert that leaves a `children = ( ... );` block (or a `};` closer) with NO matching `UUID /* name */ = { isa = PBXGroup;` opener makes Xcode refuse to even OPEN the project ("damaged and cannot be opened due to a parse error") — worse than a build failure. Cause observed this session: a Python `str.replace` whose anchor text accidentally included the SIBLING group's `= { isa = PBXGroup;` opening AND whose replacement text re-emitted it, duplicating the block and orphaning one headless copy. DETECT: the bundled script now scans every `children = (` and flags any whose nearest preceding non-blank is NOT a `isa = PBXGroup;` sitting directly under a `UUID /* x */ = {` opener (e.g. it hit a `};` or a blank first). A string-aware brace scan that goes negative before the valid EOF close is the same tell. PREVENT: when inserting a group via Python, anchor on the UNIQUE sibling UUID line and have the replacement emit ONLY the new block — never re-include the sibling's `= {` opener. After ANY group insert, run the script (it FAILS on headless fragments) and confirm `plutil -lint` -> `OK`.
- **Fuzzy patch tool FAILS on multi-line PBXGroup-block inserts.** Single-line fuzzy patches sometimes work, but inserting a whole group block (e.g. a `/* Theme */ = {isa = PBXGroup; children = (...); path = Theme; sourceTree = "<group>"; };`) reliably trips the matcher into "Found N matches" (observed 2/4/6) because every `/* Foo */ = {` block looks alike. You will burn many attempts. FIX: drop straight to a small Python `str.replace(old, new)` on the exact anchor line (the unique, distinctive one — e.g. the sibling group's UUID + ` /* Calendar */ = {`). Use a `tempfile`-based script under `/private/var/folders/.../T` with a `hermes-verify-` prefix, run it, then delete it.
- Do not grep your way to confidence. Static check proves structure, not semantics.
- Fuzzy patch tool on pbxproj: its matcher sometimes reports "2 matches" for a single real occurrence because neighbor lines repeat elsewhere. If a targeted patch fails, fall back to a small Python `str.replace` on the exact line.
- **Stray-tab over-indentation from the patch tool.** When you ADD a sibling line to a pbxproj list by giving the fuzzy patcher a single-line `old_string` (the sibling) and a `new_string` of `sibling` + newline + new line, the tool frequently emits the new line with EXTRA leading tabs vs its sibling (observed: 6–7 tabs instead of 3–4). Xcode tolerates this, but it is dirty and trips any indent-based static check. FIX: after the patch, audit every line you touched with `sed -n '<N>p' file | awk -F'\t' '{print NF-1}'` and confirm its tab count EQUALS its immediate sibling's; re-patch the offending line down to the correct indent. NOTE: a few deep-nested sections are LEGITIMATELY 6 tabs (e.g. `CreatedOnToolsVersion` under `TargetAttributes`), so scope your over-indent check to the lines YOU inserted — never `grep` the whole file for `>=6 tabs` or you'll false-FAIL on pre-existing settings.
- **Removing an SPM PACKAGE is a different shape than removing a source file (6 places, see above).** The bundled `verify_pbxproj.py` checks source-file UUID chains; it does NOT assert a removed *package* left no trace. So for package removal you MUST additionally `grep -q <PackageName> project.pbxproj` (expect empty) and confirm `Package.resolved` no longer pins it. A clean source-structure run can still hide a dangling `XCRemoteSwiftPackageReference` / `packageProductDependencies` entry that Xcode will reject on open.
- **BROAD removal scripts EAT neighboring entries — protect supabase/firebase.** A Python `str.replace`/`re.sub` that strips every line containing a substring (e.g. "GoogleSignIn") is DANGEROUS: the matcher can also delete a line whose comment merely *mentions* the substring near a wanted package, and a brace-counting loop can desync and delete the WRONG `};`. This session: a script that removed "GoogleSignIn" also dropped the `supabase-swift` `XCRemoteSwiftPackageReference` block and broke brace balance (130→unbalanced), requiring `git checkout -- project.pbxproj` to recover. FIX: remove by EXACT unique line (anchor on the full `UUID /* comment */` token, never a bare substring), one entry at a time, OR use the fuzzy `patch` tool with the complete 24-hex UUID + comment as the old_string. After each edit, `grep -c` the package name and assert it dropped by exactly the expected count; `git diff` after every step so a botch is one `git checkout` away.
- **git baseline = safety net for pbxproj edits.** Before ANY programmatic rewrite of pbxproj, the committed version is your rollback: `git checkout -- AnglerGo.xcodeproj/project.pbxproj` restores the last good state instantly. This session used it twice after script corruption. Make it muscle memory: edit → `git diff` → if corrupt, `git checkout -- <path>` → re-apply surgically. Do NOT try to hand-fix a brace-desynced pbxproj; restore and redo.
- **Package.resolved must also be cleaned.** Removing a package from pbxproj does NOT auto-prune `project.xcworkspace/xcshareddata/swiftpm/Package.resolved`; Xcode 26 regenerates it on next open, but a stale pin (e.g. `"GoogleSignIn-iOS"`) can linger. After pbxproj edits, `grep -q '"GoogleSignIn-iOS"' Package.resolved` must be empty. Note: residual transitive Google deps (abseil, gtm-session-fetcher, etc.) are HARMLESS leftovers from firebase-ios-sdk — they are not imported, and Xcode prunes them on resolve; don't chase them.
- **Brace-delta vs git is a valid corroborating signal for package removal.** The general rule "don't trust raw `{`==`}`" holds for whole-file sanity, BUT when you remove a known set of balanced blocks you can baseline: `git show HEAD:<pbx>` has N open/close; after a correct removal the count drops by exactly 2× the balanced blocks you deleted (each `{...};` block = +1 open/+1 close). This session: committed 130/130 → after removing 3 balanced blocks + 2 non-brace list lines, 124/124 (delta 6 = 3 blocks). If the delta is wrong OR `grep` still finds the package name, the edit was botched. Use it to corroborate, never as the sole gate — section markers + package-name grep remain authoritative.

## Operational notes (from real runs)
- Prefer the bundled `scripts/verify_pbxproj.py` over hand-rewriting the checker inline. It already encodes the `^\s*` anchor + UUID-chain logic — the anchor bug in `## Pitfalls` was originally introduced by an inline re-implementation. Copy the bundled script next to the pbxproj and run it; do not re-derive the regex.
- Harness re-prompts: on a mac-less CLI host the system nudges for "fresh passing verification evidence" after an edit. Re-running this static checker (cheap, ~instant) is acceptable AD-HOC evidence — but label it explicitly as static, never as a compiled build.
- Full removal proof: invoke with `--absent` for ALL THREE UUIDs of the removed file — the BuildFile UUID, the FileReference UUID, and the Group UUID. All three absent + every Compile-Sources entry resolving + balanced delimiters = clean removal. Verifying only one layer leaves a false PASS.
- **Path-mismatch proof (the common real bug):** after any on-disk `mv` or group rewire, run `verify_pbxproj.py <pbx> --path-check`. PASS means every `<group>`-sourceTree file reference resolves to a file that EXISTS on disk — this is what actually prevents the "Build input file cannot be found" error. A structure-only run (no `--path-check`) can still PASS while the user's build fails.
- Build-phase patch collisions: when the fuzzy patch tool reports "2 matches" for a single real line, do NOT loop fuzzy retries — drop to a small Python `str.replace` on the exact line text (see Pitfalls).
- Plutil / brace-count: read them right. `plutil -lint` false-fails ONLY on the benign `// !$*UTF8*$!` header quirk; when it prints `OK` that is a strong positive that the file parses, and any OTHER plutil error is real corruption. The bundled script now gates on `plutil -lint` (OK => pass; lone header quirk => ignored; other error => FAIL) AND runs a string-aware brace scan. A raw `{`==`}` count is still skewed by `}` inside quoted build settings, so never use it alone — but the corrected string-aware scan is now a real signal. Pair plutil + fragment scan + section markers; rely on section-marker balance + `--path-check` for the file-on-wrong-path bug specifically.

## Limitations (state these honestly)
This is AD-HOC static verification, not a compiled build. `--path-check` closes the biggest real-world gap (file-at-wrong-path "cannot be found" errors) but still only proves the reference and the on-disk location agree — it cannot prove the Swift compiles. Always tell the user real verification requires Xcode or xcodebuild on a Mac, label output as static, and list any pre-existing warnings separately.
