# Dimension (Measurement) Tool — LunaV inspection-record design

## Product principle (durable, founder-directed 2026-08-20)
The 3D model is a **representation** of the site item, NOT a survey-accurate
source (unlike a LiDAR point cloud). Therefore a "dimension" is an **inspector
record of what was measured at site**, not a length computed off the mesh.

Consequences baked into the tool:
- The on-model line is a **visual indicator only** — it shows WHERE a measurement
  was noted; it does NOT carry a computed value.
- Never display a computed length from `a.distanceTo(b)` as if it were real.
  The viewer force-fits every model to a 25-unit footprint
  (`scale = 25 / max(size)` in Viewer3D), so world-space distance is meaningless
  in real meters until `feat/model-scale` calibration is merged.
- The inspector fills in: **value** (number), **unit** (m / cm / mm / ft / in /
  custom free-text), and a **free-text note** describing the measured item /
  observation. All three persist to `proxies.dimension_value | dimension_unit |
  dimension_note`.

## Where it lives
- Button: left **Models** panel → **Spatial Proxy Toolbox** header → "↔ Dimension"
  (grid position after ◼ Cube / ▭ Plane). Only shown when the model panel is open
  AND not `readOnly`. Acts on the active model (`activeModelId`).
- Add: `addDimension()` in `ProjectWorkspace.tsx` — inserts a `proxies` row
  `shape:'dimension'` with sentinel endpoints `{x:-4,y:0,z:0}` → `{x:4,y:0,z:0}`.
- Render + interaction: `Viewer3D.tsx` dimension proxy branch (`shape==='dimension'`).
- Record modal: `dimEditor` state in `ProjectWorkspace.tsx` → "Record Dimension"
  popup with value / unit / note.

## Interaction
- New dimension snaps onto the model bounding box (center, ~40% width) via the
  sentinel-endpoint override in the Viewer3D render (so it appears ON geometry,
  not at world origin).
- Two teal endpoint spheres (`endpointHandlesRef`) are draggable: raycast against
  `modelGroupRef` and snap to the surface hit; fallback to a depth plane if the ray
  misses. Dragging sets `cursor:'grabbing'` and disables OrbitControls mid-drag.
- Click the center CSS2D label → opens the record modal (calls `onDimensionChange`
  with `{value,unit,note}`). Label shows `value unit` or "click to record dimension".

## Center-label → modal (not inline input)
The original build used an inline `<input>` inside the CSS2D label. Replaced with a
parent popup because the unit selector + note need room. The label's `click` handler
stops propagation and calls `onDimensionChange(id, {value,unit,note})` → parent opens
`dimEditor`. Don't revert to inline input without re-adding the unit/note UI.

## Persisting endpoint drags
`handleDragMove` raycasts the model, snaps, and calls `onDimensionDrag(id, end, pos)`
→ parent writes `point_a`/`point_b` to Supabase on every move (parent setState +
re-sync). Fine for a few proxies; don't extend to hundreds without throttling.

## DB
Columns: `dimension_value text`, `dimension_unit text`, `dimension_note text`
(NULLable). Apply via idempotent SQL (see live-migration-gate). RLS: existing
proxies policies already cover these — no policy change needed.

## Pitfalls
- Do NOT reintroduce a computed-length label ("12.34 u") — it misleads inspectors
  into thinking the number is survey-accurate.
- The model force-fit to 25 units means the on-screen line length is arbitrary; only
  the inspector's typed `value` + `unit` is meaningful.
- Drag handlers persist on every move → many re-syncs. Acceptable at low proxy counts.
