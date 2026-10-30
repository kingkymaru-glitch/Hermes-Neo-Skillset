# Lag debugging — real-time CV webapp viewer

Symptom class: "video lags / lag grows the longer it runs." Root causes, in order of
how often they bite. The rAF fix alone is NOT sufficient — causes 1 & 2 below are the
ones the original skill missed and that regrow lag even after rAF is in place.

## Cause 0 (necessary, from flask-ws-yolo-pattern.md)
Per-message `<img>.src = blobURL` repaints slower than frames arrive → event-loop
backlog → displayed frame falls behind. Fix: `<canvas>` + `requestAnimationFrame`
paint loop, store newest bytes, drop stale. THIS MUST EXIST FIRST but is not enough.

## Cause 1 — Unbounded decode fan-out (most common "still lags" cause)
WRONG (per-message, ungated):
```js
ws.onmessage = (ev) => {
  if (ev.data instanceof ArrayBuffer) {
    createImageBitmap(new Blob([ev.data], {type:'image/jpeg'}))
      .then(b => { if(latest) latest.close(); latest = b; }).catch(()=>{});
  }
};
```
Why it grows: `createImageBitmap` is async; firing one per message with no gate means
promises queue and decode on the MAIN thread even for frames already discarded. Under
load the main thread saturates, rAF starves, lag increases monotonically with run time.

RIGHT (single in-flight decode gate — drop frames while decoding):
```js
let latestBitmap = null, pendingBytes = null, decoding = false;
function decodeNext(){
  if (!pendingBytes){ decoding = false; return; }
  decoding = true;
  const bytes = pendingBytes; pendingBytes = null;
  createImageBitmap(new Blob([bytes], {type:'image/jpeg'}))
    .then(b => {
      if (latestBitmap) latestBitmap.close();
      latestBitmap = b;
      if (pendingBytes) decodeNext();   // newer frame arrived mid-decode: continue
      else decoding = false;
    })
    .catch(() => { decoding = false; });
}
// in ws.onmessage (binary branch):
pendingBytes = ev.data;
if (!decoding) decodeNext();
```
Decode work is now bounded to ~display rate; dropped frames cost nothing.

## Cause 2 — Unbounded log DOM
WRONG: `el.innerHTML += '<div>...</div>'; el.scrollTop = el.scrollHeight;` on every
detection forever. Node grows without limit → every append + scroll gets costlier.
RIGHT (cap to last N):
```js
el.innerHTML += '<div class="det">'+d.cls+' '+d.conf+'</div>';
while (el.childElementCount > 50) el.removeChild(el.firstChild);
el.scrollTop = el.scrollHeight;
```

## Cause 3 (server, secondary) — encode every frame
If `infer_loop` re-encodes EVERY captured frame to JPEG (50+ Hz) but the WS pump ships
~30 Hz and drains-to-newest, most encodes are wasted. Throttle:
```python
now_enc = time.time()
if now_enc - getattr(infer_loop, "_last_enc", 0) >= 1.0/30.0:
    infer_loop._last_enc = now_enc
    jpg = encode(draw(frame, dets), quality=60)
    # drop-oldest then put
```
Smaller win than 1 & 2 once those are fixed; removes a constant CPU floor.

## Verification (a lag fix CANNOT be proven by HTTP 200)
1. Served HTML contains the gated decoder (`decodeNext`) + bounded log (`childElementCount > 50`).
2. `node --check` the extracted inline `<script>` — no syntax errors.
3. ASK THE USER to run it for several minutes and report whether lag stays flat.
   There is no headless assertion for "lag doesn't grow over time." Trust the user's
   eyes for the long-run behavior; the checks above only prove the fixes are present.

## Gotcha — blank page after a viewer edit
If the page is blank on load (before even clicking Start), suspect a render-blocking
external `<script src=cdn>` (e.g. Cesium) that failed/slowed → the inline script never
runs. Remove CDN deps for offline-first tools (see SKILL.md Cesium rule). Also confirm
only ONE server instance is bound to the port — a stale second instance serving a
pre-edit page causes confusing "nothing changed" behavior.
