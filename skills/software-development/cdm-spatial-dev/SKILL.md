---
name: cdm-spatial-dev
description: Use when working on CDM (~/CDM) spatial platform.
---

# CDM Spatial Intelligence — development

MARU's construction Design-Management platform. Next.js 14 App Router + TypeScript +
Tailwind(dark) + shadcn/ui + lucide-react + sonner. Repo `~/CDM`
(GH `kingkymaru-glitch/CDM`). Partner sends long "anti-drift" milestone prompts;
MARU forwards them and expects one shipped version per milestone.

## Parallel-agent coordination (MAX + Neo)

MARU runs TWO agents on the SAME ~/CDM repo: **Neo (me)** and **MAX (parallel)**.
MAX deploys directly to Vercel without always pushing to GitHub, causing version drift.

### Version realignment procedure
When the user reports a version mismatch or asks to "realign":

1. **Check the live stamp:** `curl -s https://cdm-eta.vercel.app | grep -oE 'V0\.[0-9]+'`
2. **Check local stamp:** `cat lib/app-version.ts`
3. **Check git tags:** `git tag -l 'V0.8*'` — find which versions are committed but untagged
4. **Check Vercel deployment metadata:** `vercel inspect <deployment-url> --json` — the `meta.githubCommitSha` field shows the actual commit the deployment was built from. Compare this with `git log --oneline <sha>` to see what version the deployed code actually is.
5. **Tag missing versions:** `git tag V0.84 <commit-sha>` for each untagged commit
6. **Update CHANGELOG.md** with all versions (committed + deployed-only)
7. **Push tags:** `git push origin V0.84 V0.85`

### Pitfall: version stamp ≠ commit
MAX may change `lib/app-version.ts` to V0.87 without committing, while the latest git commit is V0.83. The stamp says V0.87 but the code is V0.83. Always check `git log --oneline -1` against the stamp — if they don't match, the stamp was changed without a commit.

### Pitfall: deployed ≠ committed
MAX may deploy V0.86-V0.87 directly to Vercel without git commits. These versions
exist only as Vercel deployments — there is no commit to tag. Document them in
CHANGELOG as "deployed directly to Vercel" and note the gap.

### Pitfall: Vercel auth wall blocks verification
`curl` to the production URL returns a Vercel login page, not the app. To verify
the live version, either open the URL in a browser (logged into Vercel) or check
the deployment logs via `vercel logs <deployment-id>`.

## Hard rules

- **Cesium comes from CDN at RUNTIME, never the npm package.** Importing `cesium`
  into the Next build breaks the browser bundle. Load `Cesium.js` from jsDelivr
  and use the untyped `window.Cesium` global (`any` is correct there).
- **Every release bumps `lib/app-version.ts`** (V0.xx, never reused) and the header
  shows it. Never ship without the bump.
- **MARU pastes SQL himself.** SQL is a file on his Desktop, copy-paste-pure:
  no comments, no headers, no banners. Select-all → paste → Run must work verbatim. His words:
  "no nonsense". Keep `-- ...` explanatory comments OUT even when documenting a new column; put
  the explanation HERE instead, because he selects all and pastes, so any label lands in his SQL
  editor. **Exactly ONE `.sql` on the Desktop** — merge new statements in and delete what they
  supersede (he asks *"which sql where"* the moment there are two). Never echo the Supabase key
  values; the probe script sources `.env.local` and prints only schema names.
- **'discuss first, no code' is a hard gate.** For any feature/UI ask he says
  "discuss" on, propose the control surface + data flow and wait for OK.
- **No live third-party API in the critical path.** MARU: *"i dont want any API for this
  purpose"*. A build, a demo, or a compliance output must not fail because someone else's server
  is busy — and he reacts badly to DISCOVERING a network dependency he was not told about. When
  proposing any design, surface every outbound call it makes. "Free and hosted" is not the same
  as "offline". Known live dependencies, to migrate or drop: Overpass (OSM geometry), Esri
  imagery tiles, the Cesium CDN, and the weather/quake/volcano overlays. See
  `references/offline-osm-data.md` for the local-extract path.
- **Plugins run as separate processes, one at a time.** The SIMULATION tab dispatches each test
  as its own subprocess (not a pool, not bundled). User selects the test from the dropdown,
  configures parameters, then runs — one active job at a time. Heavy tests (soil, flood, runoff)
  are async with progress; fast tests (shadow cast) can be sync. Results render as a new Cesium
  layer on the globe. See `references/simulation-plugins.md`.
  Every plugin must declare its MODEL CLASS in the UI — a screening model (bathtub flood) must
  never read as a hydraulic result. Underclaim; it is the same liability discipline as the
  human-in-the-loop rule below.

## Backend

Own Supabase project `ennvfuaimplxkzfdxfqd` (separate from LunaV
`okzmblyboudjffaifixa` and ARRAS `lxmmxpxjercmhmiuqegq` — no shared data).
Tables: `projects`, `site_risks` (PostGIS geom — the AI/seeded polygons), `document_chunks` (pgvector), `models`,
`site_plots`, `site_buildings`, `site_risk_zones`, `risk_nodes`, `context_imports`, `ai_models`. Schema in
`supabase/migrations/`. Only `site_risks` needs PostGIS — the newer tables use
`numeric` lon/lat + `jsonb`, which keeps a future local-Postgres move simple.

Model files upload to **Supabase Storage bucket `models`**, not Cloudflare R2
(R2 would need Edge Functions + secrets deployed). Swapping the backend is a
one-file change in `lib/model-upload.ts`.

**Risk node colouring — two independent dimensions, kept in step at the SOURCE.** Node dot
colour = risk CATEGORY; the ring = the RAG LEVEL. They must never drift, and the drift is easy to
reintroduce:
- Keep LEVEL and the L×S SCORE synchronised in the CONTEXT, not in each component: placement seeds
  L/S from the chosen band (`lsForLevel`), and `updateNode` recomputes `riskLevel` whenever
  likelihood/severity change. A component that derives the ring from the score alone will silently
  contradict a level the user picked — that is exactly the bug in V0.67 (placement hardcoded
  3×3, so every node scored 9 = AMBER and every ring drew amber whatever was selected).
- Have exactly ONE table of band defaults (`LS_FOR_LEVEL` in `lib/risk.ts`) and ONE set of RAG hex
  colours (`RAG_HEX`). Two copies of either will drift.
- When existing rows are found to contradict each other, **surface it and offer a one-click fix —
  never auto-backfill**. In V0.67, 8 of 13 nodes had level ≠ L×S in BOTH directions, so any
  automatic repair would have silently rewritten half of them the wrong way. MARU is
  liability-minded about records; guessing on his data is worse than asking.

**Everything is scoped to a PROJECT.** A project = one development site. Routes resolve it
from `?projectId=` (via `lib/api-project.ts`), falling back to the earliest `projects` row so
single-project/legacy calls still work. Contexts get the active project from
`ProjectsContext` (`localStorage` key `cdm.activeProject.v1`) and re-fetch when it changes.
**Never** hardcode a project id in a route — that silently merges two sites' data.
The MODELS catalogue is deliberately GLOBAL (shared across projects); every other site layer
is per-project. `ScreenContext` switches `home | workspace` and holds the create-project form
draft (so "pick on map", which leaves Home, does not wipe what the user typed).

Wire shape is camelCase; DB columns are snake_case; the route's normalizer maps between them.

**Schema source of truth is `supabase/migrations/` — NOT the Desktop.** The schema lives in
`supabase/migrations/001`-`007`; each is the canonical, commented record. The copy MARU pastes is
GENERATED from one of them by `scripts/migration_to_paste.mjs`, which strips every whole-line
comment. Never hand-maintain a Desktop `.sql` and never treat one as the source of truth: they go
stale silently, and a missing column then surfaces as a raw Postgres error mid-use. See
"Schema changes: ONE Desktop file" below for the paste-file rules and the one-file invariant.

## Contexts (state tree)

`AppShell.tsx` composes: Models → ModelPlacement → Risk → Layers → Plot →
Buildings → RiskZones → RiskNodes → Surroundings → PanelLayout. Keep new
cross-panel state in a context, not props.

The globe has FIVE layers that must stay INDEPENDENT (own context + own table +
own Cesium entity set). Never couple them: an early bug had nodes carrying
buildings, so deleting one model wiped every building off the map.

**Every per-project context MUST auto-fetch on mount and on project change** —
`useEffect(() => { void refresh(); }, [refresh])`, with `refresh` keyed on
`activeProjectId`. The multi-project refactor dropped this effect from
`BuildingsContext`, `PlotContext` and `RiskZonesContext`: placed buildings/plots/risk-zones
only appeared while you placed them live and VANISHED on every reload (the context starts
empty and never fetches). Symptom signature: a layer renders during placement but is empty
after refresh, and the dev-server log shows the `/api/<layer>` request NEVER fires while
sibling layers (risk-nodes, surroundings) do — that absence is the tell, not a rendering
bug. After ANY context refactor, verify with `grep -c 'void refresh()' contexts/*.tsx`
(1 per provider); the freshly-placed-renders-but-reload-wipes pattern almost always means
the load trigger is missing, not that the data or render is wrong.

| Layer | What | Table |
|---|---|---|
| Risk nodes | Unified risk record (human OR AI). Colour = risk CATEGORY; ring = RAG criticality from L×S. Optional radius circle or expanded polygon | `risk_nodes` |
| Buildings | An uploaded GLB dropped at a coordinate; move/rotate/scale | `site_buildings` |
| Plots | To-scale footprint W x D metres + heading | `site_plots` |
| Risk zones | Manually drawn RED/AMBER/GREEN RAG areas | `site_risk_zones` |
| Surroundings | Real-world context geometry from OSM, built by headless Blender | `context_imports` |

Seeded/demo polygons were PURGED (`scripts/purge_demo_data.mjs` deleted the 3 `site_risks`
demo rows). Risk now enters ONLY as `risk_nodes` (manual or AI), so the Risk Register and the
PDF export both build from `risk_nodes` — and only reportable ones (`OPEN` + `accepted_by`).
`site_risks` + `/api/risks` remain as unused legacy; do not resurrect them for demo data.

## UI conventions MARU asks for

- Tools live in ONE floating panel on the map's left edge, as an **R-Tessera-style
  vertical flyout tab strip**: click a tab → panel slides out; click again → closes.
  Tabs today: Node / Surroundings / Building / Plot / Risk. Make panels wide
  (~20rem) and tall so model lists are readable.
- **Panels must NOT sit inside an `overflow-y-auto` body** — it silently clips any
  dropdown inside them, so the user clicks a picker and sees nothing.
- Both side panels (Layer Controls, Agentic Workspace) default COLLAPSED, so the
  map opens full-width.
- **Persist screen + panel state to localStorage.** `useState` for `screen` (home/workspace)
  and `simOpen` means a refresh returns the user to the homepage with all panels closed —
  which reads as "the app forgot where I was". Both should persist under their own
  `cdm.screen.v1` / `cdm.simOpen.v1` keys, and a run completing should auto-open the
  Simulation panel so the result is visible without a manual refresh.
- The Edit-Node panel is FREE-FLOATING: anchor it to the node's live screen
  position (project world→window each frame via `SceneTransforms.worldToWindowCoordinates`)
  and let the user drag it by a header grip.
- HUD chips are all LEFT-aligned (basemap group, then actions, then coordinates).
  A right-aligned group collides with the coordinate chip.
- HUD chips in the map top bar are for the BASEMAP and actions (Satellite/Street, scan,
  coordinates). LAYERS — including 3D Terrain and Terrain Shading — belong in the Data Overlays
  panel, where a user hunting for a layer actually looks.
