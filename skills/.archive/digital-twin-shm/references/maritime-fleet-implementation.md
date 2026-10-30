# Live Maritime Fleet — KNOWN-GOOD Implementation (copy-with-modifications)

Verified end-to-end on MARU / my-digital-twin (commit `55581b0`,
`feat(layers): integrate live maritime fleet telemetry with glassmorphic switch
controls`). Two new files + 5 existing-file edits, all lint 0/0 / build green.
Use this as the template for ANY governed live-entity layer (vessels, aircraft,
tracked assets) — only the URL, field names, and poll cadence change.

> **Telemetry-integrity override — READ FIRST:** a LATER session REVOKED the
> simulated fallback (commit `d7b8ca3`, `refactor(egress): remove simulation
> fallback, report vesselapi connection failure`). For this user's ops/monitoring
> tools, do NOT render fake vessels as live — if the feed is down, CLEAR the
> canvas and show a red offline banner. The canonical production pattern now
> lives in `references/telemetry-integrity-no-fake-data.md`. This file is kept as
> the *structural* template (governed egress → Cesium entity layer + click HUD);
> just delete the `simulateVessels()` fallback and return `{ vessels: [], error }`
> on catch instead.
>
> **Production routing + diagnostics (later commits, already baked into the code
> blocks below):** `fcd55b9` aligned the driver to the official VesselAPI
> production route (`/v1/location/vessels/bounding-box` + discrete `filter.`
> params, `data`/`vessels` envelope, `latitude`/`longitude`/`vessel_name`/
> `speed`/`course` fields). `af82fc8` added the lightweight Layer 1 M.A.R.U.
> diagnostic trace (auth-state boolean log + connection-error log) — see
> `references/layer1-diagnostics-and-spec-matching.md`. The code blocks below are
> the CURRENT production shape; copy them as-is.

## Files

### `src/services/egressDrivers.js` (NEW — the governed egress pattern)
Single home for all governed outbound fetchers. Every function asks the gate
BEFORE firing and records AFTER a success; bails with `[]` (or `{vessels:[],error:null}`)
on deny/error. Returns a discriminator `{ vessels, error }` so the UI can
distinguish a budget-deny (keep last-known fleet) from a connection failure
(clear + report).

