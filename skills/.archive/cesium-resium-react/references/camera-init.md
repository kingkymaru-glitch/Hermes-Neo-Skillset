# Camera init, zoom clamp & home-button override (resium)

Verified pattern from the `my-digital-twin` MARU dashboard; applies to any
resium app. Companion to G22 in SKILL.md.

## Where it goes
NOT in an App-mount `useEffect`. The real `Cesium.Viewer` only exists inside the
child component that calls `useCesium()` (here `TelemetryTracker`, which also
stashes the engine into an outside `viewerRef`). Apply all camera setup there.

## Recipe (verified green: oxlint 0/0, `vite build` OK)
```js
const INITIAL_CAMERA = {
  destination: Cartesian3.fromDegrees(101.9758, 4.2105, 12500000),
  orientation: { heading: 0.0, pitch: CesiumMath.toRadians(-90.0), roll: 0.0 },
}

// inside TelemetryTracker, after `const viewer = cesiumContext?.viewer`
// (guard via G13: viewer may be undefined on first render)
viewer.camera.setView(INITIAL_CAMERA)

// clamp scroll-out so the globe never drifts into empty space
viewer.scene.screenSpaceCameraController.maximumZoomDistance = 13000000

// route home button (if ever re-enabled) back to THIS framing
if (viewer.homeButton && !viewer.homeButton.isDestroyed()) {
  viewer.homeButton.viewModel.command.beforeExecute.addEventListener((e) => {
    e.cancel = true
    viewer.camera.flyTo(INITIAL_CAMERA)
  })
}
```

## Traps
- `INITIAL_CAMERA` must use NAMED imports `Cartesian3` (from `'cesium'`) and
  `Math as CesiumMath` — there is no `Cesium.` namespace by default (G5).
- Putting `setView` in a bare App `useEffect([])` throws `setView of undefined`
  (black void) — same root cause as G6/G13.
- `homeButton` is often disabled (`homeButton={false}`); the override is then a
  defensive no-op. Guard before `addEventListener` so it never touches undefined.
- `maximumZoomDistance` clamps OUT only. Pick an initial height below it so the
  globe opens framed (not slammed to the ceiling).
- Straight-down framing: `pitch: CesiumMath.toRadians(-90)` + `heading:0, roll:0`
  gives the clean equatorial "global view" alignment used on the dashboard.