- Two independent dimensions on a risk node, never conflated:
  **colour = risk CATEGORY** (water, geotechnical, congestion, fire, structural,
  traffic, utilities, environmental, other — user-pickable, each with a default
  colour) and **ring = RAG CRITICALITY** from the OSHCIM L×S score, always drawn
  (10 m minimum radius) so criticality reads at a glance.
- The L×S editor is a **clickable 5×5 HSE matrix grid**, not two sliders: rows =
  Likelihood 5→1 (Frequent→Improbable), columns = Severity 1→5, each cell coloured
  by its RAG band showing level label + score, current cell ring-highlighted.
  HSE reviewers expect this shape. Thresholds live in `lib/risk.ts`
  (`levelForScore`: ≥15 RED, ≥5 AMBER, else GREEN).
- **Site location needs a visible marker + a way back.** Picking a site on the globe drops a
  PIN and holds briefly so the user SEES where they clicked before the screen changes back —
  an instant return with no marker reads as "nothing happened". Opening a project labels its
  site with a pin and flies the camera there; the HUD keeps a homing button (top-right) to
  return after panning away. MARU asks for this pattern explicitly: act on the globe, leave a
  durable trace of the action, and give a one-click route back to it.
- **Never leave demo data referenced in chrome.** After purging demo rows, the bottom legend
  still advertised the deleted zones and the HUD chips still read hardcoded KL values while a
  second project was active. When data becomes multi-site, sweep the HARDCODED labels too —
  they are the last place stale demo data hides.
- **Prefer "Load Building" picker → arm place mode → click globe. Do NOT add
  separate "place onto node #N" buttons; they spawned stray numbered pins.**
- **A growing set of generated results is a set of LAYERS — one switch each, never a single
  "current one".** MARU asks for this shape the moment N artefacts accumulate (simulation
  results are the first instance: *"each one of it treated as layer that i can turn on and off"*).
  The pattern, reusable for any future list-of-results feature:
  - Visibility lives in `LayersContext` as `Record<itemId, boolean>` keyed by the row id, under its
    OWN `localStorage` key (`cdm.<thing>Layers.v1`). Do NOT fold unbounded ids into
    `cdm.overlays.v1` — that loader validates against a FIXED key set and would churn forever on
    ids it can never recognise.
  - **An id ABSENT from the map is VISIBLE.** A newly finished result must appear on the globe
    with nothing ticked first; hiding one is a deliberate act that survives a reload. (Invert the
    sense and every new result silently fails to show.)
  - Keep the parent overlay key as the MASTER ("hide all of them"). Per-item switches are an
    ADDITION, never a replacement. Offer All on / All off, and cap the rendered list (~8 rows) with
    a "+N more" line so the panel cannot grow without bound.
  - **One switch, not two ideas of "shown".** If a panel also has a "Show on globe" button it must
    drive the SAME state, or the two disagree and the user cannot tell which is authoritative.
    Retire any single `displayX` selection concept rather than keeping both.
  - **Split geometry from visibility into TWO effects.** Rebuild entities only when the LIST
    changes; toggling flips `entity.show` only. Rebuilding every MultiPolygon on each switch is
    needless work on a map holding several large results.
  - Prune the map when the list changes, and **return the SAME object when nothing is stale** —
    otherwise the prune triggers a render, which triggers a write, on every refresh.
  - Label each row with the SETTING that produced it (`Flood Inundation · 5 m · 7.4 ha`), not just
    the plugin name — a 2 m flood and a 10 m flood are otherwise indistinguishable in the list.
  - Give the same toggle a colour dot matching the geometry on the globe, so the row can be
    matched to what is drawn.
- **Housekeeping asks are a recurring class — treat legends as toggles, kill dead controls,
  keep chips uniform.** MARU batch-asks for button placement/shape, glassmorphism consistency,
  and "make the X do something". Generalize the rules:
  - A bottom Red/Amber/Green legend should be a LIVE filter that shows/hides risk zones and
    risk-node rings by OSHCIM level (back a shared `riskFilter` in `LayersContext`; apply it as
    `entity.show` in the zone + node render effects). If you show the RAG legend, MARU will want
    to switch those colour groups off/on — never leave it as static labels.
  - Remove controls that do nothing rather than leaving them inert — a dead button reads as
    broken. (The Terrain switch was deleted for exactly this reason before it could be built
    properly; if a control cannot work yet, do not ship the control.)
  - Every HUD control AND the collapsed edge tabs must share the same `lunav-glass-chip` style;
    a lone odd-shaped control reads as broken.
  - Do not put dead filter state in a panel (the old Risk Tolerability chips in the Layer panel
    toggled a local array that nothing read); put the control where the action is (the map) or
    wire it. A switch that visibly does nothing is worse than no switch.
  - Give the fly-to/home button its own corner (bottom-right) so it never overlaps the top bar's
    wrap — the top bar uses `flex-wrap` and a right-aligned `ml-auto` control collides when it
    wraps.
  - Drop decorative counts (the "N active" chip) unless they carry a decision.
  - When he says rename a tab ("Layer & Risk Controls" → "Layer Control"), sweep every label:
    the open header, the collapsed edge-tab text, AND the `aria-label`s.

## Pitfalls that have cost real time

**A thrown geometry build does not fail one entity — it stops rendering app-wide.**
Everything below has silently blanked or frozen the globe at least once.

- **The Cesium viewer init effect MUST have `deps: []`.** Read all callbacks
  through a ref bag (`actionsRef.current = { placeNode, addPlotAt, ... }`). If the
  effect depends on a `useCallback` whose identity changes (e.g. picking a
  different model), the whole viewer is destroyed and rebuilt: camera resets, all
  placed entities vanish, then glitch back on the next change.
- **Never attach `outline`/`ellipse` to a `CLAMP_TO_GROUND` entity.** Cesium does
  not support it — it throws and the node disappears. Draw the circle as a
  SEPARATE entity on the ellipsoid surface. Wrap every entity build in try/catch.
- **`outlineWidth` is ignored on `ellipse`** on most WebGL builds (stays ~1px, so
  "thicker line" appears to do nothing). For a thick ring, sample the circle into a
  128-segment closed loop and draw a `polyline` with a real `width`.
- **Rotation:** set `orientation` on the Entity via
  `Transforms.headingPitchRollQuaternion` — putting it inside `model` graphics
  alongside `heightReference` is silently ignored, so the rotate slider does nothing.
- Render effects that read `viewerRef.current` must ALSO depend on a `viewerReady`
  state flag, or they run before the async viewer exists and silently bail (placed
  buildings only appeared after some later unrelated change).
- **NaN vertices stop ALL Cesium rendering** ("normalized result is not a number").
  Cause: a render helper read snake_case fields (`plot.center_lon`) while the API
  returned camelCase, so `Number(undefined)` = NaN. Always guard rows with
  `Number.isFinite` before handing them to Cesium.
- **Bulk-drawn geometry (scan features, multi-feature overlays) must be sanitized BEFORE it
  reaches Cesium, in two layers.** A single bad primitive throws `RangeError: Failed to set the
  'length' property on 'Array': Invalid array length` inside `createPotentiallyVisibleSet` and
  freezes the ENTIRE viewer (all other layers vanish with it). Server side: CLIP every feature
  to the scan box before sending it — osmium's complete-ways export returns WHOLE ways that
  cross the box (a river/railway renders kilometres past it), so clip lines (Liang–Barsky),
  polygons (Sutherland–Hodgman), drop out-of-box points, and snap results to the box edge
  (floating-point interpolation otherwise leaves ~1e-9 escapes). Client side: finite-check +
  drop consecutive duplicates + enforce min points (2 for a line, 3 for a polygon), reject
  zero-area rings (shoelace) which emit NaN, add each entity in its OWN try/catch so a bad one
  is skipped instead of killing the loop, and cap the number of features drawn (the counts
  summary is unaffected). Validate by walking every returned coordinate against the box bounds
  — assert 0 escapes, not "looks right".
- **Match nodes to models by `file_url`, never `assigned_pin_id`** (that column is
  never persisted on placement; keying off it detached every model from every node
  whenever the catalogue changed — deleting one unrelated model wiped them all).
- Cesium entity `model.scale` is a single uniform scalar — only X affects on-map
  size; per-axis needs a modelMatrix approach.
- One polyline per Cesium Entity (multi-branch lines collapse otherwise).
- **Prefer the formulation with the FEWEST sign conventions.** A direction-dependent formula
  assembled from aspect, zenith and an azimuth offset depends on three or four conventions at
  once (is dz/dy northward or southward, how is azimuth measured, which way does the raster's row
  index run), and inverting ANY one of them yields a plausible-looking number that is
  mirror-flipped. This has now bitten twice — the hillshade rendered a slope FACING the light
  darker than flat ground, and the sun's hour angle put the sun due west at 09:00. The fix is not
  to hunt the sign: re-derive in the form that has no convention to argue about (compute the
  surface NORMAL and dot it against the LIGHT VECTOR) and prove it against a tilted plane.
- **Next.js App Router: a `route.ts` serves exactly ITS OWN path segment.** A handler whose
  docstring advertises `/api/x/image` still needs `app/api/x/image/route.ts` — the parent file
  does not catch the nested path, and the request 404s with an HTML page rather than an API error.
  Branching inside one handler on a query param is not a substitute. **Call every endpoint you
  write, including ones you documented rather than coded** — that bug survived a clean typecheck,
  a clean build, and a re-read of the docstring that claimed it existed.
- **Any query param used to build a FILESYSTEM path must be validated against the exact shape you
  generate.** The shading image is addressed by a hash key; without a `/^[a-f0-9]{16}$/` test
  before `path.join`, a crafted `?key=../../…` reads any file on the machine — and the cache
  directory is a well-known location, so that test is the only thing in the way. Assert the guard
  by CALLING it (`?key=../../etc/passwd` must return 400), not by reading the code.
- To-scale ground rectangles: derive corners from centre + metres using
  ~111,320 m/deg latitude and longitude × cos(lat), then rotate by heading. For
true-size circles prefer the metre-based `EllipseGraphics` (semiMajorAxis/
semiMinorAxis) so size is right at any latitude.
- Camera freedom comes from enabling `homeButton` / `sceneModePicker` /
  `navigationHelpButton` on the Viewer.
- **The globe being FLAT is not the same as "no terrain exists".** These are two different
  things and conflating them wastes a session: the visible surface is an ellipsoid wearing live
  Esri imagery tiles, while the DEM is a local 44 MB file that ONLY the Python plugins read. The
  browser never receives a single elevation value — the most it ever learns is a tile's NAME. So
  a flood result is a correct shape lying on ground it was never compared against, and the 3.5 m
  step the analysis found is invisible on screen.
- **The Terrain toggle is BUILT and works — from the LOCAL DEM, no Cesium ION token.** It used to
  be a dead control (`terrain: false`, and with no ION token its effect returned early, so flipping
  it changed nothing) and was eventually DELETED from the interface, leaving `overlays.terrain` as
  an orphan key. It is back. Two switches, one job each, as MARU approved: **3D Terrain** reshapes
  the globe via `CustomHeightmapTerrainProvider` fed by the site's own Copernicus DEM, and
  **Terrain Shading** draws a plan-view hillshade over the imagery. Never one switch doing both.
  Both live in Data Overlays and both state the REASON under the label when they cannot work
  (no DEM for the site, or a hosted build) rather than appearing to do nothing.

### Blender exits 0 even when the Python script raises

This turns every real failure into a lying error message. Blender does not propagate an
uncaught Python exception to its exit code, so the worker sailed past the failure and died at
`fs.readFile(outFile)` — reporting `ENOENT: no such file or directory, open '.../surroundings.glb'`
when the actual cause was `HTTP Error 504: Gateway Timeout` from Overpass.

- **Always invoke Blender with `--python-exit-code 1`.** Without it a crashed build looks like a
  missing-file bug and sends you hunting the wrong layer entirely.
