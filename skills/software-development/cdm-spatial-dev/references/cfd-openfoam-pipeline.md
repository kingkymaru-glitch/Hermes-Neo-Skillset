# CFD Pipeline — OpenFOAM v2606 Wind Simulation (Detail Wind plugin)

Class-level recipe for building `engine: "cfd"` simulation plugins on the CDM platform using
OpenFOAM v2606 (native Apple Silicon). Covers the full pipeline: geometry → mesh → solve →
post-process → GeoJSON.

## When to use

- Any plugin whose engine is `"cfd"` (the simulation worker dispatches on `engine` from the registry).
- The app QUEUES a run; a local Mac worker claims it; the hosted Vercel build can only queue.
- RANS only (LES is hours/run, not suitable for a web-queued screening tool).

## Pipeline stages

### Stage 1 — Geometry (Python)

`scripts/cfd_geometry.py` converts OSM building footprints + heights → STL:

- Reads OSM GeoJSON (from `scripts/osm-buildings.mjs` quick-buildings extraction)
- Converts lon/lat to local metres using WGS84 arc-length approximation
- Extrudes each building footprint to its height as a **closed manifold** (shared corner
  vertices on walls, fan-triangulated roof/floor) — surfaceFeatureExtract requires manifold
  surfaces; non-manifold STLs cause feature extraction to silently emit no eMesh
- Outputs a single STL file

### Stage 2 — Mesh (OpenFOAM solvers)

`scripts/cfd_case_runner.sh` executes blockMesh → surfaceFeatureExtract → snappyHexMesh → checkMesh.

**Critical v2606 dict schema** (differs from older OpenFOAM versions — verify against tutorials):

```
snappyHexMeshDict {
    castellatedMesh true;
    snap true;
    addLayers true;                       // root-level flag required
    addLayersControls {
        relativeSizes false;              // MUST be at top of addLayersControls
        layers { }                        // per-patch specs OR empty
        expansionRatio 1.0;
        finalLayerThickness 0.5;
        minThickness 0.1;
        nGrow 0;
        featureAngle 60;
        nRelaxIter 3;
        nSmoothSurfaceNormals 1;
        nSmoothNormals 3;
        nSmoothThickness 10;
        maxFaceThicknessRatio 0.5;
        maxThicknessToMedialRatio 0.3;
        minMedianAxisAngle 90;
        minMedialAxisAngle 90;            // v2606 requires BOTH, not just minMedianAxisAngle
        nBufferCellsNoExtrude 0;
        nLayerIter 50;
        nRelaxedIter 20;
        relaxed {                         // v2606 requires relaxed block
            maxNonOrtho 75;
            minTetQuality -1e30;
            minTwist -1;
        }
    }
    castellatedMeshControls {
        // ...
        resolveFeatureAngle 60;           // INSIDE castellatedMeshControls (not at root)
    }
}
```

**Domain sizing rule**: `locationInMesh` must be inside the domain AND above the tallest
building. Domain height = 5x max building height (for proper wind clearance above the
buildings). Background blockMesh cell count scales as (domain_size/2)^2 * (5*building_height/2).

### Stage 3 — Solve (simpleFoam, RANS, k-omega SST)

- Steady-state RANS with atmospheric boundary layer inlet profile
- ABL inlet: `atmBoundaryLayerInletVelocity` for U, `atmBoundaryLayerInletk` for k,
  `atmBoundaryLayerInletOmega` for omega
- Ground/buildings: `noSlip` + `nutkWallFunction`
- Solver: GAMG for p, smoothSolver for U/k/omega
- 500 iterations is sufficient for a converged RANS screening run

### Stage 4 — Post-process (Python)

`scripts/cfd_postprocess.py` samples pedestrian-level wind speeds at 1.5 m:

- Reads the latest time directory's U field
- Magnitude = sqrt(Ux^2 + Uy^2)
- Classifies into Lawson comfort bands (Calm/Light/Moderate/Fresh/Strong/Severe)
- Emits GeoJSON polygons + summary (mean/max/min speed per band)

## Worker dispatch (simulation_worker.mjs)

```javascript
async function run(job) {
  // ...
  if (job.plugin_id === "wind_detail") {
    return runCfd(job, { lat, lon, radius, params });
  }
  // ... standard raster plugin path
}
```

`runCfd` extracts OSM buildings → generates STL → runs cfd_case_runner.sh → post-processes
→ stores GeoJSON on the row. Timeout: 60 min (CFD mesh+solve exceeds 30 min).

## Traps that cost real time

### macOS OpenFOAM wrapper

The `openfoam2606` wrapper mounts a DMG and sources the environment. Do NOT source
`/Volumes/OpenFOAM-v2606/etc/bashrc` directly — `WM_PROJECT_DIR` is unbound and the sourcing
fails. Use `openfoam2606 <cmd>` for every solver (blockMesh, snappyHexMesh, surfaceFeatureExtract,
checkMesh, simpleFoam).

### bash heredoc dict files

Writing OpenFOAM dict files via bash heredocs is fragile: f-string escaping collides with
OpenFOAM's `{ }` braces, `$var` expands unexpectedly, and the syntax errors are cryptic.
**Use Python to write dict files.** `scripts/cfd_write_dicts.py` writes every dict (0/U, 0/p,
0/k, 0/omega, 0/nut, system/controlDict, fvSchemes, fvSolution, snappyHexMeshDict,
blockMeshDict, surfaceFeatureExtractDict, transportProperties, turbulenceProperties) with
proper escaping via Python string formatting.

### Background CFD runs

CFD takes 10-20 min (mesh snap alone is ~130s for a 300m domain). Always run in background
with `notify=true` so you get pinged on completion. A foreground `sleep`+`tail` times out at
60s and wastes a call.

### OSM extraction bbox for CFD

The CFD worker extracts buildings over `radius * 1.5` to give the domain enough context.
The `osm-buildings.mjs` script takes `--min-lat --max-lat --min-lon --max-lon`. Convert
the study radius to lat/lon deltas using `dLat = radius / 111320`,
`dLon = radius / (111320 * cos(lat))`. Ensure buildings are actually inside the domain —
the previous test had them at 557m from centre in a 300m domain, causing snappyHexMesh to
subset to 1 cell.

### STL manifoldness check

If surfaceFeatureExtract fails to produce an eMesh or snappyHexMesh reports 0 refined
cells, the STL is non-manifold. Ensure buildings share corner vertices between adjacent
wall triangles, and roof/floor use fan triangulation from a shared centroid.

### Version drift in OpenFOAM dicts

If a solver reports `Entry 'X' not found in dictionary "system/Y"`, check the current
OpenFOAM version's tutorials at `$FOAM_TUTORIALS/mesh/snappyHexMesh/*/system/snappyHexMeshDict`
for the correct key name and location. v2606 renamed/relocated several keys compared to
earlier versions (e.g. `nLayers` → `nSurfaceLayers`, `resolveFeatureAngle` moved inside
`castellatedMeshControls`).
