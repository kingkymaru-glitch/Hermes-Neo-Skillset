---
name: ios-swift-cli-bridge
description: Bridge between terminal-side Swift edits and Xcode builds for an EXISTING Xcode (SwiftUI/iOS) project when you cannot run Cmd+B. Covers CLI-only verification (swiftc -parse), the Xcode stale-editor-buffer / PIF-wedge / "Discard Changes reverts my fix" loop, and aligning code to SPM SDK API drift (e.g. supabase-swift v1->v2). Use when a Swift build fails and you must decide code-error vs Xcode-infra, or a package upgrade broke an API.
---

# ios-swift-cli-bridge

Bridge between terminal-side Swift edits and Xcode builds for an EXISTING Xcode
(SwiftUI/iOS) project, when you cannot run `Cmd+B` yourself. Covers the verification
you CAN do from the CLI, the stale-editor-buffer / PIF-wedge / "Discard Changes reverts
my fix" loop, and aligning code to SPM SDK API drift (e.g. supabase-swift v1 -> v2).

## When to use
- Editing `.swift` files in a committed Xcode project from the terminal.
- A build fails and you must decide whether it is a real code error or Xcode infra
  (PIF / derived-data) wedged.
- A package upgrade changed an API (e.g. supabase-swift) and the code no longer compiles.
- Xcode shows old code after restart, or reports "cannot find type/func" for a file that
  IS registered in the target.

## Neighbor skills
Overlaps with `swift-cli-ios-dev` and `ios-cli-verification` (both edit/verify Swift in an
existing Xcode project). Prefer THIS skill when the failure involves Xcode's build-service
STATE (stale buffers, PIF transfer, discard-reverts-fix) or SPM SDK API drift — those are
the gaps it fills. Curator handles consolidation.

## Hard limits (verify, don't assume)
- `swiftc -parse <file>` is the ONLY Swift check runnable from the CLI. It parses ONE file
  in isolation — it does NOT resolve cross-file symbols, SPM packages, or link. A file that
  parses clean can still fail `Cmd+B`.
- You CANNOT run `Cmd+B` / the Xcode build from the terminal. Xcode's SPM resolution + link
  is the sole validator. Never claim "build is green" from `swiftc -parse` alone — label it
  explicitly as ad-hoc parse verification.
- `.xcodeproj/project.pbxproj` is NOT Swift-parseable. Only Xcode's indexing validates SPM
  package membership / new-file registration.

## Workflow: edit -> verify -> survive Xcode
1. Edit the file (`write_file` / `patch`).
2. `swiftc -parse <file>` to confirm no syntax errors. Pair with a small python check
   (`mktemp -t hermes-verify-*`) confirming required symbols/methods are present and wrong
   URLs/tokens absent. Label output explicitly "ad-hoc — NOT Cmd+B".
3. **COMMIT the fix BEFORE telling the user to restart Xcode.** Why: Xcode's
   "Source Control -> Discard Changes…" reverts the file to the LAST COMMITTED version. If
   you only edited the working copy, discard throws away your fix and restores the broken
   committed version — recreating the exact error. Committing makes the next discard revert
   to your fixed HEAD. Confirm with `git cat-file -p HEAD:<path> | cmp - <path>` -> IDENTICAL.
4. Tell the user to: right-click the file -> Source Control -> Discard Changes (or close +
   reopen the tab) to force Xcode to reload the disk version (its editor buffer may hold
   stale code from before your edit), then Cmd+Shift+K -> Cmd+B.

## Pitfall: stale editor buffer / PIF wedge
- Symptom: `Build service could not create build operation: ... unable to initiate PIF
  transfer session` + a batch of "Cannot find X" for a file already registered in pbxproj.
  This is Xcode infra wedged, NOT your code. Fix: quit Xcode (Cmd+Q, fully), reopen, let
  indexing finish, clean + build. If it persists, `rm -rf ~/Library/Developer/Xcode/DerivedData`.
- Symptom: Xcode shows OLD code after restart even though disk has your edit. The editor
  buffer predates your last write. Discard Changes / reopen the tab to load from disk.
- A file you "deleted" via Select-All+Delete in Xcode's editor is only emptied in the
  working copy; the committed version is intact — `git show HEAD:<path>` recovers it.

## DO NOT misdiagnose "missing import of defining module" as a cache problem
`Property 'X' is not available due to missing import of defining module 'Y'` is a CODE bug
(a missing `import Y`), NOT Xcode infra. In one session this error recurred after a clean
build + DerivedData wipe and was wrongly blamed on a stale cache, wasting several round-trips —
the real cause was a missing `import Supabase` in a file touching `SupabaseService.shared.client.auth`.
`swiftc -parse` cannot catch this (it is syntax-only). Triage, in ORDER:
1. `git status <file>` — is it DIRTY? If the on-disk file lacks the import, that IS the bug.
2. Read the ACTUAL on-disk bytes at the failing line; grep its `import` lines.
3. Run the import-coverage sweep below. If it reports a missing import, FIX IT — do NOT touch DerivedData.
4. ONLY conclude "cache" if the import IS present, the on-disk code is provably correct, AND a
   clean rebuild (Cmd+Shift+K) after reopen still fails identically.

The user explicitly demanded "do a thorough check on the entire code, I know you can detect the
error before I test it on Xcode" — so when ⌘B reports an import/module error, run the sweep across
the WHOLE repo, not just the one file, before claiming anything.

