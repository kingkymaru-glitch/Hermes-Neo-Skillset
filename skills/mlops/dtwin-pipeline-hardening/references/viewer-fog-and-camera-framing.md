# Viewer: Fog + Camera Auto-Framing (the "still nothing" bug)

## Symptom
User reports "still nothing" / blank 3D canvas for a *newly published* splat,
even though:
- The `.ply` exists, is listed by `/api/assets`, and fetches HTTP 200.
- Status pill shows "viewing <name>" (the synchronous click status) but never
  advances to "loaded · model.ply" — or, if it does advance, the canvas is
  still empty.
- The placeholder pillar (blue cylinder) may still be visible.

## Root cause chain (three fixes, one session)

### 3. SharedArrayBuffer requires cross-origin isolation (the FINAL root cause)
After fixing camera framing and fog, the splat STILL didn't render. The real
blocker surfaced in the headless-Chrome console:

```
DataCloneError: Failed to execute 'postMessage' on 'DedicatedWorkerGlobalScope':
SharedArrayBuffer transfer requires self.crossOriginIsolated.
```

gaussian-splats-3d defaults `sharedMemoryForWorkers: true`, so its sort worker
uses a `SharedArrayBuffer`. Browsers only allow that on cross-origin-isolated
pages, which needs two headers the stdlib server wasn't sending:

```
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
```

Fix in `server.py` `end_headers()` (send both headers) PLUS
`sharedMemoryForWorkers: false` in the Viewer constructor as a fallback. This
bug hit EVERY `.ply` — it presented as a data/camera problem but was a
serving-header problem. See SKILL.md "Cross-Origin Isolation" section for the
headless diagnosis recipe.

### 1. Camera was hardcoded to the sample's coordinate space
`main.js` had a fixed `camera.position.set(2.2,1.8,3.2)` + `controls.target(0,0.8,0)`,
tuned for the `sample` splat. Every COLMAP reconstruction lives in its own
origin + scale, so `dji_test` (center ~[0.33,3.03,4.21], extent ~17 units)
loaded but rendered off-screen / microscopic.

Fix: `frameCameraToSplat(viewer)` after `addSplatScene` — compute
`mesh.computeBoundingBox(true, 0)`, position camera at `center + dist*(0.6,0.4,1)`
with `dist = radius*2.2`, and set `camera.near = radius/100`, `camera.far = radius*50`.

### 2. `scene.fog` made the splat invisible after auto-framing
The scene declared `scene.fog = new THREE.Fog(0x0b0e13, 6, 22)` — far plane 22
units AND fog color `0x0b0e13` == renderer clear color. Once `frameCameraToSplat`
moved the camera ~18–26 units out to frame the ~17-unit `dji_test` capture, the
entire splat sat at/beyond the fog far plane → 100% fogged to the background →
invisible. The `sample` only "worked" before because its fixed camera sat ~7
units away (inside fog range).

Fix: **remove `scene.fog` entirely.** Gaussian splats don't need distance fog —
it was a leftover from the placeholder-pillar scene.

## Diagnostic that pinpointed it
Parse the binary PLY header + data to get the real extent (don't guess):

```python
import struct
with open(path,'rb') as f:
    hdr=b''
    while True:
        l=f.readline(); hdr+=l
        if l.strip()==b'end_header': break
    n=int([x for x in hdr.split(b'\n') if x.startswith(b'element vertex')][0].split()[-1])
    stride = 17*4   # x,y,z,nx,ny,nz,f_dc_0..2,opacity,scale_0..2,rot_0..3
    mn=[1e9]*3; mx=[-1e9]*3
    for _ in range(n):
        x,y,z=struct.unpack_from('<fff', f.read(stride), 0)
        for i,v in enumerate((x,y,z)):
            mn[i]=min(mn[i],v); mx[i]=max(mx[i],v)
    extent=[mx[i]-mn[i] for i in range(3)]
    print('center',[(mn[i]+mx[i])/2 for i in range(3)], 'extent',extent)
```

If `max(extent) >= ~10 units`, a 22-unit fog far plane will hide it after framing.

## Order of fixes this session (all on branch `neo`)
- `9ce9cba` — frameCameraToSplat() auto-fit
- `e25b7ff` — remove scene.fog
- (SharedArrayBuffer/COOP-COEP fix) — add COOP+COEP headers in server.py
  end_headers() and sharedMemoryForWorkers:false in the Viewer constructor
Earlier related viewer fixes: bare-specifier `./vendor/...` (b618cf3), no-cache
headers (d52e7f0), window.* exports (6740151/8cee4f4).
