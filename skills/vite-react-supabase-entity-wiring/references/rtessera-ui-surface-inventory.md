# R-Tessera UI Surface Inventory (as of 2026-07-31)

Live at https://r-tessera.vercel.app; local `npm run dev` serves on :5174.
Run the dev server and snapshot a flyout before claiming any UI defect exists.

## Flyouts / panels
- **Node List** (menu 📡): `NodeListFlyout`. Lists node groups from
  `useEdgeData()`; rows are currently NOT clickable → map (this is the
  requested "click item → fly camera to node" feature; reuse the single
  `viewerRef.camera.flyTo`). "＋ New Node Group" opens `NewNodeGroupModal`.
- **Map Control Systems** (button "Open Map Control Systems"): base layers
  (OSM / Satellite), data overlays (Situational Context, Structural Models),
  "Map Nodes" switch. Badge shows sensor count + context-feed count.
- **Situational Context** (overlay button → `SituationalEntities`): renders
  external recon cards. These are the ONLY `<a>` anchor links in the app
  besides the GLB CTA and footer GitHub link.
- **GLB Studio** (menu 🧊 → `GlbStudioPanel`): "🚀 Launch LuNav Solution
  Portal" → https://lunavsolution.vercel.app (resolves fine).
- **Sensors**: NO dedicated Sensors flyout button exists. Sensor data shows in
  the IoT Windshield HUD (simulated) and the Map Control badge. The
  cluster → group → sensor drill-down uses `<button>`s, NOT anchors — so there
  are no per-sensor external links that could be "broken".

## Links actually present (all resolve)
- Recon cards: https://earthquake.usgs.gov, https://www.windy.com,
  https://eonet.gsfc.nasa.gov
- GLB CTA: https://lunavsolution.vercel.app
- Footer: github.com/kingkymaru-glitch

## Known live console error (NOT a link bug)
`Could not find the table 'public.assets' in the schema cache` — the Digital
Twin asset loader hits a table absent from the live DB. Fix = apply an `assets`
migration MANUALLY (Vercel does not run migrations). Separate concern from the
`nodes.portal_url` column work.

## Camera fly-to
Single `viewerRef` in App.jsx tree. `viewer.camera.flyTo({ destination,
orientation, duration })` is already used by the `?model_id=` deep-link and
"Locate Me". Reuse it for Node List item click → node; never instantiate a
second Cesium viewer.
