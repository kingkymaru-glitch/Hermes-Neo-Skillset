# S22 Ultra Edge Node (android mode) — physical phone as a live spatial source

MARU's physical edge node = a Samsung Galaxy S22 Ultra running the **IP Webcam**
app over the LAN. All feeds ride HTTPS on `:8080` (live MJPEG video, snapshot
fallback, audio, and a raw GPS/sensors JSON the map reads for spatial tracking).
This is the `android` value of `EDGE_MODE` in `src/context/EdgeDataContext.jsx`.

## Why a proxy (CORS + self-signed cert)
IP Webcam serves a self-signed HTTPS cert. A browser calling
`https://192.168.0.84:8080` directly trips mixed-content + cert errors and is
blocked by CORS. Fix: call same-origin `/s22-api/*` and let Vite's dev proxy
carry it to the phone. `secure:false` makes the proxy accept the self-signed cert.

**`vite.config.js`** (`server.proxy` block):
```js
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/s22-api': {
        target: 'https://192.168.0.84:8080',
        changeOrigin: true,
        secure: false,
        rewrite: (p) => p.replace(/^\/s22-api/, ''),
      },
    },
  },
})
```
Feed URLs (android branch of `EdgeDataContext.jsx`):
```js
const S22_IP    = import.meta.env.VITE_S22_IP || '192.168.0.84'
const S22_BASE  = '/s22-api'                  // proxied → https://192.168.0.84:8080
const STREAM_URL    = `${S22_BASE}/video`     // MJPEG live video
const SNAPSHOT_URL  = `${S22_BASE}/shot.jpg`  // still fallback
const AUDIO_URL     = `${S22_BASE}/audio.wav` // audio feed
const TELEMETRY_URL = `${S22_BASE}/sensors.json` // raw GPS + sensors
```
`deviceStatus` carries `{ stream, snapshot, audio, telemetry }` so a future
video/audio surface reads them from the context (no hardcoded URLs in the UI).

**PITFALL:** the proxy is `server:` only — it runs under `vite dev`, NOT
`vite preview` (built output). For now we develop against `dev`; to make the
built app reach the phone too, add a matching `preview.proxy` or a runtime
base-URL switch.

## GPS envelope (`/sensors.json`) + parser
IP Webcam shape:
```json
{ "gps": { "unit": "deg", "data": [ [ 1781234567890, [ 3.141592, 101.686944, 45.2, 15.0, 0.0 ] ] ] } }
```
`gps.data[0] = [ timestamp_ms, [ lat, lon, alt, accuracy, speed ] ]`.
Returns `gps: false` / empty `data` until a satellite lock. Parser (tolerant):
```js
function parseGps(raw) {
  try {
    const row = raw?.gps?.data?.[0]
    if (!Array.isArray(row) || !Array.isArray(row[1])) return null
    const [ts, fix] = row
    const [lat, lon, alt, accuracy, speed] = fix
    if (typeof lat !== 'number' || typeof lon !== 'number') return null
    return {
      lat, lon,
      alt:      typeof alt === 'number' ? alt : 0,
      accuracy: typeof accuracy === 'number' ? accuracy : 0,
      speed:    typeof speed === 'number' ? speed : 0,
      ts:       typeof ts === 'number' ? ts : Date.now(),
    }
  } catch { return null }
}
```
Provider stores it in `liveGeo` (null until fix) and exposes `geo = liveGeo ||
EDGE_ANCHOR`. Android poll branch: `fetch(TELEMETRY_URL)` → `parseGps` → on fix
`setLiveGeo(fix)` + `setDeviceStatus(d => ({...d, geo: fix, gpsFix: true}))`;
on no-fix `setDeviceStatus(d => ({...d, gpsFix: false}))`; on fetch failure
`setLiveGeo(null)` + `setConnection('offline')`.

## Rendering the phone on the map (live entity)
`App` (top-level) is OUTSIDE `<EdgeDataProvider>`, so it can't see `geo`. The
seeded `DEMO_ASSETS` / Supabase `assets` array is set once and has no live GPS.
Render the S22 as a live `<Entity>` from a component that lives INSIDE the
provider tree and calls `useEdgeData()`:
```jsx
function AssetEntities({ assets }) {
  const { mode, geo } = useEdgeData()
  const showS22 = mode === 'android' && geo
  return (
    <>
      {assets.map((a) => ( /* existing purple demo points */ ))}
      {showS22 && (
        <Entity
          key="s22-ultra"
          position={Cartesian3.fromDegrees(geo.lon, geo.lat, geo.alt ?? 0)}
          name="S22 Ultra (Live)"
          description={`Latitude: ${geo.lat.toFixed(5)}\nLongitude: ${geo.lon.toFixed(5)}\nAltitude: ${geo.alt?.toFixed(1) ?? 0} m`}
        >
          <PointGraphics pixelSize={18} color={Color.fromCssColorString('#22e07a')}
            outlineColor={Color.WHITE} outlineWidth={3} />
        </Entity>
      )}
    </>
  )
}
```
Place `<AssetEntities assets={assets} />` inside `<Viewer>` (replacing the inline
`assets.map`). Because `geo` updates every poll, the green marker TRACKS the phone
— something the static `assets` array can never do. Do NOT append the phone to
`assets`; that was the user's "stuck in Demo" trap.

## Verification
For any android-mode change, build WITH the env var so the dead-code-eliminated
branch is actually compiled, then grep:
```bash
VITE_EDGE_MODE=android npm run build
grep -o '/s22-api' dist/assets/*.js   # expect at least one hit
grep -o 'S22 Ultra (Live)' dist/assets/*.js
rm -rf dist
```
In a plain `npm run build` (mock) the android strings are CORRECTLY absent —
that is dead-code elimination, not breakage.
