# Force 3D Globe — Diagnosis Tree (G14)

Symptom: user reports the Cesium/Resium map is "locked in 2D", "flat",
"can't zoom out to the sphere".

## Step 0 — PREMISE CHECK (most important)
Grep the whole project for the tokens the user blamed:
`sceneMode`, `SCENE2D`, `SCENE3D`, `SceneMode`, `mapProjection`, `globe=`,
`scene3DOnly`, `projection`, `ellipsoid`.
- If NONE are present: the code already defaults to 3D. Do NOT add
  `sceneMode={SCENE3D}` as if removing something — it's a cosmetic no-op against
  a non-existent cause. Tell the user ("sharp catch: no 2D lock to remove") and
  move to Steps 1–3 for the REAL cause.
- If a `sceneMode={SCENE2D}` IS present: remove it or set
  `sceneMode={SceneMode.SCENE3D}`.

## Step 1 — Force 3D explicitly (the real switch)
Add to `<Viewer>`:
```jsx
import { SceneMode } from 'cesium'   // named import, G5 — NOT Cesium.SceneMode
<Viewer
  sceneMode={SceneMode.SCENE3D}
  scene3DOnly          // disables 2D / Columbus-View paths — the genuine "force globe"
  ...
>
```
`scene3DOnly` is the correct equivalent of a mythical `globe={true}` prop — resium
has no `globe` prop, so `globe={true}` is a no-op.

## Step 2 — Imagery projection (usually fine by default)
OSM imagery auto-projects onto the WGS84 ellipsoid in Cesium. No wrapping needed.
Confirm the base layer is the standard token-free one (G7):
```jsx
baseLayer={new ImageryLayer(new OpenStreetMapImageryProvider({ url: 'https://tile.openstreetmap.org/' }))}
```

## Step 3 — If it STILL looks flat after a restart
The cause is then NOT projection but camera/state. Check:
- **Stale dev server:** `pkill -f vite` then restart; HMR can cache the old
  `<Viewer>` (G8). Probe the served HTML/JS for your edit.
- **Camera distance / `maximumZoomDistance`:** `INITIAL_CAMERA` at 45 km with
  `pitch: -35` may not let you zoom OUT to the full sphere. Verify the camera can
  recede; consider a `maximumZoomDistance` guard or a home-view reset.
- **Event-capture overlay:** confirm overlay wrappers (`.cmd-overlay`,
  `.chat-overlay`, `.dt-hud`) are `pointer-events: none` so the mouse-wheel
  reaches the canvas (this session: all were already none — ruled out).

## Verification
`npm run lint` (oxlint) + `npm run build` (vite build) must stay green;
`SceneMode.SCENE3D` resolves to `3` at runtime
(`node -e "import('cesium').then(c=>console.log(c.SceneMode.SCENE3D))"`).
Then a manual `npm run dev` eyeball on the real port (:5173 default, :5174 if
:5173 was taken) confirms the sphere renders and zooms out.
