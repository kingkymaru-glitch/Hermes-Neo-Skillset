---
name: cesium-resium-rendering
description: Cesium/Resium render traps — lines, entities, and externally-authored glTF models. The #1 trap: multiple Polylines per Entity silently collapses multi-branch geometry. Also covers entity-build throws that freeze the whole globe, the viewer-init deps:[] viewer-rebuild trap, and glTF axis / bounding-sphere misplacement for Blender/OSM imports.
---

# Cesium / Resium line rendering

## The #1 pitfall (cost this session 20+ turns)
**Cesium/Resium only honors ONE `<PolylineGraphics>` per `<Entity>`.** Putting multiple
`<PolylineGraphics>` as siblings inside a single `<Entity>` does NOT render N lines — it
silently collapses them (last wins / merged in sequence).

Symptoms it produces:
- A multi-branch cable (MultiLineString with >1 sub-line) shows as **one truncated line**
  instead of its full branching network.
- **Lines appear where they shouldn't** — the merged polyline connects branch endpoints in
  sequence, drawing straight segments across land/ocean the real route never follows.
- Looks like "fewer cables than the source" or "cables in wrong places."

FIX: render **one `<Entity>` per sub-line**, each with its own `<PolylineGraphics>`. For a
feature with N branches (N coordinate arrays), emit N `<Entity>` elements. Resolve sub-line
clicks back to the parent cable via a deterministic id (see React keys below).

## Coordinate order (second most common bug)
GeoJSON coordinates are `[lon, lat]`. Cesium uses `Cartesian3.fromDegrees(lon, lat, height)`.
Pass `[lon, lat]` through **verbatim** — never swap. A swap mirrors every feature across the
diagonal (a transatlantic cable renders in the Pacific; a Virginia→Spain cable lands near
Chile). If source data is already [lon,lat], do nothing to it.

## Height / clamping
- `clampToGround` over oceans with no terrain tiles misplaces lines on the 3D globe.
- For a clean, source-accurate look, render at **height 0**: `fromDegrees(lon, lat)` — no
  lift, no clamp. (A 50 km lift is cosmetic and not needed for correctness.)

## Entity-construction crashes that kill the WHOLE render (Next.js/CDN Cesium)
A throw while building ANY entity aborts the Cesium render loop — the entire globe freezes,
so "one entity vanished" is usually "every entity vanished" (the user sees nodes/globe
'disappear'). Three recurring causes and their fixes:
1. **Never attach an `outline`/`ellipse` to a ground-CLAMPED entity.** A node entity that also
   carries a `point` with `heightReference: CLAMP_TO_GROUND` cannot take an `ellipse` with
   `outline` — Cesium throws "normalized result is not a number" and kills the render.
   FIX: draw the radius circle as a **separate entity** on the ellipsoid surface (no clamp),
   keyed by the node id, and wrap each entity build in try/catch so one bad row can't take
   down the globe.
2. **Thick circles: `ellipse.outlineWidth` is silently IGNORED** on most WebGL builds
   (stays ~1 px no matter the value). To get a visibly thick ring, sample the circle into a
   closed ring of positions and draw it as a **`polyline`** (real width). ~96–128 segments is
   smooth; compute degree deltas from metres via `mPerLat=111320`, `mPerLon=111320*cos(lat)`.
3. **`Model.fromGltf` may be MISSING on the CDN global** (the `window.Cesium.Model` API is
   unreliable from a CDN build). Load a GLB as an **entity `model` graphics**
   (`viewer.entities.add({ position, model:{ uri } })`) instead of a scene primitive — it
   wires up reliably and moves/deletes with the entity.
4. **`model.orientation` is SILENTLY IGNORED when the model graphics also carries a
   `heightReference`.** Rotating a placed GLB via
   `model: { orientation: Transforms.headingPitchRollQuaternion(...), heightReference: CLAMP_TO_GROUND }`
   appears to do nothing — the slider moves, the model never turns, and no error is thrown.
   FIX: put `orientation` on the **Entity** (sibling of `position`), not inside the `model`
   graphics, and drop `heightReference` from the model:
   `viewer.entities.add({ position, orientation, model: { uri, scale } })`.
   Symptom that identifies this one: "the rotate slider does nothing" with a clean console.
