#!/usr/bin/env python3
"""CUDA 3DGS trainer using gsplat, reading a COLMAP sparse model directly.

Why this exists: the MLX trainer (splat-apple) is Apple-Silicon-only and cannot run
on a Linux/NVIDIA box. This is the CUDA replacement. It deliberately does NOT depend
on a training framework's dataset conventions — it parses the COLMAP binary model
itself, so the portable interface between stages stays the plain dataset layout.

Requirements: torch (CUDA build), gsplat, numpy, pillow.

    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu130
    pip install gsplat

Verify the CUDA build BEFORE trusting any timing:

    python -c "import torch;print(torch.__version__, torch.cuda.is_available(), torch.version.cuda)"

Usage:

    python train_gsplat_cuda.py --data <dir> --out <out.ply> [--iters 7000]

<dir> must contain `images/` and a COLMAP model at `sparse/0/` (or `sparse/`).
COLMAP commonly writes the model to `sfm/sparse/0/` — link or copy it into place
rather than editing this script.

Output is a standard 3DGS `.ply` (same layout splat-apple writes), so SuperSplat and
existing three.js viewers load it unchanged.
"""
from __future__ import annotations

import argparse
import struct
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn


# ---------------------------------------------------------------------------
# COLMAP binary readers (struct only, no pycolmap)
# ---------------------------------------------------------------------------
CAM_NPARAMS = {0: 3, 1: 4, 2: 4, 3: 5, 4: 8, 5: 8, 6: 12, 7: 5, 8: 4, 9: 4}


def read_cameras_bin(path: Path):
    cams = {}
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        for _ in range(n):
            cid, mid, w, h = struct.unpack("<iiQQ", f.read(24))
            npar = CAM_NPARAMS.get(mid, 4)
            params = struct.unpack("<" + "d" * npar, f.read(8 * npar))
            cams[cid] = dict(model=mid, width=w, height=h, params=np.array(params))
    return cams


def read_images_bin(path: Path):
    imgs = {}
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        for _ in range(n):
            iid = struct.unpack("<i", f.read(4))[0]
            q = struct.unpack("<4d", f.read(32))
            t = struct.unpack("<3d", f.read(24))
            cid = struct.unpack("<i", f.read(4))[0]
            name = b""
            while True:
                c = f.read(1)
                if c == b"\x00":
                    break
                name += c
            npts = struct.unpack("<Q", f.read(8))[0]
            f.read(24 * npts)  # xys
            imgs[iid] = dict(q=np.array(q), t=np.array(t), cam=cid,
                             name=name.decode("utf-8", "replace"))
    return imgs


def read_points3d_bin(path: Path):
    """Points + colours. The track is VARIABLE length per point — read it, never
    assume a fixed stride, or every point after the first is garbage."""
    xyz, rgb = [], []
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        for _ in range(n):
            f.read(8)                                    # point3D_id
            x, y, z = struct.unpack("<3d", f.read(24))
            r, g, b = struct.unpack("<3B", f.read(3))
            f.read(8)                                    # reprojection error
            track_len = struct.unpack("<Q", f.read(8))[0]
            f.read(8 * track_len)                        # (image_id, point2D_idx) pairs
            xyz.append((x, y, z))
            rgb.append((r, g, b))
    return np.array(xyz, dtype=np.float64), np.array(rgb, dtype=np.uint8)


# ---------------------------------------------------------------------------
# Camera math
# ---------------------------------------------------------------------------
def qvec_to_rotmat(q):
    """COLMAP quaternion (w, x, y, z) -> 3x3 rotation (world-to-camera)."""
    w, x, y, z = q
    return np.array([
        [1 - 2 * y * y - 2 * z * z, 2 * x * y - 2 * z * w, 2 * x * z + 2 * y * w],
        [2 * x * y + 2 * z * w, 1 - 2 * x * x - 2 * z * z, 2 * y * z - 2 * x * w],
        [2 * x * z - 2 * y * w, 2 * y * z + 2 * x * w, 1 - 2 * x * x - 2 * y * y],
    ], dtype=np.float64)


