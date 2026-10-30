# luna-edge pattern — condensed reference

## Four-layer layout (verified in github.com/kingkymaru-glitch/luna-edge)
```
detect/
  sources/base.py   # Source ABC; WebcamSource/IPcam/Mavic/File yield (frame,ts)
  detector/base.py  # Detector ABC; YoloDetector(skill) -> Detection[]
  geo/base.py       # GeoAdapter; NoneGeo/MavicTelemetry/FixedCam/FileReplay
  sinks/base.py     # Sink; Stdout/LocalWS/SQLite/Supabase
  main.py           # wires layers from config, runs loop
  config.yaml      # source/skill/geo/sinks/show
app.py             # Flask + flask_sock localhost webapp (:8000)
templates/index.html # control panel + lightweight Cesium viewer (offline)
```

## Detection dataclass (detect/detector/base.py)
```
@dataclass
class Detection:
    ts, cls, conf, bbox[x,y,w,h]
    lat=None, lon=None, elev=None, heading=None
```

## Model resolution (YoloDetector.__init__)
- local `skills/<skill>.pt` exists -> use it
- else alias `coco` -> `yolov8n.pt` (ultralytics auto-downloads)
- else -> fail clearly
- import fix: geo/base.py and sinks/base.py import Detection via `..detector.base`, NOT `.base`

## Smoke test (no camera needed)
Use a FakeSource yielding np.zeros frames; assert pipeline runs 3+ frames
through source->YOLO->geo->sink. Proves wiring without hardware.
Real camera/live detection unverified without a device on-site.

## Offline rules
- venv: `pip install opencv-python ultralytics flask flask-sock PyYAML`
- Run engine: `python detect/main.py --config detect/config.yaml`
- Run webapp: `python app.py` -> http://localhost:8000 (control + Cesium)
- Push to GH with: `git -c user.name=maru -c user.email=kingkymaru@gmail.com commit ...`
- Cloud sync only AFTER mission (SupabaseSink). Field = local WebSocket + SQLite.

## Known limits
- Mavic Air 2 = CLOSED firmware: YOLO on Mac from controller wifi/HDMI, not on Orin.
- No internet at deep-jungle dam: full local; LUNAV sync post-return.
