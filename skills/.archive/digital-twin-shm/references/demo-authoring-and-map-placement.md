# Demo Mock-Sensor Authoring + Map Placement (MARU / my-digital-twin)

Pattern proven during the `feat(demo): mock sensor authoring + map placement`
build (commit `a8750a3`). Use it whenever the user wants synthetic / demo
sensor nodes dropped onto the twin for partner demos without standing up a
real edge feed.

## Durable user guardrail (embed in any MARU UI work)
- NO hard-coded "SHM" in user-facing strings: menu labels, tooltips,
  disclaimers, banners, rail text. Align with "digital twin" / ecosystem
  branding. (User revoked it explicitly.)
- Mock data style: lively/varied — a few nodes should drift into WARN/ALERT
  so the triage UI looks exercised, not frozen-green.

## High-integrity architecture (no new global store)
Pipe mock sensor objects straight into `sensorPayloads` via the Live Edge
context so the EXISTING cluster -> group -> detail -> map framework adopts them
for free. Do NOT introduce a second state store.

```js
// context/EdgeDataContext.jsx
export const MOCK_SENSOR_TYPES = {
  temperature: { label:'Temperature', cluster:'environment', metric:'temp',     unit:'C', baseline:28, jitter:1.5, color:'#f97316' },
  humidity:    { label:'Humidity',    cluster:'environment', metric:'humidity', unit:'%', baseline:72, jitter:4,   color:'#38bdf8' },
  // ... 8 types across environment + structural clusters
}
const MAX_SLOTS = 3 // A/B/C per type

const [mockSensors, setMockSensors] = useState([])
const addMockSensor = (type, lon, lat) => { /* id = `${type}-${slot}`, mock:true */ }
const clearMockSensors = () => setMockSensors([])
const [placement, setPlacement] = useState(null) // { type, slot } when drop-armed

// tick branch (~2s): jitter each mock around baseline, push into
// historyRef[id] (cap ~30) -> getMockSeries(id)
const allSensors = [...sensorPayloads, ...mockSensors] // expose to consumers
```

`SensorsPanel` reads `allSensors` (not `sensorPayloads`) so demo nodes auto-land
in the right cluster. Extend `SENSOR_GROUPS` metric arrays to host new types
(e.g. environment metrics `['temp','humidity','aqi','wind']`).

## Map placement — resium click gives NO lon/lat (key gotcha)
`Viewer`'s `onSelectedEntityChange` only yields `{ id, name }` of a picked
ENTITY. A bare map click (no entity) is never reported there, and even when it
is, there is no coordinate. To place by clicking empty map, add a
`ScreenSpaceEventHandler` on `viewer.scene.canvas`:

```js
// component with useCesium() -> { viewer }
useEffect(() => {
  if (!viewer) return
  const handler = new ScreenSpaceEventHandler(viewer.scene.canvas)
  handler.setInputAction((click) => {
    const cart = viewer.camera.pickEllipsoid(click.position, viewer.scene.globe.ellipsoid)
    if (!cart) return
    const c = Cartographic.fromCartesian(cart)
    const lon = CesiumMath.toDegrees(c.longitude)
    const lat = CesiumMath.toDegrees(c.latitude)
    if (placement) { addMockSensor(placement.type, lon, lat); setPlacement(null) }
  }, ScreenSpaceEventType.LEFT_CLICK)
  return () => handler.destroy()
}, [viewer, placement])
```

Keep the existing entity-pick handler (`handleMapPick`) UNTOUCHED; only
intercept when a `placement` flag is set in context. Also support pin-by-
coordinate: two number inputs (lon/lat) validated before `addMockSensor`.

## resium vs cesium imports (easy jsx-no-undef crash)
- From `resium`: `Viewer, Entity, PointGraphics, LabelGraphics, useCesium`.
  `LabelGraphics` is a COMPONENT — forgetting it -> runtime
  "LabelGraphics is not defined" even though lint passes.
- From `cesium`: `Cartesian2, Cartesian3, Cartographic, Color, LabelStyle,
  VerticalOrigin, NearFarScalar, Math as CesiumMath`.
- Mock entity:
  ```jsx
  <PointGraphics pixelSize={16} color={Color.fromCssColorString(m.color)}
    outlineColor={Color.WHITE} outlineWidth={2}
    scaleByDistance={new NearFarScalar(1e6, 16, 1e8, 4)} />
  <LabelGraphics text={m.label} font="11px monospace" fillColor={Color.WHITE}
    style={LabelStyle.FILL_AND_OUTLINE} outlineColor={Color.BLACK} outlineWidth={2}
    verticalOrigin={VerticalOrigin.BOTTOM} pixelOffset={new Cartesian2(0, -18)} />
  ```

## Always-mounted drill reset (same-session, commit separately)
`SensorsPanel` / `SettingsPanel` are always mounted (CSS-hidden when closed,
state survives), so closing does NOT reset drill level/groupKey/view. Fix: pass
an `open` prop and `useEffect(() => { if (open) resetToRoot() }, [open])`; add a
`.sensors-back` chevron stroke-SVG at drill levels > 1.

## UX touches that shipped
- Neon-cyan glassmorphism drop banner (`--glass-bg`, `--glass-blur`,
  `--neon-cyan`) with a pulsing dot, shown while `placement` is armed.
- Crosshair cursor while drop-armed: `useEffect` toggling
  `viewerRef.current.container.style.cursor = placement ? 'crosshair' : ''`.
- `SensorDetail` (L3) renders a rolling SVG sparkline from `getMockSeries(id)`
  + a position/authored-facts block.

## Verification (standing)
`npm run lint` (oxlint, 0/0) + `npm run build` (vite) + `rm -rf dist`. Dev
server localhost:5174. Hold lint/build on pure visual edits until the user
eyeballs it; run them before commit.