def get_intrinsics(cam, target_w=None, target_h=None):
    """fx, fy, cx, cy — scaled if a target resolution is given."""
    m, p = cam["model"], cam["params"]
    w, h = cam["width"], cam["height"]
    if m in (0, 2, 3):          # SIMPLE_PINHOLE / SIMPLE_RADIAL / RADIAL
        fx = fy = p[0]
        cx, cy = p[1], p[2]
    else:                       # PINHOLE / OPENCV / OPENCV_FISHEYE / ...
        fx, fy, cx, cy = p[0], p[1], p[2], p[3]
    if target_w and target_h:
        sx, sy = target_w / w, target_h / h
        fx *= sx; cx *= sx; fy *= sy; cy *= sy
    return fx, fy, cx, cy, w, h


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
class GaussianModel(nn.Module):
    def __init__(self, xyz, rgb, sh_degree=3):
        super().__init__()
        n = xyz.shape[0]
        self.sh_degree = sh_degree
        n_coef = (sh_degree + 1) ** 2
        self.means = nn.Parameter(torch.tensor(xyz, dtype=torch.float32))
        d = torch.sqrt(((self.means - self.means.mean(0)) ** 2).sum(1)).clamp(min=1e-6)
        self.scales = nn.Parameter(torch.log(torch.sqrt(d[:, None].repeat(1, 3)) * 0.5))
        self.quats = nn.Parameter(torch.zeros(n, 4))
        self.quats.data[:, 0] = 1.0
        self.opacities = nn.Parameter(torch.logit(torch.full((n, 1), 0.5)))
        c = np.clip(rgb.astype(np.float32) / 255.0, 1e-4, 1 - 1e-4)
        c = np.log(c / (1 - c))                       # inverse sigmoid -> SH DC term
        sh = torch.zeros(n, n_coef, 3)
        sh[:, 0, :] = torch.tensor(c)
        self.shs = nn.Parameter(sh)

    def forward(self):
        # NOTE the squeeze: gsplat asserts opacities are (N,), not (N,1).
        return (self.means, torch.exp(self.scales),
                torch.sigmoid(self.opacities).squeeze(-1),
                torch.nn.functional.normalize(self.quats, dim=-1), self.shs)


