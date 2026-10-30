# my-digital-twin — UI/UX Component Patterns (Box 1 / Box 2)

Condensed, reusable patterns for the MARU dashboard's React/CSS layer. These
are NOT one-session fixes — they're the standing conventions that every future
visual change must match.

## Right-rail "secondary" drawer architecture (KEY DECISION)
- `openSecondary(which)` opens a right-side flyout (Sensors / MARU AI / Settings)
  and MUST NOT close the main left command drawer — they coexist side by side.
  This was a deliberate fix: an earlier build called `setDrawerOpen(false)` so
  Sensor Cluster slammed the main tab shut; the user rejected that ("i dont want
  this"). Match Map Control Systems behaviour (it uses `setMcpOpen(true)`, never
  touches the drawer).
- All right-rail drawers are standardized to **360px** (were 420/380/340; MCP
  was 248px on-map and is now also 360px — see correction below).
- Slide uses `transform: translateX(104%) -> 0` (NOT scale/opacity) with
  `transition: transform 0.34s cubic-bezier(0.22,1,0.36,1)` — same easing and
  motion across sensors/chat/settings/insights/MCP so they feel like one system.
  The MCP card's old pop/scale (`translateX(16px) scale(0.98)`) was replaced by
  the shared `.mcp-drawer` translateX slide to match the others exactly.
- **CORRECTION (overrides earlier note):** Map Control Systems is NOW a
  first-class right-drawer sibling, NOT an on-map 248px card. The user explicitly
  required "the same size and animation as the rest of the tab... it shall not be
  smaller and act differently. standardize the animation for all so it behaves
  like the secondary tab for Sensor Clusters and Summon MARY AI." So MCP became a
  360px `.mcp-drawer` with the identical translateX slide. Do NOT revert it to a
  smaller on-map card.

## Box 2 — Sensor Clusters three-level drill-down
File: `src/App.jsx` `SensorsPanel` + `SensorDetail`.
- Flat edge channels (`sensorPayloads` from `useEdgeData`) are grouped by a
  `SENSOR_GROUPS` map: Environment (temp) + Structural (tilt/strain/rms).
- State: `level` (cluster|group|sensor), `groupKey`, `localSensorId`.
- Breadcrumb `<nav class="sensors-breadcrumb">` gives back-nav at every level.
- L1 list of groups (with worst-flag rollup), L2 group -> its sensor rows, L3
  `SensorDetail` (type, live value, status, gateway uptime).
- Map-pin deep-link: `useEffect` on `selected` -> `findSensor(selected.id)`; if
  no match (demo map assets carry no sensor IDs) just stay at L1 — NEVER render
  an empty detail view.
- Reuses `.shm-*` tokens (`.shm-row`, `.shm-dot`, `.shm-value`, `.shm-flag`,
  `.shm-conn`). New classes: `.shm-group`, `.shm-sub`, `.shm-meta`, `.shm-count`,
  `.sensor-detail`, `.sensor-hero`, `.sensor-facts`, `.flag-pill-*`.

## Map-control button relocation (beside Locate Me) + Map Control Systems drawer
- The layer-trigger moved from the top-right MCP card to the **bottom-left**,
  next to the Locate Me (homing) crosshair, as one map-control cluster.
- Styled to match: 50px glass circle, `border-radius:50%`, same `box-shadow`
  glow, and the SAME `animation: pulse-border 2.4s ease-in-out infinite` as
  Locate Me (keyframes `@keyframes pulse-border` at App.css ~L602).
- Slides clear of the open main drawer via `.shifted { left: 516px }` (Locate Me
  is `left:458px` + 50 width + 8 gap). Driven by a `drawerOpen` prop passed down
  to `MapControlPanel` (which stays mounted inside `<Viewer>` because
  `useLayerManager` needs `useCesium()`).
