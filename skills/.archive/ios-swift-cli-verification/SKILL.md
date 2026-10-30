---
name: ios-swift-cli-verification
description: >-
  Verify SwiftUI/iOS builds from the CLI WITHOUT Xcode. Covers the critical
  gap that `swiftc -parse` checks SYNTAX ONLY (not imports, modules, or SDK
  API resolution), the Xcode stale DerivedData / editor-buffer trap that
  mis-attributes errors, and the import-coverage sweep + live backend
  reachability probe that actually catch what Cmd+B would. Trigger on:
  "verify this Swift", "swiftc parse", "build failed Xcode", "missing import
  of defining module", "cannot find type/module", any SwiftUI/iOS compile
  error triage from the CLI, or when the user says "you should have caught
  that before I built it".
category: ios
---

# iOS Swift CLI Verification

You can't click Cmd+B in a GUI, but `xcrun xcodebuild` IS the CLI equivalent
and is the AUTHORITATIVE build gate — run it whenever Xcode command-line tools
are installed. In one session it returned `** BUILD SUCCEEDED **` (exit 0) with
**0 errors** where `swiftc -parse` had falsely claimed a clean file. Prefer a
real `xcodebuild` over `swiftc -parse` for the final verdict; use `swiftc -parse`
only as a fast syntax pre-pass.

