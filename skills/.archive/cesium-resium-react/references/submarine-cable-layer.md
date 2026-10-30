# Submarine Cables / Marine Lines Layer (Resium + Cesium)

Verified working recipe for rendering the **complete published submarine-cable
network** (teleGeography / submarinecablemap.com) on a Cesium globe, keyless and
CORS-free. Companion to **G32 / G33 / G34 / G35** in SKILL.md.

> **This file's renderer is the FINAL verified-good version (G32 fix applied):**
> ONE `<Entity>` PER SUB-LINE (Cesium honors only ONE polyline per entity), height
> 0, source coords passed through verbatim. The earlier "one Entity per cable with
> multiple `<PolylineGraphics>`" form was the bug — do NOT copy it.

Data source (keyless, static):
`https://www.submarinecablemap.com/api/v3/cable/cable-geo.json`
(718 `MultiLineString` features; `properties.feature_id` unique 718/718;
`properties.id` has 21 duplicates; `properties.color` native cable color;
`length_km` per feature.)

## The three bugs that make cables "look wrong"

1. **G33 — lat/lon swap (mirrors every route to the wrong hemisphere).**
   GeoJSON stores `[lon, lat]`. `Cartesian3.fromDegrees(longitude, latitude)` also
   takes `(lon, lat)`. If you flip to `[lat, lon]` then call `fromDegrees(lon, lat)`
   on it, you actually call `fromDegrees(lat, lon)` → the whole network is mirrored
   across the `lon=lat` diagonal (a transatlantic cable lands in the South Pacific).
   Invisible to lint/build. **Don't flip.**
2. **G32 — one `<Entity>` PER SUB-LINE (NOT per cable, not per segment).** Cesium
   renders only ONE `<PolylineGraphics>` per `<Entity>`. Multiple sibling polylines
   inside one entity → all but one dropped/merged → "14-branch cable renders as 1
   line / few cables / cables in wrong places" (the merged line connects branch
   endpoints in sequence). Also: duplicate `properties.id` keys drop routes → use
   unique `feature_id`.
3. **G34 — `clampToGround` over ocean** (lines vanish/clip over water on a 3D
   globe). FINAL form: height **0** (`fromDegrees(lon, lat, 0)`), passing source
   `[lon,lat]` straight through with NO transform and NO altitude. Height 0 is the
   most faithful-to-source render (a 50km lift was tried then rejected by the user's
   "render source verbatim, don't change it" mandate).

## Coordinate-range sanity check (catch the G33 mirror instantly)

Run against the raw GeoJSON before declaring the layer done:

```js
const j = require('./public/submarine-cables.json')
const find = (n) => j.features.find(f => (f.properties.name||'').toUpperCase().includes(n))
for (const n of ['FEA','MAREA']) {
  const f = find(n)
  let minLon=999,maxLon=-999,minLat=999,maxLat=-999
  for (const line of f.geometry.coordinates)
    for (const [lon,lat] of line) {
      if (lon<minLon)minLon=lon; if (lon>maxLon)maxLon=lon
      if (lat<minLat)minLat=lat; if (lat>maxLat)maxLat=lat
    }
  console.log(n, 'lon', minLon.toFixed(1),'..',maxLon.toFixed(1),
                 'lat', minLat.toFixed(1),'..',maxLat.toFixed(1))
}
// EXPECTED: FEA lon 32.5..100.6 lat 4.4..30.0   (Egypt -> SE Asia)
//           MAREA lon -76.1..-2.9 lat 36.8..46.6 (Virginia Beach -> Bilbao)
// If MAREA shows lat ~ -76 -> you swapped lon/lat.
```

## Data driver (egressDrivers.js style)

```js
const CABLES_LOCAL = '/submarine-cables.json'   // bundled via curl, no CORS
// COLOR (final, per founder preference — SEE "Color" note below):
// muted dark slate — darker than light gray (less glare) but LOW-CONTRAST against
// the sea so the web stays RECESSIVE and does not overpower earthquake/volcano/
// weather indicators. Avoid bright blues / high-contrast grays on a sea basemap.
const CABLE_COLOR = '#3a4a57'

export async function fetchCables() {
  try {
    const res = await fetch(CABLES_LOCAL)
    if (!res.ok) throw new Error(`Cable asset ${res.status}`)
    const json = await res.json()
    const features = Array.isArray(json?.features) ? json.features : []
    const cables = features
      .map((f) => {
        const g = f?.geometry
        if (!g || g.type !== 'MultiLineString' || !Array.isArray(g.coordinates)) return null
        const name = f?.properties?.name || 'Unnamed cable'
        // GeoJSON [lon,lat]; Cesium fromDegrees(lon,lat) also (lon,lat) ->
        // PASS THROUGH UNCHANGED. Do NOT swap to [lat, lon].
        const lines = g.coordinates.map((line) =>
          line.map(([lon, lat]) => [lon, lat]))   // [lon, lat], no flip
        return {
          id: `cable-${f?.properties?.feature_id || f?.properties?.id || name}`,
          name,
          color: CABLE_COLOR,
          lengthKm: Number(f?.properties?.length_km) || null,
          source: 'Global Subsea Cable Network',
          url: 'https://www.submarinecablemap.com/',
          lines,
        }
      })
      .filter(Boolean)
    return { events: cables, error: null }
  } catch (error) {
    return { events: [], error: { code: 'CABLE_OFFLINE', message: error.message } }
  }
}
```