- **Surface Blender's own output in the job's `error_message`** (`summarizeBlenderFailure` in
  `surroundings_worker.mjs` greps for the last `RuntimeError:` / `HTTP Error NNN`). The real
  cause is buried in pages of startup logging.
- Have the script VERIFY the export exists and is non-empty before printing success.
- Diagnose by running the Blender command BY HAND and reading its log. Reproduce the exact
  worker invocation, then `tail` the output — the answer is always in there.

### Overpass is flaky — retry before concluding anything

`overpass-api.de` intermittently returns **504** under load and **429** when hammered; the SAME
bbox can fail, then succeed seconds later on retry. Do not treat one failure as "the source is
down" (and do not "fix" it by changing the bbox, projection or asset handling — that is a
wild-goose chase through the wrong layer).

- `build_surroundings.py` cycles blosm's mirrors via `addon.osmServer`:
  `"overpass-api.de" | "private.coffee" | "vk maps"` (exact enum keys), with backoff passes.
- Treat "blosm reported success but produced zero meshes" as a FAILURE so it falls through to the
  next mirror — otherwise an empty area silently exports an empty scene.
- Radius stays capped at 1 km; Overpass slows badly beyond that.
- Mirror retries are DAMAGE CONTROL, not the fix. The durable answer is to drop the live
  dependency entirely — verified blosm capability map + local-extract plan in
  `references/offline-osm-data.md`.

### A killed worker strands the job on BUILDING forever

Claiming a job stamps `updated_at`; `reclaimStaleJobs()` re-queues anything stuck on `BUILDING`
for >10 min so a closed laptop can't leave the UI spinning indefinitely. Needs
`context_imports.updated_at`.

## Human-in-the-loop (a liability requirement, not a UX nicety)

MARU: *"i cant let the blame go to yolo if anything happened."* Statutory duty
stays with the Principal Designer, so the ML must never be the decider.

Every risk — human-placed or YOLO-detected — is one `risk_nodes` row carrying
`source` (MANUAL / AI_DETECTED / HUMAN_ADJUSTED), `status` (DETECTED / OPEN /
REJECTED / MITIGATED), plus `accepted_by`, `reviewed_at`, `ai_confidence`.

- YOLO writes `DETECTED` candidates; they render distinctly and are NOT reportable.
- The reviewer gets Accept / Adjust / Dismiss. Accept or Adjust stamps
  `accepted_by` + `reviewed_at` and moves it to `HUMAN_ADJUSTED`/`OPEN`.
- **Only `status='OPEN' AND accepted_by IS NOT NULL` may appear in a report.**
- Report wording: "AI detections are advisory candidates subject to review and
  endorsement by the Principal Designer, who holds statutory responsibility under
  CDM 2024 / OSHCIM 2017."

Never fabricate product controls (RBAC, encryption) the code does not have, and
keep legal copy generic and non-overclaiming.

## YOLO model management

`Settings > AI Detection > YOLO > Custom model` (three nested levels, deliberately
buried). `ai_models` table + `/api/ai-models`; exactly ONE model active at a time
(activating one clears the others); custom weights upload to the `ai-models`
Storage bucket. Seeded with the YOLOv8n COCO baseline. The scan pipeline reads the
active model at runtime, so swapping COCO for a fine-tune is config, not a redeploy.

## Surroundings (real-world context) — LOCAL DATA ONLY, no third-party API

Pulls existing buildings/roads/water around a point, giving a siting study its real context.

**MARU's hard requirement: no network API for this.** Live Overpass was rejected for a
commercial product — a demo must not die because a stranger's server is busy. So blosm reads a
LOCAL dataset, and a study is reproducible (the data date can be cited; live data meant two runs
a week apart could differ).

### The pipeline

1. **One manual download** (`Settings → Map data`), ~239 MB, Geofabrik
   `malaysia-singapore-brunei-latest.osm.pbf`. Stored OUTSIDE the repo at
   `~/Library/Application Support/CDM/osm/` (large per-machine asset).
2. **Per build:** slice the site's bbox out of that file with **osmium**
   (`brew install osmium-tool`) and convert to OSM XML; blosm reads the small local XML.

### Why the slice-and-convert (verified in the addon source)

- blosm parses **XML only** (`etree.parse` in `parse/osm/__init__.py`). It has **no .pbf
  support** and cannot read gzipped input — so a raw Geofabrik PBF cannot be handed to it.
- It loads the whole file into memory, so a whole-country XML would be hopeless. Hence: slice
  the bbox with osmium, feed blosm a tiny file.
- `osmium extract --bbox minLon,minLat,maxLon,maxLat` → `.osm` takes ~1 s.

### Two silent-network traps — both must be closed

1. **`addon.loadMissingMembers`** makes blosm fetch incomplete relation members from the
   server even in file mode. Set it **False**, or you are back to a live dependency invisibly.
2. **Never fall back to a mirror on a local failure.** A mirror-cycling retry on the local path
   would silently reintroduce the network. Local mode = exactly one attempt, then fail loudly
   ("the site may fall outside the downloaded map data").

### Georeferencing bug: pin the projection ORIGIN in file mode

Server mode sets the projection from the bbox centre. **File mode instead derives it from the
DATA EXTENT** (the OSM nodes actually present) — which is near, but not equal to, the centre we
store on `context_imports`. Two consequences: the model sits off its trace, AND the bbox CLIP
(this script's own `TransverseMercator`) filters against a mismatched coordinate space.

**A/B on one KL site: pinned origin = 165 buildings, unpinned = 146** — 19 buildings (~12%)
wrongly dropped. Fix: before `import_data()`, set
`addon.relativeToInitialImport = True` and seed `scene["lat"]`/`scene["lon"]` with the bbox
centre; blosm then calls `osm.setProjection(ours)` and `setLatLon` stays False so it won't
overwrite them. Symptom to recognise: building COUNT changes with a pure origin change.

### Running it

**Blender cannot run in a serverless function** (879MB, no persistent FS, long runtime), so the
web app only QUEUES: `POST /api/surroundings` writes a `context_imports` row (`QUEUED`), and a
LOCAL worker claims it, builds, uploads and flips it `READY`/`FAILED`. The UI polls every 5s.

- Script: `scripts/build_surroundings.py` (OSM buildings/highways/water → single `.glb`).
- **The app spawns the worker itself — the user never opens a terminal.** MARU rejected
  "run `npm run surroundings:worker`" outright. `POST /api/surroundings` fires
  `spawn(node, [worker, '--once'], {detached:true, stdio:'ignore'}).unref()`; it drains the
  queue and EXITS. A parked poller is only ~40–60 MB, but Blender is ~500 MB–1 GB — spawn
  on demand so that cost is paid only during a build. Skip the spawn on serverless.
- **Auto-discover the toolchain; require no env vars.** Walk
  `~/Library/Application Support/Blender/*/scripts/addons/blosm` (and `~/.config/blender/*`),
  probe the usual Blender binary paths. `BLENDER_BIN` / `BLOSM_PATH` are optional overrides.
- **Georeferencing gotcha — it is the AXIS, not the origin or scale.** blosm exports local
  metres relative to the bbox centre (that part is correct), but with **+X=east / +Z=south**,
  while Cesium's `getAxisCorrectionMatrix(Y-up, Z-forward)` maps **glTF +Z→East, +X→North**.
  An OSM import therefore lands rotated ~90° — default `heading_deg = 90` for `source='osm'`.
  A lone uploaded building hides this (rotation about its own centre looks identical); only a
  cityscape exposes it. **Confirmed correct by MARU**: with 90° the imported building overlaps
  its satellite trace. Read the symptom signature, not the numbers: a model building sitting over
  greenery while the real building is a few hundred metres to one side is a ROTATION about the
  origin, never a translation or scale problem.
- **Clip geometry to the bbox before export.** Overpass returns whole ways that cross the box,
  so roads/waterways/landuse run kilometres out (a 1 km import measured 36 km × 19 km, one mesh
  17 km away). Cesium sizes and frames a model from its bounding sphere, so the import renders
  misaligned. Trim with `bmesh` to the bbox + ~25 m margin. Also drop `minimumPixelSize` from a
  large context model.
- Ship **manual alignment** (Rotate / move E-W-N-S / Scale / Reset, persisted) as the escape
  hatch — a perfect automatic georeference is fragile across sources.
- Radius is a key-in box capped at **1000 m** (Overpass slows badly beyond
  ~1km); validate server-side too.
- Render imported context MUTED (grey, blended) so the proposed building stays the
  hero. Show **"© OpenStreetMap contributors (ODbL)"** — attribution is required.
- Verified end-to-end on Blender 5.1.2 + blosm: a ~300 m KL bbox produced a valid
  glTF 2.0; a 1 km import produced 896 buildings / ~1.9 MB.
- `context_imports` also carries the alignment fields (`offset_east_m`,
  `offset_north_m`, `scale`) so a manual adjustment survives reload — added in
  `~/Desktop/apply_cdm_surroundings_v2.sql` (also retro-sets existing OSM imports to 90°).
  The Rotate slider works without it, but Move/Scale error until it is applied.

## Spatial Context Scan — REAL feature detection (no image model)

MARU asked to "run YOLO for real" and detect rivers/slopes/rail/schools/density on the basemap.
Stock COCO YOLO CANNOT do this: it is trained on ground-level photos of 80 object classes — not
satellite imagery, and these are GEOGRAPHIC FEATURES, not objects. The honest answer is Path A:
read the SAME local OSM dataset used for Surroundings, classify features by tag, and highlight
REAL, citable data. This replaced the old mock detection (`/api/scan` no longer fabricates a
"slope instability" polygon). Slope specifically is a DEM/terrain problem, not vision (flat
globe, no elevation source).

- **Pipeline:** `scripts/spatial_scan.mjs` — `osmium extract` the box from the local pbf, `osmium
  export -f geojson` (flattens tags into `properties`), then classify by tag: `waterway`/`natural=water`
  → WATER; `railway` → RAILWAY; `amenity` ∈ {school,hospital,police,worship,government,…} →
  PUBLIC_INTEREST; `leisure`/`landuse` park-ish → PARK; `landuse=residential` → RESIDENTIAL;
  `power`/utility → UTILITY. Count `building` tags separately as a density signal.
- **Scan box = the project's Surroundings coverage** (radius of the largest READY
  `context_imports` row — "the area that built the 3D model"), else the project site + 500 m.
  The route resolves that box; the client sends only `projectId` (no hardcoded centre).
- **CLIP every feature to the box** (same discipline as Surroundings) — a crossing way otherwise
  renders kilometres out. Points outside are dropped; lines/polygons clipped; snap to the edge.
- **Scan results are CONTEXT, not automatically-reportable risk.** Highlight them by category
  colour, but do NOT let them enter the Risk Register or the PDF — only a hazard a person
  explicitly accepts as a `risk_node` is reportable. The old code appended a "live detection" to
  the PDF; removing that was the liability-correct move.

## Plots: three ways to define a boundary (box / traverse / clicked polygon)

MARU wants the real shape, not a fixed box dropped from a click. The Plot tool now has a
**method switch** (Box | Traverse) and a plot's `source` column records which was used:

| Method | Use when | Status |
|---|---|---|
| `box` | you only know W x D | built (V0.62) |
| `traverse` | you have the title / plan (bearings + distances) | built (V0.62) |
| `polygon` | you can see the boundary and want to trace it | **built (V0.63)** |

**Keep ALL modes — they are not alternatives.** The box is EXACT (56 x 67 m really is that); a
clicked polygon is not. Say plainly that a clicked polygon is NOT survey-grade and steer anything
compliance-grade to exact geometry — MARU raised the accuracy point himself and does not want it
papered over.

**The click-to-draw polygon (built V0.63) — `contexts/DrawContext.tsx`.** ONE mechanism serves
both layers; `target` ("plot" | "zone") decides where the shape lands and only the COLOUR differs.
The context holds GEOMETRY ONLY (vertices + live cursor) and deliberately cannot save, so it does
not depend on PlotContext/RiskZonesContext — each layer's own panel owns the Finish action, which
avoids a circular import.

