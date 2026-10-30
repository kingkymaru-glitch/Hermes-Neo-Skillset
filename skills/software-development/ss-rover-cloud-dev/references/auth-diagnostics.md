# LunaV — Auth / Login Diagnostics & Password Reset

## "User can't log in" — full-spectrum diagnostic
LunaV inspectors sign in via Supabase email/password. The approval gate is
`profiles.approved`, re-checked in `src/middleware.ts` (Next 16: `middleware`
convention is deprecated → migrate to `proxy` when touching auth routing).
When a user escalates "can't log in", run ALL of these in order and report each
result — don't jump to a conclusion:

1. **Live site up?** `curl -s -o /dev/null -w "HTTP %{http_code}\n" https://lunavsolution.vercel.app`
   Expect 200. A bare `curl` at `okzmblyboudjffaifixa.supabase.co/rest/v1/` returns
   401 by design (no anon key) — that is NOT an outage; auth CLI queries still work.
2. **Auth account healthy?** (link first: `supabase link --project-ref okzmblyboudjffaifixa`)
   ```sql
   select id, email, email_confirmed_at, confirmed_at, last_sign_in_at,
          created_at, banned_until,
          (raw_user_meta_data->>'full_name') as full_name
   from auth.users where lower(email) = '<email>';
   ```
   Pass = `email_confirmed_at` not null, `banned_until` is null, `last_sign_in_at` recent.
3. **Approval gate?** `select * from public.profiles where id = '<id from step 2>';`
   Must have `approved = true` (else middleware redirects /login ↔ /dashboard).
4. **Code gate?** Read `src/middleware.ts` + `src/app/login/page.tsx`. Middleware calls
   `supabase.auth.getUser()` then re-checks `profiles.approved` with the user's own uid
   under RLS — if that read were blocked, even an approved user would bounce.
5. **Conclusion:** if 1–4 pass, the block is CLIENT-side: stale/corrupt session cookie
   (incognito clears it) or a forgotten password. Offer the self-serve reset below.

## Self-serve password reset (shipped fix)
- `src/app/login/page.tsx` has a **"Forgot password?"** toggle → calls
  `supabase.auth.resetPasswordForEmail(email, { redirectTo: origin + '/update-password' })`.
- `src/app/update-password/page.tsx` (new route, builds green) reads the recovery session
  via `supabase.auth.getSession()`, calls `supabase.auth.updateUser({ password })`, then
  routes to `/dashboard`.
- `redirectTo` must be an allowed Redirect URL; dashboard Site URL = `lunavsolution.vercel.app`
  so `window.location.origin` is covered.

### Admin-triggered reset (only if user explicitly asks)
There is no `supabase auth` CLI verb that emails a reset link. The self-serve app path is
preferred. Forcing it via SQL (`update auth.users set encrypted_password = ...`) is a
last resort and bypasses the user's own inbox — avoid unless asked.

## Pitfalls
- Next 16 build warns: `middleware` file convention deprecated → use `proxy`. Don't add
  new auth logic to `middleware.ts` expecting it to be the future-proof location.
- `createClient()` import = `@/lib/supabase/client` (browser) / `server` (server).
- Stale-cookie is the #1 real cause after a successful prior sign-in; always suggest
  incognito/clear-cookies before assuming a backend problem.
