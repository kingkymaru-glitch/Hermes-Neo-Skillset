---
name: free-tier-saas-supabase-r2
description: Build a zero-cost SaaS on Next.js + Supabase (auth/Postgres/Edge Functions) + Cloudflare R2 (large-file storage, zero egress) + Vercel. Covers schema+RLS design, presigned direct-to-R2 browser uploads, public read-only share-token portals, and CLI-driven wiring (secrets, deploy, env). Use when refactoring a prototype into a cloud app or standing up any free-tier multi-tenant product.
---

# Free-tier SaaS: Next.js + Supabase + Cloudflare R2

## Architecture rules
- Large binaries (3D models, photos, video) go to **Cloudflare R2**, never Supabase Storage — R2 has zero egress fees; Supabase egress will bill.
- File bytes flow **browser → R2 directly** via presigned PUT from a Supabase Edge Function. No Base64, no server relay.
- DB stores only the public R2 URL (`https://pub-xxxx.r2.dev/<key>`).
- Public share links: do NOT add anon RLS policies on tables. Expose ONE `security definer` RPC keyed by an unguessable UUID token that returns the whole project bundle as jsonb. Attack surface = one function. Pair with an owner-only `generate_share_token()` RPC that mints/rotates the token.

## Scaffold
```
npx create-next-app@latest APP --ts --tailwind --app --eslint --src-dir --no-import-alias --use-npm --skip-install
npm i @supabase/supabase-js @supabase/ssr three @types/three
```
Client/server Supabase helpers per @supabase/ssr docs (browser client + cookie-based server client + middleware auth gate). Next 16: `middleware.ts` works but warns (rename to `proxy` eventually); route params are `Promise` — `const { id } = await params`.

## Pitfalls (all hit in practice)
1. **Build fails prerendering pages that create a Supabase client** ("URL and API key required"). Fix: `export const dynamic = "force-dynamic"` in a layout.tsx for those routes, AND have a `.env.local` with at least placeholder values so local builds pass before credentials exist.
2. **Deno Edge Function files break Next's tsc**. Add `"supabase/functions"` to tsconfig `exclude`; give the function its own `deno.json`.
3. **Presigning R2 from Deno**: use `npm:aws4fetch` `AwsClient` with `region:"auto"`, `service:"s3"`, sign a PUT Request with `{ aws: { signQuery: true } }` and `X-Amz-Expires` query param. Endpoint = `https://<ACCOUNT_ID>.r2.cloudflarestorage.com/<bucket>/<key>` (no separate R2_ENDPOINT var needed).
4. **Upload progress**: fetch has no upload progress — use XMLHttpRequest PUT with `xhr.upload.onprogress`.
5. **Edge Function auth**: create the supabase client inside the function with the caller's `Authorization` header, `auth.getUser()` to reject anon, then verify resource ownership by selecting the row (RLS does the check). Validate extension allowlist + max size server-side.
6. **R2 CORS**: bucket needs a CORS rule with `AllowedMethods: [GET, PUT, HEAD]`, origins = localhost dev port(s) + prod domain, else browser PUT fails opaquely. See templates/r2-cors.json.
7. **`supabase login` fails in non-TTY** (even pty=true). Have the user run it in their own terminal, or use `SUPABASE_ACCESS_TOKEN`.
8. **You can fetch anon keys via CLI** — no need to ask user to copy from dashboard: `supabase projects api-keys --project-ref REF -o json` → write `.env.local` yourself. Verify with `curl .../rest/v1/<table>?limit=1 -H "apikey: $ANON"` (200 = schema live + key good).
9. **cwd / lockfile drift on macOS**: `next build`/`dev` pick the FIRST `package-lock.json` walking UP the tree. A repo at `~/Documents/foo` with a stray `~/package-lock.json` makes Next treat `~` as workspace root and miss the project's deps/`.env.local`. Symptom: `npm run dev` reports "Another next dev server is already running" on an unexpected port (:3210 vs :3000), or build warns "multiple lockfiles / inferred workspace root". Fix: `cd` into the real repo dir and confirm `pwd` first; when search finds a file but `read_file` says "File not found", the shell cwd drifted — re-anchor with `find`.
10. **Local-first deploy gate (user standing rule)**: if the user says "build locally first, push later when I confirm" — DO NOT commit or `git push` even if a later instruction block says "build, commit, push". Flag the conflict, then resolve in favor of local-only: build + show the running dev server, stop. A `git push` to a Vercel-linked main branch = go-live, so hold it until explicit "go". Applying Supabase schema migrations / deploying Edge Functions via CLI is fine anytime (those are Supabase-side, not a GitHub deploy).

## Wiring sequence (after user creates Supabase project + R2 bucket)
```
supabase link --project-ref REF
# schema.sql via dashboard SQL editor (idempotent: create table if not exists / drop trigger if exists)
supabase secrets set R2_ACCOUNT_ID=... R2_ACCESS_KEY_ID=... R2_SECRET_ACCESS_KEY=... R2_BUCKET=... R2_PUBLIC_BASE=https://pub-xxxx.r2.dev
supabase functions deploy r2-presign
# probe: curl POST the function with no auth → expect 401 (proves deployed + guarded)
```

## Schema conventions
- `profiles` FK to `auth.users` + `handle_new_user()` trigger (`security definer`, `on conflict do nothing`).
- Ownership chain: profiles ← projects ← models ← markers; RLS `for all using (exists (... owner_id = auth.uid()))` down the chain.
- `check` constraints for enums (role, status, file_ext); partial unique index on share token.
- **Adding a new first-class entity that must show in the client portal** (e.g. `documents`, `proxies`): (1) create the table with `create table if not exists` + owner-chain RLS policy `if not exists`; (2) `create or replace function get_shared_project(...)` and RE-EMIT the full jsonb shape — you must add the new `coalesce(jsonb_agg(...))` block inside the function body, the RPC does NOT auto-include new tables; (3) extend the TS `SharedProjectBundle` type + both server pages (owner fetch + share forward). Keep the RPC idempotent so re-running the migration is safe. See `references/extend-share-bundle.md` for the full recipe + the fail-safe pattern (defensive `?.` so the app builds/renders before the SQL is applied).
- **Fail-safe by default**: every client-share field is optional/defensive (`proxies: bundle.proxies ?? []`, `documents: (documents ?? []) as Doc[]`). The UI must render and `npm run build` must pass BEFORE the SQL migration is applied to the live DB — the schema is the last step, not a build blocker.

## Support files
- `references/r2-presign-edge-function.md` — full working Edge Function + upload client code.
- `references/extend-share-bundle.md` — recipe for adding new entity types (documents, proxies) to the client-share bundle: SQL migration + RPC re-emit + TS types + server pages, fail-safe.
- `templates/r2-cors.json` — known-good R2 CORS policy.

## Security hygiene
If the user pastes live secrets into chat, proceed but tell them to rotate the token after launch. Never echo secrets back or commit them; `.env.local` only.
