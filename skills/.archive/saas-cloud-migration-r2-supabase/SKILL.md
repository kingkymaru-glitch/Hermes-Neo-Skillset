---
name: saas-cloud-migration-r2-supabase
description: Migrate a monolithic 3D/HTML prototype into a free-tier SaaS (Next.js + Supabase + Cloudflare R2 + Vercel) with presigned direct uploads, RLS, and a public tokenized read-only client portal.
---

# SaaS Cloud Migration: Next.js + Supabase + Cloudflare R2

Use when converting a single-file HTML prototype (Base64/localStorage state) into a
multi-tenant cloud app at zero initial cost, or when adding "share with client"
read-only portals to any Supabase-backed app.

## Architecture (free-tier, scales)
- Vercel: Next.js hosting. Supabase: Postgres + Auth + Edge Functions.
- Cloudflare R2 for large files (3D models, photos): 10GB free, ZERO egress —
  never Supabase Storage for large assets (egress fees).
- Files go browser → R2 directly via presigned PUT; only URLs hit the DB. Kill all Base64.

## Steps
1. LOCATE THE REAL SOURCE FIRST. Prototypes drift — search Desktop/Downloads for
   newest variant, `open` it for user eyeball-confirmation before porting.
2. Scaffold: `npx create-next-app@latest <name> --ts --tailwind --app --eslint --src-dir --no-import-alias --use-npm --skip-install`, then npm install + `three @types/three @supabase/supabase-js @supabase/ssr`.
3. Schema (`supabase/schema.sql`): tables + RLS "owner full CRUD via auth.uid()"
   policies. For anonymous share access DO NOT add anon table policies — expose ONE
   `security definer` function `get_shared_project(share_token uuid) returns jsonb`
   that bundles the whole project (nested jsonb_agg), grant execute to anon.
   Token generation = second security-definer fn that checks ownership, returns gen_random_uuid().
   Auto-create profiles with an `on_auth_user_created` trigger.
4. R2 presign Edge Function (Deno): auth check via supabase.auth.getUser, verify
   project ownership through RLS select, sign PUT with `aws4fetch` AwsClient
   (region "auto", service "s3", signQuery, X-Amz-Expires=600). Validate ext allowlist + size cap.
   Key layout: `{userId}/{projectId}/{models|photos}/{uuid}-{safeName}`.
   Template: templates/r2-presign-edge-function.ts.
5. Client upload helper: invoke edge fn → XMLHttpRequest PUT (fetch has no upload
   progress) → save publicUrl row.
6. UI: ONE workspace component with `readOnly` prop serves both inspector route and
   public `/share/[token]` route (hide toolboxes, disable inputs, show watermark link
   for viral B2B). Three.js viewer as `dynamic(() => import(...), { ssr: false })`,
   URL-driven model loading, markers synced from DB rows to CSS2DObject pins via a
   Map keyed by row id; keep latest callbacks in a `liveRef` so the stable click
   handler sees fresh state.
7. Middleware auth gate (@supabase/ssr createServerClient pattern); public paths:
   `/`, `/login`, `/share`, `/auth`.

## Pitfalls
- `next build` prerender fails on pages creating Supabase clients when env vars are
  placeholders/missing: add `export const dynamic = "force-dynamic"` layout for
  authed pages AND put placeholder values in .env.local so local builds pass.
- Exclude `supabase/functions` in tsconfig `exclude` — Deno imports break Next's TS pass.
- Next 16: `middleware` file convention deprecated (warns, still works; rename to `proxy` eventually). Route params are Promises: `params: Promise<{id:string}>` + await.
- R2 bucket needs public r2.dev subdomain (or custom domain) AND a CORS rule
  allowing PUT from localhost + prod domain, or uploads fail as "network error".
- Verify with `npm run build`, then dev server on a spare port + curl 200 checks + `open` for the user.

## User preference (kamarulhk)
- Design language: Mercedes-Benz MBUX digital dash — near-black glass panels,
  hairline dividers, turquoise (#00e5c3) primary / amber (#ffb340) warn / red (#ff4d4d) crit,
  gauge-arc motifs (270° dials instead of pie charts), startup needle-sweep animation,
  recessed input wells, monospace tabular readouts. Apply to SS Rover work unprompted.
- Open the visual result in the browser and ask for eyeball confirmation before wiring credentials.
