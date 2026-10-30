# Layer 2 — Edge Data Coordination Layer (decoupled data pipeline)

Project: `my-digital-twin` (MARU Box 1 Spatial Base). The user's "Layer 2" is an
independent, map-agnostic data orchestration layer that streams telemetry from a
physical edge computer at a remote site. It is intentionally decoupled from the
Cesium canvas — `src/context/EdgeDataContext.jsx` imports NOTHING from
`cesium`/`resium`.

## Shape
- `EdgeDataProvider` — owns all stream state (no map state here).
- `useEdgeData()` — consumer hook; throws if used outside the provider.

## State
```
connection      'mock' | 'connecting' | 'live' | 'offline'
deviceStatus    { host, ip, online, uptimeSec, cpuLoad, memUsedPct }
sensorPayloads  [ { id, name, metric, unit, value, status: 'nominal'|'alert' } ]
lastSeen        epoch ms of last successful pull (null until first tick)
endpoint        VITE_EDGE_API_URL or 'mock://edge-sim.local'
```

## Poll loop
`setInterval(pull, POLL_MS)` where `POLL_MS = VITE_EDGE_POLL_MS || 2000`.
`pull()` runs immediately once, then on the interval. Cleanup clears the timer
and sets an `alive=false` guard so React StrictMode's double-invoke can't leak.

## Mock → real swap (env only — zero downstream change)
```
const EDGE_API_URL = import.meta.env.VITE_EDGE_API_URL || ''
const POLL_MS = Number(import.meta.env.VITE_EDGE_POLL_MS) || 2000
```
- **Mock mode** (no `VITE_EDGE_API_URL`): synthesize an SHM stream. `seedSensors()`
  builds 4 channels (north-abutment tilt °, girder strain µε, pier vibration
  mm/s RMS, bearing temp °C); `tickSensors(prev)` jitters each value and flips
  `status:'alert'` past a per-metric threshold. `deviceStatus` uptime/cpu/mem
  drift each tick.
- **Live mode** (env set): `await fetch(EDGE_API_URL, { headers:{ Accept:
  'application/json' } })`; on `!res.ok` throw → `connection='offline'`. On OK,
  read `{ sensorPayloads, deviceStatus }`, set state, `connection='live'`,
  `lastSeen=now`. The try/catch keeps the loop from dying on a flaky edge box.
- **Why this matters**: swapping the simulator for a real remote edge computer is
  a ONE-LINE config change (`VITE_EDGE_API_URL=http://<edge-ip>:port/telemetry`).
  No component edits.

## Consumption (test wire example)
Wrap the app once:
```jsx
return (
  <EdgeDataProvider>
    <div className="dt-root"> … <EdgeStatusBadge /> … </div>
  </EdgeDataProvider>
)
```
`EdgeStatusBadge` (a module-scope component so it renders INSIDE the provider)
taps the stream with no map coupling:
```jsx
function EdgeStatusBadge() {
  const { connection, deviceStatus, lastSeen } = useEdgeData()
  const dot = connection === 'live' ? 'ok' : connection === 'offline' ? 'bad' : 'mock'
  const seen = lastSeen ? `${Math.round((Date.now() - lastSeen) / 1000)}s ago` : '—'
  return <span className={`dt-edge edge-${dot}`} title={`${deviceStatus.host} · ${deviceStatus.ip}`}>
    <i className="edge-dot" />{connection === 'live' ? 'Edge' : 'Edge (sim)'}
    <span className="edge-seen">{seen}</span>
  </span>
}
```
CSS: glass pill, `.edge-dot` glowing currentColor, variants `.edge-mock`
(blue) / `.edge-ok` (green) / `.edge-bad` (red), `.edge-seen` tabular-nums.

## oxlint note
File-level `/* oxlint-disable react/only-export-components */` at the top silences
the fast-refresh warning for context+hook colocation. See SKILL.md Pitfalls.

## Next (user's call, not yet built)
- Map `sensorPayloads` into the left command drawer (live sensor list).
- Add a WebSocket variant alongside the poll loop for true push streaming.
- Wire `deviceStatus` into a Box-2 device panel.