```js
// ⚠️ STALE TRANSPORT BLOCK — DO NOT COPY. This file is STRUCTURAL-only (governed
// egress → Cesium entity layer + click HUD). The POST flat-body form below was a
// dead end; the canonical driver is GET + `filter.*` + `time.from`/`time.to`
// (see references/vesselapi-request-shape.md). For areas wider than one 4°-span
// box, tile across multiple boxes and stitch client-side — see
// references/vesselapi-spatial-tiling.md. The real, current code lives in
// src/services/egressDrivers.js (commit 3ee37bf).
const VESSELAPI_BASE = '/api-vessel/v1/location/vessels/bounding-box'
const VESSELAPI_PROVIDER = 'vesselapi_maritime'

function toNum(x) { const n = Number(x); return Number.isFinite(n) ? n : NaN }

// Tolerant mapping: read official field names with common-alternative fallbacks
// so a minor upstream rename can't break the layer. RETURN NULL for unparseable
// coords. Add a source key to the `??` chain if your VesselAPI edition differs.
function normalizeVessel(v) {
  if (!v) return null
  const lat = toNum(v.latitude ?? v.lat ?? v.y)
  const lon = toNum(v.longitude ?? v.lon ?? v.long ?? v.x)
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null
  const mmsi = v.mmsi ?? v.imo ?? v.id ?? v.name
  return {
    id: `vessel-${mmsi}`,
    mmsi: String(mmsi),
    name: String(v.vessel_name ?? v.name ?? v.ship_name ?? mmsi ?? 'Unknown'),
    lat, lon,
    cog: toNum(v.course ?? v.cog ?? v.heading ?? 0),
    sog: toNum(v.speed ?? v.sog ?? v.speed_over_ground ?? 0),
    destination: String(v.destination ?? v.dest ?? '—'),
    // Live telemetry only — always verified; no simulated path exists.
    verified: true,
  }
}

export async function fetchLiveVessels(gov) {
  // 1 · Governance gate first; deny → keep last-known fleet (error null).
  const verdict = gov?.ask?.(VESSELAPI_PROVIDER)
  if (!verdict || !verdict.allow) return { vessels: [], error: null }
  // 0 · Lightweight diagnostic — confirm auth key presence ONLY (never the key).
  console.log('[egress][vesselapi] Auth initialization state:',
    !!import.meta.env.VITE_VESSEL_API_KEY)
  // 2 · Governed egress. No fabricated fallback — report, don't invent.
  try {
    const key = import.meta.env.VITE_VESSEL_API_KEY
    const response = await fetch(VESSELAPI_BASE, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${key || ''}`,
      },
      body: JSON.stringify({
        latBottom: 2.0, lonLeft: 100.0, latTop: 7.0, lonRight: 105.0,
      }),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const json = await response.json()
    // Production envelope: data first, then vessels, then bare array.
    const list = Array.isArray(json?.data) ? json.data
               : Array.isArray(json?.vessels) ? json.vessels
               : Array.isArray(json) ? json : []
    gov?.record?.(VESSELAPI_PROVIDER)                      // count the egress
    return { vessels: list.map(normalizeVessel).filter(Boolean), error: null }
  } catch (error) {
    const message = error instanceof TypeError
      ? 'Network error — cannot reach VesselAPI (check connection / DNS).'
      : error?.message || 'VesselAPI request failed.'
    console.error('[egress][vesselapi] Live fetch failed:', message)
    console.error('[egress][vesselapi] Connection error:', error.message || error)
    return { vessels: [], error: { code: 'VESSELAPI_OFFLINE', message } }
  }
}
```

### `src/components/MaritimeEntities.jsx` (NEW — Cesium entity layer + HUD)
Mounted inside `<Viewer>` (next to `<AssetEntities>` in App.jsx) so `useCesium()`
resolves. Self-gates on `showMaritimeLayer` (returns null when off). Renders
neon-cyan point + COG-oriented heading vector + label; click opens a tracking HUD.
On `error` it clears the canvas and shows a red offline banner (never fake data).

```jsx
import { useEffect, useRef, useState } from 'react'
import { Entity, PointGraphics, LabelGraphics, PolylineGraphics, useCesium } from 'resium'
import {
  Cartesian3, Color, Cartesian2, VerticalOrigin, LabelStyle,
  ScreenSpaceEventHandler, ScreenSpaceEventType, NearFarScalar,
} from 'cesium'
import { useEdgeData } from '../context/EdgeDataContext'
import { useGovernance } from '../governance/useGovernance'
import { fetchLiveVessels } from '../services/egressDrivers'

const LIVE = Color.fromCssColorString('#22c55e') // verified live API signal
const POLL_MS = 30000 // 30s cadence — respects the 5/session egress budget

// COG (deg, clockwise from north) → destination lon/lat at a fixed range, so
// the polyline reads as a directional heading vector.
function headingDest(lon, lat, cogDeg, rangeKm = 28) {
  const R = 6371, b = (cogDeg * Math.PI) / 180
  const lat1 = (lat * Math.PI) / 180, lon1 = (lon * Math.PI) / 180
  const d = rangeKm / R
  const lat2 = Math.asin(Math.sin(lat1) * Math.cos(d) + Math.cos(lat1) * Math.sin(d) * Math.cos(b))
  const lon2 = lon1 + Math.atan2(Math.sin(b) * Math.sin(d) * Math.cos(lat1),
    Math.cos(d) - Math.sin(lat1) * Math.sin(lat2))
  return [(lon2 * 180) / Math.PI, (lat2 * 180) / Math.PI]
}

