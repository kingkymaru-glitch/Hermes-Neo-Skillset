---
name: supabase-rls-tenancy
description: >
  Supabase Row Level Security, multi-tenant (per-organization) data isolation,
  and approval-gating patterns for any app (Vite/React SPA OR Next.js).
  USE when: designing a Supabase schema with RLS, adding per-company/per-org
  isolation, wiring Supabase Auth (email+password) behind a real backend,
  building an admin approval gate ("only approved users get in"), debugging
  errors like "54001 stack depth limit exceeded" / RLS recursion, or verifying
  a signup/trigger without a deliverable email. Covers the footguns that
  bite every Supabase session, not the happy path.
---

# Supabase RLS & Tenancy

## When to reach for this
- Any table needs to be invisible across customers/companies → RLS scoped by `organization_id`.
- Supabase Auth email+password behind a real DB (not localStorage / theater auth).
- "Only admin-approved users can use the app" → approval gate.
- You see `54001 / stack depth limit exceeded` **or `42P17 "infinite recursion detected in policy"`** on an authenticated query.

## Core multi-tenant shape
- `organizations(id, name)` — one row per company.
- `user_profiles(id PK = auth.users.id, organization_id FK, role, ...)` — links auth user to an org.
- `tasks` / `audit_logs` / etc. → each carries `organization_id` and is filtered by it.
- Enable RLS on every table: `alter table <t> enable row level security;`
- A helper `my_org_id()` returns the caller's org; every policy uses `organization_id = public.my_org_id()`.

## PITFALL #1 — RLS recursion (54001 / 42P17 stack depth)  [THE big one]
If a policy on table `T` calls `my_org_id()`, and `my_org_id()` queries `T`,
Postgres re-enters RLS → calls `my_org_id()` → queries `T` → … → stack overflow.
Two live error shapes to recognize:
- `54001 "stack depth limit exceeded"` (server-side / psql / SQL Editor), and
- `42P17 "infinite recursion detected in policy for relation \"user_profiles\""`
  (the REST/anon-API shape — surface via a direct `curl .../rest/v1/user_profiles`
  with the anon key; it fires even when the app itself swallows the error).
This surfaces as a blank/hanging app the moment any authenticated query hits that table (e.g. on sign-in / fetchProfile).

FIX: make the helper `SECURITY DEFINER` so it runs as table owner and
**bypasses RLS** (no re-entry). Always pair with `set search_path = public`.
```sql
create or replace function public.my_org_id()
returns uuid language sql stable security definer set search_path = public as $$
  select organization_id from public.user_profiles where id = auth.uid();
$$;
```
Also: any admin-check helper used inside RLS (`is_admin()`) must be
`SECURITY DEFINER` for the same reason. See references/recipes.md.

MULTI-ORG variant: when `user_profiles` PK is the composite `(id, organization_id)`
(one auth user across several companies), a single-value `my_org_id()` is wrong.
Use a SET-returning `my_org_ids()` (SECURITY DEFINER, `returns setof uuid ... select organization_id from user_profiles where id = auth.uid()`), and write policies as
`organization_id in (select public.my_org_ids())` / `id = auth.uid() or organization_id in (select ...)`. Every helper and policy must switch from single- to set-shaped consistently, or an old single-value helper will error at policy-eval time.

**Same-error SECOND cause — INLINING the self-referencing subquery into the policy.** Even with a correct `SECURITY DEFINER` helper in place, if a migration writes the policy's condition as a literal subquery on the SAME table instead of calling the helper, Postgres still fires `42P17` because the subquery re-enters RLS regardless of the helper's existence:
```sql
-- WRONG: self-referencing subquery on user_profiles inside a user_profiles policy
create policy "profiles_select" on public.user_profiles
  for select using ( id = auth.uid()
    or organization_id in (select organization_id from public.user_profiles where id = auth.uid() and approved = true) );
```
**Rule: every org-membership subquery in a policy MUST route through `my_org_ids()` (`organization_id in (select public.my_org_ids())`), never inline a `from user_profiles` subquery.** Real case (RINA 2026-08-17): `20260816_multi_org_membership.sql` defined the helper correctly but inlined the subquery in all 6 policies → `fetchMyProfiles()` errored and the app showed "create company returns nothing". Surface it with a direct anon `curl .../rest/v1/user_profiles` (fires 42P17 even when the client swallows it). Full detail + review checklist in `references/rls-inline-subquery-recursion.md`.

