# Confirming which live Supabase project a deployment reads + delivering the DB fix cleanly

Session context: RINA (multi-tenant Supabase SaaS, React 19 + Vite). Two Vercel
projects / renamed+renamed domains for the same repo; user logged in but saw an
empty UI after creating a company. This file captures two reusable techniques.

## 1) Bundle-sniffing: which Supabase project does the live app really use?

The app's connection is the `VITE_SUPABASE_URL` env var **compiled into the built
JS bundle**. `vercel ls` may be absent (CLI not installed) and project names lie
(renames/pauses don't move data). Definitive check:

```bash
# get the hashed bundle filename from the live HTML shell
JS=$(curl -s <LIVE_URL> | grep -oE 'assets/index-[A-Za-z0-9_-]+\.js' | head -1)
echo "bundle: $JS"
# grep the compiled Supabase URL out of it
curl -s "<LIVE_URL>/$JS" | grep -oE 'https://[a-z0-9]+\.supabase\.co' | sort -u
```

A hit like `https://joliwavzczzfiwpwrbtf.supabase.co` proves the live app reads that
project. Compare two domains side-by-side to confirm they share (or diverge from) one DB.

### Caveats that fool people (verified this session)
- **Paused Vercel project still returns HTTP 200** and serves the last build —
  pausing changes nothing about which DB it reads. Renaming a project / changing a
  domain does NOT touch Supabase data either. So "which project has the latest data"
  is usually the wrong axis: data lives in Supabase, not Vercel.
- An old project name often becomes a **302 redirect** to the new domain (e.g.
  `riina-eight.vercel.app` → `rina-m.vercel.app`), returning a bare "Redirecting..."
  HTML shell. Use `curl -L` to follow it.
- `.vercel.app` is a **global namespace** shared by every user. A slug like
  `rina.vercel.app` may belong to an unrelated THIRD PARTY (in this session it was an
  unrelated "Rina Luxuries" Vue/Vuetify site). Never enter credentials on a domain you
  didn't verify; use the exact domain the user confirms (e.g. `rina-m.vercel.app`).

## 2) Delivering the live-DB fix (user workflow preference)

The agent cannot run DDL against the live Supabase project (no DB credentials, only the
public anon key which cannot alter functions). DDL must be handed to the user to paste
into the Supabase SQL Editor. Two things make this painless:

- **Write ONE clean, self-contained, idempotent SQL file** (e.g. `~/Desktop/<name>_fix.sql`)
  instead of dropping several inline code blocks across chat messages. The user asked
  explicitly: "write a clean SQL file in file on my desktop so i will not paste rubbish."
- Order statements top-to-bottom so it runs clean in a single paste: approve stuck rows
  first, then `create or replace` the helper function(s), then the RLS policy rewrites.
- Every statement idempotent (`create or replace`, `drop policy if exists`) so re-running
  is safe. When a name in the SQL must match user-entered data (e.g. a company name),
  call it out clearly: `update ... where name = 'LunaV Solutions'; -- change if needed`.
- After they run it, the app needs a **Refresh / re-login** — the client caches the
  profile list, so a stale empty OrgHome persists until refreshed.

## The actual RINA fix that unblocked the empty UI (for reference)

Two independent bugs produced "created a company but can't get in" + "returns nothing":
1. `create_org(name)` RPC inserted the org with `approved=false` (default) → the Tier-1
   gate in App.tsx blocked the founder with "Company registration pending" and there was
   NO self-approve path. Fix: insert `approved=true` (creator IS the SuperAdmin).
   (This exact bug is documented as PITFALL #8 in the parent SKILL.md.)
2. The `profiles_select`/`orgs_*`/`tasks_all`/`audit_all` policies used **inline
   self-referencing subqueries** (`organization_id in (select organization_id from
   public.user_profiles where id = auth.uid() ...)`) → Postgres raised
   `infinite recursion detected in policy for relation "user_profiles"` (42P17) on any
   authenticated `user_profiles` read → `fetchMyProfiles` errored → app showed nothing.
   Fix: route every policy through the **SECURITY DEFINER `my_org_ids()`** helper
   (set-returning, `returns setof uuid`, `set search_path = public`), writing policies as
   `id = auth.uid() or organization_id in (select public.my_org_ids())`. Inline subqueries
   on the same table are the anti-pattern. (This is PITFALL #1 in the parent SKILL.md.)
