# SS Rover Cloud — architecture & Phase 1.5 feature shape

## Tables (Postgres / Supabase)
- `profiles` (auth trigger `handle_new_user`)
- `projects` (owner_id, project_name, executive_summary, analytics_comment,
  client_share_token uuid unique)
- `models` (project_id, model_name, file_url [R2], file_ext glb/gltf/obj)
- `markers` (model_id, position_x/y/z, kind point|along|box, geometry_json,
  status PASS|WARNING|FAIL, image_url [R2 photo])
- `documents` [Phase 1.5] (project_id, file_name, file_url, file_ext, kind,
  file_size_bytes)
- `proxies` [Phase 1.5] (project_id, label, shape, pos/scale/rotation, color,
  texture_url)

## Access paths
- Owner (authenticated inspector): full CRUD via RLS policies keyed on
  `projects.owner_id = auth.uid()`.
- Anonymous client: ONE `security definer` RPC `get_shared_project(share_token)`
  returns the whole bundle as JSONB (models+markers, documents, proxies). No
  table-level anon policies. Token minted/rotated by `generate_share_token`.

## Client pages
- `src/app/project/[id]/page.tsx` — server component; fetches models/markers/
  documents/proxies; mounts `<ProjectWorkspace initial={…} />` (inspector mode).
- `src/app/share/[token]/page.tsx` — calls `get_shared_project`; mounts
  `<ProjectWorkspace readOnly … />` (client portal; toolbox hidden, watermark on).
- `src/components/ProjectWorkspace.tsx` — the cockpit: tab bar
  `3d | report | analytics | docs`, 3D left console (models + Spatial Proxy
  Toolbox), right drawers (finding editor, proxy editor), modals (summary, share,
  add-model w/ point-cloud note).
- `src/components/Viewer3D.tsx` — raw Three.js scene. Proxy render effect builds
  a `THREE.Mesh` (BoxGeometry default, PlaneGeometry if `shape==='plane'`),
  applies `MeshStandardMaterial`, loads `texture_url` via `TextureLoader`
  (cached in a ref), positions/scales/rotates from the proxy row.

## Phase 1.5 features (built this session)
1. **Documents tab** — upload pdf/jpg/png/webp/gif → R2 `/docs/`; card list with
   Download + Remove. Wired through `documents` table + `WorkspaceData.documents`.
2. **Spatial Proxy Toolbox** — ◼ Cube / ▭ Plane buttons spawn a proxy at
   (0,0,0); right drawer edits Scale X/Y/Z (0.1–20), Rotate X/Y/Z (±180°),
   color, and "Apply Texture (JPG)" upload mapped to the material. Persists to
   `proxies`; visible in the read-only share view.
3. **Point-Cloud note** — "Add Model" opens a modal carrying the LiDAR/.las/.laz
   → 3D Tiles / lightweight .glb guidance text.

## Fail-safe convention (keep this for future features)
Every DB write sits in try/catch and surfaces an error via the toast system
(`toast(msg, "error")`). Missing tables/RPC therefore show a red toast instead of
crashing — the app builds and runs even before the migration is applied.
