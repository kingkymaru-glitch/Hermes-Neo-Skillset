---
name: digital-twin-shm
description: "Build/extend MARU my-digital-twin dashboard: Vite+React+Cesium/Resium+Supabase SHM SPA—spatial pins, Layer 2 edge coordination, S22 android node, IoT HUDs. Compose with vite-scaffold-verification, cesium-resium-react, maru-client-layer-socket, external-api-probe. See references/* for live-feed, layer orchestration, placement, and static GLB model patterns."
---

# Digital Twin SHM

Covers MARU dashboard work in `my-digital-twin`.

## Skill boundary vs adjacent skills
- Use `vite-scaffold-verification` for fresh Vite+React project scaffolding.
- Use `maru-client-layer-socket` for client-authored spec-driven layers.
- Use `cesium-resium-react` for 3D-vue-level Cesium + Resium app-shell patterns.
- Use `external-api-probe` for AISstream / vessel live-feed diagnosis.

## Project-shape assumption
This repo uses a single `App.jsx` provider stack:
- `EdgeDataProvider`
- `GovernanceProvider`
- top-level `App` shell

`DashboardInner` is the inner dashboard layout and `<Viewer>` mount site.

## Minimal-change rule
Treat `src/App.jsx` as the single source of truth for placement/runtime logic.
Prefer new static render branches over broad layer-system changes unless the user asks for governance/toggling behavior.

## API pause rule
If the user says other API-layer work is paused, DO not add or restore tile provider rows elsewhere. Proceed with the requested localized work only.

## Desktop assets intake rule
When a user asks to upload a local desktop asset into MARU:
0. **Strip spaces/special chars from the filename BEFORE copying** (e.g. `Dam Gate.glb` → `dam-gate.glb`). A space in a GLB filename is a classic Cesium URI gotcha — the path round-trip can silently fail to load. No-space filenames remove the entire risk class. (Verified: `curl` of the raw-space path returns HTTP 000; the encoded path returns `200 model/gltf-binary`.)
1. Copy it into `public/assets/`
2. Reference it with `/assets/<filename>` rather than desktop paths or filesystem imports
3. **Verify it serves** before claiming it's wired: `curl -s -o /dev/null -w "%{http_code} %{content_type} %{size_download}\n" http://localhost:5174/assets/<filename>` must return `200 model/gltf-binary <bytes>`.
4. **For standalone 3D HTML viewers (Three.js etc.):** copy the `.html` AND any sibling assets it references (e.g. `logo.png`) into `public/models/`, then load it from a sandboxed iframe at `/models/<file>.html` — NOT into `public/assets/` and NOT in-globe. Copy siblings to the same `public/models/` folder so relative `src`/`href` resolve. Verify each serves: `curl -s -o /dev/null -w "%{http_code} %{size_download}\n" http://localhost:5174/models/<file>`. (A transient `702` byte size from `curl` is a request race — re-fetch to confirm the true size.)

## Static GLB intake recipe
**Prefer the pin + iframe-flyout pattern in `references/pin-iframe-3d-viewer.md`** — it avoids the in-globe renderer crash entirely. Legacy in-globe recipe: `references/static-glb-structural-models.md` (use only for lightweight GLBs the user insists live on the globe).
Do not extend `layerRegistry`/`MapControlPanel` until visibility is proven or explicitly requested. (When the user DOES ask for a toggle, see `references/adding-entity-layers.md` + the flag-gated pattern below.)

## CRITICAL: do NOT render heavy GLB *inside* Cesium
This repo hit a hard renderer crash — `RangeError: Failed to set the 'length' property on 'Array': Invalid array length` deep in Cesium `View.js updateFrustums` / `Scene.js executeCommandsInViewport` — triggered by toggling a structural model's GLB ON. Heavy models rendered in-globe destabilize the camera frustum culler and take the whole viewer down with a "Rendering has stopped" error (seen with the Temenggor Dam Gate GLB).

