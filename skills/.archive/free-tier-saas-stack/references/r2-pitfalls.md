# R2 debugging transcript (SS Rover session, 2026-07-24)

## Failure 1: presigned PUT always 403
Symptom: browser console `Prefetch response is not successful. Status code: 403` on
`https://ACCT.r2.cloudflarestorage.com/...`; models table empty (upload never landed).

Cause: user supplied `R2_ACCESS_KEY_ID=cfat_EFIJ...` — a Cloudflare **account API token**,
not an S3 Access Key ID. SigV4 signatures computed with it are always rejected.

Fix: Cloudflare → R2 → Manage R2 API Tokens → token → "Use the following credentials for
S3 clients" shows the real pair: Access Key ID (32 hex) + Secret (64 hex). If no longer
displayed, "Roll" the token to re-show (also rotates an exposed secret).

Direct verification (bypasses all app code):
```
curl --aws-sigv4 "aws:amz:auto:s3" --user "KEY:SECRET" \
  -X PUT --data-binary @/tmp/t.txt \
  "https://ACCT.r2.cloudflarestorage.com/BUCKET/smoke-test.txt" -w "%{http_code}"
# 200 = creds good. Then:
curl "https://pub-XXXX.r2.dev/smoke-test.txt" -w "%{http_code}"   # 200 = public access good
# cleanup: -X DELETE same signed URL (204)
```

## Failure 2: 403 persists after keys fixed — "Preflight response is not successful"
curl succeeded but browser failed: curl sends no OPTIONS preflight. Bucket had no CORS policy.

Attempted fix via S3 API:
```
curl --aws-sigv4 ... -X PUT --data-binary @cors.xml -H "Content-MD5: $MD5" \
  "https://ACCT.r2.cloudflarestorage.com/BUCKET?cors"
# => AccessDenied — Object Read & Write token lacks bucket-admin scope
```
So CORS must be pasted in the dashboard (bucket → Settings → CORS policy) unless the token
has Admin Read & Write. After saving, hard-refresh (Cmd+Shift+R) — failed preflights cache.

## Diagnostic shortcuts
- `pub-*.r2.dev/random-key` → 404 means public access enabled; 403 means it isn't.
- Edge Function unauth POST → 401 `UNAUTHORIZED_NO_AUTH_HEADER` means deployed + gated correctly.
- Check what actually landed in DB via PostgREST + service_role key (NOT `supabase db query`,
  which targets local):
  `supabase projects api-keys --project-ref X -o json` → service_role → curl rest/v1/table.

## Supabase/Vercel CLI notes
- `supabase login` and `npx vercel login` both need interactive browser auth: run as
  background pty processes, watch for "Congratulations"/success string.
- `supabase secrets set` hot-reloads Edge Functions — no redeploy needed after secret change.
- `npm i -g vercel` can exit -13 (perm); `npx vercel` works fine.
- Pipe env values: `grep KEY .env.local | cut -d= -f2 | npx vercel env add KEY production`.