# ---------------------------------------------------------------------------
# PLY writer (standard 3DGS layout)
# ---------------------------------------------------------------------------
def write_splat_ply(path: Path, means, scales, opac, quats, shs):
    n = means.shape[0]
    m = means.detach().cpu().numpy()
    s = scales.detach().cpu().numpy()
    o = opac.detach().cpu().numpy()
    if o.ndim == 1:
        o = o[:, None]
    q = quats.detach().cpu().numpy()
    sh = shs.detach().cpu().numpy()

    # f_rest_* is a FLAT range, channel-major [R0..Rk, G0..Gk, B0..Bk]. Emitting it as
    # nested [i, i+1, i+2] triples duplicates property names and breaks strict loaders.
    props = ["x", "y", "z", "nx", "ny", "nz", "f_dc_0", "f_dc_1", "f_dc_2"]
    n_rest = 3 * (sh.shape[1] - 1)
    props += [f"f_rest_{i}" for i in range(n_rest)]
    props += ["opacity", "scale_0", "scale_1", "scale_2",
              "rot_0", "rot_1", "rot_2", "rot_3"]

    rest = sh[:, 1:, :].transpose(0, 2, 1).reshape(n, -1)
    flat = np.concatenate(
        [m, np.zeros((n, 3), np.float32), sh[:, 0, :], rest,
         o, np.log(np.clip(s, 1e-9, None)), q], axis=1).astype(np.float32)

    assert len(props) == len(set(props)), "duplicate PLY property names"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"ply\nformat binary_little_endian 1.0\n")
        f.write(f"element vertex {n}\n".encode())
        for p in props:
            f.write(f"property float {p}\n".encode())
        f.write(b"end_header\n")
        f.write(flat.tobytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="dir with images/ and sparse/0/")
    ap.add_argument("--out", default="splat.ply")
    ap.add_argument("--iters", type=int, default=7000)
    ap.add_argument("--sh-degree", type=int, default=3)
    ap.add_argument("--downscale", type=int, default=2)
    ap.add_argument("--log-every", type=int, default=250)
    a = ap.parse_args()

    assert torch.cuda.is_available(), (
        "CUDA not available — install the CUDA torch wheel explicitly, a default-index "
        "install on Linux is CPU-only")
    dev = torch.device("cuda")
    torch.manual_seed(0)

    data = Path(a.data)
    sparse = data / "sparse" / "0"
    if not sparse.exists():
        sparse = data / "sparse"
    if not (sparse / "cameras.bin").exists():
        raise SystemExit(f"no COLMAP model at {sparse} — COLMAP often writes sfm/sparse/0/")

    cams = read_cameras_bin(sparse / "cameras.bin")
    imgs = read_images_bin(sparse / "images.bin")
    xyz, rgb = read_points3d_bin(sparse / "points3D.bin")
    print(f"cameras={len(cams)} images={len(imgs)} points3D={len(xyz)}")

    c0 = cams[list(cams)[0]]
    tw, th = c0["width"] // a.downscale, c0["height"] // a.downscale
    fx, fy, cx, cy, _, _ = get_intrinsics(c0, tw, th)

    model = GaussianModel(xyz, rgb, a.sh_degree).to(dev)
    print(f"gaussians={model.n} sh_degree={a.sh_degree} image={tw}x{th}")

    opt = torch.optim.Adam([
        {"params": [model.means], "lr": 1.6e-4},
        {"params": [model.scales], "lr": 5e-3},
        {"params": [model.quats], "lr": 1e-3},
        {"params": [model.opacities], "lr": 5e-2},
        {"params": [model.shs], "lr": 2.5e-3},
    ], eps=1e-15)

    from gsplat import rasterization
    from PIL import Image

    views = []
    for im in imgs.values():
        p = data / "images" / im["name"]
        if not p.exists():
            p = data / im["name"]
        if not p.exists():
            continue
        R = qvec_to_rotmat(im["q"])
        c2w = np.eye(4)
        c2w[:3, :3] = R.T
        c2w[:3, 3] = -R.T @ im["t"]
        views.append((str(p), torch.tensor(c2w, dtype=torch.float32, device=dev)))
    print(f"usable views={len(views)}")

    K = torch.tensor([[fx, 0, cx], [0, fy, cy], [0, 0, 1]],
                     dtype=torch.float32, device=dev)
    bg = torch.zeros(3, device=dev)

    t0 = time.perf_counter()
    step = 0
    for step in range(a.iters + 1):
        path, c2w = views[np.random.randint(len(views))]
        im = Image.open(path).convert("RGB").resize((tw, th), Image.LANCZOS)
        gt = torch.tensor(np.asarray(im, np.float32) / 255.0, device=dev)

        means, scales, opac, quats, shs = model.forward()
        colors, alphas, _ = rasterization(
            means, quats, scales, opac, shs,
            torch.linalg.inv(c2w)[None], K[None], tw, th,
            sh_degree=a.sh_degree, render_mode="RGB")
        loss = torch.nn.functional.l1_loss(colors[0] + (1 - alphas[0]) * bg, gt)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()

        if step % a.log_every == 0:
            el = time.perf_counter() - t0
            print(f"step {step:6d}/{a.iters}  loss {loss.item():.4f}  "
                  f"N {means.shape[0]:6d}  {(step + 1) / el:.1f} it/s  {el:.0f}s",
                  flush=True)

    el = time.perf_counter() - t0
    means, scales, opac, quats, shs = model.forward()
    out = Path(a.out)
    write_splat_ply(out, means, scales, opac, quats, shs)

    # One machine-readable line so a two-machine benchmark is mechanical, not eyeballed.
    print(f"RESULT steps={step} seconds={el:.1f} it_per_sec={(step + 1) / el:.2f} "
          f"gaussians={means.shape[0]} ply_mb={out.stat().st_size / 1e6:.1f}")


if __name__ == "__main__":
    main()
