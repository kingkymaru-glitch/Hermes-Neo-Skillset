# Honest online/offline gating

## The bug
A live-resource control was gated on a URL-string field that is set ONCE at
boot to a constant (`deviceStatus.snapshot = '/edge-api/shot.jpg'`):

```jsx
// WRONG — snapOk is always truthy, so the card renders even when offline,
// painting a broken <img> (502) and opening a 502 in a new tab.
{snapOk && (
  <a href={deviceStatus.snapshot} target="_blank" rel="noreferrer">
    <img src={deviceStatus.snapshot} alt="snapshot" />
    <span>SNAP</span>
  </a>
)}
```

## The fix
Gate on a real `online` boolean that the poll loop sets from fetch success/failure.

Data context (android / device mode poll):
```jsx
try {
  const res = await fetch(TELEMETRY_URL)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  // ...parse...
  setDeviceStatus(d => ({ ...d, online: true, gpsFix: !!fix }))
} catch {
  // proxy 502 / device unreachable — surface honestly
  setDeviceStatus(d => ({ ...d, online: false, gpsFix: false }))
  setConnection('offline')
}
```

Consumer:
```jsx
const online = deviceStatus?.online !== false
// video:
{videoOk && online
  ? <img key={seq} className="feed" src={deviceStatus.stream} alt="live" />
  : <div className="feed feed--off">{videoOk ? 'DEVICE OFFLINE' : 'NO VIDEO STREAM'}</div>}
// snapshot:
{online && snapOk && (
  <button className="snap" onClick={/* cache-busted open */}>
    <img src={`${deviceStatus.snapshot}?_=${seq}-${Date.now()}`} alt="snapshot" />
    <span>SNAP</span>
  </button>
)}
{!online && snapOk && <div className="snap snap--off"><span>OFFLINE</span></div>}
```

## CSS notes
- Snapshot tile: `display: inline-flex; padding: 0; cursor: pointer;` so a
  `<button>` looks identical to the old `<a>`. Hover => `border-color: var(--neon-cyan)`.
- `--off` variant: `border-style: dashed; cursor: default; align-items: center;
  justify-content: center;` with a faint "OFFLINE" label.

## Why this matters for telemetry screens
A wall of broken `<img>`s (502) reads as "the app is broken" when really the
device is just down or the proxy IP is stale. Honest offline state turns a
mystery into an actionable signal.
