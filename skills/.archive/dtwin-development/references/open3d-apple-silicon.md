# Open3D 0.18 on Apple Silicon — KD-tree segfault

## Symptom
Open3D operations that touch the KD-tree internally crash the process with NO
Python traceback — a hard segfault, usually during normal estimation or
statistical outlier removal. On Apple Silicon the `search_knn_vector_3d` C++
path is broken in Open3D 0.18.

## Confirmed in
- LUNASCAN (`lunascan-development` skill) — dead-code dissection + security
  hardening commits. The validated fix lives in its export module.
- DTwin P2 `clean_splat.py` statistical-outlier removal would hit this exact
  path (same Open3D dependency on Apple Silicon).

## Workaround (validated)
- Normal estimation: call `estimate_normals` with NO explicit `radius` (auto
  radius) — avoids the direct knn call.
- Outlier / denoise: do NOT use `remove_statistical_outlier` /
  `remove_radius_outlier` as-is. Prefer:
  - numpy-based distance/opacity thresholds (DTwin already drops opacity < 0.15),
  - bounding-box crop via direct coordinate slicing (no knn),
  - mesh fallback via poisson from splat centers (numpy/Open3D without knn).
- Colour transfer: avoid KD-tree nearest-neighbour; use broadcast/array math.

## Rule
Never reintroduce direct KD-tree calls (`search_knn_vector_3d`, `search_hybrid`)
in DTwin's clean step. If a future Open3D version fixes this, re-validate before
re-enabling the convenience outlier-removal helpers.
