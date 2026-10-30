# MultiLineString route / cable rendering in Resium (G32)

Draw any `MultiLineString` network (submarine cables, flight paths, pipelines,
shipping lanes) in Cesium via Resium WITHOUT the "disconnected fragments",
"few cables", or "wrong places" failures. THREE independent bugs share these
symptoms — all three fired on R-Tessera Submarine Cables this session.

## Symptom space
- Cables appear as short broken/disconnected segments, not continuous routes.
- A multi-branch cable (e.g. "Kumul Domestic Submarine Cable System", 14
  branches) shows as only a few cables / a tiny stub.
- OR some cables are simply absent.
- Browser console may show: `Encountered two children with the same key,
  'cable-<name>'`.

## THE BIG ONE — multiple <PolylineGraphics> siblings in ONE <Entity> COLLAPSE (Bug 0)
**Cesium only renders ONE `PolylineGraphics` per `Entity`.** If you put several
`<PolylineGraphics>` as children of a single `<Entity>` (one per sub-line /
branch), Cesium honors only one — the rest are dropped or merged into a single
truncated line. This is the #1 cause of "a 14-branch cable renders as 1 line /
few cables" and "cables where they shouldn't be" (the merged line connects
branch endpoints in sequence across land/ocean).

```jsx
// WRONG — multiple polylines inside ONE entity; only ONE is honored
<Entity key={cable.id} id={cable.id}>
  {cable.lines.map((line, i) => (
    <PolylineGraphics key={i} positions={...} />   // only one actually shows
  ))}
</Entity>
```

**FIX — render ONE `<Entity>` PER SUB-LINE, each its own single polyline:**

```jsx
{events.map((cable) => {
  const isSel = selected?.id === cable.id
  const color = hexToColor(cable.color)
  return cable.lines.map((line, i) => (
    <Entity key={`${cable.id}-${i}`} id={`${cable.id}__${i}`}>
      <PolylineGraphics positions={lineToCartesians(line)} width={isSel ? 4.0 : 2.5} material={color} />
    </Entity>
  ))
})}
```

Click resolution: a sub-line entity id is `cable-<feature_id>__<i>`. In the
`ScreenSpaceEventHandler`, resolve the parent cable:
`const baseId = eid.split('__')[0]` then `cablesRef.current.find(x => x.id === baseId)`.
(NEVER use `eid.replace(/-\d+$/, '')` — `feature_id` values like
`kumul-domestic-submarine-cable-system-0` already END in `-0`, so that would
strip the wrong part.)

## Bug 1 — per-segment entity explosion (fragmentation)
Naive code flattens every coordinate pair into its own 2-point segment and
renders one `<Entity>` per segment → thousands of micro-entities → Cesium
z-fights/drops them → looks fragmented + perf hog. FIX = the per-sub-line Entity
pattern above (each sub-line is an ordered point array, drawn as ONE continuous
polyline). Do NOT split a sub-line into 2-point segments.

## Bug 2 — duplicate React key / Entity id (silent route drop)
`properties.id` is often NOT unique across features (submarinecablemap.com: 21
dups among 718 — `rising-8`, `echo`, `2africa`, `connected-coast`...). Using it
as `key` + `Entity id` makes React drop/merge duplicates → those routes never
render. FIX: key by a truly unique field — `properties.feature_id` is unique
718/718 on submarinecablemap. Fallback chain: `feature_id || id || name`. Use the
SAME base string for the cable `id` (the `cable-<feature_id>` part that the click
handler splits on `__`).

## Correct component (verified green + introspected, R-Tessera)
Kumul now renders 14 sub-line entities / 81 points = exactly the source's 14
branches. Before the fix it collapsed to 1 polyline / 5 points.

```jsx
import { useEffect, useRef, useState } from 'react'
import { useCesium } from 'resium'
import { Entity, PolylineGraphics } from 'resium'
import { Cartesian3, Color, ScreenSpaceEventHandler, ScreenSpaceEventType } from 'cesium'
import { useCables } from '../services/useFeeds'

function hexToColor(hex) {
  try { return Color.fromCssColorString(hex) } catch { return Color.fromCssColorString('#1976D2') }
}

// GeoJSON is [lon, lat]; Cesium fromDegrees takes (longitude, latitude).
// Pass (lon, lat) directly — NO swap (G33), height 0 (G34), one Entity per sub-line (Bug 0).
function lineToCartesians(line) {
  return line.map(([lon, lat]) => Cartesian3.fromDegrees(lon, lat, 0))
}

export default function CableEntities({ showCables }) {
  const { viewer } = useCesium()
  const [selected, setSelected] = useState(null)
  const cablesRef = useRef([])
  const { events, error } = useCables()
  cablesRef.current = events

  useEffect(() => {
    if (!viewer || !showCables) return
    const handler = new ScreenSpaceEventHandler(viewer.scene.canvas)
    handler.setInputAction((click) => {
      const picked = viewer.scene.pick(click.position)
      const eid = picked?.id?.id
      if (eid && eid.startsWith('cable-')) {
        const baseId = eid.split('__')[0]          // cable-<feature_id>__<i> -> cable-<feature_id>
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
        return cable.lines.map((line, i) => (
          <Entity key={`${cable.id}-${i}`} id={`${cable.id}__${i}`}>
            <PolylineGraphics positions={lineToCartesians(line)} width={isSel ? 4.0 : 2.5} material={color} />
          </Entity>
        ))
      })}
      {/* selected HUD (name, lengthKm, source, url) omitted for brevity */}
    </>
  )
}
```

Driver `fetchCables()` must produce the unique `cable.id`:
`id: \`cable-${f?.properties?.feature_id || f?.properties?.id || name}\``
and `cable.lines = g.coordinates.map(line => line.map(([lon, lat]) => [lon, lat]))`
(GeoJSON MultiLineString: `coordinates` is `line[][][2]`; each `line` is an
ordered `[lon,lat]` array = one continuous sub-route).

## Data source (keyless, CORS-free)
Bundle locally (submarinecablemap.com sends NO CORS header — browser `fetch` of
the live API is blocked even though `curl` works; see G30):
`curl -s https://www.submarinecablemap.com/api/v3/cable/cable-geo.json -o public/submarine-cables.json`
then `fetch('/submarine-cables.json')`. Vite copies `public/` into `dist/`.

## Verification
- `npm run lint` (oxlint) 0/0 + `npm run build` green.
- Introspect the LIVE viewer (G38): expose `window.__viewer`, then
  `v.entities.values.filter(e=>String(e.id).startsWith('cable-kumul')).length`
  must equal the source sub-line count (14 for Kumul). If it's 1, you still have
  the Bug-0 collapse — fix the per-sub-line Entity pattern.
- Console ZERO `Encountered two children with the same key`.
- Stale dev server can re-show old bugs: `pkill -f vite` then start ONE fresh
  instance before judging (G8).
