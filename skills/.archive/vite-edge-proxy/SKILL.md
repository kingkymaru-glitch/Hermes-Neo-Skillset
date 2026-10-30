---
name: vite-edge-proxy
description: Serve a physical LAN edge/IoT device (IP webcam, phone IP-cam, IoT box) to a localhost Vite/React dev app through the dev-server proxy — bypassing self-signed-cert and CORS walls, with a runtime-dynamic target the UI can re-point without a browser refresh. Covers the live MJPEG/video reset pattern (key + cache-bust) and the "gate UI on online state, not on URL-string presence" pitfall. Use when a localhost app must show live video/telemetry from a device on a LAN IP with a self-signed cert, and the user types the device IP in a Settings UI to re-route live traffic.
---

# Serve a LAN edge device through the Vite dev proxy

## When to use
- A localhost Vite app must show live video / telemetry from a physical device on the LAN (Galaxy S22 "IP Webcam", iPhone IP-cam, ESP32, any box serving HTTPS on a LAN IP with a self-signed cert).
- Direct `https://<device-ip>:8080/...` fails in the browser with `ERR_CERT_AUTHORITY_INVALID` (self-signed) and/or CORS errors.
- The user must be able to type the device IP in a Settings UI and have live traffic re-route immediately — no dev-server restart, no page reload.
- **Cloud SaaS API with a rejected CORS preflight** (e.g. a maritime/weather/geo API that answers `OPTIONS` with 4xx or omits `Access-Control-Allow-Origin`). The browser can't call it cross-origin; proxying through Vite makes it same-origin so the preflight never reaches the client. Same `proxy` + `rewrite` mechanism, no `secure:false` (the API has a valid cert) and usually no dynamic `router` (fixed target). Full recipe + the production-400 trap in `references/cloud-api-cors-proxy.md`.

## Why a proxy (not direct fetch)
- `secure: false` on the proxy bypasses the self-signed cert server-side; the browser only ever sees `localhost:<port>`, which is trusted.
- Proxying makes every request same-origin => no CORS wall.
- A per-request `router` fn lets the target change at runtime from a cookie/localStorage value the UI writes.

## Setup (vite.config.js)
```js
const IP_OVERRIDE_KEY = 'device_ip_override'
const DEFAULT_IP = '192.168.0.84'
const DEFAULT_PORT = 8080

function readCookies(req) {
  const out = {}
  const raw = req.headers.cookie
  if (!raw) return out
  raw.split(';').forEach((c) => {
    const i = c.indexOf('=')
    if (i > -1) out[c.slice(0, i).trim()] = decodeURIComponent(c.slice(i + 1).trim())
  })
  return out
}

function resolveTarget(req) {
  const cookies = readCookies(req)
  const ip = cookies[IP_OVERRIDE_KEY] || DEFAULT_IP
  return `https://${ip}:${DEFAULT_PORT}`
}

