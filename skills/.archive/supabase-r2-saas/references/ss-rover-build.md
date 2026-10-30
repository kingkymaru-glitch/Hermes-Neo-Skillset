# SS Rover Cloud — build record (2026-07-24)

Live artifacts (for resuming work):
- Repo: /Users/kamarulhk/Documents/ss-rover-cloud (Next.js 16, Tailwind 4, three 0.185)
- Prod: https://ss-rover-cloud.vercel.app (Vercel project ss-rover-cloud, org rover-r-3d)
- Supabase: project ref okzmblyboudjffaifixa ("rover-r-platform", Sydney) — distinct from old MARU ref eobkcsxwwpszyzbwpqqy
- R2: bucket ss-rover-models, public base https://pub-61fd8335ae2e4e30b8fbe7a20f976188.r2.dev, account 33de1b89629347c527b3cebb700388b9
- Edge Function: r2-presign (secrets: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET, R2_PUBLIC_BASE)

## Schema shape (supabase/schema.sql in repo)
- profiles(id ref auth.users, role check inspector|client) + on_auth_user_created trigger
- projects(owner_id, project_name, client_share_token uuid unique, executive_summary, analytics_comment)
- models(project_id, model_name, file_url, file_ext check glb|gltf|obj)
- markers(model_id, position_x/y/z, title, status check PASS|WARNING|FAIL, description, image_url)
- RLS: owner-only `for all` policies via EXISTS join up to projects.owner_id
- Public path: get_shared_project(share_token uuid) security-definer jsonb RPC (grant execute to anon);
  generate_share_token(p_project_id) checks ownership then rotates uuid
- Migrations after initial: applied via files in supabase/migrations/ + `supabase db push --include-all`
- NOTE: adding a column consumed by the share portal requires ALSO updating get_shared_project's jsonb_build_object (did this for analytics_comment)

## Presign function key lines (supabase/functions/r2-presign/index.ts)
- Auth: createClient with caller's Authorization header, `auth.getUser()`, then RLS-checked
  select on projects to confirm ownership (no service key needed)
- Sign: `new AwsClient({..., region:"auto", service:"s3"})`;
  target URL + `X-Amz-Expires=600`; `r2.sign(new Request(target,{method:"PUT"}), {aws:{signQuery:true}})`
- Key: `${user.id}/${projectId}/${models|photos}/${crypto.randomUUID()}-${safeName}`
- deno.json with `"lib": ["deno.window"]` beside it; folder excluded in root tsconfig

## Frontend patterns that worked
- One ProjectWorkspace component, `readOnly` prop switches inspector vs /share/[token] client portal
  (hides toolbox/logout/share, disables inputs, adds watermark) — no duplicated UI
- Viewer3D: plain three.js in useEffect (not R3F), CSS2DObject pins colored by status,
  `liveRef` pattern so the stable click handler sees fresh props; dynamic() import ssr:false
- Upload: XHR PUT for progress %, model URL saved to DB only after 2xx
- Drawer images: fixed-height thumbnail + click-to-zoom overlay (prevents textarea/img layout push);
  `.mb-textarea { resize: none; }` stops user-resize pushing layout
- Report rows clickable → detail modal; row action buttons wrapped in div with stopPropagation
- Esc closes overlays innermost-first (zoom → detail → drawer)

## Design language (user preference: Mercedes MBUX dash)
Tokens in globals.css: #05070a void, glass panels (blur 22px, hairline rgba(140,170,200,.14)),
turquoise #00e5c3 / amber #ffb340 / red #ff4d4d, tabular-num "gauge-readout" mono digits,
270° SVG gauge arcs (rotate 135°, strokeDasharray fraction) instead of pie charts,
startup dash-sweep stroke animation. PASS/WARNING/FAIL chips with glowing dot.

## Ops notes
- User pasted R2 secrets in chat — flagged for rotation post-launch (roll token = new S3 pair, re-run secrets set)
- Vercel login/link/env/deploy fully CLI-driven; `vercel env add` reads value from stdin
- three.js 0.160+ deprecates PCFSoftShadowMap → use PCFShadowMap
