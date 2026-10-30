# Local 3DGS training on Apple Silicon (MLX/Metal) — verified recipe

When the user clears the MLX gate ("process to get the ply locally", or any
explicit local-training request), this recipe produced a valid Gaussian-splat
.ply on this Mac (M-series, macOS 26) — 70,499 gaussians from an 83-frame
DJI clip, ~45 min @ 2000 iters.

## Trainer
`ghif/splat-apple` — MLX backend (Metal, unified memory). NOT a pip package;
clone it (vendored under `tools/splat-apple`, gitignored in DTwin so it stays
out of repo history; only `tools/train_local.sh` + the dataset layout are tracked).

```bash
git clone --depth 1 https://github.com/ghif/splat-apple.git tools/splat-apple
cd tools/splat-apple
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt      # torch 2.10, mlx 0.30, mlx-metal, plyfile, viser
# TWO C++ extensions must be built or import fails:
python setup.py build_ext --inplace          # torch_gs._C + torch_gs._MPS (Metal)
python setup_mlx.py build_ext --inplace      # mlx cpp rasterizer
```

## Data layout (the contract `train_mlx.py --data_dir` expects)
```
<data_dir>/
  sparse/0/{cameras.bin, images.bin, points3D.bin}   # COLMAP sparse model
  images_8/                                          # frames, names MUST match COLMAP
```
- Build from a video: ffmpeg @2fps → frames → COLMAP SfM (auto, 83/83 registered
  here). Copy `sfm/sparse/0/*` → `<data_dir>/sparse/0/`, copy frames →
  `<data_dir>/images_8/`. The loader maps images by filename to COLMAP records,
  so frame names on disk must equal the names COLMAP stored.
- `--img_folder images_8` selects the frame subdir (default `images_8`;
  `images`/`images_4` also accepted).

## Run
```bash
cd tools/splat-apple && . .venv/bin/activate
export PYTHONPATH="$PWD:$PYTHONPATH"
python train_mlx.py --data_dir /Users/kamarulhk/DTwin/train/sample \
  --img_folder images_8 --num_iterations 2000 --rasterizer cpp
```
Output: `results/sample_mlx_cpp_<ts>/ply/sample_final.ply` (binary_little_endian,
`element vertex N`, props x/y/z, f_dc_0..2, opacity, scale_0..2, rot_0..3).
This schema is exactly what the three.js `gaussian-splats-3d` viewer consumes.

## Gotchas (cost real time — avoid re-hitting)
- **Import fails with `ModuleNotFoundError: torch_gs._C`** if you skip
  `setup.py build_ext`. The MLX entrypoint imports `torch_gs` at load, which
  needs the compiled `_C`/`_MPS` extensions. Build BOTH setup scripts.
- clang warns about deprecated `fastMathEnabled` in the .mm — harmless.
- Background the run (`terminal(background=true, notify_on_complete=true)`);
  ping on completion, then copy the .ply into `web/assets/<deploy>/model.ply`
  and set `MODEL_URL` in `web/main.js`.

## Wiring into the web viewer
Copy .ply → `web/assets/sample/model.ply`; set `MODEL_URL='assets/sample/model.ply'`
in main.js. Viewer: vendored `web/vendor/gaussian-splats-3d.module.js`
(`@mkkellogg/gaussian-splats-3d@0.4.7/build/gaussian-splats-3d.module.js`).
Load via `import(vendorPath)` then `new Viewer({renderer,camera,scene});
viewer.addSplatScene(MODEL_URL,{showLoadingUI:false})`. Wrap in try/catch that
only warns (so a splat failure falls back to the placeholder pillar, never blanks).