export default defineConfig({
  server: {
    proxy: {
      '/edge-api': {
        target: `https://${DEFAULT_IP}:${DEFAULT_PORT}`,
        changeOrigin: true,
        secure: false,                 // bypass self-signed cert
        rewrite: (p) => p.replace(/^\/edge-api/, ''),
        router: (req) => resolveTarget(req), // dynamic per-request target
      },
    },
  },
})
```
All app-side URLs stay `/edge-api/...` (transport-stable). Only the proxy TARGET is dynamic.

## UI re-point without refresh
1. Settings UI writes `localStorage[IP_OVERRIDE_KEY] = ip` AND mirrors it to a cookie (`document.cookie = 'device_ip_override=<ip>;path=/'`) so the server-side `router` sees it.
2. Settings calls a `reconnect()` that bumps a monotonic token (`connSeq`) in context.
3. Consumers watch `connSeq` and remount their live media (below). Poll loops key their `useEffect` deps on `connSeq` so they re-read the live target.
4. On reconnect, re-read the live IP so the UI shows exactly where the proxy now points (catches a typo'd IP at a glance).

## Pitfall: MJPEG `<img>` is sticky — it won't re-request on target change
A browser renders an MJPEG stream via `<img src=...>` and HOLDS the connection open. Changing the proxy target (new IP) does nothing to an already-loaded `<img>` — it keeps pulling from the dead connection. Fix: force a remount + cache-bust:
```jsx
const [localSeq, setLocalSeq] = useState(0)
const seq = `${connSeq ?? 0}-${localSeq}`
// ...
<img key={seq} className="feed" src={`${stream}?_=${seq}`} alt="live" />
```
`connSeq` bumps on Settings-save (auto reset); a manual ↻ button bumps `localSeq` (mid-session stall recovery). See `references/mjpeg-reset.md`.

## Pitfall: don't gate live-resource UI on URL-string presence
`deviceStatus.snapshot` is set once at boot to a constant string (`'/edge-api/shot.jpg'`), so `deviceStatus?.snapshot` is ALWAYS truthy. Gating the snapshot card on that renders a broken image and opens a 502 when the device is offline. Gate on a live `online` boolean from the poll loop instead, and disable/hide the control when offline. See `references/offline-gating.md`.

## Mock a missing device endpoint (device serves SOME paths, not all)
A LAN device (e.g. phone "IP Webcam") serves `/edge-api/video` + `/edge-api/shot.jpg`
but NOT `/edge-api/sensors.json`. The app's poll `fetch()`es the missing path, it
502s, the `catch` flips the UI to OFFLINE — even though the real streams are live.
Fix: intercept ONLY the missing path with a dev-server middleware plugin
(`enforce:'pre'` so it beats the proxy) and return the envelope shape the
consumer already parses. Full recipe + live curl verification in
`references/mock-missing-endpoint.md`. Critical bits:
- `enforce:'pre'` is required — without it the proxy owns `/edge-api/*` and the
  middleware never fires. `res.end()` short-circuits before the proxy is consulted.
- Match `req.url.startsWith('/edge-api/sensors.json')` (not `===`) so `?_=cachebust`
  query strings pass.
- Return the SHAPE the consumer parses. If `parseGps(raw)` reads `raw.gps.data[0]`,
  return `{ gps:false, ... }` -> `parseGps` returns `null` -> "no fix", SHM stays
  simulated. No app change needed.
- **Poll wiring:** gate `online` on the HTTP response, NOT on whether a fix parsed.
  A 200 (even with `gps:false`) => `online:true`. Only the `catch` (proxy truly
  unreachable) => `online:false` + "DEVICE OFFLINE". Otherwise a mocked 200 wrongly
  declares an outage.
- Set `DEFAULT_IP` in `vite.config.js` to the device's REAL LAN IP so the proxy
  points correctly on a fresh dev-server start (before the user types anything).
- The `configureServer` hook is DEV-ONLY — `vite build`/`preview` has no proxy and
  no mock; the production bundle will still 502 on that path. Dev is the target.
- Verify the mock LIVE (you can — unlike raw device reachability): start a
  throwaway `npx vite --port 5200 --strictPort` via `terminal(background=true)`,
  `curl -w "\n-> %{http_code}\n" http://localhost:5200/edge-api/sensors.json`
  (expect 200 + JSON), then `process(action='kill')`. Inline `&` is rejected by
  the shell guard.

## Pitfall: 'real'-mode telemetry freezes on a 200 (partial envelope)
Even when the fetch SUCCEEDS (200, no throw), the `real` poll branch can leave
the SHM board dead: it only advances `sensorPayloads` / `deviceStatus` IF the
envelope carries a `sensorPayloads` array / `deviceStatus`. A LAN device like
phone "IP Webcam" returns a raw GPS envelope (`{ gps:false, mocked:true }`)
with NEITHER → video plays, telemetry frozen. This is NOT a 502/missing-
endpoint case (that throws → catch → OFFLINE). Symptom the user reports:
"camera works but the sensor/location telemetry is still not updating."

Fix: treat every edge envelope as PARTIAL. If `sensorPayloads` is present and
non-empty use it; else fall back to local `tickSensors(prev)` jitter. Same for
`deviceStatus` vs a `parseGps()` fix. On `catch` also keep jittering (don't
freeze). Full recipe in `references/real-mode-telemetry-freeze.md`.

## Pitfall: cloud-API proxy prefix 400s in PRODUCTION (proxy is dev-only)
The LAN device recipe is explicit that `configureServer`/proxy is DEV-ONLY, but the
cloud-API variant hides a sharper trap. When you route an API call through a proxy
prefix (e.g. `/api-vessel`) and `rewrite` strips it, the **dev** request to the
upstream is correct because Vite's proxy consumes the prefix. In a **production
build** (`vite build` + any static host) there is no proxy, so the browser sends the
bare `/api-vessel/v1/location/vessels/bounding-box` to the production origin — which
does NOT know the `/api-vessel` route — and the upstream (or your host) returns
**HTTP 400 Bad Request**. Misdiagnosed as "the `filter.` params are malformed" when
the real cause is the un-stripped prefix.

Symptoms: works perfectly on `localhost:5174`, 400 in prod. The params (even when
assembled with `URLSearchParams`) are fine — `URLSearchParams` does NOT percent-encode
the dot in `filter.latBottom`, so dotted query keys serialize verbatim.

Two robust fixes (pick one):
1. **Dual-mode base (preferred for SPAs).** Build the URL base from an env flag:
   dev → `/api-vessel/v1/...` (rides the proxy); prod → absolute
   `https://api.vesselapi.com/v1/...` (calls the real origin, no prefix to strip).
   ```js
   const VESSELAPI_BASE =
     import.meta.env.DEV
       ? '/api-vessel/v1/location/vessels/bounding-box?' + params.toString()
       : 'https://api.vesselapi.com/v1/location/vessels/bounding-box?' + params.toString()
   ```
   (Vite exposes `import.meta.env.DEV`.) Callers stay unchanged.
2. **Prod gateway mirror.** Have the production host also proxy `/api-vessel` →
   `https://api.vesselapi.com` (same `rewrite` as Vite). Only viable if you control
   the host (nginx/CF worker/etc.).

Full walkthrough + the `URLSearchParams` dot-quirk proof in
`references/cloud-api-cors-proxy.md`.

## Diagnosing 502s in the console (three distinct causes — diagnose before fixing)
- `/edge-api/sensors.json` => 502/404 is most often **(a) endpoint missing on the
  device** — common with IP Webcam, which serves video/snapshot but not sensors.json.
  Confirm by hitting the device's OTHER paths: if `/video` + `/shot.jpg` return 200
  but `/sensors.json` 404s, the device simply doesn't expose it. Fix: mock the path
  (above) OR point at the real endpoint IP Webcam does serve. (b) **proxy mis-aimed**
  — target IP unreachable / stale / device asleep (the override cookie wasn't saved,
  or saved to a stale IP). Fix: enter the device's real LAN IP (the one that works in
  its own browser tab) into Settings -> Save. (c) **wrong path prefix** — bare-path
  502s (`video:1`, `shot.jpg:1` with no `/edge-api` prefix) = a CODE bug: a component
  requested the un-proxied path. Grep for hardcoded device paths and route them through
  `/edge-api`.
- Screenshot vision models routinely misread localhost dev screenshots (Chrome
  DevTools, fake buttons, invented labels). Trust the user's words + the raw console
  text over a vision description.

## Pitfall: DEFAULT_IP in vite.config.js drifts when the LAN subnet changes
The proxy's `DEFAULT_IP` is hardcoded in `vite.config.js`. When the Mac hops networks
(home `192.168.0.x` → phone-hotspot `172.20.10.x`, office, etc.) the device's REAL LAN IP
changes, but `DEFAULT_IP` stays on the old subnet. Symptom: you fixed the dev-server
binding (`--host`), the S22 can now REACH `http://<LAN-IP>:5174`, but the live feed / snapshot
still 502s — because the proxy aims at the stale `192.168.0.6:8080` while the device is now
at `172.20.10.x`. This is a *subset* of the 502-cause "(b) proxy mis-aimed" above, but worth
calling out because it bites exactly after you've "fixed" connectivity and the dev server
restart wiped the override cookie (a fresh `npm run dev` re-reads `DEFAULT_IP`, not the
last UI-saved value, unless the cookie persisted).

Two-state fix:
- **Quick (no restart):** open the app's Settings → enter the device's CURRENT LAN IP (the
  one that works in the device's own browser tab) → Save. The UI writes the override cookie
  + bumps `connSeq`; the `router` fn re-points live traffic immediately. No dev-server restart.
- **Durable (edit config):** update `DEFAULT_IP` in `vite.config.js` to the device's real
  current LAN IP so a fresh dev-server start points correctly before the user types anything
  (mirrors the guidance already in the mock-endpoint section). Then restart dev.

Detection: `lsof` shows the dev server on `*:<port>` (reachable), but `curl
http://<LAN-IP>:<port>/edge-api/shot.jpg` 502s → the proxy target is the stale subnet.
Confirm the device's real IP (`ipconfig getifaddr en0` on the Mac; the device's own Wi-Fi
settings) and reconcile with `DEFAULT_IP`.

- `npm run lint && npm run build` green, then `rm -rf dist`.
- Live device reachability CANNOT be verified from the agent side (no LAN access). State that explicitly; the user must eyeball localhost with the device's real IP entered.

## References
- `references/mjpeg-reset.md` — full React reset pattern + manual ↻ button.
- `references/offline-gating.md` — honest online/offline state + SNAP-button fix.
- `references/mock-missing-endpoint.md` — intercept a device-missing path via a
  `configureServer` middleware plugin (`enforce:'pre'`) + poll-wiring so a mocked
  200 doesn't flip the UI to OFFLINE; includes live curl verification.
- `references/real-mode-telemetry-freeze.md` — when the fetch SUCCEEDS (200) but
  the `real`-mode branch freezes SHM because the envelope has no `sensorPayloads`
  array; local-jitter fallback recipe (distinct from missing-endpoint 502).
- `references/cloud-api-cors-proxy.md` — CORS-bypass proxy for a cloud SaaS API
  (valid cert, fixed target, no `secure:false`), the production-400 prefix trap,
  and the dual-mode `import.meta.env.DEV` base fix.
- `references/default-ip-drift.md` — DEFAULT_IP in vite.config.js goes stale when the
  LAN subnet changes; live feed 502s even after the dev server is LAN-reachable; UI
  override vs config-edit fix.
