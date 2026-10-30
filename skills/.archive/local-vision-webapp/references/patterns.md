# Code patterns for local-vision-webapp

## 1. Four-layer skeleton (source-agnostic)
```python
# Source: any frame producer. Live vs file = just subclasses.
class Source(ABC):
    def read(self) -> tuple[np.ndarray, float]: ...   # (frame, timestamp)

# Detector: source-blind. skill = weights file (coco/ppe/crack).
class YoloDetector:
    def __init__(self, skill): self.model = YOLO(f"{skill}.pt")
    def infer(self, frame): -> list[Detection]

# GeoAdapter: optional, per source. Kept OUT of detector.
# Sink: stdout / sqlite / ws / supabase(post-mission).
```

## 2. Decoupled capture + infer (smooth video, capped detection)
```python
latest_frame = {"frame": None, "ts": 0.0}
latest_dets = {"dets": [], "ts": 0.0}

def capture_loop():
    while running:
        latest_frame["frame"], latest_frame["ts"] = src.read()

def infer_loop():
    last = 0.0
    while running:
        f = latest_frame["frame"]
        if f is None: time.sleep(0.01); continue
        if det_interval and (time.time()-last) < det_interval:
            time.sleep(0.005); continue
        last = time.time()
        small = cv2.resize(f, (640, int(h*640/w)))   # proc_w=640
        ds = det.infer(small)
        # scale boxes back to full-res, push to frame_q as JPEG
        jpg = encode(draw(f, ds), quality=60)
        frame_q.put_nowait(jpg)   # MUST exist or no video (pitfall 5)
        det_q.put_nowait([{cls,conf,bbox}... for d in ds])
```

## 3. flask_sock WebSocket handler (drain-to-newest, NO receive())
```python
@sock.route("/ws")
def ws(ws_conn):
    while True:
        try:
            jpg = None
            while True:
                jpg = frame_q.get_nowait()   # drain to newest -> low latency
        except queue.Empty:
            if jpg is not None:
                ws_conn.send(jpg)             # binary frame
        try:
            while True:
                d = det_q.get_nowait()
                ws_conn.send(json.dumps(d))   # text detections
        except queue.Empty:
            pass
        time.sleep(0.02)
        # NEVER call ws_conn.receive() here (pitfall 1: blocks, kills stream)
```

## 4. Latency: buffersize=1 on every capture
```python
cap = cv2.VideoCapture(uri)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)   # prevents ~1-1.5s backlog (pitfall 3)
```

## 5. S22 / phone IP-cam as source
- App (e.g. "IP Webcam" on Android) serves MJPEG at `http://<phone-ip>:8080/video`.
- Phone and Mac must share the SAME wifi (iPhone Personal Hotspot = 172.20.10.x subnet works).
- The phone app itself may add ~1s encode latency — if lag persists after pitfalls 1/3/4 are
  fixed, the lag is the phone app, not the pipeline.
- Verify the endpoint: `curl -sS -o /dev/null -w "%{http_code}" http://<ip>:8080/video` → 200.
