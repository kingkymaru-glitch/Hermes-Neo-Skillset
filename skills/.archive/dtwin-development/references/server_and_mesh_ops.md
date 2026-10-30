# DTWIN Server & Mesh Operations

## Local server (web twin viewer)
- Canonical launch: from `~/DTwin`, run `server.py` (use the homebrew python3.14
  at `/opt/homebrew/Cellar/python@3.14/.../Python.app/Contents/MacOS/Python`).
  Serves on **:8753**. ROOT = `~/DTwin`, so assets resolve at
  `web/assets/<name>/model.*`.
- The viewer auto-loads `/api/assets[0]`. If a DIFFERENT server instance is up
  (e.g. one rooted at `~/TriniD` on :8790), the asset list differs and a model
  like dji_701 "disappears" even though the file is on disk. ALWAYS confirm
  cwd/ROOT (`lsof -i :8753` + `pwdx <pid>`) before concluding a model is missing.
- The server died silently multiple times with no log. Relaunch WITH logging
  (`> /tmp/dtwin_server.log 2>&1`) or as a launchd service so it stays up.
- Health: `curl -s http://localhost:8753/api/assets` → `{"assets":[...]}`.

## Trim + Mesh
- **Trim is INTERACTIVE ONLY** (webapp marquee box → delete selected points →
  writes `model_trimmed.ply`). It is NOT automatic.
- **Mesh** = Poisson surface reconstruction via Open3D 0.19 in the dedicated
  venv: `tools/mesh-venv/bin/python tools/splat_to_mesh.py <in.ply> <out.glb>
  --max-faces 20000 --max-mb 30 --depth 7 --sample 40000`.
  Also exposed as `POST /api/mesh {name, max_faces, max_mb}`.
- Splat→mesh converts a POINTS glb (primitive mode 0) into a TRIANGLE mesh glb
  (mode 4). PRESERVE the original point-cloud as `model_pcd.glb` before
  overwriting `model.glb` (the pipeline writes mesh into `model.glb`).
- dji_701 example: 178,666-gaussian splat → 9,717-face triangle mesh (236 KB).
