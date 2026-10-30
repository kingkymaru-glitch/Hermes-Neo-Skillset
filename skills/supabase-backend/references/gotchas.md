# Supabase gotchas — exact reproduction recipes

All from a real session: RINA (Vite/React) + ss-rover-cloud (Next.js)
both moved to Supabase Auth + RLS, then separated onto distinct
free-tier projects. Each gotcha below includes the signal and the fix.

---

## G1 — RLS recursion → 54001 "stack depth limit exceeded"

**Signal:** browser/Edge request to `user_profiles` (or any RLS-gated
table) fails with:
```
code: "54001", message: "stack depth limit exceeded",
hint: 'Increase the configuration parameter "max_stack_depth"…'
```
Also surfaces in `supabase db query` only if you force RLS (owner bypasses it).

**Cause:** an RLS policy calls a helper like `my_org_id()` that
queries the SAME table the policy guards:
```
create policy profiles_select_own on public.profiles
  for select using (organization_id = public.my_org_id());
-- my_org_id() does: select organization_id from public.profiles where id = auth.uid();
```
Policy fires → helper queries profiles → RLS re-fires the policy →
helper again → infinite recursion → stack overflow.

**Fix:** make the helper `security definer` so it runs as the table
owner and bypasses RLS:
```sql
create or replace function public.my_org_id()
returns uuid language sql stable
security definer set search_path = public as $$
  select organization_id from public.user_profiles where id = auth.uid();
$$;
```
Verify: `select prosecdef from pg_proc where proname='my_org_id';` → `t`.

---

## G2 — "Confirm signups" toggle is invisible in the dashboard

**Signal:** a `signUp()` returns `data.user` but `data.session` is
null, and the app hangs on "check your email" / "Loading your
company…". User insists they "turned confirmation off" but the
Email provider modal (Authentication → Sign In / Providers → Email)
shows only 9 settings with NO confirm toggle.

**Cause:** on current Supabase, confirmation is NOT a switch in the
Email *provider* modal. It is driven by either:
- the **"Confirm sign up" email template** (Authentication → Emails →
  Templates → row 1: "Ask users to confirm their email address
  after signing up"), or
- the `mailer.autoconfirm` flag, which the dashboard UI hides.

**Definitive check (no UI guessing):** run a live `signUp` probe
(see `scripts/verify_signup.mjs`). The response tells you:
- `over_email_send_rate_limit` (429) ⇒ confirmation is ON (email send attempted)
- `session? true` ⇒ confirmation is OFF (user active immediately)

**Fix paths:**
- Click the "Confirm sign up" template → disable it (may require
  first "Set up SMTP" on free tier).
- Or flip `mailer.autoconfirm = true` via the Management API
  (needs a Supabase access token — `PATCH /v1/auth/config`).
- Note `auth.config` is NOT writable via `supabase db query`
  (relation does not exist for the query role) — don't waste turns there.

---

## G3 — Free tier = 2 active projects per org

**Signal:** `supabase projects create` fails:
```
The following organization members have reached their maximum limits
for the number of active free projects … (2 project limit).
```
**Fix:** delete or pause one. A dead near-twin project
(e.g. a mistyped ref) is safe to `supabase projects delete <ref> --yes`.
A real app project should NOT be deleted.

---

## G4 — CLI `projects create` syntax

Wrong: `supabase projects create --name x --region oc1`
Right: `supabase projects create <name> --org-id <org> --region <region> --db-password <pw>`
- `--name` is NOT a flag (name is positional).
- Region is a full code: `ap-southeast-2` (Sydney), NOT `oc1`.
- Org id from `supabase projects list` (the `ORG ID` column).

---

## G5 — Live signup probe (the only real verification)

Don't trust UI toggles or owner-role SQL for RLS/confirmation.
Use a Node script with `@supabase/supabase-js`:
- `signUp({ email, password, options:{ data:{ company_name:'X' }})`
  → first-admin path (trigger creates org + SuperAdmin).
- Read `r.data.session` and `r.data.user`.
- On success, query `user_profiles` / `organizations` to prove the
  trigger fired; then DELETE the test rows + `auth.users` entry.
Run it from a dir with `node_modules/@supabase/supabase-js`
(any project that has it installed). See `scripts/verify_signup.mjs`.

---

## G6 — anon key renamed to "Publishable key"

The dashboard (Settings → API Keys) no longer shows "anon public".
What you need for a browser `VITE_SUPABASE_ANON_KEY` /
`NEXT_PUBLIC_SUPABASE_ANON_KEY` is the **Publishable key**
(`sb_publishable_…`), NOT the masked Secret key.

**Pasting long keys through chat truncates them** (a ~200-char JWT
arrives with only 2 segments → `401 Invalid API key`). Avoid by:
- setting the Vercel env var directly from the dashboard clipboard, or
- saving the full key to a local file and reading it.
Public anon/publishable keys are safe to expose, but must be COMPLETE.

---

## G7 — Vercel env vars inline at BUILD time

A Vite/Next app reads `import.meta.env.VITE_*` at build time.
If `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY` are missing
in Vercel, the client throws `supabaseUrl is required.` and the
whole page is blank (module-load crash, not a component error).

**Fix:** set both in Vercel (Project → Settings → Env) AND redeploy.
Verify after deploy by fetching the live JS bundle and grepping for the
real Supabase URL (proves it was baked in). Also make the client
resilient: guard `createClient` and render a "Backend not configured"
screen instead of a blank crash.

---

## G8 — Approval gate (only admin-approved users get in)

For an app where any confirmed email currently has full access:
- add `approved boolean not null default false` to `profiles`.
- `is_admin()` SECURITY DEFINER helper; `approve_user(target)`
  RPC admin-only.
- signup trigger auto-approves known admin emails + the FIRST user
  (bootstrap, so admin is never locked out); everyone else pending.
- Middleware: after `getUser()`, if `profiles.approved = false` →
  redirect to `/login?reason=pending`. Blocks ALL protected routes.
- Edge Function (upload/presign): also reject unapproved (defense in depth).
- Watch the hardcoded admin email typo trap: `innovated` vs
  `invented` — a one-letter mismatch silently makes the founder
  stuck on "awaiting approval" forever. Verify the admin row is
  `approved=true` AND `is_admin=true` after applying.
