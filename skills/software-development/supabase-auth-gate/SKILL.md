---
name: supabase-auth-gate
description: "Add real (non-theater) auth to a client-only Vite+React SPA: email register → superadmin approval gate, backend-held credentials, Supabase RLS with a SECURITY DEFINER helper to avoid recursion, trigger-seeded pending profiles, demo-mode fallback when keys are absent, and a security audit. Trigger: user asks to 'protect the app with a password', 'add login / registration', 'only approved users can access', or any auth request on a SPA that currently has zero backend."
version: 1.0.0
---

# Supabase Auth Gate (SPA login + approval)

## When to use
- A Vite + React SPA (no server) needs login / registration / access control.
- User says "protect it with a password", "only approved users", "others register and I approve".
- Superset of any "add auth" request where the app is currently fully client-side.

## The hard truth you MUST deliver first (architect's duty)
A password check written **in the browser app is security theater** — anyone opens
DevTools, reads the code, sees the password, walks in. It fails the first hack
attempt the user asked you to survive. Real protection needs a **backend** that holds
the approved-user list and checks every login server-side; the browser only ever asks
"am I allowed?" and never sees the master list.

So the real decision is which backend, not "add a password":
- **Supabase (recommended):** managed auth, bcrypt-hashed passwords, RLS, built-in
  rate limiting, free tier. Fastest path to bank-grade auth; frontend stays Vite+React
  (no Next.js, no monorepo). This skill's default.
- **Custom Node backend:** more control, more surface to secure + babysit. Same pattern.

