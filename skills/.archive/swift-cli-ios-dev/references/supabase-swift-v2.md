# supabase-swift v2 — API facts that bite a v1-era codebase

Collected while porting AnglerGO (Xcode iOS) from Firebase to Supabase using
`supabase-swift` added via SPM. Verified against the ACTUAL pinned source —
`supabase-swift` **2.53.0** — fetched from GitHub (raw.githubusercontent, see
"Verify against the real pinned SDK" below). The installed version is authoritative;
do NOT guess from memory or from a peer agent's paste. An earlier draft of this note
(and a peer "Chairman" agent's paste) contained two WRONG claims — corrected here.

## Know the EXACT pinned version FIRST
Read `AnglerGo.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved`
and find the `supabase-swift` entry → `version`. AnglerGO pins **2.53.0**. Every
signature below is for that version. If the pin changes, re-verify, don't assume.

## CRITICAL correction — there is NO `client.postgrest` in 2.53.0
An earlier version of this note (and a peer "Chairman" agent's paste) claimed the v2
fix was to configure the coder AFTER init via:
```swift
client.postgrest.encoder.dateEncodingStrategy = .iso8601   // ❌ DOES NOT COMPILE
client.postgrest.decoder.dateDecodingStrategy = .iso8601   // ❌ no member 'postgrest'
```
That is WRONG for 2.53.0. `SupabaseClient` exposes `auth`, `storage`, `functions`,
`realtimeV2`, `from(_:)` — but NOT `postgrest`. The error is literally
`Value of type 'SupabaseClient' has no member 'postgrest'`.

**Correct approach:** just construct the client; the Postgrest query builder reached
via `client.from(_:)` already uses an ISO-8601 JSON coder by default in 2.x, so
`Date` columns like `capture_date` round-trip without any manual coder config.
```swift
client = SupabaseClient(supabaseURL: url, supabaseKey: key)   // ✅ that's it
// DB calls: client.from("catches").select().execute().value
```
Do NOT add a `client.postgrest.*` block. If you genuinely need a custom coder, use
`SupabaseClientOptions(postgrest:)` — but confirm that type exists in the pinned
version first (it did NOT in 2.53.0).

## Auth return types (2.53.0)
- `signUp(email:password:)` → returns `AuthResponse` (struct with `.session` and
  `.user`), NOT `Session`. A wrapper returning `AuthResponse?` (nil when email
  confirmation gates the session) is fine and matches call sites that do
  `if let sess = session { sess.user.id … }` (reads `AuthResponse.session.user`).
- `signIn(email:password:)` → returns `Session` directly (NOT `AuthResponse`). Keep
  the `Session` return type for `signIn`.
- `signOut()` → `async throws` (no arg).
- `currentUser` / `session` are on `AuthClient` (`client.auth.currentUser?.id`,
  `client.auth.session`).

## Email / verification
- `resendVerification` does NOT exist. Correct 2.53.0 call:
  ```swift
  try await client.auth.resend(email: email, type: .signup)
  ```
  The argument LABELS are `email:` then `type:` (NOT `type:email:`).
  `ResendEmailType` has exactly two cases: `.signup` and `.emailChange`
  (`"email_change"`). There is NO `.verifyEmail` case — using it yields
  `Type 'ResendEmailType' has no member 'verifyEmail'`. For resending the sign-up
  confirmation, use `.signup`.

  **GOTCHA that bit us (first `.verifyEmail` mistake):** a broad `grep -nE "case " Types.swift`
  matches `AuthChangeEvent` FIRST (it sits ABOVE `ResendEmailType` in the same file), so
  you see `case signedIn` / `case signedOut` / … and wrongly infer `.verifyEmail` exists or
  pick the wrong enum. Always scope the grep to the target enum:
  `awk '/public enum ResendEmailType/,/^}/' Types.swift`. The reusable recipe
  `scripts/fetch_supabase_sdk.sh` prints exactly that block.
- `resetPasswordForEmail(_:)` is the name (not `resetPassword`).

## Storage upload (2.53.0)
- `upload(_ path: String, data: Data, options: FileOptions = .init())` — note the
  labels are positional `_ path`, `data:`, `options:`. `FileOptions` init order is
  `cacheControl` FIRST, then `contentType`: `FileOptions(cacheControl: "3600",
  contentType: "image/jpeg")`. Reversing them triggers
  `Argument 'cacheControl' must precede argument 'contentType'`.
- `getPublicURL(path:)` THROWS in 2.53.0 → must be wrapped: `try client.storage
  .from(bucket).getPublicURL(path: path).absoluteString`. Forgetting `try` yields
  `Call can throw but is not marked with 'try'`.

## Verify against the real pinned SDK (don't guess)
When a v2 API is uncertain, fetch the actual source from GitHub (the sandbox has
network to raw.githubusercontent; tag uses a `v` prefix):
```bash
V=v2.53.0   # from Package.resolved
curl -sL "https://raw.githubusercontent.com/supabase/supabase-swift/$V/Sources/Auth/AuthClient.swift" -o /tmp/sb_auth.swift
grep -nE "public func (signUp|signIn|signOut|resetPasswordForEmail|resend)\b" /tmp/sb_auth.swift
grep -nE "enum ResendEmailType|case " /tmp/sb_auth_types.swift   # Types.swift if 404, find real path via tree API
```
If a guessed path 404s, list the dir: `curl -sL "https://api.github.com/repos/supabase/supabase-swift/git/trees/$V:Sources/Auth"`.
This is how the `.signup` vs `.verifyEmail` and `resend(email:type:)` facts were nailed.

## Xcode stale-buffer trap (cost us many turns)
A full-file "Select All + Delete" + paste, or "Source Control → Discard Changes",
reverts the editor to the LAST COMMITTED version. If the fix isn't committed yet,
the discard throws away your work and Xcode rebuilds the broken committed version,
so the SAME errors reappear after restart/reindex. Symptoms: screenshot shows v1 code
even though you "fixed" it; errors persist across quit/reopen.
- Fix: after a correct edit, COMMIT it (so discard can't revert to broken), then
  in Xcode discard/reopen the tab to pull the committed-correct buffer.
- The committed-good recovery path when a file is emptied: `git checkout HEAD -- <file>`
  (or `git show HEAD:<file>` to inspect first), then re-apply only the v2 fix on top.
- "Missing argument for parameter 'ownerUID' in call" with a correct caller usually
  means a STALE editor buffer of the callee (ShopsService), not a real signature
  mismatch. Discard/reopen the callee tab, clean (Cmd+Shift+K) + build (Cmd+B).

### The `#Preview` mis-attribution (the final bug this session)
A "Missing argument for parameter 'X' in call" attributed to `SomeView` is often NOT in
the body — it's in the file's `#Preview` block, which instantiates the view with the OLD
initializer signature. This session the error "Missing argument for ownerUID" pointed at
`ShopOwnerDashboardView` and the cache mis-blamed the `saveShop` call site, but the REAL
broken call was the `#Preview`:
```swift
#Preview {
    ShopOwnerDashboardView(ownerEmail: "owner@coastalprotackle.my", onSignOut: {})  // ← missing ownerUID:
}
```
Fix: add the required arg with a dummy UUID for previews —
`ShopOwnerDashboardView(ownerEmail: "...", ownerUID: "00000000-0000-0000-0000-000000000000", onSignOut: {})`.
Rule: when an error is attributed to a view's file, grep the WHOLE file (body AND `#Preview`)
for the initializer call before editing a correct caller.

### Multiple stale DerivedData folders (nuclear cache corruption)
After enough quit/reopen/index churn, Xcode can accumulate SEVERAL
`DerivedData/AnglerGo-*` folders; the index resolves symbols from an old cache and the
error NEVER clears via discard/reopen alone (steps above). The cure:
```bash
osascript -e 'quit app "Xcode"'      # must QUIT first — Xcode locks the active folder
sleep 2; pkill -f Xcode
rm -rf ~/Library/Developer/Xcode/DerivedData/AnglerGo-*   # glob clears ALL of them
```
Then reopen, let indexing FINISH (spinner gone), Cmd+Shift+K → Cmd+B. This was the actual
root-cause fix for the persistent ownerUID error after discard/reopen had failed.

## Never apply another agent's full-file "corrected" paste blindly
This session a peer ("Chairman") pasted a "v2-compatible" `SupabaseService.swift` that
(a) DELETED 8 methods 26 live call sites depended on, and (b) hardcoded the WRONG
Supabase project URL (`merfmrlkjoqrhijzfwbn` vs the real `ooeowvbrexxoaleodfum`).
Applied, it would have caused a 26-error regression + pointed the app at the wrong DB.
Rule: when an agent says "replace the whole file," diff it against the real call sites
and the real project config FIRST; keep every required method; never swap the project
URL. Prefer a minimal surgical fix over a full replacement.

## Verify before claiming green (static only)
- `swiftc -parse` on every touched file → exit 0 (syntax only; not a build).
- Grep the file for every method/property the call sites use (`authStateChanges`,
  `loadCatchesFromCloud`, `saveShopToCloud`, `currentUserIDString`, …) — all must be
  PRESENT or ⌘B throws "cannot find" per call site.
- Confirm the URL constant == the real project ref. State explicitly: full
  supabase-swift link resolves only in Xcode ⌘B.
