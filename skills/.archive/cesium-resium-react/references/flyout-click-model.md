# Flyout click model + popover standardization (MARU mission-control UI)

Reusable patterns from the 2026-07-18 UI/UX pass on the my-digital-twin
dashboard. Use these whenever a flyout/side-panel dashboard needs (a) a
brand/HUD that doesn't collide on narrow viewports, (b) every panel to animate
identically, and (c) a main-flyout -> secondary-tab navigation where re-clicking
the same button does NOT re-open/re-animate the secondary.

## 1. Single-active side manager (App.jsx)

State:
```js
const [drawerOpen, setDrawerOpen] = useState(false)    // LEFT main flyout
const [sensorsOpen, setSensorsOpen] = useState(false)  // RIGHT tab
const [chatOpen, setChatOpen] = useState(false)        // RIGHT tab
const [settingsOpen, setSettingsOpen] = useState(false)// RIGHT tab
const [flyoutSide, setFlyoutSide] = useState(null)      // 'left' | 'right' | null
```

Helpers (ONE active side at a time — left XOR right, never both):
```js
function openMain() {
  setDrawerOpen(true); setChatOpen(false); setSensorsOpen(false); setSettingsOpen(false)
  setFlyoutSide('left')
}
function openSecondary(which) {
  // Rule (b): same secondary already open -> NO-OP (no re-animation; drawer is
  // mounted and only the .open class is set, so the click is visually inert).
  if (flyoutSide === 'right' && (
    (which === 'sensors' && sensorsOpen) ||
    (which === 'chat' && chatOpen) ||
    (which === 'settings' && settingsOpen)
  )) return
  setDrawerOpen(false)            // Rule (c): open secondary -> main collapses
  setChatOpen(which === 'chat')
  setSensorsOpen(which === 'sensors')
  setSettingsOpen(which === 'settings')
  setFlyoutSide('right')
}
function closeRight(which) {
  if (which === 'chat') setChatOpen(false)
  if (which === 'sensors') setSensorsOpen(false)
  if (which === 'settings') setSettingsOpen(false)
  setFlyoutSide(null)
}
```

Wire the OverviewPanel action cards to `openSecondary(...)` (NOT openRight), so
repeated clicks on "Sensor Clusters" / "Map Control Systems" / "Governance &
Safety" while already open are inert. Map-click picks still route through
`openRight('sensors')` (sensor -> right tab) and `openMain()` (S22 -> left).

The drawers themselves must STAY MOUNTED and toggle `.open` (don't
unmount/remount), or the transition won't be continuous:
```jsx
<aside className={`sensors-drawer ${sensorsOpen ? 'open' : ''}`} aria-hidden={!sensorsOpen}>
```

## 2. Popover (Map Control) standardized to drawer motion

Problem: the card used `animation: mcp-pop 0.18s ease-out` + unmount-on-close,
while drawers slide via `transform 0.34s cubic-bezier(0.22,1,0.36,1)`. Mismatch.

CSS — keep the card mounted, drive with a transition, take it out of flex flow:
```css
.mcp { position: absolute; top: 12px; right: 12px; z-index: 22; display: flex; justify-content: flex-end; }
/* card OUT of flow so the closed (248px) card doesn't shove the trigger away */
.mcp-card {
  position: absolute; top: 0; right: 0;
  width: 248px;
  opacity: 0;
  transform: translateX(16px) scale(0.98);
  transform-origin: top right;
  transition: transform 0.34s cubic-bezier(0.22,1,0.36,1),
              opacity   0.34s cubic-bezier(0.22,1,0.36,1);
  pointer-events: none;
}
.mcp-card.is-open { opacity: 1; transform: translateX(0) scale(1); pointer-events: auto; }
```

JSX — always render the card, toggle `is-open` (no unmount):
```jsx
<div className="mcp" ref={rootRef}>
  {!open && (<button className="mcp-trigger" onClick={() => setOpen(true)}>...</button>)}
  <div className={`mcp-card${open ? ' is-open' : ''}`} role="dialog" aria-hidden={!open}>
    {/* ...card body... */}
  </div>
</div>
```
Because the card stays mounted, re-opening never re-pops — it just slides,
matching the four side drawers exactly.

## 3. Brand / HUD collision-proofing (responsive)

```css
.dt-hud { z-index: 12; }            /* above .map-brand z-11 so status wins */
.map-brand { z-index: 11; }
@media (max-width: 1200px) { .map-brand-sub { display: none; } }  /* shrink brand */
@media (max-width: 820px)  { .map-brand { display: none; } }      /* drawer header carries identity */
```
Math: brand left edge = `0.5*W - 186`; crosses HUD right edge (~362px) at
`W ~= 1096px`. Below that, shedding the sub-label then the whole brand keeps the
top-left HUD ("Edge (sim)" pill) readable.