## Approval gate recipe (only approved users get in)
Three layers, all required:
1. **DB**: `profiles.approved boolean not null default false`.
   Auto-approve the admin + the FIRST user (bootstrap, so you're never
   locked out) in the signup trigger; everyone else = pending.
   `is_admin()` = SECURITY DEFINER helper; `approve_user(target)` RPC
   guarded by `if not public.is_admin() then raise exception 'Forbidden'; end if;`.
   Grant `execute on function ... to authenticated;`.
2. **Edge / middleware**: after `auth.getUser()`, read `profiles.approved`
   for the caller; if false → redirect to `/login?reason=pending` (Next.js
   middleware) AND reject in the Edge Function (defense in depth, in case
   the edge is bypassed).
3. **UI**: login shows "awaiting approval" on `?reason=pending`;
   an `/admin` page lists pending + approved with an Approve button → `approve_user`.
Admin link shown only when `is_admin()` RPC returns true.
See references/recipes.md for the full `phase2_approval.sql`.

## PITFALL #10 — `is_admin()` hardcodes ONE email, so co-admins are locked out
A common bootstrap `is_admin()` hardcodes a single founder address:
```sql
-- WRONG once there is more than one admin
where p.id = auth.uid()
  and (u.email = 'founder@gmail.com' or u.email = 'admin@brand.app')
```
Every additional admin then silently cannot reach the admin surface (the
`profiles_select_own` policy that gates the approvals table uses the same
helper, so the page reads "Access denied"). Nothing errors — the helper simply
returns false.

This is a ROLE-LIST bug, not an auth bug. Two rules:
- **Enumerate the real admins with the user, and keep the list in ONE place**
  (the helper). Do not scatter email checks across policies.
- **Verify the list against `auth.users`, not against assumption.** Query the
  live admin users and confirm every intended admin is in the helper:
  `GET /auth/v1/admin/users` with the service_role key lists every account +
  email; compare that set to the emails inside `is_admin()`. A brand-new
  address you were told about may never have signed up, and a live admin may be
  missing from the helper.

Better than a growing email list: a `profiles.is_admin boolean` column, so
admins are rows (grantable from the UI) rather than a redeployed function. If
you keep the email list, replacing the function is a one-statement idempotent
migration — hand the user a comment-free paste copy and state plainly that it
must be applied by hand (PITFALL #3).

Note when verifying: calling `is_admin()` with the service_role key returns
`false` because there is no `auth.uid()` — that proves NOTHING about the list.
The only honest check is signing in as each admin and loading the admin page,
so say that instead of claiming the fix works.

## PITFALL #11 — permission flags default to false for EVERY existing account
A new per-account capability column (`gpu_access`, `can_publish`, `beta_opt_in`)
lands as `false` for every existing row, including the admins. If the UI gates on
that flag alone, the founder opens their own feature and is told they have no
access. Two-part fix:
- Have the gate read `is_admin() OR <flag>`, so admins are never blocked by a
  column they have not granted themselves.
- In the same migration, set the flag true for the known admins (or instruct the
  user to toggle it in the admin UI) so the intent is explicit rather than
  implied by the admin bypass.

## Verify a trigger WITHOUT a deliverable email
Supabase blocks signup on test domains (`example.com` → "Email address … is invalid")
and RLS can't be exercised via the owner channel (`supabase db query` runs as
postgres, which bypasses RLS). To prove a signup trigger works end-to-end,
insert directly into `auth.users` as the linked owner — the `on_auth_user_created`
trigger fires regardless of confirmation:
```sql
do $$ declare new_uid uuid := gen_random_uuid(); new_org uuid; begin
  insert into auth.users (id, email, raw_user_meta_data)
  values (new_uid, 'x@example.com', '{"company_name":"TriggerCo"}');
  select organization_id into new_org from public.user_profiles where id = new_uid;
  raise notice 'org=% role=%', new_org, (select role from public.user_profiles where id=new_uid);
  -- cleanup
  delete from public.user_profiles where id = new_uid;
  delete from public.organizations where id = new_org;
  delete from auth.users where id = new_uid;
end $$;
```
This is the only reliable way to confirm trigger + RLS *logic* from the CLI.

