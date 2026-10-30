# Cesium / Resium React — Gotchas & Fixes

## G1 — Full-bleed #root (most common)
The Vite `react` template's `index.css` pins the app column:

    #root {
      width: 1126px;
      max-width: 100%;
      margin: 0 auto;
      text-align: center;
      border-inline: 1px solid var(--border);
    }

A `<Viewer full>` child still renders *inside* that centered 1126px column.
Fix in App.css (and ensure `main.jsx` imports `./App.css`):

    html, body, #root {
      width: 100vw;
      height: 100vh;
      margin: 0;
      padding: 0;
      overflow: hidden;
    }
    #root { width: 100%; max-width: 100%; margin: 0; border-inline: none; }
    .dt-root { position: fixed; inset: 0; width: 100vw; height: 100vh; }

If using a class on the Viewer, force its box:
    .dt-viewer { width: 100% !important; height: 100% !important; }

## G2 — ErrorBoundary must be a class
React error boundaries cannot be function components. A Cesium init failure
inside `<Viewer>` throws during render; only a class boundary catches it:

    export default class ErrorBoundary extends React.Component {
      state = { hasError: false, message: null }
      static getDerivedStateFromError(e) { return { hasError: true, message: e?.message } }
      render() { return this.state.hasError ? this.props.fallback ?? <Fallback/> : this.props.children }
    }

Wrap the `<Viewer>` with `<ErrorBoundary>...</ErrorBoundary>`.

## G3 — Supabase VITE_ env + null-safe client
Only `VITE_`-prefixed vars reach the browser bundle via `import.meta.env`.
Building `createClient` with undefined args throws at import time and blanks
the whole app. Instead:

    const url = import.meta.env.VITE_SUPABASE_URL
    const key = import.meta.env.VITE_SUPABASE_ANON_KEY
    export const supabase = url && key ? createClient(url, key) : null
    export const isSupabaseConfigured = Boolean(supabase)

In the fetch effect, `if (!isSupabaseConfigured) { setAssets(DEMO); return }`
so the map shows demo pins until creds exist. Add `.env.example` and gitignore
`.env` so secrets never commit.

## G4 — StrictMode double-invoke
`<StrictMode>` mounts effects twice in dev. Guard async state writes:

    useEffect(() => {
      let cancelled = false
      async function load() { /* ... */ if (!cancelled) setAssets(data) }
      load()
      return () => { cancelled = true }
    }, [])

## G5 — Import sources
- resium: `Viewer, Entity, PointGraphics` (and `BillboardGraphics` if needed)
- cesium: `Cartesian3, Color, NearFarScalar`
- `Cartesian3.fromDegrees(longitude, latitude, height)` — note arg order
- Point color: `Color.fromCssColorString('#aa3bff')` for hex.

## G6 — Resium `<Viewer>` async race (page-load "black void" / `setView` crash)
Resium builds the Cesium `Viewer` **asynchronously**. `viewerRef.current` is the
React wrapper, NOT the engine — and `viewerRef.current.cesiumElement` is `null`
until the engine exists. A mount `useEffect(() => {...}, [])` that calls
`viewerRef.current.camera.setView(...)` will read `undefined.camera` and throw
`Cannot read properties of undefined (reading 'setView')`, white/black-screening
the app.

KEY FACT: resium's `<Viewer>` has NO `onReady` prop (verified in resium 1.24
source — Viewer `otherProps` are only className/id/style/full/containerProps/
extend/terrainProvider). Do NOT trust the common `onReady={...}` advice for
`<Viewer>`; it silently never fires. (A user in-session explicitly requested
`onReady` + `imageryProvider` on `<Viewer>` — both are wrong for this component;
`imageryProvider` is the legacy prop, `baseLayer` is correct — see G7.)

