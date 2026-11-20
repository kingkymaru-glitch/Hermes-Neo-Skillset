# Vercel deploy does NOT apply Supabase migrations

## The trap
A Supabase + Next.js project on Vercel can carry fix-migrations in
`supabase/migrations/` (e.g. `20260801_fix_markers_rpc.sql`) that are
**never run against the live database**, because `vercel build` only builds
the app — it does NOT execute `supabase db push` or `supabase migration up`.
The SQL functions / columns the frontend now depends on therefore don't exist
in prod, even though the repo is "correct" and the local build is green.

Symptom signature: the frontend code reads the right fields, the **local**
schema/migrations define them, but the **live** RPC returns `null`/missing
columns for those fields → e.g. a client share link shows no markers/evidence
despite correct UI wiring. This is a DB/schema mismatch, not a React bug.

## Verify the hypothesis fast
1. Read `supabase/migrations/*.sql` and `supabase/schema.sql` for the function
   / columns the UI expects (e.g. `get_shared_project` returning
   `kind`, `geometry_json`, `photos_json` on `models[].markers`).
2. Confirm the function is actually defined that way LIVE:
   - No `supabase/config.toml` / project not linked ⇒ no CLI `db push`.
   - `.env.local` has only the anon key, no DB/pooler string or access token
     ⇒ the agent cannot apply migrations itself.
3. User confirms by running the SQL in the Supabase Dashboard SQL Editor
   (project → SQL Editor → New query → Run) for the live ref.
   Then spot-check with a `SELECT` against the live table:
   ```sql
   select k.id, k.kind, k.photos_json
   from markers k
   where k.photos_json is not null limit 5;
   ```

## Idempotent live-fix SQL pattern
Hand the user a SINGLE self-contained, re-runnable SQL file that
recreates the function/columns. Use `CREATE OR REPLACE FUNCTION ...`,
`ADD COLUMN IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, and a `DO $$`
block to make an existing column `NOT NULL` only if it is currently nullable
(after backfilling). Example shape (the actual columns/fields come from the
repo's own migrations — copy them verbatim so the live function matches
`schema.sql`):

```sql
-- combine the repo's relevant fix-migrations into one idempotent file
create or replace function public.get_shared_project(share_token uuid)
returns jsonb language sql security definer set search_path = public stable
as $$ select jsonb_build_object( /* ... mirror schema.sql exactly ... */ ) $$;
grant execute on function public.get_shared_project(uuid) to anon, authenticated;
```

Save this combined file as a new migration
(`supabase/migrations/YYYYMMDD_apply_live_<bug>_fix.sql`) so it is also
documented in-repo and can be replayed via `supabase db push` once linked.

## End-to-end verification checklist (after the fix)
For "data missing in client view" bugs, verify ALL of:
1. **Type boundary** — the TS type (e.g. `Marker` in `src/lib/types.ts`)
   declares the fields; `SharedProjectBundle` carries them.
2. **Seed path** — `models` state is initialized from `initial.models`
   (the RPC bundle), and the aggregate (`allMarkers`) is a memo over those
   markers, so live data reaches props in readOnly (no separate empty
   editing state masking it).
3. **Render not readOnly-gated** — the UI that renders the fields (findings
   table thumbnail, detail-panel gallery) is NOT behind `!readOnly`, so the
   client portal actually shows them.
4. **Live DB** — the user runs the SELECT above and rows return.

## Related gotcha
The agent cannot silently apply DB changes to the user's live tenant. When
the project isn't linked and no creds are present, the correct move is:
write the idempotent SQL file, give the exact Dashboard paste-and-Run steps,
and let the user execute. Do NOT claim the DB fix is "verified" until the
user confirms or a live SELECT result is shown.

## Anti-pattern: readOnly guards hiding content you actually want shown
When fixing "client shouldn't see X", the first instinct is often to add a
`readOnly` guard that hides a render/path in the client portal. For EVIDENCE /
IMAGE-PLACEHOLDER content this is usually WRONG — the inspector pastes photos
onto proxy meshes/planes precisely so the *client* sees them. Hiding those
meshes in `readOnly` made real image placeholders (with texture_url) vanish
from the share link, which was a regression, not a fix.

Rule: distinguish **editing UI** (`!readOnly` gated — correct to hide) from
**display data** (should render for clients — do NOT gate behind readOnly).
Only gate the editor, never the visual. Before adding any `readOnly &&` /
`if (readOnly) return` that removes something from the scene, confirm with the
user whether that thing is the deliverable the client is supposed to receive.
