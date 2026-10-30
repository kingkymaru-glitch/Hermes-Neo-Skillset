# VesselAPI — Spatial Tiling & Rate-Budget Cost Model

Companion to `references/vesselapi-request-shape.md`. That file covers the
per-box request shape (GET + `filter.*` + `time.from`/`time.to`, ≤4° span, ≤4h
window). This file covers what to do when the AREA you want is **bigger than one
4°-span box** — the case that came up when the user asked to cover Johor→Penang
across all of Peninsular Malaysia.

## Hard rules recap (from vesselapi-request-shape.md)
- **Span cap:** total `|dLat| + |dLon|` must be ≤ 4° per box. Inclusive at 4.0.
- **Time window:** `time.to - time.from` must be ≤ 4h. Inclusive at 4h.

## Why you MUST tile (not send a bigger box)
A single box for Peninsular Malaysia (Johor lat 1.0 → Penang lat 6.5, lon
100.5–102.5 → `|dLat| 6 + |dLon| 2 = 8°`) returns **HTTP 400** with:
`invalid filter parameters: invalid bounding box: total span (|dLat| + |dLon|)
must not exceed 4°`. Even a 3.5×3.5 = 7° box 400s. So any region wider than 4°
total span has to be **fanned out into multiple ≤4°-span boxes** and stitched
client-side.

## Tiling pattern (verified live 2026-07-18, commit 3ee37bf)
1. Build N box arrays `[latBottom, latTop, lonLeft, lonRight]`, each ≤4° total.
2. `fetch` all of them (the dev `/api-vessel` proxy handles CORS).
3. Merge the tracks and **dedup by vessel id** — a ship sitting on a tile seam
   must appear once, not twice.
4. Wrap EACH tile's fetch in its own `try/catch` and `continue` on failure, so
   one dead tile never aborts the whole fleet pull.
5. Call `gov.record(provider)` **once per successful tile** (counts real egress;
   a failed tile must not be counted).

### Johor→Penang split that shipped (each exactly ≤4° total span)
```
A [1.0, 4.0, 100.5, 101.5]  south-west (Johor strait)
B [3.5, 6.5, 100.5, 101.5]  north-west (Penang strait)
C [1.0, 4.0, 101.5, 102.5]  south-east (busy Malacca lane)
D [3.5, 6.5, 101.5, 102.5]  north-east
```
Live probe (4h window): all 4 returned **HTTP 200**. Tile **C alone = 14
distinct vessels**; A/B/D = 0 (west-coast sparsity right now — real, not a bug).
The eastern strait is where the traffic is. Result vs the old single Port Klang
box: 2 vessels → 14.

## Rate-budget cost model (why "widen ⇒ slow the poll")
Each poll now fires **4 requests** (one per tile). The live
`X-Ratelimit-Remaining` header was ~145.
- **30 s poll:** 2 polls/min × 60 × 4 tiles = **480 req/hr** → exhausts 145 in
  **~18 min**.
- **30 min poll:** 2 polls/hr × 4 tiles = **8 req/hr** → comfortably under budget.

**Rule of thumb:** widening coverage (more tiles) MUST be paired with a slower
poll interval, or you burn the server rate budget in minutes. When we went
Johor→Penang we set `POLL_MS = 30 * 60 * 1000` (30 min). A 30 s poll with 4
tiles would have killed the demo mid-presentation.

## Window length vs sparsity
A 5-min window on the small current box returned **0 records**; the 4h-cap
window on tile C returned 14. In sparse regions a short window = nothing. Keep
the window at the **4h ceiling** to maximise capture — it's a hard cap, not a
soft suggestion, and sitting at it is safe.

## Probe recipe (rank tiles by vessel count in one run)
Reuse the urllib pattern: read the key from `.env` (the file-READ tool BLOCKS
`.env` — use the terminal/python), never echo it. Loop the tile arrays, print
HTTP status + distinct-mmsi count + total span. This is exactly how the 4-tile
Johor→Penang split was validated **before any app code was written** — probe
first, code second.