- Vertices are committed by a globe click; a rubber band follows the pointer; the fill appears at
  3+. The area is computed LIVE with the same `areaOfLonLatRing` used for storage, so the number
  shown while drawing is the number stored.
- Controls appear BOTH on a **floating map bar** (`components/DrawHud.tsx`, above the legend —
  point count, live area, Undo / Done / Cancel, Esc to cancel) AND in the panel tab that armed the
  draw. The map bar is a SECOND route, never the only one: a floating overlay is not somewhere the
  user reliably looks, and closing the panel must not strand an armed interaction (see the "panel
  that ARMED the interaction" rule below).
- **The draw branch must be the FIRST check in the globe click handler.** An armed draw has to
  beat selection/placement/other pick modes, or a click both adds a vertex and does something
  else. Guard it with a ref (`drawActiveRef`) like every other mode, since the handler is
  registered once.
- **Vertex dragging** is IMPERATIVE, not React state: on LEFT_DOWN pick an entity id prefixed
  `plotvtx-<plotId>-<index>`, stash the ring in a ref and disable
  `scene.screenSpaceCameraController.enableRotate`; MOUSE_MOVE mutates
  `entity.polygon.hierarchy` directly; LEFT_UP re-enables rotate and commits ONE
  `updatePlotRing` write. Re-rendering every plot per pointer move would be needless churn.
- Drawn zones reuse the same path: `site_risk_zones.polygon` + `area_m2`, rendering from the ring
  and hiding the box-only controls (W/D/rotate) when a ring is present.
- **Editing must be GATED behind a deliberate act.** MARU's stated flow: click points → **Done**
  connects the dots and closes the boundary → only a DOUBLE-CLICK then **Edit** makes it editable.
  Never show corner handles on plain selection: a stray drag on a boundary someone is only
  INSPECTING silently alters a compliance artefact. `DrawContext` carries `editing` (null unless
  Edit was chosen) and the handles effect keys off THAT, not off the selection id.
- **`scene.pickPosition` returns undefined on the flat ellipsoid globe**, so anything driven by
  MOUSE_MOVE silently dies. Always fall back to
  `camera.pickEllipsoid(endPosition, scene.globe.ellipsoid)`. The click path already had that
  fallback, which is exactly why clicks placed points while the rubber band stayed dead — a
  misleading half-working symptom, and the reason to test the pointer path as well as the click.
- Draw the CLOSING edge (dashed polyline, `PolylineDashMaterialProperty`) while drawing, so the
  shape reads as a complete boundary before Done rather than as an open path.
- Name the commit button **Done** (MARU's word), not Finish, and have it connect the dots.
- **Put the commit control in the panel that ARMED the interaction, not only on a floating
  overlay.** V0.63 put Undo/Done/Cancel only on a map bar; MARU never saw it, closed the Plot tab,
  and was left with a rubber band chasing his pointer and no way to finish — "i got no way to
  confirm that that is final and done". A floating HUD is a SECOND route, never the only one, and
  closing the panel must not strand an armed interaction. Also **auto-open the owning panel when a
  draw starts** (fire only on START, so closing it afterwards still works).
- Keep the save in ONE place (`contexts/useDrawCommit.ts`) when two controls can trigger it, so the
  panel and the map bar cannot drift apart on what "Done" means.
- Say it in the UI: a traced shape is **NOT survey-grade**. The panel carries that line verbatim —
  MARU raised the accuracy point himself and does not want it papered over.

**Data model (as built).** `site_plots` and `site_risk_zones` both gain `polygon jsonb` — a
GeoJSON linear ring `[[lon,lat],...]`, stored OPEN (see the pitfalls). `site_plots` also gains
`source`, `area_m2`, `stated_area_m2` and `traverse jsonb` (the original legs). `width_m` /
`depth_m` / `heading_deg` remain but must be made NULLABLE — `ALTER COLUMN ... DROP NOT NULL` —
otherwise a box-less plot cannot insert. Migration:
`supabase/migrations/004_plot_polygons.sql` (idempotent).

**Zero-downtime ordering:** the API ships the new fields before the SQL is applied, so a save
fails with a raw `Could not find the 'area_m2' column ... in the schema cache`. Wrap PostgREST
column errors in a helper that NAMES the .sql file to run — MARU hits this every time a
migration is pending, and the raw message sends him hunting the wrong layer.

## Survey plans (JUPEM) — two routes, only ONE is survey-grade

MARU asked whether an official survey plan (PDF, e.g. from JUPEM) can be scanned and overlaid on
the globe. **A PDF has no georeference** — nothing in it says where on Earth it belongs — so this
is two distinct features, and conflating them is the trap:

- **Route A — georeference the image.** Pick 2-3 control points (a corner on the plan + the same
  corner on the imagery) and the system places/warps the plan as a ground overlay. Fast and
  visual, toggleable like Surroundings — but it is a PICTURE. Never measurable. It must be
  labelled "reference only, not survey-certified".
- **Route B — extract the geometry.** A survey plan does not just draw the boundary, it STATES it:
  bearings + distances ("N 45 deg 30 min E, 100.00 m") and/or Easting/Northing. Transformed
  properly those numbers produce an **exact polygon** with the true area — the only route a
  compliance document can rely on, and it feeds straight into the Plot layer.

**Malaysian CRS caution — the real risk.** Cadastral coordinates are NOT WGS84. Peninsular
Malaysia uses Cassini state origins / MRSO; **Sabah and Sarawak differ again**; GDM2000 is the
modern datum. The plan states which system it uses. Wrong datum/projection parameters do not put
you slightly off — they put you **tens of metres** out, i.e. on the neighbour's lot.

**The trust check to build:** compute the polygon area and compare it with the area stated on the
plan. A match validates the georeference; a mismatch flags it. That single check is what turns a
pretty overlay into something defensible.

**A real title was read, and it settled the design.** A scanned `geran tanah` / `pelan tanah`
(Borang SEK title + Borang B1 land plan, Pahang) carried **bearings and distances and NO
coordinates at all**, on a standard sheet shared with dozens of neighbouring lots — so for
Malaysian titles the route that matters is **traverse entry**. It DID state the lot area
(0.4185 ha), on the title page and again on the plan sheet: exactly the verification anchor above.
CRS table, the traverse maths, `lib/traverse.ts` API and the pitfalls are in
`references/malaysian-title-boundaries.md`.

## Multi-party collaboration (agreed V0.66; comments built, invites/reviewer next)

The app becomes multi-party per project: Engineering, Maintenance and other departments
comment on the pre-planning and tag risk from their own perspective.

**Decisions locked by MARU — do not re-litigate:**

| # | Question | Decision |
|---|---|---|
| 1 | Reviewer client | the SAME app deployed to Vercel in reviewer mode. NEVER a second standalone globe client — duplicating the globe means every node-rendering fix must be made twice, and they drift |
| 2 | Access | ONE invite token PER INVITEE, revocable + expirable. It carries their name and department, so authorship comes from the TOKEN, not a typed field — a guest cannot post under someone else's name |
| 3 | Sending invites | MARU sends the link himself (WhatsApp/email). NO mail provider: an external dependency for what is an admin action |
| 4 | Voice | SCRAPPED by MARU ("its going to be hard"). The composer is text; the phone's own keyboard mic gives dictation for free with zero build |
| 5 | Invitee-tagged risk | lands as a CANDIDATE (`source='INVITED'`, `status='DETECTED'`) — visible to all, NOT reportable until the Principal Designer accepts it |
| 6 | Comments | node-level only (no project-level thread), threaded ONE level deep |

**The "contradiction" MARU raised, and the resolution — this is the key insight.** He
worried collaboration contradicts the app being "localized". It does not: everything that
makes CDM local is the SURROUNDINGS pipeline (Blender, YOLO, the 239 MB OSM slice).
Tagging risk and commenting needs NONE of it — only Cesium from a CDN plus Supabase, which
is already cloud. So the local app is simply another client of the same database: no second
DB, no sync problem, no contradiction. Say this plainly when it comes up; it is the thing
that unlocks the whole design.

**Where the access control actually lives.** A URL is not an invitation — anyone who gets a
forwarded link could write into compliance data. Every reviewer write must resolve the token
server-side (never trust a name or project id from the request body), and reviewer mode must
REFUSE the heavy admin routes server-side (surroundings build, model upload, scan).
**Hiding a button is not security.**

**Multi-party collaboration — UI architecture (V0.68+).** Two distinct surfaces, kept separate by design:

- **Invite tab** (left-edge tool strip, after Risk) = the **creation tool**. Form to generate a new invite token: name, department dropdown, role, duration/expiry, Generate → copies link. This is the admin action.
- **Collab tab** (NEW — header button, opens `/collab` page) = the **management dashboard**. Lists every invitee with token, expiry, last login, last modified (from `invite_actions`), status, and per-row actions (Copy Link, Revoke, extend expiry). This is the operational view.

The Collab button sits in the **header** (next to the "3D Model" button), NOT in the left-edge strip and NOT on the Cesium layer. The left-edge strip stays focused on the globe tools; collaboration management is a header-level concern.

**Project scoping is already built in.** Every API route resolves the project via `resolveProjectIdFor(supabase, request)` which scopes by `?projectId=`. Project A's invites, nodes, zones, and comments are invisible to Project B automatically — no extra code needed. The Collab page reads `?projectId=` the same way. **Never hardcode a project id in a route.**

**Invites (built V0.68).** `/api/invites` + the toolbox **Invite** tab. A token is 24 random bytes
generated SERVER-SIDE and never derived from the project id or the invitee's name. Invites are
REVOKED, never deleted (`revoked_at`), so the record of who had access to compliance data survives
revocation — there is deliberately no DELETE handler. Verified 15 checks including revoke, restore,
invalid role refused and no-hard-delete.

**The invite-link trap — handle it or the demo dies at the worst moment.** The main app runs on
localhost, so a link built from `window.location.origin` works for NOBODY else, and it fails
silently for the recipient. `InvitesContext` reads `NEXT_PUBLIC_REVIEW_BASE_URL` and flags the link
as local-only when it is unset; set that var to the deployed reviewer address before sending
anything. Show the link as TEXT as well as a copy button, so a broken one is visible rather than
merely un-copied.

**Comment rules enforced in the API, not the UI** (so the reviewer client inherits them):
one level of threading (a reply-to-a-reply flattens to the same parent), soft delete only
(there is deliberately NO DELETE handler — stamp `deleted_at`), and author attribution from
the token/invite rather than the request body.

**Modification log (invite_actions table).** Every reviewer write inserts a row into `invite_actions`:
- `invite_id` FK → `project_invites(id)` ON DELETE CASCADE
- `action_type`: `node_created` | `zone_drawn` | `comment_posted` | `logged_in`
- `detail JSONB`: `{ node_id, category, level, lat, lon }` or `{ zone_id, level, vertices }` or `{ comment_id, node_id }`
- `performed_at TIMESTAMPTZ DEFAULT NOW()`

The Collab page reads this join to build the "last modified" column and the per-invitee timeline.
**Risk-nodes POST and risk-zones POST need `invite_id` added** to the insert so reviewer-created
records are attributable. Currently the POST only inserts project-scoped fields — `invite_id` is
missing. Add it as an optional field that falls back to NULL for non-reviewer writes.

**`last_used_at` update.** The `/api/invites` GET handler already returns `last_used_at`. The
reviewer page load (`/review/[token]`) should update it to `NOW()` via a PATCH to `project_invites`,
so the Collab tab's "Last Login" column is accurate. Without this, the column stays NULL and the
Collab dashboard shows no login history.

**`/review/[token]` route.** BUILT and DEPLOYED at `https://cdm-8t96n0yth-lunavs.vercel.app`. The reviewer shell (`app/review/page.tsx`) is a stripped Cesium globe with category dropdown (from `DEPARTMENTS` in `lib/user.ts`), click-to-place risk nodes, click-to-draw risk zones, comment thread on selected node, NO project switcher, NO admin routes, NO delete buttons. Server validates the token via `/api/review/token` (not revoked, not expired, project exists) → renders the shell. Every write through the reviewer resolves the token server-side and logs to `invite_actions`. Viewer accepts optional `projectId` prop for review-mode override in `CesiumViewer`.

**`/collab` page.** BUILT and DEPLOYED. Collab button is in the **header** (next to "3D Model" button), NOT on the Cesium layer and NOT in the left-edge strip. The left-edge "Invite" tab keeps the creation form; `/collab` is the management dashboard showing invitees with token, expiry, last login (from `invite_actions`), last modified, and per-row actions (Copy Link, Revoke, extend). Project-scoped: `?projectId=PROJ_A` only shows Project A invitees.

**`invite_actions` table.** BUILT via `supabase/migrations/006_invite_actions.sql`. Columns: id, invite_id FK→`project_invites` ON DELETE CASCADE, action_type (`node_created`|`zone_drawn`|`comment_posted`|`logged_in`), detail JSONB, performed_at. Trigger on `project_invites` updates `last_used_at`. Risk-nodes POST and risk-zones POST both carry `invite_id` for attribution.

**The invite table (`project_invites`) columns:** id, project_id, token, invitee_name, invitee_dept, role, created_at, expires_at, revoked_at, last_used_at. **`invite_actions` is now in `supabase/migrations/006_invite_actions.sql`** — not merged into 005, separate migration. Always probe the live schema (`scripts/probe-schema.sh`) to confirm what exists before writing migration statements.

## Schema changes: ONE Desktop file, probe before, verify after

MARU pastes SQL by hand, so **how many files he has to choose between is a UX problem, not a
detail**. He asked *"which sql where"* the instant two `apply_*.sql` files sat on the Desktop —
the symptom of the one-file rule in Hard rules not being followed.

- **Keep exactly ONE `.sql` on the Desktop at all times, and hand him that exact path.**
  `scripts/migration_to_paste.mjs <migration.sql>` produces it as `apply_<migration-name>.sql`
  (e.g. `apply_simulation.sql`), stripping every whole-line comment so select-all → paste → Run
  works verbatim. The filename follows the migration; the INVARIANT is the one-file rule — never
  create a second name because the tooling used a different one. Before naming a path to him,
  `ls ~/Desktop/*.sql` and confirm it returns exactly one file. It is
  copy-paste-pure (no comments, no headers — his "no nonsense" rule). When a change adds schema,
  MERGE the new statements into that file and DELETE whatever they supersede, so "which file?" can
  never be a question. State the count explicitly ("there is exactly one") so he does not go
  hunting for others.
- **Probe the live DB BEFORE writing the file or naming it to him.** Never assume a migration was
  applied, and never hand him statements for columns that already exist. Run
  `scripts/probe-schema.sh` — it lists every table/column from PostgREST's OpenAPI document and
  reports per-column HAVE/MISSING. Both pending migrations turned out to be entirely unapplied,
  which is why two unrelated features were failing at the same time; assuming either had been run
  would have sent the debugging at the wrong layer.
- **Verify AFTER with real writes, then clean up.** "Migration applied" is not "migration works".
  POST/GET/PATCH real rows against the live DB and assert the round-trip: the ring persists,
  `area_m2` matches the expected figure, a reply-to-a-reply FLATTENS to its top-level parent, soft
  delete hides the row, and no hard-delete route exists. Then remove the test rows — via the API
  for normal tables, and by a **direct PostgREST `DELETE` for soft-delete-only tables** (the
  comments API deliberately has no delete route, so it cannot clean up after itself). Confirm the
  user's own row counts are unchanged afterwards, and say so.
The repo's `supabase/migrations/` now holds `001`-`007` (`007_simulation.sql` adds
  `simulation_runs` + `simulation_presets`), but the older tables (`risk_nodes`,
  `site_plots`, `site_buildings`, `site_risk_zones`, `context_imports`, `ai_models`) were not all
  committed there. **The LIVE database — not the repo — is the source of truth for what actually
  exists.** Read it with the probe script rather than trusting either.

  **Migration 005 (`005_collaboration.sql`) covers:** `project_invites`, `risk_comments`, and the
  `risk_nodes` contributor columns (`contributor_name`, `contributor_dept`, `contributor_invite_id`).
  It does NOT yet include `invite_actions` — that needs a new migration or a merge into the pending
  SQL. Always probe the live schema (`scripts/probe-schema.sh`) to confirm what exists before
  writing migration statements.

## Desktop direction (decided)

**Option A — desktop installer + cloud DB.** MARU's call: heavy local processing
(Blender geometry, YOLO, simulation plugins) belongs on the machine, not on serverless.
Wrap the Next.js app in Tauri (~5MB) or Electron; the `/api/*` routes run locally;
Supabase stays the DB/storage. Bundle Cesium locally (imagery tiles stay online).
Not chosen: on-prem Docker, or a fully-offline build (offline map tiles + bundled
Python is the painful 80%).

### Simulation plugins (SIMULATION tab, agreed)

MARU requested a new header tab **SIMULATION** — a dropdown lists every available test.
Selecting one opens a parameter panel (floating, draggable, consistent with Edit Node pattern).
All parameters are user-adjustable, user-saveable, and carry a `?` hover tooltip with
name/unit/valid-range/description. Plugins run as **separate processes, one at a time**.

**Tests:** Shadow Cast, Congestion, Soil Movement, Water Runoff, Flood — extensible.

### RESULTS ARE LAYERS (V0.75) — one per run

Each finished analysis is its own layer, listed under **Analysis Result** in Data
Overlays, labelled with what produced it (`Flood Inundation · 5 m · 7.4 ha`).

- Per-result visibility lives in `LayersContext` (`simLayers`, a `runId -> boolean` map),
  NOT in `SimulationContext`. LayersProvider sits ABOVE SimulationProvider, which is what
  makes that possible — check the provider order before moving this.
- Stored under its OWN localStorage key (`cdm.simLayers.v1`). Do NOT put run ids inside
  `cdm.overlays.v1`: that loader validates against the fixed `OverlayKeys` set and would
  churn on keys it can never recognise.
- **A run ABSENT from the map is VISIBLE.** So a new result appears on the globe with no
  ticking, and hiding one is a deliberate act that survives a reload.
- The parent `overlays.simulation` switch stays the MASTER (off = hide all).
- **One switch, not two ideas of "shown".** The Results list in the Simulation panel
  drives the same state, so the panel and Data Overlays cannot disagree. The old single
  `displayRun` concept was deleted.
- Split the Cesium rendering into TWO effects: geometry when the run LIST changes,
  visibility when the toggles change. Rebuilding every MultiPolygon on each toggle is
  needless work on a map holding several large results.
- `pruneSimLayers(knownIds)` in SimulationContext drops visibility for deleted runs, and
  returns the SAME object when nothing is stale so it cannot cause a render loop.

### When a plugin returns ZERO features

Flood and shadow both produce legitimate EMPTY results — no ground below the water level,
no terrain shading anything at that sun angle. The run is `READY`, its row looks like a
success, and NOTHING appears on the globe. Say why in the row and disable
"Show on globe" ("No area to show"). An empty result is still a RESULT — stored, listed
and reportable as "no area affected", which a screening study must be able to say.

### A level that makes no difference is a FINDING, not a bug

Flood at 1, 2, 3 and 4 m on the KL High-Rise site returned the identical 7.113 ha. Before
assuming a threshold bug, check the elevation histogram: the site has a flat 75-cell shelf
and then a **3.5 m vertical gap** to the next ground level, so the water level is genuinely
INSENSITIVE across that range. Report it — it is exactly the kind of thing a screening
study exists to surface, and it stops someone paying for a hydraulic study to answer a
question the terrain already answered.

### AS BUILT (V0.70) — flood + shadow shipped

**The plugin registry is the single source of truth.** `scripts/plugins/registry.json` declares
each plugin's id, label, disclaimer, `requires` and its full parameter schema (key, label, type,
unit, default, min/max, options, and a `help` string for the `?` tooltip). THREE consumers read
it and none duplicates it: `/api/simulation/plugins` serves it to the UI, the UI **builds its own
form from it**, and `run_plugin.py` validates and CLAMPS against it. Adding a plugin is a registry
entry plus a Python function — no React change, no migration. Never hardcode the parameter form in
the component (an earlier panel hardcoded 8 fields; that is the anti-pattern).