FIX — access the engine via `cesiumElement` and gate on it:

    const viewerRef = useRef(null)
    const [viewerReady, setViewerReady] = useState(false)

    // Poll via rAF until resium creates the Cesium engine instance.
    useEffect(() => {
      let raf = 0
      const check = () => {
        if (viewerRef.current?.cesiumElement) { setViewerReady(true); return }
        raf = requestAnimationFrame(check)
      }
      check()
      return () => cancelAnimationFrame(raf)
    }, [])

    useEffect(() => {
      const el = viewerRef.current?.cesiumElement
      if (!el) return
      el.camera.setView(INITIAL_CAMERA)
      readCamPos(el)
      // Live readout: scene.postRender (every frame) + camera.moveEnd (final
      // accurate read on settle). Do NOT use camera.changed here — see G9.
      const onRender = () => readCamPos(el)
      const onMoveEnd = () => readCamPos(el)
      el.scene.postRender.addEventListener(onRender)
      el.camera.moveEnd.addEventListener(onMoveEnd)
      return () => {
        el.scene.postRender.removeEventListener(onRender)
        el.camera.moveEnd.removeEventListener(onMoveEnd)
      }
    }, [viewerReady])

    function locateMe() {
      const el = viewerRef.current?.cesiumElement
      if (!el) return
      el.camera.flyTo({
        destination: Cartesian3.fromDegrees(ARRAY_CENTER.longitude, ARRAY_CENTER.latitude, 15000.0),
        orientation: { heading: 0, pitch: -45, roll: 0 },
        duration: 2.0,
        complete: () => readCamPos(el),
      })
    }

This pattern also applies to any `viewer.camera`, `viewer.scene`,
`viewer.entities`, `viewer.dataSources` access — always go through
`cesiumElement`, never the bare ref.

## G7 — No Cesium Ion token → black globe void
With no `VITE_CESIUM_ION_TOKEN`, Resium's `<Viewer>` requests Cesium Ion's
default Bing imagery on startup → 401 → globe renders as a BLACK VOID (looks
like a blank dark page, not a white error screen). This is the #1 "why is my
globe black" cause in fresh setups.

