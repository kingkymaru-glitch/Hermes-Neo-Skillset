---
name: supabase-r2-saas-stack
description: Build zero-cost SaaS on Next.js + Supabase (auth/Postgres/Edge Functions) + Cloudflare R2 for large file storage. Covers presigned direct-to-R2 uploads, share-token public portals via SECURITY DEFINER RPC, RLS patterns, and R2 credential pitfalls.
---

# Supabase + Cloudflare R2 SaaS Stack

Use when building or wiring a free-tier SaaS: Vercel frontend, Supabase (auth, Postgres, Edge Functions), Cloudflare R2 for large assets (3D models, media). NEVER store big files in Supabase Storage — R2 has zero egress fees.

## Architecture pattern
1. Browser asks Supabase Edge Function for a presigned PUT URL (auth-gated).
2. Browser PUTs file directly to R2 (bytes never touch Supabase; no Base64).
3. Public r2.dev URL saved to a DB row; frontend fetches from R2 directly.
4. Public read-only sharing = ONE `SECURITY DEFINER` RPC keyed by UUID token — no anon table policies needed. Grant execute to `anon`.

Working implementation: ~/lunavsolution-code (schema at supabase/schema.sql, edge fns at supabase/functions/r2-presign/ + supabase/functions/r2-list/, client upload at src/lib/r2-upload.ts, client list at src/lib/r2-list.ts).

## Key steps
- Edge Function signs with `aws4fetch` (`npm:aws4fetch`), region "auto", service "s3", `aws: { signQuery: true }`, endpoint `https://<ACCOUNT_ID>.r2.cloudflarestorage.com/<bucket>/<key>`.
- Client upload uses XMLHttpRequest (fetch has no upload progress API).
- `supabase secrets set K=V K2=V2 ...` hot-reloads — no redeploy needed after changing secrets.
- Get anon key programmatically: `supabase projects api-keys --project-ref REF -o json`.
- Next.js + `@supabase/ssr`: pages that create a Supabase client at render must be dynamic — add a layout with `export const dynamic = "force-dynamic"` or build-time prerender fails with "URL and API key required".
- Exclude `supabase/functions` in tsconfig `exclude` (Deno code breaks Next typecheck).
- R2 bucket needs: public r2.dev subdomain enabled + CORS JSON allowing PUT from localhost + prod domain.

## Pitfalls
- **R2 403 on upload = wrong credential type, not CORS.** Cloudflare "API token" (`cfat_...`) is NOT the S3 Access Key ID. R2's S3 API needs the 32-hex Access Key ID + 64-hex Secret shown under "Use the following credentials for S3 clients" on token create/roll. Rolling the token re-displays both.
- **`npm run build` fails with "URL and API key required"** — even for `"use client"` pages. Next.js prerenders client components server-side, which calls `createBrowserClient` from `@supabase/ssr` at build time. Fix: create `.env.local` with `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY` (auto-gitignored by `.gitignore`'s `.env*` rule). Values can be placeholders for build verification; real values go in Vercel dashboard.
- Verify R2 creds directly before blaming app code: see scripts/r2-smoke-test.sh (signed PUT + public GET + DELETE via curl --aws-sigv4).
- 404 on r2.dev root/random key = public access IS enabled (good). 403 = disabled or bad signature.
- Diagnose upload failures by querying the models table with the service_role key: empty table = upload PUT failed, not the viewer.
- User pasted secrets in chat → remind to rotate after launch.
- `supabase login` fails in non-TTY; user must run it in their own terminal (or set SUPABASE_ACCESS_TOKEN).
- `supabase db query` targets LOCAL db by default; use REST API with service_role key for remote data checks.

## References
- references/r2-presign-notes.md — presign function shape, CORS JSON, schema/RLS patterns.
- scripts/r2-smoke-test.sh — end-to-end credential verification.