**Runtime is a managed venv, provisioned by the app.** `scripts/py-runtime.mjs` creates
`~/Library/Application Support/CDM/runtime/venv` on first use — via `uv` when present (fast, and it
fetches the interpreter), else `python3 -m venv`. Requirements live in
`scripts/plugins/requirements.txt` (numpy, rasterio, shapely — intentionally short). MARU's rule
holds: the user never opens a terminal and never runs pip. `runtimeReady()` must import EVERY
module the plugins use, not a sample, or a venv created before a dependency was added reports
ready and then fails with a ModuleNotFoundError the user cannot act on.

**Terrain is Copernicus DEM GLO-30, not SRTM.** Public AWS bucket, **no key, no account**, 1°×1°
tiles (~44 MB), 30 m posting, vertical datum **EGM2008** — so the planned SRTM+geoid correction
became unnecessary, which removes an entire class of vertical-datum bug. Cached at
`~/Library/Application Support/CDM/dem/`, outside the repo. A site normally needs exactly ONE
tile; a bbox crossing a degree line needs two, and using one there silently truncates terrain.
Tile name = the tile's **south-west** corner (`N03_00_E102_00` covers 3–4 N, 101–102 E).
`tilesForBbox` is the only place that mapping lives; treat the max edge as EXCLUSIVE.

**JS has no `Math.nextafter`.** It is a C/Python function. Use an epsilon:
`Math.max(lat0, Math.floor(maxLat - 1e-9))`.

#### Geodesy traps — every one produced a confidently wrong number

EPSG:4326 rasters have their affine transform in **DEGREES**. This breaks three separate things,
and each fails SILENTLY:

- **Area.** `abs(transform.a * transform.e)` is a square-degree figure; multiplied by a cell count
  it rounds to `0.0 m²` while the cell count (1227) looks perfectly healthy. Symptom signature:
  *a count that is obviously right sitting next to an area that is obviously wrong.* Use WGS84
  metres-per-degree (the standard series, accurate to metres per degree — far inside a 30 m cell).
- **Converting a Shapely area.** A geometry area is in the CRS's own units, so multiply by
  `m_per_deg_lat * m_per_deg_lon` — NOT by the per-cell area in m². Getting this wrong makes every
  polygon fail a `min_patch_m2` filter, so a valid mask yields **zero features**.
- **`simplify_m`.** Shapely simplifies in the geometry's own units, so a metre tolerance passed
  through raw becomes a tolerance in DEGREES. Convert first. Also: on a 30 m DEM a tolerance below
  ~30 m removes **nothing** (the boundary is a 30 m staircase) — say so in the parameter help
  rather than letting the user think the control is broken.

**Never trust one route to an area.** Compute it BOTH ways — `cells × cell_area` and the dissolved
geometry's area — and assert they agree. They come from independent code paths, so agreement is
real evidence and disagreement localises the bug immediately. This is the single highest-value
check in the suite.

#### Solar-position traps

- **Normalise the hour angle to (−π, π].** A raw `lst - ra` lands near +296° where the truth is
  −64°: the same physical angle, opposite hemisphere. **Elevation is blind to it because cos is
  even**, so the elevation comes out right while the azimuth is 180° wrong — the sun reads due
  WEST at 09:00. Symptom signature: *a solar position that looks sane until you ask which way it
  faces.*
