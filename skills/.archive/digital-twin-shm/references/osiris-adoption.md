# OSIRIS → MARU Adoption Notes

OSIRIS = `simplifaisoul/osiris` (Next.js 16 + MapLibre GL, global OSINT dashboard,
~6.8k stars). MARU = `my-digital-twin` (Vite+React SPA, CesiumJS/Resium, structure-scale
SHM twin). We borrow OSIRIS *patterns*, never its stack. Adopt chunks ONE AT A TIME:
land the code, show the perf benefit with real numbers, pause for visual review, then
take the next. Do NOT batch multiple OSIRIS adoptions in one turn.

## Adopted this session (chunk 1 + chunk 2)

### Chunk 1 — viewport-aware fetch + fetched-ref dedup (egressDrivers.js)
- `fetchLiveVessels(gov, opts = {})`; `opts.viewRect` = `{ north, south, east, west }`
  from `viewer.camera.computeViewRectangle()`. Caller passes `null` when unavailable.
- `visibleTiles(viewRect)`: returns `VESSELAPI_TILES` when no rect (backward-compat
  fallback), else `VESSELAPI_TILES.filter(box intersects rect)`.
- `TILE_FETCHED_AT` Map: per-tile `Date.now()`; skip any tile fetched within
  `TILE_DEDUP_MS` (15 min). This is the literal OSIRIS "don't re-fetch what's on
  screen" discipline.
- **Pitfall #1 (false outage):** empty `visibleTiles` (camera over open ocean) made
  the old `anyOk === false` path flag "VESSEL TELEMETRY OFFLINE". Fix: early-return
  `{ vessels: [], error: null }` and keep the last-known fleet. Treat "no data in
  view" as NOT-an-outage.
- Per-layer dedup key is the `provider_id || '__na__'` + `tileKey` (mirrors OSIRIS),
  so each governance provider has its own guard.

### Chunk 2 — live per-layer entity count (MapControlPanel + EdgeDataContext)
- `EdgeDataContext` already bridges the maritime overlay via `showMaritimeLayer`.
  Added `vesselCount` state (default 0), exposed on the context value.
- `MaritimeEntities` calls `setVesselCount(next.length)` on every successful poll and
  `setVesselCount(0)` in the cleanup branch when the layer toggles off.
- `MapControlPanel` renders a live badge on the maritime entity row while active:
  `isEntityLayer(l) && active ? <span className="mcp-badge mcp-badge-live">{n} vessels</span> : ...`.
  CSS `.mcp-badge-live` = cyan tabular-nums (see App.css). Falls back to the stock
  switch when off. No new store/context needed — reuse the bridge.

## HONESTY RULE (do not overclaim)
At MARU's current 30-min blind poll, the fetched-ref guard is **dormant** — poll gap
(30m) > guard window (15m) -> it saves 0 calls there. Real value is:
(a) de-dupes rapid re-triggers (toggle off/on/off/on, jittery pan), and
(b) UNLOCKS shorter/camera-driven refresh without burning the rate budget.
- Model the actual poll cadence before quoting "% fewer". Correct arithmetic:
  zoom onto 1 of 4 tiles -> viewport alone cuts 32->8 calls over 4h (75% fewer);
  partial/full view -> 0% fewer at blind poll (all tiles on screen anyway).
- Camera-driven example: pan 4 min @1 trigger/s on 1 tile -> without guard 240
  calls, with guard 1 call (100% fewer). That's the guard's real payoff.

## Verification
- `npm run lint` (oxlint) + `npm run build` (vite) after EVERY edit batch.
  The 1 pre-existing warning (poll-effect dep-array) is NOT from OSIRIS edits.
- `rm -rf dist` after each verify (standing rule).
- Runtime (badge ticking, fleet on globe) needs the user's Cmd+B + browser run —
  state "build green, visual unverified", never claim the UI is confirmed.

## NOT adopted from OSIRIS (explicit exclusions)
RECON probing (port scan/WHOIS/DNS/CVE), crypto tracing / OFAC sanctions, Patreon/
token gating, Next.js migration. MARU stays Vite+React SPA, no monorepo.

## Planned next (deferred per user)
- Context layer (USGS seismic + NASA EONET weather + NASA FIRMS fires) as a keyless
  `LAYER_REGISTRY` `url-template` entry; small icon markers (NOT polygons).
- (optional) keyboard shortcuts; (optional) Box-2 RECON-panel *pattern* only.