### Mandatory import-coverage sweep (self-contained; run before claiming parse-green means anything)
```bash
python3 - <<'PY'
import os, re
root="<repo-root>"
swift=[os.path.join(d,fn) for d,_,fs in os.walk(root) if ".git" not in d and "DerivedData" not in d
        for fn in fs if fn.endswith(".swift")]
missing=[]
for p in swift:
    s=open(p).read()
    if re.search(r"\.client\.(auth|storage|from|postgrest)|SupabaseClient|SupabaseService\.shared\.client", s):
        if "import Supabase" not in s:
            missing.append(os.path.relpath(p, root))
print("MISSING import Supabase:" , missing or "NONE")
PY
```
Replace the regex/module for the SDK in play (e.g. Firebase, GoogleSignIn). Any hit = the real
⌘B error. Note: `swiftc -parse` is BLIND to all of this — it checks syntax only.

## Pitfall: SPM SDK API drift (supabase-swift example)
When a build fails with "no member 'X'" / "Cannot convert return expression of type Y",
fetch the ACTUAL installed package source — don't guess from memory or a pasted snippet.
- Read `Package.resolved` (`<proj>.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved`)
  to get the pinned version + revision.
- `web_extract` may be credit-blocked. Fallback:
  `curl -sL "https://raw.githubusercontent.com/<org>/<repo>/v<MAJOR.MINOR.PATCH>/Sources/<Module>/<File>.swift"`.
  NOTE: GitHub tags need the `v` prefix (`v2.53.0`, NOT `2.53.0`) or you get 404.
- Find the right source path with the tree API:
  `curl -sL "https://api.github.com/repos/<org>/<repo>/git/trees/v<ver>:<dir>"` (e.g. `:Sources/Auth`),
  or recursive `git/trees/v<ver>?recursive=1` (large repos truncate — query subdirs).
- Grep the fetched `.swift` for `public func <name>`, `public var <name>`, `enum <Name>` + `case`
  to get exact signatures. Patch your code to match THOSE, not a remembered v1 shape.

## Do NOT
- Do not paste a user-supplied "fix" verbatim without checking it against the real SDK AND the
  project's actual config. In one session a pasted "v2 fix" pointed at a Supabase project URL
  AND dropped 8 methods that 26 call sites depended on. Flag the conflict, then apply a correct
  fix. CRITICAL CORRECTION (learned the hard way): the project URL `merfmrlkjoqrhijzfwbn`
  (angler_go) is the LIVE one; the earlier `ooeowvbrexxoaleodfum` (FishGoneWild) is DEAD (DNS no
  longer resolves — expired like the Firebase project). A pasted/`Discard`-restored version that
  re-points at `ooeowvbrexxoaleodfum` will fail at runtime with "hostname could not be found".
  Verify the live host with `dscacheutil -q host -a name <ref>.supabase.co` before trusting any URL.
- Do not re-add `import Firebase`. AnglerGO migrated off Firebase (expired `fishgo-a98ae`);
  only `LoginView.signInWithGoogle()` (stubbed) + `AnglerGoApp` AppDelegate still reference
  Firebase/GoogleSignIn for OAuth (Task 1.7, held post-pitch). They compile (Firebase package
  still linked) but emit a harmless `OpenURLOptionsKey` iOS-26 deprecation warning.
- Do not assume `swiftc -parse` green means the build will pass. It is syntax-only — blind to
  missing imports, SDK-enum mismatches (e.g. `ResendEmailType.verifyEmail` doesn't exist in
  supabase-swift 2.53.0; use `.signup`), and wrong module members. Those surface only at ⌘B.

## Runtime gotchas (build is green but login/flow fails)
These are NOT compile errors — they surface only at run, so ⌘B won't catch them. Each cost a
full debugging round-trip:
- **"hostname could not be found" on `<ref>.supabase.co`** → the project URL is DEAD (DNS no
  longer resolves). Verify with `dscacheutil -q host -a name <ref>.supabase.co` before trusting
  any URL. For AnglerGO the live ref is `merfmrlkjoqrhijzfwbn`; `ooeowvbrexxoaleodfum` is dead.
- **Signup returns 429 `over_email_send_rate_limit`** → Supabase's email-send limit is
  **PROJECT-level per hour (~3-4)**, NOT per-address (a fresh unused email also 429s). Dev bypass:
  Supabase dashboard → Authentication → Providers → Email → uncheck "Confirm email" (re-enable
  pre-prod). Map this honestly in UI error text (don't show "email doesn't look right").
- **Profile upsert throwing on a brand-new (unconfirmed) user** → `profiles` RLS blocks the insert,
  and a `try await upsertProfile` right after `signUp` fails the whole registration. Make it
  non-fatal (`try?`); seed the profile on first confirmed sign-in instead.
- **Storage buckets empty** → tables may exist but the `catch-images`/`shop-logos` buckets weren't
  created → photo upload fails later. Create them (Public) in the dashboard; probe existence with
  `curl -H "apikey: $KEY" "$B/storage/v1/bucket"` (returns `[]` when empty).

## References
- `references/supabase-swift-v2.md` — condensed supabase-swift 2.53.0 API alignment (broken v1
  patterns -> correct v2 signatures), derived from fetched SDK source.
