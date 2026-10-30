# Go-live: 3 steps after the auth code is written

The auth layer is built and verified (lint 0 errors, build green) but runs in DEMO
MODE until Supabase keys exist. To make it live:

## Step 0 — Confirm the project ref (avoids silent failure)
- In the Supabase dashboard, open **Settings ▸ General**. The **Project ID** field
  (and the URL bar `…/project/<ref>/…`) show the authoritative ref, e.g.
  `eobkcsxwwpszybwpqqy`. Copy it verbatim.
- WARNING: Do NOT trust a hand-typed ref — a single stray char makes the client
  connect to a nonexistent project with no build error. If the user dictates a ref,
  re-verify it against this screen (or a screenshot) before writing `.env`.
- The Project URL will be `https://<ref>.supabase.co`. Paste this verbatim.

## Step 1 — Create a Supabase project
- Go to supabase.com → New project (free tier is fine to start).
- Note the **Project URL** and **anon public key** (Project Settings ▸ API).
  These are safe to share — public by design.
- Identify the keys by prefix, not by the user's label:
  - **Publishable / anon key** -> `VITE_SUPABASE_ANON_KEY`. Looks like
    `sb_publishable_<base64>` (newer) or a long `eyJ...` JWT (older).
  - **Secret / service-role key** -> `sb_secret_...`. NEVER into a `VITE_` var;
    store as `SUPABASE_SERVICE_ROLE_KEY` (off-bundle). Users often paste this one
    when asked for "publishable" — read the prefix and correct them.

## Step 2 — Run the schema + seed superadmin
- Open Supabase SQL Editor (Dashboard ▸ SQL ▸ New query).
- Paste `templates/schema.sql` (from this skill) and run it.
- Authentication ▸ Add user: Email `AdminMARU@maru.app`, Password = the strong one in
  your private vault note, "Auto Confirm" ON.
- In the SQL editor, run the seed block at the bottom of schema.sql:
  `update public.profiles set role='superadmin', status='approved' where email='AdminMARU@maru.app';`

## Step 3 — Add keys to .env (gitignored)
Add to the project `.env` (never commit it):
```
VITE_SUPABASE_URL=https://xxxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...public-anon-key
```
- Restart the dev server (`npm run dev`) so Vite picks up the new env.
- Refresh localhost:5175 → login as AdminMARU → visit `localhost:5175/#admin` to approve users.

## Optional hardening (recommended before any real traffic)
- Enable email confirmation (Authentication ▸ Providers ▸ Email → Confirmations) to block typo/fake emails.
- Set a password policy (min length 8+, complexity) in Authentication settings.
- Put Cloudflare in front (free tier includes basic DDoS shielding) for serious traffic.
- Keep the **service-role key** secret — backend/env only, never the browser bundle.

## Verification after go-live
Run the 4 live audit tests from references/audit.md (RLS bypass, brute-force lockout,
session expiry, HTTPS). The 4 static tests already PASS from the code build.
