# Flyout / Drawer Architecture (MARU dashboard)

Documented after the 2026-07-17 session where the user (a) moved the Connection
button out of the Overview header into a new right-side **Settings** flyout, and
(b) pulled `SensorsPanel` OUT of the left command drawer into its own right-side
**Sensor Clusters** flyout. Governing rule, stated verbatim by the user:

> **Main flyout = LEFT. Sensor clusters + all sensory flyout tabs = RIGHT.
> They must never collide with the main flyout tab.**

## Current flyout geography (App.jsx)

| Side  | Flyout                    | Trigger                       | State           | Edge anchor | Notes                                          |
|-------|---------------------------|-------------------------------|-----------------|-------------|------------------------------------------------|
| LEFT  | `cmd-drawer` (main)       | `cmd-trigger` › / marker click| `drawerOpen`    | `left:0`    | Overview + `S22Console` (when an asset is selected). |
| RIGHT | `chat-drawer` (RAG)       | "Summon MARU AI" action card  | `chatOpen`      | `right:0`   | purple (`rgba(192,132,252,…)`) left border.    |
| RIGHT | `settings-drawer`         | gear `conn-gear-btn` in header| `settingsOpen`  | `right:0`   | holds `ConnectionLaunch` pinned to its bottom. |
| RIGHT | `sensors-drawer` (Sensor Clusters) | "Sensor Clusters" action card | `sensorsOpen` | `right:0` | cyan (`rgba(56,189,248,…)`) left border. |

All overlays share the fixed-overlay + absolutely-positioned drawer profile
below. Overlays use `pointer-events:none`; only the drawer gets
`pointer-events:auto` so the 3D canvas stays draggable underneath.

## Mutual exclusion (the collision rule)

The "Sensor Clusters" action card lives in the LEFT overview. Clicking it must
NOT leave the left drawer up while a right panel opens. The `openSensors()`
helper in `DashboardInner` collapses the left AND opens the right in one shot:

```js
function openSensors() {
  // Collapse the LEFT main flyout, then open the RIGHT sensory flyout — never both.
  setDrawerOpen(false)
  setSensorsOpen(true)
}
```

This REPLACED the old `drawerView` switch, where `SensorsPanel` was a sub-view
inside the left `cmd-drawer` (`drawerView === 'sensors'`). That nesting made the
panel visually part of the left flyout and risked collision/confusion. After the
extraction, `drawerView` had no consumers and was deleted (see pitfall).

## RIGHT-side flyout CSS profile (reusable)

Mirror this verbatim for any new right-side flyout so they match the existing
chat/settings/sensors drawers (same width, same slide easing, same glass tokens):

```css
.NAME-overlay {
  position: fixed;
  inset: 0;
  z-index: 24;            /* chat=25, settings=25, sensors=24, cmd=20 */
  pointer-events: none;
}
.NAME-drawer {
  position: absolute;
  right: 0;               /* ← RIGHT anchor (use left:0 only for the main flyout) */
  top: 0;
  height: 100%;
  width: 420px;           /* match sibling widths to avoid edge jitter */
  max-width: 90vw;
  pointer-events: auto;
  transform: translateX(104%);
  transition: transform 0.34s cubic-bezier(0.22, 1, 0.36, 1);
  background: var(--glass-bg);
  backdrop-filter: var(--glass-blur);
  border-left: 1px solid rgba(56, 189, 248, 0.25);
  box-shadow: -8px 0 40px rgba(0, 0, 0, 0.45);
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 22px 20px;
  box-sizing: border-box;
  overflow-y: auto;
  color: var(--ink);
  font-family: system-ui, 'Segoe UI', Roboto, sans-serif;
}
.NAME-drawer.open { transform: translateX(0); }
```

The Settings flyout differs only in that the connection launcher is pinned to the
bottom (`margin: 0 18px 18px`) and the body is `flex:1` so the launcher sits at
the foot. Keep new flyouts consistent with this rhythm.

## Pitfall carry-over

