---
name: supabase-r2-saas
description: Build zero-cost SaaS on Next.js + Supabase (auth/Postgres/Edge Functions) + Cloudflare R2 (large-file storage, zero egress) + Vercel. Covers presigned direct-to-R2 uploads, RLS schema, tokenized public share portals, and the R2 credential/CORS traps.
---

# Zero-Cost SaaS: Next.js OR Vite SPA + Supabase + Cloudflare R2 + Vercel

Use when building or extending a SaaS that stores large files (3D models, media) on
free tiers. Core rule: **large files NEVER go through Supabase storage** (egress fees);
they go browser → R2 directly via presigned PUT from a Supabase Edge Function.
Proven end-to-end in the SS Rover (Next.js) and RINA (Vite React SPA) builds.

## Architecture

- Frontend: Next.js App Router + Tailwind on Vercel (env: NEXT_PUBLIC_SUPABASE_URL / _ANON_KEY only) — OR a Vite React SPA (env: VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY). Same Supabase backend either way; the multi-tenant onboarding pattern below is frontend-agnostic.
- DB/Auth: Supabase Postgres + Auth, RLS owner-only policies on every table
- Files: Cloudflare R2 bucket with public r2.dev subdomain; keys namespaced `userId/projectId/kind/uuid-name`
- Presign: Supabase Edge Function using `npm:aws4fetch` AwsClient, `signQuery: true`, endpoint `https://<ACCOUNT_ID>.r2.cloudflarestorage.com/<bucket>/<key>`
- Upload client: XMLHttpRequest PUT (fetch has no upload progress)
- Public share: `client_share_token uuid` column + ONE `security definer` RPC returning the whole project bundle as jsonb — anon role gets EXECUTE on the function, zero table-level anon policies. Attack surface = one UUID-keyed function.

## Critical pitfalls (each cost real debugging time)

1. **R2 credentials — `cfat_...` is NOT an S3 key.** Cloudflare API tokens start with
   `cfat_`; the S3 API needs the 32-hex Access Key ID + 64-hex Secret shown under
   "Use the following credentials for S3 clients" when creating/rolling an R2 API token.
   Wrong pair → every presigned URL 403s. Verify keys independently before blaming CORS:
   `curl --aws-sigv4 "aws:amz:auto:s3" --user "KEY:SECRET" -X PUT --data-binary @f "https://<acct>.r2.cloudflarestorage.com/<bucket>/test.txt"` → expect 200.

2. **Browser 403 with working curl = CORS preflight.** Error text contains "Preflight".
   curl skips OPTIONS preflights, so a passing curl proves keys, not browser access.
   Fix: bucket CORS policy (dashboard → bucket → Settings → CORS) allowing GET/PUT/HEAD
   from localhost dev ports AND the production domain. Object R/W tokens CANNOT set
   CORS via the S3 `?cors` API (403 AccessDenied) — needs Admin token or dashboard.
   Add the production domain to CORS from day one so deploy "just works".

3. **Edge Function secrets hot-reload** — `supabase secrets set K=V ...` takes effect
   without redeploying the function. Only redeploy when code changes.

4. **Next.js prerender vs Supabase client**: pages that create a Supabase client at
   build time crash `next build` without env vars. Either provide placeholder
   .env.local values or add `export const dynamic = "force-dynamic"` in a layout.

5. **supabase CLI login is interactive-only** (device-code flow, no TTY automation).
   Run `supabase login` in a background PTY process and watch for "Congratulations",
   or have the user run it. Same for `npx vercel login` (watch pattern works).

6. Exclude `supabase/functions` from the Next.js tsconfig (`exclude`) — Deno imports
   (`npm:...`, `Deno.*`) break the app's typecheck otherwise.

7. **Auth → URL Configuration (Site URL / redirect) — set it BEFORE remote signups.**
   Default confirmation-email links point to `localhost`, so a friend in another
   state clicks "verify" and hits a dead URL. Set in Supabase dashboard:
   Auth → URL Configuration → Site URL = `https://<your-vercel-domain>` and add
   `https://<your-vercel-domain>/**` to Redirect URLs. Required for any real
   multi-user launch, not just local testing.