> OSIRIS (`osiris-master`) bundles its own `public/data/submarine-cables.json` and
> renders `cable.geometry` verbatim in MapLibre, filtering out faint light-blue arcs
> (`#9BB5CC/#A0B8CD/#8EABC2`) and recoloring survivors to `#1976D2`. For a
> "complete network" match, DON'T filter — render all 718 routes. Same upstream
> source; the live API is fresher. **G35: render the reference source VERBATIM —
> no recolor, no filter, no altitude, no clamp — until the user explicitly asks.**
> This session the founder overrode OSIRIS's filter and demanded all 718 routes.

## Renderer (CableEntities.jsx — FINAL verified-good, G32 applied)

```jsx
import { useEffect, useRef, useState } from 'react'
import { useCesium } from 'resium'
import { Entity, PolylineGraphics } from 'resium'
import { Cartesian3, Color, ScreenSpaceEventHandler, ScreenSpaceEventType } from 'cesium'
import { useCables } from '../services/useFeeds'

function hexToColor(hex) {
  try { return Color.fromCssColorString(hex) } catch { return Color.fromCssColorString('#3a4a57') }
}

// Source coords are [lon, lat]; Cesium fromDegrees(lon, lat) also (lon, lat) ->
// pass through VERBATIM at height 0, no transform (G33/G34).
function lineToCartesians(line) {
  return line.map(([lon, lat]) => Cartesian3.fromDegrees(lon, lat, 0))
}

export default function CableEntities({ showCables }) {
  const { viewer } = useCesium()
  const [selected, setSelected] = useState(null)
  const cablesRef = useRef([])
  const { events, error } = useCables()
  cablesRef.current = events
  const connError = showCables ? error : null

  useEffect(() => {
    if (!viewer || !showCables) return
    const handler = new ScreenSpaceEventHandler(viewer.scene.canvas)
    handler.setInputAction((click) => {
      const picked = viewer.scene.pick(click.position)
      const eid = picked?.id?.id
      if (eid && eid.startsWith('cable-')) {
        // eid = cable-<feature_id>__<i>; resolve parent cable for the HUD.
        const baseId = eid.split('__')[0]
        const c = cablesRef.current.find((x) => x.id === baseId)
        if (c) { setSelected(c); return }
      }
      setSelected(null)
    }, ScreenSpaceEventType.LEFT_CLICK)
    return () => handler.destroy()
  }, [viewer, showCables])

  if (!showCables) return null
  return (
    <>
      {events.map((cable) => {
        const isSel = selected?.id === cable.id
        const color = hexToColor(cable.color)
        // ONE Entity per sub-line — Cesium honors only ONE polyline per Entity.
        return cable.lines.map((line, i) => (
          <Entity key={`${cable.id}-${i}`} id={`${cable.id}__${i}`}>
            <PolylineGraphics
              positions={lineToCartesians(line)}
              width={isSel ? 4.0 : 2.5}
              material={color}
            />
          </Entity>
        ))
      })}
      {/* selected HUD: name + lengthKm + source + url link (G16/G17 pick) */}
    </>
  )
}
```

**CRITICAL:** `id={`${cable.id}__${i}`}` (double-underscore separator) — NOT
`${cable.id}-${i}`, because `feature_id` values already end in `-<n>` (e.g.
`kumul-domestic-submarine-cable-system-0`); a trailing `-\d+` strip would corrupt
the id. Resolve parent via `split('__')[0]`.

## Color (final guidance — iterative churn this session)

The founder cycled the cable color several times: light gray `#c9ccd0` → OSIRIS
blue `#1976D2` → light gray → **muted dark slate `#3a4a57`** (final). Lesson: on a
sea/water basemap, the cable web must stay RECESSIVE and not overpower other
map indicators (earthquakes, volcanoes, weather). Rule: **darker-than-light-gray
but low-contrast with the sea** — a muted dark slate/teal reads as a quiet line
that doesn't glare or dominate. Avoid bright high-contrast blues and avoid gray
that's lighter than the water (it glares). Let the user pick the final shade; the
recessive intent is the durable preference.

## Bundling (avoid CORS — G30)

submarinecablemap.com sends **no `Access-Control-Allow-Origin`**, so a browser
`fetch()` from `localhost`/Vercel is CORS-blocked (curl works). Bundle locally:

```bash
curl -s "https://www.submarinecablemap.com/api/v3/cable/cable-geo.json" \
  -o public/submarine-cables.json
```

Vite copies `public/` → `dist/`, so it ships with the build and works on Vercel
with zero CORS. Verify served: `curl -s -o /dev/null -w "%{size_download}" \
https://<project>.vercel.app/submarine-cables.json` (569-byte = SPA fallback, not deployed).

## Deploy caveat (G31-ADDENDUM)

If the project auto-deploys from GitHub, commit with the repo's configured
`git config user.email` (e.g. `kingkymaru@gmail.com` for R-Tessera) — a throwaway
author makes the Vercel webhook no-fire and the live site stays stale.