**Preferred pattern (verified working): isolate heavy 3D in a sandboxed iframe.** Place a lightweight clickable pin at the asset's geo location; clicking it opens the standalone 3D viewer in a modal flyout (`<iframe sandbox="allow-scripts allow-same-origin allow-pointer-lock" src="/models/<viewer>.html">`). The heavy WebGL lives in the iframe, decoupled from Cesium, so it can never crash the globe. Full recipe: `references/pin-iframe-3d-viewer.md`.

For a complete trace of how node records (`model`/`portal_url` fields) flow through
`MapNodePins`, `DamGatePin`, `NodeEditorModal`, and the `structural_models` layer
toggle — including which entity renders what, where GLBs actually load, and why
they're never in-globe — see `references/node-glb-data-flow.md`.

**Only render a GLB in-globe if it is lightweight AND the user explicitly insists it live on the globe** — and even then, follow the render-loop-safe recipe below. Treat in-globe GLB as a liability, not a feature.

## In-globe GLB recipe (render-loop-safe, LAST RESORT)
If you must render in-globe: prefer loading imperatively after the viewer is confirmed (`viewer.entities.add({ model: { uri, scale, minimumPixelSize, maximumScale, scaleByDistance } })`), not resium `<ModelGraphics>`.
- **CRITICAL — do NOT track loaded/failed IDs in state and key the effect on them.** That pattern causes a render-loop bug (cleanup removes the entity next render, then it's filtered as "already loaded" and never re-added → toggle does nothing visible AND churns the scene). Key the effect ONLY on `[viewer, showStructural]`.
- When ON: `viewer.entities.add(...)` each model, push entity refs into local `added[]`, wrap each in try/catch, guard with `entity.model?.readyPromise?.catch?.(...)`.
- Return cleanup that removes ONLY `added[]`.
- When OFF: effect early-returns; cleanup runs first. No state bookkeeping, no loop.
This is non-fatal for a *missing/duff* `.glb`, but it does NOT protect against the frustum-crash above — which is why the iframe isolation is preferred for anything heavy.

## Malaysia coordinate defaults
Use documented placeholders from `references/static-glb-structural-models.md` when exact coords are unavailable.

## R-Tessera (successor project)
R-Tessera (`~/Documents/R-Tessera`, live `https://r-tessera.vercel.app`, dev `:5174`)
is the successor to MARU, built on the same Vite+React+Cesium stack. As of the
2026-08-07 rebuild it is a LEAN 2-box app — NOT the old 5-Box:

- **Box 1 — Base layers:** bottom-left 4-button selector (Map/OSM · Satellite/Esri
  raster + 3D globe / 2D flat). Recipe lives in `cesium-resium-react`
  (`references/base-layer-switching.md`).
- **Box 2 — API layers:** top-right Map Control drawer toggling live feeds:
  Earthquakes (USGS 2.5_week, keyless), Volcano Watch (NASA EONET, keyless),
  Maritime (live vessels, KEY-GATED — disabled until `VITE_MARITIME_PROVIDER` +
  key set; aisstream WebSocket or VesselAPI poll; NEVER a mock fleet),
  Global Weather (Open-Meteo point forecast, KEYLESS — batched multi-station
  call, no API key; see `references/open-meteo-keyless-weather-layer.md`).

**Rebuild rules the user asserted (2026-08-07) — embed these:**
- "Use the base layers as in OSIRIS" → COPY the pattern (4-mode selector + token-free
  raster + scene-mode morph), do NOT `git`/`cp` the OSIRIS Next.js code — different
  stack (MapLibre). Adapt to Cesium.
- "Remove all logo" → drop the brand wordmark/header; functional panels only.
  Also `.gitignore` stray `public/*.png` / demo `public/*.json` (e.g.
  `r-tessera-logo.png`, `suda-feed.json`) so they never get committed as
  dead assets on the next `git add -A`.
- "Do not put any mock data, or handler for data that is not available" → feeds
  return `{events:[], error}` on failure; unavailable features render as
  disabled-with-tooltip, never throw, never fabricate positions.
- **ROVER-KIT / real-data Supabase layers — same no-fake-data spirit, extended to the
  DB:** NEVER seed demo/fake camera (or other) rows into Supabase or the globe to
  test. To test, route the REAL Mac webcam via Luna EDGE (`ws://<mac-lan-ip>:8000/ws`
  raw binary JPEG) and register ONE real `cctv_cameras` row pointing at it. Layer
  code mirrors ProjectNodes (anon `select`, imperative Cesium entities,
  `ScreenSpaceEventHandler` LEFT_CLICK → flyTo + draggable ws feed window). Full
  recipe: `references/r-tessera-supabase-entity-layer.md`.
- Default app runs with NO keys: USGS + EONET are keyless; only maritime needs keys.

### ROVER-KIT CCTV layer (Supabase-backed entity layer — the real-data pattern)
Unlike the keyless public feeds (USGS/EONET), ROVER-KIT CCTV cameras are REAL
`cctv_cameras` rows (shared Supabase `okzmblyboudjffaifixa`, anon read). The globe
shows only real rows — NO demo item is ever pushed (user-decreed 2026-08-25). R-Tessera
stays VIEW-ONLY; camera edits live in LunaV Solutions → Vision tab. Layer build recipe,
node-click floating webcam window, and paired admin form + SQL migration:
`references/r-tessera-supabase-entity-layer.md`.

### Pitfall — "rebuild from scratch" must reconcile against the ACTUAL repo, not old notes
When the user says "redo R-Tessera from the start" / "scrap all code" / "fresh start",
the 5-Box patterns in this skill (SUDA, SETTING_ITEMS, monolithic App.css box headers,
InsightsPanel, IngestionPanel, governance registry, node bridge) are OBSOLETE — those
files were deleted and GitHub `main` was orphaned (2026-08-07). Before editing, confirm
the on-disk state with `find src -type f`. Carry over ONLY the real feed logic (the
USGS/EONET drivers + Cesium entity-render pattern from the lean app); drop all
mock-sensor / GLB / node / Supabase scaffolding. Do NOT re-add Boxes 3–5 (P.E. engine,
Tolerant Socket, SUDA) unless the user explicitly asks. The user's stated rebuild intent
was: Box 1 = OSIRIS-style 4-mode base selector (Map/Satellite raster × 3D/2D, bottom-left),
Box 2 = situational + maritime + volcano with the existing lean theme, NO logos, NO mock
data. Verified fresh-start deploy recipe (git orphan + Vercel.json Vite-SPA fix) in
`references/r-tessera-build-patterns.md`.

The old 5-Box artifacts (P.E. engine, Tolerant Socket, SUDA simulator, governance,
nodes, GLB studio, IoT HUD, Settings) were deleted in the rebuild; re-add any as
its own chunk later. Historical 5-Box build patterns live in
`references/r-tessera-build-patterns.md` (mostly superseded — verify before reuse).

**OSIRIS API catalog** (the donor dashboard, `simplifaisoul/osiris` in
`~/Downloads/osiris-master`): `references/osiris-api-catalog.md` — full 56-route
list with which feeds are keyless (the only ones R-Tessera should borrow). Rebuild
the catalog with `scripts/scan-nextjs-api-endpoints.py`.

## OSIRIS layer adoption references (Box 1 pattern donor)
OSIRIS (`simplifaisoul/osiris`, Next.js+MapLibre) is a PATTERN donor, never a migration target. Three reference files cover it:
- `references/osiris-adoption.md` — as-built record of adopted patterns (viewport dedup, live counts, Context layer, RECON placeholder, shortcuts).
- `references/osiris-layer-adoption-recipe.md` — 9-wire recipe for adding a governed keyless entity layer (the OSIRIS→MARU Box 1 pattern).
- `references/osiris-source-map.md` — actual `osiris-master` on-disk layout: real source lives in `src/` + `intel/` (NOT a root `app/`), which files hold the LayerPanel/OsirisMap/SDK patterns, and the `search_files` `.next`-cache flood gotcha (use terminal `find`). Read this before grepping OSIRIS for a new adoption.
- `references/osiris-api-catalog.md` — FULL inventory of OSIRIS's 56 Next.js API routes and the external endpoint each hits (keyless USGS/EONET/FIRMS/GDACS/adsb.lol vs key-gated RECON/Cloudflare/Gemini). Use this to pick Box-1-adoptable feeds. Rebuild with `scripts/scan-nextjs-api-endpoints.py <repo-root> [extra-src-dirs...]`.

### Pitfall — Graphify mirror masquerades as the source note
The vault's `Graphify/` folder holds AUTO-GENERATED extracted mirrors of real notes
(with a `source_file:` front-matter pointer to the original). A `search_files` for a
topic (e.g. "OSIRIS") will surface BOTH the real `DT/` note AND its `Graphify/` copy.
The `Graphify/` copy is skeletal (just connection stubs) — do NOT treat it as the
authoritative content. Read the `DT/` / `Projects/` source, or the OSIRIS references
below, and ignore `Graphify/` for substance. In one session the real `DT` note had
been renamed/emptied to "Untitled" and only the Graphify mirror remained — verify the
source path actually exists before quoting it.

## Node store: durable Supabase + localStorage (bridge is now LEGACY)
**Root cause lesson:** the original node store was a LOCAL Obsidian-file bridge
(`server/nodes-bridge.mjs` at `http://localhost:8799/api/nodes`). It cannot run
on Vercel, so on every fresh load / deploy the `GET` returned nothing and ALL
nodes vanished on refresh. That is the real "nodes don't persist" bug.

**Current pattern (durable):** `src/nodesService.js` writes to the Supabase
`nodes` table when configured AND mirrors to `localStorage`, so refresh/deploy
retention works even before the table exists or RLS is applied. Boot hydration +
fail-soft CRUD. See `references/node-persistence-durable.md` for the full
service shape, field normalization (snake_case DB ↔ camelCase bridge), App.jsx
wiring, the `sql/nodes_table.sql` migration, and the `portal_url` clickable-link
modal field. The bridge now only does local Obsidian sync — it is NOT production
persistence. Do NOT re-introduce scattered `fetch(NODES_API)` calls.

Legacy bridge details (localhost proxy, **port collision: 8787 owned by an
unrelated proxy -> bridge uses 8799**, CORS, list-with-body, `buffer()` body
parse, dangling-helper-ref crash) are in `references/obsidian-nodes-bridge.md`
for historical context only.

Frontend pattern: `nodes`/`showNodes` in `EdgeDataContext`; ONE import from
`nodesService` (alias its `deleteNode` as `deleteNodeStore` to avoid colliding
with the local handler) in `App.jsx`; `MapNodePins` + `NodeEditorModal`; direct
context toggle (NOT a LayerManager tile) in `MapControlPanel`.

### Pitfall — a directive describes components that don't exist in this checkout
Before editing, RECONCILE the directive against the actual code: grep the whole
repo (case-insensitive) for every distinctive string the directive names. If the
strings don't exist (e.g. a "fake INCLINOMETER/VIBRATION/STRAIN/MTESLA HUD",
"New Node Group"/"Create Group" buttons, a `portal_url` field, a hardcoded
`lunavsolution.vercel.app`) and there's no git history for them, the directive
targets a different/newer branch or the live site — NOT this disk state. Do NOT
fabricate edits to nonexistent components or invent a backend table you can't
create. Instead: (1) do the work that is genuinely real and verifiable, (2)
flag the non-applicable items as N/A with proof (the grep result), (3) confirm
the already-satisfied items instead of fake-re-editing them, and (4) ask which
branch/URL is the real target if the gap is large. In this session that split
was: #1/#3/#5 already done, #2 nonexistent (N/A), #4/#6 missing feature (added
real `portal_url` field+link), #7 real root cause (localhost bridge → Supabase
+localStorage). The user accepted the verification-first approach implicitly by
not objecting to the reconciliation framing.

