---
name: cesium-resium-react
description: "Build full-screen 3D geospatial React dashboards with CesiumJS via Resium (vite-plugin-cesium), optional Supabase. Covers Vite #root full-bleed, Resium error boundaries, VITE_ env, <Viewer> async race (cesiumElement vs bare ref), no-Cesium-Ion-token black-globe + OSM base, stale-dev-server trap, frozen-telemetry trap (use scene.postRender + camera.moveEnd), flyTo-no-op trap, UI/UX flyout discipline (.is-open, single-active, inert={!open}). See references/ files for live feeds A/B, mouse editor, heavy GLB iframe isolation, Supabase CRUD patterns, and rename-checklist."
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [react, cesium, resium, vite, supabase, geospatial, 3d, frontend]
---

## GLB Model Import & Spatial Transform Studio

Resium's `<Model>` renders `.glb` files via `modelMatrix`. See **references/glb-model-import-studio.md** for the full pattern: `Transforms.headingPitchRollToFixedFrame`, `ScreenSpaceEventHandler` click detection, state shape, and portal drawer lifting.

## React + Cesium Core Patterns

Use this skill whenever you build a React (Vite) app with a real-time 3D
geospatial map using CesiumJS via Resium, optionally backed by Supabase.

On-globe mouse model editor (drag-move / drag-rotate / wheel-scale / draggable
TBM pin + snap): see references/cesium-mouse-model-editor.md.
Triggers: "digital twin", "3D map", "geospatial canvas", "Cesium viewer",
"Resium <Viewer>", "assets/pins on a map", "flyout drawer", "map control
panel popover", "top-center brand collision", "standardize drawer animation",
"secondary tab re-open animation", "main flyout vs secondary flyout",
"camera initial view", "setView on startup", "maximumZoomDistance",
"zoom out limit", "home button override", "frame Malaysia / region on load". Also
load it for any UI/UX pass on the MARU / my-digital-twin dashboard.

## Stack
- React 19 + Vite, configured with `vite-plugin-cesium`
- `cesium` + `resium` for the 3D engine
- `@supabase/supabase-js` for the backend
- JSX (adjust for TS if the project uses it)

## Build steps
1. Confirm `vite.config.js` has `cesium()` — it copies Cesium static assets
   and sets `CESIUM_BASE_URL` so the globe/imagery load.
2. Override the Vite template's `#root` width constraint (Gotcha 1) with
   full-bleed CSS or the viewer renders into a centered 1126px column.
3. Wrap `<Viewer>` in a class-based `ErrorBoundary` (Gotcha 2) so a Cesium
   init throw doesn't white-screen the app.
4. Drive markers from React state: `useState([])` + `useEffect` fetch, map
   over assets to render `<Entity>` + `<PointGraphics>` at
   `Cartesian3.fromDegrees(long, lat, height)`.
5. Wire Supabase from `VITE_` env vars with a null-safe client + demo
   fallback (Gotcha 3).
6. Initialize the camera via `viewerRef.current.cesiumElement` ONLY after the
   engine is ready — gate the init `useEffect` on a `viewerReady` state polled
   with `requestAnimationFrame` (Gotcha 6). Never call `viewerRef.current.camera`
   in a bare `useEffect([])`.
7. Supply a token-free base layer so the globe renders with no Cesium Ion token:
   set `Ion.defaultAccessToken` to a dummy and pass a `baseLayer` built from
   `OpenStreetMapImageryProvider` — but FIRST import it from `'cesium'`
   (`import { ImageryLayer, OpenStreetMapImageryProvider } from 'cesium'`). A bare
   `new OpenStreetMapImageryProvider(...)` in JSX with no import throws
   `ReferenceError` and crashes the `<Viewer>` (see G7 / G7-ADDENDUM for the
   resilient memoized form). Use `baseLayer`, not the legacy `imageryProvider` prop.

## Pitfalls (details in references/gotchas.md)
- **G1 — full-bleed:** `npm create vite` pins `#root` to
  `width: 1126px; margin: 0 auto`. Override in App.css (imported from
  main.jsx) — and confirm main.jsx actually imports `./App.css`.
- **G2 — error boundary:** React error boundaries MUST be class components;
  a function component cannot catch the render-time Cesium throw.
- **G3 — Supabase env:** only `VITE_`-prefixed `import.meta.env` values reach
  the browser. Build a null client + `isSupabaseConfigured` flag so missing
  creds degrade to demo data instead of crashing at import.
- **G4 — StrictMode (fetch variety):** the fetch `useEffect` must guard with a
  `cancelled` flag cleared in cleanup, else the second StrictMode invoke
  setStates on a dead component. **NOTE: this is the *data-fetch* StrictMode
  hazard only.** The *Cesium mount* StrictMode hazard is a SEPARATE, worse
  failure — see **G28**.
- **G5 — import sources:** `Viewer, Entity, PointGraphics` from `'resium'`;
  `Cartesian3, Color, NearFarScalar, Cartographic, Math as CesiumMath` from
  `'cesium'`. NOTE: the `Cesium` NAMESPACE object is NOT imported by default —
  a blueprint that writes `Cesium.Cartographic` / `Cesium.Math.toDegrees` will
  throw `ReferenceError: Cesium is not defined` if applied verbatim. Map it to
  named imports: `Cartographic` and `Math as CesiumMath`. This exact trap fired
  this session: the prescribed fix used `Cesium.Cartographic.fromCartesian`, but
  App.jsx only had named imports, so we added `Cartographic` + `Math as CesiumMath`.
- **G6 — async race:** `viewerRef.current` is the React wrapper, NOT the engine;
  the real Cesium `Viewer` is at `viewerRef.current.cesiumElement` (null until
  ready). `<Viewer>` has NO `onReady` prop in resium 1.24 (`cesiumEventProps`
  only lists `onSelectedEntityChange`/`onTrackedEntityChange`; any
  `<Viewer onReady>` is silently swallowed by Cesium). PREFERRED FIX — render a
  child sub-component INSIDE `<Viewer>` that calls `useCesium()`; it receives the
  live `viewer` the instant the engine mounts, so camera calls run with no poll
  and no `cesiumElement` dance. See `templates/TelemetryTracker.jsx` for the
  canonical bridge (it also stashes `viewer` into an outside-accessible
  `viewerRef` so Locate Me works). INFERIOR FALLBACK (only if a child component
  is impractical): keep the engine hidden behind a `viewerReady` state polled
  with `requestAnimationFrame` until `viewerRef.current?.cesiumElement` exists,
  then gate the init `useEffect` on `viewerReady`. Calling
  `viewerRef.current.camera.setView` in a bare `useEffect([])` throws
  `setView of undefined` (black void).
- **G7 — no Ion token → black globe:** with no `VITE_CESIUM_ION_TOKEN`, default
  Bing imagery 401s → black void. Pin `Ion.defaultAccessToken` to a dummy and
  pass a token-free base layer. CRITICAL IMPORT RULE: `OpenStreetMapImageryProvider`
  is a NAMED export from `'cesium'` — it is NOT a global, and the `Cesium` namespace
  is NOT imported (see G5). Writing the inline
  `baseLayer={new ImageryLayer(new OpenStreetMapImageryProvider({url:'https://tile.openstreetmap.org/'}))}`
  in JSX WITHOUT first importing `OpenStreetMapImageryProvider` from `'cesium'` throws
  `Uncaught ReferenceError: OpenStreetMapImageryProvider is not defined` at the
  `<Viewer>` mount → the whole canvas crashes. SESSION: this exact crash fired on
  MARU at App.jsx:1439 (the bare `new OpenStreetMapImageryProvider(...)` had no import);
  fixed by adding it to the named `from 'cesium'` block. Use `baseLayer`, not the
  legacy `imageryProvider` prop. Route attribution to a hidden `creditContainer`.
