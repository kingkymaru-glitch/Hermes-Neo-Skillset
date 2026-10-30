# LunaV — Live-DB migration gate

Pattern discovered 2026-08-05: an untracked `supabase/20260801_apply_client_feedback_live.sql`
was sitting in the repo while `ProjectWorkspace.tsx` (committed) was already fully wired to
the new `markers.client_comment` / `markers.action_needed` columns + the upgraded
`get_shared_project` RPC. Vercel does NOT run migrations, so until the SQL is applied to the
live DB manually, the feature silently degrades: autosave `.update({ client_comment,
action_needed })` 400s and the Action donut reads all-false — masked only by `?? ""` /
`?? false` fallbacks in the UI.

## Detection (run this any time you open the repo)
```
git status --porcelain -- 'supabase/*.sql'
```
Any untracked/modified `.sql` under `supabase/` = pending live-DB work that is very likely
already fronted by shipped UI.

## Apply-to-live checklist
1. Read `NEXT_PUBLIC_SUPABASE_URL` from `.env.local` → that's the ACTIVE project ref
   (don't trust stale notes; `.env.local` is the source of truth).
2. `supabase link --project-ref <ref>` (re-link per session).
3. `supabase db query --linked --file <sql>` — runs via Management API, no DB password.
   - Old `supabase sql -f` is GONE in CLI 2.109+.
   - `CREATE POLICY` has no `IF NOT EXISTS` → use `drop policy if exists …; create policy …`.
4. Verify the columns/functions exist:
   `supabase db query --linked --file /dev/stdin <<'SQL' … SQL`.
5. `git add <sql> && git commit -m "…"` — BACK UP the migration on GitHub. An untracked SQL
   file is not backed up and can be lost (this is exactly what happened 2026-08-05).
6. Do NOT `git push` until the user explicitly says go (standing local-first gate).

## Why this is a standing rule, not a one-off
The LunaV deploy path is `git push main` → Vercel auto-build + auto-promote. Vercel builds
the frontend only; it never touches Postgres. So a migration file + frontend PR can ship to
prod while the DB is stale, and the breakage stays invisible until a real write hits the
missing column. Always apply + commit the SQL in the same working session as the frontend
that depends on it.
