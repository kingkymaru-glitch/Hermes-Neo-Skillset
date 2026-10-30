# Flask + WebSocket + YOLO pattern (condensed, known-good)

## Correct WS handler (Flask-Sock) — DO NOT call receive() in loop
```python
@sock.route("/ws")
def ws(ws_conn):
    import time
    while True:
        try:
            jpg = frame_q.get_nowait()      # bytes JPEG from engine
            ws_conn.send(jpg)                # binary frame
        except queue.Empty:
            pass
        try:
            while True:
                d = det_q.get_nowait()       # list of dicts
                ws_conn.send(json.dumps(d))  # text detections
        except queue.Empty:
            pass
        time.sleep(0.02)   # ~50Hz pump, non-blocking
    # disconnect detected via send() exception -> loop exits
```
WRONG (kills stream after 1 frame): calling `ws_conn.receive()` every loop to
"detect disconnect" — it blocks until the browser sends, which never happens.

## Engine: decoupled capture + inference threads
- `capture_loop()`: `latest_frame = {"frame": f, "ts": t}` (full rate).
- `infer_loop()`: throttle with `det_fps` (e.g. 8). Downscale to `proc_w` (640),
  `det.infer(small)`, scale boxes back `bbox = [v * w/proc_w for v in bbox]`.
  **CRITICAL: push the annotated JPEG to `frame_q` HERE (in infer_loop).** A
  decoupled rewrite that drops `frame_q.put(jpg)` produces "detections arrive
  but NO video" — only the det_q flows. Verified maru hit exactly this.
- Main pump: draw latest frame + latest dets, encode q60.

## Browser — USE <canvas> + requestAnimationFrame (NOT <img> src-per-message)
Setting `feed.src = URL.createObjectURL(...)` on EVERY WS message (~50/s) repaints
slower than messages arrive -> onmessage callbacks queue up -> DISPLAYED frame falls
further behind over time (e.g. ~1.5s constant + grows past 15s). Symptom maru hit.
Fix: store newest bytes, decode off the critical path, paint ONCE per display refresh,
DROP stale frames. This decouples network receipt from paint.

```html
<canvas id="feed"></canvas>
<script>
const canvas=document.getElementById('feed'); const ctx=canvas.getContext('2d');
let latest=null, pending=null;
function fit(){ const w=canvas.clientWidth,h=canvas.clientHeight;
  if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;} }
function paint(){ fit(); if(latest) ctx.drawImage(latest,0,0,canvas.width,canvas.height);
  requestAnimationFrame(paint); }
requestAnimationFrame(paint);
const ws=new WebSocket('ws://'+location.host+'/ws'); ws.binaryType='arraybuffer';
ws.onmessage=(ev)=>{
  if(typeof ev.data==='string'){ /* detections JSON */ }
  else { pending=ev.data; createImageBitmap(new Blob([pending],{type:'image/jpeg'}))
           .then(b=>{ if(latest) latest.close(); latest=b; }).catch(()=>{}); }
};
</script>
```
The rAF loop paints continuously; the WS handler only updates `pending`/`latest`.
This MUST be the default viewer — never the per-message img.src path.

## OpenCV capture: set CAP_PROP_BUFFERSIZE=1 on every source
OpenCV internally buffers decoded frames; without this the source hands you STALE
frames (adds hidden latency on top of the model). Set on webcam/ipcam/mavic in __init__:
```python
self.cap = cv2.VideoCapture(uri); self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
```

## Config keys (detect/config.yaml)
```yaml
source: {kind: ipcam, uri: "http://172.20.10.3:8080/video"}
skill: coco
conf: 0.35
proc_w: 640      # infer width; boxes scaled back
det_fps: 8       # YOLO rate; video streams at capture rate
geo: {kind: none}
sinks: [stdout]
show: false
```

## IP-cam endpoint probe (Android "IP Webcam")
GET http://<phone-ip>:8080/video -> 200 (MJPEG). Other apps differ.
Confirm same wifi/LAN; no internet needed.

## Verification probe
```python
import asyncio, websockets, time
async def go():
    n=0; t0=time.time()
    async with websockets.connect("ws://127.0.0.1:8000/ws") as ws:
        while time.time()-t0 < 3:
            await asyncio.wait_for(ws.recv(), timeout=4); n+=1
    print(n, "frames/3s")   # continuous => ~capture-rate; single => handler died
asyncio.run(go())
```
