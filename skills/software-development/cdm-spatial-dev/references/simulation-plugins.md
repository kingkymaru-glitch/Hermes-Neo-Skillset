# Simulation plugins — AS BUILT (V0.70, layers V0.75, terrain shading V0.76, water flow V0.80, erosion V0.81; CFD in progress)

Flood and shadow shipped in V0.70; each result became its own toggleable layer in V0.75; the DEM
became visible as a hillshade in V0.76; water flow (rational method + Manning's equation)
shipped in V0.80; erosion risk (slope x flow x soil) shipped in V0.81. This file records the
concrete architecture and the numeric traps, so a future plugin (SOil movement, congestion) is a
small job.

## Files

| File | Role |
|---|---|
| `scripts/plugins/registry.json` | **Single source of truth**: plugin ids, labels, disclaimers, `requires`, and the full parameter schema. Read by the API (→ UI form), by Python (validate + clamp), and by humans. |
| `scripts/run_plugin.py` | The engine. Registry-driven; one dispatch entry per plugin. Shared hydrology helper `drainage_and_flow` computes depression fill, D8 flow direction, flow accumulation, and drainage mask once for both flood and water_flow. |
| `scripts/plugins/selfcheck.py` | Invariant suite over the answers (28 checks: flood + shadow + water_flow + erosion). |
| `scripts/plugins/water_flow_selfcheck.py` | Synthetic rig for water_flow (10 checks, no DEM needed). |
| `scripts/plugins/erosion_selfcheck.py` | Synthetic rig for erosion (8 checks, no DEM needed). |
| `scripts/dam_break_selfcheck.py` | Synthetic rig for dam_break (6 checks, no DEM needed). |
| `scripts/cfd_geometry.py` | Stage 1: OSM GeoJSON → STL (local metres, manifold surfaces). |
| `scripts/cfd_write_dicts.py` | Stage 2-3: writes all OpenFOAM v2606 dict files for a wind case. |
| `scripts/cfd_case_runner.sh` | Stage 2-3: blockMesh + surfaceFeatureExtract + snappyHexMesh + simpleFoam. |
| `scripts/cfd_postprocess.py` | Stage 4: sample 1.5m plane → Lawson comfort bands → GeoJSON. |
| `scripts/cfd_snappy_dict.py` | Rewrites snappyHexMeshDict if v2606 requires resolveFeatureAngle relocation. |
| `scripts/plugins/wind_fast_selfcheck.py` | Synthetic rig for wind_fast (7 checks, no DEM needed). |
| `scripts/plugins/requirements.txt` | numpy, rasterio, shapely. Deliberately short. |
| `scripts/py-runtime.mjs` | Managed venv provisioning (uv, else stdlib venv). |
| `scripts/dem-data.mjs` | Copernicus GLO-30 tiles: naming, download, cache, status. |
| `scripts/simulation_worker.mjs` | One-shot detached worker: claim → run → store → exit. |
| `scripts/analysis_cli.mjs` | CLI the setup routes shell out to (runtime/dem status+fetch, shading, selfcheck). |
| `app/api/simulation/route.ts` | Queue a run; list; delete. |
| `app/api/simulation/plugins/route.ts` | Serve the registry. |
| `app/api/simulation/presets/route.ts` | Named parameter sets. |
| `app/api/dem-data/route.ts` | Terrain status + fetch for the active project. |
| `app/api/analysis-runtime/route.ts` | Runtime status + setup. |
| `contexts/SimulationContext.tsx` | Runs, presets, terrain/runtime status, polling. Does NOT hold visibility — see Result layers. |
| `components/SimulationPanel.tsx` | The floating panel; **builds its form from the registry**. |
| `components/AnalysisSetupManager.tsx` | Settings > Analysis runtime. |
| `components/LayerControls.tsx` | Data Overlays; carries the per-result switches under "Analysis Result". |
| `contexts/LayersContext.tsx` | Overlay toggles + the per-result visibility map (`cdm.simLayers.v1`). |
| `components/CesiumViewer.tsx` | Three effects: build result entities per run, apply per-run visibility, and add/remove the terrain-shading imagery layer. |
| `scripts/terrain_shading.py` | DEM window → hillshade PNG + a `.json` of its bounds. Writes the PNG itself. |
| `app/api/terrain-shading/route.ts` | Shading METADATA (bounds, size, elevation range); builds on first call. |
| `app/api/terrain-shading/image/route.ts` | The PNG. Separate route so it can be cached `immutable`. |
| `supabase/migrations/007_simulation.sql` | `simulation_runs` + `simulation_presets`. |

## Adding a plugin

1. Add an entry to `registry.json` (id, label, icon, summary, `disclaimer`, `requires`, `params`).
   Every param gets type, unit, default, min/max, and a `help` string written for a REVIEWER.
2. Write `plugin_<id>(dem, valid, transform, params, site)` in `run_plugin.py` and register it in
   the `PLUGINS` dict.
3. Add a synthetic rig `scripts/plugins/<id>_selfcheck.py` that runs with no DEM. Follow the
   wind_fast and water_flow rigs: hand-computable answers on flat / tilted / channel terrain,
   capable of failing. Wire it into `scripts/analysis_cli.mjs` (`--<id>-selfcheck` subcommand)
   and add an npm script (`sim:selfcheck:<id>`).
4. Add real-terrain invariant checks to `scripts/plugins/selfcheck.py` (the `--selfcheck` suite).
   At minimum: produces a result, the reported measure is positive where expected, monotonicity
   where it applies, and (for hydrology) that a channel is deeper than flat ground.
5. The UI form, validation, clamping and the run pipeline are all registry-driven — no React
   change, no migration.

For any new plugin: monotonicity where it applies, that the reported measure is consistent with the
geometry, and a synthetic rig with a hand-computable answer. Both the synthetic rig and the
real-terrain checks must pass before declaring the build done. Run: `npm run sim:selfcheck` (full
suite: flood + shadow + water_flow + wind_fast + dam_break rigs), plus `tsc --noEmit` and `next build`.

## Data flow

```
UI  ──POST /api/simulation {pluginId, params}──▶  simulation_runs row (QUEUED)
                                                   │
                              spawn detached, one-shot ▼
                     scripts/simulation_worker.mjs --once
                                                   │
                       claim (QUEUED→RUNNING) ─────┤
                       read project coords          │
                       ensure DEM tiles             │
                       ensure managed venv          │
                       exec run_plugin.py           │
                       store GeoJSON + summary ─────┘  (READY | FAILED)
UI  ◀── poll GET /api/simulation (only while in flight)
```

The UI polls ONLY while a run is QUEUED/RUNNING — a finished project must not keep a timer
alive. `reclaimStaleRuns()` re-queues anything stuck on RUNNING for >20 min so a closed laptop
does not leave the panel spinning.

## Storage rationale

`simulation_runs` stores `result_geojson` and `summary` rather than recomputing on display. A
result is EVIDENCE for a siting decision: re-running a plugin must never silently change a number
a report already cited. The row also stores `params` (post-default, post-clamp) so a run is
reproducible from the row alone, plus `dem_source` + `dem_tiles` so a result traces to its terrain.

## Terrain

Copernicus DEM GLO-30, public keyless AWS bucket, 1°×1° tiles, ~44 MB, 30 m posting, EGM2008.

```
https://copernicus-dem-30m.s3.amazonaws.com/<STEM>/<STEM>.tif
STEM = Copernicus_DSM_COG_10_<N|S><lat:02d>_00_<E|W><lon:03d>_00_DEM
```

- Tile name is the tile's **south-west** corner. `N03_00_E102_00` covers 3–4 N, 101–102 E.
- A bbox crossing a degree line needs MORE THAN ONE tile; using one silently truncates terrain.
- The max edge is EXCLUSIVE — a bbox ending exactly on 4.0 N does not need the 4 N tile.
- **JS has no `Math.nextafter`** (C/Python only). Use `Math.floor(maxLat - 1e-9)`, guarded with
  `Math.max(lat0, …)` for a degenerate bbox.

### Slope-floor trap (silent, fails spatial checks)

Never clamp every slope to a floor with `np.maximum(slope, 0.001)`. On uniformly sloped ground,
depth variation comes from accumulated discharge; a blanket 0.001 floor buries that behind a constant.
The check "steeper ground erodes more" passes while the slope response is everywhere the same.
Replace only invalid/zero: `slope = np.where(valid & (slope > 0), slope, 0.001)`.

### Self-cancelling math expressions

Avoid `tan(atan(x))`, `sqrt(x*x)` when x is already non-negative, or any expression that returns
its input unchanged. It obscures intent and can mask a sign or unit bug that the expression was
meant to catch. Write the direct computation.

### Per-feature aggregates for spatial verification

`mask_to_geojson` dissolves cells into polygons, destroying per-cell values when all cells share
a band. After dissolution, write a per-cell aggregate (e.g. `mean_depth_m`, `mean_index`) into each
feature's properties so the selfcheck rig can verify spatial patterns without re-running the plugin.

### Banded output → per-feature Cesium coloring

Any plugin that produces named bands must add a style constant and a color callback, then wire it
into the CesiumViewer render effect as a per-feature ternary. Single-colour plugins skip this.

```tsx
// In CesiumViewer.tsx:
const XXX_STYLE: Record<string, { css: string; alpha: number }> = {
  Low: { css: "#84cc16", alpha: 0.2 },
  Moderate: { css: "#f59e0b", alpha: 0.35 },
  High: { css: "#ef4444", alpha: 0.45 },
  Severe: { css: "#b91c1c", alpha: 0.55 },
};
const xxxColor = useCallback((band: unknown) => {
  const C = cesiumRef.current;
  if (!C) return null;
  const style = XXX_STYLE[String(band)];
  if (!style) return null;
  return C.Color.fromCssColorString(style.css).withAlpha(style.alpha);
}, []);

// In the render effect:
const featureColor =
  (run.pluginId === "wind_fast"
    ? windClassColor(feature.properties?.wind_class)
    : run.pluginId === "erosion"
      ? erosionRiskColor(feature.properties?.erosion_risk)
      : null) ?? color;
```

### Numeric traps (all produced plausible-looking wrong answers)

### Rasters are in DEGREES (EPSG:4326)

| What | Wrong | Right |
|---|---|---|
| Cell area | `abs(a * e)` → square degrees → **0.0 m²** | `|a| * m_per_deg_lon * |e| * m_per_deg_lat` |
| Shapely area | `geom.area * cell_area_m2` → always 0 | `geom.area * (m_per_deg_lat * m_per_deg_lon)` |
| `simplify_m` | passed raw → tolerance in DEGREES | `simplify_m / m_per_deg_lat` |

Symptom for the Shapely case: a valid mask yields **zero features** because every polygon fails
`min_patch_m2`.

Note `simplify_m` below ~30 m is a genuine no-op on a 30 m DEM (the boundary is a staircase).
Documented in the parameter help rather than left to be discovered.

### Verify area TWO independent ways

`cells × cell_area` and the dissolved geometry's area must AGREE. They come from different code
paths, so agreement is evidence and disagreement localises the bug. In practice they match to the
metre — 1,163,316.8 m² both ways. This is the strongest single check in the suite.

### An input-insensitive result is usually the DATA, not a bug

Flood at 1, 2, 3 and 4 m on one site returned the identical 7.113 ha, which reads like a threshold
or off-by-one bug. The elevation histogram showed why — no code change was needed:

```
 0.0-0.5 m above datum :  75 cells
 0.5-4.0 m above datum :   0 cells   <- a 3.5 m vertical GAP
 4.0-4.5 m             :   1 cell
```

A flat 75-cell shelf, then nothing, then the next ground level. Water level genuinely does nothing
across 1–4 m and then jumps (+3 cells at 5 m, 89 at 8 m, 111 at 10 m). Histogram the driver
variable BEFORE touching the maths; when the band is empty the plugin is right, and the flat range
is real site information worth reporting to the user.

### Hand-verifying a run: read the project's REAL coordinates first

`resolveProjectIdFor` falls back to the EARLIEST `projects` row, so "the active project" is not
whichever site you last tested. Get lat/lon from `GET /api/projects` before hand-running a plugin.
`load_dem` raising `No terrain data in the requested area (is the site on land?)` means the bbox
falls outside the tile you passed — WRONG COORDINATES, not a corrupt or missing tile.

### Solar position

- **Normalise the hour angle to (−π, π].** Raw `lst - ra` gives +296° instead of −64°. Elevation
  is blind to the sign (cos is even), so elevation looks right while azimuth is 180° wrong.
- **Equinox oracle:** sunrise azimuth 90°, sunset 270°, peak elevation ≈ 90 − latitude. Free.
- **Azimuth is meaningless near zenith** — assert at mid-morning/mid-afternoon, never local noon.

### Shadow ray-marching

- Step in **METRES**, then convert to cell offsets. Stepping in cells while requiring
  `step * tan(sun)` metres of rise makes terrain climb ~30× too fast (74% of a flat plain
  reported as shaded).
- Verify against a **synthetic rig**: a 100 m wall under a 45° sun must cast a 100 m shadow.
  Measured 93 m on a 30.9 m grid — inside the discretisation. Real terrain gives nothing to check
  against.
- **Sweep at interval MIDPOINTS.** Endpoint sampling makes durations ambiguous by a whole step.
  Exclude night samples from shaded minutes and report the excluded night minutes explicitly.

## Honest scope (stated in the UI, not just the docs)

- **Flood** = SCREENING. Bathtub (fill from the lowest ground in the site) or HAND (height above
  nearest drainage, via priority-flood depression filling + D8 flow accumulation + a contributing-
  area drainage threshold). No routing, no velocity, no duration, **not** a substitute for
  hydraulic modelling or a drainage design.
- **Water Flow** = SCREENING. Rational method (Q = CIA) for discharge, Manning's equation for depth
  and velocity. Does not model channel geometry, backwater, or temporal dynamics. **not** a
  substitute for hydraulic modelling (HEC-RAS and similar) or a drainage design.
- **Erosion Risk** = SCREENING. E = slope x accumulated flow x soil erodibility. Does not model
  sediment transport, deposition, or temporal dynamics. Not a substitute for a geotechnical
  study or a sediment transport model.
- **Dam Break** = SCREENING. 2D shallow water equations (Saint-Venant) with Manning friction
  and adaptive time-stepping (CFL). Triangular breach hydrograph via broad-crested weir equation.
  No building interaction, no sediment transport, no infiltration. Not a substitute for HEC-RAS 2D
  or MIKE 21. For demonstration and preliminary assessment only.
- **Shadow** = TERRAIN ONLY. No buildings, no vegetation — place buildings on the globe separately
  to judge their effect.
- Both carry a `disclaimer` in the registry; the panel displays it above the Run button.
- On a flat site shadow legitimately reports ~0%. Check the site's relief before calling it a bug
  (Temerloh had 43 m of relief over 2.8 km and is a genuine flat river plain).

## Result layers — one per finished run

Every READY run draws as its own Cesium entity group, so a 2 m flood and a 10 m flood can be
compared or isolated instead of only the newest being visible. Ownership is deliberately split:

- **`LayersContext` owns VISIBILITY** — `simLayers: Record<runId, boolean>`, plus
  `isSimLayerVisible(id)`, `setSimLayer(id, v)`, `setAllSimLayers(ids, v)`, `pruneSimLayers(ids)`.
  It is context state, not component state, because two components need the same answer:
  `LayerControls` (Data Overlays) and `SimulationPanel` (the Results list).
- **`SimulationContext` owns the DATA** (runs, presets, status) and no longer has a `displayRun`.
  Keeping both would have created two ideas of "which result is shown".

Key mechanics:

- **An id absent from the map is VISIBLE** (`simLayers[id] !== false`). A finished result appears
  on the globe with nothing ticked, and hiding one persists across reload.
- **Separate `localStorage` key `cdm.simLayers.v1`.** `cdm.overlays.v1` is loaded against a fixed
  `OVERLAY_KEYS` list that filters unknown keys; run ids are unbounded and come and go with the
  database, so mixing them makes the loader churn on keys it can never recognise.
- **Master + per-item.** `overlays.simulation` gates the whole group; each run has its own switch.
  Effective visibility is `master && isSimLayerVisible(id)`.
- **`pruneSimLayers` returns the SAME object when nothing is stale.** Returning a fresh object on
  every call would re-render, which would write to localStorage, on every poll tick.
- **TWO render effects.** One builds entities keyed by run id and only for runs in
  `READY && features.length > 0` (deps: the runs list); the other walks the groups and sets
  `entity.show` (deps: the runs list, the visibility map, the master switch). Rebuilding every
  MultiPolygon on each toggle would be wasteful once several large results are on the map.
- Deletion is handled in the build effect: any entity group whose run id is no longer in the
  drawable set is removed, which covers both a deleted run and one re-queued back to QUEUED.
- **Cap the rendered list (~8 rows)** with a `+N more` line — a project can accumulate runs
  indefinitely and the panel must not grow without bound.
- Geometry is drawn ground-clamped (`classificationType: TERRAIN`) and colour is chosen by
  `pluginId` (flood cyan `#22d3ee` @ 0.45, shadow slate `#0f172a` @ 0.55) — shadow reads as
  absence of light rather than as another bright overlay. Holes in the polygon are honoured
  (a dissolved flood mask can enclose dry islands), and painting over them would overstate the
  area the run reported.

### Auto-open on completion (V0.82)

`ScreenContext` persists `screen` (home/workspace) and `simOpen` to localStorage
(`cdm.screen.v1`, `cdm.simOpen.v1`). A refresh mid-run returns the user to the workspace with
the Simulation panel open — not the homepage. `SimulationContext` detects the in-flight → READY
transition and calls `setSimOpen(true)` so the result is visible without manual refresh.

### Layer clarity (V0.83)

Three UX fixes for the "result colors collide with the base map" problem:

- **Monochrome base map.** When a simulation result is visible, the satellite imagery
  desaturates to grayscale (`saturation = 0.0` on the Esri/OSM imagery layers). The result
  colors (blue/red/amber) stand out as the only colored elements on the globe. When no result
  is visible, the basemap returns to full color.
- **Wind result legend.** A "Wind Result" legend appears in Layer Controls when a wind_fast
  run is READY, showing what each band color means: Sheltered (blue), Normal (slate),
  Exposed (amber), Severe (red).
- **Solo mode.** New buttons in Layer Controls (Result only / Risk nodes / Risk plots /
  Surroundings / Reset all) show one overlay group at a time for clean risk assessment.
  `soloOverlay(key)` turns off all other overlays; `clearSolo()` restores defaults.
- **riskPlots toggle.** Hand-drawn RAG zones now have their own on/off switch in Data
  Overlays (`overlays.riskPlots`), gated in CesiumViewer's plot render effect.
- **Mock GIS toggles removed.** The non-functional slope/hydrology/utilities switches were
  removed from Layer Controls — they were placeholders that confused the layer list.

## Terrain shading — seeing the ground the analysis used

**The problem this solves.** The DEM drives every plugin and it was INVISIBLE. A flood result on a
flat sheet says where water reaches and nothing about why, so there was no way to check a result
against the terrain it came from. The hillshade is that check: the same data, lit from a fixed
angle so its shape reads as light and shade, in PLAN VIEW so it reads without tilting.

**This is a PICTURE, not 3D terrain.** The globe stays flat. Using the same DEM as a real terrain
SOURCE is the separate, larger change (see Still open) — do not conflate the two.

### The pipeline

```
LayerControls "Terrain Shading" on
   → SimulationContext.refreshShading()  (lazy: only on first enable)
   → GET /api/terrain-shading            → analysis_cli.mjs --shading-status
   → ensureShading(): bbox = site + radius×1.5, pick the DEM tile, cache, else build
   → scripts/terrain_shading.py          → <cache>/<key>.png + .json
   → CesiumViewer: SingleTileImageryProvider over the bounds, imageryLayers, alpha 0.6
```

- **Cached by a hash of the ROUNDED bbox.** `~5` decimal places means nudging a site reuses the
  image while any real move regenerates it — the cache invalidates itself instead of needing to be
  cleared. Served `Cache-Control: immutable` for a year, which is only honest because the filename
  IS the bounds.
- **Built lazily, never on every setup refresh.** Generating it spawns Python and reads the DEM;
  that is wasted work for someone who never switches it on. Once made it is a file read.
- **Alpha 0.6**, so the satellite imagery still reads through. The shading explains the ground; it
  does not replace the photo.
- **Lit from the north-west at 45°** — the cartographic convention, deliberately NOT the real sun
  position. A hillshade lit from a genuine low sun is unreadable and changes meaning with the
  clock; real sun position is what the shadow PLUGIN is for.
- **`terrainShading` is excluded from `DATA_KEYS`/`BUILDERS`** in `CesiumViewer`, like
  `simulation` and `surroundings` — those sets are for async-built entity overlays, and adding a
  key to `OVERLAY_KEYS` without excluding it there is a type error the build WILL catch.

### Writing the PNG without a new dependency

`terrain_shading.py` writes the PNG itself with `zlib` + `struct`. Do NOT add Pillow: the managed
runtime's `runtimeReady()` check would need updating, and every venv already on a machine would
have to be rebuilt — real churn for one greyscale image. A minimal PNG writer is ~20 lines
(signature, IHDR, IDAT of filter-byte-0 scanlines, IEND).

### The hillshade sign trap (bit once, looked correct)

A slope FACING the light rendered **darker** than flat ground. The usual aspect/zenith formula has
three or four sign conventions and this raster is north-up, so the row gradient needs negating to
become a northward derivative. Rather than patch the sign, the calculation is now the surface
normal dotted against the light vector:

```
dz_dx = d/dcol          # east
dz_dy = -d/drow         # north (row index grows southward)
illum = (lz - dz_dx*lx - dz_dy*ly) / sqrt(dz_dx² + dz_dy² + 1)
```

One sign to get right, provable against a tilted plane. Verified with a synthetic rig (a uniform
plane tilted one way then the other, NOT real terrain which offers nothing to compare against):
flat **184** vs 185 predicted (`40 + sin(45°)·205`), slope into the light **234**, slope away **26**.

## Still open

- **Use the DEM as a real 3D terrain SOURCE** so the globe itself has hills (the `Terrain` toggle).
  This also removes the Cesium ION token dependency. It is the bigger change and it was deliberately
  sequenced AFTER shading, because turning on real terrain changes how EVERY placed building, plot
  and Surroundings model sits — items that look fine on a flat sheet will visibly float or sink.
  Show the user a before/after rather than surprising them with it.
- Custom DEM upload / a `terrain_source` picker (planned, not built).
- Soil movement, water runoff, congestion plugins.
- Feeding accepted simulation results into the CDM report / PDF export.
- Results are stored but never cleaned up; a delete route exists, no retention policy.
- **Detail Wind (CFD)**: pipeline built but solver stage not yet verified end-to-end. All
  plumbing complete: cfd_geometry.py (OSM→STL), cfd_write_dicts.py (dict generation),
  cfd_case_runner.sh (blockMesh→snappyHexMesh→simpleFoam), cfd_postprocess.py (U field→
  Lawson comfort bands→GeoJSON). Worker dispatch on `engine: "cfd"` wired into
  simulation_worker.mjs. Turbulence model: k-epsilon (kOmegaSST crashed on v2606 — see
  pitfalls below). Status: mesh generation verified (3.3M cells, snappyHexMesh + addLayers
  succeeded). simpleFoam crashed during kOmegaSST init; switched to kEpsilon, not yet
  re validated end-to-end.

### OpenFOAM v2606 snappyHexMeshDict pitfalls

v2606 changed several dictionary key locations. The most common error is a key at the wrong
 nesting level producing "Entry not found" — read the error carefully: it reports the dictionary
path where OpenFOAM looked, not where the key actually is.

- **`relativeSizes`**: required inside `addLayersControls` when `addLayers true`. Without it:
  "Entry 'relativeSizes' not found in addLayersControls".
- **`layers`**: required inside `addLayersControls` when `addLayers true`. Can name per-patch
  layer counts: `"buildings.*" { nSurfaceLayers 5; }`. Without it: "Entry 'layers' not found".
- **`nSurfaceLayers`** (not `nLayers`): v2606 renamed the per-patch layer count key.
- **`slipFeatureAngle`**: required inside `snapControls` (not addLayersControls).
- **`nGrow`**: v2606 defaults to 0; set to `-1` for automatic growth near features.
- **`minMedialAxisAngle`**: required inside `addLayersControls` (in addition to
  `minMedianAxisAngle`). Both default to 90.
- **`resolveFeatureAngle`**: v2606 expects it INSIDE `castellatedMeshControls` (not at root).
- **`addLayers true`**: if `addLayers true` is set, `addLayersControls` must contain
  `relativeSizes`, `layers`, and all layer thickness parameters. Simplest fix for screening:
  set `addLayers false` and skip boundary layers entirely (they are not essential for a
  first-pass RANS result).

### OpenFOAM v2606 turbulence model pitfalls

- **kOmegaSST crashed** (SIGABRT) during initialization on v2606 with our mesh. Root cause
  unclear; likely a BC incompatibility with the `nutkWallFunction`/`omegaWallFunction`
  combination. **kEpsilon is more robust** on v2606 — switch if kOmegaSST aborts.
- **kEpsilon requires** fields: U, p, k, epsilon. No omega field. BCs: `kqRWallFunction`
  on walls (ground, buildings), `epsilonWallFunction` on walls. Inlet: `fixedValue` for
  both k and epsilon. k inlet = 0.1. epsilon inlet = `u*^3 / (kappa * z0)`.
- **Uniform fixedValue inlet**: the simplest robust inlet BC for v2606. ABL log-law
  profiles (`atmBoundaryLayerInletVelocity`) require a registered Function1 (`Uref`)
  and crash in dictionary parsing on macOS v2606. A uniform inlet still gives valid
  RANS results for screening; the ABL profile is a accuracy refinement, not a requirement.

### STL geometry for snappyHexMesh

surfaceFeatureExtract requires a **closed manifold** — adjacent triangles must share
vertices. A naive extrusion that emits separate triangles per face will produce an incorrect
or empty `eMesh`. The CDM cfd_geometry.py fan-triangulates the roof/floor from a centroid so
every triangle shares the centroid vertex, producing a valid manifold for snappy.

Also:
- **Do NOT include a ground plane in the STL** — the `ground` patch is already defined in
  blockMeshDict. An extra unconnected surface in the STL causes surfaceFeatureExtract to
  skip feature extraction (no .eMesh file), and snappyHexMesh then fails with "Could not
  open .eMesh".
- **`locationInMesh`** must be at a z-height ABOVE the tallest building and BELOW the
  blockMesh top. If inside a building, subsetting collapses the mesh to 1 cell.
- **Domain height**: 5x max building height gives proper vertical clearance for the ABL
  and wake. NZ must scale with domain height to keep cells near 2m (or coarser for
  screening).
