# DTwin Trim → Mesh → optimized .glb flow (added 2026-08-16)

The skill's "PLY → GLB" section only covers the POINT-CLOUD glb (`ply_to_glb.py`).
DTwin now also produces a CLEANED + MESHED .glb via an interactive trim step, then
Poisson surface reconstruction, then decimation. This is the "final web artifact is a
mesh .glb" path MARU asked for (lightweight, <20k faces, <30MB, opens in Three.js/Unity/iOS AR).

## Why trim before mesh
A raw Gaussian-splat .ply includes unwanted cloud (rig, ground, outliers). Meshing it
directly bakes that junk into the surface. The user marquees unwanted points in the
browser and deletes them first; the MESH consumes the cleaned file, not the raw splat.

## Toolchain
- `tools/mesh-venv/bin/python` — dedicated venv, **Python 3.11 + Open3D 0.19**.
  Create: `python3.11 -m venv tools/mesh-venv && tools/mesh-venv/bin/pip install open3d`
  (Open3D 0.19 is the last wheel with full Poisson; 0.18 segfaults on Apple Silicon
  KD-tree — see `open3d-apple-silicon.md`). Also `plyfile` (robust Gaussian .ply reader).
- `tools/trim_splat.py` — reads splat centers via plyfile, deletes selected indices,
  writes `model_trimmed.ply`. (Hand-rolled binary reader misaligned → 5e13 coords;
  plyfile fixed it. See PITFALL below.)
- `tools/splat_to_mesh.py` — Poisson reconstruction (depth 7) → decimate to <max-faces
  (20000) → export optimized .glb (<max-mb 30). Alpha-shape fallback if Poisson fails
  to close. Writes a CORRECT glTF 2.0 binary (see GLB layout pitfall).

## Server endpoints (server.py)
- `GET /api/points?name=<id>` — returns the cloud (downsampled) for the trim UI.
- `POST /api/trim` `{name, indices:[...]}` — removes selected points → `model_trimmed.ply`.
- `POST /api/mesh` `{name}` → SSE `GET /api/mesh` — Poisson mesh → `model.glb`
  (uses `--depth 7 --sample 30000`; depth 9 "Failed to close loop" is non-fatal).
- Mesh step uses `trimmed` file if present, else raw splat.

## Web UI (index.html + main.js)
New "04 · Trim & Mesh" panel: Deploy ID → Load points → drag marquee over cloud →
Delete selected (repeat) → Mesh → lightweight .glb (streams progress). Assets row's
View/Download/Open-folder target the mesh glb after meshing.

## PITFALL — Poisson depth 9 fails on noisy splats
`--depth 9` (Open3D default) throws "Failed to close loop" on noisy Gaussian clouds and
produces NO mesh. Use `--depth 7 --sample 30000` → ~20k faces, <1MB (dji_test: 20,000
faces, 10,093 verts, 0.48MB). Non-fatal warning; mesh still valid at depth 7.

## PITFALL — GLB writer needs mandatory chunk-type words
A hand-written GLB MUST include the 4-byte chunk-type words `JSON` and `BIN\0` between
the chunk-length and the chunk data, or three.js/Unity reject it (glTF spec). Also:
- Header after magic `glTF` is `<II` (version + total length) — NOT `<III`.
- JSON chunk padded to 4-byte alignment with SPACES (whitespace is valid JSON padding).
- `buffers[0].byteLength` must equal the real BIN length (the writer must set it, not leave 0).
Validate with a stdlib Node/Python parser: assert `magic==glTF`, `version==2`,
`total==fileLen`, json chunk type "JSON", bin chunk type "BIN\0", mode 4 (POINTS) or
4 (TRIANGLES) per primitive, faces = indexCount/3. (dji_test mesh glb verified VALID ✔.)

## PITFALL — plyfile, not hand-rolled binary, for Gaussian .ply
Gaussian .ply has packed float props (opacity, scale_0..2, rot_0..3, f_dc_0..2). A
hand-rolled struct reader misaligns (returned x=5e13). Use `plyfile.PlyData.read(in)`
and index `pc['x'].data` etc. — robust and short.

## 4K source pitfall (extraction stall)
A 4K (3840×2160) source HANGS extraction: ffmpeg ~0% CPU, 0 frames after 3+ min
(dji_701 run, 2026-08-16). Cause: no downscale + old `ffprobe -count_frames`-based cap
returned empty → no fps cap → ffmpeg decoded the whole clip. Fix: deterministic fps cap
+ auto-downscale in one `-vf` chain (see PITFALL "4K source video stalls extraction" in
SKILL.md). Verified: 300 frames @1920×1080 from a 150s/4K clip in ~46s. MARU: "we should
have not start the pipeline with 4k video."

## Close-monitor + record-errors pattern
When MARU says "wait and monitor closely, record for all errors", use a sidecar monitor
script (terminal background=true) that, while `pgrep -f pipeline.sh` is alive, tails the
log every 15s and records: (a) every `>>` stage marker as a STAGE transition, (b) every
new line matching `error|fail|exception|traceback|killed|segfault|abort|diverg|NaN|warn`.
Write to `/tmp/pipeline_<id>_record.log`. IMPORTANT: background-process "exited (exit
code None)" alerts are PHANTOM for long runs — the real status is `pgrep -f pipeline.sh`
+ `tail` on the log (the live run keeps advancing timestamps). Trust the process/list,
not the notification. A reusable monitor lives at `scripts/monitor_pipeline.sh`.

## WORKED — mesh a published splat headless (dji_701, 2026-08-16)
Trim is **interactive only** — the webapp marquee deletes points → `POST /api/trim`
writes `model_trimmed.ply`. There is NO automatic trim. The MESH step IS runnable
from CLI without the browser. Verified recipe:
```bash
cd ~/DTwin
cp web/assets/dji_701/model.glb web/assets/dji_701/model_pcd.glb   # preserve the point cloud
tools/mesh-venv/bin/python tools/splat_to_mesh.py \
    web/assets/dji_701/model.ply web/assets/dji_701/model.glb \
    --max-faces 20000 --max-mb 30 --depth 7 --sample 40000
```
Outcome: 178,666-gaussian splat → **9,717-face triangle mesh**, 236KB `model.glb`
(primitive mode 4 = TRIANGLES), original POINTS cloud kept as `model_pcd.glb` (2.6MB).
`/api/mesh` server endpoint does the same but OVERWRITES `model.glb` — so always copy
the point cloud to `model_pcd.glb` first if you want both artifacts. Verify:
`curl -sI localhost:8753/web/assets/dji_701/model.glb` → 200.
Note: the PITFALL above says the mesh writer passes `--depth 7 --sample 30000`; this
session used `--sample 40000` and still produced a valid mesh. Both sample depths are
fine; the binding constraint is `--depth 7` (depth 9 fails to close on noisy clouds).
