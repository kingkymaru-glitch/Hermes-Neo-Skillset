# `inert` vs `aria-hidden` — worked example (MARU app)

## Full Chrome DevTools warning
```
[Issue] Blocked aria-hidden on (index):1
Focus must not be hidden from assistive tech users.
Focused element:
  button.sensors-close
Ancestor:
  <aside class="sensors-drawer" aria-hidden="true">
```

## Why it fires
The Sensors drawer is closed → `aria-hidden="true"` (screen readers ignore it). But the
`.sensors-close` button inside it still has keyboard focus retained. WAI-ARIA spec: you
cannot hide a focused element from assistive tech. Chrome blocks the `aria-hidden` and
logs the warning. App still works; it's an a11y + console-noise defect.

## The fix (React 19 native boolean prop)
In `App.jsx`, every drawer that toggles `aria-hidden` also got `inert={!open}`:

```jsx
<aside className={`cmd-drawer ${drawerOpen ? 'open' : ''}`}         aria-hidden={!drawerOpen} inert={!drawerOpen}>
<aside className={`chat-drawer ${chatOpen ? 'open' : ''}`}         aria-hidden={!chatOpen}    inert={!chatOpen}>
<aside className={`settings-drawer ${insightsOpen ? 'open' : ''}`} aria-hidden={!insightsOpen} inert={!insightsOpen}>
<aside className={`settings-drawer ${settingsOpen ? 'open' : ''}`} aria-hidden={!settingsOpen} inert={!settingsOpen}>
<aside className={`sensors-drawer ${sensorsOpen ? 'open' : ''}`}   aria-hidden={!sensorsOpen}  inert={!sensorsOpen}>
```

`inert` removes the subtree from tab/focus order, so a focusable child can never sit
inside a hidden drawer → contradiction gone → warning gone.

## React version gate
- React 19.x (this app: 19.2.7): `inert={bool}` is native — write it directly.
- React 18.x and older: `inert` is NOT a React prop. Use a ref: `el.inert = !open`,
  or a string attribute. Writing `inert={bool}` silently does nothing on 18.

## Verify
`npm run build` green, refresh localhost:5174, toggle each drawer open→closed, confirm
the warning no longer appears.
