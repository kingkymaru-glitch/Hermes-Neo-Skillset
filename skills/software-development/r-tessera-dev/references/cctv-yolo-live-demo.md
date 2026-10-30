# R-Tessera CCTV + YOLO live-demo pipeline (ROVER-KIT)

## The pipeline (verified live 2026-08-25)
```
webcam → Luna EDGE (ws://localhost:8000) → cloudflared wss tunnel → R-Tessera (https live)
```
- Luna EDGE (`~/luna-edge/app.py`) is the LOCAL YOLO server. It streams annotated
  frames over `ws://localhost:8000/ws`. `/api/start` turns YOLO on, `/api/stop` off;
  the ws already carries boxes when the engine is on.
- R-Tessera renders a floating feed window (portal'd to `document.body`, z-index high)
  when a CCTV node is clicked. The window shows the remote `stream_url` as a live feed.
- The live https R-Tessera page CANNOT open `ws://localhost` (mixed-content). Fix:
  cloudflared quick tunnel → `wss://<random>.trycloudflare.com/ws` (see
  `cloudflared-tunnel-demo` skill). The CCTV row `stream_url` is set to that wss URL.

## CCTV layer facts (STANDING in this repo)
- Table `public.cctv_cameras` (Supabase, shared `okzmblyboudjffaixa`). Columns include
  `id` (uuid), `name`, `stream_url` (text, the ws/wss endpoint), `project_id`, geo fields.
- `src/components/CctvCameraLayer.jsx` is the live layer: renders Cesium `Entity` points
  for each camera row, a `ScreenSpaceEventHandler` (use `ScreenSpaceEventType.LEFT_CLICK`,
  NOT `ScreenSpaceEventHandler.LEFT_CLICK` — the latter is undefined and was the
  `Can't find variable: showCctv` / click-dead bug) that opens the feed window, and the
  `FeedWindow` component.
- `FeedWindow` MUST be wrapped in `createPortal(..., document.body)` so it escapes the
  Cesium canvas stacking context and actually shows above the globe (z-index fix).
- The window header has a YOLO **Detect toggle** (shipped commit `49ce7e6`): a button
  that POSTs `<origin>/api/start` (Detect ON) and `/api/stop` (OFF), where `origin` is
  derived from the wss stream_url (`wss:`→`https:`, strip `/ws`). Status pill shows
  `○ Detect` / `◉ DETECT`.

## Quirks that cost rounds (do not re-introduce)
- `ScreenSpaceEventType` must be IMPORTED from `cesium` into the component — it is NOT a
  property on the `ScreenSpaceEventHandler` instance. Missing import → `Can't find
  variable: ScreenSpaceEventType` at click time.
- `NearFarScalar` must also be imported from `cesium` (used for node scaling). Missing
  import → render crash.
- `ProjectNodes.jsx`: do not call `handle.remove()` where `handle` is undefined — guard
  with `if (handle) handle.remove()` in cleanup, else unmount crash on globe teardown.
- Click handler reads the picked entity's `cctvId` property (set on the Entity) to look
  up the camera row — ensure the Entity carries `cctvId`, not just `id`.

## Deploy gate
- R-Tessera auto-deploys to Vercel on push to `main` ONLY if commit author is
  `maru <kingkymaru@gmail.com>`. Commit with
  `git -c user.name=maru -c user.email=kingkymaru@gmail.com`.
- `npm run build` is the pre-push verify gate (Vite client build). Must be green.
- Run the CCTV layer from the DEV server `http://localhost:5174` for live testing before
  pushing; verify the served file actually contains your patch via `curl localhost:5174/... | grep <marker>`
  (dev server HMR can lag — curl proves what's served).

## Supabase row updater (agent has no DB creds — user pastes in SQL Editor)
```sql
update public.cctv_cameras set stream_url='wss://<tunnel>.trycloudflare.com/ws'
where name='Test CAM 02';
```
Keep a local copy at `~/Desktop/update_cctv_stream_url.sql`, refresh the wss URL after
every tunnel relaunch, re-run after reboot.