FIX — pin a dummy token so the Ion client inits without throwing, and supply a
token-free base layer. resium's `<Viewer>` forwards `baseLayer` to Cesium
(`new ImageryLayer(provider)`), which is the supported way (NOT the
`imageryProvider` prop — that's legacy/removed in current Cesium):

    import { Ion, ImageryLayer, OpenStreetMapImageryProvider } from 'cesium'
    Ion.defaultAccessToken = import.meta.env.VITE_CESIUM_ION_TOKEN || 'local-dev-no-ion'

    <Viewer
      full
      baseLayer={new ImageryLayer(
        new OpenStreetMapImageryProvider({ url: 'https://tile.openstreetmap.org/' })
      )}
      baseLayerPicker={false} geocoder={false} homeButton={false}
      sceneModePicker={false} navigationHelpButton={false}
      timeline={false} animation={false}
      creditContainer="cesium-credits"
    />

- OSM tile URL `https://tile.openstreetmap.org/` (or `a.tile.openstreetmap.org/`).
  If tiles 403/CORS in console, that's a network/provider issue — the globe
  itself is now rendering (blue earth), confirming the race/token fix worked.
- Route OSM attribution into a hidden `creditContainer` div
  (`<div id="cesium-credits" className="cesium-credit-sink" />`, visually
  clipped off-screen) so you stay attribution-compliant without a visible widget.
- To get real satellite/terrain later, set `VITE_CESIUM_ION_TOKEN` in `.env`;
  the `|| 'local-dev-no-ion'` fallback means OSM keeps working with no token.
- A *different* black void (pure black, no blue earth) usually means the
  canvas has zero height (see G1) or an uncaught JS error before render — open
  the console; a thrown `setView` (G6) produces exactly this.

## G8 — Stale dev-server / port conflict
`vite` errors "Port 5173 is in use" when an old dev server lingers. A browser
left on :5173 then hits STALE code (not your latest edits) — classic "I fixed it
but it's still blank" trap. Before declaring a front-end fix verified, kill old
servers (`pkill -f vite`; confirm ports freed with `curl -s -o /dev/null -w
"%{http_code}" http://localhost:5173/`) and start ONE fresh instance, then probe
the served module (e.g. `curl http://localhost:5173/src/App.jsx | grep <marker>`)
to confirm it contains your edit.

## G9 — `camera.changed` never fires on smooth pan/zoom (FROZEN telemetry)
`camera.changed.addEventListener(fn, 100)` registers the listener with a
`percentageChanged` threshold of 100%. Cesium compares the camera's position on
each *frame* to the position on the *previous* frame; during a normal smooth
mouse pan/zoom/drag the per-frame delta is tiny and never reaches 100%, so the
callback basically never fires. Symptom: the telemetry/HUD coordinate readout is
stuck at its initial value and does not move as you pan (the "live" listener is
dead). This is the single most common reason a "live telemetry" box appears
frozen in a resium app, and it is easy to mistake for a broken ref or a dead
button.

FIX — update the readout from the render loop, which runs every frame. The
move events live on the **Camera**, so use `camera.moveEnd` (NOT
`scene.cameraMoveEnd` — that is `undefined` and throws `reading 'addEventListener'`\nat load; see G11):

    const onRender = () => readCamPos(el)          // fires every rendered frame
    const onMoveEnd = () => readCamPos(el)         // one accurate read when motion settles
    el.scene.postRender.addEventListener(onRender)
    el.camera.moveEnd.addEventListener(onMoveEnd)
    // cleanup:
    el.scene.postRender.removeEventListener(onRender)
    el.camera.moveEnd.removeEventListener(onMoveEnd)

`scene.postRender` is the canonical Cesium live-update hook. Throttle the
`setState` with a last-value ref so the every-frame `postRender` callback does
not re-render the component while the camera is idle:

    const lastCamRef = useRef({ lat: '', long: '' })
    function readCamPos(viewer) {
      const carto = viewer.camera.positionCartographic
      if (!carto) return
      const lat = (carto.latitude * 180 / Math.PI).toFixed(4)
      const long = (carto.longitude * 180 / Math.PI).toFixed(4)
      if (lastCamRef.current.lat === lat && lastCamRef.current.long === long) return
      lastCamRef.current = { lat, long }
      setCamPos({ lat, long })
    }

Use `postRender` (plus `camera.moveEnd`) instead of `camera.changed` for any
HUD/telemetry that must track the camera continuously.

**SESSION NOTE (correction to the "never fires" wording):** the earlier claim
that `camera.changed` "never fires on smooth pan/zoom" overstates the failure.
`camera.changed` DOES fire, but only after the camera's cumulative movement
crosses `percentageChanged` (default 0.5) since the last fire — so it produces
threshold-based updates on real camera changes, not a per-frame stream. This
session the user explicitly chose `camera.changed` for the HUD lat/long readout
(per the `cesiumContext?.viewer` guard in G13) and it built green; for a COARSE
readout that's valid and lighter than `postRender`. Keep `postRender` only when
you need live tracking DURING drag. Don't blindly reject a user's `camera.changed`
prescription — verify the runtime behavior, then flag the trade-off.

## G10 — `flyTo` no-op when destination is above the current camera
A "Locate Me" / "fly to" button whose `onClick` calls
`camera.flyTo({ destination: Cartesian3.fromDegrees(lon, lat, HIGH_ALT) })` can
appear completely dead: the click handler runs, no error is thrown, but nothing
happens on screen. Root cause: `HIGH_ALT` is GREATER than the camera's current
altitude (e.g. fly target 25 km while the startup view sits at 45 km). Cesium's
`flyTo` will not animate a flight that ends "behind/above" the current eye — it
treats it as already past the destination and does nothing.

FIX — choose a destination altitude BELOW the current view, or compute it from
the live camera height:

    function locateMe() {
      const el = viewerRef.current?.cesiumElement
      if (!el) return
      const currentH = el.camera.positionCartographic?.height ?? 45000
      const targetH = Math.min(15000.0, currentH - 5000) // always closer than now
      el.camera.flyTo({
        destination: Cartesian3.fromDegrees(ARRAY_CENTER.longitude, ARRAY_CENTER.latitude, targetH),
        orientation: { heading: 0, pitch: -45, roll: 0 },
        duration: 2.0,
        complete: () => readCamPos(el),   // re-sync telemetry after the flight
      })
    }

Add a `complete` callback so the HUD re-reads the camera once the flight ends
(avoids a stale readout if `postRender` was paused during the tween). A `flyTo`
with no visible motion is almost always an altitude/direction problem, not a
ref/event-wiring problem — verify the destination is "in front of and below"
the current eye before suspecting the click handler.

## G11 — `scene.cameraMoveEnd` is undefined → load-time crash
A subtler cousin of G6. If you attach the move-end listener to the SCENE
(`el.scene.cameraMoveEnd.addEventListener(...)`), Cesium throws
`Cannot read properties of undefined (reading 'addEventListener')` at the mount
effect — because `cameraMoveEnd` does NOT exist on `Scene`. The camera move
events live on the **Camera** instance: `camera.moveEnd` and `camera.moveStart`
(confirmed in `cesium/Source/Cesium.d.ts`: `readonly moveEnd: Event;` at the
Camera class). The `viewerReady` gate in G6 already guarantees `cesiumElement`
exists, so this is NOT a readiness race — it is a wrong-object typo. The crash
reads identically to G6 (`...reading 'addEventListener'` vs `...reading
'setView'`), so check WHICH property is undefined: `scene.cameraMoveEnd` is the
tell. FIX: `el.camera.moveEnd.addEventListener(...)`.

This exact bug recurred from the skill's own G6/G9 example code (which used
`scene.cameraMoveEnd`); corrected to `camera.moveEnd` above. Always verify the
event property lives on the object you call it on — `postRender`/`preRender` are
on `Scene`, `moveEnd`/`moveStart`/`changed` are on `Camera`.