export default function MaritimeEntities() {
  const { showMaritimeLayer } = useEdgeData()
  const gov = useGovernance()
  const { viewer } = useCesium()
  const [vessels, setVessels] = useState([])
  const [selected, setSelected] = useState(null)
  const [budgetHit, setBudgetHit] = useState(false)
  const [connError, setConnError] = useState(null)
  const vesselsRef = useRef([])
  vesselsRef.current = vessels

  useEffect(() => {
    if (!showMaritimeLayer) {
      setVessels([]); setSelected(null); setBudgetHit(false); setConnError(null); return
    }
    let alive = true
    const pull = async () => {
      const { vessels: next, error } = await fetchLiveVessels(gov)
      if (!alive) return
      if (error) { setVessels([]); setSelected(null); setConnError(error); return }
      setConnError(null)
      if (gov.ask('vesselapi_maritime').allow === false) { setBudgetHit(true); return }
      if (next.length) { setVessels(next); setBudgetHit(false) }
    }
    pull()
    const t = setInterval(pull, POLL_MS)
    return () => { alive = false; clearInterval(t) }
  }, [showMaritimeLayer, gov])

  // Dedicated click-to-track HUD (separate from the canvas' generic asset pick,
  // which only resolves known asset ids → vessel clicks would otherwise open the
  // sensor tab). Match on the `vessel-` id prefix.
  useEffect(() => {
    if (!viewer || !showMaritimeLayer) return
    const handler = new ScreenSpaceEventHandler(viewer.scene.canvas)
    handler.setInputAction((click) => {
      const picked = viewer.scene.pick(click.position)
      const eid = picked?.id?.id
      if (eid && eid.startsWith('vessel-')) {
        const v = vesselsRef.current.find((x) => x.id === eid)
        if (v) { setSelected(v); return }
      }
      setSelected(null)
    }, ScreenSpaceEventType.LEFT_CLICK)
    return () => handler.destroy()
  }, [viewer, showMaritimeLayer])

  if (!showMaritimeLayer) return null

  return (
    <>
      {vessels.map((v) => {
        const [lon2, lat2] = headingDest(v.lon, v.lat, v.cog)
        const isSel = selected?.id === v.id
        return (
          <Entity key={v.id} id={v.id} name={v.name}
            position={Cartesian3.fromDegrees(v.lon, v.lat)}>
            <PointGraphics pixelSize={isSel ? 12 : 9} color={LIVE}
              outlineColor={Color.WHITE} outlineWidth={1} />
            <PolylineGraphics positions={[
              Cartesian3.fromDegrees(v.lon, v.lat),
              Cartesian3.fromDegrees(lon2, lat2),
            ]} width={isSel ? 3 : 2} material={LIVE} />
            <LabelGraphics text={v.name} font="600 12px ui-monospace, monospace"
              fillColor={LIVE} showBackground backgroundColor={Color.fromCssColorString('#0f172ab0')}
              backgroundPadding={new Cartesian2(6, 4)} pixelOffset={new Cartesian2(0, -18)}
              verticalOrigin={VerticalOrigin.BOTTOM} style={LabelStyle.FILL}
              scaleByDistance={new NearFarScalar(1.5e6, 1.0, 1.2e7, 0.35)}
              translucencyByDistance={new NearFarScalar(1.5e6, 1.0, 1.2e7, 0.35)} />
          </Entity>
        )
      })}
      {selected && (
        <div className="vessel-hud" role="dialog" aria-label="Vessel tracking">
          <div className="vessel-hud-head">
            <span className="vessel-hud-dot" />
            <span className="vessel-hud-name">{selected.name}</span>
            <button className="vessel-hud-close" onClick={() => setSelected(null)} aria-label="Close vessel HUD">×</button>
          </div>
          <dl className="vessel-hud-rows">
            <div><dt>SOG</dt><dd>{Number(selected.sog).toFixed(1)} kn</dd></div>
            <div><dt>COG</dt><dd>{Math.round(selected.cog)}°</dd></div>
            <div><dt>DEST</dt><dd>{selected.destination}</dd></div>
          </dl>
        </div>
      )}
      {budgetHit && (
        <div className="vessel-hud-notice" role="status">
          Egress budget reached · showing last known fleet
        </div>
      )}
      {connError && (
        <div className="vessel-hud-error" role="alert">
          <span className="vessel-hud-pulse" /> VESSEL TELEMETRY OFFLINE — {connError.message}
        </div>
      )}
    </>
  )
}
```

### App.jsx edits (mount the component + import)
```jsx
import MaritimeEntities from './components/MaritimeEntities'
// inside <Viewer>, after <AssetEntities assets={assets} />:
<MaritimeEntities />
```
Note: `AssetEntities` in this repo is defined IN-FILE (not imported from a module) —
grep before assuming an import exists. Add `import MaritimeEntities ...` next to
the `MapControlPanel` import instead.

### CSS — `src/App.css` (append; glassmorphic HUD matching `.placement-banner`)
`.vessel-hud` = `position:absolute; left:16px; bottom:calc(26px + 16px); z-index:24;`
glass `rgba(15,23,42,0.66)` + `blur(12px)` + `1px solid rgba(56,189,248,0.45)`.
`.vessel-hud-dot` green `#22c55e` (was neon for live-only) with `box-shadow:0 0 8px #22c55e`.
Rows are a `<dl>` grid: `dt` uppercase 10px green, `dd` 13px right-aligned. Close
`×` button resets `setSelected(null)`. `.vessel-hud-notice` = same glass, slate
text, shown when the budget gate denies (keeps last-known fleet + honest notice).
`.vessel-hud-error` = same glass but red: `color:#fecaca; background:rgba(239,68,68,0.16);
border:1px solid rgba(239,68,68,0.65);` with a pulsing `.vessel-hud-pulse` dot
(`@keyframes` opacity 1→0.3 loop). Shown on connection failure.