5. **A field-name mismatch between layers becomes NaN geometry, which freezes the WHOLE
   globe.** An entity builder that reads `plot.center_lon` while the API/context returns
   camelCase (`plot.centerLon`) computes `Number(undefined)` = `NaN` for every vertex;
   Cesium then throws `DeveloperError: normalized result is not a number` from the polygon
   worker and **stops rendering entirely** — the user reports "my node disappeared", but
   every entity died. This is the same failure signature as pitfall 4's guard, with a
   different root cause. RULE: pick ONE casing convention and normalise at exactly ONE
   boundary — have the API route map snake_case DB columns → camelCase wire shape in a
   single `normalizeX(row)` helper, and never let a component read the other convention.
   When adding a table, grep the renderer for the snake_case column names; a hit means
   the boundary was bypassed.

## The viewer-init effect MUST have `deps: []` and read callbacks from a ref bag
If the Cesium `useEffect` that creates the `Viewer` lists any callback in its dependency
array (e.g. `addPlotAt`, `addBuildingAt`, `selectPin`), then any change to that callback's
identity — picking a different model, editing a plot draft, selecting a node — **destroys and
rebuilds the whole viewer**: the camera resets, every placed entity drops, then reappears
when the effect re-runs. Symptom the user reports: "I picked a second building and my first
building vanished; the view jumped."

FIX: keep the viewer effect on `[]` and have the long-lived click handler call through a
stable ref that you repoint every render:
```js
const actionsRef = useRef({ placeX: () => {}, selectY: () => {} /* no-op defaults */ })
actionsRef.current = { placeX, selectY /* real callbacks, repointed each render */ }
// inside the [] viewer effect, click handler calls actionsRef.current.placeX(...)
```
Also gate entity-render effects on a `viewerReady` state flag set after the async viewer
initializes — otherwise they run before the viewer exists, silently bail, and only paint
after the next unrelated change.

## Debug a "something disappeared" report with a NaN/geometry guard
Before editing, add a cheap guard that skips any entity whose coordinates/radii are not
finite (`Number.isFinite`) — a single NaN vertex was the root cause of a full-render freeze.
This turns a hard crash into a skipped row and tells you where the bad data is.
ALSO wrap each entity build in try/catch and give each visual concern its OWN entity
(a node point+label on one entity, its radius ring on another keyed by the same id).
One throwing entity otherwise aborts the render loop and takes the entire globe down with
it, so "one thing vanished" almost always means "everything vanished".
ROOT-CAUSE CHECK before touching geometry: is the NaN coming from a **missing/renamed field**
(pitfall 5 above), not from bad source data? `Number(undefined)` is the most common source
of a NaN vertex and looks identical to corrupt input.

## Placing EXTERNALLY-authored glTF (Blender / OSM / photogrammetry) on the globe
A model authored outside Cesium does not land where you expect, and the failure looks like a
position or scale bug when it is neither.

**The axis trap.** Blender-authored glTF commonly exports **+X = east, +Z = south**, but Cesium's
loader calls `getAxisCorrectionMatrix(upAxis=Y, forwardAxis=Z)`, which composes
`Y_UP_TO_Z_UP × Z_UP_TO_X_UP` → **glTF +Z → East, glTF +X → North**. The model therefore lands
rotated ~90° about its placement point. Check the loaded glTF's actual axes before blaming
coordinates, then compensate with a heading (an OSM/blosm import needed `heading = 90°`).

**Why it hides:** an entity placed at a point and rotated about its OWN centre looks identical at
any heading when the model is small or near-symmetric — a single uploaded building never reveals
it. A large multi-building scan does. If a big georeferenced import looks "totally off" while
hand-placed models look right, suspect heading/axes, not position.

**Stray geometry wrecks the bounding sphere.** Source data that crosses your area of interest gets
returned whole (Overpass returns complete ways, not clipped ones), so a 1 km import can carry
features tens of km away — measured 36 km × 19 km extent with one mesh 17 km out. Cesium sizes and
frames a model from its **bounding sphere**, so the visible result is a wrongly scaled/shifted
model even though every coordinate is correct. Clip the geometry to the area before export
(`bmesh` for Blender: drop wholly-outside objects, trim straddling ones, small margin). Also drop
`minimumPixelSize` from a large context model — it fights a big bounding sphere.

**Prove the chain instead of guessing.** To test a coordinate/projection pipeline, place a marker
primitive at a KNOWN real-world coordinate using the SAME projection library the exporter uses, and
compare it to the exporter's own mesh for that feature. If they coincide (observed: within 0.11 m)
the projection, origin and axis mapping are all fine and the fault is elsewhere. Do this BEFORE
"fixing" coordinates.

