# ARRAS Spatial Control Surface Pattern

Use this when implementing the ARRAS reservoir control center inside LunaV.

## UX rules
- Centerpiece = full-screen 3D model, not a side panel.
- Device placement = click-to-place on the 3D model, reuse existing node-placement logic.
- Camera = first-class spatial object with view-direction indicator on the model.
- Clicking a placed device opens a floating, draggable, resizable flyout panel.
- Flyout closes to a remembered/default position; re-open by clicking the device node again.
- Layer toggle = small icon button top-right, below the header. Toggles visibility of device icons, inspection markers, YOLO overlay, alert/heatmap, survey grid.
- Command channel = pull-based via Supabase `commands` table, edge polls every 30s. No WebSocket/MQTT required for POC.

## Camera flyout tabs
1. Camera Settings
2. PTZ / Light / Dimmer controls
3. YOLO config
4. Viewer (latest annotated frame + playback)

## Non-camera device flyout tabs
1. Placement / Control
2. Data Log
3. Charts

## YOLO pipeline
- Pi5 captures frames → sends to Mac Mini for inference → Mac Mini returns detections → Pi5 uploads annotated frames to Supabase storage at max 1/min.
- Browser polls latest frame every ~30s for viewer tab.
- Live stream = optional; situational awareness is the goal, not real-time video.

## Branch + deploy rules
- Work on `arras/*` branches in LunaV, R-Tessera, Labs.
- Push to GitHub for record; do not merge to `main`.
- Prevent Vercel auto-deploy on feature branches with `[skip deploy]` or by pausing Git integration for those repos.
- New Supabase project for ARRAS; do not pollute LunaV production DB.