## PITFALL #2 — "Confirm signups" toggle is a mirage
When a fresh signup returns `user` but NO `session` (and the app
shows "check your email" / "awaiting approval" forever), the cause is
almost always **email confirmation still ON**. The natural instinct —
hunt the Supabase dashboard for a "Confirm signups" switch — wastes
many turns, because on current free-tier UI the toggle is NOT where
you'd expect:
- **Authentication → Providers → Email** modal: only provider on/off,
  secure-email-change, password rules, OTP expiry/length. NO confirmation switch.
- **Authentication → URL Configuration**: only Site URL + Redirect URLs. No switch.
- The actual gate is the **"Confirm signup" email template** under
  **Authentication → Emails** (disable that template), OR there is simply
  no master toggle in this UI version. Do NOT burn turns clicking
  Providers / URL Configuration looking for it.
- The Google / Magic-link provider panels are unrelated (a misconfigured
  Google toggle shows a red "Client ID required" error — ignore it for email flows).

**Verify confirmation state WITHOUT trusting the dashboard:** run a live
`auth.signUp()` probe. Inline recipe (run from a repo with
@supabase/supabase-js; pass the anon key from `.env.local`):
```bash
ANON=$(grep NEXT_PUBLIC_SUPABASE_ANON_KEY /path/.env.local | sed 's/.*=//') \
node -e '
const { createClient } = require("@supabase/supabase-js");
const s = createClient("https://okzmblyboudjffaifixa.supabase.co", process.env.ANON);
(async () => {
  const r = await s.auth.signUp({ email: `probe+${Date.now()}@gmail.com`,
    password: "TestPass123!", options: { data: { company_name: "ProbeCo" } } });
  if (r.error) { console.log(/over_email_send_rate_limit|email.*send/i.test(r.error.message)
      ? "CONFIRMATION STILL ON (email send attempted)" : "ERR: " + JSON.stringify(r.error)); process.exit(1); }
  console.log(r.data?.session ? "CONFIRMATION OFF (session returned)" : "CONFIRMATION STILL ON (no session)");
})();
'
```
If it prints `CONFIRMATION OFF` → you're done. If it errors with
`over_email_send_rate_limit` (429) or prints `STILL ON` → confirmation
is still enforced. This is the only reliable signal; the dashboard UI
lies by omission. Note: repeated test signups can trip the 429
rate-limit temporarily — wait a few min or use a plus-address
variant (`you+test1@gmail.com`).

## Apply SQL to a live project
Link once, then pipe a file (idempotent `create or replace` / `if not exists`):
```bash
supabase link --project-ref <REF>
supabase db query --linked --file supabase/schema.sql
```
For an Edge Function change (e.g. r2-presign), `supabase functions deploy <name>`
— it is NOT part of the Next.js build, so deploy it separately.

## Client hardening (avoid blank-crash deploy)
If `VITE_SUPABASE_URL` / anon key are missing (common right after connecting
Vercel), `createClient('','')` throws at import → blank white page. Guard:
```ts
export const SUPABASE_CONFIGURED = Boolean(url && anonKey);
export const supabase = createClient(url || 'https://placeholder.supabase.co', anonKey || 'x', {...});
```
and have the root component render a "Backend not configured — set env vars"
message instead of crashing. Then the deploy is debuggable, not a white screen.

## Next.js build gotcha (surfaced during a Supabase-gated app)
`useSearchParams()` in a page throws at static prerender
("should be wrapped in a suspense boundary"). Fix: split the page so the
hook lives in an inner component wrapped in `<Suspense>` (not just
`export const dynamic = 'force-dynamic'` — that did NOT help a client component).

## Project-selection discipline (MARU / free-tier)
Reuse one free-tier project across apps (RINA + ss-rover-cloud share
`okzmblyboudjffaifixa`, Sydney). Do NOT create a new project. Avoid the
near-twin dead project `eobkcsxwwpszyzbwpqqy`. The anon key lives in
whichever app's `.env.local` (`NEXT_PUBLIC_SUPABASE_ANON_KEY` / `VITE_SUPABASE_ANON_KEY`).

## PITFALL #3 — live schema drift: "schema.sql ran" is a lie on a deploy-only pipeline
`supabase/schema.sql` may say `alter table ... enable row level security;` but on a
**frontend-only deploy (Vercel/Netlify that just builds the SPA)** the SQL never
executed anywhere — the migration lives only in the repo. The live table keeps its
pre-existing state (commonly: RLS DISABLED on `user_profiles`). Result: every
authenticated client can INSERT/UPDATE/DELETE ANY profile row. The symptom is not an
error — it's an open write surface.

