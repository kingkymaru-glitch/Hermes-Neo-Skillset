# Luna-EDGE camera sources & PTZ — session detail (2026-08)

Worked example for wiring a USB PTZ webcam (Insta360 Link) into Luna-EDGE's
source pipeline + auto-detecting cameras. See SKILL.md "Cameras & PTZ" for the
condensed rules; this file is the full recipe + verification.

## Device reality — OpenCV index ≠ name order (CORRECTED this session)
Insta360 Link enumerates as a standard UVC webcam on macOS. `system_profiler
SPCameraDataType` / `ffmpeg -list_devices` report 3 cams: index 0 = FaceTime
(builtin), 1 = Insta360 Link (USB), 2 = iPhone (USB). BUT this does NOT match
OpenCV's indices — the user confirmed that on this Mac OpenCV opens the Insta360
at **index 0** and FaceTime at index 1 (OpenCV had set `CAP_PROP` to 3840x2160 on
index 0). There is no shared key between the name lists and OpenCV indices, so
NEVER pick a camera by name-by-index. The Insta360 is the only 4K (3840x2160)
device; identify it by capability (probe each index with
`cap.set(CAP_PROP_FRAME_WIDTH,3840); cap.set(CAP_PROP_FRAME_HEIGHT,2160)` and
read back; `w>=3000 and h>=2000` ⇒ `ptz=True`). Auto-select `ptz` first.

## Backend — `/api/cameras`
Probe indices 0..7 with `cv2.VideoCapture(idx)`; keep those that `isOpened()`.
OpenCV prints noisy "camera failed to properly initialize!" to stderr for
non-existent indices — suppress it by redirecting `sys.stderr`/`sys.stdout` to
`open(os.devnull,'w')` around the `VideoCapture` call (a thread-local-ish save/restore).
Return `[{index,name,builtin,ptz,works,w,h}]`. Label the 4K device
`name="Insta360 Link"` and `ptz=True`; label everything else generically
`name=f"Camera {idx}"` — do NOT map system_profiler names by position (order
mismatch ⇒ wrong names/selection). `builtin=False` (unused for selection).

## Backend — PtzSource (digital PTZ)
- Crop window in FULL-frame fractions `win=[cx,cy,hw,hh]` (hw/hh = half-widths; init `[0.5,0.5,0.5,0.5]`).
- `set_target(cx,cy,frac_w)` takes crop-frame centroid → full-frame:
  `fx=(wcx-hw)+cx*(2*hw)`, `fy=(wcy-hh)+cy*(2*hh)`, `fw=clamp(frac_w*2*max(hw,hh),0.2,0.5)`,
  clamp coords to `[fw,1-fw]`.
- `read()`: lerp `win` toward stored target at `k=0.15` (glide), clear target, crop
  `frame[y:y2,x:x2]`, resize to `out_w×out_h` (1280×720). Clamp crop bounds safely
  (`x=max(0,min(x,W-2))`, etc.).
- Register in `build_source`: `"insta360": PtzSource`, and
  `if kind=="insta360": return PtzSource(uri, track=kw.get("track", False))`.

## Backend — tracking hook in `detect/main.py` infer loop
After `latest_dets` update, when `dets and hasattr(src,"set_target")`:
```
d = max(dets, key=lambda x: getattr(x,"conf",0) or 0)
x1,y1,x2,y2 = d.bbox
cx = ((x1+x2)/2)/w; cy = ((y1+y2)/2)/h
src.set_target(cx, cy, max((x2-x1)/w,(y2-y1)/h))
```
(w,h = current frame dims; bbox is pixel coords scaled back to full frame).

## Frontend — `templates/index.html`
- `<select id="source">` gets `<option value="insta360">Insta360 Link (PTZ)</option>`.
- `#trackWrap` (with `#trackBtn` checkbox) shown only when insta360 selected, in `syncSourceUI`.
- Start payload adds `track: srcSel.value==='insta360' ? document.getElementById('trackBtn').checked : false`.
- Auto-detect on load: `detectCameras()` → GET `/api/cameras` → fill `<datalist id="camList">`
  (uri input has `list="camList"`) + auto-fill URI with the `ptz` camera
  (`find(c=>c.ptz)`), else first working; when `ptz` chosen set `#source` to `insta360`,
  else `webcam` (only when current source was `ipcam`). Fill ONLY when current URI is
  empty or still the S22 placeholder.
- `syncSourceUI` must NOT hardcode `uri='1'` when `insta360` is selected — that clobbers
  the detected index (this session it overwrote the correct index 0 with '1' = Mac cam).
  Let `detectCameras()` own the URI value.
- "Reset source" button: `fetch('/api/stop')`, restore Source=ipcam + default URI,
  untick `#trackBtn`, `syncSourceUI()`, re-run `detectCameras()`.

## Verification (ad-hoc, temp script under /tmp — NOT /private/var/.../T)
- `build_source("insta360","1",track=True)` returns a `PtzSource`; `read()` returns 1280x720.
- Unit: fake `PtzSource` (stub cap with a synthetic 720x1280 frame), `set_target(0.2,0.5,0.2)`
  → after ~10 `read()`s `win[0] < 0.5` (window drifted left); recenter test restores ~0.5.
- Flask test client: `app.test_client().get("/api/cameras")` → 200, cameras list, and the
  PTZ camera is the 4K one: assert `cameras[0]["ptz"] is True and "Insta360" in cameras[0]["name"]`
  and its `w >= 3000` (on this Mac it's index 0, but assert by capability not index).
- Served UI: `curl -s :8000/ | grep "Insta360 Link (PTZ)"`, `trackBtn`, `c=>c.ptz`, `!== -1`, `id="reset"`.
- Browser auto-fill: after a fresh load, `#uri.value === "0"` and `#source.value === "insta360"`
  (the detected Insta360), NOT `1`.

## Two traps hit
1. Auto-fill condition: placeholder is `http://192.168.0.12:8080/video`, so test `value.indexOf('192.168') !== -1`, NOT `===0` (which is never true → fill never runs).
2. `python` vs venv: use `.venv/bin/python` (bare `python` → `command not found`).
3. Template cache: restart server after any `index.html` edit or Flask serves the stale first-render.
4. **`syncSourceUI` hardcoding `uri='1'` for insta360 clobbers the detected index.** Auto-detect picks
   the right 4K index (0), then `syncSourceUI` overwrites it to '1'. Remove the hardcode; let detection
   own the URI.
5. **Trust `ptz`/capability, never the name index.** system_profiler/ffmpeg names do not map to OpenCV
   indices (this Mac: Insta360 = OpenCV index 0, not 1).
