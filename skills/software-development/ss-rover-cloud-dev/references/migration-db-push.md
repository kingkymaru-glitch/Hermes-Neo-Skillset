# Applying DB migrations to live Supabase for this project

Two working CLI paths. Prefer **db push** for NEW schema (it tracks applied state).

## Path 1 (preferred for new columns/tables): `supabase db push --linked`
1. Write the SQL as a timestamped file in `supabase/migrations/`, e.g.
   `supabase/migrations/20260726_marker_photos.sql`.
2. `supabase link --project-ref <ref>` (re-link per session if needed).
3. `supabase db push --linked` — it diffs and applies ONLY new migrations,
   recording them in the remote `_supabase_migrations` table, so re-running skips
   already-applied files. It prompts `[Y/n]`; answer Y.
4. Confirm: re-run is a no-op.

This session: `cp supabase/phase4_marker_photos.sql supabase/migrations/20260726_marker_photos.sql`
then `npx supabase db push --linked` → "Applying migration ... Finished" (exit 0).

## Path 2 (one-off / ad-hoc): `supabase db query --linked --file`
- For RPC fixes, policy changes, or data backfills where you don't want a tracked
  migration file.
- `supabase db query --linked --file supabase/phase3_share_nodes_fix.sql`
- Does NOT track applied state (re-running re-applies). Make the SQL idempotent.

## Notes
- CLI 2.109+ removed `supabase sql -f`. Use `db query` or `db push`.
- `db query` / `db push` need a linked project; link once per session.
- Active ref is read from `.env.local` `NEXT_PUBLIC_SUPABASE_URL` (not memory).
- Apply DB changes BEFORE `git push` so the Vercel Git build doesn't hit a
  missing-column runtime error.