- `position: fixed` is SAFE inside `MapControlPanel` even though it's under
  `<Viewer>`: the `.mcp-overlay` ancestor is `position:fixed; inset:0` (no
  transform), and the Viewer container fills the viewport, so the fixed button
  and the absolute `.mcp-drawer` resolve to the viewport, not the Cesium
  container. (Earlier the parent was `.mcp` `position:absolute`; it is now
  `.mcp-overlay` `position:fixed` — same safe outcome.)
- The trigger no longer owns open state. It delegates to the parent's single
  active flyout manager: `onClick={onLaunch}` where
  `onLaunch={() => openSecondary('mapctl')}`, and the close button + Escape call
  `onClose={() => closeRight('mapctl')}`. `MapControlPanel` props are now
  `{ open, onLaunch, onClose, drawerOpen }` (was `{ open, setOpen, drawerOpen }`).
- The drawer itself is `.mcp-drawer` (360px, `translateX(104%) -> 0` on
  `.is-open`, same easing as the other right drawers). Title "MAP CONTROL
  SYSTEMS". It is one of the single-active right slots — opening Sensors/Chat/
  Settings/Insights closes it and vice-versa.

## Setting flyout — two-level drill-down (menu -> detail)
File: `src/App.jsx` `SettingsPanel` + `SETTING_ITEMS`.
- Pattern for converting a FLAT settings drawer into a drill-down: extract the
  inline `<aside>` body into a `SettingsPanel` component with local `view` state
  (null = menu; else item key), driven by a `SETTING_ITEMS` array of
  `{key,label,blurb,glyph}`.
- L1 = menu of `.settings-menu-row` buttons (glyph + label + blurb + chevron);
  L2 = per-item `.settings-detail` view rendered in-place. Reuse the SAME
  `<nav class="sensors-breadcrumb">`/`.crumb` breadcrumb as SensorsPanel so both
  drawers navigate identically (Setting > Item, click crumb to go back).
- Do NOT lose existing behaviour when reshuffling: route items back to the real
  components/handlers — Edge Setting -> `ConnectionLaunch` (opens
  ConnectionSettings modal), Contact/Report -> `onSupport('contact'|'report')`
  (SupportModal). Pass these in as props (`onClose`, `onOpenConn`, `onSupport`)
  rather than reaching into App state.
- **System Governance IS a Setting item** (correction to an earlier session).
  The Setting flyout menu is: How To, Contact, Edge Setting, **System Governance**,
  Report a Problem. Clicking System Governance opens the live `<GovernancePanel>`
  (kill-switch / circuit breakers / egress budget) as an in-place detail view.
  The thing that is NOT in Setting is the main-tab **Insights** card (knowledge
  layer: standards / ISO / PE expert) — that is its own separate right-drawer
  placeholder. Do not re-conflate the two: a prior build split the governor OUT
  of Setting into a standalone main-tab drawer; the user corrected that — the
  governor lives UNDER Setting, the knowledge layer ("Insights") is the separate
  main-tab surface.
- The trigger button label was renamed Edge Connection -> "Setting" in BOTH the
  drawer footer (`.drawer-footer-btn`) and the overview action card — grep the
  old label to catch every render site before claiming a rename done.
- New classes: `.settings-menu-row`, `.settings-menu-text`, `.settings-menu-chev`,
  `.settings-detail`, `.settings-detail-lead`, `.settings-steps`. Reuse
  `.settings-action` + `.settings-action-glyph` for the detail-view CTAs.
- Dedup user-supplied item lists (a spec listing "Contact" twice = one row);
  flag the dedup back to the user rather than silently rendering duplicates.

## Main-tab "Insights" card (knowledge layer) + governor UNDER Setting
File: `src/App.jsx` (`insightsOpen` state + dedicated placeholder drawer) +
`GovernancePanel` (mounted under Setting).
- **CRITICAL architecture correction.** The 5-Box model splits the main-tab card
  from the safety governor:
  • Main-tab card = the **knowledge layer** (engineering standards, ISO docs,
    inspection process playbooks, PE expert insights that decide how/what/when
    inspection parameters are used). It was named "Governance & Safety" then
    "System Governance" in earlier builds — BOTH WRONG. Final name is
    **"Insights"**. It opens its own right-drawer placeholder (`insightsOpen`);
    no content yet. Glyph: stacked-book; subtitle "Standards · ISO · PE expert".
  • The **safety governor** (kill-switch / circuit breakers / egress budget) is
    NOT on the main tab — it lives UNDER **Setting -> "System Governance"**, which
    mounts the live `<GovernancePanel>` as an in-place detail view.