RULE: any new column / RLS change requires the SQL to be **manually pasted into the
Supabase SQL Editor** for the live project (hand it to the user as the action item).
Verify state first rather than trusting the repo file:
```sql
select relname, relrowsecurity
from pg_class where relname in ('user_profiles','tasks','audit_logs','organizations');
```
If `relrowsecurity` is `f` on a table you intended to protect, ENABLE it. Treat
"Vercel built successfully" as evidence the *code* shipped, never as evidence the
*DB migration* ran. Put the migration SQL in `supabase/migrations/<date>_*.sql`
(committed + pushed) AND state plainly that the user must apply it by hand.

## PITFALL #4 — client mapper hardcoding blanks out a column
When mapping a DB row -> client `User`/`Profile` state, do NOT hardcode a field to
`''`. A hardcoded `jobDescription: ''` in the profile→user mapper makes the field
always display blank AND, on save, silently overwrite real data with `''`. Always
map every column (`profile.job_description ?? ''`), and when you ADD a column, grep
every row→client mapping and carry it through. This is where new fields "work in
the DB but never show/edit in the UI" — the gap is in the mapper, not RLS.

## Mutating RLS: INSERT / UPDATE / DELETE recipe
SELECT-only hardening is not enough — once you ENABLE RLS you must also define the
write policies or every write is denied (or, worse, was wide-open before). Org-scoped
+ role-scoped pattern, assuming `my_org_id()` + `is_admin()` SECURITY DEFINER helpers
exist (see references/recipes.md):
```sql
-- SELECT: org directory + own row (pending user sees their own row for "awaiting approval")
drop policy if exists "profiles_select" on public.user_profiles;
create policy "profiles_select" on public.user_profiles
  for select using ( organization_id = public.my_org_id() or id = auth.uid() );
-- INSERT / DELETE: SuperAdmin only
drop policy if exists "profiles_insert" on public.user_profiles;
create policy "profiles_insert" on public.user_profiles
  for insert with check ( public.is_admin() or organization_id = public.my_org_id() );
drop policy if exists "profiles_delete" on public.user_profiles;
create policy "profiles_delete" on public.user_profiles
  for delete using ( public.is_admin() );
-- UPDATE: member may edit ONLY their own row; SuperAdmin edits anyone in org
drop policy if exists "profiles_update" on public.user_profiles;
create policy "profiles_update" on public.user_profiles
  for update using ( id = auth.uid() or public.is_admin() )
  with check ( id = auth.uid() or public.is_admin() );
alter table public.user_profiles enable row level security;
```
Signup still works: the `handle_new_auth_user()` trigger is SECURITY DEFINER, so it
bypasses these policies (no RLS recursion — helpers are SECURITY DEFINER too). Full
write-policy walkthrough + a signup-verification probe in `references/write_policies.md`.

## PITFALL #5 — a missing DELETE (or any write) policy denies the command SILENTLY
If a table has SELECT/INSERT/UPDATE policies but NO `delete` policy, RLS treats the
absent policy as DENY for that command — but the Supabase client reports it as a
SUCCESS-SHAPED response (`{ data: null, error: null }`), 0 rows affected. So a
"Remove user" button does nothing, a cleanup script reports ok, and `user_count`
never drops — there is NO error to catch. **Symptom, not an error:** a delete that
"succeeds" but the row is still there. RULE: after enabling RLS you must define the
write policy for EVERY command you actually use (INSERT/UPDATE/DELETE), not just the
ones you first thought of. Add an idempotent delete policy:
```sql
drop policy if exists "profiles_delete" on public.user_profiles;
create policy "profiles_delete" on public.user_profiles
  for delete using ( organization_id = public.my_org_id() or id = auth.uid() );
```
VERIFY after applying: read `user_count()` (anon-granted metric, P24-style) BEFORE and
AFTER an attempted delete — if the count doesn't drop, RLS is silently denying it.
Vite's `npm run build` NEVER parses SQL, so a missing policy is invisible at build
time; grep every `removeProfile` / `from(...).delete()` call site and confirm a
matching policy exists. Full repro + the live-count probe in
`references/rls-delete-policy-gotcha.md`.