Deliver this honestly, then proceed (don't fake a client-side lock and call it secure).

## Architecture (the guard model)
```
Browser (React) ──register(email,pw)/login──▶ Supabase Auth (bcrypt, JWT)
                                                    │
                                          Postgres profiles { id, email, role, status }
                                          status: pending | approved | rejected
                                          role:   user | superadmin
                                                    │
                                          RLS: app data readable ONLY if
                                          auth.uid() AND status='approved'
```
- **superadmin (you):** seeded row role=superadmin, status=approved.
- **new signup:** trigger inserts profile row role=user, **status=pending** → locked out.
- **approval:** superadmin flips status→approved in a private admin panel. Only the
  superadmin RLS policy can write status/role.

## KISS file recipe (Vite+React)
- `src/supabaseClient.js` — `createClient(url, anonKey)`; export `null` + `isSupabaseConfigured=false` when keys absent (graceful, no import-time throw).
- `src/auth/useAuth.jsx` — `AuthProvider` context: session, profile, signIn, signUp, signOut, `isAuthed/isApproved/isSuperadmin`. Signup MUST `signOut()` immediately so pending users can't auto-enter.
- `src/auth/AuthGate.jsx` — wraps the app: no config → DEMO MODE (visible banner, unlocked); loading → spinner; !authed → LoginScreen; !approved → "Awaiting approval"; superadmin + `#admin` → AdminPanel; else children.
- `src/auth/LoginScreen.jsx` — Sign In / Request Access (email + password, min length 8).
- `src/auth/AdminPanel.jsx` — superadmin-only: list users, Approve/Reject.
- `src/auth/auth.css` — styling.
- Wire in `App.jsx`: `<AuthProvider><AuthGate>{...app...}</AuthGate></AuthProvider>`.
- `supabase/schema.sql` — table + trigger + RLS + `is_superadmin()` + seed steps (template provided).

## RLS anti-recursion (the gotcha)
A policy like `using (exists (select 1 from profiles where id=auth.uid() and role='superadmin'))`
causes **infinite recursion** — Postgres re-evaluates RLS on `profiles` while checking
`profiles`. Fix: wrap the check in a **`SECURITY DEFINER` function** (`is_superadmin()`
in the template) that bypasses RLS. Reference `public.is_superadmin()` inside policies.

Policies to create:
- SELECT: `auth.uid() = id OR public.is_superadmin()`
- UPDATE: `using (public.is_superadmin()) with check (public.is_superadmin())` (only superadmin changes role/status — the approval gate)
- INSERT: `with check (false)` — block client inserts; the `handle_new_user()` trigger does it securely.
- Trigger `on_auth_user_created` → insert profile (role=user, status=pending).

## Secret hygiene (non-negotiable)
- **anon key**: public by design — safe in gitignored `.env` as `VITE_SUPABASE_*`.
- **service-role key**: NEVER ships to the browser; backend/env only.
- **user password**: only in the user's private vault note + hashed in Supabase. Never in source/git.
- **Generate a strong password** for the superadmin (random 20-char). Refuse weak requests
  (e.g. `ADMIN1234`) and record the auditor's objection in the vault — but keep the username the user asked for.
- Don't read `.env` with the file tool (secret-bearing, blocked by design). To check key
  presence without echoing secrets, grep via terminal: `grep -q "VITE_SUPABASE_URL=https" .env`.

## Demo-mode fallback (ship-safe)
When keys are absent, do NOT lock the app silently and do NOT leave it unprotected-looking.
Render the real app behind a prominent fixed banner: "⚠ DEMO MODE — auth not active. Add
VITE_SUPABASE_URL/KEY to .env". This makes accidental unsecured deploys impossible to miss.

## Security audit (run after build; record pass/fail in vault)
Static (no live DB needed — runnable today):
1. Secret leak: `grep -rso "password\|service_role" dist/` → must be empty.
2. Register can't auto-enter: confirm `signUp` calls `signOut()`.
3. Injection: no raw SQL from client; all writes via parameterized `.update().eq(id)` (RLS enforces).
4. Privilege escalation: only `is_superadmin()` SECURITY DEFINER can write role/status.
Live (gated on keys): 5. unauth client read blocked by RLS; 6. brute-force rate-limit/lockout;
7. session expiry + logout invalidation; 8. HTTPS in production.

Be honest in the audit: mark live tests PENDING until keys exist. Never fabricate them.

## Support files
- `templates/schema.sql` — paste-ready Supabase SQL (table, trigger, RLS, `is_superadmin()`, seed steps).
- `references/activation.md` — the 3-step go-live (create project → run schema + seed → add .env keys).
- `references/audit.md` — expanded audit checklist + the exact grep commands.
- `references/confirm-signups-dashboard.md` — the "turn off email confirmation" dashboard maze (where the toggle actually lives, what the live `signUp` probe proves, and the Management-API flip when the UI hides it).
- `scripts/live_audit.mjs` — 6-check live audit (anon reach, table exists, RLS isolation, RLS insert-block, superadmin seeded, auth user created). Guards against fake-pass on transport failure. Runs from EITHER the agent sandbox (once the ref is correct — see Pitfall #5) OR the user's Mac: `node live_audit.mjs` inside the project dir. The 6 PASS lines are the real live signal.
  RLS insert-block, superadmin seeded, auth user created). Guards against fake-pass on
  transport failure. Runs from EITHER the agent sandbox (once the ref is correct — see
  Pitfall #5) OR the user's Mac: `node live_audit.mjs` inside the project dir. The 6 PASS
  lines are the real live signal.

## Multi-tenant / multi-company (the RINA pattern, 2026-07-26)
When the user wants several independent companies, each with its own admin and fully
separate data, on a Vite+React SPA with real Supabase Auth (email+password), use per-org
scoping + RLS — NOT a per-browser localStorage partition (that's the no-backend stopgap in
`local-storage-mock-removal`; it doesn't sync across devices). The user explicitly chose
**real email+password auth** over lightweight magic-link for proper isolation.

### Schema (every table scoped by `organization_id`)
- `organizations(id, name)`; `user_profiles(id=auth.users.id, organization_id, name, email,
  position, department, role, active, …)`; `tasks(organization_id, data jsonb)`;
  `audit_logs(organization_id, data jsonb)` (jsonb keeps the existing `Task`/`User` shape
  intact and minimizes schema churn).
- RLS on every table: `using (organization_id = public.my_org_id())` where `my_org_id()` is a
  plain SQL function `select organization_id from user_profiles where id = auth.uid()`.
  **`my_org_id()` MUST be `SECURITY DEFINER set search_path = public`.** This is the
  OPPOSITE of the profiles trap but for the SAME reason: the `user_profiles` RLS policy
  references `public.my_org_id()`, and `my_org_id()` queries `user_profiles` — so WITHOUT
  SECURITY DEFINER the inner query re-enters RLS → calls `my_org_id()` again → infinite
  recursion → **`54001 stack depth limit exceeded`** on EVERY authenticated
  `select * from user_profiles` (sign-in, fetch profile, anything). This bit RINA live
  (2026-07-26): the fix was `create or replace function public.my_org_id() returns uuid
  language sql stable security definer set search_path = public as $$ select organization_id
  from public.user_profiles where id = auth.uid(); $$;`. Confirm with
  `select prosecdef from pg_proc where proname='my_org_id';` → `t`. If you forget
  SECURITY DEFINER, the app boots + sign-in succeeds, then dies at the first
  `user_profiles` read with 54001.
- **Signup trigger** `on_auth_user_created` (SECURITY DEFINER) branches on
  `NEW.raw_user_meta_data`:
  - `company_name` present → `insert organizations` (new org) + `user_profiles` (role
    `SuperAdmin`, active) for `NEW.id`. = "first admin creates the company."
  - `organization_id` present → join existing org: if an **invited** profile exists (same org
    + email + `active=false`), UPDATE it to claim (`id=NEW.id, active=true`); else INSERT a
    `Member`. = "invited member joins."
  - neither → insert an orphan `Member` (admin reassigns later) — acceptable stopgap.
- **Trigger verification without a deliverable email:** inserting into `auth.users` directly
  (as the project owner via `supabase db query`) fires the trigger — confirms org+SuperAdmin
  profile are created, then `delete` the test rows. Don't fight Supabase's signup domain
  blocklist (`example.com` → "is invalid") by hunting for a test email.
- **Supabase blocks signup on non-deliverable domains** with `Email address "x@example.com"
  is invalid` — that's a domain blocklist, NOT "signups disabled." For testing use a real email
  or DISABLE Auth ▸ Providers ▸ Email ▸ "Confirm signups" (see Pitfall #7 re: confirmation OFF).
- **Signup diagnostic (definitive — run it, don't infer from the UI).** When the user says
  "can't create account" on a Supabase-backed app, run a Node `signUp` via the anon key
  against the live project and read the raw result — do NOT guess. A reusable probe:
  ```js
  const { data, error } = await supabase.auth.signUp({ email, password, options:{ data:{...} } });
  console.log('session?', !!data?.session, '| user?', !!data?.user, '| error:', error?JSON.stringify(error):'none');
  ```
  - `user? true, error: none, session: false` → **email confirmation is ON**. The auth user
    IS created but no session; the app bounces you ("check your email" / "awaiting approval").
    This is the #1 cause of "can't create account" on BOTH a vite SPA and a Next.js app
    that share one Supabase project — one "Confirm signups OFF" toggle in the dashboard fixes both.
    (This session: RINA "New company" + SS Rover "Register Inspector" BOTH returned exactly this;
    toggling confirmation off was the fix.)
  - `Email address "x@..." is invalid` → domain blocklist (use a real email / gmail plus-address
    `you+test1@gmail.com`, which still lands in your inbox and isn't blocked).
  - `Signups not allowed` / `403` → signups genuinely disabled (different from the above).
  - `user? true, session: true` → all good; account created AND logged in.
  After the user toggles confirmation off, re-run the probe: `session: true` proves both apps now
  let you straight in. (Reusable probe shape: a Node `signUp` via the anon key printing
  `session?`, `user?`, `error` for BOTH the RINA `company_name` meta shape and the
  SS Rover plain shape — adapt the fields to the two apps' metadata.)

### SPA approval gate — `approved` column + RPC + client gate (RINA, 2026-07-26)
When a Vite SPA already has multi-tenant auth (the pattern above) and you add an *admin-approval* step (new users can't enter until a Super Admin approves), do THREE coordinated things:

1. **DB**: `alter table user_profiles add column if not exists approved boolean not null default false;` `is_admin()` SECURITY DEFINER + `approve_user(target uuid, approve boolean)` SECURITY DEFINER (admin-only, `if not is_admin() then raise exception`). Signup trigger: first admin (company_name) → `approved=true`; member join / orphan → `approved=false`.
2. **RLS — THE TRAP**: if you harden `profiles_select` to `organization_id = my_org_id() and approved = true`, a PENDING user can no longer read their OWN row → client `fetchMyProfile()` returns null → they get bounced to Login instead of seeing "Awaiting approval." **Fix: the select policy MUST still let a user read their own row regardless of `approved`:** `using ( (organization_id = public.my_org_id() and approved = true) or id = auth.uid() )`. They still can't see anyone else; `tasks`/`audit` policies stay `approved=true` so pending users can't read company data.
3. **Client**: surface `approved` through the auth hook; in `App.tsx` gate `if (user.approved === false) return <AwaitingApproval/>` (with a logout). Add an admin-only "User Approvals" view that calls `supabase.rpc('approve_user', { target, approve })`.

- **Deploy the SQL via `supabase db push --linked`** into `supabase/migrations/` (not `db query`) — see `supabase-backend` P14/P15 for the migration-collision rule (the version key is the leading `YYYYMMDD`; same-day files collide, so use a distinct date).
- Verify the gate live with a signup probe, NOT a build. A `fetchMyProfile` returning null for a pending user is the symptom of the RLS trap above.

### Supabase free tier = 2 active projects/org + `projects create` CLI syntax (2026-07-26)
When the user wants to **separate two apps onto their own Supabase projects** (e.g. RINA
off the shared `rover-r-platform`), the blocker is the **free-tier cap of 2 ACTIVE projects per org**.
`supabase projects create` then fails with:
`The following organization members have reached their maximum limits for the number of active
free projects within organizations where they are an administrator or owner: <org> (2 project limit).`
**Fix before creating:** delete or pause one existing project to free the slot. The dead near-twin
(e.g. `eobkcsxwwpszyzbwpqqy`) is safe to drop; a user's REAL project is NOT — ask
explicitly before `supabase projects delete <ref> --yes` (irreversible).
**CLI syntax gotchas (both bit this session):**
- `supabase projects create` takes the name **positionally**, NOT `--name`:
  `supabase projects create <name> --org-id <ORG_ID> --region <REGION> --db-password <PW>`
- Region is the **full code**, not the short form: `ap-southeast-2` (Sydney), NOT `oc1`.
  A wrong region errors `Invalid value for flag --region: "oc1"`.
- Org ID comes from `supabase projects list` (the `ORG ID` column, e.g. `zhoagkgipvuehtagrpzg`).
See `references/supabase-project-cli.md` for the exact recipe + verification.

### "Confirm signups" is NOT in the Email provider panel (current Supabase UI)
A live session burned ~10 screenshots hunting for a "Confirm signups" toggle. On the current
Supabase dashboard it is **template-driven, not a master switch in Authentication → Sign In / Providers → Email**
(that panel's 9 settings stop at "Email OTP length" — the toggle is NOT there). Where it actually lives:
- **Authentication → Emails → Templates** → row **"Confirm sign up"** (*"Ask users to confirm their email
  address after signing up"*). Disabling that template is the lever — but on free tier without
  custom SMTP the templates are partly read-only, and the authoritative enforcement flag
  `mailer.autoconfirm` is **NOT editable via `supabase db query`** (`auth.config` relation "does not exist"
  through the query role) and is **hidden from this dashboard UI**.
- The ONLY way to truly flip it programmatically is the **Supabase Management REST API** with an
  **access token** (Settings → API → access token): `PUT /v1/auth/config` body `{"mailer_autoconfirm": true}`.
  The agent CANNOT do this without the user pasting a token.
**Definitive diagnosis = the live `signUp` probe, never the UI:** a fresh signup returning
`over_email_send_rate_limit` (429) PROVES Supabase is still attempting to send a confirmation email →
confirmation is ON (the rate-limit is just because repeated diag signups hit the send cap). When the probe
returns `session? true` with NO email-send attempt, confirmation is confirmed OFF. This is the proof — do NOT
trust a green build or a dashboard screenshot of the wrong panel.
**Practical unblock for testing:** if the confirm email was actually sent, just **click the link** (the app
says so: *"Check your email to confirm, then sign in"*). Email rate-limiting from diag scripts can
SILENTLY drop a real app's confirm email into the void — wait 15–30 min for the limit to clear, or
use the access-token flip. Turning confirmation OFF removes the dependency entirely.
### React data flow (the ordering trap)
- `useAuth()` returns `{ session, orgId, loading }` (`orgId` from the profile's
  `organization_id`). `App` is a thin shell: `if (auth.loading) spinner; if (!user) <Login/>;
  return <Workspace key={user.id + orgId} user orgId ... />`.
- **PITFALL — child effects run BEFORE parent effects.** If data hooks
  (`useUsers/useTasks/useAudit`) read the org from a module-global set inside `useAuth`'s
  effect, their own `useEffect(reload)` fires first (child-before-parent) and loads with a
  NULL org → empty data, never reloading. **Fix: pass `orgId` as a prop into each hook and make
  `reload` depend on `[orgId]`** (`useUsers(orgId)` → `useEffect(reload,[reload])`). The
  `key={user.id+orgId}` on Workspace also remounts on org change.
- **PITFALL — don't write a new record through a hook that captured the old array at mount.**
  `addUser`/`upsert` close over the hook's `useState` initializer; after the org flips that
  closure is stale. Make `upsertProfile` a true **upsert** (`supabase.from('user_profiles')
  .upsert(row, { onConflict: 'id' })`) so new ids INSERT and existing ids UPDATE — one path for
  "add member" and "edit role." Fixes the classic bug where "add user" silently did nothing
  because the handler only issued an UPDATE by id.
- `src/lib/supabase.ts` must be import-safe (see `vercel-prod-deploy-verification` env pitfall):
  export `SUPABASE_CONFIGURED = Boolean(url && anonKey)`; App shows a "Backend not configured"
  screen when false — never a blank crash.

See `references/multitenant-vite-supabase.md` for the concrete RINA schema + hook/Login diff map.
The Vercel `VITE_*` env gap (build green, runtime dead) is in `vercel-prod-deploy-verification`.

## Go-live pitfalls (real user gotchas)
These bit a live session — bake them in so the next one doesn't repeat them.

1. **Project-ref typo = SILENT failure (the #1 time-sink).** MARU's real ref is
   `eobkcsxwwpszyzbwpqqy` (note the `z`). A one-char drift (`eobkcsxwwpszybwpqqy`,
   missing `z`) makes `VITE_SUPABASE_URL` point at a project that does NOT exist ->
   `ENOTFOUND`, login hangs/fails, and a naive checker reports a FAKE failure. This
   exact typo was once misdiagnosed as a sandbox firewall block (Pitfall #5).
   - ALWAYS read the ref from the dashboard (General page "Project ID" field, or
     the API page which shows the full `https://<ref>.supabase.co` URL), and copy
     it verbatim. Never trust a hand-typed ref the user pasted — re-check it against
     the screenshot value, then DNS-verify before trusting it:
     `python3 -c "import socket; print(socket.gethostbyname('<ref>.supabase.co'))"`
     resolving to an IP = real ref; `gaierror` = typo.
2. **Don't derive the ref from the secret blob.** A Supabase `sb_secret_...` /
   `sb_publishable_...` value does NOT cleanly contain the project ref. Decoding the
   secret yields binary garbage (it's an encryption key, not a JWT). Do not guess the
   URL from it — that produces a wrong ref (this happened once). Use the dashboard.
3. **Key-type confusion is common — verify the prefix before writing.**
   - publishable / anon key -> goes into `VITE_SUPABASE_ANON_KEY`. It looks like
     `sb_publishable_<base64>` (newer) OR a long `eyJ...` JWT (older). Public by design.
   - service-role key -> `sb_secret_...`. Goes into a NON-`VITE_` var (e.g.
     `SUPABASE_SERVICE_ROLE_KEY`) so it never enters the browser bundle.
   - Users frequently paste the `sb_secret_...` and CALL it the publishable key.
     Read the prefix; if it's `sb_secret_`, correct them and store it off-bundle.
4. **Write .env with terminal, never read it with the file tool.** `read_file` on a
   secret-bearing `.env` is blocked by design. To set/verify keys without echoing
   secrets: `grep -q "^VITE_SUPABASE_URL=https" .env` or `sed -n 's/^VITE_SUPABASE_ANON_KEY=.\{12\}.*/\1.../p' .env`
   for a prefix-only view. Use python3 + `open()` for precise replacements.

5. **Agent sandbox CAN reach Supabase — verify the ref before blaming a block.** This
   skill once claimed the agent sandbox egress-blocks the whole `*.supabase.co` zone.
   That was WRONG and wasted a round-trip. Once the project ref in `.env` is correct,
   the agent terminal reaches `<ref>.supabase.co` directly (roundtrip ~400ms) and runs
   the live audit to 6/6 itself — no Mac needed. The earlier `ENOTFOUND` was purely a
   one-char ref typo (Pitfall #1), not a firewall.
   - DIAGNOSIS RECIPE (still tells block vs typo):
     `python3 -c "import socket; socket.gethostbyname('<ref>.supabase.co')"`
     `gaierror` on a ref you just copied from the dashboard = TYPO, not a sandbox
     block. Resolve the correct ref and retry from the agent. Only if it STILL fails
     from the agent after a verified-correct ref should you ask the user to run it on
     their Mac as a cross-check (`cd <project> && node live_audit.mjs`).
   - NEVER fabricate a live PASS. A buggy checker can mark a transport failure as PASS
     — guard with a transport-failure regex (as the script does).
   - GENERALIZE: this "don't trust a negative connection from the sandbox" rule applies to
     ANY external host the agent must reach to verify a live feed — e.g. AISStream's
     `stream.aisstream.io`. A sandbox `ENOTFOUND`/timeout there is NOT proof the API key is
     bad; verify DNS+TCP reachability or run the probe from the user's Mac before concluding
     the credentials are at fault.

6. **Supabase lowercases emails — match the STORED case or seeds silently no-op.**
   case-insensitive). A seed SQL `where email = 'AdminMARU@maru.app'` matches ZERO
   rows and promotes NOTHING — the profile stays `role=user, status=pending` and the
   audit fails with "Cannot coerce the result to a single JSON object" (`.single()`
   finds 0 rows). `listUsers()` matching has the same trap.
   - Seed/promote SQL and audit queries MUST use the LOWERCASED form
     (`adminmaru@maru.app`).
   - In audit JS, normalize before compare:
     `x.email.toLowerCase() === 'adminmaru@maru.app'`.
   - `scripts/live_audit.mjs` and `templates/schema.sql` seed steps already use the
     lowercased form — preserve it if you edit them.

7. **Email confirmation OFF is correct when the superadmin inbox is non-deliverable.**
   If the seeded superadmin email is a fake/non-receiving address (e.g. MARU's
   `adminmaru@maru.app`, a placeholder domain with no mailbox), leaving Supabase
   Authentication ▸ Providers ▸ Email ▸ "Confirm email" **OFF** is the right call — two
   facts make it so:
   - The superadmin was created with **Auto Confirm User** ticked, so its row is already
     `confirmed_email=yes` and logs in fine even with global confirmation off.
   - If confirmation were ON, any later password-reset / email-change would email a
     verification link to the dead address and **strand the account** (no way to receive it).
   Re-enable confirmation ONLY when public signup opens with real, deliverable inboxes +
   working Supabase SMTP. This is a deliberate, documented security decision — do NOT nag
   the user to turn it on, and record it in the vault as "intentionally OFF" with the reason,
   never as an unchecked gap. Password policy (min length + complexity) is still worth
   enabling independently under Authentication ▸ Attack Protection.

## Pitfall #8 — anon key truncated through chat paste (2026-07-26)
When the user pastes a Supabase **anon key** into chat, it frequently arrives
**truncated mid-signature** (only two `.`-segments, ends abruptly like
`...dIP9z9ZYs`). Reusing it yields a misleadingly GENERIC error:
`401 Invalid API key` from the live `signUp`/REST probe — NOT "key too short",
so it reads like a *wrong-project* problem when it's actually *incomplete paste*.
- A real anon JWT has ~200+ chars, THREE dot-separated parts
  (`eyJ…eyJ…<long signature>`), ending in a full signature, not a stub.
- **Fix / preferred path: do NOT round-trip the key through chat.** Have the user
  set `VITE_SUPABASE_ANON_KEY` **directly in Vercel** (Project → Settings →
  Env) by copy-pasting from the Supabase dashboard (Settings → API → anon public).
  No truncation in that path.
- If the user DOES paste it and the probe 401s, re-request the **complete**
  string (must have two dots + long tail) before debugging further.
- Same truncation trap applies to ANY long secret pasted into chat (service-role
  keys, Vercel tokens, SMTP_PASS). For those, prefer the user sets them in
  the dashboard/env directly, or the paste is verified complete.
- The session's reusable live probe (prints `session?`, `user?`, `error`) lives in
  the Multi-tenant section above — run it against the NEW project ref after separation
  to prove org+SuperAdmin profile are created, then clean up the test row.

## Confirm-signups dashboard maze — consolidated reference
The "turn off email confirmation" hunt burned ~10 screenshots because the toggle
is **template-driven, hidden from the obvious panel, and the authoritative flag is
unreachable from this agent**. See `references/confirm-signups-dashboard.md` for the
exact nav + the definitive `signUp`-probe diagnosis + the Management-API flip.

## Next.js App Router approval gate (ss-rover-cloud, 2026-07-26)
When the app is **Next.js (App Router) with `middleware.ts`** (not a Vite SPA), the
gate lives at the edge, not in a React `<AuthGate>`. The hole the user hit:
"`middleware` + the upload Edge Function only checked `supabase.auth.getUser()`
(authenticated), so ANY confirmed email = instant full access." Fix = add an
`approved` flag + admin-only approval, enforced in BOTH places.

### Schema (idempotent migration, same patterns as above)
- `alter table profiles add column if not exists approved boolean not null default false;`
- Backfill: `update profiles set approved=true where id in (select id from auth.users
  where email in ('you@x.com'))` + bootstrap `where (select count(*) from profiles)=1`.
- `is_admin()` SECURITY DEFINER (no RLS recursion — same trap as `is_superadmin()`):
  `select exists(select 1 from profiles p join auth.users u on u.id=p.id
   where p.id=auth.uid() and u.email in ('you@x.com'))`.
- `handle_new_user()` trigger: auto-approve admin emails + first user, else `approved=false`.
- `approve_user(target uuid)` SECURITY DEFINER; `if not is_admin() then raise exception 'Forbidden'`.
  `grant execute on function approve_user(uuid) to authenticated;`
- RLS: `profiles_select_own` → `using (auth.uid()=id OR public.is_admin())`;
  add `profiles_admin_update` `for update using (public.is_admin()) with check (public.is_admin())`.
- **Grant the helper too:** `grant execute on function is_admin() to authenticated;` —
  Next client calls `supabase.rpc('is_admin')` to show/hide the admin link; without the grant
  it 403s. The trigger's `handle_new_user` is SECURITY DEFINER so it needs no grant.

### Middleware edge gate (`src/middleware.ts`)
After `getUser()`, for any NON-public path, fetch the flag and redirect:
```ts
if (user && !isPublic) {
  const { data: prof } = await supabase
    .from("profiles").select("approved").eq("id", user.id).single();
  if (!prof?.approved) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("reason", "pending");
    return NextResponse.redirect(url);
  }
}
```
This blocks ALL protected routes (dashboard, project, everything) before any page/function runs.
`isPublic` = `/`, `/login`, `/share`, `/auth` (so the pending message can render).

### Middleware must PRESERVE THE DESTINATION and bounce signed-in users off `/login`
A bare `url.pathname = "/login"` throws away where the user was going — they deep-link
to a project, sign in, and land on `/dashboard`, then have to navigate back by hand.
Every redirect to `/login` must carry `?next=`:
```ts
if (!user && !isPublic) {
  const url = request.nextUrl.clone();
  const wanted = path + (request.nextUrl.search || "");   // keep the query too
  url.pathname = "/login";
  url.search = "";                                          // wipe stale params
  url.searchParams.set("next", wanted);
  return NextResponse.redirect(url);
}

// Already signed in + approved? /login is pointless — send them into the app.
if (user && path.startsWith("/login")) {
  const { data: prof } = await supabase
    .from("profiles").select("approved").eq("id", user.id).single();
  if (prof?.approved) {
    const url = request.nextUrl.clone();
    const nextParam = request.nextUrl.searchParams.get("next");
    url.pathname = nextParam && nextParam.startsWith("/") ? nextParam.split("?")[0] : "/dashboard";
    url.search = nextParam && nextParam.includes("?") ? "?" + nextParam.split("?")[1] : "";
    return NextResponse.redirect(url);
  }
}
```
- **Reset `url.search = ""` before setting a param** — `nextUrl.clone()` carries the
  ORIGINAL query, so a stale `?reason=pending` survives and stacks with the new param.
- **The login page must honour it, and GUARD against open redirect.**
  `const redirectTo = nextParam && nextParam.startsWith("/") && !nextParam.startsWith("//") ? nextParam : "/dashboard"`.
  Without the `//` check, `?next=//evil.com` is a protocol-relative redirect off-site.
- Prefer `/dashboard` as the link target everywhere (marketing CTAs, cross-product
  links) rather than `/login`: the middleware turns it into `login?next=/dashboard`
  when signed out and straight into the app when signed in — one link, both cases.
- Verify with curl (no session needed):
  `curl -s -o /dev/null -w "%{redirect_url}" https://<domain>/project/abc` →
  expect `.../login?next=%2Fproject%2Fabc`; `/admin?tab=x` → `next=%2Fadmin%3Ftab%3Dx`
  (proves the query string survived the encoding round-trip).

### Defense-in-depth on the upload Edge Function (`supabase/functions/r2-presign`)
Don't trust the middleware alone — also reject at the function after `getUser()`:
```ts
const { data: prof } = await supabase.from("profiles").select("approved").eq("id", user.id).single();
if (!prof?.approved) return json({ error: "Account pending approval" }, 403);
```
Then `supabase functions deploy r2-presign` (it's a Deno function, NOT part of `npm run build` — easy to forget).

### Login pending banner (`src/app/login/page.tsx`)
`"use client"` + `useSearchParams()` requires a **`<Suspense>` boundary** or the
Next build fails prerendering `/login` with `useSearchParams() should be wrapped in a
suspense boundary`. Two fixes:
- **PITFALL (chose this):** split into `<LoginForm>` (holds the hooks that call
  `useSearchParams`) and a default-export `<LoginPage>` that renders
  `<Suspense fallback={...}><LoginForm/></Suspense>`. Don't bother with
  `export const dynamic="force-dynamic"` — on a `"use client"` page that does NOT satisfy
  the Suspense requirement and the build still errors. (This session: `force-dynamic`
  was tried first and did NOT fix it — the hook MUST sit below a Suspense
  boundary, which only the split achieves.)
- The `?reason=pending` banner: amber "Your account is awaiting approval from the
  administrator." Signup handler pushes `/login?reason=pending` (NOT `/dashboard`)
  so pending users land on the message, never inside the app.

### Admin approval UI
- New route `src/app/admin/page.tsx` (server/client): lists pending + approved
  (`select id,full_name,role,approved,created_at` — RLS lets admin see all via
  `is_admin()` in the policy). Approve button → `supabase.rpc('approve_user',{target:id})`.
- Dashboard shows a "User Approvals" link ONLY when `supabase.rpc('is_admin')` is true
  (don't show the link to non-admins even though RLS would block the page anyway).
- Admin identity is hardcoded in SQL (`email in (...)` in `is_admin` + the trigger's
  `when new.email in (...)`). To add/change an admin, edit BOTH spots + re-apply the migration.
- Safety net: first-ever user auto-admin as a safety net.

### PITFALL — hardcoded admin email typo locks the FOUNDER out, silently
This bit a live session (SS Rover, 2026-07-26): the SQL hardcodes
`innovatedmaru@gmail.com` (with an **O**) but the founder's real account is
`inventedmaru@gmail.com` (with an **E**). Mismatch → `is_admin()` =
false AND the backfill/trigger never auto-approves that row → founder is
stuck on "awaiting approval" **forever, with no error anywhere** (signup
succeeds, login just bounces to the pending screen). RINA did NOT hit this
because its "New company" path makes *whoever creates the company* the
SuperAdmin — no hardcoded email. That model is more robust; prefer it.
- **Verify the admin email against the ACTUAL `auth.users` row, never memory:**
  `select email from auth.users order by created_at desc limit 5;` and copy the
  real string verbatim. One-char drift (`o`↔`e`, `.com`↔`.app`) is
  invisible in a screenshot and fatal.
- **After any admin-email change, re-apply the migration AND backfill the
  existing row.** The trigger only fires on NEW signups, so an already-created
  admin row stays `approved=false` until you
  `update profiles set approved=true where email='<exact real email>';`
  (or re-run the backfill `where email in (...)`). This session: fixing the typo
  in SQL then re-applying flipped the existing founder row to approved — that's the
  actual unblock, not just the code edit.
- **The tell:** signup probe returns `user? true, error:none` but the user
  can NEVER log in / is always "pending". That's an approval-flag or
  admin-identity mismatch, NOT a signup failure. Diagnose with the signup probe
  (above) + `select email, approved, is_admin() from profiles…`.
- **`is_admin()` returns false when you run it as the linked OWNER** (postgres),
  because `auth.uid()` is NULL in that context. To check it for the real user,
  simulate: `where u2.id = (select id from auth.users where email='<real>')` —
  don't trust the owner-context `is_admin()` result as "not admin."
- Prefer the RINA model (company creator = admin) unless the user explicitly
  wants a fixed super-admin identity. If you do hardcode, treat that email as a
  high-risk literal and verify it against `auth.users` every time.

## Email admin on every new signup (Supabase trigger → Edge Function → Gmail SMTP)
User asked: "email me every time a new user applies for sign up." Pattern that works
on the free tier without a mail-service account:

### Edge Function `supabase/functions/notify-admin/index.ts` (Deno)
- `import { serve } from "https://deno.land/std@0.168.0/http/server.ts";`
  `import * as nodemailer from "npm:nodemailer@6.9.1";`
- Read creds from Supabase **secrets** (never code): `Deno.env.get("SMTP_USER")`,
  `Deno.env.get("SMTP_PASS")`. If missing → `return new Response("SMTP secrets not set",{status:500})`.
- `nodemailer.createTransport({ host:"smtp.gmail.com", port:465, secure:true,
  auth:{ user, pass } })` then `transporter.sendMail({ from, to: ADMIN_EMAIL,
  subject, text })`. `ADMIN_EMAIL` is a hardcoded constant (e.g. "you@gmail.com").
- The function does NO auth check and NO DB read → it's safe to make **public**.
- LSP errors on `Deno`/`npm:`/`serve` are EXPECTED in a tsc-driven repo (the file is
  Deno); `supabase functions deploy` bundles for Deno and they don't block. Ignore them.

### Trigger that calls it (`supabase/phase2b_notify.sql`)
```sql
create or replace function public.notify_admin_on_signup()
returns trigger language plpgsql security definer set search_path = public as $$
declare
  proj_ref text := 'YOUR_PROJECT_REF';
  edge_url text; payload jsonb;
begin
  edge_url := 'https://' || proj_ref || '.supabase.co/functions/v1/notify-admin';
  payload := jsonb_build_object('email', coalesce(new.email,''),
                                'name', coalesce(new.raw_user_meta_data->>'full_name',''));
  perform net.http_post(url:=edge_url,
    headers:=jsonb_build_object('Content-Type','application/json'),
    body:=payload::text);
  return new;
exception when others then return new;   -- NEVER block signup if notify fails
end; $$;
drop trigger if exists on_auth_user_notify on auth.users;
create trigger on_auth_user_notify after insert on auth.users
  for each row execute function public.notify_admin_on_signup();
```
- `net.http_post` is Supabase's built-in HTTP client (enabled by default). 
- **Do NOT put an `apikey` header** unless `app.settings.supabase_anon_key` is set —
  it is FALSE by default (`select current_setting('app.settings.supabase_anon_key',true) is not null`
  → false). Either set that setting OR (chosen path) make the function public with
  `supabase functions deploy notify-admin --no-verify-jwt` and send NO apikey header. The
  trigger above uses the no-key path.
- `exception when others then return new` is critical: if the email send fails, signup must
  still succeed. Without it the trigger would abort the `auth.users` insert.

### Secrets (you need the Gmail app password from the user)
- `supabase secrets set SMTP_USER=you@gmail.com` (safe, it's their known email).
- `SMTP_PASS` = a **Gmail app password** (16 chars, generated at
  myaccount.google.com → Security → App passwords; needs 2-Step Verification on).
  It is NOT the normal Gmail password. The agent CANNOT fetch it — must ask the user.
- The function returns 500 ("SMTP secrets not set") until `SMTP_PASS` exists; the trigger's
  exception handler swallows it so signup still works. Verify end-to-end only AFTER the
  user supplies the app password: set it, then do a throwaway signup and confirm the
  email lands.

## Forgot / reset password (Supabase native — Vite SPA + Vercel)
Supabase handles password reset natively via `resetPasswordForEmail` + the
`PASSWORD_RECOVERY` session event. Pattern (shipped RINA 2026-08-17, commit `213bb8d`):
- API (`lib/api.ts`): `resetPassword(email, redirectTo)` →
  `supabase.auth.resetPasswordForEmail(email, { redirectTo })` (redirectTo =
  `window.location.origin` so the reset link returns to the app); and
  `updatePassword(newPw)` → `supabase.auth.updateUser({ password: newPw })`.
  Both return `error?.message` (or null) instead of throwing.
- Detect recovery: `onAuthChange(cb)` now passes the **event** as a 2nd arg. In the
  `useAuth` hook, set `recovery = (event === 'PASSWORD_RECOVERY')`. Expose `recovery`.
- Render: when `recovery` is true, `App` shows the Login component in "set new
  password" mode (a password field + `updatePassword`), NOT the company picker.
  On success call `auth.logout()` so the user signs in with the new password.
- `forgotOpen` toggle on the sign-in form: email field → `resetPassword` →
  generic "if that email is registered, a link has been sent" (don't leak which
  emails exist).
- **Env/email config is the real gotcha** — the code path is trivial; the email
  actually sending depends on Supabase SMTP / email-provider setup and can land in
  spam. Verify the live round-trip with a real inbox; can't be proven from the agent.
  See Pitfall #7 re: confirmation OFF + non-deliverable admin inbox.

## PITFALL — the approver/admin must BYPASS the gates they administer
If an admin/approver (platform admin, superadmin) is also a *member* of an org whose
`approved=false` (or is paused), the very approval gate they operate will lock THEM
out ("Company registration pending") — because they created/own a company that was
never approved. A platform admin who approves companies must never be blocked by the
approval/pause/member gates. **Rule: every gate condition in `App.tsx` must carry
`&& !platformAdmin` (or the admin equivalent):**
- Tier-1 org-approval: `if (orgId && !orgApproved && !platformAdmin)`
- Paused: `if (orgId && orgPaused && !platformAdmin)`
- Tier-2 member-approval: `if (user.approved === false && !platformAdmin)`
This bit RINA live (2026-08-17, commit `f022ad1`): inventedmaru (Master Admin) logged
in and landed on "Company registration pending" because their own company was
`approved=false`. The fix was adding `!platformAdmin` to all three gates. Any NEW gate
added to such an app must carry the admin exemption or the admin gets stuck.

## See also
- `frontend:vite-build-verification` — build-green hides runtime `ReferenceError`s (Pitfall 6/6b/6c); verify the page loads.
- `software-development:systematic-debugging` — root-cause before any fix, including "the app is insecure" class bugs.
