# MLX 3DGS: checkpoint + densification + SH-degree porting (train_mlx.py)

Verified technique for hardening the DTwin MLX (splat-apple) trainer. All of
this was implemented and unit-tested on the dji_701 / sample datasets; the full
2000-iter prod run is the only unverified seam (CPU python rasterizer is slow;
use `--rasterizer cpp` on GPU, one build at a time — see GPU guard in SKILL.md).

## What was added
- **Crash-safe checkpointing**: `save_ply` every `--checkpoint_every` iters +
  a best-PSNR snapshot kept alongside. Protects against the pipeline EXIT-trap
  wipe (see SKILL.md EXIT-trap pitfall) — checkpoints live in `results/<name>_mlx_cpp_*/ply/`
  which the trap WILL delete on exit, so copy the final/best ply to `web/assets/<name>/`
  before the run ends, or the only surviving artifact is what pipeline.sh already published.
- **Resolution ramp**: train at low res early (scaled camera intrinsics + PIL
  target resize), full res later. Saves GPU without changing the renderer.
- **Adaptive densification** (standard 3DGS clone/split/prune) + **SH degree 1–3**
  (default 3) for sharper splats.

## MLX 0.30.6 API gotchas (blocked the port; use these workarounds)
- **No `mx.image.resize`.** Resize targets with PIL: `target = np.array(Image.fromarray(target).resize((W,H), 2))`.
- **No boolean-array indexing** (`means[keep]` errors). Convert masks to integer
  index arrays via numpy: `idx = np.where(mask)[0]` then `mx.take(means, mx.array(idx), axis=0)`.
  Apply the SAME index set to every param tensor (means/scales/quats/opac/sh) so
  shapes stay aligned.
- **Recompute size/opacity masks from CURRENT arrays inside EACH densify branch.**
  Clone then split both grow `params` (N0→2·N0). If you cache `max_scale_dim` /
  `opac_sig` from the pre-growth arrays, the split/prune mask broadcasts a stale
  length against the grown `grads_avg` → shape mismatch. Compute both clone and
  split masks from the PRE-growth arrays, then append all new Gaussians in one
  pass (don't split-then-prune on already-grown arrays).

## Densification port (mlx_gs/core/gaussians.py)
- `init_gaussians_from_pcd` returns a `Gaussians` dataclass — convert to the dict
  the loop expects: `{"means","scales","quaternions","opacities","sh_coeffs"}`
  at `run_training` init (the `resume` path already yields a dict).
- `densify_and_prune(params, mean_grad, extent, grad_threshold)`: standard
  `percent_dense = 0.0001 * extent`; clone small-grad+under-dense, split
  large-grad+large, prune `sigmoid(opacity) < min_opacity` or `max_scale > 0.01*extent`.
  Opacity threshold on `mx.sigmoid(opac)[:,0]` (raw opac init is 0 → all pruned otherwise).
- **Optimizer must be recreated after densify**: `optimizers = make_optimizers(params)`
  (shapes changed). Do this right after `params = densify_and_prune(...)`.

## SH degree (mlx_gs/renderer/renderer.py + gaussians.py)
- Store coeffs as `(N, K, 3)`, `K = (sh_degree+1)^2`. DC term `f_dc` is `sh_coeffs[:,0,:]`;
  higher bands `sh_coeffs[:,1:,:]`.
- Renderer must EVALUATE the SH basis for degree>0 (the original was DC-only and
  would render flat). Evaluate the real spherical-harmonic basis per Gaussian.
- `save_ply` / `load_gaussians_from_ply` must round-trip `rest` for K>1; guard
  `rest.reshape(N, K, 3)` against empty arrays (K>1 but N=0 after an all-prune).

## train_mlx.py CLI flag semantics (easy to loop on)
- Densify is ON by default. There is **NO `--densify` flag** — disable with
  `--no_densify`. Tuning flags: `--densify_from`, `--densify_until`, `--densify_interval`,
  `--grad_threshold`.
- There is **NO bare `--checkpoint` flag** — checkpointing is always on when
  `--checkpoint_every N` is set (and `--resume <ply>` to continue).
- argparse aborts on `--densify` (ambiguous with `--densify_from`); always pass
  the explicit `_from/_until/_interval` flags.

## Validate changes WITHOUT touching the live GPU job
- **Unit smoke test** (fast, CPU): init → `densify_and_prune` (assert N grows) →
  `save_ply` + `load_gaussians_from_ply` (assert SH K preserved) → render one frame.
  This caught every shape bug above.
- **End-to-end on real data**: call `run_training(...)` as a REAL SUBPROCESS
  (`python train_mlx.py --data_dir ... --img_folder images_8 --rasterizer python
  --num_iterations 60 --densify_from 15 --densify_until 55 --densify_interval 10
  --checkpoint_every 20`), NOT via `importlib.util.exec_module` — importlib path
  resolution differs from CLI and the COLMAP loader's cwd matters (it failed to
  find `sparse/0` under exec_module but works as a subprocess). Keep iters tiny;
  the python rasterizer is slow on 70k+ points.
- **NEVER patch `train_mlx.py` / `gaussians.py` mid-flight** on the running job —
  let the active build finish, then relaunch (same care as editing pipeline.sh).
