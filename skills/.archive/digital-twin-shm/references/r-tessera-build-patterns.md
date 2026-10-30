# R-Tessera Build Patterns (CURRENT — lean rebuild, 2026-08-07)

> ⚠️ The June/July-era content (5-Box, SUDA GH Action cron, `asap/suda-simulator.mjs`,
> `public/suda-feed.json`, `InsightsPanel`, `IngestionPanel`, `SETTING_ITEMS`, monolithic
> box-header `App.css`) describes the OLD architecture and is NO LONGER TRUE. The user
> wiped all of it and orphaned GitHub `main` for a clean slate. Do not re-add those
> boxes unless explicitly asked. The SKILL.md R-Tessera section is the authoritative
> short summary; this file is the detailed current state + fresh-start recipe.

## Repo identity (unchanged)
- Local: `~/Documents/R-Tessera`
- GitHub: `kingkymaru-glitch/R-Tessera` (main; history orphaned 2026-08-07)
- Live: `https://r-tessera.vercel.app`
- Dev: `http://localhost:5174` (`npm run dev`)
- Vercel project: `r-tessera`

## Current architecture (Box 1 + Box 2 only)
- **Box 1 — Base Layers.** Cesium/Resium. Bottom-left 4-mode selector:
  - raster half: `map` (OpenStreetMap raster) | `satellite` (Esri World Imagery)
  - scene half: `3d` (SCENE3D globe) | `2d` (SCENE2D / Columbus View)
  - Active base = raster + scene. Swapped at runtime via a `useCesium` child
    bridge that (a) removes existing imagery layers + adds the chosen
    `ImageryLayer`, (b) calls `viewer.scene.morphTo2D/3D(0)`.
  - Source: `src/baseLayers.js` + `src/components/BaseLayerSelector.jsx`.
  - No Ion token: `Ion.defaultAccessToken = 'local-dev-no-ion'`; token-free
    raster basemaps only (no black globe).
- **Box 2 — API Layers.** Top-right `MapControlPanel` (was `mcp-drawer`).
  - `Situational · Earthquakes` → USGS 2.5_week GeoJSON (keyless).
  - `Volcano Watch` → NASA EONET open volcanoes (keyless).
  - `Maritime · Live Vessels` → KEY-GATED. Disabled-with-tooltip until
    `VITE_MARITIME_PROVIDER` (`aisstream`|`vesselapi`) + matching key set in
    `.env.local`. Real aisstream.io WebSocket (or VesselAPI poll) wiring present;
    NEVER a mock fleet.
  - Each toggle shows a live count badge; clicking a pin opens a glass HUD.
  - Source: `src/services/egressDrivers.js`, `src/services/useFeeds.js`,
    `src/components/SituationalEntities.jsx`, `src/components/MaritimeEntities.jsx`.

## Hard product rules (user-decreed 2026-08-07)
- **NO logos.** Brand header / wordmark / hero art removed. Functional glass panels only.
- **NO mock data, NO handlers for unavailable data.** Feeds return
  `{events:[], error}` on failure; gated features stay disabled (tooltip), never
  throw, never fabricate positions. Maritime is the canonical example (dark until keys).

## Tooling / build
- Stack: React 19 + Vite 8 + Cesium 1.143 + Resium 1.24 + @tanstack/react-query.
- `src/App.css` is a single lean stylesheet (glassmorphism; base-selector
  bottom-left, mcp-drawer top-right). NOT the old box-header monolith.
- `vercel.json` = Vite SPA shape: `buildCommand: npm run build`,
  `outputDirectory: dist`, `framework: vite`, SPA rewrite to `/index.html`.
  (The OLD `@vercel/static-build` + committed-`dist` vercel.json is GONE — it
  would break a clean Vite deploy.)
- `.gitignore` excludes `dist/`, `node_modules`, `.env.local`, `.vercel`.
- Gate: `npm run lint` (oxlint 0/0) + `npm run build` (vite), then `rm -rf dist`.

## Fresh-start deploy recipe (2026-08-07, verified)
Use when the user says "rebuild from scratch" / "fresh start" / "scrap all code":
1. Reconcile against ACTUAL repo first (`find src -type f`); the old 5-Box
   artifacts are NOT on disk anymore — do not edit them.
2. Prune stale dirs/files from disk: `server/`, `asap/`, `supabase/`, `docs/`,
   old `README.md`/`ARCHITECTURE.md`/`R-TESSERA_FUNCTION_MAP.md`, `start.bat`/
   `start.command`, the `.github` workflow, stale `public` logos/glb/suda-feed,
   and any `.hermes/plans` not part of the new app.
3. Fix `vercel.json` to the Vite SPA shape; simplify `.gitignore` (dist ignored).
4. `git checkout --orphan fresh-start` → `git rm -rf --cached .` → `git add .`
   (respects .gitignore). On an orphan with no commit yet you CANNOT
   `git reset HEAD <path>` — to drop stray staged files use `git rm --cached
   --quiet <path>` instead.
5. Commit → `git branch -M main` → `git push --force origin main`.
   (Force-push rewrites remote history — correct for a deliberate fresh start;
   confirm scope with the user first.)
6. Vercel auto-builds on push. Verify: `curl -sI https://r-tessera.vercel.app`
   (expect 200) AND grep the live HTML for the fresh bundle hash
   (`assets/index-<hash>.js`) to confirm the new build, not a stale one, is live.


