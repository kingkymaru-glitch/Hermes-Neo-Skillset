# Cesium / Resium on-globe mouse model editor

Build a "drag the 3D model with the mouse" alignment UX in a React + Resium
dashboard. Use it for the "align uploaded model to its Temporary Bench Mark
(TBM), rotate, scale" workflow — the fast draft path before a surveyor feeds
exact numbers.

## Mounting
The editor is a React component rendered INSIDE the `<Viewer>` tree (it needs
`useCesium()` for the live `viewer`). Keep a single source of truth in app
state (e.g. a context field like `editingWallId`) and pass the wall object +
an `onPatch(patch)` callback down. The component reads `wall.model.scale`,
`wall.model.rotationDeg`, `wall.origin.{lat,lon}` and writes them back on every
gesture via `onPatch`.

## Drag-to-MOVE (lat/lon)
```
const handler = new ScreenSpaceEventHandler(viewer.scene.canvas)
handler.setInputAction((d) => { downRef.current = d.position }, LEFT_DOWN)
handler.setInputAction(() => { downRef.current = null }, LEFT_UP)
handler.setInputAction((m) => {
  if (!downRef.current) return
  const ray = viewer.camera.getPickRay(m.endPosition)
  const pos = viewer.scene.globe.pick(ray, viewer.scene)   // ground hit
  if (!pos) return
  const cart = Cartographic.fromCartesian(pos)
  onPatch({ origin: { lat: toDeg(cart.latitude), lon: toDeg(cart.longitude) } })
}, LEFT_MOVE)
```

## Drag-to-ROTATE (heading)
Gate by a `mode` prop ('move' | 'rotate' | 'scale') so the gesture is
predictable. In rotate mode, on LEFT_MOVE compute the heading from base to cursor:
```
const base = Cartesian3.fromDegrees(origin.lon, origin.lat, 0)
const ray = viewer.camera.getPickRay(m.endPosition)
const hit = viewer.scene.globe.pick(ray, viewer.scene)
if (!hit) return
const ang = Math.atan2(hit.y - base.y, hit.x - base.x)
onPatch({ model: { rotationDeg: ((toDeg(ang) + 90) % 360 + 360) % 360 } })
```
Using the ground hit (not a picked entity) makes rotation work anywhere you
drag, not just on a tiny handle.

## Wheel-to-SCALE
Cesium has no wheel input action — attach a native canvas listener:
```
const canvas = viewer.scene.canvas
const onWheel = (e) => {
  if (mode !== 'scale') return
  e.preventDefault(); e.stopPropagation()      // keep the globe from zooming
  const f = e.deltaY < 0 ? 1.04 : 0.96
  const next = clamp((wall.model.scale ?? 1) * f, 0.01, 20)
  onPatch({ model: { scale: next } })
}
canvas.addEventListener('wheel', onWheel, { passive: false })
```
`stopPropagation` is essential in scale mode or the camera zooms while you
resize the model.

## TBM pin (drag + snap)
Render the bench-mark as an `<Entity>` (point + label/flag). Make it draggable
with the same LEFT_DOWN/MOVE/UP logic as the model, writing `tbm:{lat,lon}`.
"Snap base to TBM" just sets `origin = tbm` — the model base then drops exactly
on the survey point (origin-snap alignment). Keep a numeric TBM lat/lon field
for the surveyor's exact figure; the pin is the fast draft.

## Render the editable model
```
const originPos = Cartesian3.fromDegrees(origin.lon, origin.lat, 0)
const hpr = new HeadingPitchRoll(toRad(model.rotationDeg ?? 0), 0, 0)
const mtx = Transforms.headingPitchRollToFixedFrame(originPos, hpr)
<Model url={model.url} modelMatrix={mtx} scale={model.scale ?? 1} show={!!model.url} />
```
The model's base sits at `origin`; rotate about that base (HPR fixed frame).

## PITFALLS
- **Double-model z-fight.** If the wall component ALSO renders `<Model>`, the
  editor's copy and the wall's copy overlap. Gate the wall's `<Model>` with
  `editingWallId !== wall.id` so only the editor's transformable copy shows
  while aligning.
- **Context-destructure black screen.** If you reference a context field in JSX
  (`editingWallId && <HUD/>`) but forgot to add it to the `useEdgeData()` (or
  `useX()`) destructure, React throws `ReferenceError: X is not defined` and the
  whole tree crashes to a black screen. ALWAYS grep every `useX()` member you
  use in a component against its destructure, especially after copy-pasting a
  render block from another component. This is the #1 cause of "app went black
  after my last edit".
- **Visibility guards.** Render the editor model only when
  `show && origin && model.url`; otherwise `Cartesian3.fromDegrees(NaN)` throws
  and crashes the canvas.
- **Camera vs model drag.** In move/rotate modes, let Cesium pan (don't
  stopPropagation on LEFT); in scale mode only, stopPropagation the wheel.
