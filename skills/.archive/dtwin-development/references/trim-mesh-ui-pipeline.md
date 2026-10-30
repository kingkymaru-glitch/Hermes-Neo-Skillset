# DTwin Trim + Mesh + Viewer-UI pipeline (Neo, 2026-08-16)

Reference for the on-demand trim/mesh + asset-browser UI on branch `neo`.
Companion to the SKILL.md "Trim + Mesh" section (which it supersedes for the
post-2026-08-16 behavior).

## Asset folder contract (per model, `web/assets/<name>/`)
- `model.ply` — original Gaussian splat (fidelity source-of-truth).
- `model_trimmed.ply` — written by `/api/trim` after box-deletes.
- `model.glb` — triangle mesh (glTF 2.0, primitive mode 4 TRIANGLES,
  `KHR_materials_unlit`), written by `/api/mesh` / `splat_to_mesh.py`.
- `model_points.ply` — sampled + normal-estimated cloud (mesh stage input).
- `model_raw.ply` — **raw Poisson surface, pre-decimation** (inspect in Blender/MeshLab).
- `model_mesh.ply` — final decimated, vertex-colored mesh.
- `model_mesh_manifest.json` — `{method, depth, sample, max_faces, n_raw,
  n_faces, artifacts:[...]}`.

## Backend endpoints (server.py, stdlib, :8753)
- `GET /api/assets` → `{"assets":[{name,has_trimmed}]}`. Front-end MUST
  normalize each item to `.name` (do NOT pass the object as a path segment).
- `GET /api/points?name=X` → samples the CURRENT cloud (`model_trimmed.ply` if
  present else `model.ply`), returns `{count,total,points,alpha,src_idx}`.
  `src_idx[i]` maps sampled point i to its real index in the splat.
- `POST /api/trim {"name","indices":[...]}` → keeps splat points NOT in
  `indices`, writes `model_trimmed.ply`. Operates on the current cloud so
  successive deletes accumulate. `indices` are REAL splat indices (use `src_idx`).
- `POST /api/mesh {"name","source":"original|trimmed"}` → Poisson (`depth=7`,
  `sample=40000`) → quadric decimate (≤`max_faces`, default 20000) → glb.
  `source=trimmed` requires `model_trimmed.ply` (else 400). Persists
  points/raw/mesh + manifest. SSE on `GET /api/mesh/log`.
- `GET /api/open-folder?name=X` → `subprocess.run(["open", assets_dir])`
  (macOS Finder). Rejects names containing `/` or `\`.
- `DELETE /api/assets/<name>` → `rm -rf web/assets/<name>`.

## Front-end (web/main.js + web/index.html)
- Marquee select: bind `canvas.addEventListener('mousedown', startMarquee)` on
  `#view`; suspend OrbitControls during drag, restore on mouseup.
- `loadPoints` stores `serverIdx = j.src_idx`; `deleteSelected` sends the
  real splat indices `sel.map(i=>serverIdx[i])`.
- Export radio `name="meshSrc"` (original|trimmed); disabled-"Trimmed" until
  `has_trimmed`. `finishBtn` reads the checked value → `source`.
- Asset row actions: ◉ View (`loadGlb`/`loadSplat`), 📂 Folder (`/api/open-folder`),
  ✕ Delete (confirm → DELETE).

## Gotchas (cost real time this session)
1. Box-select dead if bound to the sidebar panel — canvas is not its child.
2. `assets/[object Object]/model.ply` = `/api/assets` object passed as a string.
3. Trim delete no-op = missing `src_idx` + reloading the ORIGINAL cloud.
4. Poisson mesh was built in memory and discarded — now `model_raw.ply` is saved
   so reconstruction quality is inspectable.

## CLI mesh (verified dji_701 / CMPK1)
```bash
tools/mesh-venv/bin/python tools/splat_to_mesh.py \
  web/assets/<name>/model.ply web/assets/<name>/model.glb \
  --max-faces 20000 --max-mb 30 --depth 7 --sample 40000
# mesh-venv: python3.11 + open3d 0.19 (0.18 segfaults on Apple Silicon)
```