**Ship a manual align escape hatch.** A perfect automatic georeference is fragile across sources,
so expose rotate / nudge-in-metres / scale on the placed model and persist those per import; then
bake the value the user settles on into the default.

## React keys
- `properties.id` is frequently **not unique** across features (duplicate ids → React key
  collisions → dropped routes). Use a genuinely unique field (e.g. `feature_id`) for Entity
  keys.
- When you split one cable into N sub-line Entities, encode the parent so click handlers can
  recover it: id = `cable-<feature_id>__<i>` (use `__`, NOT `-<i>`, because `feature_id`
  values like `kumul-...-0` already end in `-0` and a trailing `-N` strip would corrupt them).
  Strip deterministically: `id.split('__')[0]`.

## StrictMode
Cesium double-mounts under React.StrictMode and throws "object destroyed" / "this object was
destroyed". Remove `<React.StrictMode>` wrapper in main.jsx for Cesium/Resium apps.

## Color / visibility (user iterated here — real lesson)
The user equates "looks sparse/wrong" with a DATA bug. It is usually NOT. Order of fixes
tried this session (only the per-Entity polyline collapse was the real cause):
1. Light gray `#c8ccd0` on a bright OSM basemap → too faint, read as "missing." Bumped to
   OSIRIS blue `#1976D2`, then user said blue overpowered other map indicators. Final:
   **muted dark slate `#3a4a57`** — darker than light gray (less glare) but low-contrast
   against sea, so the web stays recessive vs earthquakes/volcanoes/weather.
2. 2D-vs-3D density: defaulting to SCENE2D flat did NOT fix perceived sparseness (data was
   already correct) — it was cosmetic. Do not chase projection as the cause.
3. Contrast/color tweaks are cosmetic, not root-cause. Verify geometry via the live viewer
   (above) BEFORE changing color. Rule from the user: cable web must not overpower other map
   indicators — keep it recessive (muted/dark, not bright).

## Verified debug technique (introspect the LIVE viewer)
When you can't trust what you see, don't guess — read the actual rendered geometry:
1. Temporarily expose the viewer in the ViewerBridge effect:
   `if (typeof window !== 'undefined') window.__viewer = viewer`
2. In the browser console:
   - `viewer.entities.values.filter(e => String(e.id).startsWith('cable-')).length` → count
   - `viewer.scene.mode` → 2 = SCENE2D (flat), 3 = SCENE3D (globe). Confirms projection.
   - For one entity: `e.polyline.positions.getValue(viewer.clock.currentTime)` → ECEF
     Cartesians. Convert to lon/lat in Node (see references/debug-ecs-verify.md) and compare
     to the source. This is how we PROVED MAREA rendered at exactly the source coords and that
     Kumul had collapsed to 1 polyline (the bug).
3. Remove the `window.__viewer` line before committing.

## Diagnostic triage ORDER (do these in sequence — don't jump to "geometry is wrong")
When the user says cables look wrong (sparse / in wrong places / missing branches), run this
order. Most of a 20-turn detour came from skipping to "fix the geometry" before ruling out the
cheap causes:
1. **Stale cache / stale deploy** — hard-refresh, and confirm the live build hash actually
   changed after your push (the Vercel webhook only fires for commits authored as the deploy
   identity). A previously-broken build (e.g. lat/lon swap) can stay cached in browser/edge.
2. **Projection** — confirm with `viewer.scene.mode` (2 = SCENE2D flat, 3 = SCENE3D globe). A
   3D globe foreshortens and reads as "sparser" than the source's flat map even when geometry
   is correct.
3. **Coordinate swap** — pick ONE known cable (e.g. MAREA Virginia→Spain) and verify its
   rendered endpoints match the source. A swap mirrors everything across the diagonal.
4. **Per-Entity polyline collapse** (the real bug above) — count sub-line Entities per cable:
   `viewer.entities.values.filter(e => String(e.id).startsWith('cable-kumul')).length`.
   Source Kumul has 14 sub-lines → expect 14 Entities. If you see 1, you've found the collapse.
   This distinguishes "collapsed" (still there, merged) from "missing" (not rendered at all).
Rule: verify with the live viewer BEFORE editing code. Editing on a guessed cause wastes turns.

## References
- `references/debug-ecs-verify.md` — ECEF→lon/lat Node snippet + the Kumul repro (14 sub-lines
  collapsed to 1 polyline before the fix, 14 entities after).