8. **Free-tier email is rate-limited (~3–4/hr shared SMTP).** Signing up a few test
   accounts in quick succession makes the NEXT signup fail with
   "email rate limit exceeded" even though the form/validation are correct. It is
   NOT an app bug — it self-resets in ~1h. For real user onboarding, wire Resend
   (free: 3,000/mo) as the auth email provider (Auth → Providers → Email → custom SMTP)
   and the limit disappears. Also: confirmation emails from shared SMTP often land in
   spam, so tell users to check spam.

### Signup verification probe (prove the flow works)
After setting Site URL, confirm end-to-end without a real user:
```bash
URL=$(grep NEXT_PUBLIC_SUPABASE_URL .env.local | cut -d= -f2)
ANON=$(grep NEXT_PUBLIC_SUPABASE_ANON_KEY .env.local | cut -d= -f2)
TEST="probe$(date +%s)@gmail.com"
curl -s -X POST "$URL/auth/v1/signup" -H "apikey: $ANON" -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST\",\"password\":\"Test123456!\"}" \
  -w "\nHTTP %{http_code}\n"   # expect 200 + confirmation_sent_at set
```
A 200 with `confirmation_sent_at` proves: signup accepted, confirmation email fired,
account gated until verified. (Create one throwaway user; delete it in
Auth → Users if you want a tidy list.)

## Deploy without dashboard paste-work

- Env vars via CLI pipe: `grep KEY .env.local | cut -d= -f2 | npx vercel env add KEY production`
- `npx vercel link --yes --project <name>` then `npx vercel deploy --prod --yes`
- Read anon/service keys programmatically: `supabase projects api-keys --project-ref <ref> -o json`
- Smoke-test the public share path as an outsider: anon RPC via curl + `curl -w "%{http_code}"` on the share URL.
- **Push the project to GitHub (version control / handover):** if `gh auth status`
  says not logged in but the Mac has Keychain GitHub access, recover the token and
  auth headlessly — no browser, no hand-typed PAT:
  ```bash
  TOKEN=$(printf "protocol=https\nhost=github.com\n\n" | git credential-osxkeychain get 2>/dev/null | grep "password=" | cut -d= -f2)
  echo "$TOKEN" | gh auth login --with-token
  gh repo create <name> --private --source=. --remote=origin --push   # one shot: create + push
  ```
  (If `git credential-osxkeychain get` is empty, fall back to `gh auth login`
  browser flow.) Vault note + memory of the live URL/refs makes the next session
  resume cleanly.

## Verification pattern

Never claim "wired up" from config alone. Chain-test with real requests:
signed PUT to R2 (200) → public read on r2.dev URL (200) → anon RPC returns data →
share page 200 with expected content grep. Cleanup test objects with signed DELETE (204).

## Multi-tenant onboarding (many companies, isolated) — Vite SPA proven (RINA)

When the product serves multiple separate orgs (each with its own admin + people), isolate by `organization_id` on every table and enforce with RLS. Pattern that shipped clean:

- Tables: `organizations(id)`, `user_profiles(id=auth.users.id, organization_id, …role…)`, plus `tasks`/`audit_logs` carrying `organization_id` (store the app's Task object as a `jsonb data` column to avoid 20 scalar columns and keep the client `Task` type intact — RLS filters by `organization_id` only).
- RLS helper: `create function my_org_id() returns uuid language sql stable as $$ select organization_id from user_profiles where id = auth.uid() $$;` then every policy is `using (organization_id = my_org_id())`. The helper runs as the invoker so it can read the caller's own profile row.
- **One trigger does both onboarding paths** (`on_auth_user_created after insert on auth.users`):
  - first admin → client passes `options.data = { company_name, name, … }`; trigger `insert into organizations` then `insert into user_profiles (… role 'SuperAdmin')`.
  - invited member → client passes `options.data = { organization_id, name, … }`; trigger finds an existing invited profile (same email + org, `active=false`) and claims it (`update … set id=new.id, active=true`), else inserts a `Member`.
  - Keep the trigger `security definer` so it can write `user_profiles` through RLS.
- Client wiring (Vite): `createClient(url, anon)`, `supabase.auth.signUp({ email, password, options:{ data } })`. After `onAuthStateChange`, read `user_profiles` for the session user; expose `orgId` from the profile and pass it DOWN to the data hooks so they reload when it changes (React runs CHILD effects before PARENT effects — reading a module-global `orgId` in a child hook's mount effect fires BEFORE the parent auth effect sets it → empty load. Thread `orgId` as state/props, never a captured global, for the initial load).
- **Debug the trigger without a deliverable email:** Supabase blocks signups from many domains (`example.com`, `rinatest.app`, …) with "Email address … is invalid", and free-tier SMTP is rate-limited. You can't always fire a real signup from a script. Instead test the trigger directly as the project owner (postgres bypasses RLS, so this proves the trigger logic, NOT RLS enforcement): `insert into auth.users (id, email, raw_user_meta_data) values (gen_random_uuid(), 'x@example.com', '{"company_name":"Co"}');` then `select * from user_profiles where id=<that id>` → expect an org + SuperAdmin profile. Clean up both rows after. RLS enforcement itself must be verified by code/policy review or a real JWT, not this owner-channel test.
- **Confirm signups must be OFF for headless/local testing** (Auth → Providers → Email → disable "Confirm signups"), else signUp returns a session=null state and the UI shows "check your email" forever. For real launch, set Site URL + turn confirmation back on (see pitfall 7) and warn users about spam.

### Vite SPA deploy gotchas
- `npm run build` SUCCEEDS even when `VITE_SUPABASE_URL`/`VITE_SUPABASE_ANON_KEY` are unset — Vite just inlines empty strings, so the app loads but every auth call fails silently at runtime. The env vars must be set in the Vercel dashboard (Project → Settings → Env) for the deployed build; `.env.local` only covers local dev. There is no Vercel CLI/token in this environment, so this is a manual dashboard step the agent cannot complete — hand the user the exact two key/value pairs and ask them to redeploy.
- Keep a `supabase/` folder + `supabase link --project-ref <ref>` so `supabase db query --linked --file supabase/schema.sql` applies schema. Idempotent DDL (`add column if not exists`, `drop policy if exists … create policy`, `create or replace function`) so re-applying is safe.
- See references/multitenant-vite-supabase.md for the exact schema.sql + client/api layer shape.

## Reusable technique — client-side image resize BEFORE R2 upload (replaces hard byte caps)

A hard per-file byte cap (e.g. "max 200KB") just REJECTS the upload — a
3MB phone photo is thrown away client-side and the user gets a confusing
"too large" error. Better: downscale **in-browser** before the bytes leave
the tab, so any photo uploads small without a cap the user can hit.

Add a client-only helper (no backend / Edge Function / R2 change):
```ts
export async function resizeImage(file: File, maxDim = 1280, quality = 0.8): Promise<File> {
  if (!file.type.startsWith("image/")) return file;            // pass non-images through
  try {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, maxDim / Math.max(bitmap.width, bitmap.height));
    const w = Math.round(bitmap.width * scale), h = Math.round(bitmap.height * scale);
    const canvas = document.createElement("canvas");
    canvas.width = w; canvas.height = h;
    const ctx = canvas.getContext("2d");
    if (!ctx) return file;
    ctx.drawImage(bitmap, 0, 0, w, h);
    bitmap.close?.();
    const blob = await new Promise<Blob | null>((r) => canvas.toBlob((b) => r(b), "image/jpeg", quality));
    if (!blob) return file;
    return new File([blob], file.name.replace(/\.[^.]+$/, "") + ".jpg", { type: "image/jpeg" });
  } catch {
    return file;   // decode/encode failure → upload original rather than throw and break the flow
  }
}
```
Then in every image upload path: `const resized = await resizeImage(file, 1280, 0.8); uploadToR2(resized, …)`.

- A 3MB photo → ~120–300KB (longest-edge downscale + JPEG@0.8 is the real
  weight-killer; a 4000px phone shot dropped to 1280px cuts pixels ~10×).
- Keep a LOOSE safety cap on the RAW input (e.g. 15MB) so a 200MB RAW
  doesn't freeze the tab during `createImageBitmap` decode — but don't cap
  the output; the resize makes output small automatically.
- Apply to ALL image upload paths for consistency (node photos, proxy
  textures, avatars) — not just one, or users hit asymmetry. Node photos:
  1280px @ 0.8. Proxy textures: 1024px @ 0.85 (slightly higher quality,
  smaller max dim).
- The original bytes NEVER touch R2; only the resized blob is PUT.
- Bonus: display is faster everywhere because less data is served back.
- **Harden with try/catch** (this session's shipped version): wrap the whole
  decode/draw/encode in `try { … } catch { return file; }`. `createImageBitmap`
  throws on unsupported/garbage input — without the catch the upload flow
  crashes; with it, the original file uploads as a safe fallback.

Shipped for ss-rover-cloud node photos + proxy textures (verified: `npm run
build` green, live upload of a >200KB original succeeded after resize). The
3-photo-per-node limit stayed; only the byte-cap was removed.

## Reusable technique — split glTF (.gltf + .bin) → single .glb, client-side, before R2 upload

A `.gltf` is JSON that **references an external `.bin`** (geometry/buffers) and
sometimes sibling image files. Uploading ONLY the `.gltf` leaves the `.bin`
behind on disk → the viewer (`THREE.GLTFLoader`) throws `Failed to load buffer
"<name>.bin"` and the model never renders. Two things are required:

1. **The file picker `accept` filter MUST include `.bin`** (and the image
   extensions). Otherwise macOS greys the `.bin` out — the user can SEE it but
   not SELECT it (same class of bug as excluding an allowed extension). The
   picker uses `multiple`, so the user selects both `.gltf` and `.bin`
   together.
2. **Pack them into one `.glb` in-browser before upload** so the viewer loads a
   single self-contained file. Inline the `.bin` (+ any textures) as base64
   `data:` URIs, then wrap the modified glTF JSON in the GLB container (JSON
   chunk + empty BIN chunk). No backend / Edge Function change.

The actual helper (drop in `src/lib/gltf-pack.ts`, call from the model-upload
handler when `ext === "gltf"`): see references/gltf-r2-upload.md.

- Verified against a real 5.7 MB `.bin`: GLB header valid (`glTF` magic,
  version 2, length matches), zero buffers left external after packing.
- `.glb` and `.obj` pass through unchanged (no packing). The viewer already
  loads `.glb` natively via `GLTFLoader`.

## Pitfall — the public share RPC must emit EVERY column the read-only view reads

The tokenized share portal (`get_shared_project` security-definer RPC) builds
each marker's JSON. If you later add a column the client portal reads (e.g.
`photos_json` for evidence photos) but **forget to add it to the RPC's
`jsonb_build_object`**, the inspector view shows it (reads the table directly)
but the **client portal shows the node with the field missing/empty** — e.g.
nodes render but their evidence photos are gone. This bit ss-rover-cloud: a
multi-photo migration emptied the legacy `image_url` and the RPC still returned
only `image_url` (now null) and omitted `photos_json`. Fix: re-`create or
replace function` the RPC to include `photos_json` (coalesce to `'[]'::jsonb`),
re-apply via `supabase db push`. Lesson: any column a read-only/share view
consumes MUST be in the RPC projection, or that surface silently drops it.

## Pitfall — `supabase db push` migration filename collision on same date

`supabase db push` keys applied migrations by a **date-prefix** in the filename
(`<timestamp>_name.sql`). Two files with the SAME date prefix (e.g.
`20260726_marker_photos.sql` already applied, then you add
`20260726_share_photos.sql`) collide on the `schema_migrations_pkey` unique
constraint → `ERROR: duplicate key value violates unique constraint
"schema_migrations_pkey" (Key (version)=(20260726) already exists)`. The file
is also SKIPPED if the name doesn't match `<timestamp>_name.sql` (e.g.
`20260726b_...` → "file name must match pattern"). Fix: give the new migration
a **distinct timestamp** (`20260727_share_photos.sql`). Always check existing
migration timestamps before naming a new one.

## References
- references/ss-rover-build.md — full build recipe: schema/RLS SQL shape, presign function, share portal, session log
- references/multitenant-vite-supabase.md — RINA multi-tenant Vite SPA: schema.sql, trigger, RLS, client/api layer, orgId threading
- references/gltf-r2-upload.md — glTF→GLB client-side packer helper + verification recipe
