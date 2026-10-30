# R2 presign + share-token portal notes (from ss-rover-cloud build, 2026-07)

## R2 CORS JSON (paste in bucket Settings -> CORS policy)
```json
[
  {
    "AllowedOrigins": ["http://localhost:3000", "http://localhost:3210", "https://YOUR-APP.vercel.app"],
    "AllowedMethods": ["GET", "PUT", "HEAD"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

## Edge Function presign core (Deno)
```ts
import { AwsClient } from "npm:aws4fetch@1.0.20";
const r2 = new AwsClient({ accessKeyId, secretAccessKey, region: "auto", service: "s3" });
const target = new URL(`https://${accountId}.r2.cloudflarestorage.com/${bucket}/${key}`);
target.searchParams.set("X-Amz-Expires", "600");
const signed = await r2.sign(new Request(target, { method: "PUT" }), { aws: { signQuery: true } });
// return { uploadUrl: signed.url, publicUrl: `${publicBase}/${key}` }
```
Validate inside the function: auth.getUser() first; whitelist extensions; cap size; verify row ownership via RLS-scoped select (fetch the project with user's JWT — null = not owner).
Key scheme: `${user.id}/${projectId}/${models|photos}/${uuid}-${safeName}`.

## Share-token public portal (no anon table policies)
- Column `client_share_token uuid unique` (null = private) + partial index.
- `get_shared_project(share_token uuid) returns jsonb` — SECURITY DEFINER, stable, builds the whole nested bundle (project -> models -> markers) with jsonb_agg; `grant execute to anon, authenticated`.
- `generate_share_token(p_project_id)` — SECURITY DEFINER, raises unless `owner_id = auth.uid()`, rotates token.
- Frontend: same workspace component with `readOnly` prop — hides admin panels, disables inputs, shows watermark. One component, two modes.

## RLS pattern for nested ownership
Child tables check ownership by EXISTS-join up to projects.owner_id = auth.uid() (markers -> models -> projects). `for all using(...) with check(...)` on each.

## Misc
- Profile auto-create: trigger on auth.users insert -> profiles row (security definer fn).
- Next 16: `params` is a Promise in page props — `const { id } = await params`.
- middleware.ts convention deprecated in Next 16 (warns, still works; rename to proxy eventually).
