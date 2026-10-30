#!/usr/bin/env python3
"""
Splat .ply -> vertex-coloured mesh .ply, with cluster isolation.

Stops at .ply on purpose: the final .glb belongs to the Blender refine stage,
which is the only place final decimation / UV / scale normalisation happens.

Usage:
  mesh-venv/bin/python mesh_from_splat.py in.ply out.ply [--max-faces N]
      [--depth D] [--alpha-thresh A] [--sample N] [--crop-pct P] [--no-cluster]

Cluster isolation (ON by default) is what stops Poisson welding ground and
background into the subject. A bbox crop is offered but is usually the wrong tool:
a moving capture yields a long strip, so any axis-aligned box containing the
subject also contains a large slice of the surroundings.

Requires open3d + plyfile (the DTwin mesh venv has both).
"""
import argparse
import json
import os
import sys

import numpy as np


def read_gaussian_ply(path):
    """f_dc is the SH DC term; 0.28209 = 1/(2*sqrt(pi))."""
    import plyfile
    p = plyfile.PlyData.read(path)
    v = p["vertex"]
    xyz = np.stack([np.asarray(v["x"]), np.asarray(v["y"]), np.asarray(v["z"])], -1).astype(np.float32)
    f_dc = np.stack([np.asarray(v["f_dc_0"]), np.asarray(v["f_dc_1"]), np.asarray(v["f_dc_2"])], -1).astype(np.float32)
    rgb = (0.5 + 0.28209479177387814 * f_dc).clip(0, 1)
    names = v.data.dtype.names or ()
    alpha = (1.0 / (1.0 + np.exp(-np.asarray(v["opacity"])))).astype(np.float32) \
        if "opacity" in names else np.ones(len(xyz), np.float32)
    return xyz, rgb, alpha


def keep_largest_cluster(pcd, eps_frac=0.02, min_points=30):
    """
    Keep the biggest connected blob.

    eps scales with the cloud extent, which matters because a reconstruction has no
    absolute units -- the same setting then works at any capture scale.
    """
    import open3d as o3d
    pts = np.asarray(pcd.points)
    if len(pts) < min_points * 2:
        return pcd, 1
    extent = pts.max(0) - pts.min(0)
    eps = float(extent.max() * eps_frac)
    labels = np.array(pcd.cluster_dbscan(eps=eps, min_points=min_points))
    ids, counts = np.unique(labels[labels >= 0], return_counts=True)
    if len(ids) == 0:
        return pcd, 1
    keep = labels == ids[int(np.argmax(counts))]
    print(f"[mesh] cluster eps={eps:.2f}: kept {int(keep.sum()):,} of {len(pts):,} "
          f"in largest of {len(ids)} clusters", flush=True)
    out = o3d.geometry.PointCloud()
    out.points = o3d.utility.Vector3dVector(pts[keep])
    cols = np.asarray(pcd.colors)
    if cols.shape[0] == len(pts):
        out.colors = o3d.utility.Vector3dVector(cols[keep])
    return out, len(ids)


def run(in_ply, out_ply, max_faces, sample, depth, alpha_thresh, crop_pct, cluster):
    import open3d as o3d
    xyz, rgb, alpha = read_gaussian_ply(in_ply)
    print(f"[mesh] {xyz.shape[0]:,} gaussians", flush=True)
    print(f"[mesh] bounds min={np.round(xyz.min(0),2).tolist()} "
          f"max={np.round(xyz.max(0),2).tolist()}", flush=True)

    mask = alpha >= alpha_thresh
    if crop_pct > 0:
        lo, hi = xyz.min(0), xyz.max(0)
        pad = (hi - lo) * (crop_pct / 100.0)
        for ax in range(3):
            mask &= (xyz[:, ax] >= lo[ax] + pad[ax]) & (xyz[:, ax] <= hi[ax] - pad[ax])
    xyz, rgb = xyz[mask], rgb[mask]
    if xyz.shape[0] < 500:
        raise RuntimeError(f"only {xyz.shape[0]} points survive filtering - crop too tight")
    if sample and xyz.shape[0] > sample:
        idx = np.random.RandomState(0).choice(xyz.shape[0], sample, replace=False)
        xyz, rgb = xyz[idx], rgb[idx]

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(xyz)
    pcd.colors = o3d.utility.Vector3dVector(rgb)
    n_clusters = None
    if cluster:
        pcd, n_clusters = keep_largest_cluster(pcd)

    pcd.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=0.05, max_nn=30))
    pcd.orient_normals_consistent_tangent_plane(30)

    mesh = o3d.geometry.TriangleMesh()
    method, d = None, depth
    while True:
        print(f"[mesh] poisson depth={d}", flush=True)
        try:
            mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd, depth=d)
        except Exception as exc:
            print(f"[mesh] poisson failed at depth={d}: {exc}", flush=True)
            break
        # Poisson always emits a low-confidence outer shell; trim it or the model
        # comes back as a closed balloon around the subject.
        mesh.remove_vertices_by_mask(densities <= np.quantile(densities, 0.02))
        mesh.compute_vertex_normals()
        method = "poisson"
        print(f"[mesh] raw faces={len(mesh.triangles)}", flush=True)
        if len(mesh.triangles) <= max_faces * 1.5 or d <= 5:
            break
        d -= 1
    if len(mesh.triangles) == 0:
        print("[mesh] poisson unreliable - alpha shape fallback", flush=True)
        mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_alpha_shape(pcd, 0.1)
        mesh.compute_vertex_normals()
        method = "alpha"
    if len(mesh.triangles) > max_faces:
        mesh = mesh.simplify_quadric_decimation(max_faces)

    os.makedirs(os.path.dirname(os.path.abspath(out_ply)), exist_ok=True)
    o3d.io.write_triangle_mesh(out_ply, mesh)
    meta = {"input": in_ply, "output": out_ply, "method": method,
            "poisson_depth": d, "faces": int(len(mesh.triangles)),
            "vertices": int(len(mesh.vertices)),
            "has_vertex_colors": bool(mesh.has_vertex_colors()),
            "clusters_found": n_clusters,
            "params": {"max_faces": max_faces, "sample": sample,
                       "alpha_thresh": alpha_thresh, "crop_pct": crop_pct,
                       "cluster": cluster}}
    with open(os.path.splitext(out_ply)[0] + ".mesh.json", "w") as fh:
        json.dump(meta, fh, indent=2)
    print(f"MESH_OK faces={len(mesh.triangles)} verts={len(mesh.vertices)}", flush=True)
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--max-faces", type=int, default=300000,
                    help="generous by default - the Blender stage does final decimation")
    ap.add_argument("--sample", type=int, default=600000)
    ap.add_argument("--depth", type=int, default=9)
    ap.add_argument("--alpha-thresh", type=float, default=0.05)
    ap.add_argument("--crop-pct", type=float, default=0.0)
    ap.add_argument("--no-cluster", action="store_true")
    a = ap.parse_args()
    sys.exit(run(a.input, a.output, a.max_faces, a.sample, a.depth,
                 a.alpha_thresh, a.crop_pct, not a.no_cluster))
