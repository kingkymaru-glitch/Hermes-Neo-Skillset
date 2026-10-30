# OSIRIS-adopted: Viewport-Aware + Fetched-Ref Dedup Fetch (MARU)

Adopted 2026-07-19 from the `simplifaisoul/osiris` layer pattern into MARU's
live maritime egress (`src/services/egressDrivers.js` + `src/components/MaritimeEntities.jsx`).
Two cheap discipline rules that cut API egress for a zoomed-in field engineer and
prevent a stale/blank-canvas bug. This is the canonical shape — copy-with-modifications
for ANY tiled live-entity layer.

## The two rules

### 1 · Viewport-aware tile filtering
Only fetch tiles whose bounding box intersects the camera's visible rectangle.
The camera rect comes from `viewer.camera.computeViewRectangle()`
(north/south/east/west in radians). If `null`/unavailable → fall back to ALL tiles
(safe default; never silently drop the fleet).

```js
const TILE_FETCHED_AT = new Map() // "latB,latT,lonL,lonR" -> last success ts

function visibleTiles(viewRect) {
  if (!viewRect) return VESSELAPI_TILES
  return VESSELAPI_TILES.filter(([latB, latT, lonL, lonR]) => {
    const latOk = latB <= viewRect.north && latT >= viewRect.south
    const lonOk = lonL <= viewRect.east && lonR >= viewRect.west
    return latOk && lonOk
  })
}
```

### 2 · Fetched-ref dedup guard
A `Map` records the last successful pull per tile key. Skip any tile fetched
within `TILE_DEDUP_MS` (set to HALF the poll interval). Marks the skipped tile
as `anyOk = true` so it is NOT counted as a connection failure.

```js
const TILE_DEDUP_MS = 15 * 60 * 1000 // half of POLL_MS (30m)
// inside the tile loop:
const tileKey = tile.join(',')
if (Date.now() - (TILE_FETCHED_AT.get(tileKey) ?? 0) < TILE_DEDUP_MS) {
  anyOk = true // previously-fetched data still on screen — not a failure
  continue
}
// ... fetch ...
gov?.record?.(VESSELAPI_PROVIDER)
TILE_FETCHED_AT.set(tileKey, Date.now()) // mark fresh for the guard
```

### Wiring the camera rect in (MaritimeEntities.jsx)
```js
const getViewRect = () => {
  try {
    const rect = viewer?.camera?.computeViewRectangle()
    if (!rect) return null
    return { north: rect.north, south: rect.south, east: rect.east, west: rect.west }
  } catch { return null }
}
const { vessels: next, error } = await fetchLiveVessels(gov, { viewRect: getViewRect() })
```
Signature is now `fetchLiveVessels(gov, opts = {})` — backward compatible (no
`viewRect` ⇒ all-tile fallback).

## CRITICAL PITFALL — open-ocean false offline (caught & fixed this session)
If the camera points at open ocean, NO tile intersects → `visibleTiles` returns
`[]`. With the old loop, the fetch body never ran, `anyOk` stayed false, and the
driver WRONGLY returned `{ vessels: [], error: { code: 'VESSELTELEMETRY_OFFLINE' } }`
— a phantom outage. FIX: guard before the loop:

```js
const tiles = visibleTiles(viewRect)
if (tiles.length === 0) return { vessels: [], error: null } // "no data in view", NOT outage
```
Keep the last-known fleet; never blank the canvas or raise a red banner when the
user is simply looking at water.

## Honesty note — when the guard actually saves calls
At the CURRENT 30-min blind poll, the guard is DORMANT (poll gap 30m > 15m guard),
so it adds ZERO savings there. Its real value:
- De-dupes RAPID re-triggers (toggle layer off/on/off/on, jittery pan).
- UNLOCKS shorter / camera-driven refresh without burning the rate budget.
  e.g. pan 4 min @1 trigger/sec on one tile: no guard = 240 API hits; with guard = 1.
Don't oversell the guard on a long blind-poll — the VIEWPORT filter is the win at
blind cadence (zoomed onto 1 of 4 tiles → 75% fewer calls over 4h).

## Performance numbers (4h = 8 blind polls, simulated)
| View                      | OLD (all 4) | NEW (viewport) | Saved |
|---------------------------|-------------|----------------|-------|
| Zoomed 1 structure (tile A) | 32        | 8              | 75%   |
| Partial (tiles A+B)        | 32        | 32             | 0%    |
| Full national (all 4)      | 32        | 32             | 0%    |
Viewport savings scale with how tight the camera is. Guard savings appear only
with shorter/camera-driven cadence.

## Verification (this session, green)
- `npm run lint` → 0 errors (1 pre-existing unrelated warning: poll-effect
  dependency-array notice).
- `npm run build` → 77 modules transformed, built OK.
- Runtime (live VesselAPI) still needs the user's Cmd+B + browser run.
- Simulate the dedup/viewport math in Python before claiming a % — it exposed
  both the dormant-guard nuance and the open-ocean regression above.
