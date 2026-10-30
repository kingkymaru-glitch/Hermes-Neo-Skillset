# edge-ai-vision pitfalls (detailed fixes)

## 1. Circular import on Detection dataclass
The `Detection` dataclass lives in `detect/detector/base.py`.
`detect/geo/base.py` and `detect/sinks/base.py` import it. They MUST use:
    from ..detector.base import Detection
NOT `from .base import Detection` (that resolves to the geo/sinks own base.py
which doesn't define Detection → ImportError on partially-initialized module).
Symptom: `ImportError: cannot import name 'Detection' from partially initialized module`.

## 2. YOLO weights file naming
ultralytics auto-downloads `yolov8n.pt` when you pass `"yolov8n.pt"`. It does NOT
know `"coco.pt"`. Fix: map skill "coco" -> "yolov8n" and check `skills/<name>.pt`
exists first; else fall back to the alias name. Custom skills (ppe/crack) are
real files you place in `skills/`.

## 3. OpenCV camera on macOS
`cv2.VideoCapture(0)` can fail to open on macOS (especially with the default
backend). Test both `cv2.CAP_ANY` and `cv2.CAP_AVFOUNDATION`; verify the device
index actually opens and `read()` returns a frame. Built-in webcam is usually
index 0 but front/back or external cams shift it.

## 4. IP-cam / phone stream endpoint
Android "IP Webcam" app serves MJPEG at `http://<ip>:8080/video` (200) and
`/videofeed` (200) but `/mjpegfeed` and `/stream` are 404. Probe with curl
before wiring. Use the URL exactly as shown in the app's start screen.
Plain HTTP on a LAN (e.g. iPhone hotspot 172.20.10.x) is fine and offline.

## 5. flask_sock dual-type WebSocket
`socket.send()` accepts both `str` (detection JSON) and `bytes` (JPEG frame).
Use this to push annotated frames (bytes) AND detections (text) on one socket.
Browser: set `ws.binaryType='arraybuffer'`; branch on `typeof data === 'string'`
(detections) vs else (Blob image). Do NOT try to JSON-encode the JPEG.

## 6. Cesium offline
The viewer HTML loads Cesium JS from unpkg CDN. For true field (no internet)
use, download Cesium once and serve it locally (vendor into static/). Until then
the map won't render offline — the video + detection log still work.

## 7. Vision tool 404 outage
The `vision_analyze` / browser_vision tools can 404 (auxiliary backend outage).
Workaround: save the camera frame with cv2.imwrite, then run YOLO on it and read
the class/conf text output instead of visually inspecting. Screenshots still save.
