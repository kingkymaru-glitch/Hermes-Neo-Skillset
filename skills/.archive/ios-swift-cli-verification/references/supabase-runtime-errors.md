# Supabase runtime errors (auth) — diagnosing without Xcode

These surface at RUN time (simulator console), not compile time. A green Cmd+B does
NOT preclude them. All were hit live on AnglerGO.

## 1. "A server with the specified hostname could not be found."
- `NSURLErrorDomain`, `NSErrorFailingURLString=https://<ref>.supabase.co/...`
- MEANING: the hardcoded Supabase project host does NOT resolve in DNS. The project
  is expired/removed (like a dead Firebase project), or the ref is a typo.
- NOT a code bug. Verify: `dscacheutil -q host -a name <ref>.supabase.co` — empty = dead.
- Compare against the URL the user's dashboard actually shows; a previously-correct ref
  can silently die. In AnglerGO the "FishGoneWild" ref `ooeowvbrexxoaleodfum` was dead;
  `merfmrlkjoqrhijzfwbn` (the "angler_go" project) resolved and was live.

## 2. anon key validity (keys are project-scoped)
- GET `https://<ref>.supabase.co/auth/v1/signup` with `apikey` + `Authorization: Bearer` header:
  - **405** = key accepted, host alive (GET not allowed for signup; expected).
  - **401 `{"message":"Invalid API key"...}`** = key does NOT belong to this project.
- Before swapping a URL, test the existing key against the candidate host (405 = keep key).

## 3. HTTP 429 "email rate limit exceeded" on signup
- Supabase throttles confirmation emails (default ~3/hr per address). Repeated test
  signups trip it.
- MISLEADING-MAPPING TRAP: a `friendlyMessage` that does `if message.contains("email")`
  will render this as "That email address doesn't look right." — WRONG. Map
  `rate`/`limit`/`too many` FIRST, before the generic "email" branch.
- Bypass for testing: use a `+alias` (Gmail delivers `inventedmaru+2@gmail.com` to the
  same inbox; Supabase sees a distinct address, resetting the per-address limit), or
  wait ~1h.

## 4. "Build Succeeded" but the RUNNING app still hits the OLD URL/constant
- Cause: stale COMPILED module. Xcode regenerates a NEW
  `~/Library/Developer/Xcode/DerivedData/AnglerGo-<hash>` folder; the cached
  `.swiftdoc` / `.swiftmodule` baked the old constant, and incremental Cmd+B reused it.
- Fix: quit Xcode, `rm -rf ~/Library/Developer/Xcode/DerivedData/AnglerGo-*` (ALL
  hashes, not just the one you remember), reopen, **Cmd+Shift+K → Cmd+B** (clean build
  recompiles the changed file). Then run.
- Diagnose: `grep -rl "old-string" ~/Library/Developer/Xcode/DerivedData/AnglerGo-*`
  confirms the stale module carries the old value.
