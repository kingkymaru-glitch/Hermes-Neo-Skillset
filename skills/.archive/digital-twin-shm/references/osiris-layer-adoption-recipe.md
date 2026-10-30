# OSIRIS → MARU: adding a governed keyless entity layer (recipe)

Pattern borrowed from the OSIRIS OSINT dashboard (simplifaisoul/osiris) and
adapted into MARU Box 1. Use whenever you add a new ambient overlay layer that
renders entities on the Cesium globe from a public feed.

## Adoption boundary
- KEEP: viewport-aware + dedup fetch, live per-layer counts, Situational/
  Environmental Context layer, RECON as UI-only placeholder, `?` keyboard help.
- DROP: OSIRIS OSINT internals (port-scan/WHOIS/DNS/CVE, crypto/OFAC, token,
  Next.js). RECON in MARU = scouting LINKS only, no live probing.

## Step-by-step (9 wires)
1. egress driver (src/services/egressDrivers.js): `fetchX(gov)`. KEYLESS CORS
   feeds only. Gate with `gov?.ask?.(PROVIDER)`; `Promise.allSettled` the feeds,
   normalize, `gov?.record?.(PROVIDER)` per success; return `{data,error}`.
   NEVER fabricate on failure — return `{data:[], error:{...}}`, UI reports it.
2. governance (src/governance/governanceRegistry.js): add `PROVIDER` entry.
3. layer registry (src/layers/layerRegistry.js): entity entry `kind:'entity'`.
4. LayerManager guard (src/layers/LayerManager.js): `activate()` returns early
   on `kind:'entity'` (no imagery provider).
5. context flag (src/context/EdgeDataContext.jsx): `showX`/`setX` + `xCount`.
6. component (src/components/XEntities.jsx): gate on `showX` (null when off).
   Poll slow; imperative entity sync (see cesium-resium-react
   references/cesium-entity-by-id-pitfall.md); click HUD via ScreenSpaceHandler;
   on error clear + offline banner.
7. Map Control row (src/MapControlPanel.jsx): `isEntityLayer` toggle + count.
8. styles (src/App.css): glass HUD + `.x-badge-live`, mirror vessel HUD.
9. mount (src/App.jsx): import + render inside `<Viewer>` by MaritimeEntities.

## Keyless feeds that worked
- USGS: earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_week.geojson
- NASA EONET v3: eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=100
- FIRMS EXCLUDED (needs API key).

## Keyboard shortcuts (`?` overlay, OSIRIS-derived)
- `?`/Shift+/ toggles help modal (global window keydown).
- L locate, S sensors, M map-control, C chat, G settings→Governance,
  I insights, O settings root. Ignore INPUT/TEXTAREA/contentEditable targets.
- Deep-link Settings detail via `defaultView` prop on SettingsPanel.
