# Telemetry Integrity — Never Fabricate Fleet Data (MARU Maritime Layer)

## The rule
For an operational / monitoring dashboard, NEVER present simulated or estimated
positions as if they were live telemetry. If the live feed is unreachable, the
app must CLEAR the canvas and visibly REPORT the connection failure — not fill
the map with a "high-fidelity local simulation."

## Why this was a hard correction
Commit history on `my-digital-twin` shows the arc:
- `55581b0` feat(layers): integrate live maritime fleet telemetry …
- `9cb28ca` fix(egress): resilient vesselapi fallback to simulated fleet on network failure  ← added sim fallback
- `f499701` fix(layers): enforce telemetry integrity coloring for maritime tracking  ← green/red split
- `d7b8ca3` refactor(egress): remove simulation fallback, report vesselapi connection failure  ← SIM REVOKED
- `fcd55b9` feat(egress): align vesselapi driver with official production bounding-box routing  ← verbatim spec
- `af82fc8` diag(egress): add lightweight vesselapi connection trace + auth-state check  ← Layer 1 trace

The user explicitly ordered the fallback REMOVED: "We are removing the fake data
layer entirely to ensure operational integrity. The app must fetch true live
telemetry or clearly report the connection failure."

## Production pattern (replaces the sim fallback)
`src/services/egressDrivers.js` · `fetchLiveVessels(gov)` returns a discriminator:

```js
export async function fetchLiveVessels(gov) {
  const verdict = gov?.ask?.(VESSELAPI_PROVIDER)
  if (!verdict || !verdict.allow) return { vessels: [], error: null } // budget deny: keep last-known fleet
  // Lightweight auth-state check (boolean presence only — never the key):
  console.log('[egress][vesselapi] Auth initialization state:',
    !!import.meta.env.VITE_VESSEL_API_KEY)
  try {
    const key = import.meta.env.VITE_VESSEL_API_KEY
    const res = await fetch(VESSELAPI_BASE, { headers: { Authorization: `Bearer ${key}` } })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const json = await res.json()
    const list = Array.isArray(json?.data) ? json.data
               : Array.isArray(json?.vessels) ? json.vessels
               : Array.isArray(json) ? json : []
    gov?.record?.(VESSELAPI_PROVIDER)
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

Caller (`MaritimeEntities.jsx`) then:
- on `error` → `setVessels([])`, `setSelected(null)`, show a red
  `vessel-hud-error` banner: `🔴 VESSEL TELEMETRY OFFLINE — {message}`.
- on budget deny (`error === null` + empty) → keep last-known fleet, show the
  existing `.vessel-hud-notice` ("Egress budget reached").
- `verified` flag stays `true` on normalized vessels as a correctness marker;
  the green/red canvas color split is no longer needed (everything is live green).

## Routing + domain corrections (chronological)
- `https://api.vesselapi.io/...` → `https://api.vesselapi.com/...`
  (`ERR_NAME_NOT_RESOLVED` was a config typo, not a real outage.)
- Production route is `https://api.vesselapi.com/v1/location/vessels/bounding-box`
  with **discrete `filter.` query params** (`filter.latBottom`, `filter.lonLeft`,
  `filter.latTop`, `filter.lonRight`) — NOT a compound `?bbox=minlat,minlon,...`.
- Response envelope: read `res.data` first, then `res.vessels`, then a bare
  array. Official fields: `latitude`/`longitude`/`vessel_name` (fallback `name`)/
  `speed` (fallback `sog`)/`course` (fallback `cog`). Auth header:
  `Authorization: Bearer ${VITE_VESSEL_API_KEY}`. Wire these VERBATIM from the
  user-supplied spec — don't guess param names or casing.

## Pitfall — don't reintroduce the sim fallback
The "resilient simulation fallback so the demo never goes blank" framing was
user-approved, then REVOKED in the same project. General lesson: for THIS user's
ops/monitoring tools, do NOT default to fabricating fallback data — even for a
pitch. If you think a demo needs data when the feed is down, surface it as a
clearly-labeled placeholder or ask, never silently render fake vessels as live.
