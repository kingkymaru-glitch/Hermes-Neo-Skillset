# Streaming stability — Luna-EDGE proven fixes

Concrete patterns that stop the classic "works for 15s then lags / boxes flicker /
Stop hangs / phone won't connect" failures in an offline YOLO webapp. All verified
live on github.com/kingkymaru-glitch/luna-edge (Flask + flask_sock + OpenCV).

## 1. Anti-growing-lag paint loop (browser)
NEVER do `createObjectURL(blob)` + `img.src` on every WS message (~50/s) — callbacks
queue faster than paint and lag grows unboundedly. Instead:

```html
<canvas id="feed"></canvas>
<script>
const canvas = document.getElementById('feed');
const ctx = canvas.getContext('2d');
let latestBitmap = null, pendingBytes = null;
function fitCanvas(){ const w=canvas.clientWidth,h=canvas.clientHeight;
  if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;} }
function paint(){ fitCanvas(); if(latestBitmap) ctx.drawImage(latestBitmap,0,0,canvas.width,canvas.height);
  requestAnimationFrame(paint); }          // paint only on rAF; drop stale frames
requestAnimationFrame(paint);
// WS onmessage (binary): pendingBytes = ev.data; (no decode here)
</script>
```

## 2. Anti-flicker box hold (browser overlay)
Boxes baked into the JPEG pop in/out when a frame momentarily misses the object.
Ship the RAW frame from the engine (engine: `encode(frame, quality=60)`, NOT
`encode(draw(frame, dets), ...)`). Draw boxes in the browser with a 0.5s hold:

```js
let latestDets = [];           // [{cls,conf,bbox:[x,y,w,h], seen:performance.now()}]
const HOLD_MS = 500;
// on WS text msg: latestDets = JSON.parse(ev.data).map(d=>({...d, seen:performance.now()}));
// in paint(), after drawImage:
const sx = canvas.width/(latestBitmap.width||canvas.width);
const sy = canvas.height/(latestBitmap.height||canvas.height);
const now = performance.now();
for(const d of latestDets){
  if(now - d.seen > HOLD_MS) continue;                // expire after 500ms
  const [x,y,w,h]=d.bbox;
  ctx.strokeRect(x*sx, y*sy, w*sx, h*sy);
  ctx.fillText(`${d.cls} ${d.conf.toFixed(2)}`, x*sx, Math.max(y*sy-4,10));
}
```

Tuning: raise HOLD_MS if objects leave residue too long; lower if stale boxes linger.

## 3. Hardened streaming-Stop (engine + server)
A stalled IP-cam `read()` blocks forever → zombie thread, Stop does nothing. Fix:
engine takes a `threading.Event` and a read watchdog; Stop sets it + joins.

```python
# engine run(config, stop_event=None):
import threading
if stop_event is None: stop_event = threading.Event()
# capture loop:
def safe_read():
    res=[None]
    def _r():
        try: res[0]=src.read()
        except Exception: res[0]=None
    t=threading.Thread(target=_r, daemon=True); t.start(); t.join(3.0)
    return res[0] if not t.is_alive() else None   # 3s watchdog
def capture_loop():
    while stop["go"] and not stop_event.is_set():
        item = safe_read()
        if item is None:
            if config["source"]["kind"]=="file" and not config["source"].get("loop"):
                stop["go"]=False; return
            continue
        latest_frame["frame"], latest_frame["ts"] = item
# Stop endpoint:
ev = _state.get("stop_event")
if ev is not None: ev.set()
_state["running"] = False
t = _state.get("thread")
if t is not None:
    t.join(timeout=5)        # bounded; daemon thread can't outlive process anyway
```

Verify: inject a source whose `read()` sleeps forever, start, Stop, assert
`thread.is_alive()==False` and a 2nd Start succeeds.

## 4. Browser decode-gate (prevent decode backlog)
Per-message `createImageBitmap` piles up if frames arrive faster than decode.
Gate to a single in-flight call, keep only the newest:

```js
let decoding=false;
function decodeNext(){
  if(!pendingBytes){ decoding=false; return; }
  decoding=true; const bytes=pendingBytes; pendingBytes=null;
  createImageBitmap(new Blob([bytes],{type:'image/jpeg'}))
    .then(b=>{ if(latestBitmap) latestBitmap.close(); latestBitmap=b;
               if(pendingBytes) decodeNext(); else decoding=false; })
    .catch(()=>{ decoding=false; });
}
// WS onmessage binary: pendingBytes = ev.data; if(!decoding) decodeNext();
```

## 5. IP-cam "not connected" (connectivity)
- Phone + Mac MUST be on the SAME subnet. The URI is the phone's CURRENT LAN IP,
  NOT localhost/127.0.0.1 (that's the phone itself).
  - Home WiFi → `192.168.x.x`  (e.g. `http://192.168.0.12:8080/video`)
  - iPhone Personal Hotspot → `172.20.10.x`
- The app PULLS the video FROM the phone's IP-cam app (e.g. "IP Webcam", endpoint
  `/video`). If the phone changes network, the IP changes → update the URI.
- Bind the server to `0.0.0.0` (not just `127.0.0.1`) ONLY if you also want to open
  the control page from the phone browser at the Mac's LAN IP. The Mac→phone pull
  works regardless of bind address.
- Hardcode the S22 URI default in the page; if it goes blank, re-check the phone's
  shown stream URL.

## 6. Cesium / map viewer — removed, not added (yet)
The lightweight Cesium twin viewer was DEAD WEIGHT: Geo=none by default, only a stub
for the unbuilt Mavic map, and a `unpkg` CDN `<script>` that breaks the page offline.
Offline-first = NO external script tags. Re-add a viewer ONLY when the Mavic
geo-adapter lands and boxes need lat/lon on a map — and vendor it locally.
