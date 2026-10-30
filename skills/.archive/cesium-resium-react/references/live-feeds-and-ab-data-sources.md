# Live feeds & A/B data-source patterns (Cesium/Resium)

Two reusable techniques from wiring AISStream (live WebSocket push) as a
selectable alternative to VesselAPI (poll of a 4h-historical dedup window) in a
live-vessel Cesium layer.

## 1. Imperatively-managed entities (NOT resium `<Entity>` JSX)

**Problem:** A live/polled feed re-adds an entity by id on every refresh.
resium's declarative `<Entity id={x}>` re-mounts and throws
`Entity with id X already exists in this collection` for vessels that persist
between refreshes.

**Fix:** Manage entities imperatively via `viewer.entities` inside a `useEffect`
keyed on the data array. `getOrCreateEntity(id)` is idempotent and never throws;
prune any entity whose id dropped out of the latest feed.

```jsx
useEffect(() => {
  if (!viewer) return
  if (!vessels.length) {
    viewer.entities.values
      .filter((e) => typeof e.id === 'string' && e.id.startsWith('vessel-'))
      .forEach((e) => viewer.entities.remove(e))
    return
  }
  const seen = new Set()
  for (const v of vessels) {
    const e = viewer.entities.getOrCreateEntity(v.id)
    e.position = Cartesian3.fromDegrees(v.lon, v.lat)
    e.point = new PointGraphics({ pixelSize: 9, color: LIVE })
    // e.polyline / e.label ...
    seen.add(v.id)
  }
  viewer.entities.values
    .filter((e) => typeof e.id === 'string' && e.id.startsWith('vessel-') && !seen.has(e.id))
    .forEach((e) => viewer.entities.remove(e))
}, [vessels, viewer])
```

Layer must render `null` (not mount the entities effect) when the toggle is off,
so the clear path runs and the scene graph stays clean.

## 2. Live-WebSocket-vs-poll A/B data source

**Pattern:** two providers feed ONE entity layer. The user flips the source at
runtime; the layer's data-gathering `useEffect` branches on a `provider` state
(`'vesselapi'` poll vs `'aisstream'` push) and re-subscribes when it changes.

Key rules:
- **Share one governance budget.** Register both providers (e.g.
  `vesselapi_maritime` + `aisstream_maritime`) but point both at the SAME
  `dailyLimit`/`sessionLimit` so they A/B fairly under one cap.
  ⚠️ **CRITICAL — do NOT `gov.record()` per push.** A busy strait pushes
  hundreds of AIS pings/sec. Recording egress on every message trips the
  per-provider circuit breaker almost instantly → the breaker KILLS ALL egress
  (every governed feed, not just vessels). For a live WebSocket source, call
  `gov.record(providerId)` EXACTLY ONCE on `onopen` (one connection = one budget
  hit). Per-ping counting is the single most common way to nuke your own egress.
  The poll source (VesselAPI) still records once per poll as before.
- **Selector lives OUTSIDE the layer-toggle button.** Render the source chips
  in a sibling element (e.g. a `<Fragment>` wrapping the row `<button>` + a
  `.maritime-source` div). Picking a source must NOT toggle the layer — otherwise
  switching sources would also switch the layer off.
- **Row enabled if EITHER key exists.** If AISStream is the free, no-proxy
  alternative, gate the row on `vesselKey || aisstreamKey`, not just the paid
  key — else the free tier is unreachable.
- **No simulation fallback.** On connection error, clear the canvas and show a
  red HUD/status banner with a machine-readable code
  (`AISSTREAM_NOKEY | STALE | ERROR | CLOSED`) so the user can self-diagnose.
  Never render fake vessels.
- **Stale guard for WS:** if no message for ~60s, surface a "silent drop" status
  but keep the last-known fleet on screen (nozzle, not blank-out).

### AISStream client shape (free, CORS-clean, no dev proxy)
```js
// ⚠️ BoundingBoxes MUST be an array of boxes, each box a 4-corner list of
// [lat, lon] TUPLES — NOT a keyed {lat_min,...} object. A keyed object makes
// the server reject the handshake and CLOSE the socket instantly right after
// onopen (only symptom: "AISStream connection closed"). This was a real shipped
// bug; the tuple format fixed it. Full AISStream playbook:
// digital-twin-shm references/aisstream-live-integration.md
// ⚠️⚠️ KEEP THE BOX SMALL — the FREE tier enforces a GEOGRAPHIC AREA quota.
// A full-Malacca box (~1–6.5°N, 98–104.5°E) does NOT error and does NOT
// close the socket — the server simply sends NOTHING ("silent"). Symptom that
// wastes a diagnosis: "0 vessels" + a healthy-looking connection + no error.
// The fix is to SHRINK the box to a small patch (~50×90 km). A verified-live
// working box (Lumut, MARU):
const AIS_BBOX = [[3.9, 100.05], [4.6, 100.05], [4.6, 100.85], [3.9, 100.85]] // SW,NW,NE,SE ~ Lumut sea area
const ws = new WebSocket('wss://stream.aisstream.io/v0/stream')
ws.onopen = () => {
  ws.send(JSON.stringify({
    APIKey: import.meta.env.VITE_AISSTREAM_API_KEY,
    BoundingBoxes: [AIS_BBOX],
    FilterMessageTypes: ['PositionReport'],
  }))
  gov.record('aisstream_maritime') // ONCE per connection — NOT per message
}
// onmessage: each frame is a JSON array; keep latest per MMSI in a Map.
// Prune tracks silent >15min so the strait doesn't accumulate ghost dots.
// onclose/onerror: surface the server's real close code+reason (see playbook),
// not a generic "closed".
```
No Vite `/api-*` proxy needed (CORS-clean). Contrast VesselAPI: must proxy
through Vite (`server.proxy['/api-vessel']`) because it lacks CORS headers.

