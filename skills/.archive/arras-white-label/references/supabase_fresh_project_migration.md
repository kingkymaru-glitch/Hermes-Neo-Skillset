# ARRAS Supabase Fresh-Project Migration Gotchas

## Failure: Edge Functions 404 on fresh project
- **Cause:** ARRAS Supabase starts with ZERO Edge Functions deployed. The code in `supabase/functions/r2-presign/index.ts` exists locally but is not deployed. Features that upload files (GLB, photos, docs) 404 until the function is deployed.
- **Fix:** Link and deploy:
  ```bash
  cd ~/ARRAS
  supabase link --project-ref lxmmxpxjercmhmiuqegq
  supabase functions deploy r2-presign r2-list notify-admin
  ```
- **Then set R2 secrets** via Supabase Dashboard → Edge Functions → <function> → Secrets. The secrets are `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `R2_PUBLIC_BASE`.

## Failure: R2 secrets not accessible from .env or Vercel
- **Cause:** R2 credentials are stored as Supabase secrets, not in `.env.local` or Vercel env vars. You cannot read them via CLI or inspect them programmatically.
- **Fix:** Ask the user to provide the 5 R2 values from Cloudflare R2 dashboard (Account ID, Access Key ID, Secret Access Key, Bucket name, Public URL). Do not block — ask directly.

## Failure: relation "public.projects" does not exist
- **Cause:** The monolithic `schema.sql` references columns in `get_shared_project` that were never added to the `projects` table definition (`analytics_comment`, `executive_summary`, `spatial_model_id`, `detail_model_id`).
- **Fix:** Ensure all columns referenced by RPCs exist in the table definitions. For fresh projects, either:
  - Add missing columns directly to the `create table` statement, or
  - Run `alter table ... add column` before creating the RPC that reads those columns.

## Failure: column p.analytics_comment does not exist
- **Cause:** Same root issue — base `projects` table missing columns that migrations add later.
- **Fix:** Apply migrations in timestamp order, never paste `schema.sql` alone for a fresh DB. Better yet, rewrite `schema.sql` to include all columns up front.

## Fresh-Project Safe Pattern
1. Create `arras_base_schema_clean.sql` with complete table definitions.
2. Append ARRAS-specific migrations at the end.
3. Remove all comments for clean copy-paste into Supabase SQL Editor.
4. Use `create or replace function` for RPCs so re-runs are idempotent.

## Vercel Env Var Gotcha
- `NEXT_PUBLIC_*` variables must have **visibility: config**.
- `service_role` must have **visibility: secret** and must never be added to Vercel env vars.