## G18 — `<Viewer baseLayer>` prop + a LayerManager that also activates the default ⇒ DUPLICATE + DESYNC
When you pass a `baseLayer` prop to `<Viewer>` (the G7 fix for the no-Ion-token
black void), Cesium paints THAT layer at stack index 0 on first paint. It is
load-bearing — removing it re-opens the black-globe void. The trap: if you also
have a `LayerManager` service that, on mount, calls `activate(DEFAULT_BASE_ID)`
to "bring up the default base," you get TWO problems at once:

1. **Duplicate layer.** `activate()` builds a *second* `UrlTemplateImageryProvider`
   for OSM and `viewer.imageryLayers.add(imagery, 0)`, stacking a redundant OSM
   `ImageryLayer` on top of the prop's layer. Wasted tile fetches + double paint.
2. **State desync (the worse one).** The manager's base-exclusivity
   (`setBaseExclusive`) only iterates the layers in its OWN `active` Map. The
   prop's OSM layer is NOT in that map, so when the user picks a different base
   (e.g. Satellite), `setBaseExclusive` removes only the manager-tracked layer and
   leaves the prop's OSM underneath. The panel reports "Satellite active" but the
   globe still shows OSM. The UI's active state no longer matches the globe.

FIX — make the manager OWN the prop's base layer. In the `LayerManager`
constructor, capture the viewer's initial base handle and register it under the
default id so exclusivity manages it (and never call `activate(default)` from the
hook's mount effect — it's a redundant no-op OR the source of the duplicate):

    constructor(viewer) {
      this.viewer = viewer
      this.active = new Map()
      this.activeBaseId = DEFAULT_BASE_ID || null
      // Capture the <Viewer baseLayer> prop's handle as the default base so we
      // (a) never build a SECOND default layer and (b) base-exclusivity can
      // remove it when the user picks a different base.
      const first = viewer.imageryLayers.get(0)
      if (DEFAULT_BASE_ID && first) {
        this.active.set(DEFAULT_BASE_ID, { layer: first, provider: null })
      }
    }

Then the React hook's mount effect just does `managerRef.current = new LayerManager(viewer)`
— NO `activate(default)` call. Switching bases now correctly removes the prop's
OSM. This is the canonical pattern for the MARU `LayerManager`
(see `frontend:digital-twin-shm`, `references/layer-orchestrator.md`). If you ever
see "I switched base but the old map is still showing," suspect a missing
constructor capture + a stray `activate(default)` in the mount effect.