- **G7-ADDENDUM — make the base layer RESILIENT (memoize + try/catch + fallback):** the
  inline `baseLayer={new ImageryLayer(new OpenStreetMapImageryProvider(...))}` form has
  TWO flaws beyond the import trap: (1) it reconstructs the provider on EVERY render
  (wasted network/CPU, re-runs inside `<Viewer>`'s props each render), and (2) if the
  constructor throws (bad Cesium build, OSM unreachable at construct time) the
  `<Viewer>` tree throws and the ErrorBoundary takes down the whole layout. PREFERRED
  form — a `useMemo(..., [])` provider built ONCE, feature-checks the constructor,
  falls back to `UrlTemplateImageryProvider` (also a named `'cesium'` import), and
  returns `undefined` (not throw) if everything fails so the viewer still boots
  without base tiles:
  ```js
  import { ImageryLayer, OpenStreetMapImageryProvider, UrlTemplateImageryProvider } from 'cesium'
  const baseLayer = useMemo(() => {
    try {
      const provider = typeof OpenStreetMapImageryProvider === 'function'
        ? new OpenStreetMapImageryProvider({ url: 'https://tile.openstreetmap.org/' })
        : new UrlTemplateImageryProvider({
            url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            credit: '© OpenStreetMap contributors', maximumLevel: 19,
          })
      return new ImageryLayer(provider)
    } catch (err) {
      console.warn('[DigitalTwin] base imagery unavailable — viewer starts without a base layer', err)
      return undefined
    }
  }, [])
  // <Viewer baseLayer={baseLayer} ...>
  ```
  This also makes HMR/prod-build safe (provider constructed exactly once). Verified
  green on MARU (oxlint 0/0, vite build OK) after the G7 crash.
- **G8 — stale dev server:** old `vite` on :5173 serves stale code → "fix didn't
  work" trap. Kill with `pkill -f vite`, start one fresh instance, probe the
  to confirm it contains your edit.

## Pitfalls (continued)
- **G9 — `camera.changed` is THRESHOLD-based, not per-frame (coarse HUD, not
  frozen):** `camera.changed.addEventListener(fn, percentageChanged)` fires only
  after cumulative camera movement crosses `percentageChanged` (default 0.5) since
  the last fire — so it gives threshold updates on real camera changes, NOT a
  per-frame stream. During a smooth continuous pan, the per-frame delta is small
  so the callback doesn't fire every frame; it is NOT dead, but it will look
  "stuck" between threshold crossings. For a readout that must update DURING
  drag, drive it from `el.scene.postRender` (every frame) + `el.camera.moveEnd`
  (final accurate read on settle) instead. SESSION CORRECTION: the prior wording
  ("never fires on smooth pan/zoom") overstated the failure; this session the
  user explicitly chose `camera.changed` for a coarse lat/long HUD (guarded by
  `cesiumContext?.viewer`, see G13) and it built green. Don't blindly reject a
  `camera.changed` prescription — verify runtime behavior, then flag the
  trade-off (coarse vs live). NOTE: the move events live on the **Camera**, not
  the Scene — `el.scene.cameraMoveEnd` is `undefined` and throws `Cannot read
  properties of undefined (reading 'addEventListener')` at load (see G11). Throttle setState with a last-value
  ref so `postRender` (every frame) doesn't re-render idle. Canonical Cesium
  live-update pattern — full example in references/gotchas.md G6.
- **G10 — `flyTo` no-op when destination is *above* current camera:** a
  `locateMe` button calling `camera.flyTo({ destination: Cartesian3.fromDegrees(
  lon, lat, HIGH_ALT) })` can appear dead if HIGH_ALT exceeds the camera's
  current altitude (e.g. target 25 km when the startup view is 45 km). Cesium
  won't animate a flight that ends "behind/above" the current eye. FIX — pick a
  destination altitude BELOW the current view (15 km), or read
  `viewer.camera.positionCartographic.height` to size a closer target; add a
  `complete: () => readCamPos(el)` callback so telemetry re-syncs post-flight.
- **G11 — `scene.cameraMoveEnd` is undefined → load-time crash:** a deeper
  cousin of G6. Attaching the move-end listener to the SCENE
  (`el.scene.cameraMoveEnd.addEventListener(...)`) throws `Cannot read
  properties of undefined (reading 'addEventListener')` at the mount effect,
  because `cameraMoveEnd` does NOT exist on Cesium's `Scene` — the move events
  live on the **Camera** (`camera.moveEnd`, `camera.moveStart`; confirmed in
  `cesium/Source/Cesium.d.ts`). The `viewerReady` gate already guarantees
  `cesiumElement` exists, so this is NOT a readiness race — it is a
  wrong-object typo. The crash reads like G6 (`...reading 'addEventListener'` vs
  `...reading 'setView'`), so check WHICH property is undefined:
  `scene.cameraMoveEnd` is the tell. FIX: `el.camera.moveEnd.addEventListener(...)`.
  Rule of thumb: `postRender`/`preRender` are on `Scene`; `moveEnd`/`moveStart`/
  `changed` are on `Camera`.

- **G13 — `useCesium()` empty context on first render (the `reading 'scene'`
  crash):** when you bridge the engine via a child component that calls
  `useCesium()` (the PREFERRED fix for G6), Resium provides context only AFTER
  the `<Viewer>` mounts — so on the very first render `useCesium()` returns an
  EMPTY OBJECT `{}`, and `const { viewer } = useCesium()` yields `viewer =
  undefined`. Any `viewer.camera`/`viewer.scene` access before a guard throws
  `Cannot read properties of undefined (reading 'scene')` — exactly the crash
  this session fixed. SAFE pattern (optional chaining, NOT bare destructure):
  ```js
  const cesiumContext = useCesium()
  const viewer = cesiumContext?.viewer // {} on first render -> undefined, safe
  useEffect(() => {
    if (!viewer || typeof viewer.isDestroyed !== 'function' || viewer.isDestroyed()) return
    // ... camera calls now safe
  }, [viewer, ...])
  ```
  Distinct from G6's `cesiumElement` ref race: the child bridge already has the
  live `viewer` once context populates, but you must still guard the first
  render where context is `{}`. The skill's `templates/TelemetryTracker.jsx`
  MUST use this `ctx?.viewer` form (update it if it still does `const { viewer }
  = useCesium()`). Also stash the genuine `viewer` into an outside `viewerRef`
  (`if (viewerRef) viewerRef.current = viewer`) so a Locate-Me button outside
  `<Viewer>` can `camera.flyTo`.

- **G15 — `flyTo` TUMBLES (multi-flip) when launched from deep space, even
  with a pinned `orientation`:** a Locate-Me `camera.flyTo({ destination,
  orientation: { heading: 0, pitch: -45, roll: 0 } })` looks correct on paper,
  but from far out (zoomed to the whole Earth) the START frame is a degenerate
  top-down pose, so Cesium's shortest-arc interpolation rolls the pinned
  heading/pitch through multiple flips on the way in. (Distinct from G10, where
  the flight is DEAD because the destination is *above* the current eye — here
  it flies, but spins.) FIX — branch on current altitude and route through a
  clean overhead waypoint first when far out:
  ```js
  const DEST = Cartesian3.fromDegrees(lon, lat, 15000.0)
  const h = el.camera.positionCartographic?.height ?? 0
  if (h > 1.0e6) {                       // ~above low Earth orbit → tumble zone
    el.camera.flyTo({
      destination: Cartesian3.fromDegrees(lon, lat, 3.0e6),
      orientation: { heading: 0, pitch: -90, roll: 0 },   // straight down, no roll
      duration: 1.5,
      complete: () => el.camera.flyTo({                   // then drop to vantage
        destination: DEST,
        orientation: { heading: 0, pitch: -45, roll: 0 },
        duration: 2.0,
      }),
    })
    return
  }
  el.camera.flyTo({ destination: DEST, orientation: { heading: 0, pitch: -45, roll: 0 }, duration: 2.0 })
  ```
  Each leg starts/ends at a well-defined orientation, so no roll-tumbling.
  Close in (normal use) the single direct flight already animates cleanly.

- **G14 — "map is stuck in 2D / flat" is almost never a `sceneMode` prop:** Cesium's
  `<Viewer>` defaults to `SceneMode.SCENE3D`; there is no `globe={true}` prop in
  resium (so a prescribed `globe={true}` is a silent no-op), and OSM imagery
  already auto-projects onto the WGS84 ellipsoid by default (no wrapping hack
  needed). So a user's "remove the 2D override" blueprint usually has nothing to
  remove. TO FORCE 3D EXPLICITLY (the real switch): add
  `sceneMode={SceneMode.SCENE3D}` AND `scene3DOnly` to `<Viewer>`. `scene3DOnly`
  is the genuine "disable 2D / Columbus-View code paths" flag — closest correct
  equivalent of a `globe`/"force globe" toggle. Import `SceneMode` from `'cesium'`
  (named, per G5 — do NOT write `Cesium.SceneMode`). Full diagnosis tree when the
  globe won't show the 3D sphere: references/force-3d.md.

- **G16 — clicking an `<Entity>` to drive a selection panel:** Resium maps Cesium's
  `selectedEntityChanged` to a REAL `<Viewer>` prop `onSelectedEntityChange` (it's
  in resium's `cesiumEventProps`, not a custom prop). Wire it to a `selectedAsset`
  state: `onSelectedEntityChange={(e) => setSelectedAsset(e ? { id: e.id, name:
  e.name } : null)}`. Gotchas: (1) give each `<Entity>` an `id` prop — without it
  `entity.id` is `undefined` and can never match; (2) set `infoBox={false}` +
  `selectionIndicator={false}` or Cesium's default InfoBox popup shows alongside
  your panel; (3) the `id` is distinct from React `key`. Full project-specific
  console that consumes this lives in `frontend:digital-twin-shm`
  (`references/s22-console.md`).
  (4) **RE-CLICK TRAP:** `onSelectedEntityChange` only fires when the *selected*
  entity CHANGES — so re-clicking an already-selected dot (e.g. open S22, dismiss
  the drawer, click S22 again) fires NOTHING and the panel stays shut. For a
  reliable click-to-toggle, use the G17 ScreenSpaceEventHandler pattern instead.

- **G17 — `onSelectedEntityChange` only fires on SELECTION CHANGE → re-click is a
  no-op (the "sometimes won't open" bug):** Cesium's `selectedEntityChanged` (and
  Resium's `onSelectedEntityChange`) fires ONLY when the selected entity differs
  from the previous one. Open S22 → drawer opens → dismiss (selection stays
  `s22-ultra`) → click S22 again → Cesium sees no change → nothing fires → panel
  stays shut. Reliable fix: attach a `ScreenSpaceEventHandler` `LEFT_CLICK` to
  `viewer.scene.canvas` that calls `viewer.scene.pick(click.position)` on EVERY
  click and resolves the entity directly:
  ```js
  const handler = new ScreenSpaceEventHandler(viewer.scene.canvas)
  handler.setInputAction((click) => {
    const obj = viewer.scene.pick(click.position)
    const entity = (obj && obj.id && typeof obj.id.id === 'string')
      ? { id: obj.id.id, name: obj.id.name } : null
    onPickRef.current(entity)   // route to latest handler via a ref
  }, ScreenSpaceEventType.LEFT_CLICK)
  // cleanup: if (!handler.isDestroyed()) handler.destroy()
  ```
  Hold the handler in a `useRef` (`onPickRef.current = handleMapPick` each render)
  so the one-time listener always sees the latest closure; add `onPickRef` to the
  effect deps to keep oxlint quiet. Clicking empty space → `obj.id` is undefined →
  treat as 'deselect'. This replaces `onSelectedEntityChange` for any
  click-to-open panel. Full MARU wiring (per-entity **side routing** — S22→LEFT
  main drawer, sensor→RIGHT tab — plus the **single-active side manager** that
  stops left/right panels colliding) in `references/reliable-entity-pick.md`.

- **G18 — map chrome must NOT eat globe pointer events:** putting a brand
  wordmark / data disclaimer / legend ON the canvas is fine, but a plain
  `position: absolute` overlay with `pointer-events: auto` (or any interactive
  ancestor) blocks dragging the globe through that region. FIX — wrap ALL
  non-interactive chrome in ONE container `{ position: absolute; inset: 0; z-index: 11; pointer-events: none; }` (z above HUD z-10, below flyouts z-20+) so the
  globe stays fully draggable and children inherit `pointer-events: none`. Place
  the brand top-CENTER (HUD top-left, Map Control top-right, Locate-Me
  bottom-left leave center-top free) and the disclaimer bottom-right. Keep
  clickable overlays (Locate-Me z-30, MCP trigger z-22) as SEPARATE `position:
  fixed` elements with `pointer-events: auto`, shifted via a `.shifted` class
  when a flyout is open. Full pattern + placement cheat-sheet →
  `references/map-overlay-chrome.md`.

- **G19 — top-CENTER brand collides with a left-anchored HUD on narrow
  viewports (the "brand eats the Edge/sim pill" bug):** a centered brand
  (`left:50%; transform:translateX(-50%)`) and a left-anchored HUD
  (`left:12px`, ~350px wide) only stay apart while the viewport is wide. The
  brand's left edge = `0.5·W − halfBrandWidth`; it crosses the HUD's right edge
  (~362px) when `W < ~1096px` (typical half-screen snap / 13" laptop). Because
  the brand usually has the higher `z-index`, it PAINTS OVER the HUD status pill
  (e.g. "Edge (sim)") — looks fine on a 1440px monitor, breaks on a laptop.
  FIX (proof the layout responsively, don't just nudge): (a) raise the HUD
  `z-index` ABOVE the brand so functional status always wins any residual touch;
  (b) `@media (max-width:1200px){ .brand-sub{display:none} }` — drop the long
  sub-label so the brand shrinks to M-mark + wordmark (~120px) and clears the
  HUD; (c) `@media (max-width:820px){ .brand{display:none} }` — the drawer
  header already carries the identity there. Same shedding approach pro apps
  (Google Maps, Figma) use for top chrome. SESSION: this exact collision was
  confirmed real on MARU and fixed this way.

- **G20 — floating popover vs drawer animation mismatch (the "Map Control opens
  differently from every other panel" bug):** a `position:fixed`/absolute
  popover (e.g. the Map Control card) authored with its own `animation: pop
  0.18s ease-out` + unmount-on-close animates DIFFERENTLY and OPPOSITELY to the
  side drawers (which slide via `transform 0.34s cubic-bezier(0.22,1,0.36,1)`).
  The popover also has no CLOSE animation (the card unmounts instantly), so the
  open/close feel is asymmetric. STANDARDIZE: make the popover use the SAME
  easing + duration as the drawers and make it SYMMETRIC. Pattern: keep the card
  ALWAYS MOUNTED and toggle an `.is-open` class (don't unmount), drive it with a
  `transition` (not a one-shot `animation`), start `opacity:0; transform:
  translateX(16px) scale(0.98)` → `.is-open{opacity:1; transform:none}`. Because
  the card stays mounted, re-opening never re-pops — it just slides. CRITICAL
  PITFALL: if the popover's parent is a `display:flex` container and the card is
  a flex child, the closed (248px) card shoves the trigger ~248px away from the
  corner. Take the card OUT of flow with `position:absolute; top:0; right:0`
  inside the anchored wrapper so the trigger stays pinned. SESSION: this exact
  mismatch on MARU fixed by moving Map Control to the drawer easing + always-
  mounted `.is-open` + absolute positioning.

- **G21 — single-active flyout CLICK model (suppress re-open animation on
  repeated same-button clicks):** product requirement for a mission-control
  feel — (a) clicking a main-flyout button opens its secondary tab on the RIGHT
  and closes the main drawer; (b) RE-clicking the SAME main button while that
  secondary is ALREADY open must be a NO-OP — the panel stays put, no re-open
  animation; (c) interacting with the secondary tab closes the main drawer.
  IMPLEMENTATION: keep a `flyoutSide` state ('left'|'right'|null) + per-tab
  booleans. A single `openSecondary(which)` helper early-returns when
  `flyoutSide==='right' && <that tab is already open>` — because the drawer is
  already mounted and only the `.open` class is set, the repeated click is
  visually inert (no re-animation). It also sets `drawerOpen=false` so the main
  collapses (rule c). Don't unmount/remount drawers per click — they must stay
  mounted and toggle `.open` so transitions are continuous. Remove dead helpers
  (e.g. an `openSensors()` that just called `openRight('sensors')`) once
  `openSecondary` supersedes them. Full wiring → `references/flyout-click-model.md`.

- **G22 — camera initial framing, zoom-out clamp, and home-button override MUST
  live inside the `useCesium` bridge (not an App-mount effect):** `viewer.camera.setView(...)`, `viewer.scene.screenSpaceCameraController.maximumZoomDistance = N`, and `viewer.homeButton.viewModel.command.beforeExecute` all require the REAL `Cesium.Viewer` instance. In a resium tree the App-level `<Viewer>` React ref is the wrapper (see G6/G13); the only spot guaranteed to hold the live engine is the child component that calls `useCesium()` (here `TelemetryTracker`, which also stashes the viewer into an outside `viewerRef`). Apply all three there. Verified recipe (full in `references/camera-init.md`):
  ```js
  // inside TelemetryTracker, after const viewer = cesiumContext?.viewer
  viewer.camera.setView({
    destination: Cartesian3.fromDegrees(lon, lat, heightM),
    orientation: { heading: 0.0, pitch: CesiumMath.toRadians(-90.0), roll: 0.0 },
  })
  viewer.scene.screenSpaceCameraController.maximumZoomDistance = 13000000
  if (viewer.homeButton && !viewer.homeButton.isDestroyed()) {
    viewer.homeButton.viewModel.command.beforeExecute.addEventListener((e) => {
      e.cancel = true
      viewer.camera.flyTo(INITIAL_CAMERA)
    })
  }
  ```
  Traps: (1) `setView` in a bare `App useEffect([])` throws `setView of undefined` / black void (same root as G6) — the bridge is the fix; (2) `INITIAL_CAMERA` must use NAMED imports `Cartesian3` + `Math as CesiumMath` (G5 — no `Cesium.` namespace); (3) `homeButton` is often disabled (`homeButton={false}`) — guard before `addEventListener` or it's a no-op/undefined; the override stays correct as defensive "if re-enabled" routing; (4) `maximumZoomDistance` clamps scroll-OUT only — pick an initial height BELOW it so the globe opens framed, not slammed to the ceiling. SESSION: this exact placement + recipe built green (lint 0/0, vite build OK) on MARU.

 - **G22-ADDENDUM — camera "center at startup" is an OPENING POSE ONLY, not a navigation lock:** the G22 recipe ADDS `maximumZoomDistance` + a `homeButton` `beforeExecute` override. Only include those if the user EXPLICITLY wants the camera LOCKED. A plain "center the globe when the app opens" request means: `camera.setView({ destination: Cartesian3.fromDegrees(0, 0, 24000000), orientation: { heading: 0, pitch: CesiumMath.toRadians(-90), roll: 0 } })` (whole-Earth, straight down) and NOTHING ELSE — no zoom ceiling, no home override, navigation fully free. SESSION: MARU commit `76c5368` added exactly those locks on a "frame Malaysia" ask; the user LATER REVOKED it — "I did not ask for locked GPS to Malaysia... align the earth so it sets in the middle... do not lock the navigation." The locks were stripped, only the centered opening pose kept. Treat G22's lock snippet as opt-in, never default.

 - **G23 — always-mounted flyout deep-link state SURVIVES close (the "reopen jumps to the deepest level" bug):** panels like `SensorsPanel` (`level`/`groupKey`/`localSensorId`) and `SettingsPanel` (`view`) keep their drill-down state in `useState`, but they are ALWAYS MOUNTED — rendered inside the hidden drawer `<aside>` and toggled only via a CSS `.open` class. The × just removes `.open`; it does NOT unmount, so the state stays at the deepest level. Reopening resumes there (user saw: close L3 detail → reopen from main tab → straight to L3, skipping L1/L2). FIX: pass an `open` prop down and reset drill-down to root in an effect gated on it:
 ```js
 useEffect(() => {
   if (open) { setLevel('cluster'); setGroupKey(null); setLocalSensorId(null) }
 }, [open])
 ```
 Apply the same for ANY always-mounted panel with internal nav state. Also add an EXPLICIT back chevron (not just a breadcrumb) at every sub-level — breadcrumbs read as labels, not buttons, so users miss them. The one-tap `‹` must step back exactly one level (L3→L2→L1), not straight to root. SESSION: this exact bug on MARU's 3-level Sensor Clusters (clusters → group → sensor) and Settings; fixed by `open`-prop reset + injected `.sensors-back` chevron. Canonical recipe → `references/flyout-state-reset.md`.

 - **G24 — CSS duplicate-selector SILENT OVERRIDE + "rendered class has no matching rule" (the disclaimer-overlap + top-left base-layer-control bugs):** two CSS failure modes, both silent:
 (a) **DUPLICATE SELECTOR** — two rules for the same selector (e.g. `.map-disclaimer`): a LATER one with `bottom:14px` silently overrode an EARLIER `bottom: calc(26px + 12px)`, dropping the box onto the 26px Status Rail (overlap). Later same-specificity rules ALWAYS win, with no warning.
 (b) **STALE/MISSING RULE** — a component renders `className="mcp-drawer"` (always mounted) but the stylesheet only had DEAD rules `.mcp` / `.mcp-card` (renamed-away) and NO `.mcp-drawer`, so the panel collapsed to an unstyled static block pinned top-left = the "base layer control on top of the screen" the user spotted.
 SESSION: both bugs on MARU; fixed by consolidating `.map-disclaimer` to one rule and adding real `.mcp-drawer` / `.mcp-drawer.is-open` (360px right slide, same easing as the other flyouts).

 - **G26 — "why does the map show only 2 markers when the feed returned 20 records?" is almost always CORRECT DEDUP, not a bug (the live-feed probe discipline):** a polling AIS feed (VesselAPI bounding-box with a `time.from`/`time.to` window) returns **historical PINGS per vessel**, not a single current snapshot. So 20 records across 2 distinct mmsi → after the G25 `getOrCreateEntity` dedup (one entity per mmsi), you correctly see **2 markers**. Before suspecting a render/normalizer bug, PROBE the live feed through the SAME proxy+path the app uses and count three things: (1) total records, (2) distinct `mmsi`, (3) records with valid `latitude`/`longitude`. Reusable probe: `scripts/probe-vesselapi.sh` (run from the repo root; it mirrors `egressDrivers.js` box+window, reads the key the SAFE way, prints records vs distinct vessels). SESSION MISDIAGNOSIS TO AVOID: the first probe printed `.get('name')`/`.get('lon')` and showed `name=None` — a BUG IN THE PROBE, not the app (the real keys are `vessel_name`/`latitude`/`longitude`, which the app normalizer already reads). Always print the actual upstream keys. Other real causes of "few markers" (distinct from dedup): the box is empty for that region/time (compact 1° box → 0; 4°-span Port Klang box → ~20), or all records share one mmsi (track of one vessel). The VesselAPI request-shape caps (≤4° span, ≤4h window) live in `digital-twin-shm` (`references/vesselapi-request-shape.md`).

 - **G25 — resium `<Entity id=…>` RE-ADDS by id every poll → `DeveloperError: An entity with id X already exists in this collection.`** (the "hundreds of uncaught promise rejections" bug): when vessel/asset data refreshes on an interval (e.g. every 30s), any entity that PERSISTS between refreshes gets a fresh `<Entity id={v.id}>` mount, and resium calls `viewer.entities.add` again → Cesium throws `DeveloperError` (rejects duplicates). The point still renders, but the throw is an unhandled promise rejection that spams the Console (323× seen) and eventually destabilizes the page. **FIX — manage entities IMPERATIVELY, never through `<Entity id>` JSX for a polling feed.** Use `viewer.entities.getOrCreateEntity(id)` (idempotent — returns the existing entity if present, never throws) to upsert, and PRUNE stale `vessel-*` entities that dropped out of the feed:
 ```js
 // inside the useCesium bridge; deps [vessels, selected, viewer]
 if (!vessels.length) {
 viewer.entities.values
   .filter((e) => typeof e.id === 'string' && e.id.startsWith('vessel-'))
   .forEach((e) => viewer.entities.remove(e))
 return
 }
 const seen = new Set()
 for (const v of vessels) {
 const e = viewer.entities.getOrCreateEntity(v.id)   // idempotent
 e.position = Cartesian3.fromDegrees(v.lon, v.lat)
 e.point = new PointGraphics({ pixelSize: 9, color: LIVE, outlineColor: Color.WHITE, outlineWidth: 1 })
 e.polyline = new PolylineGraphics({ positions: [/* … */], width: 2, material: LIVE })
 e.label = new LabelGraphics({ /* … */ })
 seen.add(v.id)
 }
 viewer.entities.values
 .filter((e) => typeof e.id === 'string' && e.id.startsWith('vessel-') && !seen.has(e.id))
 .forEach((e) => viewer.entities.remove(e))
 ```
 NOTE: assign the graphics as `e.point = new PointGraphics({…})` (plain cesium graphics objects), NOT `<PointGraphics>` JSX — there is no JSX in the imperative path. Keep the `useCesium` `ctx?.viewer` guard (G13) and the `ScreenSpaceEventHandler` click-to-track pattern (G17) for the HUD. SESSION: this exact rejection storm fired on MARU's live VesselAPI feed (a persisting vessel like `vessel-563118300` re-added each poll); fixed by the imperative `getOrCreateEntity` + prune rewrite of `MaritimeEntities.jsx`. Verified green (oxlint 0/0, vite build OK). The bbox/span/window caps that interact with this feed live in the project's `digital-twin-shm` skill (`references/vesselapi-request-shape.md`).

  - **G27 — closed flyout drawer with `aria-hidden="true"` + a focusable child throws a console `Blocked aria-hidden` a11y warning (the "sensors-close focus hidden" bug):** every mission-control dashboard has right-side `<aside>` drawers toggled by a CSS `.open` class while staying ALWAYS MOUNTED (G20/G21/G23). When closed they commonly carry `aria-hidden={!open}` to keep screen-readers from reading hidden chrome. But the drawer's own close button (`.sensors-close`, `.settings-close`, etc.) RETAINS focus after the user tabs/click-closes, so Chrome sees a focused element INSIDE an `aria-hidden` subtree → `Blocked aria-hidden on (index):1 — an element because its descendant retained focus. The focus must not be hidden from assistive technology users.` It's harmless functionally but spams the Console and fails a11y audits. **FIX (React 19): add `inert={!open}` to the SAME `<aside>` as the `aria-hidden`.** `inert` removes the closed subtree from the tab/focus order AND from assistive tech, so no focusable child can ever live inside the hidden drawer — the contradiction (hidden ancestor + focused descendant) is gone and the warning clears. `inert` is a native boolean prop in **React 19** (this repo: `react: ^19.2.7`), so `inert={!open}` works directly — NO ref shim needed (on React ≤18 you'd set `el.inert = !open` via a ref instead). **Apply to ALL always-mounted drawers that use `aria-hidden={!open}`** (cmd-drawer, chat-drawer, both settings-drawer variants, sensors-drawer) — not just the one that logged the warning, or the others throw the IDENTICAL warning when their close button retains focus. SESSION: this exact warning fired on MARU's `.sensors-drawer` (focused `button.sensors-close`, ancestor `<aside aria-hidden="true">`); fixed by adding `inert={!sensorsOpen}` (and the other three) in App.jsx; oxlint 0 errors + vite build OK.

- **G28 — React StrictMode double-mount tears down Cesium → `DeveloperError: This object was destroyed` (the "blank globe / Cesium error card" dev-only crash):** Resium's `<Viewer>` is NOT StrictMode-safe. In dev, StrictMode mounts → unmounts → remounts; the first `viewer` instance gets `destroy()`-ed but a stale effect closure still touches it, so you get `DeveloperError: This object was destroyed, i.e., destroy() was called.` and the globe whitescreens or shows Cesium's own render-error card. The classic "StrictMode is just a harmless dev check" premise is FALSE for Cesium. FIX (preferred): do NOT wrap the Cesium tree in `<StrictMode>` — remove it from `main.jsx` (keep `QueryClientProvider`). FIX (defense-in-depth): guard every viewer-touching effect in the `useCesium` bridge with `if (!viewer || viewer.isDestroyed?.()) return` + try/catch (raster swap, scene morph, viewerRef stash). Full recipe → `references/strictmode-cesium-crash.md`. SESSION: this exact crash fired on a R-Tessera rebuild (whole app blanked) and was fixed by dropping StrictMode + adding `isDestroyed()` guards to the bridge.

- **G29 — a render-time `ReferenceError` whitescreens the app and React hides the real cause (the "blank page, generic 'error occurred in <X>' warning" trap):** when a component throws during render (e.g. you added a prop to the call site in App.jsx but forgot to add it to the component's destructured params → `ReferenceError: showWeather is not defined`), React swallows the real exception into the generic "An error occurred in the <Component> component. Consider adding an error boundary…" warning and prints NO stack. If the throwing component is rendered OUTSIDE the app's `<ErrorBoundary>` (a sibling of `<Viewer>`, not a child), the boundary can't catch it and the whole app whitescreens with no usable error. SURFACING TRICK (temporary, revert after): patch `main.jsx` with `window.onerror` / `unhandledrejection` handlers that write `e.error.stack` into `#root`, reload, read the real stack, fix the root cause, then revert the patch. PREVENTION: when you pass a new prop into a call site, ALWAYS add it to that component's destructured param list in the SAME edit (one `patch` per file won't catch the other); grep the prop name across the component file before claiming done. Also wrap every top-level UI panel (not just `<Viewer>`) in an error boundary. Full diagnostic + recipe → `references/strictmode-cesium-crash.md`. SESSION: `ReferenceError: showWeather is not defined at MapControlPanel.jsx:30` was surfaced this way on R-Tessera and fixed by adding the two missing props to the signature.

- **G30 — browser `fetch()` of a third-party geo/JSON feed can be CORS-blocked EVEN THOUGH `curl` succeeds (the "CABLE FEED OFFLINE — Network error" + `TypeError: Failed to fetch` trap):** many public geo feeds (e.g. `submarinecablemap.com/api/v3/cable/cable-geo.json`, 718 MultiLineString cables) send **no `Access-Control-Allow-Origin` header**, so a browser `fetch()` from `localhost` / `*.vercel.app` is blocked by the browser's same-origin policy, while `curl` (which ignores CORS) returns 200. Symptom: `fetch()` throws `TypeError: Failed to fetch` / `Network error`, and the layer's error HUD fires even though the URL is correct. DIAGNOSE before blaming the URL: `curl -s -D - -o /dev/null -H "Origin: http://localhost:5174" <URL> | grep -i "access-control"` — if no `access-control-allow-origin` line appears, it's CORS, not a dead endpoint. FIX (preferred, CORS-free + offline-safe): **bundle the dataset locally** — `curl -s <URL> -o public/<name>.geojson`, load it via `fetch('/<name>.geojson')` first, fall back to the remote URL only if the local fetch fails. Vite copies `public/` into `dist/` automatically, so it ships with the build and works on Vercel with zero CORS. Alternative when the feed MUST stay live: proxy it (Vite `server.proxy` in dev + a Vercel serverless function in prod) — heavier. The local-bundle pattern also makes the layer render with no network at all. SESSION: this exact CORS block fired on R-Tessera's Submarine Cables layer (submarinecablemap.com, no CORS header); fixed by bundling `public/cables.geojson` (718 features) and loading `/cables.geojson` first. Full recipe + source list → `references/cors-blocked-geo-feeds.md`.

- **G31 — "I pushed to GitHub" does NOT mean "it's live on Vercel" (the deploy-verification trap):** a `git push origin main` only updates the repo. The live site updates ONLY if (a) Vercel's Git integration is connected to that repo+branch, OR (b) you ran a Vercel deploy. A push alone is silent if the integration was never wired (or points at a different source/branch). VERIFY before declaring done: probe the live URL AND confirm the deployed build matches your commit — `curl -s https://<project>.vercel.app/ | grep -o '<title>[^<]*</title>'` and compare the served `index.html` assets/hash, or `curl` a file you added (e.g. `curl -s -o /dev/null -w "%{size_download}" https://<project>.vercel.app/cables.geojson` — a 569-byte response that's actually the SPA's `index.html` fallback means the file isn't deployed). If the integration isn't connected, a Vercel deploy needs a token: `vercel deploy --prod --token <TOKEN>` (install CLI locally if global install is permission-blocked: `npm i -D vercel` then `./node_modules/.bin/vercel`). SESSION: R-Tessera's `r-tessera.vercel.app` was serving a PRE-FRESH-START build (`/cesium/Cesium.js` references, no `cables.geojson`) after the push — the Git integration wasn't live, proving the push didn't deploy.

- **G31-ADDENDUM — even a CONNECTED Git integration can silently NOT deploy if the commit AUTHOR EMAIL doesn't match the webhook's expected identity:** the integration being wired is necessary but NOT sufficient. Vercel's GitHub webhook fires the build only for commits authored by an identity it recognizes; if you commit with a throwaway author (e.g. `git -c user.email="hermes@local" commit …`), the push succeeds and the repo updates, but the deploy webhook does NOT fire and the live site stays on the previous build indefinitely — indistinguishable from "integration not connected" from the CLI side. DIAGNOSE: `git log -1 --format='%an <%ae>' HEAD` vs the repo's configured `git config user.email`; if they differ (your commit used a different author), that's the trigger failure. FIX: re-author the tip as the repo's configured identity and re-push — `git commit --amend --author="$(git config user.name) <$(git config user.email)>" --no-edit` then `git push --force-with-lease origin main` (force-with-lease, never blind --force). For R-Tessera the expected author is `kingkymaru@gmail.com` (per vault GEMINI R-TESSERA CEO.md: "commit SHAs with kingkymaru@gmail.com trigger Vercel auto-deployments"). After the re-authored push, Vercel auto-builds + auto-promotes within ~1 min. HABIT: when committing app code for a Vercel-Git project, use the repo's configured `git config user.email` — do NOT override with `git -c user.email=...` or `HERMES`-style identities, or the deploy won't fire. Concretely: prefer plain `git commit` over `git -c user.name=... -c user.email=... commit`. NOTE: this is SEPARATE from the vercel-prod-deploy-verification skill's "Variant B — Vercel account-email mismatch" (which is a Vercel-side *block* on the deploy, shown as a red "Blocked" alert). G31-ADDENDUM is a SILENT webhook no-fire: the deploy simply never starts, no alert. The live signature (stale build, no new Deployments row for your HEAD hash) is the only tell.

- **G32 — MultiLineString route/cable data MUST render as ONE `<Entity>` PER SUB-LINE (each with a SINGLE `<PolylineGraphics>`) — NOT per-segment entities, and NOT multiple polylines inside one entity (the "cables render as disconnected fragments / few cables / wrong places" bug):** three independent mistakes share these symptoms. (0) **THE BIG ONE — Cesium only renders ONE `PolylineGraphics` per `<Entity>`.** Putting several `<PolylineGraphics>` as siblings inside a single `<Entity>` (one per sub-line/branch) means Cesium honors only ONE — the rest are dropped or merged into a single truncated line. This is the #1 cause of "a 14-branch cable (e.g. Kumul) renders as 1 line / few cables" and "cables in wrong places" (the merged line connects branch endpoints in sequence). FIX: render ONE `<Entity>` PER SUB-LINE, each its own single `<PolylineGraphics>`, id `cable-<feature_id>__<i>`, and resolve the parent cable on click via `eid.split('__')[0]` (never `replace(/-\d+$/,'')` — `feature_id` like `kumul-domestic-submarine-cable-system-0` ends in `-0`). (1) **Per-segment entity explosion:** `coordinates.flatMap(line => line.map(([a,b]) => [a,b]))` then one `Entity` per 2-point segment → ~14k micro-entities → fragmented + perf hog. FIX: each sub-line is an ordered point array → draw it as ONE continuous polyline (the per-sub-line Entity pattern), do NOT split into 2-point segments. (2) **Duplicate React key / Entity id (silent route drop):** `properties.id` is often NOT unique (submarinecablemap.com: 21 dups among 718 — `rising-8`, `echo`, `2africa`...). Using it as `key` + `id` → React `Encountered two children with the same key` and DROPS/merges duplicates → routes never render. FIX: key by `properties.feature_id` (unique 718/718), fallback `feature_id || id || name`; same base string for the cable `id` that the click handler splits on `__`. Convert each sub-line's `[lon,lat]` to `Cartesian3.fromDegrees(lon, lat, 0)` in order (NO swap — G33). VERIFIED: Kumul = 14 sub-line entities / 81 pts after the fix (was 1 polyline / 5 pts before). Introspect the live viewer (G38) and count `cable-kumul-*` entities — must equal the source sub-line count (14). Full corrected component + recipe → `references/multilinestring-route-render.md`.

 - **G33 — lat/lon SWAP mirrors every route to the WRONG HEMISPHERE (the "cables look nothing like the real map" bug, invisible to lint/build):** the single most common cause of a submarine-cable / route layer that "isn't the right marine cable lines" even though the data is correct. SYMPTOM: every route renders in the wrong place — e.g. a transatlantic cable like MAREA (Virginia Beach → Bilbao) appears over the South Pacific / off Chile instead of the Atlantic. The whole network is mirrored across the `lon = lat` diagonal. ROOT CAUSE: a transform step flipped GeoJSON `[lon, lat]` → `[lat, lon]` (e.g. `g.coordinates.map(line => line.map(([lon, lat]) => [lat, lon]))`), and then `Cartesian3.fromDegrees(lon, lat, h)` was called on the ALREADY-SWAPPED pair → effectively `fromDegrees(lat, lon)` = swapped. `Cesium.Cartesian3.fromDegrees(longitude, latitude)` takes `(lon, lat)`, so passing the flipped pair routes every point to `(lat, lon)`. This is invisible in `oxlint`/`vite build` — only visible on the globe. FIX: do NOT flip. Pass `[lon, lat]` straight through from GeoJSON; `fromDegrees(lon, lat, height)` is already correct. VERIFY before declaring done (the cheap check that catches it): sanity-check a KNOWN cable's coordinate range from the raw GeoJSON — FEA should be lon 32.5–100.6 / lat 4.4–30.0 (Egypt → SE Asia); MAREA should be lon −76.1..−2.9 / lat 36.8..46.6 (Virginia → Spain). If a transatlantic cable shows latitude ≈ −76 (i.e. near the South Pacific), you swapped. ALSO verify the rendered component reads `fromDegrees(lon, lat)` and is NOT receiving a `[lat, lon]` array. SESSION: this exact swap fired on R-Tessera Submarine Cables 3+ times (the driver flipped, the component didn't un-flip) and was the true root cause behind repeated "doesn't match OSIRIS" complaints — the GeoJSON data was confirmed 1:1 correct vs the live API, so the bug was purely coordinate ordering. Full verified component + coordinate-check recipe → `references/submarine-cable-layer.md`.

 - **G34 — `clampToGround` over ocean VANISHES/MISPLACES; but the SAFE DEFAULT is HEIGHT 0, NOT 50km (the "lines look broken over water" bug):** SYMPTOM: routes render broken, clipped, or float at wrong altitude over ocean on a 3D globe. ROOT CAUSE (1): `PolylineGraphics` with `clampToGround` needs ground primitives + terrain; over oceans there are NO terrain tiles, so Cesium drops/misplaces the line. FIX part 1: drop `clampToGround`. ROOT CAUSE (2) + CORRECTION: a 50 km lift (`fromDegrees(lon,lat,50000)`) was tried as the fix, but the USER OVERRODE it — for a "render the source verbatim, don't change it" mandate the correct FINAL form is HEIGHT 0: `Cartesian3.fromDegrees(lon, lat, 0)`, passing source `[lon,lat]` straight through with NO transform and NO altitude. Height 0 is the most faithful-to-source render and avoids any offset that could read as "wrong place" at some zoom. Use height 0 UNLESS the user explicitly wants a lifted overlay; only reach for a small height if clampToGround-less lines are clipped by terrain in a land-heavy view. PAIR WITH G33: correct coords + height 0 = accurate source-faithful route rendering. SESSION: R-Tessera Submarine Cables — `clampToGround` left cables clipped over water; a 50km lift was applied, then the user said "render source verbatim, don't change it" and the final verified-good form is height 0.

 - **G35 — when replicating a layer the user references by an existing project (OSIRIS), READ THAT PROJECT'S SOURCE first AND RENDER THE SOURCE VERBATIM — do NOT reconstruct from assumptions, and do NOT embellish (the "copy OSIRIS / don't change it" correction):** the user said "look at osiris-master and replicate the submarine cables." Two wrong moves this session: (a) building from a generic live API + my own color/filter guesses instead of reading the reference; (b) imposing my OWN transforms on top of correct data — a 50km altitude lift, a light-gray recolor, an `ignoredColors` filter, a lat/lon flip — each "improvement" introduced a new bug and delayed the fix. The user's explicit mandate: "take the input from source, don't change it first, let it be, the color etc." So the CORRECT workflow: (1) read the reference repo's source for the exact data URL + render path; (2) bundle/load that same data; (3) render it with the MINIMAL transform that Cesium requires (GeoJSON `[lon,lat]` → `fromDegrees(lon,lat,0)`, one Entity per sub-line, unique `feature_id` keys) and NOTHING ELSE — no recolor, no filter, no altitude, no clamp, until the user explicitly asks. CAVEAT: mirror data + render technique faithfully, but DROP any reference REDUCTION (e.g. OSIRIS's `ignoredColors` filter) when the user wants "everything / complete / exactly as published" — this session the user overrode OSIRIS's filter and demanded all 718 routes. RULE OF THUMB: correct-coordinate rendering with zero embellishment beats a "prettier" version that's also wrong. Verify the render against the source by introspecting the live viewer (G38), not by reasoning from the dataset. SESSION: R-Tessera Submarine Cables — first attempts added a filter (127 cables), a swap (wrong hemisphere), a 50km lift; the final correct version is the source verbatim at height 0.

 - **G36 — "count the data, not the screen" is the WRONG verification for a visual-fidelity complaint (the "dont count from the code, count from the image" correction):** when the user says a layer "doesn't look like the reference" or "has fewer cables than OSIRIS," your instinct to diff feature counts (718 vs 717) or grep the GeoJSON is NOT what they're asking. They are judging the RENDERED SURFACE — line density, continuity, placement, contrast — on the actual map/screenshot. This session the user explicitly said "dont count from the code, count from the image, Osiris has a much denser marine lines on the surface" after I answered a Singapore-cable question with raw dataset counts. The dataset count was HIGHER on R-Tessera (718 vs 717) yet the surface looked sparser — because (a) the default 3D globe foreshortens/compresses the same cables vs OSIRIS's flat 2D map, and (b) faint thin lines read as "few." LESSON: for any "looks wrong / doesn't match reference" complaint, verify by INSPECTING THE RENDERED OUTPUT (screenshot, or the live viewer), and treat projection + line-visibility as first-class causes — not just data correctness. If you cannot see the image (vision tool down), SAY SO and reason about the rendered surface from the code path (projection mode, line width/alpha/color, entity count) rather than falling back to dataset counts as "proof" it's fine. The user's screenshot is ground truth; your dataset-count parity is not.

 - **G37 — to match an OSIRIS-style dense flat-map look, DEFAULT the Cesium viewer to 2D (SCENE2D), not 3D globe, and render route lines fully opaque + slightly thicker:** OSIRIS (and most 2D web-map reference apps) draw cable/route networks on a flat projection where every line is fully spread out and visible. A Cesium 3D globe foreshortens the same geometry near the limb and overlaps many lines, so even a correct 718-cable network reads as sparse. FIX: default `scene` state to `'2d'` (morph via `viewer.scene.morphTo2D(0)` in the useCesium bridge — see base-layer section; call exactly ONE morph, never both), and set cable/route polylines to near-opaque (`alpha 1.0`) at `width >= 2.0` in a high-contrast color so the full network reads as densely as the reference. SESSION: R-Tessera Submarine Cables — switching default `useState('3d')` → `useState('2d')` + alpha 0.9→1.0 + width 1.6→2.0 made the surface density match OSIRIS; before that the user perceived "far fewer cables" purely from the 3D projection.

 - **G41 — Google Photorealistic 3D Tiles are SCENE PRIMITIVES + need a PUBLIC env key (the "one token-free exception" pattern):** adding Google's photorealistic meshes is the ONE sanctioned exception to R-Tessera's token-free Cesium design. Mechanics: (1) `Cesium3DTileset.fromUrl('https://tile.googleapis.com/v1/3dtiles/root.json', { maximumScreenSpaceError: 16 })` — the tileset is added to `viewer.scene.primitives`, NOT as imagery and NOT as an `<Entity>`; (2) `GoogleMaps.defaultApiKey` must be set from `VITE_GOOGLE_MAPS_API_KEY` (Cesium attaches it to tile requests); (3) they render ONLY on a globe, so force `scene = '3d'` (morph via the bridge) when the toggle turns on; (4) lazy-load — build + `primitives.add` only on enable, `primitives.remove` on disable/unmount, with the usual `isDestroyed?.()` + try/catch guards (G28); (5) SECURITY: a `VITE_` key is inlined into the client bundle, so the Google Cloud key MUST carry an HTTP-referrer restriction (`r-tessera.vercel.app` + `localhost`) or strangers burn your quota. If the key is missing/blocked, surface via an error callback and DISABLE the control row (graceful, no crash). Full recipe + builder → `references/google-3d-tiles.md`. SESSION: this exact pattern shipped on R-Tessera (Google 3D layer added, commit `e90868a`), oxlint 0/0 + vite build OK.

 - **G41-ADDENDUM — the photorealistic mesh is HIDDEN if you DON'T strip the flat imagery, AND it must be a BASE-MAP button, not a data-overlay toggle (the "toggle on → nothing different" bug):** TWO failures this session after G41 shipped. (A) **Mesh-under-imagery:** G41's first cut lazily added the tileset to `primitives` but the bridge's raster-swap effect STILL re-added the Esri/OSM `ImageryLayer` on every render — so the photorealistic 3D mesh rendered *underneath* the flat draped Esri satellite and the globe looked identical ("I toggle Google 3D and it shows no difference"). FIX: when Google is the active base, set `rasterLayer = null` in the memo AND in the imagery-swap effect, remove ALL imagery layers and only add a raster layer when `raster !== 'google3d'`. The mesh and the flat imagery are MUTUALLY EXCLUSIVE — never both present. (B) **Wrong control location:** a Photorealistic-3D-Tiles layer is a BASE MAP (a photorealistic globe), NOT a situational data overlay — putting its toggle in the Box-2 "Data Overlays" panel was a model error. The user corrected: it belongs as a third button in the bottom-left BASE-MAP selector (next to "Satellite Esri"), i.e. a third `RASTER_MODES` entry `{ id: 'google3d', label: 'Google', sub: '3D' }`. Selecting it sets `raster='google3d'` AND `scene='3d'` (force globe), and triggers the lazy `Cesium3DTileset` build in the bridge. Remove any Google-3D row from the data-overlay panel. (C) **Visibility scale:** even with the mesh unmistakably loading, at the world-altitude default camera the photorealistic tiles are sub-pixel — they only "pop" when you ZOOM INTO A CITY. If a user says "still nothing" while zoomed out, that is expected, not a bug. SESSION: this exact "nothing different" was the G41-ADDENDUM bug on R-Tessera; fixed by `rasterLayer = null` when google + stripping all imagery, moving the control to the base selector, and confirming the local `.env.local` had NO key (grep `VITE_GOOGLE_MAPS_API_KEY` returned 0 — the disabled-button + missing-key combo is the first thing to verify when "Google 3D does nothing"). Verified green (oxlint 0/0, vite build OK).

 - **G40 — cable/route overlay COLOR must stay RECESSIVE on a sea basemap (the iterative-color-churn correction):** the founder cycled the Submarine Cables color light-gray `#c9ccd0` → OSIRIS blue `#1976D2` → light gray → **muted dark slate `#3a4a57`** before settling. The durable preference is NOT any single hex — it's the INTENT: the cable web must NOT overpower other map indicators (earthquakes / volcanoes / weather). RULE for any dense route overlay on water: pick a tone that is **darker than light-gray (less glare) but LOW-CONTRAST against the sea** — a muted dark slate/teal reads as a quiet line; avoid bright high-contrast blues and avoid gray lighter than the water (it glares). Let the user choose the exact shade, but encode the recessive intent. SESSION: R-Tessera — light gray was "too visible"; dark slate `#3a4a57` was accepted. See `references/submarine-cable-layer.md` "Color" note for the final guidance + full renderer.

 - **G42 — Cesium in Next.js (non-Resium) breaks the production bundle with an illegal `\0`/octal escape (the "green build, blank page / SyntaxError" bug):** when you `import { Viewer } from 'cesium'` + the widgets CSS inside a **Next.js** route, `next build` SUCCEEDS but the browser throws `SyntaxError: The only valid numeric escape in strict mode is '\0'` (or `Octal escape sequences are not allowed in template strings`) and the route's chunk never parses → React doesn't hydrate → blank page / "click does nothing". ROOT CAUSE: Cesium's npm package embeds its wasm as a base64 string containing `\0` bytes; inside a **template literal** `\0` is illegal in strict-mode ES, and Next's minifier preserves it (Vite/esbuild are fine — that's why the Resium path here works). **DIAGNOSE before shipping:** after `next build`, run the `node --check` loop over `.next/static/chunks/*.js` (see `references/cesium-nextjs-cdn-load.md`) — only the Cesium chunk fails; "build passed" is NOT sufficient. **FAILED fix:** `transpilePackages: ['cesium']` does NOT fix it (it's the wasm/base64 `\0`, not transpilation). **WORKING fix:** do NOT statically import Cesium — inject `<script src="https://cdn.jsdelivr.net/npm/cesium@<ver>/Build/Cesium/Cesium.js">` + the widgets CSS at runtime in a `useEffect` and use the global `window.Cesium` (`const C = await loadCesium(); new C.Viewer(...)`). Offline variant: `cp -r node_modules/cesium/Build/Cesium public/cesium` and load from `/cesium/...`. Either way, never let Next's bundler process the Cesium package. SESSION: this exact break fired on LUNAV's `/project/[id]/home` Cesium globe; fixed by the CDN runtime-load; verified by `node --check` on all chunks (ALL PARSE OK). Full recipe → `references/cesium-nextjs-cdn-load.md`.

 - **G44 — toggling a Cesium `<Viewer>` and a sibling page/section in the SAME conditionally-rendered React branch crashes on unmount (`TypeError: t.remove is not a function` at the Cesium `viewer.destroy()` path):** when `view==='globe'` renders `<GlobeView>` (a `<Viewer>`) and `view==='labs'` renders a different component in the SAME tree (e.g. `{view==='globe' && <GlobeView/>} {view==='labs' && <LabsPage/>}`), switching `view` unmounts the globe DURING the same commit as the sibling mounts — React interleaves Cesium's `viewer.destroy()` (which touches `.remove()` on already-removed entities) with the new render, and Cesium throws. SYMPTOM: clicking the in-app "Labs" button from inside the globe whitescreens (blank page, no stack). FIX (preferred, also enables a standalone page): **don't co-locate the globe and the sibling in one conditional tree.** Two verified fixes: (a) **Lagged unmount** — keep `globeAlive` true for one macrotask after `view` flips to 'labs' (`setTimeout(()=>setGlobeAlive(false),0)`) so the globe tears down ALONE, after Labs has painted; or (b) **separate route / separate deploy** — make the sibling its OWN page (its own entry/build) and link to it (`<a href>`), so the whole globe React root is replaced natively and Cesium never races a sibling. SESSION: this exact `t.remove is not a function` crash fired when LunaV Labs was an in-app sub-view of R-Tessera; fixed first by lagged-unmount, then by extracting Labs to its OWN Vercel project (`lunav-labs`) — which also gave the cleaner "standalone landing page" the founder wanted. The standalone-route fix is the durable one for any "globe + a non-globe page in the same app" requirement.

 - **G45 — SCROLL-DRIVEN GLOBE STAGE (scrollytelling) is a real, reusable pattern:** a fixed Cesium `<Viewer>` behind a scrolling foreground doc, camera eased between per-section `focus` poses by scroll progress. Verified on LUNAV Labs (`lunav-labs`). Core recipe: (1) globe in `.lv-stage { position:fixed; right:0; width:58%; height:100vh }` ALWAYS mounted (never in a conditional branch — see G44); (2) dim veil + scanline over it (`pointer-events:none`; `filter: brightness(0.72)`) so foreground copy stays crisp; (3) `App` tracks `scrollTop/(scrollHeight-clientHeight)` → `progress 0..1`, passes to stage; (4) stage maps progress → nearest section index → `focus {lon,lat,height}`, then LERPS `viewer.camera.setView` every `requestAnimationFrame` (smooth, not snappy); (5) per-section reveal via IntersectionObserver adding `.in` (ghost name slides, image flies from side, text fades, staggered). SELF-CONTAINED layers ON (no Supabase): bundle `submarine-cables.json` (G30) + live USGS quakes (keyless) + local pins from `projects.js`. Full recipe → `references/scroll-driven-globe.md` (NOTE: if that file is absent in your skill install, the essentials are: fixed-always-mounted stage, progress→focus lerp, IntersectionObserver `.in` reveals). SESSION: shipped live at lunav-labs.vercel.app with the real R-Tessera globe + cables + quakes + pins as backdrop.

 - **G46 — GLOBE FLICKERS during scroll = TWO COMPETING CAMERA WRITERS (per-frame `setView` vs Cesium render loop):** the naive scroll-globe runs its OWN `requestAnimationFrame` loop calling `camera.setView(...)` every frame, while Cesium's internal render loop ALSO touches the camera each frame. Two writers, out of sync → judder/flicker on every scroll tick. FIX (steady): drive the camera from Cesium's OWN clock — `viewer.clock.onTick.addEventListener(cb)` + `viewer.clock.shouldAnimate = true`. The clock is GPU-synced, so the `setView` lands exactly when the renderer draws → no collision. Do BOTH dolly-out + spin inside the ONE `onTick` callback: lerp height/pitch/lat toward the scroll target at ~0.05, advance `heading` by a fixed `SPIN` ≈ 0.025°/tick for a constant axial spin. NEVER also call `flyTo` on progress change — its timed animation fights the per-tick `setView` and re-introduces judder. SINGLE setView per tick. Canonical component → `references/scroll-driven-globe-steady.md`. SESSION: this flicker fired on LUNAV Labs; fixed by moving the camera write into `onTick` + dropping the custom RAF + the flyTo.

 - **G47 — GLOBE BLINKS between SECTIONS = React RE-MOUNTING the `<Viewer>` (unmemoized child + prop-driven re-render):** the scroll-globe sits behind a long foreground doc; if `App` calls `setProgress` on every scroll event and `<GlobeStage progress={progress} />` is NOT memoized, every scroll re-renders `App` → re-renders `GlobeStage` → resium tears down + rebuilds the WebGL `<Viewer>` → the canvas FLASHES at each section change. (Distinct from G46's per-frame judder — this is a hard re-init flash on section boundaries.) FIX: (1) `export default memo(GlobeStage)` so parent re-renders never touch it; (2) pass scroll progress via a `ref`, NOT a changing prop — `App` writes `progressRef.current = p` (no re-render) and `GlobeStage`'s `onTick` reads `progressRef.current` each frame; (3) throttle the scroll handler with `requestAnimationFrame`. Verify in-browser: scroll section 1→last and confirm the Cesium `<canvas>` is the SAME DOM node (`sameCanvasNode: true`) — proves no re-mount. SESSION: this blink fired on LUNAV Labs (down-arrow/wheel between pages); fixed by `memo` + `progressRef` + throttled scroll; confirmed via same-canvas-node check. NAVIGATOR DEAD-BUTTON cousin: if a floating up/down navigator calls `el.scrollIntoView()` per section index, EVERY section must register its ref incl. the LAST (e.g. CTA footer) — forgetting `ref={el=>(sectionsRef.current[N]=el)}` makes the last down-click a silent no-op ("page 6→7 does nothing").

 - **G43 — `LEFT_DOUBLE_CLICK` input action fires UNRELIABLY in Cesium's ScreenSpaceEventHandler, and the `selectedEntity` deferred-selection race makes single-click feel like "first click does nothing, second click acts" (the "open node detail" bug):** two distinct failure modes bit the R-Tessera Projects panel this session. (A) **Double-click trap:** binding `handler.setInputAction(onClick, ScreenSpaceEventType.LEFT_DOUBLE_CLICK)` (action code 8) to open a detail panel produced a panel that NEVER opened — Cesium's default double-click also triggers entity tracking and the custom double-click handler wasn't reliably invoked in this pipeline. SYMPTOM: "double-click does nothing." FIX: use `LEFT_CLICK` (action 1) instead — it always fires. (B) **Deferred selection race:** an earlier single-click handler read `viewer.selectedEntity` inside the click callback. Cesium only POPULATES `selectedEntity` AFTER the click completes, so the FIRST click selected the entity (handler saw `null`), and only the SECOND click found the already-selected entity. SYMPTOM: "first click nothing, second click navigates." FIX: do NOT use `viewer.selectedEntity` for immediate picks — call `viewer.scene.pick(click.position)` INSIDE the click handler; it returns the picked object synchronously from the click coordinates, no selection round-trip. Reliable id extraction from the PickedObject (defensive, since Cesium wraps the Entity differently for point/label/primitive):
  ```js
  const resolveNodeId = (picked) => {
    const candidate = picked?.id?.id ?? picked?.id ?? picked?.primitive?.id
    let str = candidate
    if (typeof str !== 'string' && str?.id) str = str.id   // normalize nested Entity wrapper
    if (typeof str === 'string' && str.startsWith('node-')) return str.replace('node-', '')
    return null
  }
  handler.setInputAction((click) => {
    if (!show || !click?.position) return
    const picked = viewer.scene.pick(click.position)
    const nodeId = resolveNodeId(picked)
    if (nodeId) { const n = nodes.find(x => x.id === nodeId); if (n) openDetail(n) }
  }, ScreenSpaceEventType.LEFT_CLICK)
  ```
  (C) **Camera lock after entity click:** Cesium's default double-click sets `viewer.trackedEntity`, pinning the camera onto the entity and freezing globe navigation centered on it. Even after switching to single-click, if double-click is ever reachable it locks. GUARD: reset every frame in the `useCesium` bridge:
  ```js
  const release = () => { if (viewer.trackedEntity) viewer.trackedEntity = undefined }
  const handle = viewer.scene.preRender.addEventListener(release); release()
  // cleanup: handle.remove()
  ```
  SESSION: this exact combination (double-click-no-open + deferred-selection race + camera-lock) fired on R-Tessera's `ProjectNodes.jsx`; fixed by LEFT_CLICK + immediate `scene.pick` + `trackedEntity` preRender guard, vite build OK. This supersedes G17's "use LEFT_CLICK + scene.pick" advice — now with the WHY (double-click unreliable, selectedEntity deferred) and the robust id walk. Full verified `ProjectNodes` click→detail code + panel-placement notes → `references/cesium-entity-click-detail.md`.

 - **G38 — INTROSPECT THE LIVE VIEWER to get ground truth when "cables look wrong" (the decisive diagnostic, beats guessing):** when the user insists routes are in the wrong place / missing but your code looks correct, STOP reasoning from the source data and INTERROGATE the actual rendered scene. Expose the viewer temporarily: in the `useCesium` bridge add `if (typeof window !== 'undefined') window.__viewer = viewer` (DEBUG — remove after). Then in the browser `console` evaluate against `window.__viewer`:
  (a) **entity count + scene mode** — `v.entities.values.filter(e=>String(e.id).startsWith('cable-')).length` (should equal source feature count, e.g. 718) and `v.scene.mode` (2 = SCENE2D, 3 = SCENE3D);
  (b) **NaN check** — for each cable entity, `g.positions.getValue(v.clock.currentTime)` and count `isNaN(p.x||p.y||p.z)` (0 = no broken geometry);
  (c) **coordinate proof** — pick a KNOWN cable by id (`v.entities.getById('cable-marea-0')`), read its positions, convert ECEF Cartesian → lon/lat in Node (`x,y,z` → `r=√(x²+y²)`, `lat=atan2(z, r(1-e²))` iterate, `lon=atan2(y,x)`, ×180/π) and compare to the source. SESSION: this proved MAREA renders at exactly the source coords (Virginia Beach → Bilbao) — confirming the code was correct and the "wrong cables" the user saw were a STALE CACHE (G39), not a code bug. This introspection is the single most reliable way to tell "code is right, something else is wrong" from "code is wrong" — use it BEFORE more code changes.

 - **G39 — "cables in wrong places / missing" with VERIFIED-CORRECT CODE is usually a STALE CACHE, not a bug (the deploy-vs-reality trap):** if G38 shows the right entity count, right scene mode, 0 NaN, and correct coordinates for a known cable, then the code IS correct — and what the user is looking at is an OLD BUILD. Causes: (1) the browser cached the previous (buggy) JS bundle — fix with a HARD refresh (Cmd+Shift+R / private window); (2) Vercel's edge served a stale deployment (compare the live `index.html` build hash from `curl -s https://<site>/ | grep assets/index-` against your local `npm run build` hash — mismatch = stale); (3) an intermediate commit with the bug got cached between your fix and the user's view. DO NOT keep layering fixes on top of a verified-correct render — that's how this session burned several cycles. Instead: confirm correctness via G38, then tell the user to hard-refresh and verify the live build hash matches. Only return to code changes if G38 shows an actual discrepancy (wrong count, NaN, or a known cable at the wrong lon/lat).

## Diagnostic ladder — "this map layer looks wrong / doesn't match the reference"
When the user says a route/cable/overlay "isn't right" or "doesn't look like the reference," FIRST get eyes on the RENDERED SURFACE — open the app, or ask the user for a screenshot, or (if vision is available) analyze the screenshot. Do NOT start by computing dataset counts and declaring parity — the user is judging the pixels, not the GeoJSON. (G36: this session the user said "dont count from the code, count from the image.") Then run this ORDERED checklist (each step is a gotcha already in this skill). Do NOT start by assuming the dataset is stale ("data drift") — that was a repeated misdiagnosis this session:
0. **Introspect the live viewer FIRST (G38):** expose `window.__viewer`, then in the browser console count cable entities (`v.entities.values.filter(e=>String(e.id).startsWith('cable-')).length` — should equal source count, e.g. 718), read `v.scene.mode` (2=2D, 3=3D), check for NaN positions, and convert a KNOWN cable's ECEF positions back to lon/lat to compare against the source. If the count is right, mode is right, 0 NaN, and the known cable matches the source → the CODE IS CORRECT and the user is seeing a STALE CACHE (G39): tell them to hard-refresh and verify the live build hash. Only proceed to code fixes if G38 shows a real discrepancy.
1. **Data drift?** Re-fetch the live source and diff `feature_id`/feature count vs the bundled file (`node -e` comparing `Set` of ids). If 0 drift, the data is fine → step 2. (submarinecablemap.com 718 features matched 1:1 this session.)
2. **Coordinate swap? (G33)** — the #1 cause of "wrong place / mirrored." Check a KNOWN feature's lon/lat range from raw GeoJSON (FEA: lon 32.5–100.6 / lat 4.4–30.0; MAREA: lon −76..−3 / lat 36.8–46.6). If a transatlantic cable shows lat≈−76, you flipped `[lon,lat]`→`[lat,lon]`. FIX: pass `(lon,lat)` straight to `fromDegrees`.
3. **Fragmented / disconnected? (G32)** — one Entity per feature, continuous PolylineGraphics per sub-line; unique `feature_id` keys (not duplicate `properties.id`). Console `same key` errors = duplicate ids dropping routes.
4. **Broken over ocean / wrong altitude? (G34)** — drop `clampToGround`; lift to `fromDegrees(lon,lat,50000)`.
5. **Looks too sparse / fewer than reference?** — usually VISIBILITY + PROJECTION, not count. Verify the rendered count matches the source count; then check (a) color/alpha/width — faint thin lines (e.g. `#9aa0a6` @0.7α, 1.6px) read as "few"; brighten (e.g. `#c8ccd0` @1.0α, 2.0px); and (b) PROJECTION — a 3D globe foreshortens/compresses the same cables vs a flat 2D map (G37); default the viewer to 2D (SCENE2D) to match a 2D-reference density. Also: before the G33 fix, mirrored cables sat in empty ocean regions, so the visible area looked sparse.
6. **CORS? (G30)** — if the layer shows "feed offline" but `curl` works, bundle the data into `public/`.
Only after all six pass should you suspect the reference itself differs (region-filtered subset, etc.).

## Base-layer + scene-mode switching (the "base map selector" pattern)
When you need a user-facing base-map switcher (e.g. OSIRIS-style Map / Satellite +
2D / 3D), build it from TWO independent controls — never a single `<Viewer>` prop:

- **RASTER swap** — in a `useCesium` child bridge, remove all existing
  `viewer.imageryLayers` and add the chosen `ImageryLayer`. Build the layer ONCE
  via `useMemo` (see G7-ADDENDUM) so it isn't reconstructed every render.
  Token-free options that work with no Ion token:
  - OSM: `new OpenStreetMapImageryProvider({ url: 'https://tile.openstreetmap.org/' })`
  - Esri sat: `new UrlTemplateImageryProvider({ url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', maximumLevel: 19 })`
- **SCENE swap** — `viewer.scene.morphTo2D(0)` / `viewer.scene.morphTo3D(0)`
  (duration 0 = instant). Read current mode from `viewer.scene.mode` and morph
  ONLY when it differs from the target.
  **GOTCHA (double-morph bug):** do NOT call both `morphTo2D` and `morphTo3D` in one
  effect (a "reset-then-set" pattern) — it double-morphs and leaves the globe in the
  wrong mode. Branch on the target `SceneMode` and call exactly ONE morph. Do not
  set `sceneMode={...}` on `<Viewer>` (see G14); morph imperatively from the bridge.
  **LAYER EXTENSION — Google Photorealistic 3D Tiles (G41/G41-ADDENDUM):** a third,
  optional base-layer-style toggle adds Google's photoreal mesh. It is NOT an
  imagery layer and NOT an `<Entity>` — it is a `Cesium3DTileset` added to
  `viewer.scene.primitives`, lazy-built only on enable, env-keyed via
  `GoogleMaps.defaultApiKey`. See the G41 pitfall + `references/google-3d-tiles.md`
  for the full recipe. Force `scene='3d'` when it turns on (tiles render on a globe
  only). **CRITICAL (G41-ADDENDUM):** Google 3D is a BASE MAP — add it as a third
  `RASTER_MODES` entry (`{ id: 'google3d', label: 'Google', sub: '3D' }`), NOT a
  data-overlay toggle. When `raster === 'google3d'`, set `rasterLayer = null` in the
  memo, remove ALL `viewer.imageryLayers`, and drive the tileset build from the
  `raster` value (not a separate `showGoogle3D` flag). The photorealistic mesh and
  the flat imagery are MUTUALLY EXCLUSIVE — if you leave the Esri/OSM imagery on, the
  mesh renders *underneath* it and the globe looks unchanged ("toggle does nothing").
- Keep `<Viewer baseLayer={...}>` as a token-free DEFAULT (memoized) so the globe
  never paints black before the bridge swaps it.

Full working recipe (verified green on a R-Tessera rebuild, vite + react 19 +
cesium 1.143):

```js
// config — two independent halves
import { ImageryLayer, OpenStreetMapImageryProvider, UrlTemplateImageryProvider, SceneMode } from 'cesium'

export const RASTER_MODES = [
  { id: 'map', label: 'Map', sub: 'OSM' },
  { id: 'satellite', label: 'Satellite', sub: 'Esri' },
]
export const SCENE_MODES = [
  { id: '3d', label: '3D', sub: 'Globe' },
  { id: '2d', label: '2D', sub: 'Flat' },
]
export function buildRasterLayer(rasterId) {
  try {
    if (rasterId === 'satellite') {
      return new ImageryLayer(new UrlTemplateImageryProvider({
        url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        maximumLevel: 19, credit: '© Esri, Maxar, Earthstar Geographics',
      }))
    }
    return new ImageryLayer(new OpenStreetMapImageryProvider({ url: 'https://tile.openstreetmap.org/' }))
  } catch (err) { console.warn('[base] raster build failed:', err); return undefined }
}

// bridge — swap imagery + morph scene (lives INSIDE <Viewer>)
function ViewerBridge({ raster, scene, viewerRef }) {
  const cesiumContext = useCesium()
  const viewer = cesiumContext?.viewer
  const rasterLayer = useMemo(() => buildRasterLayer(raster), [raster])
  useEffect(() => {
    if (!viewer || viewer.isDestroyed?.() || !rasterLayer) return
    try {
      const layers = viewer.imageryLayers
      for (let i = layers.length - 1; i >= 0; i--) layers.remove(layers.get(i))
      viewer.imageryLayers.add(rasterLayer)
    } catch (err) {
      console.warn('[base] raster swap skipped (viewer not ready):', err?.message)
    }
  }, [viewer, rasterLayer])
  useEffect(() => {
    if (!viewer || viewer.isDestroyed?.()) return
    try {
      const mode = scene === '2d' ? SceneMode.SCENE2D : SceneMode.SCENE3D
      if (viewer.scene.mode !== mode) {
        if (mode === SceneMode.SCENE2D) viewer.scene.morphTo2D(0)
        else viewer.scene.morphTo3D(0)   // call EXACTLY ONE morph — never both
      }
    } catch (err) {
      console.warn('[base] scene morph skipped (viewer not ready):', err?.message)
    }
  }, [viewer, scene])
  useEffect(() => {
    if (!viewer || viewer.isDestroyed?.()) return
    viewerRef.current = viewer
  }, [viewer, viewerRef])
  return null
}
// NOTE: the `isDestroyed?.()` + try/catch guards are the G28 defense-in-depth
// fix — WITHOUT them a StrictMode double-mount (or HMR) touches a destroyed
// viewer and whitescreens the globe. Keep them even after StrictMode is removed.
```
Selector: two `role="radiogroup"` groups (raster | scene) of small buttons,
`aria-checked` active state, docked `position:fixed; left/bottom`, `pointer-events:auto`
over a `pointer-events:none` globe container (see G18).

## UI/UX delivery discipline (STANDING — load for any visual pass)
The user runs a professional-UX bar on this dashboard. For EVERY UI/UX change,
before reporting done: (1) RE-LOOK at the WHOLE layout — ask explicitly "any
overlap? any oddly-placed buttons/placeholders?" and only claim done if ~90%
confident it's clean; (2) if unsure, compare against known-good references
(other pages / past work) rather than shipping; (3) deliver in SMALL CHUNKS —
one feature/behavior per turn, never batch many steps into one reply (batching
degrades quality and burns tokens); (4) for a simple decision you already asked
the user before, REUSE that answer from memory instead of re-asking — only ask
when the trade-off is genuinely new. Hold `oxlint` until the user eyeballs the
canvas (visual-approval gate), but always run `npm run build` to prove it
compiles, then `rm -rf dist`. This standing loop was made explicit by the user
on 2026-07-18 and must run after every cosmetic/UX edit, not just once.

## Templates
- `templates/supabaseClient.js` — null-safe Supabase client from VITE_ env.
- `templates/ErrorBoundary.jsx` — class-based boundary for Resium.
- `templates/full-bleed.css` — App.css snippet overriding the #root column.
- `templates/TelemetryTracker.jsx` — KNOWN-GOOD `useCesium` child bridge:
  live camera telemetry (postRender + camera.moveEnd) + exposes viewer to an
  outside `viewerRef` for flyTo. Drop inside `<Viewer>`.

## Scripts
- `scripts/probe-vesselapi.sh` — live-feed diagnostic: GETs the same proxy+path
  the app uses, counts records vs distinct mmsi vs valid coords to prove "few
  markers = correct dedup" (G26). Run from the repo root with the dev server up.

## References
- `references/multilinestring-route-render.md` — G32: rendering `MultiLineString` route/cable networks in Resium — the CRITICAL "one `<Entity>` per sub-line (Cesium honors only ONE polyline per entity)" collapse bug, plus per-segment fragmentation and duplicate-`feature_id` key drops, with the verified-correct `CableEntities.jsx` (Kumul = 14 sub-line entities / 81 pts).
- `references/submarine-cable-layer.md` — G32/G33/G34/G35/G40: the FINAL verified-good Submarine Cables recipe (one Entity per sub-line, height 0, source verbatim, recessive color `#3a4a57`), with the corrected `CableEntities.jsx` + `eid.split('__')[0]` click-resolve. NOTE: this file was rewritten this session to fix a STALE pre-G32 renderer example.
- `references/submarine-cable-layer.md` — G33 + G34: the full Submarine Cables / marine-line layer recipe (keyless submarinecablemap.com bundle, one-Entity-per-cable, NO lat/lon swap, height-offset instead of clampToGround) with the verified `CableEntities.jsx` + a coordinate-range sanity check to catch the mirror bug.
- `references/submarine-cable-layer-verification.md` — G33/G34/G38/G39: the viewer-introspection recipe (expose `window.__viewer`, count entities / scene.mode / NaN, convert ECEF→lon/lat to prove a known cable renders at source coords), the ECEF→ll Node converter, and the stale-cache (G39) disambiguation. Use this BEFORE more code changes when "cables look wrong."
- `references/google-3d-tiles.md` — G41: the lazy Google Photorealistic 3D Tiles recipe (scene primitive, env-keyed `GoogleMaps.defaultApiKey`, force-3D, graceful degrade, public-key referrer restriction). The one token-free exception.
- `references/cesium-nextjs-cdn-load.md` — G42: Cesium inside a **Next.js** route breaks the production bundle (illegal `\0`/octal escape in Cesium's wasm-as-base64 → browser SyntaxError, blank page). The `node --check` chunk loop to prove it + the CDN/static runtime-load fix (do NOT statically import Cesium in Next).
- `references/cesium-threejs-integration.md` — cross-engine digital-twin integration: Cesium globe (geo-index master) ↔ Three.js detail viewer (inspection) — the "link don't embed" pattern, coordinate-space incompatibility, asset→project pointer table. Use for "merge / integrate our map platform with our 3D-inspection app" questions.
- `references/strictmode-cesium-crash.md` — G28 (StrictMode → Cesium "object destroyed" crash + `isDestroyed()` bridge hardening) and G29 (surfacing swallowed React render errors via a temp `main.jsx` `window.onerror` patch).
- `references/cors-blocked-geo-feeds.md` — G30: diagnosing + fixing CORS-blocked browser `fetch` of third-party geo/JSON feeds (submarinecablemap, etc.) by bundling into `public/`; includes the keyless submarine-cable data source + MultiLineString→Cesium polyline recipe.
- `references/vercel-push-deploy.md` — G31 + G31-ADDENDUM: verify a GitHub push actually deployed (live-signature probes) AND the silent webhook no-fire when the commit author email mismatches the Vercel-expected identity; re-author + force-with-lease fix.
- `references/cors-blocked-geo-feeds.md` — G30: diagnosing + fixing CORS-blocked browser `fetch` of third-party geo/JSON feeds (submarinecablemap, etc.) by bundling into `public/`; includes the keyless submarine-cable data source + MultiLineString→Cesium polyline recipe.
- `references/camera-init.md` — verified camera framing + zoom-clamp + home-button-override recipe for the `useCesium` bridge (G22, G22-ADDENDUM).
- `references/flyout-state-reset.md` — canonical "reset drill-down on open + explicit back chevron" recipe for always-mounted flyout panels (G23).
- `references/scroll-driven-globe-steady.md` — G46/G47 canonical: steady (no-flicker, no-blink) scroll-globe GlobeStage.jsx + verification.
- `references/mckinsey-narrative-skeleton.md` — 7-beat McKinsey scrollytelling skeleton + sourced ROI figures + LUNAV Labs anatomy.

## Workflow: verify user-prescribed framework APIs before applying (G12)
When the user hands a "copy-paste this exact fix" blueprint that names a
framework prop/API, VERIFY it against the installed package before applying —
users (and LLM-drafted blueprints) routinely prescribe APIs that don't exist in
the installed version. This session: a "use `<Viewer onReady>`" blueprint was
prescribed twice; resium 1.24 `<Viewer>` has no `onReady` (would be a silent
no-op), and the blueprint also used `setCameraLat`/`setCameraLng` while the file
used a single `camPos` state, and `scene.cameraMoveEnd` (undefined — events are
on the Camera). Procedure when a blueprint is given:
  1. grep the installed lib source for the named prop/hook (e.g.
     `search_files node_modules/resium/src/Viewer/Viewer.ts` for `onReady`;
     `search_files` the package's `*.d.ts` for the exported hook).
  2. If the prop/hook doesn't exist or doesn't fit the file's existing state
     shape, DO NOT apply verbatim — adapt to the verified-correct equivalent
     (here: `useCesium` child component instead of `onReady`; `setCamPos`
     instead of two setters).
  3. Name the trap explicitly in your reply ("sharp catch") so the user sees
     why the prescribed line was rejected — don't silently substitute.
  SESSION EXAMPLE (this fix): the prescribed `TelemetryTracker` blueprint used
  `Cesium.Cartographic`/`Cesium.Math` (no `Cesium` namespace imported → would
  throw `ReferenceError`), `setCameraLat`/`setCameraLng` props (the file's HUD
  actually uses a single `camPos` state via `setCamPos`), and `camera.changed`
  for telemetry. Adapted to verified-correct equivalents: named imports
  `Cartographic` + `Math as CesiumMath`, kept `setCamPos({ lat, long })`, and
  used `camera.changed` per the user's explicit preference with the
  `cesiumContext?.viewer` guard (see G13).

  **PREMISE CHECK (extends step 1):** before you even reach adaptation, verify the
  *claimed bug source actually exists in the file*. This session the user ordered
  "remove `sceneMode={SCENE2D}` / set `globe={true}`" to un-flatten the globe — but
  a repo-wide grep showed NO `sceneMode`, `globe`, or `mapProjection` override
  anywhere; Cesium already defaults to `SCENE3D`. Editing against a non-existent
  cause wastes a turn and can introduce no-ops. Procedure: grep the project for
  the exact token the user blamed; if it's absent, say so up front ("sharp catch:
  there's no 2D lock to remove") and pivot to the real root cause (e.g. camera
  distance, `scene3DOnly` not set) instead of applying the prescribed prop.

## Verification
- **Structural / logic fixes** (unsafe `useCesium()` extraction, wrong import,
  event-wiring bug, ref/prop mismatch): run BOTH `npm run lint` (oxlint) and
  `npm run build` (vite build) as the gate — green build proves imports/JSX/
  wiring compile. This session: oxlint 0 errors + `vite build` transformed 63
  modules with no errors, confirming the `cesiumContext?.viewer` fix.
- **Visual / UI changes** (layout, colors, HUD styling, glassmorphism): the
  lint/visual pass is a visual-approval gate — hold `oxlint` until the user
  eyeballs the canvas. Still run `npm run build` to confirm it compiles.
- Cesium render + live Supabase only run in-browser via `npm run dev`, so pair
  build-green with a manual dev check. After `npm run build`, `rm -rf dist` so
  the build output doesn't pollute a commit (`git check-ignore dist`).
