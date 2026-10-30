---
name: supabase-backend
description: >-
  Build and operate Supabase-backed apps (schema, RLS, Auth, multi-tenant
  isolation, CLI project lifecycle, migrations applied to a live project, and
  wiring env vars into Vite/Next + Vercel). Trigger on: "add Supabase
  Auth", "RLS per organization/tenant", "create Supabase project", "Supabase
  CLI create/link project", "multi-company isolation", "Vercel env var not
  picked up", or any task touching supabase/schema.sql, supabase/functions,
  or a `*_auth_user_created` trigger. Also trigger on: "forgot password",
  "password reset", "Supabase persistence", "import .glb models",
  "cloud save badge", "deploy not updating", "jsonb[] write fails", "anon view missing data", "public viewer sees nothing". See
  references/vercel-migrations-not-applied.md for the
  Vercel-does-not-run-migrations trap and the idempotent live-fix pattern,
  and references/live-db-fix-runbook.md for the apply + verify runbook, and references/sql-returns-table-column-order.md for the common RETURNS TABLE column-order mismatch (42P13).
category: database
---

# Supabase Backend (schema, RLS, Auth, CLI, Vercel wiring)

Class-level playbook for shipping a Supabase-backed app without the
recurring traps. Read `references/gotchas.md` for exact reproduction
recipes; `scripts/verify_signup.mjs` is a reusable live-flow probe.
Before pasting any "run this in SQL Editor" migration, see
- `references/verify-before-apply-live.md` — the read-only CHECK 1/2/2b/2c
  sequence and the `::regproc` 42883 false-negative gotcha.
- `references/verify-live-schema-anon-probe.md` — P40/P41: prove a live
  schema/RPC is actually applied using ONLY the anon key (no CLI link, no
  service role); the error-message reading table (a domain error = function
  RAN = pass) and the `rpc()` param-NAME trap. Also the two-app-share-one-
  backend (reader gets anon only) link pattern + key-copy hygiene.
- `references/cross-app-write-read-rpc.md` — two apps sharing ONE Supabase
  project: app A OWNS a table (RLS: owner verified inside a `security definer`
  RPC) while app B reads it via an anon-only view (no service role). Reusable
  for any "writer site → read-only globe/viewer" split; includes the
  mint_handoff_token deep-link handoff pattern.

## USER STYLE PREFERENCE (MARU — embed, don't re-learn)
- When handing over SQL to run in the Supabase Dashboard SQL Editor, give a
  **BARE, paste-ready code block with NO comments and NO explanation** — just
  the `sql`. This founder explicitly rejects annotated/explained SQL
  ("write me a clean code not with ur comment etc", "ok write me a clean code
  that i could copied and paste there"). The annotated/explained version may
  live in `references/` or in chat prose, but the deliverable he pastes must be
  comment-free. Same for any other copy-paste artifact he'll paste into another
  tool. Corollary: keep migration `templates/*.sql` comment-free too (see
  `templates/array_column_migration.sql`).
- **For a multi-statement DB change, write it as ONE clean idempotent `.sql`
  FILE on his Desktop and hand him the path** — he asked for this explicitly
  ("write a clean sql file in file on my desktop so i will not paste rubbish").
  He opens the file, copies all, pastes once, runs once. He WILL ask "where is
  the sql, ill paste it" / "write it to my desktop" if you dump multi-block SQL
  in chat. The repo SQL stays in `supabase/`, the Desktop copy is his one-shot
  apply file. Run the whole file (not just the first statement) — a partial
  paste that approves an org but skips the RLS rewrite leaves the recursion bug
  live, so you get in but then hit empty/error screens. Prefix a "run ONCE in
  SQL Editor, idempotent" header in the file (he reads the file, so a short
  comment there is acceptable; keep the executable body clean).

## When to use
- Designing tables + Row Level Security for multi-tenant (per-org) data.
- Adding email+password Auth, an approval gate, or a signup trigger
  that creates a profile/org.
- Applying SQL to a live (linked) project via `supabase db query`.
- Debugging blank-page crashes, 54001 errors, or "stuck at login".

## Core patterns (do these by default)

1. **Tenancy = `organization_id` column + RLS**, not separate schemas.
   Every table (`organizations`, `user_profiles`, `tasks`, …) carries
   `organization_id uuid`. One RLS helper returns the caller's org:
   ```sql
   create or replace function public.my_org_id()
   returns uuid language sql stable
   security definer set search_path = public as $$
     select organization_id from public.user_profiles where id = auth.uid();
   $$;
   ```
   **SECURITY DEFINER is mandatory** — see Pitfall 1.

2. **Signup trigger creates the profile/org.** `on_auth_user_created`
   (SECURITY DEFINER) reads `new.raw_user_meta_data`:
   - `company_name` present → create org + SuperAdmin profile.
   - `organization_id` present → claim an invited (active=false) profile,
     else insert a Member.
   The trigger fires on `auth.users` INSERT regardless of email
   confirmation, so the profile row exists even pre-confirm.

3. **Apply migrations with `supabase db query --linked --file`.**
   Link once: `supabase link --project-ref <ref>`. Then pipe SQL.
   Owner role bypasses RLS, so this channel can't *verify* RLS
   enforcement — verify enforcement via a real JWT (live signup test).

## Self-serve password reset (recovery flow)

When a user can't sign in (forgotten password, or a stale/corrupt auth
cookie that makes `getUser()` fail and bounce them to login), give them a
**self-serve** path instead of an admin reset. Two pieces:

1. **Login page "Forgot password?" link** → calls
   `supabase.auth.resetPasswordForEmail(email, { redirectTo: window.location.origin + '/update-password' })`.
   `redirectTo` MUST be in Supabase's allowed redirect URLs — for a
   deployed app the Site URL (dashboard Auth → URL Configuration) equals
   the production origin, so `window.location.origin` satisfies it
   automatically. For localhost testing you must ADD `http://localhost:3000`
   to the redirect list or the link bounces.
2. **`/update-password` page** → the email link lands here carrying a
   recovery token in the URL. Supabase JS **auto-exchanges** it into a
   session on load (no manual token parsing). The page calls
   `supabase.auth.updateUser({ password: newPassword })` then routes to
   the dashboard/login. Use a real `<input type=password>` + confirm field.

This fixes the whole account (no ban/RLS trap) — verified in ss-rover-cloud
(LUNAV) 2026-07-29. The trigger script is `scripts/reset_password_email.cjs`;
full page template in `references/password-reset-flow.md`.

**P30b — Reset link opens `localhost:3000` with `#error=access_denied&error_code=otp_expired` = the project Site URL / Redirect URL was never pointed at prod.** Even when the app sends the correct `redirectTo` (production origin), Supabase only honors it if it's in the project's allowed **Redirect URLs**. If it isn't, Supabase falls back to the project **Site URL** — which for a newly created project defaults to `http://localhost:3000`. Result: the email link opens localhost (or errors `otp_expired` / `access_denied`) and the recovery token is never exchanged. **Fix (dashboard, no code):** Authentication → URL Configuration → Site URL = `https://<your-domain>` and add `https://<your-domain>/**` to Redirect URLs. The user must request a FRESH link after the fix (the burned one can't be revived — `otp_expired` is permanent for that token). This is a config gap, NOT a code bug. RINA 2026-08-17.

## Pitfalls (each has a recipe in references/gotchas.md)

- **P1 — RLS recursion → 54001 "stack depth limit exceeded".**
  RLS policy calls `my_org_id()`, which queries `user_profiles`,
  re-entering RLS → infinite loop. Fix: helper MUST be
  `security definer` (runs as table owner, bypasses RLS).
- **P1b — Inline self-referencing subquery in an RLS policy → 42P17 "infinite recursion detected in policy" (fires EVEN when the helper is SECURITY DEFINER).** When a policy body sub-selects the SAME table it's on (`organization_id in (select organization_id from public.user_profiles where id = auth.uid() and approved = true)`), Postgres rejects it regardless of whether `my_org_id()`/`my_org_ids()` is SECURITY DEFINER — the recursion is in the POLICY's own inline subquery, not the helper. Symptom: anon REST read of the table returns `{"code":"42P17","message":"infinite recursion detected in policy for relation \"user_profiles\""}`; a logged-in user's `fetchMyProfiles()` errors and the app silently falls into its empty/choose-a-company state ("logged in but see nothing") — NOT a crash. **Fix: route the policy through the SECURITY DEFINER set-returning helper** (`create or replace function public.my_org_ids() returns setof uuid security definer ... as $$ select organization_id from public.user_profiles where id = auth.uid(); $$;`) and use `organization_id in (select public.my_org_ids())` in the policy — never an inline subquery on the same table. Apply the same helper call to ALL policies that must resolve "which orgs does the caller belong to" (orgs, tasks, audit, profiles). RINA 2026-08-17: the 20260816 multi-org migration inlined the subquery; every profiles/tasks/audit read 42P17'd until policies were rewritten to call `my_org_ids()`. Full before/after + the master-admin companion patterns in `references/multi-org-master-admin-control.md`.
- **P2 — "Confirm signups" toggle is NOT where you'd expect.** In the
  NEW Supabase dashboard it is NOT in the Email *provider* settings
  (Auth → Providers → Email shows only password/OTP/SMTP, no confirm
  toggle) and NOT in URL Configuration. It lives at **Authentication
  → Emails → Templates → row 1 "Confirm sign up"** (a 6-row template
  list: Confirm sign up / Invite user / Magic link / Change email /
  Reset password / Reauthentication). Disabling that template, or the
  hidden `mailer.autoconfirm` flag (P9), stops the requirement. New
  projects default ON, so `signUp` returns `user` but no `session` →
  app hangs on "check your email". Verify via the live signup test
  (P5), not the dashboard maze. If the user reports "I flipped
  confirmation off but still stuck", they likely toggled the wrong
  screen — send them to Authentication → Emails → Templates.
- **P61 — `signUp` for an ALREADY-REGISTERED email returns a DECOY user with NO error.** Supabase's anti-enumeration behaviour: calling `auth.signUp({ email, password })` with an email that already exists does NOT set `error` and does NOT create a user — it returns 200 with a `user` object whose `identities` array is EMPTY. Code that only does `if (error) throw error` then treats this as a fresh signup, so an app that gates new accounts behind admin approval tells a RETURNING user "awaiting approval" — forever, because nothing was created and no email was sent. **Fix: after `signUp`, treat an empty `identities` as "account already exists":**
  ```ts
  const { data, error } = await supabase.auth.signUp({ email, password, options: { data: { full_name } } });
  if (error) throw error;
  if (data.user && data.user.identities && data.user.identities.length === 0) {
    setError("An account with this email already exists. Try signing in, or reset your password.");
    return;
  }
  // genuine new signup -> show the pending-approval state
  ```
  This is the CORRECT behaviour to preserve for security (it must not reveal to an anonymous prober whether an address is registered) — you are not "fixing" Supabase, you are handling the documented shape so a returning user isn't stranded. Pairs with P2/P10/P12 (the other ways signup appears to succeed but doesn't).

- **P3 — Free tier = 2 active projects/org.** `supabase projects
  create` fails with "maximum limits … 2 project limit" until you
  delete/pause one. A dead near-twin project is safe to drop.
- **P4 — CLI `projects create` syntax:** positional name, NOT
  `--name`; region is a full code like `ap-southeast-2`, NOT `oc1`.
  `supabase projects create <name> --org-id <id> --region <region>
  --db-password <pw>`.