> Environment note: if `xcrun xcodebuild -version` errors ("command line tools
> not found"), fall back to the parse + sweep sequence below — but treat any
> "green" as provisional, not authoritative.

## Core trap (this cost ~10 wasted build cycles in one session)
`swiftc -parse file.swift` checks grammar only. It does NOT:
- resolve `import` statements or modules,
- catch "missing import of defining module 'Auth'" / "cannot find type",
- catch SDK API mismatches (wrong member, wrong return type, e.g. supabase-swift v2),
- catch missing `import Combine` for `@Published` / `ObservableObject`.

A file that parses clean CAN still fail Cmd+B with 15 errors. Claiming
"parse green = build green" is wrong. Always label a parse pass as a
*syntax check*, never "build green".

## What actually catches build errors (do ALL of these proactively)
The user expects you to find errors BEFORE they build, not just parse and
wait. Run the checks below, then report which you ran and which error
class each can/can't catch.

1. **Import-coverage sweep (highest-value CLI check).** For every `.swift`
   that touches a type/member from an external module, confirm that file
   `import`s it. Recurring real case: a file uses
   `SupabaseService.shared.client.auth…` but only `import SwiftUI` → Xcode
   reports "Property auth is not available due to missing import of defining
   module 'Auth'". Inline sweep (run from repo root):
   ```bash
   python3 - <<'PY'
   import os, re
   root="."
   for dp,_,fn in os.walk(root):
       if "DerivedData" in dp or ".git" in dp: continue
       for f in fn:
           if not f.endswith(".swift"): continue
           s=open(os.path.join(dp,f)).read()
           if re.search(r"\.client\.(auth|storage|from|postgrest)|SupabaseClient|SupabaseService\.shared\.client|AuthResponse", s) \
              and "import Supabase" not in s:
               print("MISSING import Supabase:", os.path.relpath(os.path.join(dp,f),root))
   PY
   ```
   Generalize the marker set for Combine / FirebaseAuth / GoogleSignIn as
   needed. Zero output = clean.

2. **SDK-surface check when an API mismatch is suspected.**
   **PREFER THE INSTALLED PACKAGE over a GitHub fetch.** A raw GitHub
   fetch (`raw.githubusercontent.com/.../v2.53.0/...`) is often TRUNCATED
   or points at the wrong file path, so grepping it can miss the struct
   you need and lead you to invent a type name. The package Xcode already
   resolved lives in DerivedData — grep THAT:
   ```bash
   PKG=~/Library/Developer/Xcode/DerivedData/AnglerGo-*/SourcePackages/checkouts/supabase-swift
   grep -rn "struct AuthOptions" "$PKG/Sources"          # real type name?
   grep -rn "emitLocalSessionAsInitialSession" "$PKG/Sources" | grep -iE "var|let|init"
   ```
   Real case (2026-07-27): Xcode reported `Cannot find 'AuthOptions' in scope`
   at `SupabaseClientOptions(auth: AuthOptions(emitLocalSessionAsInitialSession: true))`.
   **The fix is NOT bare `AuthOptions` and NOT a guessed `AuthClientOptions`** — both fail.
   Grepping the INSTALLED checkout proves `AuthOptions` is a **NESTED** type:
   `public struct SupabaseClientOptions { … public struct AuthOptions … }`
   (Types.swift:11/49, with `extension SupabaseClientOptions.AuthOptions` at :209).
   Bare `AuthOptions` is NOT in scope (that IS the original error), and `AuthClientOptions`
   does not exist at all. The correct call is the **fully-qualified**
   `SupabaseClientOptions.AuthOptions(emitLocalSessionAsInitialSession: true)`.
   The greps that reveal nesting (run these — don't guess the name):
   ```bash
   PKG=~/Library/Developer/Xcode/DerivedData/AnglerGo-*/SourcePackages/checkouts/supabase-swift
   grep -rn "struct AuthOptions" "$PKG/Sources"                      # line + enclosing struct
   grep -rn "extension SupabaseClientOptions.AuthOptions" "$PKG/Sources"  # proves nesting
   ```
   **Rule — never rename an SDK type by intuition.** When "Cannot find 'X' in scope" fires for
   a package type, grep the REAL declaration in the DerivedData checkout and check its NESTING
   scope; use the fully-qualified name if it's nested. A guessed rename (`AuthClientOptions`)
   is a second wrong fix that still fails the build. Only fall back to a pinned GitHub raw
   fetch if the package isn't on disk (e.g. after `rm -rf DerivedData`). See supabase-backend
   `references/supabase-swift-v2-api.md` for the v2.53.0 facts (and note the nested
   `SupabaseClientOptions.AuthOptions` correction there).

3. **Live backend-reachability probe** for any hardcoded URL: `dig`/`curl`
   the host BEFORE trusting it. "hostname could not be found" at runtime =
   dead project (DNS gone), not a code bug. See supabase-backend P26.

## Xcode stale-buffer / DerivedData trap
Symptoms: same error persists across clean builds; error points at a call
site but the on-disk definition is correct; "Missing argument for parameter X"
attributed to the wrong file. Cause: Xcode accumulates multiple
`~/Library/Developer/Xcode/DerivedData/AnglerGo-*` folders; the stale index
resolves symbols from an old copy, so (e.g.) a `#Preview` missing a required
init arg gets mis-reported as a `saveShop` call-site error.

Recovery:
1. Quit Xcode fully (`osascript -e 'quit app "Xcode"'`; kill if needed).
2. `rm -rf ~/Library/Developer/Xcode/DerivedData/AnglerGo-*` (clears ALL
   stale caches for that target).
3. Reopen project; let indexing FINISH (spinner gone) before building.
4. Also have the user right-click the suspect file → Source Control →
   Discard Changes to reload the committed (correct) version into the
   editor buffer — Xcode's open tab can hold a stale copy even after a
   DerivedData wipe.

### CRITICAL caveat — cache is the LAST hypothesis, not the first
A persistent error that survives a clean build + `rm -rf DerivedData` +
a confirmed-correct on-disk file is a REAL bug, NOT stale cache. In one
session the "ShopOwnerLoginView: missing import of defining module 'Auth'"
error (10×) was wrongly blamed on stale DerivedData across ~6 build cycles;
the actual cause was a genuine missing `import Supabase` in that file
(`swiftc -parse` missed it because parse is syntax-only). Rule:
- If the on-disk file is correct AND the error persists after a full clean,
  the error's *attribution* (e.g. to a call-site or a different file) is
  often WRONG. Inspect the ACTUAL error line/location, not the issue
  navigator's grouping.
- Correlate the exact error text to the real symbol. Xcode grouped the
  `import Supabase` miss under `ShopOwnerLoginView` but the navigator
  pointed at a `saveShop` call-site — mis-attribution.
- The user explicitly expects pre-build detection. If you cannot run Cmd+B,
  run the import-coverage sweep + SDK-surface probe + backend reachability
  probe BEFORE handing back, and state which error classes each check covers.

## Verification sequence (use ALL; parse alone is insufficient)
1. `swiftc -parse <file>` — syntax only; call it "syntax check".
2. import-coverage sweep (above).
3. for SDK-API doubts: fetch pinned source, grep real signatures.
4. for runtime URL doubts: `curl`/`dig` the host.
5. tell the user the ONLY authoritative gate is their Cmd+B; state clearly
   which checks you ran and which error class each can/catch.

## Authoritative gate: run `xcodebuild` (when CLI tools exist)
`swiftc -parse` is syntax-only; `xcodebuild` is the real compiler and catches
import/module/SDK-API errors that parse misses. Invocation that worked
(AnglerGo, Xcode 26.6, iOS Simulator, no booted sim required):
```bash
cd <project-root>
rm -rf /tmp/build.log
xcrun xcodebuild build \
  -scheme <SchemeName> \
  -project <Project>.xcodeproj \
  -destination 'generic/platform=iOS Simulator' \
  -configuration Debug \
  CODE_SIGN_STYLE=Automatic ONLY_ACTIVE_ARCH=YES \
  > /tmp/build.log 2>&1
echo "exit=$?"; grep -E "BUILD SUCCEEDED|BUILD FAILED" /tmp/build.log
```
- Discover scheme/targets: `xcrun xcodebuild -list -json` (parse with python3).
- Read the log: `grep -cE "error:" /tmp/build.log` (0 = clean), and grep for the
  specific error text you were chasing to confirm it's gone.
- This is the gate the harness "unverified" flag ultimately wants. Run it for
  the final verdict; `swiftc -parse` alone is not enough.

### Ad-hoc verification script pattern (harness "unverified" flag)
When the harness flags an edit as unverified, write a `hermes-verify-*` script
under the OS temp dir, assert AGAINST THE REAL BUILD LOG + source, run it, then
delete it. Label results explicitly "AD-HOC VERIFY: PASS" (never "suite green").
Reusable skeleton in `scripts/verify_ios_build.sh`.

PITFALL — your own assertion regex can self-fail (false negative). In one
session the check `grep -E "\bAuthOptions\(" | grep -v "SupabaseClientOptions.AuthOptions"`
flagged the QUALIFIED name as "bare" because `\bAuthOptions\(` matches inside
`SupabaseClientOptions.AuthOptions(`. Fix: anchor the bare-name check so a
leading `.` excludes it:
`grep -nE '(^|[^.])\bAuthOptions\(' file | grep -v "SupabaseClientOptions.AuthOptions("`
Only a TRUE bare `AuthOptions(` (no preceding dot) survives. Always sanity-check
your assertion script on known-good input before trusting its verdict.

### Rollback pitfall — `git restore` can restore a broken HEAD
When asked to "roll back to when it worked," do NOT `git restore --source=HEAD
--staged --worktree -- .` blindly. A session reverted to a HEAD that ITSELF
contained the broken `AuthOptions` line; the "restored working" state still
failed to compile. Before reverting, confirm HEAD actually builds (or at least
note the known-broken line). After any restore, re-run `xcodebuild` (or the
parse+sweep) so you hand back a state you verified, not a state you assumed.

## Cross-links
- `scripts/verify_ios_build.sh`: runnable `xcodebuild` gate + ad-hoc asserts
  (build log + source sweep) for the harness "unverified" flag. Copy it to
  `/tmp/hermes-verify-*.sh`, fill args, run, delete. (Includes the qualified-name
  regex fix below so your assertion won't self-false-negative.)
- supabase-backend (`references/supabase-swift-v2-api.md`): supabase-swift
  v2 API surface + the "dead project = DNS gone" runtime diagnostic (P26).
- xcode-pbxproj-verification / xcode-pbxproj-safe-edit: for editing the
  .pbxproj to register new Swift files in the target (a missing registration
  shows as "cannot find type" at build).
