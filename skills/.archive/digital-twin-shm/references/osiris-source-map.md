# OSIRIS source map (for future Box 1 adoptions)

Condensed map of the actual `osiris-master` checkout on disk, captured 2026-08-07.
Read this BEFORE grepping OSIRIS for a new pattern to adopt — it tells you where the
real source lives and which files are the adoption candidates. The *already-adopted*
chunks (viewport dedup, live counts, Context layer, RECON placeholder, `?` shortcuts)
live in `references/osiris-adoption.md` and `references/osiris-layer-adoption-recipe.md`.

## On-disk location
`/Users/kamarulhk/Downloads/osiris-master` (full source, not a zip). 124 `.ts/.tsx`
files. Self-hosted instance runs on `:3001` (per memory); the repo itself defaults to
`:3000` (`next.config.ts` = Next.js `standalone` output).

## Stack
Next.js 16 (App Router, Turbopack) · TypeScript 5 · MapLibre GL JS (WebGL) ·
Framer Motion · Lucide React · separate Express scanner backend in `intel/`.

## Real source layout (NOT a root `app/`)
- `src/app/` — `page.tsx`, `layout.tsx`, `globals.css`, `docs/` (API catalog UI)
- `src/components/` — 24+ panels: `LayerPanel`, `OsirisMap`, `IntelFeed`,
  `LiveAlerts`, `MarketsPanel`, `SatellitePanel`, `ScmPanel`, `OsintPanel`,
  `AiAnalyst`, `KeyboardShortcuts`, `ViewPresets`, `WorldRemote`, `GlobalStatusBar`,
  `ScaleBar`, `DrawingToolbar`, `ArcGISPanel`, `CameraViewer`, `EntityGraphPanel`,
  `SearchBar`, `SharePanel`, `TokenPanel`, `ErrorBoundary`, `AiOverview`
- `src/lib/` — `ai-engine.ts`, `gdeltEvents.ts`, `sanctions.ts`, `countryCentroids.ts`,
  `bulgaria-sources.ts`, `osint-utils.ts`, `stealthFetch.ts`, `ssrf-guard.ts`
- `src/lib/sdk/` — `LatticeAdapter.ts`, `PolybolosClient.ts`, `types.ts` (the
  "OSIRIS SDK" entity layer — interesting but NOT adopted into MARU)
- `intel/` — standalone Express scanner service (RECON backend; OSIRIS-only, not ported)

## How to inspect without the cache flood (GOTCHA)
`search_files` against this repo returns hundreds of hits from `.next/dev/cache/*`,
`.next/dev/trace`, `node_modules/`, and `dist` build artifacts — useless for source
discovery. Use the terminal `find` instead:
```bash
cd ~/Downloads/osiris-master
find src -maxdepth 2 -type d
find src -type f \( -name '*.ts' -o -name '*.tsx' \) | grep -iE 'viewport|layer|recon|map|hud'
```
Never rely on `search_files` for source trees that contain a Next.js/Vite build dir.

## Adoption-candidate files (the patterns behind the already-adopted chunks)
### `src/components/LayerPanel.tsx` — layer grouping + live counts + capability gate
This is the direct ancestor of MARU's per-layer count badge (`mcp-badge-live`).
Shape worth porting conceptually:
```ts
interface LayerDef { key: string; label: string; dataKey: string;
  catKey?: string;          // reads a bucket out of data.category_counts
  requires?: string; }      // capability that must be server-configured for layer to appear
interface LayerGroupDef { label: string; fullLabel: string;
  icon: React.ComponentType<...>; layers: LayerDef[]; }
// LAYER_GROUPS: SDK / AVIATION / MARITIME / SPACE / SURVEIL / HAZARD / THREAT / NETWORK
// activeLayers state + setActiveLayers; capabilities?: Record<string,boolean> hides `requires` layers
```
- Live counts come from `data.category_counts`; the panel reads `catKey` buckets.
- `requires` + `capabilities` is a clean "hide layer until its backend is configured"
  gate — MARU's governance `gov?.ask?.(PROVIDER)` serves the same role.

### `src/components/OsirisMap.tsx` — MapLibre GL mount
Concept-only reference; MARU uses Cesium/Resium, so only the *idea* (viewport-aware
fetch driven by the camera rectangle) ports — already done in `egressDrivers.js`.

### `src/lib/stealthFetch.ts`, `ssrf-guard.ts`
OSINT proxy/security patterns. Not needed for MARU (no outbound RECON probing).

## Already adopted vs excluded (recap — full detail in osiris-adoption.md)
- ADOPTED: viewport-aware fetch + fetched-ref dedup; live per-layer counts;
  Situational/Environmental Context layer (USGS + NASA EONET, keyless; FIRMS excluded
  — needs API key); RECON as UI-only placeholder; `?` keyboard help.
- EXCLUDED: RECON live probing (port-scan/WHOIS/DNS/CVE), crypto/OFAC tracing,
  Patreon/token gating, and any Next.js migration (MARU/R-Tessera stay Vite SPA).

## If a new OSIRIS pattern is to be adopted
Follow `references/osiris-layer-adoption-recipe.md` (9-wire recipe) and the
one-chunk-at-a-time rule. Reconcile the candidate file against the actual checkout
(grep first) before editing — never assume the on-disk file matches an older note.
