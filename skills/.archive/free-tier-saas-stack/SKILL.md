---
name: free-tier-saas-stack
description: Build and ship a zero-cost SaaS on Next.js + Supabase (auth/DB/Edge Functions) + Cloudflare R2 (large files, zero egress) + Vercel. Covers presigned direct-to-R2 uploads, share-token public portals via security-definer RPC, R2 credential/CORS pitfalls, and CLI-only deploy.
---

# Free-Tier SaaS Stack (Next.js + Supabase + R2 + Vercel)

Use when: user wants a cloud app with auth, DB, and large-file storage at $0/month, or when refactoring a monolithic HTML prototype into a hosted product.

## Architecture rules
- Large binaries (3D models, video, images) go to **Cloudflare R2**, never Supabase Storage — Supabase egress fees are the cost trap; R2 egress is free.
- Upload path: browser → Supabase Edge Function (auth check + presign PUT, 10 min expiry) → browser PUTs bytes straight to R2 via XMLHttpRequest (for progress events; fetch has no upload progress). File bytes never touch Supabase.
- Serve files from the bucket's public r2.dev subdomain (or custom domain); store that public URL in the DB.
- Public read-only share portals: do NOT add anon RLS policies. Expose ONE `security definer` SQL function `get_shared_project(share_token uuid) returns jsonb` that bundles the whole object graph; `grant execute to anon`. Attack surface = one UUID-keyed function. Token generation likewise via a definer RPC that checks `owner_id = auth.uid()`.
- Same workspace component serves inspector and client: pass `readOnly` prop; hide admin controls, disable inputs, add branded watermark in read-only mode.

## Workflow (proven order)
1. `npx create-next-app --ts --tailwind --app --src-dir` + `@supabase/ssr @supabase/supabase-js three`.
2. Write full schema.sql (tables + RLS + definer RPCs) idempotent (`if not exists`), keep in `supabase/schema.sql`; later changes as `supabase/migrations/*.sql` pushed with `supabase db push --include-all`.
3. Edge Function presign with `npm:aws4fetch` (`AwsClient`, region "auto", service "s3", `signQuery: true`). Exclude `supabase/functions` from Next tsconfig (Deno globals break `tsc`).
4. Add `export const dynamic = "force-dynamic"` layout to any Supabase-reading route, or `next build` fails prerendering without env vars.
5. CLI wiring, no dashboard needed for most steps:
   - `supabase login` (needs real browser; run as background pty process, user authorizes device code)
   - `supabase link --project-ref X`, `supabase secrets set K=V ...` (hot-reload, no redeploy), `supabase functions deploy NAME`
   - Fetch anon key programmatically: `supabase projects api-keys --project-ref X -o json`
   - Vercel: global `npm i -g vercel` may fail with perm error — just use `npx vercel`. Login via background pty (device code). Env vars: `grep KEY .env.local | cut -d= -f2 | npx vercel env add KEY production`. Deploy: `npx vercel deploy --prod --yes`.
6. Verify from outside after every deploy: curl the routes, curl the share URL and grep for real data.

## Pitfalls (all hit live — see references/r2-pitfalls.md for transcripts)
- **R2 credential trap**: a `cfat_...` Cloudflare account API token is NOT an S3 Access Key ID. R2's S3 API needs the 32-hex Access Key ID + 64-hex Secret shown once under "Use the following credentials for S3 clients" when creating/rolling an R2 API token. Wrong type ⇒ every presigned PUT 403s.
- **Verify credentials directly** before blaming code: `curl --aws-sigv4 "aws:amz:auto:s3" --user "KEY:SECRET" -X PUT --data-binary @f "https://ACCT.r2.cloudflarestorage.com/BUCKET/key"` — 200 proves keys; then GET the pub URL proves public access.
- **CORS preflight 403 even when curl works**: curl skips preflight. Browser OPTIONS needs a bucket CORS policy (AllowedOrigins incl. localhost ports AND the future Vercel domain from day one; Methods GET/PUT/HEAD; Headers *; ExposeHeaders ETag). An Object-Read-Write R2 token CANNOT set CORS via S3 API (`?cors` PUT ⇒ AccessDenied — bucket admin scope); user must paste JSON in dashboard. After fixing, hard-refresh — failed preflights cache.
- 404 (not 403) from a random key on `pub-*.r2.dev` = public access IS enabled; 401 from an Edge Function without auth header = deployed correctly.
- Secrets pasted into chat are exposed — tell the user to roll the token after launch.
- `supabase db query` connects to LOCAL db by default; query the hosted project via PostgREST with the service_role key instead.
- Empty DB table + 403s in console = the upload failed; don't debug the viewer first.

