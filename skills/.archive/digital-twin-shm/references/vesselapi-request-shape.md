# VesselAPI — Live Request-Shape Progression (KNOWN-GOOD FINAL FORM)

Captures the exact error → fix arc from the maritime egress work so future
iterations on this API start from the WORKING shape instead of re-deriving it.
**LAST CORRECTED 2026-07-18 (two sessions, same day).** Session 1 reached a real
200 OK via DevTools Network capture (GET + `filter.*` + ≤4° span, no time
params). Session 2 added `time.from`/`time.to` and hit a NEW 400: the **time
window** (`time.to - time.from`) must not exceed 4h — found only by hitting the
live API directly and reading the 332-byte error body, NOT from the DevTools
"400 Bad Request" headline. Also learned the compact 1° box returns 0 vessels
while the full 4°-span Port Klang box returns ~20 (EMPIRICAL BOX PROBE below).
Prior versions wrongly crowned the `bbox` array / POST as the fix — dead end.
The GET + `filter.*` + ≤4° span + ≤4h window form below is what the live server
actually accepts (verified 200, ~20 vessels).

## Endpoint (dev)
Relative proxy path: `/api-vessel/v1/location/vessels/bounding-box`
(absolute in prod if you switch to a build-time env:
`https://api.vesselapi.com/v1/location/vessels/bounding-box`). The `/api-vessel`
prefix is ONLY resolved by the Vite dev proxy (vite.config.js) — a static
production build has no such route, so the bare path 400s unless prod serves an
equivalent gateway or you flip to the absolute URL via a `VITE_EDGE_MODE`-style
flag.

## FINAL KNOWN-GOOD fetch (dev) — proven 200 OK (live, 2026-07-18)

Lives as `buildVesselUrl()` in `src/services/egressDrivers.js`. Verified live:
HTTP 200, ~20 vessels in the Port Klang box.

```js
function buildVesselUrl() {
  const now = new Date()
  // API hard ceiling: time.to - time.from must not exceed 4h.
  const past4Hours = new Date(now.getTime() - 4 * 60 * 60 * 1000)
  const params = new URLSearchParams()
  // Port Klang box at the full 4°-span cap (returns ~20 live vessels).
  params.append('filter.latBottom', '2.0')
  params.append('filter.lonLeft', '100.5')
  params.append('filter.latTop', '4.0')
  params.append('filter.lonRight', '102.5')
  params.append('time.from', past4Hours.toISOString())
  params.append('time.to', now.toISOString())
  return `/api-vessel/v1/location/vessels/bounding-box?${params.toString()}`
}
const response = await fetch(buildVesselUrl(), {
  headers: { Authorization: `Bearer ${import.meta.env.VITE_VESSEL_API_KEY}` },
}) // GET (default), NO body, NO Content-Type
```
Span check: `|dLat| = 4.0 − 2.0 = 2.0°`, `|dLon| = 102.5 − 100.5 = 2.0°`,
**total = 4.0°** — exactly at the hard 4° cap (still accepted). Time window =
`now − 4h`, exactly at the hard 4h ceiling (still accepted). Both caps are
INCLUSIVE: sit at the boundary, don't cross it.

## Request-shape evolution (real error strings from the live server)
1. `GET` + oversized query `?filter.latBottom=2.0&…&latTop=7.0&lonRight=105.0`
   → `HTTP 400 Bad Request`. **Root cause was the box being too big**
   (|dLat|+|dLon| = 12°, later 15°), NOT the GET method. Misread at the time as
   "GET rejected" → wrongly switched to POST.
2. `POST` + JSON body `{ filter: { latBottom, lonLeft, latTop, lonRight } }` →
   `invalid_request_error` (server rejects the nested `filter` wrapper). → flatten.
3. `POST` + flat JSON body `{ latBottom, lonLeft, latTop, lonRight }` at root →
   `latTop must be greater than latBottom and lonRight must be greater than
   lonLeft`. Server reads keys LITERALLY and validates the inequalities on raw
   input. → NOT accepted.
