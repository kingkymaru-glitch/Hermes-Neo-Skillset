---
name: supabase-free-tier-bootstrap
description: Set up, wire, and debug a Supabase project (esp free tier) for a test app. Covers create project, apply schema, app env vars, and the recurring killers email-confirmation-default-ON, RLS helper recursion 54001, publishable-key retrieval, db-query owner-bypass, 2-project free-tier limit. Trigger when standing up or debugging any Supabase-backed Vite or Next app.
---

# Supabase Free-Tier Project Bootstrap & Debug

Use for: creating a Supabase project (free tier) for a test app, applying schema,
wiring a Vite/Next client, or debugging "signup works but no session / stuck on
login / blank app / 54001 stack depth" on a Supabase app.

## Trigger-to-action
- New isolated app needed (user "separate it / fresh project") -> CREATE a new project.
- App blank with `supabaseUrl is required` / `Missing VITE_SUPABASE_URL` -> env vars missing (see App env).
- User registers but stuck at "check your email" / "awaiting approval" / no session -> email confirmation is ON (see Pitfalls).
- Authenticated query errors `54001 stack depth limit exceeded` -> RLS recursion (see Pitfalls).

## Steps
1. Create project (CLI):
   `supabase projects create <name> --org-id <orgid> --region <region> --db-password <pw> --yes`
   - Region is POSITIONAL, codes like `ap-southeast-2` (Sydney), `us-east-1`. NOT `oc1`.
   - List orgs/refs: `supabase projects list`.
   - DB password: `openssl rand -base64 18 | tr -d '/+=' | head -c 24`.
   - Account switching: `yes | supabase logout`, then `supabase login --token <access-token>`.
     In non-TTY (agent sessions), `supabase login` alone fails: "Cannot use automatic login
     flow inside non-TTY environments." Always pass `--token`. Get tokens from
     https://supabase.com/dashboard/account/tokens.
2. Free-tier limit = 2 active projects per org. If blocked, delete/pause a dead twin
   (`supabase projects delete <ref> --yes`) — CONFIRM with user first (irreversible). A near-twin
   project with a similar ref is usually the safe one to drop.
   - **Auto-pause (verified):** a FREE project is auto-paused after **1 week of inactivity** —
     the DB disconnects and any client (app or sibling app) gets connection errors until you
     unpause it in the dashboard (Project → Settings → General → "Restore project" / pause toggle).
     For an app used only occasionally (e.g. at gatherings), this is real friction: either warn the
     user to unpause before use, or note Pro removes the pause. Don't present a free project as
     "always on."
   - **Reuse-an-existing-project instead of separating (counter-pattern to the "separate them"
     pitfall below):** when you're already AT the 2-project cap and the new app's schema is
     self-contained (its own tables + RPCs with no name clash), DROP it into an existing project
     rather than creating a 3rd. Steps: (1) grep both schemas for `create table` names to prove
     zero collision; (2) run the new app's schema.sql in that project's SQL Editor; (3) point the
     new app's client at the SAME `VITE_SUPABASE_URL`/publishable key the existing app uses. This
     keeps you inside the free cap. Caveat: the 1-week auto-pause then affects BOTH apps, and
     Storage buckets are shared (prefix new objects, e.g. `skins/`, `skypins/`).
3. Link + apply schema:
   `supabase link --project-ref <ref>`
   `supabase db query --linked --file schema.sql`
4. App env (Vite): `VITE_SUPABASE_URL=https://<ref>.supabase.co`,
   `VITE_SUPABASE_ANON_KEY=<Publishable key>`. For deployed (Vercel): set these in
   Project -> Settings -> Env, then REDEPLOY. Missing vars -> client throws at import -> blank crash.
5. Turn OFF email confirmation for testing BEFORE asking the user to register (see Pitfalls).

