# AISStream live WebSocket integration (MARU maritime 2nd source)

Verified pattern for the `aisstream` branch of the maritime layer (commit
`95fa5b7`). AISStream.io is a FREE, CORS-clean live-AIS WebSocket — no dev
proxy, no per-poll rate-limit 429s (it's a push stream). The free tier caps the
**message rate** (drops excess positions), not a bill — confirm to the user they
won't be charged, no credit card required.

## Connect-message shape (THE #1 GOTCHA)

```js
// ⚠️ KEEP THE BOX SMALL. The free tier enforces a GEOGRAPHIC AREA quota, not
// just a message rate. A full-Malacca box (~1–6.5°N, 98–104.5°E) does NOT
// error and does NOT close the socket — the server simply sends NOTHING
// ("silent", 0 vessels, healthy-looking connection). Shrink to a small patch.
// Verified-live working box (Lumut, MARU):
const AIS_BBOX = [
  [3.9, 100.05],  // SW  (south of Lumut, open transit lane)
  [4.6, 100.05],  // NW  (north of Lumut, open transit lane)
  [4.6, 100.85],  // NE  (toward Pulau Pangkor / coast)
  [3.9, 100.85],  // SE  (south, anchorage + strait)
]
ws.send(JSON.stringify({
  APIKey: import.meta.env.VITE_AISSTREAM_API_KEY,
  BoundingBoxes: [AIS_BBOX],   // array of boxes, each box an array of [lat,lon] tuples
  FilterMessageTypes: ['PositionReport'],
}))
```

**Critical:** `BoundingBoxes` must be an array of boxes, each box a 4-corner list
of `[lat, lon]` tuples. Sending a keyed object `{lat_min, lat_max, ...}` makes
the server REJECT the handshake and **close the socket immediately** after
opening → the only symptom is `onclose` firing right after `onopen` ("AISStream
connection closed"). This was a real bug shipped to the user; the tuple format
fixed it.

## Diagnosis playbook (when the banner says closed)

AISStream closes instantly on any of: invalid key, **unverified account email**,
wrong BoundingBoxes format. Surface the real reason, don't swallow it:

```js
ws.onclose = (ev) => {
  const reason = ev?.reason || ''
  const code = ev?.code
  let msg = 'AISStream connection closed.'
  if (code === 1008 || reason) {
    msg = `AISStream closed (${code || 'n/a'})${reason ? `: ${reason}` : ''}. ` +
          `Check the API key is active/verified and the bounding-box format is valid.`
  }
  onStatus({ code: 'AISSTREAM_CLOSED', message: msg })
}
ws.onerror = (ev) => {
  const detail = ev?.message || ''
  onStatus({ code: 'AISSTREAM_ERROR',
    message: detail ? `AISStream WebSocket error: ${detail}`
                    : 'AISStream WebSocket error (could not reach stream.aisstream.io).' })
}
```

Triage order when "connection closed":
1. Key present? (`AISSTREAM_NOKEY` if missing — that's a setup hint, render amber not red.)
2. Account email verified at aisstream.io? (most common remaining cause after a
   correct client — free signup still needs the verification click.)
3. BoundingBoxes format = tuple array? (the bug above.)
4. Box too large? Free tier is a rate cap, a giant global box just yields fewer
   messages, not an error.

## Message handling

- Server sends a JSON array of message objects per frame: `const arr = Array.isArray(msg) ? msg : [msg]`.
- Filter `m.MessageType === 'PositionReport'`; read position from `m.MetaData`
  (`latitude`/`longitude`/`cog`/`sog`/`MMSI`/`Ship.Name`/`Ship.Destination`).
- Keep `tracks: Map<MMSI, {v, trail:[[lon,lat]...], t}>`; append to `trail`
  (cap ~24 pts), prune entries silent >15 min (ghosts). Emit keep-latest-per-MMSI
  list to the renderer.
- **Governance:** record ONCE per connection (`gov.record('aisstream_maritime')`
  in `onopen`), NOT per message — a busy strait pushes hundreds/sec and
  per-message counting trips the circuit breaker and kills ALL egress. Reuse the
  `vesselapi_maritime` budget so the two sources A/B fairly.

## Camera framing (do NOT skip)

A live feed is INVISIBLE if the Cesium camera is parked elsewhere (the app boots
over the demo site / Panama). On first successful `onopen`, fly the camera to the
feed region. Generic pattern lives in cesium-resium-react
(`references/live-feeds-and-ab-data-sources.md`): deep-space-safe
`setView`→`flyTo`, guarded once-per-session so reconnects don't yank the view.

## No simulated fallback

Per the telemetry-integrity rule: if AISStream is down, CLEAR the canvas and show
an amber/red offline banner. Never render fake vessels. A 429 only applies to
poll sources (VesselAPI); AISStream is push and won't 429 — but on `onclose`
keep last-known fleet on screen (nothing lost, it just went quiet).
