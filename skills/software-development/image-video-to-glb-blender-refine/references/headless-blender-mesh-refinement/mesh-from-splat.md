# Splat → mesh (Poisson) with subject isolation

Turning a trained Gaussian splat into a surface mesh, as the input to the
Blender refine stage. Requires Open3D (use a dedicated mesh venv; `open3d`
0.19+ works, `trimesh` is not needed).

## Reading a 3DGS .ply
A trained splat PLY carries `x,y,z` plus `opacity`, `f_dc_0..2`, `scale_*`,
`rot_*` (and `f_rest_*` for SH > 0). Two conversions matter:

```python
rgb   = (0.5 + 0.28209479177387814 * f_dc).clip(0, 1)   # 0.28209 = 1/(2*sqrt(pi))
alpha = 1.0 / (1.0 + np.exp(-opacity))                 # opacity is stored raw/logit
```

Filtering on `alpha >= 0.05` typically drops a few percent of Gaussians. A higher
threshold (0.15) is worth trying when a scene splat has a lot of faint haze.

## THE FAILURE MODE: Poisson on a whole-scene splat
Poisson welds **everything** in the cloud into one closed surface. A scene splat
contains ground, background and sky floaters, so the result is a shapeless blob —
observed as a vertical column rising from a flat base when the real subject was a
pavilion.

A **bounding-box crop does not fix this.** Measured: trimming 18% off each side
of the splat bounds removed only 474 of 48,510 points, because the bounds are set
by distant floaters, not by the dense subject. On a path-based capture (a drone
flying a route) the cloud is a long strip — here 132 × 50 × 187 units — and any
axis-aligned box that contains the subject also contains a large slice of the
surroundings.

## THE FIX: keep the largest connected blob
DBSCAN on the point cloud, then keep the biggest cluster. Scale `eps` to the
cloud extent so the same setting works at any capture scale (a reconstruction has
no absolute units):

```python
import numpy as np

pts = np.asarray(pcd.points)
extent = pts.max(0) - pts.min(0)
eps = float(extent.max() * 0.02)          # 2% of the longest axis
labels = np.array(pcd.cluster_dbscan(eps=eps, min_points=30))
ids, counts = np.unique(labels[labels >= 0], return_counts=True)
keep = labels == ids[int(np.argmax(counts))]
```

Measured on the failing case: 11 clusters, the largest holding 36,393 of 37,455
points. Keeping it produced a recognizable structure where the uncropped Poisson
had produced a column. Raise `eps` to 0.04 if the subject fragments into pieces
(it then finds 2 clusters, 36,694 vs 590).

Guard the degenerate case: if fewer than ~500 points survive, raise rather than
meshing a handful of points into nonsense.

## Poisson parameters
```python
pcd.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=0.05, max_nn=30))
pcd.orient_normals_consistent_tangent_plane(30)
mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd, depth=9)
mesh.remove_vertices_by_mask(densities < np.quantile(densities, 0.02))
```
- `depth=9` is a reasonable default; step down if the solver is slow or the mesh
  is far over budget. Poisson emits `Failed to close loop [..]` warnings to stderr
  on noisy clouds — noise, not a failure, provided faces are produced.
- Always trim the low-density shell; Poisson wraps the whole cloud in one.
- Fall back to `create_from_point_cloud_alpha_shape` if Poisson returns nothing.
- Verify `mesh.has_vertex_colors()` before writing — the colour comes from the
  splat's DC term and is what the Blender material later consumes.

## Budget the decimation across BOTH stages
Decimate in Blender, not here. A splat-derived mesh is decimated twice if the mesh
stage also applies a tight `--max-faces`, and the second pass costs detail for no
benefit. Give the mesh stage a generous budget (~300k) and let the Blender refine
stage hit the final target.

## One capture, two artefacts — never confuse them
A splat-derived mesh is a **visual** asset. Surface extraction rounds corners,
bridges gaps and inflates thin features, so it is not dimensionally trustworthy.
The **measurement** source is the COLMAP point cloud from the same run (3DGS needs
COLMAP poses anyway, so it is already there). Measure off the cloud, show the mesh.
