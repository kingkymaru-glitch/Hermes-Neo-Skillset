# AISStream Live Provider + Maritime Error Taxonomy (MARU)

Two durable learnings from the "make the AIS ship look like a real Malacca
tracker" pass (commits `d7625d3`, `43dda8e`). Both belong to the live-maritime
class: (1) a FREE live 2nd source and (2) how to classify feed failures so the
operator is told the truth instead of panicking.

## 1 · AISStream — selectable 2nd vessel provider (live, not historical)

Why it exists: VesselAPI is a **4h-historical AIS archive** (dedup per MMSI =
only ~2 ships at Port Klang). AISStream.io is a **FREE, CORS-clean WebSocket
push of CURRENT positions** — so the strait actually looks busy. Adopted as a
*selectable* 2nd source (NOT a swap) so the two can be A/B'd.

Key differences from VesselAPI (don't carry assumptions across):
- **No proxy.** `wss://stream.aisstream.io/v0/stream` is CORS-clean; the browser
  connects directly. VesselAPI NEEDS the `/api-vessel` Vite proxy (rejected
  preflight otherwise). Env var: `VITE_AISSTREAM_API_KEY` (free at aisstream.io).
- **Push, not poll.** Open socket, send subscription, get `PositionReport`
  frames. Nothing to poll, no rate-limit storm like VesselAPI's 429s.
- **Live only** — no 4h rewind. Answers the earlier "why only 2 ships?" gap.

Canonical client shape (`src/services/aisStreamClient.js`):
```js
export function connectAISStream(gov, onUpdate, onStatus) {
  const key = import.meta.env.VITE_AISSTREAM_API_KEY
  if (!key) { onStatus({ code:'AISSTREAM_NOKEY', message:'Add VITE_AISSTREAM_API_KEY to enable AISStream.' }); return { stop(){} } }
  const ws = new WebSocket('wss://stream.aisstream.io/v0/stream')
  ws.onopen = () => {
    ws.send(JSON.stringify({ APIKey: key, BoundingBoxes:[{lat_min:1,lat_max:6.5,lon_min:98,lon_max:104.5}], FilterMessageTypes:['PositionReport'] }))
    onStatus(null)
    if (!recorded) { gov?.record?.('aisstream_maritime'); recorded = true }
  }
  ws.onmessage = (ev) => { /* keep-latest-per-MMSI + breadcrumb trail; emit on change */ }
  ws.onerror   = () => onStatus({ code:'AISSTREAM_ERROR', message:'AISStream WebSocket error.' })
  ws.onclose   = () => onStatus({ code:'AISSTREAM_CLOSED', message:'AISStream connection closed.' })
  return { stop(){ closed = true; ws?.close() } }
}
```
- **Per-MMSI keep-latest + breadcrumb trail** (last 24 pts); prune tracks silent
  15 min so the strait doesn't fill with ghosts. Trail = `[[lon,lat],...]` on each
  vessel; rendered as a fading Cesium polyline.
- **COG arrow billboard**: inline SVG ship-arrow data-URI (`VESSEL_ARROW_URI`),
  rotated by `cog` via `BillboardGraphics.rotation` so vessels visibly head
  along course — the signature AIS-console look. Use `Math.toRadians(90 - cog)`
  (Cesium rotation is CCW from east; arrow points north = up at cog 0).

GOVERNANCE PITFALL: record() the egress ONCE on `onopen`, NOT per message. A
busy strait pushes hundreds of pings/sec; per-message `gov.record('aisstream_maritime')`
would instantly trip the circuit breaker and kill ALL egress (vessel +
situational). Register an `aisstream_maritime` provider in `governanceRegistry.js`
that REUSES the same budget as `vesselapi_maritime` so the A/B is fair under one cap.

**Source selector UX** (`vesselProvider` state in `EdgeDataContext`):
- Two chips in the maritime row (VesselAPI | AISStream). Picking a chip sets the
  source but must NOT toggle the layer (`showMaritimeLayer` is separate).
- Row is enabled if EITHER key is present (the free AISStream tier is reachable
  without the paid VesselAPI key); tooltip mentions both keys.
- Default to `aisstream` when its key is present, else `vesselapi`.

## 2 · Maritime error taxonomy — 429 is NOT an outage

The original code treated every failure identically: clear fleet + red
"VESSEL TELEMETRY OFFLINE". That is WRONG for two very common, recoverable cases:
- **HTTP 429 (rate-limit)** — upstream free-tier quota hit. NOT a dead server.
  Keep the last-known fleet on screen; show amber "throttled — will refresh when
  the window resets." Nothing is lost.
- **Missing key (AISStream NOKEY / VesselAPI key absent)** — a SETUP hint, not an
  outage. Show amber "add VITE_*_API_KEY to enable", never red.

Classification pattern (drives banner colour + role):
```js
const isRecoverable = connError.code === 'VESSELAPI_THROTTLED' || connError.code === 'AISSTREAM_NOKEY'
className={isRecoverable ? 'vessel-hud-error vessel-hud-warn' : 'vessel-hud-error'}
role={isRecoverable ? 'status' : 'alert'}
// text: THROTTLED/NOKEY -> amber "throttled/setup"; else red "VESSEL TELEMETRY OFFLINE"
```
And in the VesselAPI poll effect, on a 429 do NOT `setVessels([])` — return early
after setting the amber notice so the last-known fleet stays rendered.

Detect 429 explicitly in `fetchLiveVessels` (don't let it fall through to a
generic `!response.ok` skip):
```js
if (response.status === 429) { rateLimited = true; continue }
if (!anyOk) {
  const code = rateLimited ? 'VESSELAPI_THROTTLED' : 'VESSELAPI_OFFLINE'
  throw new Error((rateLimited ? 'VesselAPI rate-limited (HTTP 429) — quota hit; fleet refreshes after window resets.' : 'All vessel tiles failed') + ` [${code}]`)
}
```

### CSS — `.vessel-hud-warn` (amber recoverable variant of `.vessel-hud-error`)
```css
.vessel-hud-warn { background: rgba(71,51,8,0.72); border-color: rgba(245,158,11,0.6); box-shadow: 0 0 14px rgba(245,158,11,0.25); color: #fde68a; }
.vessel-hud-warn .vessel-hud-error-dot { background:#f59e0b; box-shadow:0 0 8px #f59e0b; animation:none; }
```
Red `vessel-hud-error` is now reserved for genuine dead-server (TypeError /
network / DNS) only.

## Why this matters (UX lesson)
A red "OFFLINE" banner for a 429 or a missing-key hint reads as a CRASH to the
user and triggers panic. Recoverable conditions must be visually calm (amber,
role="status", no pulse animation). The error CODE — not the presence of an
error — decides severity.
