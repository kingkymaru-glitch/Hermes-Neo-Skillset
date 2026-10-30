# 'real'-mode poll freezes telemetry when the envelope has no sensorPayloads

## The trap (distinct from "endpoint missing")
When `VITE_EDGE_MODE='real'` (or `VITE_EDGE_API_URL` is set, which the S22
android path uses), the poll loop's `real` branch often looks like this:

```js
const data = await res.json()
if (Array.isArray(data.sensorPayloads)) setSensorPayloads(data.sensorPayloads)
if (data.deviceStatus) setDeviceStatus((d) => ({ ...d, ...data.deviceStatus, online: true }))
```

A LAN device like phone "IP Webcam" serves a raw GPS envelope
(`{ gps:false, mocked:true }`) — it has NO `sensorPayloads` array and often
no `deviceStatus`. So:
- video (separate `/video` feed) plays fine,
- but `sensorPayloads` is never advanced → the SHM cards look DEAD while the
  video is live. Classic "stale telemetry" the user sees as a UI bug.

Note this is different from the missing-endpoint 502: there the fetch *throws*
and the catch flips OFFLINE. Here the fetch *succeeds 200* but the branch just
does nothing because the shape doesn't match.

## Fix — local-jitter fallback so the board never looks dead
```js
const data = await res.json()
if (Array.isArray(data.sensorPayloads) && data.sensorPayloads.length) {
  setSensorPayloads(data.sensorPayloads)          // structured bridge → use it
} else {
  setSensorPayloads((prev) => tickSensors(prev)) // no array → synthesize SHM locally
}
if (data.deviceStatus) {
  setDeviceStatus((d) => ({ ...d, ...data.deviceStatus, online: true }))
} else {
  const fix = parseGps(data)                     // pull GPS if envelope has it
  setLiveGeo(fix || null)
  setDeviceStatus((d) => ({ ...d, online: true, gpsFix: !!fix }))
}
```
On `catch` (bridge unreachable) ALSO keep jittering so the board stays alive:
```js
} catch {
  setSensorPayloads((prev) => tickSensors(prev)) // keep alive, not frozen
  setConnection('offline')
}
```
`tickSensors(prev)` is the same synthetic-jitter fn the mock/android modes use —
drift each channel, re-classify flag by thresholds. Reuse it; don't re-invent.

## Rule of thumb
For any edge-device poll branch, assume the device's envelope is PARTIAL.
Advance every state slice by a sensible fallback (structured value if present,
local synthesis otherwise) so no part of the UI can freeze on a 200 response.
Only a thrown fetch (proxy 502 / connection refused) is a real outage.
