# R-Tessera Supabase Entity Layer (ROVER-KIT CCTV pattern)

Use this when adding a REAL-DATA (Supabase-backed) entity layer to R-Tessera that is
NOT a keyless public feed — e.g. ROVER-KIT CCTV cameras, TNB grid nodes, any
operator-maintained asset that lives in a `cctv_cameras`-style table. Contrast with
the keyless feeds (USGS/EONET) covered elsewhere: those are public GETs; these are
authenticated/anon-read rows the operator edits through LunaV Solutions.

## HARD RULE — never seed demo/fake data
User decreed (ROVER-KIT build, 2026-08-25): **never push demo/fake camera rows or
test events into R-Tessera or Supabase to "see it work".** The globe shows ONLY real
rows. To test the live feed, route the REAL Mac webcam through Luna EDGE:
- `cd ~/luna-edge && source .venv/bin/activate && python app.py`
- open `http://localhost:8000`, pick the Mac webcam source, click Start
- it streams **raw binary JPEG** frames over `ws://<mac-lan-ip>:8000/ws`
- register ONE real `cctv_cameras` row in LunaV Solutions → Vision with Live Feed URL
  = `ws://<mac-lan-ip>:8000/ws`, then open it on the globe.

## Layer pattern (mirrors ProjectNodes — reuse, don't reinvent)
1. **Hook** `src/services/use<Cctv>Cameras.js`:
   - `fetch<Cctv>Cameras()` + `use<Cctv>Cameras()` doing an **ANON** `select` from
     `<table>` via the existing `createSupabase()` anon client
     (`src/lib/supabaseClient.js`). No service-role key on the client.
2. **Layer** `src/components/<Cctv>CameraLayer.jsx`:
   - Props: `show` (bool gate from the MapControlPanel toggle), `viewerRef`
     (Cesium `Viewer`). When `show` is false, render nothing.
   - On `viewer` ready (`viewerRef.current`): imperative
     `viewer.entities.add({ position: Cartesian3.fromDegrees(lon,lat,0),
     point:{...}, label:{ text: name, ... } })` per row — mirror the ProjectNodes
     render shape (red point + label).
   - **Node click**: `new ScreenSpaceEventHandler(viewer.scene.canvas)` +
     `ScreenSpaceEventHandler.LEFT_CLICK`; in the handler
     `viewer.scene.pick(event.position)`; if the picked entity belongs to this
     layer, `viewer.flyTo(entity)` then open a floating feed window.
   - **Floating feed window**: a React component (draggable by a red title bar,
     closable ×) painting ws frames to a `<canvas>`:
     `const ws = new WebSocket(streamUrl); ws.onmessage = e => { const blob =
     e.data; createImageBitmap(blob).then(b => ctx.drawImage(b,0,0)); }`.
     Glass styles in `App.css` under `.rt-feed-*`.
3. **Wire** into the provider stack (same shape as ProjectNodes toggle):
   - `App.jsx`: `const [show<Cctv>, setShow<Cctv>] = useState(false)` + pass to GlobeView.
   - `GlobeView.jsx`: `<CctvCameraLayer show={show<Cctv>} viewerRef={viewerRef} />`
     (import + mount inside the viewer-ready branch).
   - `MapControlPanel.jsx`: import `use<Cctv>Cameras`, add a toggle row with a live
     `data?.length ?? 0` count badge.

## Paired admin form (LunaV Solutions — R-Tessera stays VIEW-ONLY)
User rule: camera edits live in **LunaV Solutions** (`~/lunavsolution-code`) →
Project → Vision tab, NOT inside R-Tessera. R-Tessera only reads + displays.
- Add new fields by extending the `upsert_<table>` RPC with **optional trailing
  params** (`p_stream_url text default null`). DO NOT reorder required params.
- Migrate via `supabase/migrations/YYYYMMDD_<name>.sql` — this is run by the user in
  the Supabase SQL Editor; it is **NOT auto-applied** by `vercel deploy`.
- RPC param convention (matches existing `upsert_cctv_camera`): required params
  first, defaults last; the component calls with named args so a new optional param
  is safe to omit.

## Build / verify gate
- R-Tessera: `npm run lint` (oxlint) + `npm run build` (vite) must pass.
- LunaV Solutions: `npx tsc --noEmit` clean.
- Commit each repo separately; `git rebase origin/main` then `git push` both.

## Demo run (end-to-end)
1. LunaV Solutions → Vision → add camera, set Live Feed URL =
   `ws://<MAC-LAN-IP>:8000/ws`, Save.
2. Start Luna EDGE (`~/luna-edge`, Flask YOLOv8n COCO) → webcam → Start.
3. R-Tessera → toggle ROVER-KIT · CCTV Cameras ON → red node appears at its lat/lon.
4. Click node → camera flies in + floating live webcam window opens.

## Gotchas captured from the build
- `ScreenSpaceEventHandler` must be imported from `resium` (not `cesium`) in this
  repo's React setup, and constructed with `new ScreenSpaceEventHandler(
  viewer.scene.canvas)` — not a Resium `<ScreenSpaceEventHandler>` child.
- Patch whitespace mismatches: when editing App.jsx/GlobeView, re-read the exact
  section before patching — a stray `/>` that closes `<GlobeView ...>` early will
  silently drop following props.
- MapControlPanel count badge: use `data?.length ?? 0`, not `events.length`.