- **The equinox is a free oracle.** On 21 March the sun rises due east (azimuth 90°) and sets due
  west anywhere on Earth, and peak elevation ≈ 90 − latitude. Measured 90.0° / 270.5° / 86.7° vs
  86.5° predicted. Use it; it costs nothing and catches sign errors instantly.
- **Azimuth is meaningless near the zenith.** At 85° elevation a small solar movement swings the
  azimuth through a wide arc in minutes. Assert on a mid-morning / mid-afternoon sample, never at
  local noon.
- **A ray march must step in METRES, not cells.** Requiring `step * tan(sun)` metres of rise per
  CELL makes terrain climb ~30× too fast on a 30 m DEM — 74% of a flat river plain came back
  "shaded". Convert the ground step to cell offsets.
- **Verify a ray march against a hand-computable rig**, not real terrain: a 100 m wall under a 45°
  sun MUST cast a 100 m shadow. Measured 93 m on a 30.9 m grid — inside the discretisation. A test
  that cannot fail is not a test, and real terrain gives you nothing to check against.
- **A sweep must sample interval MIDPOINTS**, not endpoints. Sampling `t, t+30, …, t+300` for a
  300-minute window gives 11 instants and makes every duration ambiguous by a whole step — "sunlit"
  came out equal to the full window even though the first sample was before sunrise. Also exclude
  night samples from shaded minutes (counting them is literally true but reports 100% of the site
  shaded for any pre-dawn window) and report the excluded night minutes explicitly.

**Honest scope, stated in the UI.** Flood is a SCREENING method (bathtub / HAND) — no routing, no
velocity, no duration, not a substitute for hydraulic modelling. Shadow is TERRAIN ONLY — no
buildings, no vegetation. Both carry a `disclaimer` string in the registry that the panel displays.
On a flat site shadow legitimately reports ~0%; that is the terrain, not a failure — check the
site's relief before concluding the plugin is broken (Temerloh had 43 m of relief over 2.8 km).

**Results are STORED, never recomputed for display.** A result is evidence for a siting decision
and must not change under a report that already cites it. They render on the SAME globe via a
`simulation` overlay key — and that key must be EXCLUDED from `DATA_KEYS`/`BUILDERS` in
`CesiumViewer` (those are for async-built overlays) and given its own effect, exactly like
`surroundings` and `riskNodes`.

`npm run sim:selfcheck` runs the invariant suite (20 checks). `scripts/plugins/selfcheck.py`
asserts properties any correct answer must have — the two area routes agree, area is monotonic in
water level, safety factor is equivalent to raising the level, min-patch only REMOVES area, and the
sun has the properties the sun actually has.

**An input-insensitive result is usually a property of the DATA, not a bug — histogram the driver
before touching the code.** Flood at 1, 2, 3 and 4 m on one site returned the identical 7.113 ha,
which reads exactly like a threshold or off-by-one bug. The elevation histogram showed why: a flat
75-cell shelf at 0–0.5 m above datum, then a **3.5 m vertical GAP with zero cells**, then the next
ground at 4.0 m. Water level genuinely does nothing across that range and then jumps (+3 cells at
5 m, 89 at 8 m, 111 at 10 m). Check the driver variable's distribution FIRST; when the band is
empty the plugin is right — and the surprise is real site information worth telling MARU, because
"arguing about 2 m versus 3 m on this site is arguing about nothing" is exactly what a screening
run exists to surface.

**When verifying a run by hand, read the project's REAL coordinates — never reuse the last site
you tested with.** `resolveProjectIdFor` falls back to the EARLIEST `projects` row, so "the active
project" is not whichever site you last worked on. Get lat/lon from `GET /api/projects` first.
Symptom signature: `load_dem` raises `No terrain data in the requested area (is the site on
land?)` — that means the bbox falls outside the tile you passed, i.e. WRONG COORDINATES, not a
corrupt or missing tile. Chasing the tile download is the wrong-layer wild goose chase.

**DEM data management — as planned, then superseded by the Copernicus build above.** The list
below was the SRTM-era plan; V0.70 shipped Copernicus GLO-30 instead (keyless, already EGM2008),
so the SRTM + geoid-correction steps did NOT happen and are not needed. What survives is the
pattern and the still-open custom-upload idea:

- One download per site tile, stored locally (`~/Library/Application Support/CDM/dem/`) — same
  pattern as the OSM extract: download once, work offline, cite the data date.
- User-uploaded DEM (selectable per test) is **still open** — the `terrain_source` idea was not
  built; the panel currently has no DEM picker.
- Geoid correction is **not needed** with Copernicus GLO-30 (it is already orthometric/EGM2008).
  It WOULD be needed for raw SRTM — one more reason the Copernicus choice was the right one.

**Plugin contract:** input JSON path → plugin runs as subprocess → output GeoJSON path → CDM reads + renders as new Cesium layer.
Isolation: subprocess per plugin (crash-safe; one segfault does not take down CDM). Same pattern as ROVER-KIT's local model runner.

**When a hydrology plugin needs shared terrain analysis (fill, flow direction,
accumulation), compute it once in a shared helper and have both plugins consume it.
The flood plugin (V0.70) computes depression fills, D8 flow direction, and flow
accumulation; the water_flow plugin (V0.80) also needed all three so
`drainage_and_flow` computes them once and both plugins call it. This avoids two
copies of the same expensive pass, which would drift apart.**

**Parameters per test (all adjustable + saveable):** each test declares its param schema;
CDM renders the form. Shadow cast: sun lat/long, date/time, height source, DEM selection.
Flood: DEM selection, water level (m), return period (yrs), reservoir polygon.
Water flow: rainfall intensity, infiltration rate, runoff coefficient, Manning's roughness.
Soil movement: DEM, soil type, cohesion, friction angle, rainfall, safety factor threshold.
Congestion: path network, demand points, walking speed, time window.

**Key design decisions:**
- DEM pipeline is the blocker — shadow cast first validates the plugin mechanism, then flood/runoff follow once DEM is sliced.
- Vertical datum correction (EGM2008) mandatory for flood; SRTM is ellipsoidal, offset 10-30m in Malaysia.
- Resolution trade-off: SRTM 30m is fine for flood/soil; shadow cast is blurred at that scale.
- Copernicus GLO-30 is keyless and already EGM2008 — SRTM + geoid correction is not needed.
- Free data sources only (MARU rule); no third-party API.

Full plugin contract + parameter schemas + results rendering in `references/simulation-plugins.md`,
which also carries a **reference-architecture section** distilling GeoLibre Desktop's proven sidecar
patterns (framework-free shared compute, /status graceful-degradation contract, backend-served param
schema, generic async jobs, separate-process heavy models, hardened localhost token + path
allowlist) as the model to copy when building CDM's plugin host. That file also documents the
`wind_detail` CFD pipeline (4 stages: geometry→STL, dict generation, mesh+solve, post-process) and
the OpenFOAM v2606 snappyHexMeshDict/turbulence pitfalls discovered while building it.

## Deploy to Vercel (lunavs team)

CDM is deployed as a Vercel project under team `lunavs`, project name `cdm`. See
`references/vercel-deploy.md` for the full procedure — link, env vars, deploy, verify.

**Key points:** project name must be `cdm` (not auto-detected "CDM"); the anon key
must be `--type config`; the deployed site is behind Vercel Deployment Protection
(SSO login wall) on the `lunavs` team.

**Vercel link gotcha.** `vercel link` auto-detects the repo name as "CDM" and fails validation.
Always specify `--project cdm`. Verify the link succeeded with `vercel inspect` — a stale or
missing link means `vercel deploy` will either create a wrong-named project or fail silently.
After linking, the first `vercel deploy` may fail if env vars weren't added yet — add all four
Supabase vars BEFORE deploying, or the API routes throw "Missing Supabase env" at runtime.

## Before you build: confirm WHERE you are

A feature request arrives attached to a NAME, not a repo. Establish all five of these first — each
has already been wrong at least once, and each is cheap to check.

- **WHICH REPO.** `~/CDM` (GH `kingkymaru-glitch/CDM`, Supabase `ennvfuaimplxkzfdxfqd`) and
  `~/lunavsolution-code` (GH `kingkymaru-glitch/lunavsolution`) are SEPARATE apps with separate
  backends and separate version counters. A feature built in the wrong one is invisible to MARU and
  silently welds two products together — and a note written into the CDM Obsidian file citing
  `src/lib/app-version.ts` V0.20 was actually quoting lunavsolution's counter while CDM sat at
  V0.68. Run `git remote -v` and `cat lib/app-version.ts` before the first edit. If the answer is
  not the repo he named, SAY SO plainly rather than porting the work over silently.
- **NEVER REWRITE an Obsidian note from memory — read it, then PATCH it.** `write_file` OVERWRITES,
  and a 220-line `Projects/CDM/CDM.md` was destroyed down to a 25-line stub in one call because the
  file had only been read with offset/limit pagination (the tool warns `_warning: was last read
  with offset/limit — re-read the whole file before overwriting`; heed it). Recovery: the vault IS a
  git repo, so `git show <sha>:<path>` — but only the commits made in that session exist, so this
  works only if the file was committed before the clobber. Otherwise the content is gone. Use
  `patch` for note edits, `read_file` (whole file) before any `write_file`, and commit the vault
  BEFORE a risky rewrite.
- **SYNCED?** `git rev-parse HEAD` vs `git rev-parse origin/main`
  (`git rev-list --left-right --count origin/main...HEAD`). Ahead is normal; behind means you are
  about to build on a stale base.
- **IS THE TREE CLEAN?** `git status --porcelain`. **Never start a new feature on top of uncommitted
  work.** A whole unfinished arc was sitting there untracked (the `/collab` + `/review` surface).
  Get a decision before touching it: commit it as its own version, stash it (`git stash -u`), or
  drop it. Two features in one dirty tree destroys the rollback point AND the ability to bisect
  which change broke what — and it compiles fine, so nothing warns you.
- **IS THE RELEASE RECORD CURRENT?** Compare `git tag -l | sort -V | tail -1` against
  `lib/app-version.ts`, plus `gh release list`. Code at V0.68 with releases stopping at V0.53 means
  fifteen shipped versions have no tag and no release — exactly the rot the milestone rule exists to
  prevent, and invisible unless you look.
- **WHAT IS ACTUALLY LIVE?** `vercel ls` (the CLI is already authenticated). The deployed build is
  NOT the local tree — production was ~20h old while the tree carried newer uncommitted work.
  Whenever he asks "what's the status", report the live version and the local version separately.
  Map a deployment to its commit with
  `vercel api "/v6/deployments?limit=3&projectId=<id>"` → `meta.githubCommitSha` — that is how you
  prove a specific version is deployed rather than assuming the newest build is yours.
  A LOCAL BUILD PASSING IS NOT EVIDENCE A DEPLOYED ROUTE WORKS. See "Verify hosted-only behaviour
  against the DEPLOYMENT" below — a hosted-only branch never executes on the dev machine.
- **RECON IN A BOX, THEN STOP.** "Look at <external app> and tell me what we can adopt" is a
  BOUNDED reconnaissance, not an open dig. Read the module/router inventory ONCE, batch the greps,
  and stop the moment you can answer. Re-issuing a command whose output you already have produces
  nothing new and reads to MARU as being stuck — he will interrupt with "why are u looping". If a
  lookup feels like it needs a sixth pass, the answer is already in hand: stop reading and write
  the comparison.

### Terrain: shading and 3D ground from the site's own DEM

Both use the Copernicus DEM already cached for the analysis plugins. **No Cesium ION
token, no third party** — which matters because the ION requirement is what had made the
Terrain switch a DEAD CONTROL that was eventually deleted from the interface entirely,
leaving `overlays.terrain` as an orphan key. It is back and it works.