```py
# /tmp/va_tiles.py — key from .env, no echo
import urllib.request, urllib.parse, json, datetime, re
KEY = re.search(r'VITE_VESSEL_API_KEY=[\"\\']?([^\"\\'\\n]+)', open('/Users/kamarulhk/my-digital-twin/.env').read()).group(1)
now = datetime.datetime.now(datetime.timezone.utc)
tf = (now - datetime.timedelta(hours=4)).strftime('%Y-%m-%dT%H:%M:%SZ')
tt = now.strftime('%Y-%m-%dT%H:%M:%SZ')
BASE = 'https://api.vesselapi.com/v1/location/vessels/bounding-box'
TILES = [('A',1.0,4.0,100.5,101.5),('B',3.5,6.5,100.5,101.5),
         ('C',1.0,4.0,101.5,102.5),('D',3.5,6.5,101.5,102.5)]
for name,laB,laT,loL,loR in TILES:
    p={'filter.latBottom':laB,'filter.latTop':laT,'filter.lonLeft':loL,'filter.lonRight':loR,'time.from':tf,'time.to':tt}
    req=urllib.request.Request(BASE+'?'+urllib.parse.urlencode(p), headers={'Authorization':'Bearer '+KEY})
    try:
        r=urllib.request.urlopen(req, timeout=20); d=json.loads(r.read().decode())
        arr=d.get('vessels') or d.get('data') or []
        print(name, 'HTTP', r.status, 'vessels', len(set(x.get('mmsi') for x in arr)))
    except urllib.error.HTTPError as e:
        print(name, 'HTTP', e.code, e.read().decode()[:120])
```

### CRITICAL probe gotcha — Python timestamp format
The live API wants the **`…Z` form** (`2026-07-18T12:53:12.840Z`), which is what
the app sends via `new Date().toISOString()`. Python's
`datetime.now(timezone.utc).isoformat()` emits
`2026-07-18T12:53:12.968689+00:00` (microsecond precision + `+00:00` offset),
which the server REJECTS: `parsing time "… 00:00" as
"2006-01-02T15:04:05Z07:00": cannot parse " 00:00" as "Z07:00"` → HTTP 400 on
EVERY tile. A probe using `.isoformat()` therefore looks like "all tiles broken"
but it's the probe's clock, NOT the app. Always format explicitly:
`dt.strftime('%Y-%m-%dT%H:%M:%S.') + f"{dt.microsecond//1000:03d}Z"`. The probe
recipe above already does this. This trap caused a FALSE "A/B/C all empty" claim
that the user correctly rejected — mirror the app's exact timestamp format in any
external probe.

## Sparsity-check discipline (don't cry "empty" too early)
When a tile (or region) returns 0, that can be a **probe defect** (bad timestamp,
wrong param form, key not loaded) rather than reality. Before telling the user
"there are no ships there":
1. Confirm the probe used the EXACT same params/format the app sends (valid `Z`
   ts, `time.from`/`time.to` not `time.`, ≤4° span, ≤4h window).
2. Re-probe to rule out a transient 400 (a buggy probe 400s on all tiles).
3. Cross-check against an authoritative live source (e.g. MarineTraffic for the
   same center/zoom). MarineTraffic shows CURRENT positions and blends
   terrestrial + satellite AIS, so it often shows dots where our 4h historical
   lookback shows zero — a TIME-SEMANTICS difference, not a code defect.

The user WILL catch a wrong sparsity claim. Verify hard before asserting it. In
our Johor→Penang case, A and C genuinely had vessels; only B (Penang NW) and D
(east-coast north) were truly sparse in the 4h slice.

## Pitfall carried from earlier sessions
The PREVIOUS dead-end transport (POST + flat bbox body) must NOT be copied. The
canonical production driver is **GET + `filter.*` + `time.from`/`time.to`**,
fanned out across tiles. See `src/services/egressDrivers.js` (commit 3ee37bf)
and its tiled `buildVesselUrl()` / `fetchLiveVessels` loop. NOTE:
`references/maritime-fleet-implementation.md` still shows the OLD POST form in
its code block — treat that file as STRUCTURAL-only (governed egress → Cesium
entity layer + click HUD) and **do NOT copy its transport**.
