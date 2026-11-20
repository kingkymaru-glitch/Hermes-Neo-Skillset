# CDM desktop conversion + embedded 3D context pipeline

## Decision: Option A — desktop installer + cloud DB

Rationale (MARU): heavy processing power available locally; that work belongs on the machine, not
on serverless/Vercel. The webapp is already cleanly layered, so wrapping costs days, not a rewrite.

Alternatives: **B — on-prem Docker server** (revisit if clients demand data residency) and
**C — fully offline desktop** (~2–3 months; offline map tiles + bundled Python are the painful 80%).

## Layer-by-layer effort

| Layer | Effort | How |
|---|---|---|
| UI (Next.js) | Easy (days) | Wrap in **Tauri** (~5 MB, Rust) or Electron (~150 MB, JS). UI runs as a local server inside the wrapper — no rewrite. |
| API routes | Easy | `/api/{models,plots,risk-nodes,risk-zones,buildings}` already exist; run locally unchanged. |
| Database | Easy | Stay on Supabase (hosted Postgres + PostGIS). Only `site_risks` needs PostGIS. |
| Storage | Easy | Supabase Storage bucket `models`. Swap to local FS later. |
| Auth | Easy | Supabase auth → desktop session / license key. |
| Cesium / 3D | Moderate | Bundle Cesium locally (drop the CDN); Esri imagery tiles stay ONLINE. |
| Blender context import | Moderate | Bundled `Blender.app`, headless. |
| YOLO detection | Heavy | Local Python service (PyInstaller or sidecar); GPU helps. |

**The offline blocker to be honest about:** map imagery is a live Esri tile service. Truly offline
means shipping an MBTiles/tile cache — the single biggest cost, not the app code.

**Packaging reality:** `Blender.app` is ~879 MB (self-contained Python 3.13 + libs); a stripped
bundle is ~600 MB minimum. With a bundled YOLO service the installer is ~1 GB+. Fine for
enterprise/on-prem, not a casual download. Decide whether the Blender pipeline ships *inside* the
installer or as an optional first-run download.

## Embedded 3D context pipeline (fifth globe layer)

Source: `Projects/3D Building Builder.md` in the vault — a **shipped + tested** headless Blender
pipeline (blosm v2.7 + BlenderGIS) that imports real-world building geometry from OpenStreetMap /
Google 3D Tiles for a lat/lon bounding box and exports glTF. Verified on KLCC: 115 buildings,
217 KB glTF, ~0.9 s. Runs `blender --background --python script.py` — no GUI, no display server.

**Why CDM needs it:** a siting study cannot be judged in a void. CDM can place ONE uploaded
building on a node, but "where should this sit and which way should it face" depends on the
surroundings (adjacent school, towers, roads, water). This adds the **Context** layer to the
existing four (plots / buildings / risk nodes / zones).

### Integration shape
- Table `context_imports` (shipped shape): `center_lon` / `center_lat` (the point the user pinned),
  `radius_m` (key-in box, capped 1000 m), `heading_deg`, `offset_east_m`, `offset_north_m`, `scale`,
  `source` (`osm` | `google_3d_tiles`), `file_url` (glTF in Storage), `building_count`, `status`
  (`QUEUED`/`BUILDING`/`READY`/`FAILED`), `error_message`.
- A **local worker** runs the headless Blender script, writes the glTF to Storage, then the row.
- Expose Context as a **Data Overlay toggle group**, same pattern as the "Identified Risk"
  overlay.

### The worker must be spawned BY THE APP, one-shot
MARU rejected "open a terminal and run `npm run surroundings:worker`" outright — a user must never
run commands. `POST /api/surroundings` therefore spawns the worker itself:
`spawn(process.execPath, [worker, '--once'], { detached: true, stdio: 'ignore' })` then `unref()`.
It drains the queue and EXITS, so nothing lingers.

- **One-shot beats a daemon here.** A parked poller is only ~40–60 MB, but Blender itself is
  ~500 MB–1 GB, so the honest answer to "does it eat RAM in the background?" is: not when idle, but
  do not keep Blender resident. Spawn-on-demand pays that cost only during a build.
