# Geo-linking architecture — Cesium globe ↔ Next.js inspection app via shared Supabase

## Context
R-Tessera (CesiumJS SPA, Vite, deployed to r-tessera.vercel.app) ↔ LunaV
(Next.js 16+ App Router, deployed to lunavsolution.vercel.app). Two separate
repos, one shared Supabase project (`okzmblyboudjffaifixa`, Sydney). The
linking flow lets an inspector PIN a LunaV project onto the R-Tessera globe,
and R-Tessera viewers navigate back to the LunaV project page.

## Core pattern — two tokens, two purposes

| Token | Minted by | Stored in | Used for |
|---|---|---|---|
| `handoff_token` | LunaV RPC `mint_handoff_token` (owner-only) | `projects.handoff_token` (uuid, transient) | Authorizes the PIN write in `upsert_project_node`. NOT for sharing. |
| `client_share_token` | LunaV (project creation) | `projects.client_share_token` (uuid, permanent) | Powers `/share/<token>` public client portal. Copied into `project_nodes.lunav_share_token` for PUBLIC pins so [Go to Project] deep-links back. |

## Flow (owner pinning from LunaV)
1. LunaV dashboard → "Link to R-Tessera" button → `mint_handoff_token()` →
   opens R-Tessera with `?link=1&project=<id>&token=<handoff>&name=<n>&share=<s>`.
2. Inspector clicks the globe to set location, enters description, picks public/private.
3. Save → `upsert_project_node(p_lunav_project_id, p_handoff_token, name, desc, lon, lat, visibility, p_share_token)`.
4. The handoff token is verified server-side against `projects.handoff_token` (must match the minted UUID).
5. Public pin → `p_share_token` (the project's `client_share_token`) stored as `lunav_share_token`. Private → NULL.

## Flow (viewer on R-Tessera)
1. Project nodes load from `project_nodes` (anon SELECT, RLS allows all).
2. Click marker → info card with [View Homepage] (always → `/project/<id>/home` read-only) + [Go to Project] (gated).
3. [Go to Project]: public → `https://lunavsolution.vercel.app/share/<lunav_share_token>`; private → `/login?project=<id>`.

## Flow (Project Homepage reads the pin coordinate)
The homepage route `/project/[id]/home` reads `project_sites` for shape/polygon/remarks,
but seeds `center_lon/lat` from `project_nodes.lon/lat` when `project_sites.center` is null.
This captures the pin coordinate into the homepage's Cesium satellite view (no manual re-draw).
The pin coordinate is anon-readable (RLS `nodes_select_all`), so even read-only viewers see
the centered map.

## Key tables (all in one Supabase project)
```
projects
  └─ handoff_token uuid (minted at link time, verified on pin)
  └─ client_share_token uuid (permanent, powers /share)

project_nodes (geo-index, public read)
  └─ lunav_project_id → projects.id
  └─ lunav_share_token (copy of client_share_token for public pins)
  └─ lon, lat (pin coordinate)
  └─ handoff_token (the token that authorized the pin)

project_sites (homepage canvas, owner write)
  └─ project_id PK FK → projects.id
  └─ center_lon, center_lat (seeded from project_nodes on homepage load)
  └─ area_polygon (GeoJSON, drawn by inspector)
  └─ area_model_url (R2 .glb from LUNASCAN)
  └─ remarks (jsonb: name/date/coordinate/client/inspector/project_id)
  └─ extra_fields (jsonb array of {title,description})
```

## Deployment — two-repo Vercel auto-deploy
- **R-Tessera**: Vite SPA, commit author must be `kingkymaru@gmail.com` for Vercel webhook to fire.
  - Commit: `git -c user.name=maru -c user.email=kingkymaru@gmail.com commit ...`
  - Env: `VITE_SUPABASE_URL` + `VITE_SUPABASE_ANON_KEY` (or hardcode — see `references/hardcoded-anon-key-vercel.md`)
- **LunaV**: Next.js 16+, commit author `innovatedmaru@gmail.com` for Vercel deploy.
  - Commit: `git -c user.name=MaruTheBlackCat -c user.email=innovatedmaru@gmail.com commit ...`
  - Env: `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY` (same Supabase project)

## Pitfalls specific to this architecture
- **pgcrypto not available**: `hmac()`/`encode()` need the `pgcrypto` extension (not enabled by default).
  Fix → `gen_random_uuid()` (core PG13+) + store the token on the project row. See the SKILL.md body.
- **Cesium in Next.js production build**: static `import { Viewer } from 'cesium'` breaks the bundle
  (`\0` in wasm/base64 template literals → `SyntaxError`). Fix → CDN runtime load. See `cesium-resium-react`
  skill `references/cesium-nextjs-cdn-load.md`.
- **Cesium CDN race condition**: the homepage camera `flyTo` fires before the CDN script finishes loading.
  Fix → `cesiumReady` state as a `useEffect` dep. Same ref as above.
- **Popup blocker**: `window.open(...)` called after `await supabase.rpc(...)` is blocked by browsers
  (popup not in the same user-gesture tick). Fix → open the window synchronously first, then set its
  `location.href` after the await.
- **Autosave cursor reset**: controlled remarks inputs bound directly to an async-saved state re-render
  on every keystroke (cursor jumps to front). Fix → local form state as source of truth + 600ms debounced
  persist. Generic React pattern, not Cesium-specific.

## Agent-side verification (live probe)
Use the anon key to confirm state from the agent (no browser needed):
```js
const { createClient } = require('@supabase/supabase-js');
const sb = createClient(URL, ANON);
// handoff column exists?
await sb.from('projects').select('handoff_token').limit(1);
// mint runs (anon → expect 'Unknown project', NOT 'function does not exist')
const r = await sb.rpc('mint_handoff_token', { p_project_id: '00000000-0000-...' });
console.log(r.error?.message); // 'Unknown project' == fixed
// node center readable?
await sb.from('project_nodes').select('lon,lat').eq('lunav_project_id', projectId).maybeSingle();
```
