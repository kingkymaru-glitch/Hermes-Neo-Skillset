# splat-apple setup (MLX Gaussian Splatting, Apple Silicon)

Repo: https://github.com/ghif/splat-apple (clone --depth 1)
Backend: MLX + Metal (unified memory). Fast on M1/M2/M3/M4.

## Install (one time)
```bash
cd tools/splat-apple
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt        # torch 2.10, mlx 0.30, plyfile, viser...
python setup_mlx.py build_ext --inplace   # Metal rasterizer (_rasterizer_metal)
python setup.py     build_ext --inplace   # TORCH_gs._C + _MPS  <-- EASY TO MISS
```
## CRITICAL GOTCHA (2026-08-14, cost one failed run)
The MLX trainer (`train_mlx.py` → `mlx_gs.io.colmap`) imports `torch_gs` at
load time, which needs the C++ ext `torch_gs._C`. If you only built
`setup_mlx.py`, it dies with:
  ModuleNotFoundError: No module named 'torch_gs._C'
**Fix: build BOTH setup_mlx.py AND setup.py.** Order doesn't matter, both
`build_ext --inplace`. Deprecation warning on `fastMathEnabled` is harmless.

## Dataset layout the trainer expects
```
<data_dir>/
  sparse/0/{cameras.bin, images.bin, points3D.bin}   # COLMAP binary model
  images_8/  (or images/ or images_4/)                # frame images
```
Image files must be named so they resolve: either match COLMAP `images.bin`
recorded names, OR be sortable index-ordered (loader falls back to index when
name not found on disk). Verify with a quick python read of images.bin names
vs disk listing before training.

## Run
```bash
. .venv/bin/activate
export PYTHONPATH="$PWD:$PYTHONPATH"
python train_mlx.py --data_dir /abs/path/train/sample \
  --img_folder images_8 --num_iterations 2000 --rasterizer cpp
```
Output: `results/<deploy>_mlx_cpp_<timestamp>/ply/<deploy>_final.ply`
PLY attributes: x,y,z, nx,ny,nz, f_dc_0..2, opacity, scale_0..2, rot_0..3
(standard 3DGS PLY — loadable by three.js gaussian-splat viewer, SuperSplat,
Unity GaussianSplatting).