**Terrain Shading** (`/api/terrain-shading` + `/image`) — a hillshade picture of the
ground, drawn over the imagery in plan view.

**3D Terrain** (`/api/terrain` + `/tiles`) — Cesium gets real hills via
`CustomHeightmapTerrainProvider`.

#### The heightmap export, and why it exists

Cesium asks for HUNDREDS of terrain tiles while you pan, and **Node cannot read a
GeoTIFF** (no GDAL). Shelling out to Python per tile is hopeless. So the DEM window is
converted ONCE by `scripts/build_terrain.py` into:

- `heights.f32` — raw little-endian float32, **row-major, NORTH-FIRST**
- `terrain.json` — bounds, size, row order, elevation range

The tile route loads that into memory ONCE (module-scope `Map`, ~1.7 MB per site) and
samples it bilinearly. Row order is north-first, matching both the export and what
Cesium expects for heightmap terrain, so **nothing is flipped anywhere in the path**.

#### Verify row order with an A/B, never by eye

A flipped grid still looks like terrain — the hills are just in the wrong places, and
nothing about the picture reveals it. The only convincing test compares the export
against the DEM BOTH ways and shows which ordering matches:

```
mean |difference| treating export as NORTH-first :  0.00 m
mean |difference| treating export as SOUTH-first : 42.02 m
```

A nearest-neighbour comparison against exact DEM reads always disagrees by a few metres
on a slope, so a tight tolerance proves nothing — use the A/B, which has no tolerance.

#### Terrain tiles: clamp in, no-data out

- **Tiles outside the export return `undefined`** (route sends 204) so Cesium stays on
the ellipsoid rather than inventing ground we never measured. The export covers the site
plus **10 km**.
- **Inside the export, sampling CLAMPS at the edges.** Without the clamp a tile at the
boundary interpolates against a hard zero and cuts a cliff at the edge of the data.
- **Bound `w`/`h`.** The sample loop is unbounded work driven by a query string; a
crafted request would ask for an arbitrarily large array. Clamped to 256.
- **Validate the key as `^[a-f0-9]{16}$` before it touches a filesystem path.** The cache
dir is well known, so this check is the only thing between a crafted URL and any file on
the machine. Combine with `path.join` on a validated key — never on raw input.

#### Hillshade: use the dot product, not the aspect/zenith formula

The classic `sin(alt)cos(slope) + cos(alt)sin(slope)cos(az - aspect)` form carries a chain
of sign conventions (is `dz/dy` northward or southward? how is raster azimuth measured?)
and getting ANY of them backwards makes a slope facing the light render DARKER than flat —
which looks plausible enough to ship. This bug happened here.

Use instead:

```
normal = (-dz_dx, -dz_dy, 1) / sqrt(dz_dx² + dz_dy² + 1)
light  = (sin(az)cos(alt), cos(az)cos(alt), sin(alt))
illum  = normal · light        # one sign, provable against a tilted plane
```

Negate the row gradient (`dz_dy = -dz_drow`) because **row 0 is the NORTH edge** in a
north-up raster. Lit from the north-west at 45° — the cartographic standard, deliberately
NOT the real sun position (that is what the shadow plugin is for; a hillshade lit by a
real low sun is unreadable and changes meaning with the clock).

Verify with a synthetic rig — flat / slope into the light / slope away — because real
terrain gives you nothing to compare against. Expected: `40 + sin(45°)*205 = 185` for
flat ground.

#### Writing a PNG without adding a dependency

A greyscale hillshade is a trivial PNG: signature + IHDR + IDAT (zlib of scanlines, each
prefixed with filter byte 0) + IEND. Keeping it in the standard library avoids adding
Pillow to the managed runtime, which would change the runtime contract and force every
existing venv to be rebuilt.

## A guard in the UI is not a guard in the system

**Serverless cannot run a plugin** — no Python, no persistent filesystem, no terrain cache. So
the app only QUEUES and a local one-shot worker fulfils it; on Vercel `spawnWorkerOnce()` returns
early by design. Three separate failures came out of that one fact, and each looked fixed while it
was not:

1. **The panel looked ready.** On a hosted build it accepted a Run that nothing would ever
   fulfil — no error, no timeout, a spinner that never resolves. A silent failure is worse than a
   refusal. Fixed by reporting `execution: "local" | "hosted"` from `/api/analysis-runtime` and
   disabling the button with the reason above it.
2. **The hosted flag was set AFTER the work it was meant to skip.** The route shelled out to
   `scripts/analysis_cli.mjs` for its status, then added the hosted flag to the result. On Vercel
   `scripts/*.mjs` is NOT bundled into the function, so the spawn threw `ERR_MODULE_NOT_FOUND`
   first and the route returned a module-resolution stack trace — the same silent-queue problem
   wearing an error message. **Put the hosted branch FIRST, before any spawn.** Nothing should be
   probed that cannot exist.
3. **The UI refused; the API did not.** `POST /api/simulation` still accepted a run on the hosted
   build. Two POSTs to the live endpoint each created a row that sat at `QUEUED` with no error and
   nothing to execute it — found only by counting rows before and after. **Every route that starts
   work must refuse for itself.** GET stays open on purpose (runs and presets are SHARED, so a
   result computed locally correctly appears on the hosted build).

### Verify hosted-only behaviour against the DEPLOYMENT, never locally

A hosted-only branch cannot be exercised on the dev machine — locally `process.env.VERCEL` is
unset, so the hosted path never runs and a local build passing proves nothing about production.

- `vercel curl <path>` reaches a deployment behind Vercel Deployment Protection (it mints a
  bypass token using the authenticated CLI session). Plain `curl` gets a 302 to the SSO wall.
- Its telemetry line can swallow the response body — pipe through `grep -o '{.*}'` and check the
  JSON, or redirect and read the file. **A swallowed body is how a stray row gets missed.**
- For a "does this create something it shouldn't" check, count before and after. A response you
  failed to read is not evidence that nothing happened.
- **Clean up any rows a deployment test creates**, and re-count to prove you did. Test data in a
  compliance project is worse than no test. Delete by the FULL uuid — a truncated id gives
  `invalid input syntax for type uuid`.

### Hosted vs local is not new — SURROUNDINGS has always worked this way

Blender cannot run serverless either, so `POST /api/surroundings` skips the spawn on Vercel for
 exactly the same reason. What was new in V0.70-73 is that the SIMULATION feature SAID so instead
 of letting the user discover it by watching a job that never completes. Apply the same
 `execution: local | hosted` reporting to any future feature that needs a local process.

### The polling worker pattern — how it actually works

The live Vercel app QUEUES jobs; a local worker on MARU's Mac picks them up. **This is the
 primary solution** — not the bridge/tunnel. Free quick tunnels (Cloudflare `trycloudflare.com`,
 `loca.lt`) are rate-limited and return 502s under load, so the polling worker pattern is what
 actually ships.

**Combined launcher + menu bar indicator:**
- `~/Desktop/CDM Worker.command` — double-click to start BOTH workers and launch the indicator:
  ```bash
  pkill -f "surroundings_worker.mjs" 2>/dev/null
  pkill -f "simulation_worker.mjs" 2>/dev/null
  nohup node scripts/surroundings_worker.mjs > bridge/worker.log 2>&1 &
  nohup node scripts/simulation_worker.mjs >> bridge/worker.log 2>&1 &
  open "$HOME/Desktop/CDM Worker.app"
  ```
- `~/Desktop/CDM Worker.app` — menu bar indicator (Swift `.app` bundle, compiled from
  `~/CDM/bridge/indicator.swift`). Polls every 5s via `pgrep` to detect worker state:
  - 🟢 CDM = both workers running
  - 🟡 CDM = only one running
  - 🔴 CDM = both stopped — click `CDM Worker.command` to restart
  - Menu shows: status, "Surroundings: 🟢/🔴", "Simulation: 🟢/🔴", "Open CDM…", "Quit"
- **Both workers poll Supabase every 5s** for QUEUED jobs, claim them atomically, run the heavy
  pipeline (Blender/osmium for Surroundings, Python/DEM for Simulation), upload results, flip to
  READY. The web UI polls every 5s and auto-refreshes.
- **Stale job reclaim:** workers reclaim jobs stuck >10 min (surroundings) or >20 min (simulation)
  so a closed laptop can't strand a job on BUILDING/RUNNING forever.

**MARU's rule: end users NEVER run terminal commands.** The app triggers backend jobs itself.
 The worker is an internal implementation detail — MARU starts it with a double-click, not a
 terminal command. Don't tell him to "run `npm run surroundings:worker`".

### Hosted routes must QUEUE, not refuse

On the live Vercel deployment, `POST /api/surroundings` and `POST /api/simulation` must **QUEUE**
 the job (insert a row with status=QUEUED) — the local worker picks it up. They must NOT refuse
 with 409.

- `app/api/surroundings/route.ts` — `spawnWorkerOnce()` returns early on Vercel (no local Blender),
  but the QUEUE insert still happens. ✅ Correct.
- `app/api/simulation/route.ts` — **had a hard 409 block that refused to QUEUE on hosted builds.**
  Removed. Now it inserts the QUEUED row regardless of host; the local worker claims it.
- **UI must reflect this:** the SimulationPanel button now says "Queue Flood analysis (runs on your
  Mac)" on hosted builds instead of being disabled with "Run an analysis on the installed app".
- **The button has TWO independent gates — both must be opened.** The API 409 in `route.ts` is the first gate; the second is `SimulationPanel.tsx`'s `blocked` state, which was `const blocked = hosted || (needsTerrain && !terrainReady) || !runtimeReady`. That line kept the button disabled on the live web even after the API block was removed, because the Vercel host reports `terrainReady: false` and `runtimeReady: false` (no local DEM cache or Python). The fix: `const blocked = !hosted && ((needsTerrain && !terrainReady) || !runtimeReady)` — hosted builds never block on server-side readiness, since the Mac worker handles all of that when it picks up the job. After changing the API, ALWAYS check the panel's `disabled={...}` prop for a second gate before declaring the button live. The same two-gate pattern applies to ANY feature that's unblocked for hosted builds: first the API route, then the UI panel.
- GET routes stay open on hosted builds — results computed locally appear on the live web.

### Bridge server (fallback, not primary)

When a tunnel IS available (VPS SSH or named Cloudflare), the bridge server can trigger builds
 directly without waiting for the poll:

- **Bridge code:** `~/CDM/bridge/server.mjs` — listens on `127.0.0.1:8790` (port 8787 occupied
  by LM Studio `cursor-hy3-proxy`), exposes `POST /spawn` (kicks the worker) and `GET /health`.
  Fires macOS notifications via `osascript` on build start/success/failure. Auto-spawns
  `surroundings_worker.mjs --once` and drains the queue. Optional `BRIDGE_SECRET` bearer-token auth.
- See `references/local-bridge-tunnel.md` for the tunnel evaluation (free tunnels fail; VPS/named
  Cloudflare work).

### The live web CANNOT run local jobs — MARU discovered this the hard way

**When MARU accesses the live Vercel deployment and clicks "Build" on Surroundings (or "Run" on
Simulation), the job enters QUEUED and hangs FOREVER.** This is not a bug — `spawnWorkerOnce()`
returns immediately when `process.env.VERCEL` is set (line 52 of `app/api/surroundings/route.ts`),
and the simulation worker has the same guard. There is no tunnel, no bridge, and no cloud fallback.

The live web is a VIEW-ONLY + DATA-ENTRY shell: it renders the globe, reads/writes Supabase rows,
accepts GLB uploads, manages risk nodes — but it CANNOT trigger Blender, osmium, or the Python
plugins. Those require a LOCAL Mac running the polling worker (`npm run surroundings:worker` or
`npm run sim:worker`) to claim queued jobs.