4. `POST` + inverted flat keys (`latBottom:8, latTop:1, lonLeft:106, lonRight:99`)
   to satisfy a suspected server-side key-swap → **SAME literal inequality error**.
   The "server swaps the keys, so invert the values" theory was WRONG. Rolled back.
   Hard rule: if the validator enforces `latTop > latBottom` literally, inverting
   values only re-throws the identical error. Never ship a payload-shape theory
   without testing it against the live server.
5. `POST` + unified `bbox` array `[minLon,minLat,maxLon,maxLat]` → **DEAD END**.
   Shipped as a commit but the user later confirmed it never reached 200 OK;
   the official docs say the endpoint is GET with `filter.*` params. Abandoned.
6. **FINAL (confirmed 200 OK):** back to `GET` + `filter.*` query params, box
   tightened to ≤4° total span, and (session 2) `time.*` window capped at ≤4h.
   The earlier 400s were the span and the window, not the transport.

## TWO post-200 facts that matter more than transport
- **Empty fleet is still a 200.** The live 200 returned `Content-Length: 14`
  (`{"vessels":[]}`) — a successful but EMPTY vessel list for that exact box.
  So a green 200 with no cyan tracks on the map is "API working, no vessels in
  box", not a bug. **Box emptiness is real and region-dependent** (see EMPIRICAL
  BOX PROBE): the compact 1° Port Klang box returned 0 vessels; the full 4°-span
  Port Klang box returned ~20. If you expect traffic, widen the box toward the
  4° span cap or confirm VesselAPI coverage there. "Compact + high-traffic" was
  mutually exclusive in this region. Our response mapping reads the `vessels`
  key correctly, so empty data is upstream, not a parse fault.
- **"Egress budget reached" is OUR governance, not the API.** That notice
  (`MaritimeEntities.jsx` line ~211) fires from the client-side governance gate,
  not VesselAPI. `vesselapi_maritime` is registered with `sessionLimit: 100,
  dailyLimit: 100`; `effectiveCap` in NORMAL mode = `floor(min(100,100)*0.8)`
  = 80. Bumped from 5→100 so the 30 s poll survives a full partnership
  presentation. Counters persist in localStorage. Don't confuse it with an
  API-side rate limit (the live `X-Ratelimit-Remaining` header was ~145 —
  server-side was fine).

## EMPIRICAL BOX PROBE (2026-07-18, live)
A Python script sourced the key from `.env` and called the upstream directly
with several boxes (4h window each). Results (vessels):
- A — compact Port Klang `2.2–3.2 / 100.8–101.8` (span 1.0°): **0**
- B — Malacca lane `2.5–3.5 / 101–102` (span 2.0°): **0**
- C — wide Port Klang `2.0–4.0 / 100.5–102.5` (span 4.0°): **~20** ← used
- D — Strait `1.5–4.5 / 100.5–102.5` (span 5.0°): SKIP (>4° cap → 400)
- E — Johor `1.2–1.6 / 103.8–104.2` (span 0.8°): **~20** (different region)

Takeaway: probe boxes directly against the live API before committing to
coordinates — a green 200 means nothing if the box is empty. Use the probe
script pattern (curl/urllib, key from `.env`, no echo) to rank boxes by vessel
count in one run.

