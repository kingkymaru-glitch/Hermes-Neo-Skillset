# Mocking a missing LAN-device endpoint in the Vite dev proxy

## Problem
A physical LAN device (e.g. a phone running "IP Webcam") serves SOME endpoints
over the proxy (`/s22-api/video`, `/s22-api/shot.jpg`) but NOT others. The app
polls `/s22-api/sensors.json`; the device 404s / the proxy 502s it. The poll's
`fetch()` throws -> the UI flips to OFFLINE even though the real streams (video/
snapshot) are perfectly live. The user explicitly asked: "if the app doesn't
natively provide a sensors.json, mock the expected telemetry so the dashboard
stops showing OFFLINE."

## Fix - intercept the one path with a dev-server middleware plugin
Add a Vite plugin whose `configureServer` runs BEFORE the proxy (`enforce:'pre'`)
and returns a believable JSON envelope for the missing path. Everything else
passes through to the real device.

```js
// vite.config.js
function s22SensorsMock() {
  return {
    name: 's22-sensors-mock',
    enforce: 'pre',                 // wins over server.proxy for this path
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (!req.url || !req.url.startsWith('/s22-api/sensors.json')) return next()
        res.writeHead(200, { 'content-type': 'application/json' })
        res.end(JSON.stringify({ gps: false, mocked: true, source: 'vite-s22-mock' }))
      })
    },
  }
}

export default defineConfig({
  plugins: [react(), cesium(), s22SensorsMock()],
  server: { proxy: { /* .../s22-api... */ } },
})
```

Key points:
- `enforce:'pre'` matters - without it the proxy owns `/s22-api/*` and the
  middleware never sees the request. `pre` makes the middleware run first and
  `res.end()` short-circuits before the proxy is consulted.
- Match on `req.url.startsWith('<path>')`, not equality, so `?_=cachebust`
  query strings pass the guard.
- Return the SHAPE the consumer already parses. Here the app's `parseGps(raw)`
  reads `raw.gps.data[0]`; `gps:false` (or missing `data`) -> `parseGps` returns
  `null` -> "no fix", so SHM channels stay simulated as designed. No app code
  change needed.

## Wire the poll so a mocked 200 does NOT mean OFFLINE
The consumer's poll loop must distinguish "proxy responded 200 but no GPS fix"
(expected, device is fine, SHM simulated) from "proxy truly unreachable"
(wrong IP / device asleep -> real outage). Gate `online` on the HTTP response,
not on whether a fix was parsed:

```js
try {
  const res = await fetch(TELEMETRY_URL)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const raw = await res.json()
  setDeviceStatus((d) => ({ ...d, online: true, gpsFix: !!parseGps(raw) }))
} catch {
  setDeviceStatus((d) => ({ ...d, online: false, gpsFix: false })) // real outage
}
```

Only the `catch` (proxy 502/connection refused) flips the console to a clean
"DEVICE OFFLINE". A 200 with `gps:false` keeps `online:true`.

## Set the DEFAULT proxy IP to the device's real LAN IP
The UI override is mirrored into a cookie and the `router(req)` reads it - but
on a FRESH dev-server start (before the user has typed anything), the proxy
falls back to `DEFAULT_IP`. Set `DEFAULT_IP` to the device's actual LAN IP so it
points correctly out of the box. (S22 Ultra running IP Webcam was `192.168.0.6`.)

## Verification (you CAN prove the mock live - unlike raw device reachability)
Start a throwaway dev server on a port the user is NOT using, then curl:
```
npx vite --port 5200 --strictPort &
sleep 4
curl -s -w "\n-> %{http_code}\n" http://localhost:5200/s22-api/sensors.json
# expect: {"gps":false,"mocked":true,"source":"vite-s22-mock"}  -> 200
```
Kill the server after. This exercises the EXACT path the browser uses (dev
server only - the `configureServer` hook does NOT run under `vite build`/`preview`,
so the production bundle will still 502 on that path; dev is the target here).

Inline `&` backgrounding is rejected by the shell guard - launch with
`terminal(background=true)` then curl in a follow-up call, then `process(action='kill')`.

## When to drop the mock
If the device later exposes a native `sensors.json`, delete the one plugin
(or gate it behind an env flag) so the real feed is used. Leave a one-line note
at the call site so a future session knows it's a stand-in.
