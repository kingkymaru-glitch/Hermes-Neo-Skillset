# MLX 3DGS implementation gotchas — verified 2026-08-16

MLX on this Mac is **0.30.6**. Concrete, copy-paste patterns for
`tools/splat-apple/train_mlx.py`, `mlx_gs/core/gaussians.py`,
`mlx_gs/renderer/renderer.py`. Each was hit and fixed this session.

## 1. Densify: pre-growth masks + int indices + sigmoid opacity

```python
def densify_and_prune(params, grads, extent, grad_threshold=2e-4,
                      percent_dense=0.01, min_opacity=0.005, max_scale=0.1, n_split=2):
    means, scales, quats, opac, sh = (params["means"], params["scales"],
        params["quaternions"], params["opacities"], params["sh_coeffs"])
    import numpy as np
    def _idx(mask_bool):                       # mask_bool: mx.bool (N,)
        return mx.array(np.nonzero(np.asarray(mask_bool, dtype=bool))[0])
    # ---- compute BOTH masks from PRE-GROWTH arrays ----
    max_scale_dim = mx.max(mx.exp(scales), axis=1)
    opac_sig = mx.sigmoid(opac)[:, 0]          # NOT raw opac
    clone_mask = (grads > grad_threshold) & (max_scale_dim <= percent_dense*extent) & (opac_sig > min_opacity)
    split_mask = (grads > grad_threshold) & (max_scale_dim >  percent_dense*extent) & (opac_sig > min_opacity)
    ci, si = _idx(clone_mask), _idx(split_mask)
    # build clone/split tensors here, then append all at once...
    # ---- PRUNE on CURRENT arrays (recompute after growth) ----
    opac_sig = mx.sigmoid(opac)[:, 0]
    prune_mask = (opac_sig < min_opacity) | (mx.max(mx.exp(scales), axis=1) > max_scale*extent)
    keep = _idx(~prune_mask)
    # final: slice all params by `keep`, then concatenate clones/splits
```

Do NOT recompute a mask after `mx.concatenate` grows the arrays — `grads`
still has the old N → broadcast mismatch `(N0) vs (N0+Δ)`.

## 2. SH degree > 0 in the renderer (branch on sh_coeffs.shape[1])

```python
SH_C0 = 0.28209479177387814
if sh_coeffs.shape[1] > 1:
    f_dc = sh_coeffs[:, 0, :]
    f_rest = sh_coeffs[:, 1:, :]               # (N, K-1, 3)
    x, y, z = dir[:, 0], dir[:, 1], dir[:, 2]  # normalized view dirs (N,)
    sh = [mx.ones_like(x) * SH_C0,
          y, x, z,
          3*z*z - 1, x*y, x*z, y*z, 0.5*(x*x - y*y)]   # l=0,1,2 basis
    color = SH_C0 * f_dc
    for d in range(1, sh_coeffs.shape[1]):
        color = color + sh[d] * f_rest[:, d-1, :]
else:
    color = 0.5 + SH_C0 * f_dc                 # DC-only (original)
```

Without this branch, higher SH bands are silently ignored → flat/black in browser.

## 3. Train-loop init must wrap the dataclass into a dict

```python
g = init_gaussians_from_pcd(xyz, rgb, sh_degree=sh_degree)
params = {"means": g.means, "scales": g.scales, "quaternions": g.quaternions,
          "opacities": g.opacities, "sh_coeffs": g.sh_coeffs}
```

## 4. save_ply guard for empty rest (N == 0)

```python
K = sh.shape[1]
if K > 1 and xyz.shape[0] > 0:
    rest = sh[:, 1:, :].reshape(xyz.shape[0], -1)
else:
    rest = np.zeros((xyz.shape[0], 0), dtype=np.float32)
```

## 5. Smoke-test as a REAL subprocess (not importlib)

```bash
cd ~/DTwin/tools/splat-apple && .venv/bin/python train_mlx.py \
  --data_dir /Users/kamarulhk/DTwin/train/sample --img_folder images_8 \
  --num_iterations 60 --rasterizer cpp --sh_degree 3 \
  --densify_from 15 --densify_until 55 --densify_interval 10 --checkpoint_every 20
```

Fast unit smoke (no dataset, ~seconds):

```python
import mlx.core as mx, numpy as np
from mlx_gs.core.gaussians import init_gaussians_from_pcd, densify_and_prune, load_gaussians_from_ply
from train_mlx import save_ply
xyz = mx.random.normal((300, 3)); rgb = mx.clip(mx.random.normal((300, 3)) * 0.5 + 0.5, 0, 1)
g = init_gaussians_from_pcd(xyz, rgb, sh_degree=3)
p = {"means": g.means, "scales": g.scales, "quaternions": g.quaternions,
     "opacities": g.opacities, "sh_coeffs": g.sh_coeffs}
p2 = densify_and_prune(p, mx.array(np.random.rand(300)), 1.0, grad_threshold=2e-4)
assert p2["means"].shape[0] > 0            # grows 300 -> 600
save_ply("/tmp/s.ply", p2)
r = load_gaussians_from_ply("/tmp/s.ply")
assert r["sh_coeffs"].shape == (p2["means"].shape[0], 16, 3)   # SH round-trip
```

## 6. Confirmed data-loss: pipeline.sh EXIT trap

`tools/pipeline.sh` line ~213: `trap 'rm -rf "frames/$NAME" "train/$NAME"; rm -rf "$RESULT_BASE/${NAME}_mlx_cpp_"*; exit 1' EXIT`
runs on **every** exit. On 2026-08-16 the finished `dji_701` run's
`train/dji_701` + `results/..._mlx_cpp_*` were deleted the instant the job ended.
In-trainer checkpoints do NOT survive unless the trap is relaxed (preserve
`results/<name>_mlx_cpp_*/best_psnr.ply`, or copy to `splats/<name>/`).