## Technique notes
- **TWO independent 400 causes — span cap AND time window.** Both are hard
  server-enforced limits (not transport/encoding):
  (a) **Span cap**: total `|dLat| + |dLon|` must be ≤ 4°.
  (b) **Time window**: `time.to - time.from` must NOT exceed **4h**
      (`invalid_request_error`, code `invalid_parameter`:
      "time window (time.to - time.from) must not exceed 4h0m0s. Split larger
      ranges into sequential calls and stitch results client-side; use half-open
      intervals (e.g. one slice's time.to = T, next slice's time.from = T + 1ms)
      to avoid boundary duplicates.").
  A 2026-07-18 session added `time.from`/`time.to` with a 24h window and got 400 —
  the span was fine, the WINDOW was the trigger. (The API even tells you how to
  page: split into sequential ≤4h slices and stitch client-side with a 1ms
  overlap gap.) Size the box to fit AND cap the window at 4h; don't switch
  transport when you see 400.
- `URLSearchParams` does NOT percent-encode the dot, so
  `params.append('filter.latBottom','2.0')` serializes verbatim (same bytes as an
  inline string). Safe to use for the `filter.*` keys.
- **ISO timestamps: leave `%3A` alone.** `URLSearchParams` encodes the `:` in
  `2026-07-17T11:28:19.740Z` as `%3A`. That IS the form the API wants — DO NOT
  `replace(/%3A/g, ':')` back to raw colons. A patch that un-encoded the colon
  was tried; the API's strict URL parser rejects raw `:` in query values (400).
  Also: the 24h-window 400 persisted even WITH `%3A` encoding, proving the colon
  was never the cause — the window was. Trust the live error body (below), not a
  screenshot headline.
- **Read the REAL error body — don't trust the 400 headline or a screenshot.**
  When a proxied fetch 400s, the DevTools "400 Bad Request" status + a
  vision-described screenshot hide the cause. Source the API key from `.env` in
  the shell (`set -a && . ./.env && set +a` — the file-READ tool BLOCKS `.env`,
  use the terminal) and curl the UPSTREAM directly so you can read the JSON error
  body. Proven recipe (key never echoed):
  ```bash
  cd /Users/kamarulhk/my-digital-twin && set -a && . ./.env && set +a && \
  curl -s -o /tmp/va.json -w "HTTP=%{http_code}\n" \
    -H "Authorization: Bearer $VITE_VESSEL_API_KEY" \
    'https://api.vesselapi.com/v1/location/vessels/bounding-box?filter.latBottom=2.0&filter.lonLeft=100.5&filter.latTop=4.0&filter.lonRight=102.5&time.from=...&time.to=...'
  ```
  Then read `/tmp/va.json` — the body told us the 4h window rule verbatim. A
  short Python script (under `/tmp`) can probe several boxes in one run to find
  where the API has traffic (see EMPIRICAL BOX PROBE above). This direct-probe
  pattern beats guessing from a 400 status every time.
- Headers: GET needs ONLY `Authorization: Bearer …`. Do NOT send
  `Content-Type: application/json` on a GET (no body). Adding it on GET is
  harmless but pointless; on POST it's required.
- Response envelope (unchanged across the shape changes):
  `res.data` → `res.vessels` → bare array. Field mapping stays tolerant
  (`latitude`/`lat`, `course`/`cog`, `speed`/`sog`, `vessel_name`/`name`).
- **Use a real Network capture, not guesswork.** The DevTools Network tab
  (Headers: Request URL / Method / Status / Content-Length / X-Ratelimit*)
  is the authoritative ground truth — it ended the 15-commit thrash by showing
  the URL, Bearer, 200, and the 14-byte empty body. But the *status line* alone
  is insufficient for a 400 — pair it with the live upstream error body.
- Debugging discipline: record the EXACT error string each time and change ONE
  shape per iteration so you can tell which fix worked. A wrong hypothesis
  (steps 4, 5) only costs a round-trip if you roll it back the moment the live
  server disproves it.
- **Never let a skill/reference file crown an unverified shape as "ACCEPTED".**
  This file did that for the bbox array and was wrong for a full session. Mark a
  shape confirmed only after a real 200/2xx with expected data, captured from the
  live response — not from a user saying "let's try X".

## KEY TRAP — env var name
It is `VITE_VESSEL_API_KEY` (note the `_` between `VESSEL` and `API`;
`VESSEL` is double-S, single-L). A self-introduced typo to `VITE_VESSELAPI_KEY`
(missing the underscore) made the Bearer empty → silent 401/denial. Match `.env`
exactly; after any rename, grep the driver + the diagnostic log line for the
same name.
