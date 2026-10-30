# MARU Flyout / Drawer Convention (my-digital-twin)

Authoritative drawer model for the MARU dashboard. Captured after the
2026-07-18 UI/UX recheck where the user rejected a behavior and asked for
size standardization + a 3-level sensor tree.

## Architecture of the nav surfaces

- **Main command drawer** — top-left `cmd-trigger`, primary nav (OverviewPanel).
  Slides from the LEFT. This is the home base.
- **Secondary tabs (right rail)** — Sensor Clusters, MARU AI Engine (chat),
  Governance & Safety (Settings). Open on the RIGHT. These are siblings of the
  main drawer, NOT a replacement for it.
- **Map Control Systems** — NOT a side drawer. It is an on-map card docked
  top-right (`.mcp`, z-22, ~248px) inside the Cesium `<Viewer>`. It is the
  "invisible-until-needed" layer orchestrator. Keep it separate.

## Hard rules

1. **Main drawer stays open when a secondary opens.** This was a user
   correction. The original `openSecondary(which)` called `setDrawerOpen(false)`
   — the user explicitly did NOT want that ("i dont want this"), citing that
   Map Control Systems already kept the main drawer open. Fix: `openSecondary`
   sets ONLY the specific open-flag (`setSensorsOpen` / `setChatOpen` /
   `setSettingsOpen`) + `setFlyoutSide('right')`; it never touches
   `drawerOpen`. All secondary buttons must behave like Map Control.
2. **Right-rail drawers standardized to 360px.** Were 420 (sensors) / 380 (chat)
   / 340 (settings). Now all `width: 360px`. Share the standard transition:
   `transform 0.34s cubic-bezier(0.22, 1, 0.36, 1)` slide+fade, toggled by an
   `.open` class on an always-mounted panel (no mount/unmount pop).
3. **Do NOT force Map Control to 360px.** It is a different surface (on-map
   overlay). "Standardize the size of all secondary tabs" means the right-rail
   drawers; the on-map card is intentionally smaller. If the user later wants
   Map Control promoted to a 360px side drawer, that is a deliberate redesign
   of the "invisible-until-needed on-map" decision — confirm before doing it.
4. **Re-click same open secondary = no-op.** `openSecondary` early-returns when
   the requested tab is already open (no re-open animation). Keeps repeated
   clicks visually inert.

## Sensor Clusters — 3-level drill-down (Box 2)

Flat edge channels come from `useEdgeData().sensorPayloads` (metrics:
`tilt`, `strain`, `rms`, `temp`). They are grouped via a `SENSOR_GROUPS` map so
swapping the feed later needs zero component changes:

```
SENSOR_GROUPS = [
  { key:'environment', label:'Environment Sensors', blurb:'Atmospheric & thermal field conditions', metrics:['temp'] },
  { key:'structural',  label:'Structural Sensors',  blurb:'Load, strain & vibration of the asset', metrics:['tilt','strain','rms'] },
]
```

- **L1 Sensor Clusters** — list the groups. Each group row shows channel count
  + a worst-flag rollup (any alert → alert, else any warning → warning, else
  nominal). Reuse `.shm-row.flag-*` styling.
- **L2 group** — its channels as `.shm-row`s (live value + flag). A scope line
  shows the group blurb.
- **L3 sensor** — `SensorDetail` card: hero live value + flag pill, then a
  `<dl class="sensor-facts">` with Type (metric label), Sensor ID (mono), Live
  status, Gateway uptime (`formatUptime(deviceStatus.uptimeSec)`), Feed cadence,
  Threshold state.
- **Breadcrumb** nav (`Sensor Clusters › Group › Sensor`) with a `.current`
  marker and clickable ancestors — back affordance at every level.
- **Map-pin deep-link** — in `SensorsPanel`, a `useEffect` matches
  `selected.id` against a sensorPayload; on hit, jump straight to L3 (set
  `groupKey`, `localSensorId`, `level:'sensor'`). Demo map assets have no sensor
  ID → no match → stay at L1 (never render an empty detail view).
- **State**: `level` ('cluster'|'group'|'sensor'), `groupKey`, `localSensorId`.

Reuse the existing `.shm-*` CSS tokens so the tree stays visually consistent
with the rest of the HUD.

## Delivery discipline

- Build features in small, single-purpose commits (user: "always break in small
  chunks" + "next"). Commit 1 = behavior/width standardize; commit 2 = the
  drill-down, etc.
- Verify each chunk with `npm run lint` (oxlint) + `npm run build` (vite), then
  `rm -rf dist`. The user eyeballs in a running `localhost:5174` — you do NOT
  browser-test here, so state that explicitly rather than claiming a visual pass.
- Apply the standing UI/UX recheck loop after every visual change (overlap /
  stray buttons / collisions) per memory.