### Pitfall — "ghost" node: renders on the globe but is NOT in source or the intended vault
If a map marker/node (e.g. an old demo site like "Temenggor Dam Gate") appears
but `grep` across `src/`, `public/`, and the target vault (`Obsidian/DT Nodes`)
finds nothing, the data is being served by a **STRAY BRIDGE PROCESS**, not the
one your code talks to. Classic cause: both the OLD repo (`my-digital-twin`,
reading `obsidian_maru_1/DT Nodes`) and the NEW fork (R-Tessera, reading
`Obsidian/DT Nodes`) are checked out and you've run `npm run dev` in each — so
TWO copies of `nodes-bridge.mjs` run on different ports reading different
vaults. A `NODES_API`→port mismatch (code says 8899, the real bridge is on 8799)
hides it: the app silently loads an empty source while the stray bridge feeds
the visible node. Full diagnosis + fix recipe: `references/ghost-node-debugging.md`.

### Pitfall — dangling reference after a refactor (silent runtime crash)
`npm run build`/`lint` PASS even if a handler calls a function you deleted
earlier in the same session. Biome's `no-unused-vars` flags an unused *definition*
but does NOT catch a call to a now-undefined name inside an event handler
(`createNode`/`updateNode`/`deleteNode` called `refreshNodes()` after it had been
removed → `ReferenceError` on every Save/Delete at runtime, build green). Fix:
after any refactor that removes a helper, grep for its old name across handlers
and replace the call sites (here: a `reloadNodes()` re-fetch). Also delete any
dead renamed helpers (`refreshFocusCoord`) — Biome WILL warn on those, but only as
a warning, not an error.