- v0.2.0 Dev Log records the original sin at commit `afa870b` ("nested Governance
  in Settings flyout"). The pendulum then swung too far (governor pulled OUT to its
  own main-tab drawer) — the user corrected that too. End state: governor under
  Setting; Insights = separate main-tab knowledge surface. Do not re-conflate.
- Both the Insights drawer and the Setting flyout share `.settings-drawer` /
  `.settings-head` / `.settings-close` styles + the 360px right slot; the strict
  one-side model means they can never show at once (no collision).
- Wiring checklist when adding a new right-drawer sibling: add `useState`, set it
  in `openMain`/`openRight`/`openSecondary`, add an `if (which === '<key>')`
  branch in `closeRight` + `closeAllFlyouts`, and render an
  `<aside className={`settings-drawer ${xOpen ? 'open' : ''}`}>` block.
- **The single-active flyout manager is the source of truth for ALL right
  drawers** — Sensors (`sensorsOpen`), MARU AI (`chatOpen`), Settings
  (`settingsOpen`), Insights (`insightsOpen`), and Map Control Systems
  (`mapctlOpen`). They all go through `openSecondary(which)` /
  `openRight(which)` / `closeRight(which)` and share the `flyoutSide` slot, so
  exactly one right panel is visible at a time and NONE of them closes the main
  left command drawer. Map Control Systems is NOT an exception anymore — it used
  to be a standalone `mcpOpen` toggled by `setMcpOpen(true)` outside the manager
  (which let it overlap other right drawers); it is now `mapctlOpen` inside the
  same manager. When promoting any future panel to a right drawer, wire it into
  the manager rather than giving it a private `setXxxOpen` toggle.

## Cesium startup camera — center the globe, do NOT lock navigation
File: `src/App.jsx` `INITIAL_CAMERA` const + the `TelemetryTracker` viewer effect.
- **The startup camera is an OPENING POSE ONLY. Never lock navigation to it.**
  A build framed the camera on Peninsular Malaysia AND added
  `screenSpaceCameraController.maximumZoomDistance = 13000000` + a `homeButton`
  `beforeExecute` override that flew back to that frame. The user rejected all of
  it: "i did not ask the starting screen with locked gps to Malaysia. rather
  align the earth so it sets in the middle of the screen when start, do not lock
  the navigation."
- Correct "center the globe" pose: `Cartesian3.fromDegrees(0.0, 0.0, 24000000)`
  with `pitch: -90deg` (straight down), heading/roll 0 — full sphere framed dead
  center. Apply once via `viewer.camera.setView(INITIAL_CAMERA)` in the viewer
  effect, then do NOTHING else.
- Do NOT set `maximumZoomDistance`, do NOT override `homeButton` beforeExecute,
  do NOT re-fly on any event. Pan/zoom/tilt must stay fully free after load.
- Distinguish "initial framing" (a one-shot `setView` — fine) from "navigation
  lock" (zoom ceilings, home overrides, re-centering listeners — only if the user
  explicitly asks). When in doubt, framing yes, lock no.

