# Real-time local vision webapp (Flask + flask_sock + YOLO)

Reusable pattern for streaming live frames + detections from a Python engine to a
localhost browser, fully offline (field-demo safe once libs are vendored).

## Architecture (decoupled — connect order doesn't matter)
```
engine thread ──▶ frame_q (Queue, jpeg bytes) ──┐
engine thread ──▶ det_q   (Queue, list[dict])  ──┼─▶ @sock.route("/ws") drains both
                                               │     → ws.send(bytes) for frame
browser ◀── ws ───────────────────────────────┘     → ws.send(json)  for detections
```
Engine never holds the socket. Flask app owns global frame_q / det_q; the WS
handler loops get_nowait() on both and sends. Browser: binaryType='arrayblob',
onmessage: string -> detections, else -> URL.createObjectURL(Blob) into <img>.

## Minimal engine emit (inside the capture loop)
```python
from detect.viewer import draw, encode   # draw() boxes, encode() -> jpeg bytes
if frame_q is not None:
    jpg = encode(draw(frame, dets))
    if frame_q.full(): frame_q.get_nowait()
    frame_q.put_nowait(jpg)
if det_q is not None and dets:
    det_q.put_nowait([{"cls":d.cls,"conf":round(d.conf,3),
                        "bbox":[round(v,1) for v in d.bbox],
                        "lat":getattr(d,"lat",None),"lon":getattr(d,"lon",None)}
                       for d in dets])
```

## Minimal Flask WS handler
```python
@sock.route("/ws")
def ws(ws_conn):
    while True:
        try: ws_conn.send(frame_q.get_nowait())          # binary jpeg
        except queue.Empty: pass
        try:
            while True: ws_conn.send(json.dumps(det_q.get_nowait()))  # text
        except queue.Empty: pass
        try: ws_conn.receive()                            # detect disconnect
        except Exception: break
```

## Pitfalls (seen this session)
- Coupling engine run(socket=_state["socket"]) at start time -> blank GUI if
  browser connects after Start. Use queues (above).
- "Source map failed to load" devtools warning = HARMLESS (Cesium CDN debug map).
  Not the blank-video cause. Do not chase it.
- flask_sock socket.send() accepts both str (JSON) and bytes (jpeg) -- use
  that to multiplex frame + detections on one socket.
- cv2.VideoCapture(idx) on macOS needs CAP_AVFOUNDATION for some cams; index 0
  is the default built-in cam. IP-cam/phone stream = cv2.VideoCapture("http://ip:port/video").

## Verified probe recipe (no browser needed)
```python
import asyncio, websockets
async def go():
    async with websockets.connect("ws://127.0.0.1:8000/ws") as ws:
        for _ in range(25):
            m = await asyncio.wait_for(ws.recv(), timeout=6)
            if isinstance(m, bytes):
                print("binary frame", len(m), "jpeg=", m[:2]==b'\xff\xd8'); return
asyncio.run(go())
```
A valid run prints `binary frame <N> jpeg= True`. (Install websockets in venv.)

## S22 / phone as IP webcam (field demo)
- App "IP Webcam" -> Start server -> MJPEG at http://<phone-ip>:8080/video.
  Probe curl -o /dev/null -w "%{http_code}" http://<ip>:8080/video (200 = good;
  /videofeed also works, /mjpegfeed -> 404 on this app).
- Phone + Mac MUST share one wifi. iPhone Personal Hotspot -> 172.20.10.x subnet.
- No internet required; pure LAN. Pass URL as ipcam source.

## Offline caveat
Cesium map in the viewer loads JS from unpkg.com -> FAILS with wifi off. For the
dam demo, vendor Cesium locally (download once into the app, serve from static).
The vision stream itself is LAN-only and fine.
