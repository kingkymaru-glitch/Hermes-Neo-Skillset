# Free / Keyless Ambient Map Overlays (MARU / my-digital-twin)

How to add a NO-API-KEY geospatial data layer (weather grid, prayer times, OSM
POI, etc.) to the Cesium map, covering Malaysia-wide (or worldwide when the
source allows). Builds on the entity-layer contract in
`references/layer-orchestrator-and-governance.md` — read that first for the
registry/context/toggle shape. This file adds the KEYLESS specifics: the Vite
proxy touchpoint, the graceful-degrade contract, and a verified free-API bank.

## The 8-touchpoint recipe (entity layer, keyless)

The orchestrator doc lists 7 touchpoints; for keyless APIs add an 8th — the
Vite `server.proxy` block — so the browser stays same-origin and never trips a
CORS preflight. (Open-Meteo is CORS-clean already, but proxying anyway matches
the `/api-vessel` pattern and is mandatory for e-Solat/Overpass, which LACK a
CORS header.)

1. `src/services/egressDrivers.js` — add `fetchXxx(gov)` returning
   `{ points:[], error:null }` on success or `{ points:[], error:{code,message} }`
   on failure. Gate on `gov?.ask?.(providerId)`; call `gov?.record?.(providerId)`
   after a good fetch. NEVER fabricate readings.
2. `src/governance/governanceRegistry.js` — add a provider `{ id, label, desc,
   dailyLimit, sessionLimit, warnAt:0.8, enabled:true }`. Keyless ⇒ generous caps
   (e.g. 200 daily / 60 session). Distinct id from any key.
3. `src/layers/layerRegistry.js` — add an entity row
   `{ id, group:'overlay', kind:'entity', label, category:'DATA OVERLAY',
   provider:<id>, requiresKey:null }`.
4. `src/context/EdgeDataContext.jsx` — add `const [showX,setShowX]=useState(false)`
   and a `const [xCount,setXCount]=useState(0)`, expose both in the context value.
5. `src/components/XxxLayer.jsx` — the entity component (template below).
6. `src/MapControlPanel.jsx` — branch the row: `isLayerOn` returns the context
   flag for entity rows; `onToggle` flips it; live badge = count. Add the layer's
   flag/count to the `ENTITY_META` map (see existing maritime/situational rows)
   so the badge reads `N nodes | zones | POIs`.
7. `src/App.jsx` — import + mount `<XxxLayer />` INSIDE `<Viewer>` (next to
   `<SituationalEntities>`). Component self-gates on its flag (renders null off).
8. `vite.config.js` — add a `server.proxy['/api-xxx']` entry (see below).

## Vite proxy block (the keyless differentiator)

```js
proxy: {
  // ...existing /api-vessel, /s22-api ...
  '/api-openmeteo':      { target: 'https://api.open-meteo.com',                 changeOrigin: true, rewrite: p => p.replace(/^\/api-openmeteo/, '') },
  '/api-openmeteo-air':  { target: 'https://air-quality-api.open-meteo.com',     changeOrigin: true, rewrite: p => p.replace(/^\/api-openmeteo-air/, '') },
  '/api-openmeteo-marine':{ target: 'https://marine-api.open-meteo.com',         changeOrigin: true, rewrite: p => p.replace(/^\/api-openmeteo-marine/, '') },
  '/api-esolat':         { target: 'https://www.e-solat.gov.my',                 changeOrigin: true, rewrite: p => p.replace(/^\/api-esolat/, '') },
  '/api-overpass':       { target: 'https://overpass-api.de',                    changeOrigin: true, rewrite: p => p.replace(/^\/api-overpass/, '') },
}
```
The driver fetches the PROXY PATH (`/api-openmeteo/v1/forecast?...`), never the
raw `https://` URL. Dev-only; the proxy is NOT in the production bundle.

## Graceful-degrade contract (NON-NEGOTIABLE)

Every keyless layer MUST:
- On fetch failure return `{ points:[], error:{code,message} }` — NOT throw, NOT
  fabricate. Map stays clean.
- Render a RED "OFFLINE — <message>" banner (glassmorphic, `pointer-events:none`)
  only when `error` is set. Never hidden.
- Show nothing (no pins) when offline or toggled off.
- Count live data and feed the panel badge via `<x>Count`.

The OSM POI layer is the ONE that may legitimately render empty (public Overpass
rate-limits / 406s from some networks). That is reported, not faked.

