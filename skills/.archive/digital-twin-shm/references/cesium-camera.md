# Cesium camera & interaction patterns (Resium)

Proven patterns for the my-digital-twin / MARU SPA. All use Resium's `<Viewer>`
with a forwarded `ref` to reach the underlying Cesium `Viewer`.

## Get the Cesium Viewer instance
Resium forwards the Cesium `Viewer` through `ref`:
```jsx
import { Viewer } from 'resium'
import { useRef } from 'react'
const viewerRef = useRef(null)
// ...
<Viewer full ref={viewerRef} />
// later: viewerRef.current.camera ...
```

## Initial camera focus on mount
So the globe opens already centered on your asset array (not the default world
view):
```jsx
useEffect(() => {
  const viewer = viewerRef.current
  if (!viewer) return
  viewer.camera.setView({
    destination: Cartesian3.fromDegrees(lng, lat, 45000),
    orientation: { heading: 0, pitch: -35, roll: 0 },
  })
}, [])
```

## Live camera telemetry (HUD) — no render loop
```jsx
function readCamPos(viewer) {
  const c = viewer.camera.positionCartographic
  if (!c) return
  setCamPos({
    lat: (c.latitude * 180 / Math.PI).toFixed(4),
    long: (c.longitude * 180 / Math.PI).toFixed(4),
  })
}
useEffect(() => {
  const viewer = viewerRef.current
  if (!viewer) return
  readCamPos(viewer)
  const off = viewer.camera.changed.addEventListener(() => readCamPos(viewer), 100)
  return () => off()
}, [])
```
Notes:
- `positionCartographic` is in **radians** → multiply by `180/Math.PI` for degrees.
- `camera.changed` is throttled by the `percentageChanged` (2nd) arg — fires
  after ~1% camera movement. Cheap; updates in steps during fast drags. Covers
  pan / tilt / wheel-zoom without a wasteful `requestAnimationFrame` loop.
- For buttery-smooth per-frame readout, swap to a `requestAnimationFrame` loop
  (more React re-renders — only if the HUD genuinely needs it).

## Animated fly-to ("Locate Me" button)
```jsx
// destination BELOW current eye or the flight is a no-op (see cesium-resium-react G10);
// from deep space a single pinned flight TUMBLES — route via an overhead waypoint (G15).
const DEST = Cartesian3.fromDegrees(lng, lat, 15000.0)
const h = viewer.camera.positionCartographic?.height ?? 0
if (h > 1.0e6) {
  viewer.camera.flyTo({
    destination: Cartesian3.fromDegrees(lng, lat, 3.0e6),
    orientation: { heading: 0, pitch: -90, roll: 0 },
    duration: 1.5,
    complete: () => viewer.camera.flyTo({
      destination: DEST, orientation: { heading: 0, pitch: -45, roll: 0 }, duration: 2.0,
    }),
  })
} else {
  viewer.camera.flyTo({ destination: DEST, orientation: { heading: 0, pitch: -45, roll: 0 }, duration: 2.2 })
}
```

## Keep the globe interactive under the HUD
Overlay wrappers: `position:fixed; inset:0; pointer-events:none;`. Only
interactive children (trigger, drawer, button, input) get `pointer-events:auto`.
Without this the absolute HUD layer swallows all globe drag/zoom clicks.
