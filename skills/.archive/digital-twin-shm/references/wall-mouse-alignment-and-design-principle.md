# MARU "the Wall" — mouse model alignment + design principle

## Feature: Digital Twin Studio mouse alignment
"the Wall" = a per-station surface (Digital Twin Studio) hosting the client's
3D model (generic glTF/GLB — NOT a vendor-specific format) + optional Lidar
(Cesium 3D Tiles), with named slots and socket pins. After uploading, the user
aligns the model on the globe with the mouse:

- **Studio form** (vendor-neutral): Model URL (hint glTF/GLB or Cesium 3D
  Tiles, "export from any 3D tool"), Lidar/point-cloud URL, format dropdown,
  lat/lon origin, slots. All fields have `id` + `<label htmlFor>` (a11y).
- **"Adjust on map"** button → opens a mouse editor: drag-move (lat/lon),
  drag-rotate (heading), wheel-scale, draggable TBM pin + "Snap base to TBM".
- **Numeric Scale (×) + Heading (°)** fields stay for the survey-grade path.
- Both mouse + numeric paths write the SAME stored transform (model.scale,
  model.rotationDeg, origin.lat/lon, tbm.{lat,lon}).

State: EdgeDataContext holds `twinWalls{}` (id→validated wall), `twinWallId`
(active), `showTwinWall`, `editingWallId`, `patchTwinWall(id,patch)`,
`startTwinEdit(id)`, `stopTwinEdit()`, `activeTwinWall`.
Components: DigitalTwinWall.jsx (render), TwinWallStudio.jsx (form),
TwinWallEditorOverlay.jsx (Cesium mouse events), TwinWallEditorHUD.jsx (DOM
control bar), twinRegistry.js (validateWall — PRESERVES scale/rotationDeg/tbm).

## DESIGN PRINCIPLE (user-stated, 2026-07-19)
MARU development prioritises **RAPID DEPLOYMENT + ADOPTABILITY**, NOT replacing
surveyor accuracy. The platform is a shelf that holds ANY level of modelling
detail — a survey-grade LiDAR+GNSS model OR a rough photogrammetry block —
per the user's need. The model's accuracy is entirely the user's call; MARU
just gets it published as a DT fast. Build for quick publish, not certification.
Concretely: the mouse editor is the "fast draft align" path; numeric
Scale/Heading are the "I have real survey numbers" path; both write the same
transform so a draft can be tightened later without rebuild.

## PITFALLS
- Context fields used in JSX must be destructured from `useEdgeData()` in the
  consuming component or the tree crashes to a black screen (ReferenceError).
- Gate the wall's own `<Model>` render on `editingWallId !== wall.id` while
  the editor is open, or the two models z-fight.