## Pitfalls (the recurring killers)
- Email confirmation default ON -> `signUp` returns `user` but `session:false`;
  app shows "check your email" or (if approval-gated) "awaiting approval" forever.
  Modern Supabase has NO master "Confirm signups" toggle in the dashboard — it's
  TEMPLATE-based. Path: Authentication -> Emails -> Templates -> "Confirm sign up" -> disable.
  (Older/other versions: set `mailer.autoconfirm` — not exposed in dashboard UI on newer
  versions; needs Management API token.) Symptom of still-ON: live `signUp` returns
  `over_email_send_rate_limit` (429) -> throttle blocks the confirm email -> signup silently fails.
- Anon key renamed to "Publishable key" (`sb_publishable_...`), under
  Settings -> API -> "Publishable and secret API keys" tab. NOT the masked "Secret key".
  Pasting long JWTs through chat TRUNCATES them (chat cuts the signature tail) ->
  `401 Invalid API key`. Fix: set Vercel env directly from clipboard (the copy button
  gives the FULL key; the display is truncated with `…`), or save the key to a file the
  agent reads. Never hand-type a JWT.
- **Vercel env var visibility:** `NEXT_PUBLIC_*` variables MUST use `visibility: config`, not `secret`. If Vercel complains on save, look for the Visibility field in the env var form and switch it. `service_role` must remain `secret` and must never be added to Vercel client-side env vars.
- RLS helper recursion (54001 "stack depth limit exceeded"): a function that queries a
  table whose RLS policy calls that same function -> infinite recursion on any authenticated
  query. Fix: make the helper `security definer` so it runs as table owner and bypasses RLS
  (no re-entry). Example:
  ```sql
  create or replace function public.my_org_id()
  returns uuid language sql stable security definer set search_path = public as $$
    select organization_id from public.user_profiles where id = auth.uid();
  $$;
  ```
- `supabase db query --linked` runs as the project OWNER -> bypasses RLS. You CANNOT
  verify RLS enforcement through it (owner ignores policies). To test RLS, use a real
  authenticated JWT. `auth.config` is NOT writable via the query role
  (`relation "auth.config" does not exist`). `current_setting('app.settings.supabase_anon_key', true)`
  is often NULL.
- **Test-user cleanup: do NOT use the JS client's `supabase.auth.admin.deleteUser` from a
  linked/script context** — it needs a service_role Bearer token and fails "This endpoint
  requires a valid Bearer token". Delete orphaned auth rows via SQL instead:
  `supabase db query --linked --file` running `delete from auth.users where email like '%+tag%'`
  (plus the matching profile/org rows). Use the owner role, not the publishable client.
- **Don't trust a CHAINED `select` right after `signUp` to confirm the trigger fired.**
  `signUp` resolves, but the AFTER-INSERT trigger's profile insert may not be visible in
  the same script's immediate follow-up `select` (returns null even though the row exists).
  Verify the trigger independently: a separate `supabase db query --linked` run
  (`select count(*) from public.user_profiles`) or re-query in a fresh process. The DB
  state is the source of truth, not the script's return value.
- **Copy the publishable key with the dashboard COPY ICON, not manual select.** The API
  Keys screen shows the key truncated with `…` in the input box; manual select-copy grabs
  only the truncated fragment -> pasted into chat/Vercel it 401s ("Invalid API key", only
  2 segments). The copy button yields the FULL `sb_publishable_…` token. If pasting through
  chat, the key keeps arriving truncated — set Vercel env directly from clipboard, or save
  to a file the agent reads.
