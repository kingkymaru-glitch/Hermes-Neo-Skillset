---
name: supabase-r2-vercel-saas
description: Build and ship a zero-cost SaaS on Next.js + Supabase (auth/Postgres/Edge Functions) + Cloudflare R2 (large file storage, zero egress) + Vercel. Covers presigned direct-to-R2 uploads, RLS + share-token public portals, R2 credential/CORS debugging, and full CLI-driven deploy.
---

# Supabase + R2 + Vercel free-tier SaaS

Use when: turning a prototype (often a monolithic HTML file with Base64/localStorage) into a hosted multi-user app with big-file storage, or debugging R2 uploads/CORS, or wiring Supabase Edge Functions to R2.

## Architecture (proven stack)
- Frontend: Next.js App Router + Tailwind on Vercel free tier.
- DB/Auth: Supabase (Postgres + RLS + Auth + Edge Functions).
- Large files (3D models, media): Cloudflare R2 — NEVER Supabase Storage for big assets (egress fees). R2 free tier = 10GB, zero egress.
- Upload path: browser → Edge Function returns presigned PUT URL → browser PUTs bytes directly to R2 → save public r2.dev URL in DB. No Base64, bytes never touch Supabase.

## Key patterns
1. **Presign Edge Function**: use `npm:aws4fetch` AwsClient with `region:"auto", service:"s3"`, sign a PUT Request with `{aws:{signQuery:true}}` against `https://<ACCOUNT_ID>.r2.cloudflarestorage.com/<bucket>/<key>`, `X-Amz-Expires` param. Validate auth (supabase.auth.getUser with forwarded Authorization header), extension allowlist, size cap, and project ownership (a plain RLS select does the ownership check for free). Working code: see this session's file at ~/Documents/ss-rover-cloud/supabase/functions/r2-presign/index.ts and `templates/r2-presign-edge-function.ts`.
2. **Client upload**: use XMLHttpRequest for the PUT (fetch has no upload progress). Key format `userId/projectId/kind/uuid-safename`.
3. **Public share portal** (no-login read-only links): do NOT add anon RLS policies on tables. Instead one `security definer` SQL function `get_shared_project(token uuid) returns jsonb` that bundles the whole object graph; `grant execute to anon`. Token generation via a second owner-checked security-definer function. Attack surface = one UUID-keyed RPC.
4. **Same workspace component, two modes**: pass `readOnly` prop; hide admin toolboxes, disable inputs, show watermark. Avoids duplicating the viewer for the client portal.
5. **Next.js build with Supabase**: pages using the Supabase server client fail prerender without env vars. Fix: `export const dynamic = "force-dynamic"` in a layout for authed routes, and keep placeholder values in .env.local so `npm run build` passes pre-wiring.
6. **Middleware auth gate**: @supabase/ssr createServerClient in middleware; public paths = /, /login, /share/*, /auth/*.

## R2 pitfalls (each cost real debugging time)
- **Credential type confusion (403 on every signed request)**: a Cloudflare token starting `cfat_...` is an ACCOUNT API token, NOT an S3 Access Key ID. The S3 API needs the 32-hex Access Key ID + 64-hex Secret shown under "Use the following credentials for S3 clients" when the R2 token is created/rolled. If the user pastes cfat_..., stop and ask them to roll the token.
- **Verify creds yourself before blaming CORS**: `curl --aws-sigv4 "aws:amz:auto:s3" --user "KEY:SECRET" -X PUT --data-binary @file https://<acct>.r2.cloudflarestorage.com/<bucket>/test.txt` — 200 proves keys; then GET the pub-....r2.dev URL to prove public read. See `scripts/r2-smoke-test.sh`.
- **curl works but browser 403 = CORS preflight**: browsers send OPTIONS first; curl doesn't. Bucket needs a CORS policy (dashboard → bucket → Settings → CORS). Include localhost dev ports AND the production Vercel domain from day one. JSON shape in `templates/r2-cors.json`.
- **Setting CORS via S3 API needs Admin-scope token**: an Object Read&Write token gets AccessDenied on `?cors` PUT. Either dashboard, or ask for an Admin token.
- **Public read**: enable the r2.dev subdomain on the bucket; 404 (not 403) on a missing key confirms public access is on.
- R2_ENDPOINT env var is unnecessary — build the endpoint from R2_ACCOUNT_ID.

## Supabase CLI (all headless-able)
- `brew install supabase/tap/supabase`; `supabase login` needs a real browser (fails in non-TTY — have the user run it, or use SUPABASE_ACCESS_TOKEN).
- Link state lives at `supabase/.temp/project-ref`. `supabase projects list` shows the linked marker.
- Secrets hot-reload: `supabase secrets set K=V ...` — no function redeploy needed.
- Fetch anon/service_role keys programmatically: `supabase projects api-keys --project-ref REF -o json` — lets you write .env.local without the user copy-pasting from the dashboard.
- Verify schema landed: curl the REST endpoint with anon key, expect 200 on a table select.
- `supabase db query` connects to LOCAL db by default — for remote quick checks use the REST API with service_role instead.
- Exclude `supabase/functions` in the Next.js tsconfig (Deno globals break tsc).

## Vercel CLI deploy (no dashboard needed)
- `vercel login` uses a device code; run in background pty and give the user the URL to authorize.
- `npx vercel link --yes --project NAME`, then pipe env values: `grep VAR .env.local | cut -d= -f2 | npx vercel env add VAR production`.
- `npx vercel deploy --prod --yes`; verify from outside with curl (200 on routes + grep a known string in the share page HTML).
- Only NEXT_PUBLIC_* Supabase vars go to Vercel; R2 secrets live on the Edge Function.

## Vercel `--prod` alias-promotion HANG + recovery (recurring — costs real time)
In some environments `npx vercel deploy --prod --yes` builds and uploads fine but then **hangs indefinitely** on the final alias-promotion step (the process never exits; foreground calls time out at 600s, backgrounded ones run 30+ min). The build itself often DID finish. Symptoms: a NEW `https://<project>-<random>-<scope>.vercel.app` URL is minted (confirm via `npx vercel ls`), but the prod alias (`<project>.vercel.app`) never flips and the process never returns.

**Safe procedure (do not block on the hung CLI):**
1. Run the deploy in the **background** with `notify_on_complete=true` (use terminal(background=true); never rely on foreground for `--prod` here).
2. Verify the build actually completed WITHOUT waiting for the process: `grep -rl "<known-string>" .next/static` confirms your code is in the compiled client bundle. If the new URL is listed by `npx vercel ls`, the build is ready.
3. If the process is stuck on promotion, **kill it** (process(action=kill) / SIGTERM). Killing the parent deploy ORPHANS its build — the new URL will report "not ready" if you alias it directly, so a killed deploy's URL cannot be promoted.
4. **To actually go live:** run a FRESH `npx vercel deploy --prod --yes` (background) and let it complete uninterrupted, OR after a clean completed deploy, promote with `npx vercel alias set <ready-build-url> <prod-alias>`. The alias step can ALSO hang — treat the same way (verify with curl, not by waiting for the CLI).
5. Proof of live: `curl -s -o /dev/null -w "%{http_code}" https://<prod-alias>` returns 200 AND a known-string grep on the served bundle/HTML matches.

Pitfalls:
- `--prebuilt` fails ("no prebuilt output found in ./.vercel/output") unless you ran `vercel build` first — don't use it as a shortcut after a normal build.
- `timeout 90 cmd` is GNU-only; **macOS has no `timeout` binary** — use background terminal + process(action=wait/poll) instead.
- A build minted by a KILLED `vercel deploy --prod` is "not ready" for aliasing — re-deploy cleanly rather than aliasing the orphan.
- Don't claim "done" until curl on the prod alias returns 200 with the new code; the CLI exit code is unreliable when it hangs.

### DURABLE FIX: GitHub ↔ Vercel Git integration (preferred over fighting the CLI)
When the CLI alias-promotion step repeatedly fails (hanging or `fetch failed` / `not ready` for every build), stop retrying and let Vercel build+promote on its own servers:
- Dashboard: Project → Settings → Git → Connect GitHub → authorize the correct account → link `owner/repo` → Production Branch = `main`.
- After that, every `git push` to `main` auto-builds AND auto-promotes the alias reliably. This is the permanent fix for the alias hang.
- CLI blocker: `npx vercel git connect <url>` fails with `Error: Failed to link … You need to add a Login Connection to your GitHub account first. (400)`. This is a **browser OAuth step only the user can do in the Vercel dashboard** — hand them the exact steps and wait.
- Stronger verification than curl: `npx vercel inspect <prod-alias> --timeout 20` prints the alias `url` under "General" — compare its build hash to your latest `vercel ls` entry. curl alone is weak on auth-gated apps (always 302). A user screenshot showing the feature missing is GROUND TRUTH — trust it over CLI output.
- See the standalone skill `vercel-prod-deploy-verification` for the full verification loop and the `references/vercel-alias-pitfall-recipe.md` transcript.

See `references/vercel-prod-deploy-hang-recovery.md` for the exact transcript pattern and command sequence.

## Verification discipline
End-to-end proof beats "secrets saved": after any credential/CORS change, run the signed PUT + public GET smoke test, query the DB for the actual row, curl the share URL anonymously. Report each hop's status code.

## Security hygiene
If the user pastes live secrets into chat, proceed but flag it and get the token rolled after launch. Rolling an R2 token conveniently re-displays the S3 credential pair.

## Support files
- `templates/r2-presign-edge-function.ts` — known-good presign Edge Function.
- `templates/r2-cors.json` — R2 bucket CORS policy shape.
- `scripts/r2-smoke-test.sh` — signed PUT / public GET / cleanup probe.
- `references/share-token-schema.sql` — tables + RLS + security-definer share RPC pattern.
- `references/vercel-prod-deploy-hang-recovery.md` — `vercel deploy --prod` hang detection + recovery (killed orphan build, macOS no-`timeout`, alias-not-ready).