When you pull a sub-view out of the left drawer (removing the `drawerView`
branch), the `drawerView` / `setDrawerView` state becomes unused → oxlint
`no-unused-vars` warning. `search_files` for the name, delete the `useState`
declaration AND every `setXxx(...)` call site, then re-lint. Don't leave a dead
state var — it trips the stale-evidence gate. (Caught + fixed this session.)

## R-Tessera fork: right-rail launcher (`RMenuFlyout`) + generalized slot manager

R-Tessera (the live MARU fork) extends the right side with a persistent
launcher tab and a generalized single-active flyout manager. When you add a
new right-side panel here, follow this instead of the older `openSensors()`
one-shot.

### The launcher tab
A fixed, always-visible tab pinned to the mid-right edge opens the main menu:
```jsx
<button className="rt-tab" onClick={() => setRtmenuOpen(true)} aria-label="R-Tessera menu">
  <img src="/r-tessera-logo.png" alt="R-Tessera" className="rt-tab-logo" />
</button>
```
`.rt-tab` is `position:fixed; right:0; top:50%; transform:translateY(-50%)`.
It does NOT collide with the bottom-left `MapControlPanel` (`mcp-trigger`) —
different edges. Keep that separation (globe chrome rule: left = main, right =
sensory/utility).

### Single-active slot manager (in `DashboardInner`)
State = one boolean per slot: `mapctlOpen, sensorsOpen, chatOpen, settingsOpen,
insightsOpen, rtmenuOpen, nodelistOpen, settingOpen`. Three helpers drive them:

```js
function openRight(which) {            // any right slot, no same-tab guard
  setDrawerOpen(false)
  setChatOpen(which === 'chat'); setSensorsOpen(which === 'sensors')
  setSettingsOpen(which === 'settings'); setInsightsOpen(which === 'insights')
  setMapctlOpen(which === 'mapctl'); setRtmenuOpen(which === 'rtmenu')
  setNodelistOpen(which === 'nodelist'); setSettingOpen(which === 'setting')
  setFlyoutSide('right')
}
function openSecondary(which) {        // same-tab no-op guard (no re-open flash)
  if (flyoutSide === 'right' && (
    (which === 'sensors' && sensorsOpen) || (which === 'mapctl' && mapctlOpen) ||
    (which === 'rtmenu' && rtmenuOpen) || (which === 'nodelist' && nodelistOpen) ||
    (which === 'setting' && settingOpen) /* …others… */)) return
  // …set only the matching slot true, setFlyoutSide('right')…
}
function closeRight(which) {
  if (which === 'rtmenu') setRtmenuOpen(false)  /* …others… */
  setFlyoutSide(null)
}
// closeAllRight() clears every right slot; closeAllFlyouts() clears left + right.
```
Render every panel through one inert overlay + drawer, exactly like
`MapControlPanel`/`SensorsPanel`:
```jsx
<div className="rt-overlay">
  <aside className={`rt-drawer ${open ? 'open' : ''}`} aria-hidden={!open} inert={!open}>
    {/* … */}
  </aside>
</div>
```

### Naming trap: `settingOpen` ≠ `settingsOpen`
`settingOpen` = the R-menu's lightweight **Setting** flyout (About / Version /
Help — intentionally empty placeholders per spec). `settingsOpen` = the deep
**Settings** drawer (ConnectionLaunch, governance, etc.). They are DIFFERENT
slots. Do not wire the R-menu "Setting" button to `settingsOpen` — it opens the
wrong (heavy) panel. Keep the two names distinct.

### Reuse, don't reinvent
- **New Node Group** modal reuses the existing `cameraFocusLonLat()` map-pick
  helper via a `getFocusCoord` prop (same as `NodeEditorModal`), and the
  existing `createNode` / `NODES_API` transport. Groups are stored as nodes
  with `isGroup:true` so they appear in the Node List flyout.
- **Layer Control** button in the R-menu calls `openSecondary('mapctl')` — the
  SAME slot the bottom-left layer trigger opens. One source of truth.

### Placeholder nuance (user preference)
Empty-by-design scaffolding the user explicitly requested (e.g. Setting flyout
buttons left blank "for now") is NOT "dead UI" — do not "clean it up" or delete
it. Only remove UI the user did NOT ask to be empty.