## Pitfall: JSX className vs CSS mismatch = unstyled block "stuck on screen"
Symptom this session: user asked "why is there base layer control on top of the
screen?" It was NOT the Cesium `baseLayerPicker` (already `false`, along with
geocoder/homeButton/timeline/animation/navHelp/sceneModePicker). The real cause:
`MapControlPanel.jsx` rendered `<aside className="mcp-drawer">` (always mounted in
the DOM so `useLayerManager`/`useCesium` has the engine), but App.css still only
defined the OLD `.mcp` / `.mcp-card` rules — there was **no `.mcp-drawer` rule at
all**. With zero positioning CSS the always-mounted `<aside>` collapsed to a
static block at the top-left of the Cesium container, permanently showing "MAP
CONTROL SYSTEMS / Base Layers / Data Overlays".
- **Debug recipe:** when a stray/unstyled panel appears on the map, grep the CSS
  for the EXACT className the JSX renders (`.mcp-drawer`), not the class you think
  exists. A rename in the component that wasn't mirrored in CSS leaves an
  always-mounted element with no positioning. Fix = add the matching rule (here:
  `.mcp-drawer { position:fixed; top:0; right:0; width:360px; height:100%;
  transform:translateX(104%) }` + `.mcp-drawer.is-open { transform:translateX(0) }`).
- Remove the dead old rules (`.mcp`, `.mcp-card`, `.mcp-card.is-open`) in the
  same patch and fix any now-inaccurate section comment.
- **Doc correction:** an earlier note in this file claimed a `.mcp-overlay`
  `position:fixed; inset:0` ancestor makes the fixed trigger safe. There is NO
  `.mcp-overlay` wrapper — `MapControlPanel` returns a Fragment with the
  `.mcp-trigger` button and the `.mcp-drawer` aside as SIBLINGS. Both use
  `position:fixed`, which resolves to the viewport regardless of the Cesium
  container, so they're safe on their own — but don't rely on a wrapper that
  isn't there.

## Status Rail — external links
- The Status Rail center segment is classification/branding placeholder text
  ("RESTRICTED ACCESS // ..."). Builder credit ("ENG BY MARU LABS") is an
  assistant constant; the center label is the user's to own. When asked to point
  it at the user's GitHub, link handle `kingkymaru-glitch`
  (`https://github.com/kingkymaru-glitch`), `target="_blank"
  rel="noreferrer noopener"`, via a `.rail-link` class that inherits the 11px
  mono tone (subtle cyan underline, neon-cyan on hover) — don't introduce a
  default-blue anchor into the aerospace rail.

## Workflow guardrails (creative UI)
- Hold lint/test nags until the user eyeballs the running app (localhost:5174),
  but ALWAYS run `npm run lint && npm run build && rm -rf dist` before committing.
- Commit per feature; never one giant WIP commit.
- Recheck rule after every visual change: any overlap? stray/orphan button?
  Match the surrounding component family before declaring done.
- **Check the Obsidian vault BEFORE reshaping nav/architecture.** The MARU
  blueprint (5-Box model) lives in `~/Documents/obsidian_maru_1` — resume order
  VAULT MAP -> HermesProgress -> `DT Inspection MARU.md`. When the user says an
  item "was meant for a different purpose" or "check the vault about the whole
  idea", do NOT guess the target of a nav item — read the blueprint first, then
  confirm the destination (or pick the recommended option). This is exactly how
  the Governance-vs-Setting conflation was caught and fixed.
- **Prop-destructure pitfall (MapControlPanel):** when a parent passes a prop
  (e.g. `drawerOpen` into `MapControlPanel`), the child MUST destructure it in
  its signature or it throws `ReferenceError: <x> is not defined` at render. A
  "variable not defined" crash in a presentational component that receives data
  from App almost always means the prop is passed but not destructured — verify
  the signature before hunting for a missing context/hook. Fix:
  `function MapControlPanel({ open, onLaunch, onClose, drawerOpen })` +
  `npm run lint` green.
- **Private-toggle overlap pitfall:** a right drawer must never own its own
  `useState` + `setXxxOpen(true)` toggle outside the single-active manager. The
  old Map Control panel did exactly that (`mcpOpen` / `setMcpOpen`) and so could
  sit open ON TOP OF the Sensors/Chat drawers — a double-panel collision the user
  rejected ("it shall not be smaller and act differently, standardize ... for
  all"). Always route a right panel through `openSecondary`/`closeRight` so it
  shares the `flyoutSide` slot and is mutually exclusive with its siblings.