- **P5 — Verify Auth flows with a live signup probe** (script below),
  not by guessing. `session? true` ⇒ confirmation OFF;
  `over_email_send_rate_limit` ⇒ confirmation ON (email attempt
  proves it). A plain `select` as owner can't reproduce RLS.
- **P6 — anon key renamed to "Publishable key"** (`sb_publishable_…`)
  in the new Supabase dashboard (Settings → API Keys). The OLD
  `anon public` key is gone. Use the Publishable key for browser
  `VITE_SUPABASE_ANON_KEY` / `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- **P7 — Vercel env vars are inlined at BUILD time.** Missing
  `VITE_SUPABASE_URL`/`ANON_KEY` ⇒ the client throws
  "supabaseUrl is required" and the page is blank. Set them in
  Vercel (Project → Settings → Env) and REDEPLOY. Make the
  client resilient: guard the `createClient` call and render a
  "Backend not configured" screen instead of a blank crash.
- **P8 — Don't paste long secrets/keys through chat.** They truncate
  at the boundary (a 200-char JWT arrives cut to 2 segments →
  401). Set Vercel env directly from the dashboard clipboard, or
  write the key to a local file and read it. Public anon keys are
  safe to expose but must be COMPLETE.
- **P9 — `auth.config` is NOT writable from the linked SQL/CLI
  channel.** `update auth.config …` fails with `relation
  "auth.config" does not exist` (42P01) — the table is internal and
  hidden from the query role. You CANNOT flip `mailer.autoconfirm`
  from `supabase db query`. Non-dashboard paths: the Supabase
  Management REST API (needs an access token) or the dashboard
  Email-template / URL-Configuration toggles. Don't burn a turn on
  the SQL route — go to the dashboard or API.
- **P10 — Email rate-limit blocks the WHOLE signup, not just the
  mail.** When confirmation is ON and the project hits
  `over_email_send_rate_limit` (429), `signUp` returns `user? true`
  but NO `session` and the account is effectively dead — the app
  shows "email rate limit exceeded". Triggered by repeated test
  signups (incl. the agent's own diagnostic scripts). Fix: turn
  confirmation OFF for the test project, OR wait ~15–60 min for the
  per-project hourly cap to clear. Verify with the live probe (P5):
  `over_email_send_rate_limit` ⇒ cap hit; `session? true` ⇒ clear.
- **P11 — Export/share RPCs must return EVERY column the client
  renderer consumes.** A share/portal bundle built by an RPC that
  omits fields the viewer requires (e.g. marker `kind` +
  `geometry_json` for a Three.js/Map viewer) renders NOTHING — every
  node fails its `if (kind===…)` branch. Always mirror the full
  client `Marker`/`Model` type in the RPC's `jsonb_build_object`,
  including nested `geometry_json`. Test the portal with a real
  share token, not just the owner view. See `references/share-export-gotchas.md`.
- **P11b — Column RE-NAMING / data MIGRATION breaks RPCs even when the
  new column is in the type.** Adding a new column and migrating data
  OUT of an old one (e.g. `image_url` → `photos_json`) is invisible to
  an RPC that cherry-picks columns. The owner view reads `photos_json`
  (fine); the share/portal RPC still only returned `image_url` (now
  empty after the migration) and omitted `photos_json` → clients saw
  nodes but NO evidence photos. Symptom: "inspector sees it, client
  link doesn't." Rule: **every time you add/migrate a column, grep ALL
  `get_shared_project` / `get_*_bundle` RPCs and add the new column to
  (`coalesce(k.photos_json, '[]'::jsonb)` so
  old rows don't null-crash).** Also grep every `select <col list>` and
  `update … set` that names columns. See `references/share-export-gotchas.md`.

- **P35 — Repo SQL / RPC is correct but the LIVE RPC is stale = migrations were NEVER applied (CLI not linked, Vercel-only deploys).** Symptom: the client/portal view is missing data (e.g. markers show but evidence photos don't, or proxies are absent) AND the repo's `schema.sql` + `migrations/*.sql` already contain the correct fix — yet the bug persists on the deployed site. Root cause: **`git push` → Vercel auto-builds the Next app, but Vercel NEVER runs Supabase migrations.** If `supabase link --project-ref …` was never done, there is **no `supabase/config.toml`**, so `supabase status` fails ("No such container" / "not linked") and `supabase db push --linked` can't run. Everything under `supabase/` is then merely aspirational — the live DB holds whatever was last typed into the Supabase **SQL Editor** (dashboard) by hand. **Diagnostic (run this BEFORE writing more SQL):**
  1. Confirm the SHARE/portal handler wires the data into a `readOnly` component (e.g. `share/[token]/page.tsx` passes `models` + `proxies` + `documents` into `<ProjectWorkspace readOnly …>`). If it doesn't, that's the bug.
  2. Confirm the frontend renders that data REGARDLESS of `readOnly` (no `readOnly &&` guard hiding markers/evidence). A guard dropping it = frontend bug, not DB.
  3. If 1+2 pass, data is dropped at the RPC. Diff the repo RPC's `jsonb_build_object` (in `schema.sql` / the fix migration) against the TS type it feeds (`Marker`, `ModelWithMarkers`, …). Any field the type has but the RPC omits = missing in the client.
  4. Determine whether the LIVE RPC matches the repo: run `supabase status` or look for `supabase/config.toml`. **If it's not linked → the live RPC is stale by definition** — apply the canonical RPC from `schema.sql` to live.
  **Fix:** apply the canonical `get_shared_project` (and any other changed functions) to the LIVE DB via the Supabase SQL Editor (dashboard → SQL → paste + Run) OR `supabase link --project-ref <ref> && supabase db push --linked`. The project ref is in `.env.local` `NEXT_PUBLIC_SUPABASE_URL` (`https://<ref>.supabase.co`); the CLI link also needs a Supabase access token (dashboard → Account → Access Tokens). `.env.local` typically has only the URL + Publishable (anon) key, NOT a DB/pooler string — so the SQL Editor path needs no extra creds, the CLI path needs the token. Real case (LUNAV ss-rover-cloud, 2026-07-29): `get_shared_project` in `schema.sql` already returned `photos_json`, a fix commit (`aec963b`) was pushed, yet the client link showed markers without evidence because prod had never received the RPC — `supabase status` was unlinked. Triage recipe + the companion frontend fixes in `references/client-view-missing-data-triage.md`.

- **P50 — When tuning RLS to let admins edit OTHER members' rows keeps failing, stop tuning RLS and route the write through a SECURITY DEFINER RPC.**
- **P53 — Landing-page content editable from the DB (admin-only content table).**
  When a founder wants the hero/tagline/stats text editable without code changes, use a
  `landing_content` table with a `section` key ('hero', 'stats', 'highlights', 'center_model')
  and a `data jsonb` column. RLS: `SELECT` public, `INSERT/UPDATE` only when
  `profiles.role = 'admin'`. The `/admin` Next.js route lets the owner edit text + upload a
  GLB center model; the homepage reads from `landing_content` on render. Pairs with P51/P52
  (the `center_model.url` row drives the Three.js swap). Real case (Trip.Pancing, 2026-09-22):
  `landing_content` section 'hero' holds {title, tagline, subtagline}, section 'center_model'
  holds {url: 'https://…supabase.co/storage/.../model.glb', use_default_lure: false}.
- **P54 — Event lifecycle cron (active → ended → archived) uses pg_cron, not Vercel cron.**
  When a founder wants time-bound listings to auto-expire (e.g. events, auctions, bookings),
  use Supabase `pg_cron` (SQL `cron.schedule`) — runs inside the DB, no external service, no
  Vercel cron limits. Two jobs per lifecycle: (a) `flag-ended-events` —
  `UPDATE events SET status='ended' WHERE status='active' AND event_date < now()`; (b)
  `archive-ended-events` — `UPDATE events SET status='archived' WHERE status='ended' AND
  ended_at < now() - interval '7 days'`. Cron expressions run in UTC — convert MYT (UTC+8)
  by subtracting 8 hours: 00:05 MYT = 16:05 UTC. The `events` table needs `ended_at` and
  `deleted_at` timestamptz columns to track the lifecycle. RLS: the archive transition is
  internal (no client write needed). Real case (Trip.Pancing event lifecycle, 2026-09-22).
- **P55 — RLS self-referencing policy = infinite recursion (42P17/54001).** When a policy body
  sub-selects the SAME table it's on (e.g. `profiles` policy doing
  `exists (select 1 from profiles where id = auth.uid() and role = 'admin')`), Postgres rejects
  it with `infinite recursion detected in policy for relation "profiles"` — EVEN when the
  helper is SECURITY DEFINER. Fires for ANY self-referencing policy on any table. **Fix: route
  ALL cross-row authorization checks through a SECURITY DEFINER function**
  (`create or replace function public.is_admin() returns boolean as $$
  select exists(select 1 from public.profiles where id = auth.uid() and role = 'admin');
  $$ language sql security definer set search_path = public;`) and call it in the policy
  (`using (public.is_admin())`). The function runs as table owner, bypasses RLS, never
  re-enters the policy. Apply the SAME pattern to any policy checking a role/permission stored
  on the same table (e.g. `is_event_creator()`, `is_shop_owner()`). Real case (Trip.Pancing,
  2026-09-22): profiles/events/landing_content policies all referenced `profiles` inline →
  54001 "stack depth limit exceeded" on first page load. Fixed by `008_fix_rls_recursion.sql`.
  When a founder wants time-bound listings to auto-expire (e.g. events, auctions, bookings),
  use Supabase `pg_cron` (SQL `cron.schedule`) — runs inside the DB, no external service, no
  Vercel cron limits. Two jobs per lifecycle: (a) `flag-ended-events` —
  `UPDATE events SET status='ended' WHERE status='active' AND event_date < now()`; (b)
  `archive-ended-events` — `UPDATE events SET status='archived' WHERE status='ended' AND
  ended_at < now() - interval '7 days'`. Cron expressions run in UTC — convert MYT (UTC+8)
  by subtracting 8 hours: 00:05 MYT = 16:05 UTC. The `events` table needs `ended_at` and
  `deleted_at` timestamptz columns to track the lifecycle. RLS: the archive transition is
  internal (no client write needed). Real case (Trip.Pancing event lifecycle, 2026-09-22). A SuperAdmin/MasterAdmin must edit/remove ANY member of their org, but direct `.upsert()`/`.delete()` on `user_profiles` kept letting them edit ONLY their own row — even after RLS policies were rewritten (the live policies were inconsistent with the repo migration; this project had a recurring "migration never applied / RLS drifted" pattern). RLS is fragile for admin-masquerading-as-org-member writes. The deterministic fix is server-side functions that bypass RLS, admin-gate in SQL, and self-log — it works no matter what RLS policies are live:
  - `upsert_user_profile(org uuid, payload jsonb)` — create/edit a user.
  - `delete_user_profile(org uuid, target uuid)` — **SOFT delete** (`active=false`) so it can be undone (hard delete can't be undone).
  - `restore_user_profile(org uuid, target uuid)` — re-activate (`active=true`) to undo.
  All three begin `if not is_org_admin(org) then raise exception` (helper `is_org_admin` = caller has `role in ('SuperAdmin','MasterAdmin')` for that org, SECURITY DEFINER), then apply the change, then `insert into audit_logs` with a `jsonb_build_object('action','user_updated'|'user_deleted'|'user_restored','performedBy',auth.uid()::text,'performedOn',target::text,'details',...,'timestamp',now()::text)` — giving an audit trail for free. `grant execute … to authenticated`. Client calls the RPCs; `fetchUsers` filters `.eq('active', true)` so soft-deleted users hide until restored; the Admin UI keeps a ~6s `lastRemoved` undo banner calling the restore RPC. This is the general pattern for "one privileged role edits every row in an org" — prefer an admin RPC over an ever-changing RLS policy. RINA 2026-08-17 (user reported RLS-only edits failing three separate times).
  See also P37 (missing delete policy = silent no-op delete) — the RPC path sidesteps that class of RLS gap entirely.
- **P31 — New columns added to tables MUST be reflected in share RPCs.**
  When adding a column (like `model_id` to proxies), the `get_shared_project`
  RPC must include it in the `jsonb_build_object` output or the client portal
  will miss it. Always update the RPC when schema changes. Verify by:
  1. Grepping the RPC for the table name
  2. Adding any new columns to the JSON output
  3. Testing the share link with a real token

- **P32 — RLS policy referencing a non-existent column = 400 error + silent data loss.**
  When a migration adds a column (e.g. `model_id` to `proxies`) but is NOT applied
  to the live database, RLS policies that reference the new column will fail at
  query time with `ERROR: column "model_id" does not exist` (or 400 from client).
  Symptoms: proxy shapes missing, 400 errors on proxy operations, RLS policies
  failing silently. **Fix:** always apply migrations via `supabase db push --linked`
  BEFORE deploying code that uses the new column. Verify with `select * from
  pg_attribute where attrelid='proxies'::regclass` to confirm column exists.
  See session `2026-07-29 spatial-proxy-fix` for reproduction recipe.

- **P33 — Migration file applies to live DB but RPC not updated = partial/incomplete data in share portal.**
  When a migration is applied to live DB but the corresponding `get_shared_project` RPC
  function is NOT updated (or has an older version), clients see incomplete data. The
  `phase3_share_nodes_fix.sql` file existed in the repo with the correct SQL but was
  NOT applied to the live database. The migration `20260731_proxies_model_id.sql` applied
  an OLD version of the RPC missing `kind`, `geometry_json`, and `photos_json`.
  **Fix:** The `phase3_share_nodes_fix.sql` file contains the correct version - run it
  against live DB via SQL Editor. Always verify the RPC function version matches what's
  in the codebase by comparing the SQL output fields with the TypeScript types.

- **P34 — Marker evidence photos disappear in client share = missing `photos_json` in RPC.**
  When markers have `photos_json` populated (Phase 4 evidence photos) but the
  `get_shared_project` RPC omits this field, clients see markers but NO evidence photos.
  The owner view works because it uses a different query path; the share portal fails
  because the RPC is the only data source. **Fix:** ensure `photos_json` is included in
  the RPC's `jsonb_build_object` with `coalesce(k.photos_json, '[]'::jsonb)` for safety.
- **P12 — "Session exists but no profile" hang.** App shows
  "Signed in — Loading your company…" forever, or bounces to login
  with no error. Cause: the auth user was created (a session exists)
  but `user_profiles` has no row for that id — the signup never
  completed the profile insert (email rate-limit killed it per P10,
  or the `on_auth_user_created` trigger errored). Diagnose:
  `select count(*) from public.user_profiles
   where id = (select id from auth.users where email='x@y.z')`.
  If 0, the trigger didn't persist. Fix: turn confirmation OFF
  (P2/P9/P10) and retry; if still 0, read Supabase **Logs → Auth**
  for the trigger error. Note: the trigger fires on `auth.users`
  INSERT regardless of confirmation, so a missing profile means the
  INSERT itself rolled back, not just a pending email.
- **P13 — Separating two apps that share ONE Supabase project.**
  When a founder wants App B off the shared project (data/email
  isolation), create a fresh project: `supabase projects create
  <name> --org-id <id> --region <region> --db-password <pw>` (P3/P4),
  `supabase link --project-ref <new>`, apply that app's schema
  (`supabase db query --linked --file schema.sql`), then repoint the
  app's Vercel env (`VITE_SUPABASE_URL` + Publishable key, P6/P7) and
  REDEPLOY. The OLD project (and its users/data) is untouched. A
  dead near-twin project can be deleted to free the free-tier slot
  (P3). After repoint, grep the live bundle for the new project ref
  to prove Vercel baked it in (P7 verification step 4).

- **P14 — `supabase db execute` is NOT a valid subcommand** in the
  installed `supabase` CLI. `npx supabase db --help` lists only
  `diff / dump / push / pull / reset / lint` — there is no `execute`, and
  passing `--project-ref` to `db` is rejected ("Unrecognized flag"). The
  older docs-era `supabase db query --linked --file x.sql` may also be
  unavailable. **Reliable path:** write the DDL into
  `supabase/migrations/<YYYYMMDD>_<name>.sql` and run `supabase db push --linked`.
  It diffs against the remote `_supabase_migrations` table and applies ONLY
  new files (existing migrations are skipped, so re-pushing is safe). Use
  idempotent DDL (`alter table … add column if not exists`,
  `create or replace function`) so repeated pushes never error. Confirm with
  `select count(*) from <table>` / `pg_attribute` after.

- **P15 — Migration filename collision: the UNIQUE key is the date
  prefix, not the full name.** `supabase db push` records the leading
  `<YYYYMMDD>` timestamp as `version` in `supabase_migrations.schema_migrations`
  (PK). Two files `20260726_marker_photos.sql` and `20260726_share_photos.sql`
  collide → `ERROR: duplicate key value violates unique constraint
  "schema_migrations_pkey" (SQLSTATE 23505) Key (version)=(20260726) already
  exists`. Adding a letter suffix (`20260726b_…`) then FAILS the file pattern
  → `Skipping migration … (file name must match pattern "<timestamp>_name.sql")`
  so it never applies. **Fix: give the new migration a DISTINCT full date
  (e.g. `20260727_share_photos.sql`), never a same-day variant or `b` suffix.**
  Plan migrations so each lands on a unique calendar date, or bump the date.
- **P16 — Client-side image resize before R2 upload (kill the hard byte
  cap).** A `file.size > MAX` reject blocks legitimate big photos. Instead
  downscale in-browser with `createImageBitmap` + `<canvas>.toBlob("image/jpeg",
  0.8)` capped at ~1280px longest edge, then `uploadToR2(resized)`. A 3MB
  phone photo becomes ~100–300KB without the user hitting a "too large"
  error. Keep a LOOSE raw safety cap (~15MB) only so a 200MB RAW can't
  freeze the tab. Preserve PNG alpha: if the source `type === "image/png"`,
  output `image/png` and skip the white `fillRect` (so proxy textures keep
  transparency). Reusable helper + exact flow in `references/r2-client-resize.md`.
  Apply to node photos AND proxy textures for consistency.
- **P17 — `<input accept>` greys out a NEEDED extension (file visible but
  unselectable).** macOS (and others) dim/disable any file whose extension is
  NOT in the `accept` attribute — the user can SEE it but cannot pick it. Two
  real bugs this project: split glTF's companion `.bin` was greyed out
  (picker was `.glb,.gltf,.obj`, no `.bin`), and proxy PNG textures were
  greyed out (picker was `image/jpeg,image/jpg`, no `image/png`). Both looked
  like "the file won't select." **Rule:** the `accept` list must include EVERY
  extension the handler consumes, INCLUDING companion files (`.bin` for split
  `.gltf`). Also confirm the R2 presign Edge Function `ALLOWED_EXT` includes
  the type — a mismatch fails LATER (400 on presign), not at the picker. Full
  detail + the glTF packer in `references/r2-asset-upload.md`.
- **P18 — Split glTF (.gltf + .bin) upload fails in the viewer.** A `.gltf`
  is JSON that references an external `.bin` (and optional images). Uploading
  ONLY the `.gltf` succeeds (R2 gets it) but `THREE.GLTFLoader` then fetches
  `…bin` next to it on R2 → `Failed to load buffer "X.bin"`. Symptom: a green
  "uploaded to R2" toast, THEN a red THREE error — confusing. **Fix: pack
  split glTF → single `.glb` in the browser before upload** (`gltfToGlb()`):
  inline the `.bin` (+ images) as base64 data URIs, wrap in the GLB container
  (JSON chunk + empty BIN chunk), upload the one `.glb`. `GLTFLoader` reads
  `.glb` natively — viewer unchanged. Requires P17 (`.bin` must be selectable)
  and a multi-select hint ("select the .gltf AND its .bin together"). Algorithm
  + Node sanity-check + verification in `references/r2-asset-upload.md`.
- **P19 — Approval-gate RLS trap: a pending user can't read their OWN profile.** When you add an `approved` flag and harden `profiles_select` to `organization_id = my_org_id() and approved = true`, a pending (not-yet-approved) user can no longer read their own row → the client's profile fetch returns null → instead of seeing an "Awaiting approval" screen they get bounced to Login (or loop). The fix: the select policy MUST still allow a user to read their own row regardless of `approved`: `using ( (organization_id = public.my_org_id() and approved = true) or id = auth.uid() )`. They still see no other user, and `tasks`/`audit` policies stay `approved = true` so pending users get no company data. `my_org_id()` is SECURITY DEFINER so it resolves the caller's org even though the policy now filters the row. Full SPA recipe (column + `is_admin()`/`approve_user` RPC + client gate) is in `supabase-auth-gate` ("SPA approval gate" subsection). Deploy DDL via `supabase db push --linked` (P14/P15) — verify the gate with a live signup probe, not a build (a null profile for a pending user IS the symptom of this trap).
- **P20 — Adding a gating column (`approved`, `active`, …) locks out PRE-EXISTING rows.** `add column … default false` makes every existing row `false`, so an admin/owner who signed up BEFORE the migration is now `approved=false` and gets blocked at the gate ("Awaiting approval" / can't log in). This is a self-inflicted lockout the moment the migration applies. **Fix: backfill in the same deploy.** Either include the backfill in the migration, or add a follow-up migration that flips the existing privileged rows BEFORE users hit the new code:
  ```sql
  -- unblock pre-existing admins / first users after adding `approved`
  update public.user_profiles
    set approved = true
    where role = 'SuperAdmin'
       or id in (select distinct on (organization_id) id
                 from public.user_profiles order by organization_id, created_at asc);
  ```
  Make the backfill idempotent (re-runnable) so a re-push never errors. Deploy the DDL, THEN the client — never ship the client gate before the backfill is live. If you already shipped and locked yourself out, run `update … set approved=true where email='<you>'` directly in the Supabase SQL Editor (runs as postgres, bypasses RLS) — the `approve_user` RPC won't help because you can't log in to call it.
- **P21 — A mid-apply `db push` error leaves the migration "pending" and re-offers it with a STALE same-date version.** If a push fails (e.g. the P15 date-collision `duplicate key … schema_migrations_pkey`, or a transient error), the CLI does NOT record that version, so the NEXT `supabase db push --linked` re-lists the SAME file as still-to-apply and re-hits the same error. Renaming with a same-day `b_` suffix fails the filename pattern (P15) and never applies. **Escape: rename the stuck file to a FRESH calendar date** (e.g. `20260728_approval_backfill.sql`) — that's a new `version`, applies cleanly, and the original error is moot. Symptom to recognize: push prints "Applying migration <samefile>…" then `duplicate key … (version)=(<date>) already exists` on the SECOND attempt. Just bump the date.
- **P22 — Approval UI shows "0 pending" despite the row existing = `profiles_select` over-restricted.** The classic mistake when adding an approval gate: harden `profiles_select` to `organization_id = my_org_id() and approved = true`. That hides pending users from EVERYONE — including the Super Admin — so they never appear on the User Approvals page, even though the row sits in Supabase (you can see it in the table editor, which isn't org-filtered for the project owner). **Signature:** admin opens User Approvals → "0 pending / Everyone is approved", but a pending email is clearly visible in the `user_profiles` table. **Correct policy:** the org *directory* (profiles) stays visible within the org; only `tasks`/`audit` get the `approved` gate. Use `using ( organization_id = public.my_org_id() or id = auth.uid() )` for `profiles_select` — do NOT require `approved = true` there (the own-row `or id = auth.uid()` clause from P19 already lets a pending user read their own row so the "Awaiting approval" screen shows). Keep `tasks_all`/`audit_all` requiring `approved = true` so pending users get no company data. The symptom "row exists but invisible to admin" is the tell — don't re-verify with a build; check the policy text.

 **Recurrency trap (seen RINA 2026-08-07):** a LATER migration in the same repo can re-introduce this exact over-restriction AFTER an earlier fix migration "corrected" it. RINA's `20260729_profiles_rls_fix.sql` set the correct `or id = auth.uid()` policy, but `approval.sql` (applied later) reset `profiles_select` to `organization_id = my_org_id() and approved = true` — so pending users were hidden again and the approval list rendered empty. **Rule:** never trust that an earlier fix migration is the live state. After any approval-gate change, read the LIVE policy text (`select qual from pg_policies where policyname='profiles_select'`) or run a live approval probe, and make the canonical SPA policy `organization_id = public.my_org_id() or id = auth.uid()` (add `or public.is_platform_admin()` for a two-tier gate — P39).

 - **P37 — Missing DELETE RLS policy = SILENT no-op delete.** Every table that has select/insert/update RLS policies but NO `delete` policy will *accept* a client `delete` and return `{error: null}` while touching **0 rows** — the caller believes it worked, nothing was removed. Symptom is sneaky: `user_count`/`count(*)` doesn't drop, and orphan/dead rows accumulate. Real case (RINA, 2026-08-07): the AdminPanel "Remove user" button and the agent's own cleanup both reported success but left the rows; a live `user_count` probe showed it had gone 5→7 from two throwaway signups that could NOT be deleted via anon/RLS. A plain `select`/RPC check can't catch it — only an actual `delete` (or reading `pg_policies` for `cmd='DELETE'`) reveals the missing policy. **Fix:** add the delete policy alongside the others, scoped the same as select/update:
  ```sql
  drop policy if exists "profiles_delete" on public.user_profiles;
  create policy "profiles_delete" on public.user_profiles
    for delete using ( organization_id = public.my_org_id() or id = auth.uid() );
  ```
  Verify by running ONE real delete through the app/RLS path and confirming the count drops (not via build, not via owner-level SQL which bypasses RLS). Note: the Supabase Dashboard table editor runs as postgres (bypasses RLS), so deleting there "working" does NOT prove the client delete policy exists — the two are different privilege levels.

  **Verification-hygiene (RINA 2026-08-07):** a live signup probe that CREATES test rows but can't DELETE them will STRAND orphan rows in prod (here: 2 throwaway users, `user_count` 5→7, that the agent could not remove via anon RLS). Before running an E2E signup probe, either confirm a DELETE policy exists, or tell the user to remove the test rows via the Dashboard (postgres, bypasses RLS). Never create test data you cannot clean up through the same path.

- **P38 — Centralized platform-admin approval gate vs per-org silos (when the founder wants to approve EVERY signup).** Multi-tenant RLS (`organization_id = my_org_id()`) scopes every SuperAdmin to ONLY their own company, so a "User Approvals" list filtered by org never shows cross-company signups — and a "New company" founder auto-approves themselves and never reaches your queue. If the requirement is "every registration on the app lands in MY (owner) account for approve/reject" (the LUNAV model), you must ADD a platform-admin concept ON TOP of the per-org role:
  ```sql
  create or replace function public.is_platform_admin()
  returns boolean language sql stable security definer set search_path = public as $$
    select exists (
      select 1 from auth.users u
      where u.id = auth.uid()
        and u.email in ('owner@domain.com','admin@domain.com')  -- hardcoded owner emails
    );
  $$;
  ```
  - Signup trigger: every new `auth.users` row lands `approved = false` EXCEPT the platform-admin emails (and optionally the first user as bootstrap). This makes ALL signups — including "New company" founders — pending.
  - RLS `profiles_select`: `using ( auth.uid() = id or public.is_platform_admin() )` so the platform admin sees EVERY pending user across all orgs; the approval UI lists `approved=false` with a `company_name`/`organization_id` column so the owner knows who's joining what.
  - `approve_user(target)` guarded by `is_platform_admin()`.
  - Trade-off to surface BEFORE building: this makes the owner a manual bottleneck for EVERY registration (the founder may not realize "New company" founders will now need approval too). Confirm whether they want full LUNAV-mirror (owner approves all) vs keep per-org SuperAdmins AND add a separate platform-level view. LUNAV's exact wiring is in `references/centralized-approval-gate.md`.
 - **P39 — Two-tier approval gate (company registration by platform admin + delegated per-org member approval).** A hybrid of P38 and the per-org silo, used when the founder wants to approve EVERY NEW COMPANY but delegate member approvals to each company's own SuperAdmin (RINA, 2026-08-07). Mechanics: add `organizations.approved`; `is_platform_admin()` = hardcoded owner emails (SECURITY DEFINER); the signup trigger's `company_name` branch makes the founder `approved=false` + org `approved=false` (TIER 1) EXCEPT the platform-admin's own email auto-approves (so the owner is never locked out); member-join stays `approved=false` (TIER 2). App code gates on `orgApproved` BEFORE the `user.approved` gate, and a `CompanyApprovals` screen (visible only to `is_platform_admin()`) approves orgs via an `approve_organization` RPC. The canonical `profiles_select` for this shape is `organization_id = my_org_id() or id = auth.uid() or is_platform_admin()` — see `references/two-tier-approval-gate.md` for the full SQL + SPA gate + verification recipe. **Trade-off to confirm first (same as P38):** making "New company" founders pending turns the owner into a manual bottleneck for every company signup — the founder may not realize founders will now need approval too.
   **P39 extension (RINA 2026-08-17) — the in-app `create_org` RPC bypasses the signup trigger and locks the founder out.** The auto-approve logic in P39 lives in the `on_auth_user_created` SIGNUP trigger. But an already-authed user creating a company via an in-app RPC (`create_org(name)`) does NOT route through that trigger — if the RPC inserts `organizations` without setting `approved`, the org is born `approved=false` and the Tier-1 gate ("Company registration pending") blocks the founder who just created it, with no self-approve button. **Fix: the RPC must set `approved=true` explicitly** (the founder IS the org's SuperAdmin — `insert into public.organizations (name, approved) values (trim(name), true)`). Rule: **every org-creation path (signup trigger AND in-app RPC) must set `approved` explicitly; never assume one path carries the other.** Additionally, a platform admin who must "help set up" other companies needs (a) `master_admin_enter_org(org)` — a SECURITY DEFINER RPC that upserts an approved SuperAdmin profile row for the caller into the target org so `selectOrg` works (see reference), (b) an `orgs_select` policy that adds `or is_platform_admin()` so the control list shows EVERY company, (c) the control screen reachable from the choose-a-company page (else a master admin with no enterable company can never reach it — dead loop), and (d) a creator column is absent on `organizations` so show each company's creator by fetching the EARLIEST SuperAdmin profile via a SECURITY DEFINER `fetch_orgs_with_creator()` RPC. All four companion patterns + SQL in `references/multi-org-master-admin-control.md`.
   **P39 extension 4 (RINA 2026-08-17) — relabel a role/enum display WITHOUT migrating the stored value.** When the founder finds a role name confusing ("Department Head" vs the person's actual position) and wants it shown differently ("Verifier"), do a **display-only rename**: keep the stored value (`'DepartmentHead'`) and change ONLY the display strings in every component that renders it — role badge/label mapper, `member.role.replace('DepartmentHead','Verifier')`, `<option value="DepartmentHead">Verifier</option>`, profile/OrgHome ternaries, help copy. This avoids migrating the stored value across all rows and leaves every `role === 'DepartmentHead'` permission check untouched. Find all spots: `grep -rn "Department Head\|DepartmentHead" src/`. Only migrate the stored value if the founder explicitly wants the DB to literally say the new word. See `references/multi-org-master-admin-control.md` §8.
   **P39 extension 2 (RINA 2026-08-17) — a platform admin must NEVER be caught by the approval/pause/member gates.** If the admin's OWN company has `approved=false` (or they enter a paused company), the Tier-1/pause/Tier-2 gates render "Company registration pending" and lock the admin out of the whole app — even though the admin is the one who approves/pauses. In the SPA gate code, EVERY gate condition must skip the platform admin: `if (orgId && !orgApproved && !platformAdmin)`, `if (orgId && orgPaused && !platformAdmin)`, `if (user.approved === false && !platformAdmin)`. Detect `platformAdmin` async via `await isPlatformAdmin()` in a useEffect (it's not available synchronously at first render). Regular users stay gated exactly as before; only the admin is exempt. Symptom family: "Master Admin logs in and lands on 'Company registration pending' for their own approved company."
   **P39 extension 3 (RINA 2026-08-17) — an org-status read must NEVER fail closed when a column is missing.** A company-status check doing `.select('approved, paused')` errors the ENTIRE query (42703) if `paused` doesn't exist yet (un-applied migration); if the catch falls back to `approved=false`, EVERY user sees "Company registration pending" for fully-approved companies. Fetch the always-present `approved` column and the optional `paused` column as TWO separate error-swallowing queries, and fail OPEN (treat read errors as approved=true) for the gate that blocks users. See `supabase-js-column-pitfalls` #3b for the code pattern. Verification habit: if a user is blocked at a gate but their DB row is correct, probe whether the app selects a not-yet-migrated column (anon REST returns 42703) — an un-applied migration silently degrades to the blocking default.
 - **P23 — Repeated diagnostic signups burn the email rate-limit and BLOCK your own E2E verification.** P10 says confirmation-ON projects rate-limit signups; but the *agent's own* verification scripts (create company → join member → approve) fire several `auth.signUp` calls and hit `over_email_send_rate_limit`, so the gate can't be E2E-proven and the cap lingers. **Mitigations:** (a) prefer a DIRECT owner-level check over live signups when confirming RLS/approval *state* — e.g. run `select email, approved, organization_id from user_profiles` in the Supabase SQL Editor (runs as postgres, bypasses RLS) to see actual values; (b) NEVER loop diagnostic signups; one attempt then wait (cap is per-project hourly); (c) if you must prove the trigger, use a throwaway domain that passes Supabase's email validator (`@example.com` and `@rinatest.app` were rejected — `@gmail.com` worked but then rate-limited). Bottom line: verify schema/state via SQL Editor `select`, not by hammering signUp.
- **P24 — Read-only metrics for a growth/health dashboard (no PII, no RLS break).** To chart "new users" / usage without exposing data, add `SECURITY DEFINER` count-only functions granted to `anon`, and poll them from a script. Pattern (RINA + LUNAV, 2026-07-27):
  ```sql
  create or replace function public.user_count()
  returns bigint language sql stable security definer set search_path = public as $$
    select count(*) from public.user_profiles;
  $$;
  grant execute on function public.user_count() to anon, authenticated;
  ```
  Pair with `pending_user_count()` (where approved=false) for approval queues, and per-table counts (`model_count`, `marker_count`) as usage proxies for apps with no "users" concept. A Node `healthcheck.mjs` (run `node healthcheck.mjs` from a dir with `@supabase/supabase-js`) polls live HTTP + these RPCs and appends a dated row to an Obsidian `HEALTH_LOG.md` table — re-runnable growth tracking. Keep functions COUNT-only; never return rows/PII. Apply via `supabase db push --linked` (P14/P15). Full script + Obsidian table format in `references/metrics-growth.md`.

 - **P25 — Supabase<->GitHub link is SAFE across projects; auto-deploy needs `supabase/migrations/` layout.** Linking multiple Supabase projects to the same GitHub account/org does NOT merge databases (each isolated by its own ref) — no conflict even when MARU/RINA/AnglerGO all link the same GitHub. It's a per-project OAuth grant + repo connection. Cross-account is fine too (a project under `inventedmaru@gmail.com` can authorize the same GitHub as one under `kingkymaru`) — just log into the right Supabase account when you click Link. **Benefit:** `supabase` CLI migration tracking + optional CI auto-deploy. **Trap:** auto-deploy expects `supabase/migrations/<YYYYMMDD>_name.sql` (P14/P15); SQL in a non-standard folder (e.g. `Supabase/catches.sql`) won't auto-apply until restructured. Linking alone = CLI access; it does NOT silently run existing SQL. Full detail in `references/supabase-github-link.md`.

- **P26 — A Supabase URL that "hostname could not be found" at runtime = DEAD PROJECT, not a code bug.** When the app throws `NSURLErrorDomain` "A server with the specified hostname could not be found" for `https://<ref>.supabase.co`, the project ref no longer resolves in DNS (expired/removed — same failure mode as a Firebase project expiry). Verify from the CLI BEFORE trusting any URL: `dig +short <ref>.supabase.co` (empty = dead) and `curl -X POST …/auth/v1/signup -H "apikey: <key>"` → HTTP 200/400/405 = host+key live; `401 {"message":"Invalid API key"}` = wrong key for that project; "Could not resolve host" = dead. The anon/publishable key (`sb_publishable_…`) is PROJECT-SCOPED — a key copied from a dead project won't authenticate a live one; confirm the key against the live host, not by eye. Real case (AnglerGO, 2026-07-27): `ooeowvbrexxoaleodfum` (FishGoneWild) was DNS-dead; the live project is `merfmrlkjoqrhijzfwbn`.
  **Display-name ≠ ref gotcha:** the dashboard project NAME (e.g. "FishGoneWild") is just a label the founder sets — it does NOT identify the project. The real identity is the **ref** in the URL (`<ref>.supabase.co`). So a screenshot showing "FishGoneWild" with buckets can STILL be the live `merfmrlkjoqrhijzfwbn` project (Supabase lets you name any project anything). Don't conclude "the dead project is alive" from the dashboard name — re-run `dig`/`curl` on the actual ref. In AnglerGO, the buckets appeared under a "FishGoneWild"-named dashboard but were on `merfmrlkjoqrhijzfwbn` (the live ref), confirming the code's URL swap was correct. SDK API surface + the Swift-side verification trap (parse ≠ build) are in `references/supabase-swift-v2-api.md`.

 - **P29 — A "patch some fields" RPC that uses `COALESCE(p_x, col)` silently BLOCKS clearing a field to NULL.** When the RPC does `set col = coalesce(p_col, col)`, passing `p_col = null` (to blank a field) keeps the OLD value — `coalesce(null, old)` = old. So "Remove logo" / "Reset accent" / "clear company name" actions can never blank a field; they look like no-ops. **Fix: the RPC writes each field LITERALLY (`col = p_col`), and the caller ALWAYS sends the FULL current state** (read client state → merge patch → send all columns). `null` then genuinely clears. Keep `coalesce` ONLY for the one field that MUST always have a value (e.g. `brand_theme = coalesce(p_theme, 'dark')` so a stray null can't violate a NOT-NULL/CHECK). Real case (ss-rover-cloud Phase 5 client white-label, 2026-07-28): `update_project_branding(p_project_id, p_company_name, p_logo_url, p_theme, p_accent)` first written with 4 COALESCEs — "Remove logo" passed `p_logo_url=null` and silently kept the URL. Rewrote to literal writes + full-state calls from the React Appearance panel. The matching client pattern (read full state, send all fields) is in `react-app-shell-customization`.

 - **P28 — iOS OAuth (Apple + Google) to Supabase needs BOTH code AND dashboard config; code alone won't auth.** In supabase-swift v2.53.0 the correct call is `client.auth.signInWithIdToken(credentials: OpenIDConnectCredentials(provider: OAuthProvider.google/.apple, idToken:, accessToken:/nonce:))`. **Type-name trap (burned a whole session):** `OAuthProvider` IS valid, but the auth-options type for the client init is NOT `AuthOptions` (bare) and NOT `AuthClientOptions` (doesn't exist). It is the NESTED `SupabaseClientOptions.AuthOptions` — use `SupabaseClientOptions(auth: SupabaseClientOptions.AuthOptions(emitLocalSessionAsInitialSession: true))`. Writing bare `AuthOptions(...)` reproduces the "Cannot find 'AuthOptions' in scope" error; see `references/supabase-swift-v2-api.md`. **To REMOVE OAuth safely (the path actually taken 2026-07-27):** don't stub — delete the `signInWithGoogle`/`signInWithApple` methods from the service, the `GIDSignIn.sharedInstance.signIn`/`SignInWithAppleButton`/nonce helpers from LoginView, the `GoogleSignIn`/`CryptoKit`/`AuthenticationServices` imports, the two wrapper methods in AppState, AND unlink the `GoogleSignIn-iOS` SPM package (remove its PBXBuildFile/PBXSwiftPackageProductDependency/XCRemoteSwiftPackageReference lines from .pbxproj + its `googlesignin-ios` entry from Package.resolved) so resolution can't block the build. Email/password Supabase auth stays. Google: use the already-SPM-linked `GoogleSignIn` SDK (`GIDSignIn.sharedInstance.signIn(withPresenting:)` → `user.idToken?.tokenString` + `user.accessToken.tokenString`) and exchange via the wrapper above. Apple: `SignInWithAppleButton` + `CryptoKit` SHA-256 nonce (raw nonce → Supabase, hashed → Apple request). MANDATORY config before it works: (1) Xcode target → Signing & Capabilities → + Capability → **Sign in with Apple** (founder confuses purple folder-group with the blue project icon — click BLUE, pick TARGETS not Project; needs paid Apple Dev membership); (2) Supabase → Auth → Providers → Google enabled, Client ID = `GoogleService-Info.plist` CLIENT_ID, redirect `https://<ref>.supabase.co/auth/v1/callback`; (3) Google Cloud Console adds that same redirect URI; (4) Supabase → Providers → Apple enabled. Pitfalls: `swiftc -parse` won't catch wrong SDK types (grep the INSTALLED package under DerivedData); dropping Firebase lets you delete `GIDSignIn.sharedInstance.handle(url)` (kills the `OpenURLOptionsKey` warning); `SignInWithAppleButton` compiles without the capability but errors at tap-time. Full recipe in `references/supabase-swift-ios-oauth.md`.

 - **P27 — Storage buckets EXIST but have 0 policies → upload is DENIED (the `[]` anon probe is a FALSE NEGATIVE).** After creating buckets in the dashboard (Storage → Files → Buckets; they show "PUBLIC"), an app upload (`storage.from('catch-images').upload(...)`) still fails with a 400/permission error because there are **no Storage policies** — with 0 policies, even `authenticated` users are denied INSERT. The trap: probing buckets with the **anon** key returns `[]` (`curl …/storage/v1/bucket` → `[]`), which LOOKS like "buckets don't exist" — but it's just that anon can't LIST them (expected with 0 policies). The dashboard (your logged-in role) sees them fine. So `[]` ≠ absent. **Fix:** add INSERT (and owner-scoped UPDATE/DELETE) policies in the SQL Editor:
 ```sql
 CREATE POLICY "auth upload catch-images"
   ON storage.objects FOR INSERT TO authenticated
   WITH CHECK (bucket_id = 'catch-images');
 CREATE POLICY "auth upload shop-logos"
   ON storage.objects FOR INSERT TO authenticated
   WITH CHECK (bucket_id = 'shop-logos');
 CREATE POLICY "auth manage own catch-images"
   ON storage.objects FOR UPDATE TO authenticated
   USING (bucket_id = 'catch-images' AND owner = auth.uid());
 CREATE POLICY "auth manage own shop-logos"
   ON storage.objects FOR UPDATE TO authenticated
   USING (bucket_id = 'shop-logos' AND owner = auth.uid());
 ```
 Full case (AnglerGO, 2026-07-27): buckets shown in dashboard but app upload failed until the 4 policies above were added; the anon `[]` had falsely suggested the buckets were missing.

 - **P30 — Password-reset email is rate-limited; triggering it twice in a row fails** with `email rate limit exceeded` (Supabase anti-abuse throttle). In ss-rover-cloud (2026-07-29) a second `resetPasswordForEmail` call ~90s after the first returned `RESET_FAIL: email rate limit exceeded` — the first attempt likely already queued the mail, so the user may still get it. **Fix:** don't loop reset calls; one attempt, then tell the user to check their inbox (incl. spam). If you must retry, wait ~60–90s+. This is the SAME throttle family as P10 (signup) but fires on `resetPasswordForEmail` specifically. There is **no server-side override** — the admin cannot force a faster reset; the user self-serves from the UI. If the user reports "I never got the email", first confirm the address matches a confirmed `auth.users` row (`select email, email_confirmed_at from auth.users where email='x'`), then have THEM retry, not you.

- **P45 — Renaming a column (or converting single→array) breaks the deployed app with "could not find the '<newcol>' column in the schema cache" — and the repo migration is NOT applied.** When you add/retype a column (e.g. `area_polygon` JSONB → `area_polygons` JSONB[], or add a new `annotations` JSONB[] column) and update the TS type, the frontend compiles and `next build` is green — but the LIVE DB still has the OLD column (or no new column), so every `upsert`/`select` throws `site save failed: could not find the "<newcol>" column of <table> in the schema cache` (PostgREST PGRST204). Root causes, in order of likelihood: (1) **Vercel-only deploy never runs migrations** (P35/P14) — `git push` builds Next but the `supabase/migrations/*.sql` never reached prod; (2) **no `supabase link`** so the CLI can't push; (3) the migration was written but never pasted into the SQL Editor; (4) **the migration SQL itself ERRORED** (e.g. P46's `malformed array literal`) so the ALTER aborted and the new column was never created even though the user "ran" it. **Fix sequence:** write ONE idempotent migration file (`supabase/migrations/<FRESH_DATE>_<name>.sql` — see P15 date rule) that does the rename/convert/add, hand it to the user to run in the Dashboard SQL Editor (preferred — no CLI/token needed), then `NOTIFY pgrst, 'reload schema';` at the end so PostgREST picks up the new shape immediately (otherwise the cache can lag even after the column exists). For the CORRECT single→array convert syntax see P46 (the `'{}'::jsonb[]` form, NOT `'[]'::jsonb[]`). **Diagnostic:** before touching code, confirm the live column exists with `select column_name from information_schema.columns where table_name='<tbl>'` in the SQL Editor (runs as postgres, sees real schema). If the new column is absent but the repo migration has it → migrations were never applied (P35), OR the run errored (P46). **Real case (LUNAV Project Homepage, 2026-08-09):** added `annotations` + converted `area_polygon`→`area_polygons` in types.ts and the component, build green, but saves failed because the live `project_sites` still had the old single column — fixed only when the corrected migration SQL (P46 form) was run in the Dashboard + `NOTIFY pgrst`. Rule: a new/renamed column error is ALWAYS a DB-apply gap, never a frontend bug — apply the migration and reload the PostgREST schema cache before debugging further.

- **P46 — `ALTER COLUMN … TYPE jsonb[] USING '[]'::jsonb[]` throws `ERROR 22P02: malformed array literal: "[]"`.** When converting a `jsonb` column to `jsonb[]` (or setting a `jsonb[]` default), the empty-array LITERAL is `'{}'::jsonb[]`, NOT `'[]'::jsonb[]`. Postgres reads `[]` as an array-dimension marker and rejects it as a "malformed array literal"; the canonical empty array is `{}`. The broken form also tends to appear as `ARRAY[area_polygon]::jsonb[]` with a redundant `::jsonb[]` cast on the `ARRAY[...]` constructor (which ALREADY yields `jsonb[]`) — that cast is what trips the parser. **Correct, copy-paste-safe conversion (single jsonb → jsonb[]):**
  ```sql
  ALTER TABLE project_sites
    ALTER COLUMN area_polygon TYPE jsonb[]
      USING (CASE WHEN area_polygon IS NULL THEN '{}'::jsonb[] ELSE ARRAY[area_polygon] END),
    ALTER COLUMN area_polygon SET DEFAULT '{}'::jsonb[];
  ALTER TABLE project_sites
    ADD COLUMN IF NOT EXISTS annotations jsonb[] NOT NULL DEFAULT '{}'::jsonb[];
  NOTIFY pgrst, 'reload schema';
  ```
  Or, even safer when an OLD column exists and you're renaming it: `ALTER TABLE … RENAME COLUMN area_polygon TO area_polygons;` FIRST (no data loss, keeps the old jsonb type), THEN convert its type with the `'{}'` literal above. **Verification after running:** `select column_name, data_type from information_schema.columns where table_name='project_sites' and column_name in ('area_polygons','annotations');` should return both rows with `jsonb[]`. If it returns `area_polygon` (singular) instead of `area_polygons`, the earlier `ALTER … TYPE`/`RENAME` did NOT apply (the `USING` error aborted the statement) — the column silently stayed old, which is exactly why P45's "could not find the column" then appears. **Real case (LUNAV, 2026-08-09):** the first migration used `'[]'::jsonb[]` in both the USING and the DEFAULT → `22P02 malformed array literal`, the ALTER aborted, `area_polygons` was never created, and the frontend then failed with P45. Re-running with `'{}'::jsonb[]` + dropping the redundant `::jsonb[]` cast on `ARRAY[...]` fixed it. **User-style note:** this founder wants PASTE-READY SQL with NO explanatory comments — hand over the bare `sql` code block, not the annotated version (otherwise he asks "write me a clean code").

- **P47 — `jsonb[]` (Postgres native array) CANNOT be written by Supabase JS from a JS array; use plain `jsonb` instead.** When a column is `jsonb[]` and the app does `supabase.from('t').upsert({ col: [{...}, {...}] })` (a JavaScript/JSON array), PostgREST cannot coerce the JSON `[...]` payload into a Postgres native `jsonb[]` — the write is rejected (the save errors or silently writes nothing), even though `tsc`/build are green and a direct `select` of the column type looks fine. **Rule: any column the frontend writes as a JS array MUST be plain `jsonb` (a JSON array), never `jsonb[]`.** `jsonb` accepts `[...]` natively; `jsonb[]` requires a Postgres array literal (`ARRAY[...]::jsonb[]`), which the Supabase client does not emit. The rest of the schema already follows this (e.g. `remarks jsonb`, `extra_fields jsonb`, `markers.photos_json jsonb`) — match it. **Conversion `jsonb[]` → `jsonb` (preserves data, fixes the write):**
  ```sql
  ALTER TABLE project_sites
    ALTER COLUMN area_polygons TYPE jsonb
      USING (CASE WHEN area_polygons IS NULL THEN '[]'::jsonb ELSE to_jsonb(area_polygons) END),
    ALTER COLUMN annotations TYPE jsonb
      USING (CASE WHEN annotations IS NULL THEN '[]'::jsonb ELSE to_jsonb(annotations) END);
  NOTIFY pgrst, 'reload schema';
  ```
  `to_jsonb(jsonb[])` collapses the native array into a JSON array. After this, the app's `area_polygons.map(...)` / `.filter(...)` code works unchanged (it already treats the value as a JS array). **Real case (LUNAV Project Homepage, 2026-08-09):** P45 + P46 got the columns created as `jsonb[]` and the schema-cache error cleared, but boxes/polygons/notes STILL couldn't be saved — the writes failed because `jsonb[]` rejected the JS-array payload. Only converting to plain `jsonb` (above) made writes succeed. Diagnosing "type exists but writes fail" ⇒ suspect `jsonb[]` before anything else.

- **P48 — `ALTER COLUMN … TYPE jsonb` fails with `ERROR 42804: default for column cannot be cast automatically to type jsonb` when the old default is a `jsonb[]` literal (`'{}'::jsonb[]`).** Converting a column that already has a `jsonb[]` DEFAULT to `jsonb` aborts because Postgres can't auto-cast the array-literal default. **Fix: DROP DEFAULT first, convert, then SET the new `jsonb` default:**
  ```sql
  ALTER TABLE project_sites ALTER COLUMN area_polygons DROP DEFAULT;
  ALTER TABLE project_sites ALTER COLUMN annotations DROP DEFAULT;
  ALTER TABLE project_sites
    ALTER COLUMN area_polygons TYPE jsonb
      USING (CASE WHEN area_polygons IS NULL THEN '[]'::jsonb ELSE to_jsonb(area_polygons) END);
  ALTER TABLE project_sites
    ALTER COLUMN annotations TYPE jsonb
      USING (CASE WHEN annotations IS NULL THEN '[]'::jsonb ELSE to_jsonb(annotations) END);
  ALTER TABLE project_sites ALTER COLUMN area_polygons SET DEFAULT '[]'::jsonb;
  ALTER TABLE project_sites ALTER COLUMN annotations SET DEFAULT '[]'::jsonb;
  NOTIFY pgrst, 'reload schema';
  ```
  This is the COMPLETE copy-paste-safe form when a column was previously created as `jsonb[]` (e.g. via P46) and you now need it as `jsonb` (P47). The `DROP DEFAULT` lines are what resolve 42804.

- **P49 — An anon/read-only view MUST load a no-anon-SELECT table via the SECURITY DEFINER RPC, never a direct client `select`.** When a table has only an owner-all RLS policy (no `anon`/`authenticated` SELECT policy), a logged-out client's `supabase.from('t').select('*')` returns **null/error** — so any server component or client that reads the row directly shows empty data (the saved box/area/polygon "disappears" for public viewers). The only anon-readable path is a `SECURITY DEFINER` RPC (e.g. `get_shared_project`) that returns the row in its bundle. **Wiring pattern (LUNAV Project Homepage, 2026-08-09):** when the page has a `shareToken`, load the row via the RPC, not the direct table read:
  ```ts
  export async function loadSharedSite(shareToken: string) {
    const { data, error } = await supabase.rpc("get_shared_project", { share_token: shareToken });
    if (error) throw new Error(`Shared site load failed: ${error.message}`);
    return (data as { site?: ProjectSite | null })?.site ?? null;
  }
  // in the load effect: if (shareToken) s = await loadSharedSite(shareToken); else s = await loadProjectSite(projectId);
  ```
  Symptom: "owner sees the area, anon sees nothing, no error in console" ⇒ the component is doing a direct `select` on an owner-only table. Fix by branching to the RPC when a share/handoff token is present. Pair with P41 (the RPC is the anon-safe reader) and P11b (the RPC must SELECT the new column).

- **P56 — A `returns <table>` RPC with no matching row returns a ROW OF NULLs, not SQL NULL — which kills any poll loop.** An empty result from a function declared `returns public.some_table` comes back as HTTP 200 with a JSON **object whose every field is null** (a composite record), not `null`. A poller doing `if row:` sees a **truthy** value and proceeds to use a nonexistent row — the first field access throws (`'NoneType' object is not subscriptable`). This is the classic shape for a job-queue claim RPC (`claim_next_job(worker)`) polled in a loop, and it fails within seconds of the service starting. **Fix: guard on the identity field, never on truthiness:** `if row and row.get("id"):`. Diagnose by calling the RPC directly when the table is empty and reading the body — if it is an object of nulls, that is this trap, not an auth or schema problem. Corollary for ops: after enabling any polling worker service, READ ITS LOG immediately — `systemctl is-active` returning `active` only means the process started, not that the loop is healthy.

- **P57 — Supabase Storage object paths are BUCKET-RELATIVE; a key that includes the bucket name double-prefixes.** `POST /storage/v1/object/<bucket>/<key>` already carries the bucket, so if your `key` also begins with the bucket name (e.g. you store `gpu-jobs/<id>/result.glb` and build the path the same way) the object lands at `<bucket>/<bucket>/<id>/...` — a silently nested folder, NOT an error. The write returns success and the recorded key looks plausible; only a later download reveals it (`404 {"code":"NoSuchKey"}`), and listing the bucket shows a folder named after the bucket itself. **Fix: normalise on BOTH upload and download and store the bucket-relative key in the row:**
  ```python
  def _bucket_relative(key: str) -> str:
      prefix = f"{BUCKET}/"
      while key.startswith(prefix):
          key = key[len(prefix):]
      return key
  ```
  **General rule: fetch and verify the artifact — do not trust a success status or a plausible stored path.** A job marked DONE with a well-formed key proves the writer finished, not that the bytes are retrievable.

- **P57b — Creating a bucket via REST: omit `file_size_limit` or get `413 Payload too large`.** `POST /storage/v1/bucket` with `{"id":"x","name":"x","public":false,"file_size_limit":5368709120}` is rejected with `{"statusCode":"413","error":"Payload too large","code":"EntityTooLarge"}` — the request body is size-checked against the very limit being set. Create the bucket with just `id`/`name`/`public`, then set a limit separately if needed. Note the `413` arrives as an HTTP **400** at the client, so read the JSON `code`, not the status line.

- **P58 — Never judge a credential by its SHAPE, or by how a file RENDERS it.** Two opposite ways to get this wrong, both expensive:
  - **False negative (worse).** A user hand-off can arrive with the value elided for display (`eyJhbG..._7_8`) because the editor/export summarised the middle. Declaring the credential truncated from that text is WRONG — the underlying file may hold it intact. Read the RAW bytes (`open(p,'rb')` and strip RTF control words) before forming any verdict.
  - **False positive.** A value can look structurally plausible and still be junk — e.g. four fields that are all 64-hex hashes. A bucket NAME is a readable word (`ss-rover-models`), never a hash; an R2 account id is 32 chars, not 64. Hashing-each-field is a common export bug.

  The only reliable test is a **live probe**, and the verdict must carry its evidence:
  - JWT (anon / service_role): base64url-decode segment 2 and assert `ref` equals the project ref and `role` is what you expect (see P43b), THEN make one real call — a table read (`HTTP 200`) plus a privileged RPC (`HTTP 204`) proves it end to end.
  - Object-storage keys: attempt the real `list_buckets`/list call and read the error. `Invalid endpoint` or a DNS `label too long` means the account id is not an account id; a TLS handshake failure on a truncated id means the same.
  - Say "it decodes to `role: service_role`, `ref` matches, and a live RPC returned 204" — checkable. "This looks wrong" is not, and a wrong call here blocks the user's entire build.

- **P59 — Publish artifacts through an EXPLICIT private→public bucket transition; never make the working bucket public.** When a backend process (worker, cron, pipeline) produces files a viewer must render, give it a PRIVATE working bucket and publish as a separate, user-triggered act. The viewer needs an unauthenticated URL, so publishing = copy the artifact into a PUBLIC bucket, insert the app's own asset row (`public.models`-style, with a `source` value so the UI can badge provenance), and stamp the public URL back on the producing record so it renders as a link instead of a button. Two buckets, one transition. Why not just make the working bucket public: it exposes every intermediate and failed artifact, and it removes the human gate between "computed" and "served to clients" — which matters for a custody/liability-sensitive product. Client-side publish path that works with only a normal session: sign a short-lived URL for the private object (`POST /storage/v1/object/sign/<bucket>/<key>` → `signedURL`), fetch it, re-upload with `x-upsert: true` to the public bucket, then insert the asset row. Keep the producing record's `public_url` NULL until published so the UI can distinguish "done" from "published".\n  **The product rule underneath it:** a job that produces a file is not usable by the user until it has a row in the app's asset table the existing viewer already reads. Build the publish step in the SAME pass as the job list — shipping "job done" with no way to view the output is technically complete and practically useless.

- **P60 — A status/heartbeat table accumulates stale rows; never `limit 1` without an explicit ORDER BY.** Any table that upserts one row per client/worker id ever seen (heartbeats, presence, probe ids) grows rows you forgot about. A bare `.select("*").limit(1)` returns an ARBITRARY row — in practice often the alphabetically-first dead one — so the UI reports "offline/unreachable" while the real worker is heartbeating seconds ago. This presents as a false alarm on a healthy system and sends you debugging the wrong end. **Fix: always order by the freshness column descending.**
  ```js
  .from("gpu_workers").select("*").order("last_heartbeat", { ascending: false }).limit(1).maybeSingle()
  ```
  Also DELETE throwaway probe rows once you have finished testing credentials — they are the usual culprit. Liveness must be computed from the row's own timestamp (`online && now - last_heartbeat < 30s`), not from the row's mere existence.

- **P36 — Client-generated string IDs for a `uuid` PK fail SILENTLY, and fire-and-forget async hides it.** When the frontend builds a row with a fake id like `user-${Date.now()}-${n}` and upserts it into a table whose PK is `uuid` (`create table … (id uuid primary key …)`), Postgres rejects the insert with `invalid input syntax for type uuid` — but the rejection is invisible if the upsert call is fire-and-forget (not awaited) AND the calling prop/handler doesn't return the promise. The code then shows a false "N added" success toast while nothing was written. **Two-part fix:** (1) never mint string ids for a uuid PK — either let the DB generate it (`default gen_random_uuid()` and omit `id` from the insert), or use a real `crypto.randomUUID()` on the client so the row passes the type check; (2) await every Supabase write (`await onAddOrUpdateUser?.(row)`) and have the handler return the promise (`const upsertUser = (p) => usersApi.upsert(p)` — note the `return`), so a thrown error reaches the `catch` and a real error message can be shown instead of a fake success. Repro recipe in `references/uuid-pk-client-id-gotcha.md`.
- **P40 — `rpc()` matches the call object's keys to the function's PARAMETER NAMES, not position/type.** Calling `supabase.rpc('get_shared_project', { p_token: x })` against a function declared `get_shared_project(share_token uuid)` reports `Could not find the function public.get_shared_project(p_token) in the schema cache` — indistinguishable from "function missing" but actually a NAME mismatch. ALWAYS grep the function definition for the exact param name and call with that key. Symptom to recognize: the SQL Editor shows the function exists, yet the JS client claims it can't be found. Fix: use `{ share_token: x }`, not `{ p_token: x }`. See `references/verify-live-schema-anon-probe.md` for the full anon-key verification probe (how to prove tables/RPCs are live without `supabase db push`).
- **P41 — Two apps can intentionally SHARE one Supabase project (link, don't merge).** When a globe/index app (e.g. R-Tessera, Vite+Cesium) and a detail app (e.g. LunaV, Next+Three.js) must cross-reference, point BOTH at the same backend; the reader app gets ONLY the anon key and reads a public index table + calls owner-validated RPCs with a handoff token minted by the writer. Never ship a service-role key to the reader. RLS: writer tables owner-all; the shared index table grants `anon + authenticated` SELECT (markers are meant to be visible) and gates writes behind an owner-validated RPC. Pattern + key-copy hygiene in `references/verify-live-schema-anon-probe.md`.

- **P42 — `hmac()` needs the `pgcrypto` extension (not enabled by default).** An RPC calling `hmac(<text>,<secret>,'sha256')` or `encode(...)` compiles (CREATE OR REPLACE succeeds) but THROWS at call time with `function hmac(text, text, unknown) does not exist`, and the client sees a **404** on `rpc()` — looks like "function missing / not applied" but the body just references an unavailable extension (Supabase projects don't enable pgcrypto by default). Fix without the extension: use `gen_random_uuid()` (core PG13+) and bind the token to a row by storing it (e.g. `alter table projects add column if not exists handoff_token uuid; ... update projects set handoff_token = gen_random_uuid() ... return ...::text`). Read the rpc error MESSAGE: `function hmac does not exist` = body references a missing extension; `Unknown project`/`Not project owner` = function RAN (proof it's live); `...p_token... not found in schema cache` = param-NAME mismatch (P40). Don't reach for `hmac`/`crypt` unless you first `create extension pgcrypto`.

- **P43b — Decode the JWT to PROVE a key was rotated (not the wrong project).** When every Supabase call returns `Invalid API key` but you're sure the URL is right, don't guess. Decode the anon key's payload (base64url of the 2nd JWT segment) and read `iss` (should be `supabase`), `ref` (must equal the project ref in the URL), `role` (`anon`), and `exp`. If `ref`+`role`+`iss` are correct, the key STRING is stale — the JWT signing secret was rotated in the dashboard, so the old key is rejected everywhere (reads AND writes). Fix: copy the current key from dashboard → Settings → API → Publishable key. **Triple-drift trap:** the deployed app (Vercel) may already hold the NEW key while BOTH your local `.env.local` AND any hardcoded reader key (e.g. R-Tessera's anon client) still hold the OLD one — so local probes and the reader app fail while prod looks fine. Update all three in lockstep. **Also:** if a row (e.g. a geo-node) EXISTS in the DB under an "invalid" key, the write clearly succeeded earlier (under the pre-rotation key) — so do NOT assume the insert path is broken; the failure is purely the stale credential, not your schema/RPC.

  **P42-ADDENDUM — end-to-end token-binding without pgcrypto (LunaV→R-Tessera geo-link).**
  1. `alter table public.projects add column if not exists handoff_token uuid;`
  2. `mint_handoff_token`: SECURITY DEFINER, owner-verify, `gen_random_uuid()`, store on project, return text.
  3. `upsert_project_node`: verify `p_handoff_token = (select handoff_token::text from projects where id = p_lunav_project_id)`.
  Full SQL recipe + anon-key probe in `references/verify-live-schema-anon-probe.md`.

- **P43 — Hardcode public anon keys to skip Vercel env vars.** For a PUBLIC publishable key (already in browser bundles), hardcoding URL + key directly in the client factory (`createClient('https://<ref>.supabase.co', '<anon>', {...})`) bypasses Vercel env vars entirely. No dashboard, no plan upgrade. Used for R-Tessera's anon client pointing at LunaV's shared project. Safe ONLY for publishable keys, never service-role. Remove the null guard. **Catch: if the key was ROTATED in the Supabase dashboard, the hardcoded value is stale.** When every call returns "Invalid API key" but the JWT payload decodes to the right project ref, the key was rotated — Vercel has the new key but `.env.local`/hardcode has the old one. Diagnose by decoding the JWT payload to verify `ref`/`role`/`iss` (see `references/anon-key-rotation.md`). Fix: copy the current key from Supabase dashboard → Settings → API.

- **P43c — A "node vanished on refresh" is usually a stale-key READ failure, not a broken write.** When the same anon key is reused across two apps (writer app + reader app), a dashboard key rotation leaves the reader (and any hardcoded copy) with the OLD key while the deployed writer holds the NEW one. The reader's `select` then returns "Invalid API key" → UI shows no node → user assumes the insert didn't persist. But the row IS in the DB (written under the pre-rotation key). **Before assuming the write path is broken, run `scripts/probe_supabase_key.cjs`** (`ANON=<key> URL=<url> node ... <table>`): it decodes the JWT (proves ref/role), then does a live `select('count')`. "Invalid API key" + correct ref = rotated key; fix by copying the current Publishable key into ALL three places (Vercel env, `.env.local`, any hardcoded reader client). This exact bug hit R-Tessera↔LunaV: nodes were saving fine; the homepage map just couldn't READ them until the key was refreshed. Symptom-to-action: row exists in DB but UI can't read it ⇒ stale credential, not a schema/insert bug.

- **P44 — A React autosave form editing only a SUBSET of a JSONB column snapshot-stales the local form and OVERWRITES the whole blob, wiping auto-filled sibling fields.** When a field (e.g. `remarks` jsonb) holds both auto-filled values (name, coordinate) AND user-typed values (date, client), and the editor seeds its local `form` state from `site.remarks` ONCE at mount — but the async load effect that populates those auto-fields finishes AFTER mount — the form starts empty. Then each keystroke saves `snapshot = { ...form, [field]: value }` (only the local, empty form), which `upsert`s the entire `remarks` column and DESTROYS the auto-filled name/coordinate. After refresh everything is gone (the bad blob was persisted). **Fix (two parts):** (1) on save, merge over the CURRENT persisted object via a ref — `snapshot = { ...siteRemarksRef.current, [field]: value }` — never over the editor's stale local form; (2) re-sync the form when `site.remarks` changes (`useEffect` on `site?.remarks`) so async-seeded fields surface without clobbering in-progress typing. Real case (LUNAV Project Homepage RemarksEditor, 2026-08-09): typing the date erased the auto-filled project name + coordinate; the merge-over-ref fix made name/coordinate survive every edit and persist across refresh. Rule: never build the saved payload from a component-local snapshot of a shared/auto-filled column — read the live value at save time.

- **P36b — Inconsistent FK key-type breaks the join even after the row persists.** A `reports_to` / `parent_id` column must store the SAME key type on BOTH ends. In the RINA upload bug, the batch path stored `reportsTo` as a UUID while the org-chart render matched `child.reportsTo === parent.name` (a name) — so uploaded rows showed as disconnected cards with no reporting lines. A manual "Edit" path stored the name. **Rule:** pick ONE key type for the relationship (UUID id is right for Supabase FKs) and use it everywhere — the insert, the lookup (`users.filter(u => u.id === child.reportsTo)`), and the dropdown (`<option value={u.id}>`). Grepping one path but not the other hides the mismatch until the hierarchy renders wrong. See `references/uuid-pk-client-id-gotcha.md` for the RINA end-to-end fix (AdminPanel batch upload + OrgChart render).

## PostGIS geometry + seed-from-scratch (WKT in, GeoJSON out)
When a table holds a PostGIS `geometry(Polygon,4326)` column and you seed/write it from supabase-js:
- **PostgREST CANNOT insert a `geometry` value from JSON** — a direct `.insert({geom: <geojson>})`/`.upsert` fails. Route every geometry write through an RPC that takes the polygon as **WKT text** and converts server-side: `ST_GeomFromText(p_wkt, 4326)` on insert, and return the row with `ST_AsGeoJSON(geom)::jsonb` so the client reads geometry as GeoJSON (Cesium/Leaflet consume it directly). Fetching the column via PostgREST already returns it as GeoJSON Polygon — no conversion on read.
- **A `language sql` function body cannot run a bare scalar `INSERT ... RETURNING` as a subquery** (`syntax error at or near "INTO"`). Wrap the write in a data-modifying CTE: `WITH ins AS (INSERT ... RETURNING *) SELECT jsonb_build_object(...) FROM ins;`.
- Migration ordering: `create extension if not exists postgis;` FIRST; declare the column `geometry(Polygon,4326) NOT NULL` so SRID is enforced by type (matches Cesium WGS84). Add a GiST index for spatial/proximity queries.
- **supabase CLI and the Management API MASK API keys in terminal/printed output** (middle-ellipsis) — but the FULL keys ARE present in the raw JSON the command writes to a file / returns in the response body. Read the file via `node -e "require('<file>').keys.find(k=>k.name==='service_role').api_key"`; never trust a printed/rendered value. Then write `.env.local` directly from the parsed value (never echo the secret). Same P8 family as not pasting keys through chat.
- **`dotenv.config()` default path is `.env`, not `.env.local`.** A Node/tsx seed/script client that loads `dotenv/config` won't read `.env.local` → env vars undefined. Use `config({ path: '.env.local' })`.
- **gitignore `supabase/.temp/`** — it holds linked-project metadata (project ref, pooler url, version files); not secret but machine-local noise. Note create-next-app's stock `.gitignore` ignores `.env*.local` but NOT a bare `.env` — add `.env`.
- Seed idempotently: look up the project by name before insert (reuse its id) and skip child/risk inserts when rows already exist, so re-running never duplicates.
- RLS for a read-open POC: `create policy ... for select using (true)` on each table is enough to let the anon browser key fetch the rows (geo for the viewer); keep writes RPC/service-role only for now.

## PITFALL: Vercel auto-deploy does NOT run Supabase migrations
 For a Next.js+Vercel app, `git push` → `next build` only. It never connects to
 Postgres and never executes the `supabase/migrations/*.sql` in the repo. So the
 live DB silently drifts from repo migrations: new columns, RPC body changes, RLS
 edits never reach prod. Symptom: frontend code + types + build are all green,
 yet the live feature is broken (e.g. a share portal missing markers/evidence
 because the live RPC still omits those fields). A migration file existing in the
 repo is NOT proof it was applied. Diagnostic order for any "works in code but
 not in prod" Supabase bug: (1) `supabase` CLI reports "no config.toml" → project
 not linked, migrations never pushed; (2) `.env.local` has only URL+anon key (no
 pooler/token) → agent can't push, it's the user's privilege; (3) build ONE
 idempotent SQL file combining all unapplied migrations and hand it to the user to
 run in the Dashboard SQL Editor (preferred, no CLI) — see
 `references/vercel-deploy-does-not-run-migrations.md`. Always fix the DB FIRST
 before assuming the frontend is the culprit.

 ## Verification (run before claiming done)
 1. `npm run build` green (or `next build`).
> Swift/iOS clients: `swiftc -parse` is SYNTAX-ONLY — it misses
> missing-import and SDK-API errors that Cmd+B catches. Run an
> import-coverage sweep and, for SDK-API doubts, fetch the pinned source
> from GitHub. See the `ios-swift-cli-verification` skill.
2. Apply SQL to linked project; confirm objects exist
   (`select count(*) from pg_trigger where tgname='on_auth_user_created'`).
3. **Live signup probe** (`scripts/verify_signup.mjs`) against the
   real project ref + anon key: proves trigger creates org+profile
   and reveals confirmation state. Clean up the test row after.
4. For deployed apps: fetch the live JS bundle and grep for the
   real Supabase URL (proves Vercel env was baked in).

## Support files (this skill)
- `references/gotchas.md` — exact reproduction recipes for every
  pitfall above (G1–G8), with the SQL/CLI/response that
  proves the failure and the fix.
- `references/share-export-gotchas.md` — P9 (`auth.config` unwritable
  from CLI), P10 (email rate-limit kills the whole signup), P11
  (share/export RPC must return every column the client renders), P11b
  (photos_json missing from share RPC = markers visible but NO evidence photos),
  P33 (migration file applies to live DB but RPC not updated = partial/incomplete data).
- `references/rebrand-logo.md` — full app rename + logo swap checklist
  (grep residual brand incl. alt-text, plinth-vs-float on dark UI,
  transparent-PNG alpha check via PIL, `@next/next/no-html-link-for-pages`).
- `references/r2-client-resize.md` — client-side image downscale helper
  (createImageBitmap + canvas.toBlob) to drop the hard byte cap; applied
  to node photos + proxy textures in ss-rover-cloud.
- `references/uuid-pk-client-id-gotcha.md` — P36/P36b: client minted a string id (`user-${Date.now()}-n`) into a `uuid` PK → silent insert failure masked by fire-and-forget async (RINA .xlsx batch upload); plus the FK key-type mismatch that breaks the org-chart join. Repro + two-part fix + the Node-xlsx verification harness.
- `references/centralized-approval-gate.md` — P38: when the founder wants to approve EVERY signup (LUNAV model) vs per-org SuperAdmin silos; `is_platform_admin()` email-list pattern, the trigger-email-branch gotcha, and the centralization trade-off to confirm first.
- `references/two-tier-approval-gate.md` — P39: hybrid gate where the owner approves EVERY NEW COMPANY (TIER 1) and each company's SuperAdmin approves its own members (TIER 2); full SQL (`organizations.approved`, `approve_organization` RPC, canonical `profiles_select`) + SPA gate + verification recipe.
- `references/multi-org-master-admin-control.md` — P1b (RLS 42P17 recursion from an inline self-referencing policy subquery, fixed via SECURITY DEFINER `my_org_ids()`), the in-app `create_org` founder-lockout (RPC must set `approved=true`; signup trigger doesn't cover it), master-admin `master_admin_enter_org` + `orgs_select` platform-admin override + control reachable from choose-a-company page + creator-lookup `fetch_orgs_with_creator()` RPC, and the company-name header. RINA 2026-08-17.
- `references/multi-report-jsonb-array.md` — store a 1..N relationship (e.g. "reports to 1..N bosses") as a plain `jsonb` array column, not `jsonb[]` and not a junction table at small scale. Legacy single-field fallback in one id-set helper, multi-parent render in the org chart, multi-select edit-row UI. RINA `reports_to_ids` 2026-08-17.
- `references/r2-asset-upload.md` — file-picker `accept`-filter gotcha
  (needed extensions greyed out) + split glTF → single `.glb` packer
  algorithm (gltfToGlb) for R2 model uploads.
- `scripts/verify_signup.mjs` — reusable Node probe (run
  `ANON=<publishable_key> node verify_signup.mjs` from a dir with
  `@supabase/supabase-js` installed). Reports key-valid, trigger
  fired, confirmation ON/OFF. Clean up the test row via owner SQL
  (NOT the JS admin call — needs Bearer token).
- `references/health-check.md` — the 4-probe routine (build + live curl +
  Supabase REST/RLS probe + RPC existence) for a one-shot "app health report"
  across deployed Supabase-backed apps; how to read the result.
- `references/supabase-swift-v2-api.md` — supabase-swift v2.53.0
  API surface (client init, `from(_:)` not `postgrest`, `AuthResponse?`
  from signUp, `auth.resend(email:type:)` with `ResendEmailType.signup`,
  Storage `FileOptions` arg order + throwing `getPublicURL`, ISO-8601
  default coder) + the Swift CLI verification trap (`swiftc -parse` ≠
  build) and the dead-project DNS diagnostic (P26).
- `references/supabase-swift-ios-oauth.md` — iOS Apple + Google OAuth to
  Supabase (v2.53.0 `signInWithIdToken` recipe, GoogleSignIn + Apple nonce
  flow, mandatory Xcode/capability + dashboard config, P28 pitfalls).
- `references/supabase-github-link.md` — Supabase<->GitHub linking safety (no DB
  merge across projects, cross-account OK) + the auto-deploy `supabase/migrations/`
  layout trap (P25). Consult when a founder asks "will linking conflict with my
  other projects?".
- `references/password-reset-flow.md` — the full `/update-password` Next.js page
  template + the login-page "Forgot password?" toggle pattern (ss-rover-cloud
  LUNAV, 2026-07-29). Covers the P30 reset-email rate limit.
- `references/client-view-missing-data-triage.md` — fast triage for "client/portal
  view missing data": how to separate FRONTEND bugs (proxy tab won't close, proxy
  overlay leaks into readOnly view) from a DB bug (live `get_shared_project` RPC
  stale because the CLI was never linked and Vercel doesn't run migrations).
  Reuse the 4-step order on any share/portal defect.
- `scripts/reset_password_email.cjs` — reusable Node script that loads `.env.local`,\n  calls `resetPasswordForEmail` for a given address, and reports success/failure\n  WITHOUT printing secrets (run `node reset_password_email.cjs <email>` from the\n  project root).\n- `scripts/probe_supabase_key.cjs` — decode an anon JWT (proves project ref/role)\n  and run a live `select('count')` to distinguish a ROTATED key ("Invalid API key")\n  from a broken schema/RPC. Use before concluding a "node vanished" = write failure\n  (P43c). Run `ANON=<key> URL=<url> node probe_supabase_key.cjs [table]`.

- `templates/array_column_migration.sql` — copy-paste-ready (comment-free) migration that converts a single jsonb column to a JSON-array `jsonb` (NOT `jsonb[]`) and adds a sibling array column, including the DROP DEFAULT step (P45–P48). Use when a frontend writes a JS array.
- `references/pgvector-rag.md` — enable pgvector RAG on Supabase + drive it from supabase-js: write/query the embedding as pgvector-LITERAL TEXT (an array arg mangles), `returns table` RPC with `embedding <=> query_embedding_text::vector`, the `rpc()` type-inference cast, one shared real/mock embedder for BOTH seed and search, deterministic L2-normalized mock (never zeros), idempotent seed.

## Vercel + Supabase env (the silent blocker)
Build reads `import.meta.env.VITE_*` at build time. If the
deployed bundle lacks the URL, the app crashes on load. Always
set BOTH `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`
(= Publishable key) in Vercel and redeploy after adding them.

## Local AI layer on Apple Silicon
When the project uses a local LLM on Mac Mini / Mac Studio for inference or
fine-tuning:
- **Target model for this project:** Qwen 3.8 27B (Apache 2.0, 27B dense,
  multimodal, 256k context). Earlier drafts referenced Qwen 3 8B by mistake;
  the 27B variant is the intended target.
- **Inference on 64GB unified RAM:** full-precision 27B needs ~54GB, leaving
  little headroom for KV cache + system. Use **4-bit quantization** (~14–16GB)
  for comfortable multi-request throughput on Apple Silicon.
- **Fine-tuning on 64GB unified RAM:** feasible with QLoRA / 4-bit base, but
  tight on a single machine. Preferred split: one Mac for training, one Mac for
  production inference.
- **Deployment:** server-side inference only; the browser renders results. Do
  not run model inference in the frontend.
