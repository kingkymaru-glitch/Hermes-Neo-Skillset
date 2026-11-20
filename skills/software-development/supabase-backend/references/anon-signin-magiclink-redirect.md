# Anonymous sign-in (default-off) + magic-link redirect allowlist on shared projects

Two Auth-config traps hit while testing SkyPin (Flutter AR app) on the shared
rina-platform Supabase project. Both are dashboard-side fixes, not code bugs.

## P51 — Anonymous sign-in is DISABLED by default

**Symptom:** `signInAnonymously()` (or `client.auth.signInAnonymously()`) throws

```
AuthAPIException: Anonymous sign-ins are disabled
status code: 422
code: anonymus_provider_disbled
```

The error code is MISS-SPELLED `anonymus_provider_disbled` (one 'n', one 'l').
Match/diagnose on that literal string, not the canonical spelling.

**Root cause:** Supabase ships with Anonymous Sign-Ins OFF. The RPC/SQL/probe
path cannot enable it — it is a dashboard-only toggle.

**Fix (dashboard, no code, no rebuild):**
1. Supabase → project → **Authentication**
2. **Sign In / Providers** tab
3. Scroll to the bottom → **Anonymous Sign-Ins**
4. Toggle ON (optionally set the anonymous session expiration)
5. Save

**Why you'd use it:** to skip the email round-trip so a developer can test the
core loop. An anonymous sign-in yields a REAL `auth.uid()`, so RPC/RLS gates
that check only `auth.uid() is not null` pass (room creation works). But the
identity is ephemeral — fine for testing; disable for production real-user auth.

## P52 — Magic-link `emailRedirectTo` ignored on a SHARED project

**Symptom:** user taps the email magic link and lands on the OTHER app's site
(e.g. RINA's domain) instead of SkyPin.

**Root cause:** `signInWithOtp(email:, emailRedirectTo: 'skypin://login')` is
honored ONLY if `skypin://login` is in the project's Redirect URLs
(Auth → URL Configuration). On a project shared with another app (SkyPin
reusing rina-platform, whose Site URL is RINA's domain), Supabase discards the
un-allowlisted custom redirect and falls back to the project **Site URL** → RINA.

**Fix (dashboard, no code):** add every scheme the app uses as `emailRedirectTo`
to Redirect URLs:
- `skypin://login`
- `skypin://join`

Same root cause as P30b (password-reset link), but this is the signup/magic-link
flow, and the "shared project whose Site URL belongs to another app" angle is
distinct.

**In-app deep-link handling still required:** the app must listen for the scheme
(AppLinks stream in Flutter / `Linking` in React Native), then for `/login` call
`getSessionFromUrl(uri)` to exchange the token; for `/join` parse the room token
and route to the join screen.

## Real session (SkyPin, ~2026-08-31)
- Anonymous auto sign-in added at startup so MARU could test without email; the
  button/auto path errored with the 422 `anonymus_provider_disbled` until he
  flipped the Anonymous Sign-Ins toggle in the dashboard.
- Magic links had been opening RINA (the shared project's Site URL); adding
  `skypin://login` + `skypin://join` to Redirect URLs fixed it.