## Static Vite/React SPA deploy to Vercel (the "Phase A" path)
When the app is a plain Vite/React SPA (no Next.js, no server, no DB yet), deploy is simpler than the Next.js path — no env vars, no Edge Function, no presign unless you later add storage:
- `npm install && npm run build` → static `dist/`.
- `npx vercel deploy --prod --yes` — Vercel auto-detects Vite (build `npm run build`, output `dist`). No framework config needed.
- Phase B persistence without a backend: wire a localStorage hook layer (see references/vercel-static-vite.md for the seed pitfall).
- Phase C multi-customer white-label: keep all client copy in one `src/config/copy.ts` (see references/whitelabel-copy.md).

## Standing ship workflow (adopted as a hard rule by the user)
After any code change the user wants live, run in order: `npm run build` → `git commit` → `git push` → `npx vercel deploy --prod --yes`. Keeps the private GitHub repo and the live app in sync every change. Don't ask each time once the user has approved the pattern.

## Publish to GitHub without interactive `gh auth login`
On a Mac where `gh` isn't logged in but the machine has prior HTTPS access, the token lives in the macOS Keychain. Recover + use it (no browser needed):
```
TOKEN=$(printf "protocol=https\nhost=github.com\n\n" | git credential-osxkeychain get 2>/dev/null | grep password= | cut -d= -f2)
echo "$TOKEN" | gh auth login --with-token
gh repo create NAME --private --source=. --remote=origin --push
```
Pitfall: the `printf` payload MUST end with a blank line; omit it and the helper returns nothing. `gh auth login --with-token` reads the token from stdin.
Pitfall: a fresh `git init`'d repo may lack a `.gitignore` — add one (exclude `node_modules/`, `dist/`, `.env*`) before the first commit so the repo stays lean.

## UI hardening that recurs in data tables/drawers
- Long unbroken strings blow tables out and push right-hand columns off-screen: `tableLayout: "fixed"` + `<colgroup>` widths + `-webkit-line-clamp: 3` + `overflowWrap: "anywhere"`; full text lives in a click-through detail modal.
- Drawer images: fixed-height thumbnail + click-to-zoom fullscreen overlay, never natural-size (pushes layout). `textarea { resize: none }` globally.
- Esc closes overlays innermost-first (zoom → detail → drawer).
- Three.js: `PCFSoftShadowMap` deprecated in r160+, use `PCFShadowMap`. Near-black scene backgrounds hide dark models — lift stage to steel blue-grey (~0x232d3a) while keeping UI chrome dark; brighten ambient/key lights.
- Dark navy logos vanish on dark UIs: mount on a light rounded "plinth" tile.

## Templates
- `templates/r2-cors.json` — known-good R2 bucket CORS policy.
- `templates/r2-presign-edge-function.ts` — full Supabase Edge Function (auth + validation + aws4fetch presign).

## References
- `references/vercel-static-vite.md` — Vite SPA → Vercel deploy, localStorage Phase B wiring, and the empty-seed pitfall that silently wipes demo data.
- `references/whitelabel-copy.md` — keep all client copy in `src/config/copy.ts` so one product serves many customers without touching components.
