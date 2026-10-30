# Pitfall 11 — "curl works but the browser fetch fails" is almost always CORS, not a code bug (bundle static JSON into public/)

## Symptom
A `fetch(url)` to a third-party JSON endpoint returns data fine via `curl` (HTTP
200, body present) but the in-app `fetch` throws / the layer shows "FEED OFFLINE —
Network error". No network issue on the server side; the data is clearly reachable.

## Why
`curl` does NOT enforce CORS. The browser DOES. A cross-origin `fetch` from
`http://localhost:5174` to `https://some-other-host/api.json` is blocked by the
browser unless the response carries an `Access-Control-Allow-Origin` header. Many
public datasets (e.g. `submarinecablemap.com`, some government GeoJSON) send NO CORS
header, so the browser silently blocks the response even though `curl` succeeds.

## Diagnostic (one curl proves it)
```
curl -s -D - -o /dev/null -H "Origin: http://localhost:5174" "https://HOST/path.json" \
  | grep -i "access-control\|http/"
```
- If there is NO `access-control-allow-origin: *` line → it is CORS. The browser
  will block it. `curl` working was a red herring.
- If `access-control-allow-origin: *` IS present → the failure is something else
  (auth, payload, code), not CORS.

## Fix (KISS, no backend): bundle the data into the app
For effectively-static datasets (reference GeoJSON, cable maps, country borders,
boundary files — anything that doesn't change minute-to-minute), download it ONCE
into `public/` and load from the same origin. Vite serves `public/*` at `/`, so a
`public/cables.geojson` is fetchable at `/cables.geojson` with NO CORS, and it
also works in the production build (Vite copies `public/` into `dist/`).

```
# download once
curl -s "https://HOST/path.json" -o public/cables.geojson
# verify it ships
ls -la dist/cables.geojson   # after build
```

Loader pattern (try local first, fall back to remote so it still works in dev
without the asset, and auto-heals if the asset is missing):
```js
const LOCAL = '/cables.geojson'
const REMOTE = 'https://HOST/path.json'
async function loadJson() {
  try {
    const res = await fetch(LOCAL)
    if (res.ok) return await res.json()
  } catch { /* fall through to remote */ }
  const res = await fetch(REMOTE)
  if (!res.ok) throw new Error(`remote ${res.status}`)
  return await res.json()
}
```
Verified green in a R-Tessera rebuild: `submarinecablemap.com/api/v3/cable/cable-geo.json`
sent no CORS header (browser-blocked, "CABLE FEED OFFLINE"), fixed by bundling
`public/cables.geojson` (718 features) and loading local-first.

## When NOT to bundle
If the data is genuinely live (per-second telemetry, user-specific queries, paid
APIs with secrets), bundling is wrong — use a **dev proxy** (`server.proxy`, see
Pitfall 2) for localhost and a serverless function / same-origin route for prod.
Bundling is for static reference data only.

## Related
- Pitfall 2 — dev proxy for self-signed / CORS backend during development.
- Pitfall 8 — stale dev server squatting the port; always kill stale `vite`
  before starting a fresh one (use `--strictPort` to fail fast instead of silently
  moving to :5175 and serving stale code at the old port).