## PITFALL #6 — supabase-js masks 500s as `AuthRetryableFetchError {}`; unmask with curl
When a signup/trigger throws server-side (e.g. a trigger `INSERT ... values (...,
null, ...)` into a NOT-NULL column → `23502`), the JS client returns
`error = { name: 'AuthRetryableFetchError', message: '{}', status: 500 }` — an EMPTY
body. You cannot see the real cause from the client. UNMASK by hitting the REST
endpoint directly with curl:
```bash
curl -s -i -X POST "https://<REF>.supabase.co/auth/v1/signup" \
  -H "apikey: <PUBLISHABLE_KEY>" -H "Content-Type: application/json" \
  -d '{"email":"x@example.com","password":"Throwaway-Test-1!","options":{"data":{"name":"T"}}}'
```
The response body shows the true error, e.g.
`{"code":"23502","message":"null value in column \"organization_id\" ... violates not-null constraint"}`.
Use this whenever `signUp` returns `{}` — the real failure is in the trigger/RLS,
- Also: an orphan `v_org is null` branch in a signup trigger that
  inserts `organization_id = null` is a DEAD trap — NOT NULL rejects it with 23502;
  only offer "new company" or "join company" paths that always supply an org.

## PITFALL #7 — "I'm logged in but the UI is empty" (membership-gate blind spot)
Symptom: the user authenticates fine (session exists) but sees no company/tasks/data.
The cause is almost NEVER auth (they got in) — it's the membership/approval gate,
which runs AFTER auth:
- **Step A (membership):** app runs `SELECT * FROM user_profiles WHERE id = auth.uid()`
  joined to `organizations`. **Zero rows → OrgHome renders "You're not part of any
  company yet"** with `authed=true` — so it does NOT bounce to login. This empty-OrgHome
  is the key tell that distinguishes "no profiles" from "not logged in".
- **Step B (Tier-2 approval):** a profile row with `approved=false` → OrgHome card
  renders DISABLED "Pending approval"; clicking does nothing.
- **Step C (wrong org / no seed):** profile `approved=true` but `organization_id`
  points to an org with no seeded rows → empty dashboard.
Most-common real cause: the seed/test data was written to a **different Supabase
project** than the live app queries (project-ref mismatch in the deploy env vars), OR
the signup trigger never created the profile row, OR `approved` was left false.

You CANNOT diagnose this from the agent CLI: RLS scopes `user_profiles` to the caller's
auth token, and the anon REST API returns only the logged-in user's own rows (which you
don't hold). **Hand the user a read-only probe for the Supabase SQL Editor:**
```sql
select id, organization_id, email, role, approved, active
from user_profiles where email = '<user@email>';
select id, name, approved from organizations;
```
- 0 rows in `user_profiles` → profile row missing → re-run the signup trigger or INSERT a
  row linking the auth `uid` to an org.
- row exists, `approved=false` → `update user_profiles set approved=true where email='<user@email>';`
- row exists & approved but the org has no tasks → seed is in the wrong org or wrong project.
See `references/empty-ui-diagnostic.md` for the full probe + the two-tier approval
control-flow (org `approved` AND profile `approved`) that produces the empty/disabled states.

## PITFALL #8 — founder locked out of their OWN just-created company (RPC vs trigger divergence)
Symptom: a platform/admin user clicks "New company" in-app, the org + their
SuperAdmin profile are created, but they land on "Company registration pending"
(Tier-1 gate) with NO way to self-approve — a dead-end. The founder built a
company they can't enter.

Root cause: **two creation paths diverge on approval state.**
- The `on_auth_user_created` **signup trigger** auto-approves the org for known
  admin emails (`approved = true`) so the owner is never locked out — BUT it only
  runs on `auth.users` INSERT and only when `company_name` is in `raw_user_meta_data`.
- A `create_org(name)` **RPC** for an already-authed user inserts the org WITHOUT
  setting `approved` → it defaults to `false`, and does NOT route through the
  trigger. The Tier-1 gate then blocks the creator.

FIX: the `create_org` RPC must set `organizations.approved = true` (the creator IS
the SuperAdmin of that fresh company — there is no one to wait on). Approving
unconditionally at create time is correct; the platform-approval gate still guards
the *join-by-invite* path. Do NOT leave it relying on the signup trigger.
```sql
insert into public.organizations (name, approved) values (trim(name), true) returning id into v_org;
insert into public.user_profiles (id, organization_id, ..., role, active, approved)
values (auth.uid(), v_org, ..., 'SuperAdmin', true, true);
```
Also unblock the already-stuck org: `update public.organizations set approved = true where name = '<name>' and approved = false;`

