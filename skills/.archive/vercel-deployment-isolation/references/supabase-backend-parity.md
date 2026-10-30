# Fresh Supabase DB backend-parity checklist (white-label duplicates)

When you duplicate a codebase (repo mirror) and point it at a NEW Supabase
project, the new DB is NOT ready just because the base tables/RLS exist. The
app's runtime RPCs and migrations must also be applied, or features silently
fail on first real interaction. Learned from the ARRAS (lunavsolution →
ARRAS) white-label, 2026-09-08.

## Symptom pattern
- App deploys and renders fine (build passes, login eventually works) but:
  - "+ Create" project does nothing
  - "User Approvals" button missing / admin check fails
  - search / share / CCTV / R-Tessera link error out
- Root cause: missing RPC functions, NOT missing UI or wrong deploy.

## Step 1 — RPC parity check (find the delta)
```python
import re
# app calls
calls = set()
for f in src.rglob("*.ts*"):
    calls |= set(re.findall(r'\.rpc\("(\w+)"', f.read_text()))
# schema defines
defs = set()
for f in [*base.glob("*.sql"), *base.glob("migrations/*.sql")]:
    defs |= set(re.findall(r'create or replace function public\.(\w+)', f.read_text()))
missing = calls - defs   # these MUST be added to the fresh DB
```

## Step 2 — where each commonly-missing RPC lives
- `is_admin`, `approve_user`          → `phase2_approval.sql` (standalone, NOT schema.sql)
- `search_projects`                   → `migrations/2026*_search_projects.sql`
- `mint_handoff_token`                → `migrations/*_geo_linking.sql`, `*_handoff_fix.sql`
- `set_marker_client_feedback`        → `migrations/*_client_feedback_write.sql`
- `upsert_cctv_camera`                → `migrations/*_cctv_cameras.sql` + `*_fix_upsert_param.sql`
- `get_project_public_home`           → often NOT in any repo file; only in the
                                        live production DB. Write it yourself:
                                        SECURITY DEFINER, anon+authenticated grant,
                                        returns `jsonb_build_object('project_name', ...)`
                                        for pinned/public projects.

Apply the standalone phase files FIRST (they define foundational RPCs), then
all migrations in date order. Most are idempotent (`create or replace`,
`create table if not exists`).

## Step 3 — brand_theme 'glass' constraint
A hand-built base schema usually allows only `('dark','light','midnight')`, but
the app defaults to `'glass'`. Fix so project INSERT doesn't fail with
`23514 ... projects_brand_theme_check`:
```sql
ALTER TABLE public.projects DROP CONSTRAINT IF EXISTS projects_brand_theme_check;
ALTER TABLE public.projects ADD CONSTRAINT projects_brand_theme_check
  CHECK (brand_theme IN ('dark','light','midnight','glass'));
NOTIFY pgrst, 'reload schema';
```

## Step 4 — middleware approval gate
If middleware does `select approved from profiles` for every authed user and
the fresh DB lacks that column, ALL logins redirect-loop to
`/login?reason=pending`. Fix: add `approved boolean default true` to profiles,
OR strip the approval-gate block from the duplicated repo's middleware. Also
remove the signup `router.push("/login?reason=pending")` redirect if there is
no real approval flow.

## Step 5 — verify with a real interaction, not just build
- login with a created user → dashboard
- create a project → workspace loads
- open each tab (Spatial / 3D / Docs / etc.) and confirm they render
A green `next build` proves only that the code compiles, not that the DB
backend is complete.