## 3. COG-rotated ship-arrow billboards + breadcrumb trails

For a live AIS console look (vs the static dot+vector of VesselAPI), render each
vessel as a `BillboardGraphics` whose image is an inline SVG ship-arrow data-URI
rotated by `rotation: CesiumMath.toRadians(v.cog)` — **billboard `rotation` is in
RADIANS; passing a raw degree value silently renders the arrow unrotated** (a
degree→radian conversion bug will bite you here; also check any bearing passed to
camera/rectangle math — a radian-bearing compared against a degree threshold
filters out every tile). Add a `PolylineGraphics` trail from the last ~24
breadcrumb positions, fading via `PolylineGlowMaterial` or a per-point color ramp,
so busy straits stay readable.
- **Ghost pruning:** drop any MMSI track silent >15 min (no position update) so
  the strait doesn't accumulate stale dots. Keep this in the client's Map,
  independent of the scene-graph prune.
- **Live HUD:** show MMSI, SOG, COG, a MOORED/UNDERWAY flag (SOG < ~0.5 kn ⇒
  moored), and an "N vessels tracked" tally — matches real AIS consoles.
- **Default source:** when the AISStream key is present at load, default
  `vesselProvider` to `'aisstream'` so a fresh setup lands straight on the live
  tracker; VesselAPI stays the selectable A/B alternative.

## 4. Fly the camera to the feed region on connect (or the feed is INVISIBLE)

**Bug shipped + fixed (`95fa5b7`):** a live feed rendered 0 vessels even though
the WebSocket was healthy — because the Cesium camera was parked over a totally
different ocean (app boots over the demo site / Panama). The vessels WERE
streaming in, just 18,000 km off-screen. Symptom: "0 vessels" + a working
connection. The fix: on first successful `onopen`, `flyTo` the feed's bounding
region. Use the deep-space-safe pattern (also in App.jsx `locateMe`) so it works
whether the camera is at street level or in orbit:

```js
const straitFlownRef = useRef(false)
const flyToFeed = useCallback(() => {
  if (straitFlownRef.current) return
  const el = viewer
  if (!el || typeof el.camera?.flyTo !== 'function') return
  straitFlownRef.current = true
  const DEST = Cesium.Cartesian3.fromDegrees(102.5, 3.5, 900000.0) // feed center
  const radial = el.camera.position ? Cesium.Cartesian3.magnitude(el.camera.position) - 6378137 : 0
  const camHeight = el.camera.positionCartographic?.height ?? radial
  if (camHeight > 1.0e6) {                       // from deep space: snap, then fly
    el.camera.setView({
      destination: Cesium.Cartesian3.fromDegrees(102.5, 3.5, 3.0e6),
      orientation: { heading: 0, pitch: -90, roll: 0 },
    })
    el.camera.flyTo({ destination: DEST, orientation: { heading: 0, pitch: -45, roll: 0 }, duration: 2.0 })
    return
  }
  el.camera.flyTo({ destination: DEST, orientation: { heading: 0, pitch: -45, roll: 0 }, duration: 2.0 })
}, [viewer])
```

Guard with a `useRef` flag so reconnects don't yank the operator's view every
time the socket drops/reopens. Fire it from the `onStatus(null)` (connected)
callback, NOT from `onopen`, so it only runs once the handshake truly succeeded.
This pairs with the flyTo-no-op trap (destination above current camera altitude)
already in the SKILL.md — the deep-space branch avoids the tumble.

## 5. Surface live diagnostics IN-APP (no DevTools peekaboo)

**Trap shipped + burned two diagnostic round-trips (`a34a871`→`ac9ba47`):**
asking the user to open DevTools Console + a `?aisdebug=1` flag to confirm
whether the WS was streaming. The user (a) dropped the query param on a hard
refresh (address bar reverted to `localhost:5175`) and (b) opened the wrong
DevTools tab (Issues, not Console). Two wasted screenshots. **Fix the next
session by putting the diagnostic in the app chrome itself.**

Add an `aisStat { frames, lastPing }` to the shared context. In the WS
`onmessage` handler (every frame, NOT every message-of-interest), bump it:
`setAisStat((s) => ({ frames: s.frames + 1, lastPing: Date.now() }))`.
Render it under the source chip in the sidebar:
`${frames} frames · last ${secsAgo}s ago`, or `∅ no frames yet` when zero.

Then the operator diagnoses WITHOUT opening DevTools:
- frame counter ticking ⇒ server IS streaming; "0 vessels" just means none fell
  inside the box at that instant (quiet patch of water).
- stuck on "∅ no frames yet" for 60s ⇒ server sends nothing ⇒ free-tier area
  throttle / wrong box ⇒ shrink or split the box.

⚠️ **The "VESSEL TELEMETRY OFFLINE" banner is MISLEADING for a live WS.** It
fires on the 60s *stale* guard (no vessel landed in the box), which triggers
EVEN WHEN frames are arriving for ships just outside the box. Trust the frame
counter, not that banner. (Keep `?aisdebug=1` as an optional power-user escape
hatch, but don't make it the primary diagnostic path.)

## 6. Hard-refresh after a live-feed code change (stale-dev-server trap, again)

A Vite hot-reload does NOT re-run the component's mount effect that opens the WS
and fires the one-time camera `flyTo`. After editing the AISStream client or
camera, tell the user to **hard refresh (`Cmd+Shift+R`)**, not just rely on HMR,
or the camera stays parked over the old region and the socket never reconnects —
reproducing a phantom "0 vessels / no frames" that is actually a stale session.
