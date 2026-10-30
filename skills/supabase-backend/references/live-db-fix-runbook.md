# Live DB Fix Runbook (Vercel deploys do NOT run Supabase migrations)

## The trap
A repo migration that fixes schema/RPC exists, the frontend code is correct,
but PROD still shows missing/empty data (e.g. client share link missing defect
markers + evidence). Root cause: `git push` → Vercel only runs `next build`;
`supabase db push` is NOT wired into the deploy. So the live DB lags the repo.
Always suspect an unapplied migration BEFORE blaming React.

## When you have no Supabase creds / project not linked
Check `.env.local` for a pooler/DB URL + access token. If absent and
`supabase/config.toml` is missing (project not linked), you CANNOT apply from
CLI. Path: Supabase Dashboard → SQL Editor → paste the migration → Run. The
agent writes the idempotent SQL file; the user runs it (live-DB writes are a
privilege the agent holds no creds for here).

## Idempotent live-fix SQL template
Combine every fix migration into ONE file so it is re-runnable safely:
  - `ALTER TABLE ... ADD COLUMN IF NOT EXISTS ...`
  - Backfill: `UPDATE ... SET col=(subquery) WHERE col IS NULL AND EXISTS(...)`
  - `DO $$ BEGIN IF EXISTS (... is_nullable='YES') THEN ALTER TABLE ... SET NOT NULL; END IF; END $$;`
  - `CREATE OR REPLACE FUNCTION public.<rpc>(...) ...` (replaces whole body)
Idempotent = safe to paste twice; never use raw `ALTER ... ADD COLUMN` unguarded.

## Verify end-to-end (don't stop at "SQL ran")
1. Type boundary: confirm the TS type for the payload already declares the new
   field (e.g. `Marker.kind/geometry_json/photos_json` in `src/lib/types.ts`) so
   data isn't dropped at the prop boundary.
2. UI render: grep the render path — confirm the new field is actually rendered
   AND is NOT gated behind `!readOnly` (common mistake: hiding client data you
   meant to show).
3. Live SELECT to prove the RPC payload is populated:
     SELECT k.id, k.kind, k.photos_json
     FROM markers k JOIN models m ON m.id=k.model_id
     JOIN projects p ON p.id=m.project_id
     WHERE k.photos_json IS NOT NULL LIMIT 5;
   If rows return, the client view will show them.

## Anti-pattern caught this session
Hiding "proxy" meshes in `readOnly` (client) view to "keep planning private"
was WRONG — those meshes are image placeholders the inspector pastes photos
onto, so the client MUST see them. Distinguish "editing UI" (`!readOnly` gated)
from "display data" (should render for clients). Gate only the editor, not the
visual. First instinct ("hide X in client view") is often wrong for image/
evidence content — confirm intent before adding a readOnly guard.