## Gotchas specific to live-entity layers
- **Don't reuse `onSelectedEntityChange` for the click HUD** (see cesium-resium-react
  G16/G17): it only fires on SELECTION CHANGE, so re-click is a no-op. This
  component uses its OWN `ScreenSpaceEventHandler` LEFT_CLICK + `scene.pick` and
  matches the `vessel-` id prefix — independent of the canvas' generic asset pick.
- **`useCesium()` returns `{}` on first render** (cesium-resium-react G13): the
  `if (!viewer || !showMaritimeLayer) return` guard in the effect handles it; the
  effect re-runs once context populates. The component itself still `return null`
  when off, so no listener is created until the layer is on.
- **Keep the COG vector FIXED-RANGE** (28 km) rather than scaling by speed — a
  speed-scaled vector overlaps neighbours at high zoom and looks noisy. Fixed
  range reads cleanly as a heading arrow.
- **Tolerant field mapping is the key durability win**: the user's "real schema"
  was a CONFIG SPEC, not a sample JSON. `normalizeVessel` reads official names
  AND alternatives (`latitude`/`lat`, `course`/`cog`, `speed`/`sog`). If the real
  VesselAPI edition uses a quirky spelling, add ONE line to the `??` chain — no
  other change needed. Don't hardcode a single assumption for FIELD names.
- **URL/params/headers are NOT tolerant** — wire the user-supplied spec VERBATIM
  (see `references/layer1-diagnostics-and-spec-matching.md`). The production route
  is `/v1/location/vessels/bounding-box` with discrete `filter.*` params, NOT
  `?bbox=2.0,100.0,7.0,105.0`.
- **Budget gate on poll**: after a successful `fetchLiveVessels`, re-check
  `gov.ask('vesselapi_maritime').allow === false` — if the gate flipped deny
  mid-session, STOP overwriting `vessels` (keep last-known fleet) and show the
  notice. This keeps the map alive instead of blanking on quota exhaustion.
- **Bundle impact is tiny**: +4.7 kB JS gzip for the whole layer. Live-entity
  layers are cheap; don't fear adding them.

## How this resolved the "payload never arrived" premise-check
The prior reference warned: build shape-independent stages (registries + toggle)
first, then STOP and ask for the endpoint. This session the user later PASTED a
VesselAPI config spec (endpoint + auth + field mapping). It was a spec, not JSON,
so the tolerant `normalizeVessel` was the right call (no guessing, one-line
extensibility). Lesson: the premise-check is about NOT GUESSING FIELD NAMES, which
a tolerant mapper fully satisfies — you do NOT need a literal sample JSON row if
you map defensively and expose the `??` chain for easy extension. URL/param/header
NAMES, however, you DO take verbatim from the spec — never invent those.
