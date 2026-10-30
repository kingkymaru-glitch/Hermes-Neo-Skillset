# Cesium globe <-> Three.js detail viewer integration ("link don't embed")

Reference for the founder-class question: "how do we merge / integrate our
geospatial map platform with our 3D-inspection app?" Established during the
R-Tessera (Cesium/Resium globe) <-> LunaV (Three.js inspection) discussion.

## The core finding
This is NOT a merge of two equal platforms. It is **master/detail via a pointer**:

- **Cesium globe = GEOGRAPHIC INDEX (master).** Renders the planet, situational
  layers, and geo-anchored ASSET pins. Has NO notion of a detailed model.
- **Three.js stage = INSPECTION WORKSPACE (detail).** Loads ONE model (GLB/GLTF/
  OBJ) from a URL, renders markers/proxies on it, in a local scene. Has NO
  geographic context.

The value is a single source of truth: one asset (the GLB) referenced by a
geographic record (a lat/lon pin on the globe) AND by an inspection record
(markers in the detail app). You don't merge codebases; you connect them.

## Why "embed" is the wrong shape (coordinate-space incompatibility)
Cesium renders in **WGS84 / ECEF** on a globe. Three.js (raw `three` /
`react-three-fiber`) renders a **local Euclidean scene** — LunaV's `Viewer3D.tsx`
re-centers the GLB at the origin and scales it to a 25-unit footprint
(`box.getCenter`, `obj.position.sub(center)`, `scale = 25 / max(size)`). It has
no lon/lat.

Consequences:
- You CANNOT drop a Three.js model into the Cesium globe without a full rewrite
  (Cesium3DTileset + cartographic glTF positioning, terrain alignment). Project,
  not merge.
- Two WebGL contexts in one DOM (Cesium canvas + Three.js canvas stacked) fights
  for the GPU + event loop. **Reject it. LINK, DON'T EMBED.**
- Keep them as SEPARATE routes / deploys.

## The concrete link pattern
1. **Globe side (master)** adds an ASSET layer: geo-anchored assets, each with a
   pointer to the detail app's project id.
   - Cheapest start: static JSON in `/public` (matches how R-Tessera bundles
     cables — keyless, CORS-free, ships in the build). Shape:
     `{ id, name, lon, lat, detail_project_id, owner }`.
   - Promote to a Supabase table only if assets must be editor-managed.
2. **Click an asset pin** -> open the detail workspace (e.g.
   `window.open('https://<detail-app>/project/<detail_project_id>')` or a route
   handoff). The detail app already loads model + markers from its own DB
   (e.g. LunaV's `project/[id]` reads `projects -> models -> markers`).
3. **Detail side (optional back-link):** add a `geo_anchor jsonb` (lon/lat) to
   the detail project for "where am I" + back-to-globe link. Not required for
   the one-way drill-down.

## What each side keeps unchanged
- Cesium app: token-free basemaps, situational layers, Google 3D base
  (see `google-3d-tiles.md`), asset pins as `<Entity>` at
  `Cartesian3.fromDegrees(lon, lat, h)`.
- Three.js app: existing `Viewer3D` stage as-is — it only needs `modelUrl` +
  markers and cares nothing about the globe. The seam is purely the
  `detail_project_id` pointer, not the rendering.

## Decision points to confirm with the founder before building
- **Direction:** one-way (globe -> detail) vs two-way (detail back-link)?
- **Pointer store:** static JSON (`/public`) vs Supabase table? Recommend
  static JSON to start (matches keyless/cable approach), promote only if
  editor-managed assets are needed.

## Anti-patterns to reject
- Copying the detail viewer's React/Three code INTO the globe app (doubles
  maintenance across two repos/deploys).
- Porting the globe into the detail app as a component (Cesium-in-Next 16 is its
  own world of pain; detail app is Next 16 with breaking changes).
- Embedding one WebGL canvas inside the other.
- Treating "merge" as "combine UIs" — the job is connect, not combine.
