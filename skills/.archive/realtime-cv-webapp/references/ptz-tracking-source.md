# Digital PTZ webcam source (Insta360 Link) + tracking — Luna EDGE

Verified end-to-end on ~/luna-edge (Flask + YOLO). Adds a PTZ-capable UVC webcam as a
selectable source with a working digital tracking mode. No proprietary SDK.

## Detect the device (macOS)
- `system_profiler SPCameraDataType` → Insta360 Link shows as `UVC Camera VendorID_11802
  ProductID_19457`, Unique ID `0x11000002e1a4c01`.
- `ffmpeg -f avfoundation -list_devices true -i ""` → video index [1] = Insta360 Link.
- OpenCV index is usually FaceTime=0, Insta360=1, iPhone=2. VERIFY by actually probing
  `cv2.VideoCapture(idx).isOpened()` + `read()` a frame — don't trust system order blindly.

## PtzSource (detect/sources/base.py)
Keeps a crop window as fractions of the FULL frame `win = [cx, cy, half_w, half_h]` (init [.5,.5,.5,.5]).
`read()`: `cap.read()`, then if a target is pending, lerp the window toward it (`k=0.15`); crop
`frame[y:y2, x:x2]` (clamped), `cv2.resize` to `(out_w, out_h)`.

```python
class PtzSource(Source):
    def __init__(self, uri, track=False, out_w=1280, out_h=720):
        super().__init__(uri)
        self.cap = cv2.VideoCapture(int(uri) if str(uri).isdigit() else uri)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not self.cap.isOpened(): raise RuntimeError(f"Webcam not opened: {uri}")
        self.track = bool(track); self.out_w, self.out_h = out_w, out_h
        self.win = [0.5, 0.5, 0.5, 0.5]; self._target = None

    def set_target(self, cx, cy, frac_w):
        """cx,cy,frac_w are fractions of the CURRENT (crop) frame.
        Map crop-space -> full-frame space via the live window, then store."""
        if not self.track: return
        wcx, wcy, hw, hh = self.win
        fx = (wcx - hw) + cx * (2 * hw)
        fy = (wcy - hh) + cy * (2 * hh)
        fw = max(0.2, min(0.5, float(frac_w) * 2 * max(hw, hh)))
        self._target = (max(fw, min(1-fw, fx)), max(fw, min(1-fw, fy)), fw)

    def read(self):
        ok, frame = self.cap.read()
        if not ok: return None
        H, W = frame.shape[:2]
        if self._target:
            cx, cy, hw = self._target; k = 0.15; w = self.win
            w[2] += (hw - w[2]) * k; w[0] += (cx - w[0]) * k; w[1] += (cy - w[1]) * k
            self._target = None
        cx, cy, hw, hh = self.win
        x = max(0, min(int((cx-hw)*W), W-2)); y = max(0, min(int((cy-hh)*H), H-2))
        x2 = max(x+1, min(int((cx+hw)*W), W));  y2 = max(y+1, min(int((cy+hh)*H), H))
        crop = frame[y:y2, x:x2]
        if crop.size and (crop.shape[1] != self.out_w or crop.shape[0] != self.out_h):
            crop = cv2.resize(crop, (self.out_w, self.out_h), interpolation=cv2.INTER_LINEAR)
        return crop, time.time()
```

## Detector hook (detect/main.py, in infer_loop)
After computing `dets` and scaling boxes back to full-res px:
```python
if dets and hasattr(src, "set_target"):
    d = max(dets, key=lambda x: getattr(x, "conf", 0) or 0)
    x1, y1, x2, y2 = d.bbox
    src.set_target(((x1+x2)/2)/w, ((y1+y2)/2)/h, max((x2-x1)/w, (y2-y1)/h))
```
`w,h` = frame dims (the CROPPED frame when tracking is on) → fractions are crop-space, which
PtzSource correctly maps back.

## build_source registration
```python
kinds = {..., "insta360": PtzSource, ...}
if kind == "insta360": return PtzSource(uri, track=kw.get("track", False))
```

## UI (templates/index.html)
- `<option value="insta360">Insta360 Link (PTZ)</option>` + a Tracking-mode checkbox
  (`<input id="trackBtn" type="checkbox">`) inside a `#trackWrap` shown only for insta360.
- `syncSourceUI()` shows `trackWrap` when `srcSel.value==='insta360'` and sets the URI field to `1`.
- Start payload: `source:{kind, uri, track: srcSel.value==='insta360' ? trackBtn.checked : false}`.

## Verify
- Unit (no camera): `PtzSource.__new__` + a FakeCap returning a synthetic frame; `set_target(0.2,.5,.2)`
  (left-of-crop) → after ~10 `read()` the window `win[0]` must drift < 0.5. Confirms mapping + lerp.
- End-to-end: POST `/api/start` with `source:{kind:'insta360',uri:'1',track:true}` → status
  `running:true`; engine log prints `source=insta360`; POST `/api/stop` clean.
- Ensure the served HTML actually contains the new option/toggle (grep the served page) — a stale
  old server on the port serving pre-edit HTML will silently fail this.

## macOS server launch trap
`python app.py` fails with "command not found: python" when the shell isn't activated — use the
explicit venv interpreter `.venv/bin/python app.py`. Before relaunching after edits, kill stale
instances: `pkill -f "luna-edge/app.py"` and confirm port 8000 is free, else the browser can hit an
old pre-fix server (symptom: 200 OK but new UI elements absent).