**If MARU asks "why is it stuck on QUEUED from the live app?" — the answer is always the same:**
the local worker is not running, OR the live deployment can never reach it. The fix is to either
run the worker on the Mac while the Mac is awake, or move the pipeline to a cloud worker.

Do not let MARU test Surroundings/Simulation features from the live web expecting them to work.
The live URL is for viewing results already built locally, not for building new ones.

## Ship loop (every change)

1. Edit; `npx tsc --noEmit` must be clean.
   **To test a PURE module (no React/DOM) BEFORE wiring it into a UI**, compile it standalone and
   drive it from node — the editor's per-file `tsc` is skipped on this project (path aliases),
   so run it yourself: `npx tsc lib/<mod>.ts --outDir /tmp/tt --target es2020 --module commonjs
   --skipLibCheck`, then `node -e 'const m = require("/tmp/tt/<mod>.js"); ...'`. Do this for every
   maths/parse module and write the fixtures as assertions with numeric tolerances. It caught a
   real bug (a unit suffix digit parsed as part of the number) before any UI existed to hide it,
   and for geometry it is the ONLY verification available — you cannot see the globe.
- **Verify every numeric feature against a rig with a hand-computable answer, or an A/B between
  two hypotheses — never against real data.** Real terrain/data gives you NOTHING to compare
  against, so a "working" number is indistinguishable from a plausible wrong one. This principle
  has now caught six real bugs across as many features: the row-order A/B (export north-first =
  0.00 m vs south-first = 42.02 m), the hillshade rig (flat ground must read `40+sin(45°)*205`),
  the shadow wall rig (a 100 m wall under a 45° sun must cast a 100 m shadow), the equinox oracle
  (rise due east, set due west), the two-route area check (`cells×cell_area` vs dissolved geometry
  area), and the two-route terrain sanity (tile range vs DEM range). Reach for the rig FIRST,
  before wiring anything into the UI; it is the only verification available when you cannot see
  the globe.
2. **STOP THE DEV SERVER FIRST** (`pkill -f "next dev"`), *then* `npx next build` — lint errors
   fail the build (unused vars, `any`). Dev and build share the SAME `.next/` directory, so
   building while `next dev` is live clobbers the dev server's route manifest: **`/` begins
   returning Next's own 404 page while `/api/*` still answers 200.** That signature (app root
   dead, APIs healthy) reads like a routing or middleware bug and is neither — it is a corrupted
   build dir. Diagnose by curling `/` and grepping the body for `could not be found`; fix with
   `pkill -f "next dev"` → `rm -rf .next` → `npm run dev`. Corollary: after ANY `next build`,
   treat the running dev server as stale and restart it before telling MARU to test.
3. Bump `lib/app-version.ts`.
4. Commit + `git push origin HEAD`.
5. Restart `npm run dev` (background) and tell MARU to test.
6. If new tables/columns/buckets: **probe first** (`scripts/probe-schema.sh`), MERGE the pending
   statements into the ONE Desktop file, DELETE anything it
   supersedes, hand MARU that single path + the click-by-click steps, then verify with real writes
   and clean up. See "Schema changes: ONE Desktop file" below.

MARU tests the WebGL himself — you cannot see the globe. Ask for the exact
console error text when something fails.

## Debugging a client-side render/display bug you cannot see

You have no eyes on the globe (no headless Chrome on MARU's Mac; `browser_exec` can't reach
localhost from a cloud backend). When MARU reports a visual failure, do NOT keep asking him to
read things — put the evidence somewhere you can read it yourself.

1. **Verify the DATA first, exhaustively, before touching rendering.** Every placed row,
   model reference, and file URL must be confirmed (reachable = `curl` returns 200 AND
   `access-control-allow-origin: *` — curl alone does not prove the browser can load it; and
   validate each GLB is parseable glTF by reading its JSON chunk's `asset`/`meshes`). When the
   data is provably correct, the bug is client-side.
2. **Split "context short" from "won't draw" with an ON-SCREEN diagnostic chip.** The common
   trap is conflating "the record is missing" with "the render fails". Render a small
   bottom-left chip `foo N · models N · rendered N` inside the viewer's effect (a `useState`
   updated by the effect). If `rendered < foo`, entities aren't being created (context/fetch
   bug); if `rendered === foo` but nothing shows, the GLB isn't drawing (load/CORS) — the chip
   is the fork. The chip is also OCR-able (see next point), so you can read it yourself.
3. **Add `[layer:server]` and `[layer:client]` console logging** to the fetch route (projectId
   resolved + rows returned) and the context (`activeProjectId` sent + rows received). When the
   chip count < API count, these two lines tell you whether the browser sent the wrong project id
   or the API returned partial data — without a single round of user report.
4. **OCR a screenshot when `vision_analyze` 404s.** MARU pastes macOS screencapture paths. When
   vision is down, extract the on-screen text with the Swift Vision framework (`swift ocr.swift`;
   `VNRecognizeTextRequest`, `.accurate`, print `x`/`ybot` per line where `ybot` is distance from
   the bottom — a bottom-left chip has small `ybot`, a header has large `ybot`). Copy the file to
   a flat path first (screencapture paths live in a TCC dir with spaces). This is how to read the
   diagnostic chip yourself without vision and without asking MARU. No tesseract needed —
   a ~30-line Swift script using `VNRecognizeTextRequest` is all it takes (`.recognitionLevel =
   `.accurate`, `usesLanguageCorrection = false` so file names and counts are not "corrected",
   print `topCandidates(1).first.string` plus `boundingBox.origin` per observation).
   **The same trick reads a SCANNED PDF that has no text layer** — which is what a real title,
   contract or stamped form usually is. Detect it first: the file contains `/Image` but no
   `/Font`, and `read_file` returns nothing useful. Render each page with PDFKit and OCR that:
   `PDFDocument(url:)` → `page.thumbnail(of:for:)` → `VNImageRequestHandler(cgImage:)`, one pass
   per page, printing the page number with each block. **Render BIG (~2400 px page width)** —
   small digits on a dense sheet vanish when you downscale. Treat OCR as a way to LEARN what the
   document contains; have the user TYPE the values that go into the app. OCR on a dense
   cadastral sheet WILL misread (a dropped decimal point turns `108.96` into `108964`), and an
   auto-filled survey number is a silent wrong answer.
5. **A "displaced / missing" placed model is usually the CAMERA, not the model.** The globe
   flies to `projects.location_lat/lng` on open. If that still carries a stale default (e.g. the
   original KL default) while the work — surroundings import centre, placed buildings, nodes,
   plots — is clustered elsewhere (the real site), everything reads "missing" or "moved".
   Compare the project site vs the surroundings centre vs the placement cluster; if they diverge
   by km, PATCH the project location to the work cluster (one safe field) so the camera lands on
   the actual site. A placed model renders exactly at its stored coords — check the anchor
   reference before hunting a geometry/offset bug.
6. **Give every placed building an always-on anchor point + label** (a `point` graphics on the
   entity, independent of the GLB). The location is then visible even if the model fails to
   draw, which converts "is it there?" into "the dot is there but the shape isn't" — isolating
   GLB rendering from entity creation.

## Recording milestones (releases + docs)

MARU asks for this as **"record all milestone and success to GH and obsidian"**. Hit all four
surfaces — a milestone that exists only in git history is not recorded. Do this whenever an arc
of work lands, not only when he asks.

1. **Tag + GitHub Release per version.** `gh release create <tag> --target <sha>` creates BOTH the
   tag and the release, so there is no separate `git tag` / `git push --tags` step. One release
   per shipped version (V0.xx), title = version + one-line summary.
   **If you DO push a tag on its own, it has NO release** — a tag that looks shipped with no notes
   and no body. Check `gh release list` against `git tag -l` before declaring the record complete,
   and backfill the gap with `gh release create <tag>`. Tagging and releasing are two surfaces and
   only one of them happens automatically.
2. **`CHANGELOG.md` in the repo** — grouped by MILESTONE, not by commit. Record the why and the
   measured evidence, not a feature list; fold related versions into one entry when they formed
   one arc. Also park the standing architectural decisions there (Cesium from CDN, Supabase
   Storage over R2, Blender cannot run serverless, desktop direction).
3. **`SUCCESSLOG.md` in the repo** — problem → fix → verified results, newest first. This mirrors
   the convention MARU's sibling repos (R-Tessera, LunaV) already use, so keep the shape.
4. **Obsidian** — the project note (`Projects/CDM/CDM.md`), `HermesProgress.md` (PREPEND a dated
   entry; that file is newest-first), and the `VAULT MAP.md` index line.

**The vault index line is the one that silently rots.** It still advertised V0.01 long after the
app was at V0.53. Grep the index for a version string in the same pass and fix it, and correct
any "Still open" list in the project note — items shipped earlier often linger there as pending.

**Resolve SHAs from git — never hand-copy them.** A dropped character produces a MISLEADING
`HTTP 422 ... tag_name is not a valid tag / Release.target_commitish is invalid`, which blames the
tag when the real fault is the commit. Never "fix" it by retrying a different tag name. Use
`scripts/publish-milestone-releases.sh` — it resolves each hash from git and validates it with
`git cat-file -e` before calling `gh`, and skips releases that already exist so a re-run is safe.

**Scripted regex edits over code or generated text are unreliable — verify structure after.** A
multi-line regex that removes a block can eat the adjacent structural line: a cleanup regex once
swallowed the `return (` that opened a component's JSX (→ `TS1381: Unexpected token`) and, in a
separate case, stripped the wrong trailing backslashes from a batch of `gh` calls and silently
corrupted their argument lists. Rules:
- Prefer the `patch` tool with EXACT surrounding context for source edits; it fails loudly on an
  ambiguous match instead of mangling neighbours. **When a patch's `old_string` spans a structural
  boundary (end of one function/block, start of the next), the replacement must re-include EVERY
  line the anchor covered** — using a closing brace as the anchor once removed the whole next
  function's body, and a patch that left a file momentarily collapsed a block, each costing a
  repair cycle. Re-read the region after any patch that removes lines.
- After any scripted regex edit, run `npx tsc --noEmit` + `npx next build` AND eyeball the edited
  region — the build catches the breakage, but the point is to confirm no collateral edit.
- **Never leave a JSX file momentarily invalid between two edits.** This has burned twice: a
  fragment opened in one patch and closed in the next (`RiskZonePanel`), and a ternary wrapped by a
  patch that omitted its opening paren (`CommentsTab`). Each left the file unparseable for a few
  seconds, `next dev` logged the error, and **MARU's background-process notification captured that
  transient state and he reported a bug that no longer existed** — costing a whole round trip of
  "it's broken" → "that was stale". When adding a wrapper element or parens, write the WHOLE file
  in one operation, or make the FIRST edit the one that leaves the file valid. Kill the dev server
  BEFORE building (see the Ship loop) so it is not capturing your intermediate edits at all.
  **When a background-process notification DOES report an error, verify the current state before
  reacting:** confirm the process is still alive, reproduce against the file as it is now
  (`tsc --noEmit`, `curl /`), and report what you checked. It has three times been a replay of a
  killed process's last captured output rather than a live fault, and each false alarm cost a full
  round trip of "it's broken" → "that was stale".

  **Where these replays come from, so they are recognised instantly:** starting the dev server with
  `background=true, notify=true` means that when you `pkill` it, the process EXITS and its
  completion notification carries the ENTIRE captured stdout — every request it served. That replay
  lands after you have moved on, looks exactly like a live fault report, and is pure noise when the
  lines are all `200`/`201`. Prevention: for a dev server you intend to kill, either omit `notify`
  or redirect its output to a file and read it deliberately. And read the STATUS CODES first — a
  replay of all-2xx is healthy output, not a bug report.
- For repeated multi-field data (release batches), do not build one command with `\` line
  continuations; pass a delimited file and read it with `while IFS='|' read -r tag commit title body`.
