# AISStream — LIVE WebSocket vessel feed (NOT REST)

AISStream is a **persistent WebSocket** (`wss://stream.aisstream.io/v0/stream`),
a completely different paradigm from VesselAPI's REST polling. This reference
captures what actually made it work on MARU after a multi-session debug (key
refused → "closed" → "silent" → live dots), so the next session starts past the
pitfalls. The live code lives in `src/services/aisStreamClient.js` +
`src/components/MaritimeEntities.jsx`.

> Telemetry-integrity rule still applies: live-only, NO simulated fallback. If
> the WS is down, clear the canvas + show the red offline banner (same as
> VesselAPI). Don't paint fake boats.

## Connect handshake (exact shape — wire verbatim)
```js
ws.send(JSON.stringify({
  APIKey: import.meta.env.VITE_AISSTREAM_API_KEY,
  BoundingBoxes: [ /* array of boxes */ AIS_BBOX ],
  FilterMessageTypes: ['PositionReport'],
}))
```
- `BoundingBoxes` is **an array of boxes**; each box is a **4-corner `[lat, lon]`
  tuple list in SW, NW, NE, SE order**.
- One box: `[[ [lat,lon], [lat,lon], [lat,lon], [lat,lon] ]]`.

## TWO distinct failure modes — read the banner, don't guess
1. **"connection closed" (e.g. code 1008) = handshake REJECTED.**
   Cause: bad key OR wrong `BoundingBoxes` format. The server closes the socket
   *instantly*. The #1 root cause we hit: sending `BoundingBoxes` as a keyed
   object `{lat_min:…, lat_max:…}` instead of the tuple array. **The tuple array
   is mandatory** — a keyed object makes AISStream reject the handshake and drop
   the socket. Fix once, never reintroduce the object form.
2. **"silent connection" = handshake ACCEPTED, key valid, but zero messages.**
   Cause: the box is **too wide** for the free plan's messages/min quota. The
   server sends *nothing* instead of disconnecting. This is NOT an error — it's
   the free tier silently throttling an oversized request. Fix = **shrink the
   box** (see quota note below). We went: full Malacca Strait (98–104.5°E, silent)
   → Singapore Strait (102.7–104.4°E, worked) → Lumut (100.3–100.85°E, current).

## Free-tier quota (the silent-connection driver)
- Free AISStream: **no charges**, but caps messages/min. Asking for a huge box
  (entire strait = thousands of vessels) blows the cap → server sends silence.
- **Fix is always: smaller box.** A tiny box (≈0.5°×0.5°, e.g. Lumut) sits
  comfortably in quota and still shows real traffic.
- AISStream lets you pass **multiple boxes** in `BoundingBoxes` — to cover a
  wider area within quota, split it into several small boxes rather than one
  giant one.
- If still silent after shrinking: widen slightly west (more open strait =
  more passing traffic) or split into 2 small boxes.

## Account / verification (GitHub OAuth gotcha)
- Signing up with GitHub sends the verify email to the address GitHub exposes.
  If the user has **"Keep my email address private" ON in GitHub**, that address
  is `noreply@github.com` → the verify email vanishes into a void, user sees
  nothing. The account then sits "unverified."
- GH-OAuth accounts are **often auto-verified anyway**, so the key may work
  without clicking anything. Don't assume the missing email = broken key.
- If the WS still shows "closed (1008) / key invalid" after the tuple-format fix,
  the account is genuinely unverified: have the user turn OFF "private email" in
  GitHub, resend the verification from aisstream.io, OR change the account email
  to a real one. Also check Spam/Junk.

## Camera — app booted over Panama (the silent killer you can't see)
- The default camera was parked over **Panama** (the demo site). Even after
  vessels streamed in, they spawned 18,000 km away in the strait and the user
  saw "0 vessels" with no clue. **Always fly the camera to the target area on
  first AISStream connect.**
- Do it **once-per-session** (guard with a `useRef` flag) so reconnects don't
  yank the operator's view.
- **Deep-space-safe:** only fly if the camera is currently very far out
  (`camHeight > 1.0e6` m). If already zoomed in on the area, don't move it.
- Pattern (in `MaritimeEntities.jsx`, needs `import * as Cesium from 'cesium'`
  and a `useCallback`): on AISStream `status` → connected, compute
  `Cesium.Cartesian3.fromDegrees(lon, lat, height)` for the area and call
  `viewer.camera.flyTo({ destination, orientation:{heading:0,pitch:-45,roll:0},
  duration:2.0 })`. For a far-out start, `setView` to a high altitude first, then
  `flyTo` the lower destination.
- Current Lumut target: `100.61, 4.23`, height ≈ 350 km. (Singapore Strait was
  `103.4, 1.4`.)

## Error surfacing (so the banner tells the truth)
- Capture the **real** close code + reason in `ws.onclose`/`ws.onerror` and push
  it into the banner text. With the generic "closed" message the user can't tell
  "bad key" from "bad bbox" from "quota silence." Surface `event.code` +
  `event.reason` (and the browser's `error` detail on `onerror`).

## Env / secrets
- Key: `VITE_AISSTREAM_API_KEY` in `.env` (gitignored — line 11). Never commit
  the key; refer to it as `[REDACTED]`. Live-only, CORS-clean from the browser.

## Checklist before telling the user it's fixed
- [ ] `BoundingBoxes` is the tuple-array form (not keyed object) → kills "closed"
- [ ] box is small enough for the free quota → kills "silent"
- [ ] camera flies to the area on connect → kills "0 vessels over Panama"
- [ ] account verified (or GH-OAuth auto-verified) → key accepted
- [ ] banner surfaces real close code/reason for future diagnosis
