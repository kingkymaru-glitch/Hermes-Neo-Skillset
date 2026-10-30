# CORS-Blocked Geo Feeds (G30) — bundle locally instead of fetching cross-origin

## The trap
A public geo/JSON endpoint works from `curl` (HTTP 200) but a browser `fetch()`
throws `TypeError: Failed to fetch` / "Network error". The layer HUD says
"FEED OFFLINE" even though the URL is correct. Cause: the server sends **no
`Access-Control-Allow-Origin` header**, so the browser's same-origin policy blocks
the response. `curl` ignores CORS, which is why it succeeds and the browser
doesn't.

## Diagnose (don't guess)
```bash
# If NO access-control-allow-origin line appears → it's CORS, not a dead endpoint
curl -s -D - -o /dev/null -H "Origin: http://localhost:5174" <URL> \
  | grep -i "access-control"
```

## Fix — bundle the dataset into `public/`
CORS-free, works offline, ships with the Vite build (Vite copies `public/` →
`dist/` automatically).

1. Download once (refresh manually when the upstream changes):
   ```bash
   curl -s <REMOTE_URL> -o public/cables.geojson
   ```
2. Load the local copy FIRST, fall back to remote only on failure:
   ```js
   const LOCAL = '/cables.geojson'
   async function loadJson() {
     try {
       const res = await fetch(LOCAL)
       if (res.ok) return await res.json()
     } catch { /* fall through */ }
     const res = await fetch(REMOTE_URL)
     if (!res.ok) throw new Error(`feed ${res.status}`)
     return await res.json()
   }
   ```
3. `public/cables.geojson` is served at `/cables.geojson` in dev AND prod — no
   serverless function needed.

If the feed MUST stay live (can't bundle): proxy it — `server.proxy` in Vite for
dev + a Vercel serverless function (`/api/<feed>`) for prod that re-fetches
server-side and returns the JSON with permissive CORS. Heavier; prefer bundling
for effectively-static data (cables, country borders, etc.).

## Concrete keyless source: submarine communication cables
- URL: `https://www.submarinecablemap.com/api/v3/cable/cable-geo.json`
  (teleGeography / submarinecablemap.com). **No CORS header** → bundle it.
- Shape: `FeatureCollection`, ~718 features, each
  `geometry.type === 'MultiLineString'`, `properties.name` (cable system),
  `properties.color` (hex). Coordinates are `[lon, lat]` (GeoJSON order).
- Render as resium `<PolylineGraphics>` per segment. Flip coords to
  `[lat, lon]` for Cesium and build `Cartesian3.fromDegrees(lon, lat, 0)`:
  ```js
  function cableSegments(cable) {
    const segs = []
    for (const line of cable.lines) {            // each line: [[lat,lon],...]
      for (let i = 0; i < line.length - 1; i++) {
        const [lat1, lon1] = line[i]
        const [lat2, lon2] = line[i + 1]
        segs.push({
          id: cable.id,
          positions: [
            Cartesian3.fromDegrees(lon1, lat1, 0),
            Cartesian3.fromDegrees(lon2, lat2, 0),
          ],
        })
      }
    }
    return segs
  }
  // <PolylineGraphics positions={seg.positions} width={1.6}
  //   material={Color.fromCssColorString(cable.color)} clampToGround />
  ```
- Click-to-identify: `ScreenSpaceEventHandler` `LEFT_CLICK` →
  `viewer.scene.pick(click.position)` → `obj.id.id` (carries the cable id) →
  resolve from a ref of the cables array → show a glass HUD with the name.
- This is the correct interpretation of "maritime lines" when the user means
  undersea comms cables (NOT live ship AIS tracks, which need a key-gated
  websocket).

## Other keyless feed sources confirmed CORS-open (browser-safe, no bundling)
- Open-Meteo `https://api.open-meteo.com/v1/forecast` →
  `access-control-allow-origin: *` (batched multi-point via comma-separated
  `latitude`/`longitude` works, returns an array).
- USGS earthquakes, NASA EONET volcanoes → CORS-open.
- Submarinecablemap.com → **NOT** CORS-open → bundle (above).