## Component template (entity layer, keyless, click-HUD)

Mirror the existing `MaritimeEntities`/`SituationalEntities` shape:
- `useEdgeData()` → its flag + count setter; `useGovernance()` → `gov`; `useCesium()` → `viewer`.
- `useEffect` polls on its flag: `if(!showX){ setXs([]); setXCount(0); return }`,
  else `fetchX(gov)`, set state + count, `setInterval(pull, POLL_MS)`.
- A `ScreenSpaceEventHandler(viewer.scene.canvas)` LEFT_CLICK picks
  `viewer.scene.pick(click.position)?.id?.id`, looks up the entity, opens a
  glassmorphic HUD (`meteo-hud` / `prayer-hud` / `osm-hud` classes already in
  App.css). `handler.destroy()` on cleanup.
- `if(!showX) return null` — self-gates.
- Pins: `<Entity position={Cartesian3.fromDegrees(lon,lat,0)} heightReference={CLAMP_TO_GROUND}>` with `<PointGraphics>` + `<LabelGraphics>` (color = metric, `scaleByDistance`/`translucencyByDistance` for zoom fade). Helpers `toNum`/`Color.fromCssColorString` exist in the repo.

## Verified free / keyless API bank (Malaysia-capable)

All reachable 2026-07-19 via curl; no key. Use through the proxy.
- **Open-Meteo Weather** `GET /api-openmeteo/v1/forecast?latitude=1.5,...&longitude=100,...&current=temperature_2m,precipitation,wind_speed_10m`
  → multi-location returns an ARRAY of `{current:{...}}` in input order (single
  location returns one object — normalize both). GLOBAL source.
- **Open-Meteo Air Quality** `/api-openmeteo-air/v1/air-quality?...&current=us_aqi,pm2_5,pm10`. GLOBAL.
- **Open-Meteo Marine** `/api-openmeteo-marine/v1/marine?...&current=wave_height,wave_period,wind_wave_height`. GLOBAL. Land nodes return null `wave_height` → filter out (only paint water).
- **e-Solat (JAKIM)** `/api-esolat/index.php?r=esolatApi/takwimsolat&period=week&zone=JHR01` → `json.prayerTime[]` weekly; pick today's entry by `new Date(t.date).getDate()`. Zones: JHR01 KDH07 MLK01 NSN01 PHG01 PNG01 PRK01 PLS01 SGR01 KUL01 TRG01 KT01 SWK01 SWK08 SBH01 SBH02 (Peninsular + Borneo). MY ONLY. NO CORS header ⇒ MUST proxy.
- **OpenStreetMap Overpass** `POST /api-overpass/api/interpreter`, body `data=[out:json][timeout:25];(node["amenity"="hospital"](bbox);node["harbour"="yes"](bbox););out body 200;`. Peninsular bbox `(1.0,99.5,7.0,104.3)`. 406 from some networks ⇒ MUST proxy + graceful degrade.

### Malaysia seed grid pattern (for global grids)
Build a ~1° step grid covering Peninsular (1.5–6.5N × 100–104E) + Borneo
(1–7N × 109–119E), pass latitudes/longitudes as COMMA-SEPARATED lists so ONE
fetch paints the whole country. The grid is just a seed; the source is worldwide.

### Excluded on request
Financial APIs (BNM, stock) were explicitly out of scope. Keep them out.

## Web "Cmd+B" gate
After all edits: `npm run lint` (oxlint, target 0 errors; pre-existing warnings
in `MaritimeEntities` are benign) and `npm run build` must both be green. This
is the web equivalent of a green Xcode build — do NOT claim a browser-verified
visual pass (no browser here); the user does the visual review + commit.

## Pitfalls
- Forgetting touchpoint #8 (proxy) for e-Solat/Overpass ⇒ runtime CORS/406 fail.
- Assuming a single-location Open-Meteo response is always an array — normalize
  object-vs-array (`meteoPoints` helper does this).
- Painting marine wave pins on land nodes (null wave_height) ⇒ filter them out.
- Hardcoding prayer zone dates without the `new Date(t.date).getDate()` match ⇒
  wrong day's times. The JAKIM field names (fajr/dhuhr/asr/maghrib/isha) are the
  assumed contract; if the endpoint differs, the layer shows OFFLINE rather than
  wrong times — adjust the mapper, do not guess-and-ship silently.
