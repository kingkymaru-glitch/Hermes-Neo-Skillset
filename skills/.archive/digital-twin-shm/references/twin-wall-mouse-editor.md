# The Wall — on-map mouse alignment editor (Cesium/Resium)

Let the user drag/rotate/scale a 3D model with the mouse and snap its base to a
Temporary Bench Mark (TBM). Built for MARU "the Wall" (DigitalTwinWall +
TwinWallEditorOverlay + TwinWallEditorHUD), but the Cesium technique is generic.

## Why
The Studio form only accepts typed lat/lon/scale/heading. Field engineers want
to grab the model and align it by eye, then fine-tune with numbers. TBM = a
known survey point; snapping the model base onto it makes the alignment exact
without the user doing coordinate math.

## Architecture (3 moving parts)
1. **Context edit-mode state** — `editingWallId` + `patchTwinWall(id, patchSlice)`
   in `EdgeDataContext`. The editor calls `patchTwinWall` on every drag delta so
   the store is the single source of truth and the wall re-renders live.
2. **`TwinWallEditorOverlay`** (inside `<Viewer>`, uses `useCesium()`) — the
   `ScreenSpaceEventHandler` that does the actual mouse work.
3. **`TwinWallEditorHUD`** (DOM overlay, not Cesium) — Move/Rotate/Scale mode
   buttons + live readout + "Snap base to TBM" + Done. Mode state lives HERE and
   is passed to the overlay as a `mode` prop.

## The Cesium primitives
- `viewer.scene.pick(x, y)` → returns the picked object; read `obj.id.id` to get
  the Entity `id` string you assigned. Use stable ids like
  `twin-tbm-<wallId>` / `twin-rot-<wallId>` so you know WHAT was grabbed.
- `viewer.camera.pickEllipsoid(x, y)` → **Cartesian3 on the WGS84 ellipsoid** (no
  terrain). Use this for the cursor ground position when dragging.
- `Cartesian3.fromCartesian3(c, Ellipsoid.WGS84)` + `.toString()` → `lon,lat,height`
  in degrees. Round to 6 dp before writing to the store (avoids jitter churn).

## Mode pattern (keeps drag predictable)
Drive the gesture off the HUD `mode`, not off which tiny handle was clicked:
- `mode === 'rotate'` → on LEFT_DOWN set `drag = ROTATE` immediately (ignore pick).
- `mode === 'scale'`  → on WHEEL over the picked model, adjust `model.scale`
  (clamp 0.01-20). Return on all other mouse actions.
- `mode === 'move'`   → on LEFT_DOWN, `pick()` decides: TBM pin → `drag = TBM`,
  else `drag = MOVE`.

Store drag kind in a `useRef` (not state) so the MOUSE_MOVE handler reads it
without re-binding. Reset to `NONE` on LEFT_UP.

## Rotation math (heading from model origin → cursor azimuth)
East-north-up convention. On MOUSE_MOVE in rotate mode:
```js
const dLon = CesiumMath.toRadians(cursor.lon - origin.lon)
const dLat = CesiumMath.toRadians(cursor.lat - origin.lat)
const hdg  = CesiumMath.toDegrees(Math.atan2(dLon, dLat)) // 0° = north, CW
onPatch({ model: { ...wall.model, rotationDeg: +((hdg + 360) % 360).toFixed(1) } })
```
The wall renders `<Model modelMatrix={Transforms.headingPitchRollToFixedFrame(
Cartesian3.fromDegrees(lon,lat,alt), new HeadingPitchRoll(toRadians(heading),0,0))}/>`.

## TBM snap (origin-snap: model base drops onto the bench-mark lat/lon)
1. Render a draggable ⚑ `Entity` at `wall.tbm` (or at `wall.origin` if no TBM yet).
2. In move mode, picking that pin sets `drag = TBM`; dragging writes `tbm.lon/lat`.
3. "Snap base to TBM" button: copy `tbm` → `origin` so the model base sits exactly
   on the bench mark. Disabled when no `tbm` exists.
(Survey-precise alternative = pick a point ON the model = the bench mark; not
built — origin-snap covers 90% of cases.)

## Pitfalls (hit during build)
- **Double model render**: the wall's `<Model>` AND the editor's `<Model>` both
  draw during edit → z-fight. Gate the wall's `<Model>` with
  `!(editingWallId === wall.id)` so only the live editor copy shows.
- **Don't hand-edit pick handle ids**; `pick().id.id` is a string, not the Entity.
  Compare against the literal id you set on the `<Entity id=...>`.
- **`model.scale` / `model.rotationDeg` / `tbm` must survive normalization** in
  `validateWall` (twinRegistry.js) — store `model` wholesale so sub-fields pass
  through (don't destructure-and-drop them).
- **Wheel = scale must be gated to 'scale' mode** or it fights camera zoom.
- **HUD mode drives the overlay**: pass `mode` as a prop and add it to the
  `useEffect` dep array so the WHEEL gate re-binds when the user switches mode.

## Files (MARU)
- `src/components/TwinWallEditorOverlay.jsx` — handler + pick handles + TBM pin.
- `src/components/TwinWallEditorHUD.jsx` — mode buttons + readout + snap + done.
- `src/components/DigitalTwinWall.jsx` — wall render; hides its own `<Model>` while editing.
- `src/components/TwinWallStudio.jsx` — adds Scale/Heading/TBM fields + "Adjust on map".
- `src/context/EdgeDataContext.jsx` — `editingWallId`, `startTwinEdit`, `stopTwinEdit`, `patchTwinWall`.
- `src/twin/twinRegistry.js` — `validateWall` keeps model sub-fields + `tbm`.

Verify with `npm run lint` + `npm run build` (0 errors). Dev server must be
restarted if `vite.config.js`/proxy changed; plain component edits hot-reload.