- **Auto-discover the toolchain** — never require the user to set env vars. Walk
  `~/Library/Application Support/Blender/*/scripts/addons/blosm` (and `~/.config/blender/*`) for
  the addon dir, and probe the usual binary paths for `Blender`. `BLENDER_BIN` / `BLOSM_PATH` stay
  as optional overrides only.
- Skip the spawn on serverless (`if (process.env.VERCEL) return`), with the polling worker as the
  documented fallback.

### The real gotcha #1: axis convention (NOT origin, NOT scale)
blosm exports **local metres relative to the bbox centre** — that origin assumption is CORRECT
(blosm's TransverseMercator builds from `((minLat+maxLat)/2, (minLon+maxLon)/2)`). The misalignment
is the **axis convention**:

- blosm/Blender: **+X = east, +Z = south**, +Y = up.
- Cesium's glTF loader calls `getAxisCorrectionMatrix(upAxis=Y, forwardAxis=Z)`, which composes
  `Y_UP_TO_Z_UP × Z_UP_TO_X_UP` → **glTF +Z → East, glTF +X → North**.

So an OSM import lands rotated ~90° about its origin. Compensate with a default `heading_deg = 90`
for `source='osm'` (`google_3d_tiles` is a different convention — keep 0).

**Why this hid for so long — the diagnostic that matters:** a single uploaded building rotated
about its own centre looks fine, so per-model GLB uploads never exposed it. A whole cityscape does.
When a big georeferenced import looks "totally off" but a hand-placed building looks right, suspect
an axis/heading error, not a position or scale error.

**How to prove the coordinate chain instead of guessing:** script Blender to import the real area
AND drop a marker cube at a known OSM coordinate projected with blosm's own
`util.transverse_mercator.TransverseMercator`. If the marker lands on blosm's own building mesh
(observed: within 0.11 m), the projection, origin and axis mapping are all correct and the fault is
elsewhere. Do this before "fixing" coordinates.

### The real gotcha #2: stray geometry blows the bounding sphere
Overpass returns **whole ways that cross the bbox**, so roads / waterways / landuse extend
kilometres beyond it. Observed on a 1 km import: world extent **36 km × 19 km** with one mesh
**17 km** from origin. Cesium sizes and frames a model from its **bounding sphere**, so the model
renders misaligned and badly scaled even though the coordinates are right.

**Clip every mesh to the requested box before export** — `bmesh`, drop objects wholly outside,
trim straddling ones, ~25 m margin so boundary buildings aren't gutted. Verified: extent
36 km → 2048 m (exactly 2×1025 m for a 1 km radius).

Also drop `minimumPixelSize` from a large context model — it fights a big bounding sphere.

### Escape hatch: let the user align by hand
Because a perfect automatic georeference is fragile across sources, ship manual alignment: on the
selected import expose **Rotate (0–360°), move E/W and N/S (±500 m), Scale (0.5–2×), Reset**,
persisted to `offset_east_m` / `offset_north_m` / `scale` / `heading_deg` so an adjustment survives
reload. Applying offsets in metres: convert at the origin
(`mPerLat = 111320`, `mPerLon = 111320 * cos(lat)`). Once the user finds the value that snaps the
geometry onto the imagery, bake it in as the default for new imports.

### Known gaps
- BlenderGIS georeferencing tools need GDAL/PyProj/Pillow (optional — basic OSM import works
  without them).
- blosm **Pro** (~$30) is required for textured buildings / terrain texturing.
- Google 3D Tiles needs a Google API key (`blosm.dataType = '3d-tiles'`).
- Overpass API slows beyond ~1 km radius — tile the import for large sites.
- Blender 5.1 needs `from gui import` → `from ..gui import` in blosm's `building/renderer.py`;
  re-apply after any addon update.

## Related
- Vault: `Projects/CDM/CDM-Desktop-Architecture-Option-A.md`,
  `Projects/CDM/CDM-Local-AI-Appliance-MOAT.md` (the local-AI "doctor" appliance story),
  `Projects/3D Building Builder.md`.
- Repo mirrors: `docs/FEATURES-ROADMAP.md`, `docs/ARCHITECTURE_AND_PIPELINE.md`.