- **Symptom: "Signed in. Loading your company…" (post-login spinner that never resolves).**
  Session exists but there is NO `user_profiles` row for that user -> app can't resolve a
  company -> hangs. Common cause: the account was created on a DIFFERENT/shared Supabase
  project than the client is wired to (e.g. two apps sharing one project; the RINA client
  pointed at SSR's project, so RINA's profile lived on SSR's side). Fix: point the client's
  `VITE_SUPABASE_URL`/anon key at the SAME project that holds the profile, or create the
  profile/org for that user.
- **Two apps sharing one Supabase project -> separate them:** create a NEW project
  (`supabase projects create …`), `supabase link --project-ref <new>`, re-apply `schema.sql`,
  then point the app's env (local `.env.local` + Vercel) at the new ref + publishable key,
  redeploy, and confirm the live bundle no longer references the OLD ref (`curl` bundle,
  grep for old ref = 0, new ref = 1). Free-tier limit (2 projects/org) means you must delete
  a dead twin first (confirm with user — irreversible). After separation, email-confirmation
  is a PER-PROJECT setting, so flip it independently on the new project.
- Next.js build: `useSearchParams()` needs a `<Suspense>` boundary or
  `export const dynamic = "force-dynamic"`, else prerender fails with
  "useSearchParams() should be wrapped in a suspense boundary". Split page into
  `<Suspense><Inner/></Suspense>`.
- `npm run build` (rolldown) may emit chunk-size warnings (cosmetic) but exit 0 — not an error.

- **Reuse a sibling project's publishable key from its local `.env` (no paste, no truncation):**
  when the agent machine already has a DIFFERENT app (e.g. `~/riina`) wired to the SAME target
  Supabase project, the key is in that app's `.env.local` as `VITE_SUPABASE_ANON_KEY=` (client-safe,
  publishable). Extract it via terminal and patch the new app's config WITHOUT echoing it into chat:
  ```bash
  KEY=$(grep -E "^VITE_SUPABASE_ANON_KEY=" ~/riina/.env.local | cut -d= -f2-)
  # substitute into the new app's config (sed / patch) — never `echo $KEY`
  ```
  File-read tools may BLOCK `.env*` (secret-bearing) — use `grep`/`cut` in terminal, not read_file.
  This beats asking the user to copy-paste (avoids the chat-truncation 401) and keeps the secret
  out of the transcript. Works only when both apps share a machine + project; otherwise fall back
  to the dashboard Copy-icon rule above.
- **Two apps sharing one Supabase project -> you may WANT to keep them shared** (inverse of the
  "separate them" advice): if the new app is a small companion (e.g. an AR viewer reusing the same
  GPS tables), reuse is cheaper than a 3rd project. Use the reuse counter-pattern in Step 2; only
  SEPARATE when schemas conflict or you need per-app auth/email settings.

## Verification
- Live signup test: node script with `@supabase/supabase-js` + anon key ->
  `supabase.auth.signUp({email, password, options:{data:{...}}})`; assert `user? true` and
  (first-admin flow) that the trigger created the org + profile via a follow-up `select`.
  `over_email_send_rate_limit` = confirmation still ON.
- Deploy check: `curl` the live bundle, grep for the project ref (env baked in) and
  absence of `placeholder.supabase.co` (not the placeholder client).

## Migration pattern: replacing legacy `/api/*` routes with direct Supabase
- When removing a server route, grep the entire `src/` for the old path string
  (e.g. `/api/nodes`) BEFORE deploy. Leftover fetch calls hit 404 on Vercel, which
  serves SPA fallback only.
- Prefer context-level helpers (`loadXFromCloud`, `addX`, `updateX`, `removeX`) that
  update local state optimistically and reconcile after. Components should call those
  helpers, not raw fetch.
- If you alias context exports for clarity (`addNode: addNodeFromCloud`), update ALL
  call sites consistently. A single leftover unaliased call can resolve to a stale
  local updater instead of the cloud function.

## Field-mapping guard
- Before saving from client to Supabase, verify the object keys match the table schema
  EXACTLY. Common mismatch: `url` vs `model_url`, `latitude`/`longitude` vs `lat`/`lon`.
  Build can pass while data lands in wrong columns or is rejected at runtime.
- Fix pattern: `saveGlbModelToCloud({ ...row, model_url: model.url, lat: model.latitude, lon: model.longitude })`.

## Component undefined-variable audits
- When fixing a missing context prop in one component (e.g. `glbCloudStatus`), grep
  the component folder for any other destructuring of the same context object to avoid
  shipping one fix while another component still crashes.
- Fallback pattern: `const { status } = useContext(MyContext); const safe = status || 'idle';`.

## Execution note (this user)
When the setup path is clear from context, EXECUTE directly — don't ask A/B questions
("should I do X or Y?"). Reserve clarify() for genuine ambiguity (e.g. which admin
email). The user gives terse directives ("create everything new, separate it"); act on them.