### New node UX — prefill from viewport center
When creating a map node, seed Lat/Lon from the coordinate the user is looking
at (Cesium `pickEllipsoid` at the canvas center via `cameraFocusLonLat()`), but
keep the fields editable; offer a "◎ Use map center" re-grab button for new nodes.
Full recipe + modal wiring + CSS: `references/new-node-viewport-center.md`.

## Photogrammetry intake (RealityScan-style → MARU GLB)
When the user asks to "install RealityScan" to feed scanned models into the twin:
RealityScan desktop is Windows+NVIDIA only and cannot run on this arm64 Mac. Diagnose
first (sw_vers, brew search, ~/Downloads, Xcode ObjectCapture presence), then offer a
working route (S22 mobile app / Apple Object Capture / Windows VM) — never claim a
macOS install. The scan output is a `.glb` that then flows into MARU via the GLB-intake
recipes above. Decision tree + env check + route guidance: `references/photogrammetry-intake.md`.

## Three.js defect-annotation pattern (plain Three.js twins — e.g. ss-rover-cloud Viewer3D)
When building Point/Line/Box markup on a 3D inspection twin in plain Three.js (no
R3F), preserve the severity counting model and avoid the hover-opacity trap:
- Each annotation = ONE row with a `status` (PASS/WARNING/FAIL); severity totals are
  `filter(m => m.status===X).length`. Adding Line/Box kinds must NOT change this
  (one annotation = one defect, never count vertices/sub-parts).
- Data: `kind: 'point'|'along'|'box'` + `geometry_json { points?, size?, color?, dash?,
  thickness? }`. Box position = CENTRE (build Box3 from centre +/- size/2), not a
  corner — single-click-centre + drawer sliders beats two-corner drag on empty space.
- Line endpoint nodes MUST scale with thickness or thin lines get fat blobs:
  `radius = clamp(thickness*0.9, 0.18, 1.5)`.
- Box stays SEE-THROUGH: edges ~0.9 opacity + faint fill ~0.08 with `depthWrite:false`.
  NAIVE hover that forces `opacity=1`/`0.45` makes the fill solid and hides the
  model. Fix: tag each hoverable mesh `userData.baseOpacity` (tube .95, node 1, edge
  .9), tag the box FILL `userData.skipHover=true`, and in hover set
  `opacity = hovered ? base : base*0.4` (skip skipHover meshes).
- Hover-select: `pickMarker(e)` raycasts only meshes with `userData.markerId`;
  clicking a line/box when NOT armed calls `onMarkerClick(id)` (same path as a pin).
- Reuse the point-node editor drawer for Line/Box: Title/Severity/Remarks/Photo/
  Delete + an "Annotation Style" block (colour, Solid/Dashed, thickness / X/Y/Z size).