## PITFALL #9 — ERROR 0A000: calling a set-returning helper directly in a policy (`= any(fn())`)
When you use the multi-org `my_org_ids()` helper (`returns setof uuid`), you MUST write every
policy as `organization_id in (select public.my_org_ids())`. The intuitive `= any(...)` form
is a trap:

```sql
-- WRONG → ERROR: 0A000: set-returning functions are not allowed in policy expressions
create policy "p_select" on public.org_chart_positions
  for select using ( organization_id = any (public.my_org_ids()) );   -- 0A000 at apply time

-- RIGHT → wraps the set-returning fn in a subquery (same as tasks/audit_logs patterns)
create policy "p_select" on public.org_chart_positions
  for select using ( organization_id in (select public.my_org_ids()) );
```

Postgres forbids calling a set-returning function (`setof uuid`) **directly** inside a policy
USING/CHECK expression — that is exactly `0A000`. The `in (select fn())` form is the only
supported shape. The error fires the moment you paste the SQL into the SQL Editor
(apply-time, not query-time), so it never surfaces as a runtime app error — it just blocks
the migration from applying.

THE SAME TRAP INSIDE A SECURITY DEFINER FUNCTION. If your upsert RPC guards membership with
the wrong construct it errors too:
```sql
-- WRONG → unnest() on a setof is the wrong shape; raises at call time
if p_org is distinct from any (select unnest(public.my_org_ids())) then raise exception '...'; end if;
-- RIGHT → same `in (select ...)` test
if not (p_org in (select public.my_org_ids())) then raise exception 'Not a member of this organization.'; end if;
```

RECOGNITION: the error string is `ERROR: 0A000: set-returning functions are not allowed in
policy expressions`. If you ever see it, grep your SQL for `= any (public.my_org_ids())` or
`= any(public.my_org_ids())` and convert every match to `in (select public.my_org_ids())`.
This is distinct from PITFALL #1's recursion (42P17 / 54001) — 0A000 is a *syntax/expression*
rejection of the SRF call, not an infinite loop. See `references/rls-set-returning-0a000.md`
for the exact transcript + the idempotent fixed migration for a per-feature table
(`org_chart_positions`) so the pattern is copy-pasteable.

## references/
- `references/recipes.md` — exact working SQL: `my_org_id()` SECURITY DEFINER,
  full approval-gate migration, trigger-verification DO block.
- `references/write_policies.md` — INSERT/UPDATE/DELETE policy set, why signup is
  unaffected, the client-mapper blanking pitfall, and how to verify after applying.
- `references/rls-delete-policy-gotcha.md` — P5 silent-delete diagnosis (the
  `user_count` before/after probe + fix SQL) and P6 curl-unmask recipe + the
  create-company→join-member→`pending_user_count` 0→1 probe that proves an
  approval gate actually lands new signups as pending and visible to the admin.
- `references/empty-ui-diagnostic.md` — P7 "authenticated but empty UI" probe SQL +
  the two-tier approval control-flow (OrgHome empty-state / disabled card / workspace
  gate) so you can tell the user exactly which of the three states they're hitting.
- `references/master-admin-company-control.md` — platform-admin controls for EVERY
  company (approve/reject/delete), incl. the `orgs_select` master override so the admin
  sees orgs they're not a member of, a guarded SECURITY DEFINER `delete_organization`
  RPC that cascades users/tasks/audit, the reachability rule (put the control button
  on the OrgHome page too, not only the workspace nav — else a company-less admin is stuck),
  "Enter as Super Admin" cross-tenant access, the wire-`onEnterOrg`-in-every-render-site
  dead-button pitfall, master-admin default-landing on control centre, creator resolution
  via earliest-SuperAdmin RPC, and the company-name-in-header rule.
- `references/rls-inline-subquery-recursion.md` — the SECOND cause of `42P17 infinite
  recursion`: a policy that INLINES `from user_profiles` instead of calling the
  SECURITY DEFINER helper (fails even when the helper is correct).
- `references/rls-set-returning-0a000.md` — PITFALL #9: the `0A000 set-returning functions
  are not allowed in policy expressions` error from `= any(public.my_org_ids())`; the exact
  error transcript + the corrected idempotent migration (table + 4 policies + upsert RPC) that
  the RINA org-chart-canvas feature used.

