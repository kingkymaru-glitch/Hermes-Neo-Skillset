# SS Rover Cloud buildout — session detail (2026-07-24)

Repo: ~/Documents/ss-rover-cloud · Supabase project: rover-r-platform (okzmblyboudjffaifixa, Sydney) · Bucket: ss-rover-models · Prod: https://ss-rover-cloud.vercel.app

## Schema shape (supabase/schema.sql in repo)
profiles(id refs auth.users, role check inspector|client) with `handle_new_user()` trigger on auth.users insert.
projects(owner_id, client_share_token uuid unique nullable, executive_summary) — partial index on share_token where not null.
models(project_id, file_url = public R2 URL, file_ext check glb|gltf|obj).
markers(model_id, position_x/y/z double precision, status check PASS|WARNING|FAIL, image_url).
Two SECURITY DEFINER fns: get_shared_project(share_token) → jsonb bundle (grant anon+authenticated); generate_share_token(p_project_id) → checks owner, gen_random_uuid(), grant authenticated only.

## Presign Edge Function (supabase/functions/r2-presign/index.ts)
- npm:aws4fetch AwsClient{region:"auto", service:"s3"}, sign PUT with `aws:{signQuery:true}`, X-Amz-Expires=600.
- Auth: createClient with caller's Authorization header → getUser(); then `.from("projects").select("id").eq("id",projectId).single()` — RLS itself proves ownership.
- Key layout: `{userId}/{projectId}/{models|photos}/{uuid}-{sanitizedName}`.
- Allowed ext: glb gltf obj jpg jpeg png webp gif; 200MB cap.
- tsconfig: exclude `supabase/functions` from Next's tsconfig or Deno globals break the LSP/build.

## R2 CORS JSON that worked (dashboard paste)
```json
[{"AllowedOrigins":["http://localhost:3000","http://localhost:3210","https://ss-rover-cloud.vercel.app"],
  "AllowedMethods":["GET","PUT","HEAD"],"AllowedHeaders":["*"],"ExposeHeaders":["ETag"],"MaxAgeSeconds":3600}]
```

## Verification transcript (pattern to reproduce)
1. Signed PUT smoke test with real S3 keys → 200; public read via pub-XXXX.r2.dev → 200; signed DELETE cleanup → 204.
2. r2.dev root/missing key returns 404 when public access enabled (403 would mean not public).
3. Anon RPC: `curl -X POST .../rest/v1/rpc/get_shared_project -H "apikey: $ANON" -d '{"share_token":"..."}'` → project+models+markers JSON.
4. Prod: curl / , /login, /share/TOKEN → 200; grep body for project name to prove SSR + DB.

## UI notes (MBUX design system, user-loved)
- globals.css defines full "Mercedes MBUX cockpit" token set: --dash-void #05070a, --mb-turquoise #00e5c3, --mb-amber #ffb340, --mb-red #ff4d4d, hairline borders, .dash-panel glass, .mb-btn machined buttons, gauge-arc SVGs (270° speedometer dials instead of pie charts).
- Layout stability lesson: `.mb-textarea{resize:none}` + fixed-height (150px) image thumbnails that open a zoom overlay — user complained resizable textarea pushed the photo out of the drawer.
- Overlay stack: drawer → detail modal (z-40) → image zoom (z-50); Esc closes innermost first.
- Defect images stored in R2 (marker.image_url) so zoom shows full-res original.
- THREE.PCFSoftShadowMap deprecated in three ~0.185 → use PCFShadowMap.
