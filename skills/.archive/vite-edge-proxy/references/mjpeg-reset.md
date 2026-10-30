# MJPEG `<img>` live-reset pattern

## Problem
MJPEG (IP Webcam, most phone IP-cam apps) is served as a multipart still-image
stream. Browsers render it with `<img src=...>`, NOT `<video>`. Once loaded, the
`<img>` holds the HTTP connection OPEN and never re-requests. So:

- Changing the proxy target (device IP) in a Settings UI does nothing visible.
- A device that backgrounds/sleeps mid-session stalls the feed; no auto-recovery.

## Fix A — auto reset on settings change
Plumb a monotonic reconnect token (`connSeq`) from the data context into the
consumer. Bumping it remounts the `<img>` against the new target.

```jsx
function Consumer({ deviceStatus, connSeq }) {
  const [localSeq, setLocalSeq] = useState(0)
  const seq = `${connSeq ?? 0}-${localSeq}`
  return (
    <img key={seq} className="feed"
         src={`${deviceStatus.stream}?_=${seq}`}
         alt="live feed" />
  )
}
```

`key={seq}` forces React to unmount/remount the element (new `<img>` => new
request). `?_=${seq}` is belt-and-suspenders cache-busting in case a service
worker or the browser caches the URL.

## Fix B — manual ↻ button (stall recovery)
```jsx
<button className="refresh" onClick={() => setLocalSeq((n) => n + 1)}
        aria-label="Refresh stream" title="Re-connect to current device IP">↻</button>
```
Pairs with a small CSS `:active { transform: rotate(-180deg) }` for feedback.
Bumping `localSeq` remounts the same device IP without touching `connSeq`.

## Where connSeq comes from
Data-context `reconnect()` does `setConnSeq(n => n+1)`. Settings UI calls
`reconnect()` after saving a new IP. The poll-loop `useEffect` lists `connSeq`
in deps so it re-reads the live proxy target too.

## Snapshot (still) endpoints
For one-shot stills (`/shot.jpg`), the same cache-bust applies but is simpler —
just append `?_=${Date.now()}` at click time so each SNAP opens a fresh frame:
```jsx
onClick={() => window.open(`${deviceStatus.snapshot}?_=${Date.now()}`, '_blank', 'noopener')}
```
