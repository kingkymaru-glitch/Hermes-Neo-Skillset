# Map-control cluster + dead-UI purge (R-Tessera / MARU pattern)

User repeatedly asks to REMOVE non-working / placeholder UI rather than hide it.
Removal != deleting one line — hunt the whole trace so nothing dead lingers.

## 1. Removing a config-driven map layer (e.g. weather/flight overlays)
Layers are declared in `src/layers/layerRegistry.js` and rendered by the
Map Control Systems drawer (`MapControlPanel.jsx`, driven by `useLayerManager`).
To remove a layer: delete its object from the registry. That is the ONLY edit
needed — the drawer, toggle state, and LayerManager all iterate the registry, so
removing the declaration removes the button, the toggle, and any live tile.
- Dead rows are easy to spot: `requiresKey: 'openweather'` with no key wired,
  or `{ enabled: false, badge: 'soon' }` placeholder rows. Delete both kinds.
- Do NOT leave a "soon" badge row as a "teaser" — user wants it gone.
- Fix any nearby comment that names the deleted layer (e.g. "ships, flight paths").

## 2. Purging an orphaned asset/marker
A marker may NOT be live even if it "exists":
- Search for where the asset array is defined (e.g. `const DEMO_ASSETS = []`).
  If it is empty, no entity is rendered on the globe — there is nothing to
  un-mount; you only need to remove the cosmetic traces.
- Trace ALL references before declaring done:
  (a) entity/description strings in code (e.g. governanceRegistry.js desc),
  (b) orphaned files in `public/models/` (e.g. `dam-gate-3d.html`) — `rm` them,
  (c) saved node files in the Obsidian vault (`~/Documents/Obsidian/DT Nodes`),
  (d) docs (`*.md`) that name it.
- `grep -rn` the repo (case-insensitive) for the name after editing; expect 0 hits.

## 3. Inlining a floating button next to the layer icon
Original: a standalone `<button className="new-node-btn" + " shifted">` absolutely
positioned at bottom-left, shifting when the left flyout drawer opens.
Desired: a compact pill inline beside the layer (stack) icon, moving WITH it.
Pattern (verified in R-Tessera):
- In `MapControlPanel.jsx`, wrap the layer trigger + the new pill in one flex
  cluster: `<div className={'map-ctl-cluster' + (drawerOpen ? ' shifted' : '')}>`.
  Pass the action via a prop from the owner (e.g. `onAddNode={handleAddNode}`)
  rather than re-declaring the handler inside the panel.
- CSS: `.map-ctl-cluster { position:absolute; left:22px; bottom:22px; display:inline-flex; gap:10px; transition:left .28s ease; }`
  `.map-ctl-cluster.shifted { left:302px; }` (matches the open-drawer offset).
  `.node-pill { ...pill styling... }`.
- Remove the old absolutely-positioned `.new-node-btn` block AND the trigger's
  own `position:fixed` + `.mcp-trigger.shifted` rule — the cluster now owns
  positioning/shifting. Keep `.mcp-trigger` as a plain flex child (no fixed/left/bottom).
- Pitfall: when deleting a CSS rule that has an adjacent `.xxx:hover {` block,
  re-attach the selector line — fuzzy patch can swallow it and leave orphaned
  declarations. Re-read the region after editing CSS.

## Verification
- `npm run lint` (0 errors; pre-existing warnings OK) + `npm run build` must pass.
- `ls public/models/` confirms the orphan file is actually gone (Vite SPA fallback
  returns 200 for a deleted path — the curl check is NOT proof; trust the ls).
- HMR on the dev server reflects changes without restart.
