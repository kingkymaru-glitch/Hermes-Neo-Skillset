# Cloud SaaS API → Vite dev-proxy (CORS bypass + production-400 trap)

Use when a browser-side fetch to a public API fails with a CORS preflight error
(`OPTIONS` 4xx, or the console shows "blocked by CORS policy: No
'Access-Control-Allow-Origin'"). The API is server-side reachable (no self-signed
cert), so this is the LAN-recipe's simpler cousin: no `secure:false`, no dynamic
`router`.

## vite.config.js
```js
export default defineConfig({
  plugins: [react(), cesium()],
  server: {
    port: 5174,
    proxy: {
      '/api-vessel': {
        target: 'https://api.vesselapi.com',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api-vessel/, ''), // upstream sees /v1/...
      },
    },
  },
})
```
- `changeOrigin: true` rewrites the Host header so the upstream accepts it.
- `rewrite` strips the prefix so the upstream receives its real path
  (`/v1/location/vessels/bounding-box`). Without it the upstream gets
  `/api-vessel/v1/...` → 404/400.
- **Restart the dev server** after editing `vite.config.js` — Vite reads it only at
  boot; HMR will NOT register a new proxy.

## Driver (src/services/egressDrivers.js)
```js
// Dev: rides the /api-vessel proxy. Prod: absolute URL (see dual-mode below).
const VESSELAPI_BASE = (() => {
  const params = new URLSearchParams()
  params.append('filter.latBottom', '2.0')
  params.append('filter.lonLeft', '100.0')
  params.append('filter.latTop', '7.0')
  params.append('filter.lonRight', '105.0')
  return `/api-vessel/v1/location/vessels/bounding-box?${params.toString()}`
})()
```
Bearer auth passes straight through the proxy (headers are forwarded):
```js
const res = await fetch(VESSELAPI_BASE, {
  headers: { Authorization: `Bearer ${import.meta.env.VITE_VESSEL_API_KEY || ''}` },
})
```

## Proof: URLSearchParams does NOT encode the dot
The user may ask to assemble dotted query keys (`filter.latBottom`) "cleanly" to
avoid distortion. Confirmed empirically:
```js
const p = new URLSearchParams()
p.append('filter.latBottom', '2.0'); p.append('filter.lonLeft', '100.0')
p.append('filter.latTop', '7.0'); p.append('filter.lonRight', '105.0')
p.toString()
// => "filter.latBottom=2.0&filter.lonLeft=100.0&filter.latTop=7.0&filter.lonRight=105.0"
```
The `.` stays a literal dot (it is not a reserved char for query values). So a
URLSearchParams-built URL is byte-identical to a hardcoded equivalent — the refactor
improves robustness, not wire format. Good to know before "fixing" a supposed
encoding bug.

## THE TRAP: works in dev, 400 in production
Because the proxy only exists under `vite dev`, the relative `/api-vessel/...` path
is correct in dev (Vite strips it) but **400s in a production build** — there the
browser hits your static host/origin with the bare `/api-vessel/v1/...` path, which
nothing strips, so the upstream (or your host) returns HTTP 400 "Bad Request".
Symptom: green on `localhost:5174`, 400 in prod. Easily misread as malformed params;
it is the un-stripped prefix.

### Fix A — dual-mode base (preferred for SPAs)
```js
const VESSELAPI_BASE =
  import.meta.env.DEV
    ? `/api-vessel/v1/location/vessels/bounding-box?${params.toString()}`
    : `https://api.vesselapi.com/v1/location/vessels/bounding-box?${params.toString()}`
```
`import.meta.env.DEV` is `true` under `vite dev`, `false` in `vite build`. Callers
untouched. Prod now calls the real origin with no prefix to strip.

### Fix B — mirror the proxy in prod
If you control the host, proxy `/api-vessel` → `https://api.vesselapi.com` (nginx /
Cloudflare Worker / etc.) with the same `rewrite`. Keep code on the relative path.

## Verification
- `npm run lint && npm run build` green, then `rm -rf dist`.
- Dev CORS fix CAN be verified internally: after a dev-server restart,
  `curl -w "\n-> %{http_code}\n" "http://localhost:5174/api-vessel/v1/location/vessels/bounding-box?filter.latBottom=2.0&filter.lonLeft=100.0&filter.latTop=7.0&filter.lonRight=105.0"`
  (expect 200 with the envelope, or a 401/403 if the API key is missing — NOT a
  CORS error). This confirms the proxy strips the prefix correctly.
- Production-400 can only be confirmed by the user deploying the built bundle; the
  dual-mode base is the structural guarantee.
