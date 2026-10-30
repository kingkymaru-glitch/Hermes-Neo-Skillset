# CDM Simulation Architecture

## Plugin System

- **Plugin engine**: `scripts/run_plugin.py` — Python process that reads DEM, runs physics, writes GeoJSON
- **Plugin registry**: `scripts/plugins/registry.json` — parameter schema (UI auto-renders from this)
- **DEM management**: `scripts/dem-data.mjs` — downloads Copernicus GLO-30 tiles to local cache
- **Python runtime**: `scripts/py-runtime.mjs` — provisions a managed venv (does NOT use system Python)
- **Worker**: `scripts/simulation_worker.mjs` — polls Supabase `simulation_runs` table for QUEUED jobs

## Job Lifecycle

User clicks Run → row inserted with status QUEUED → worker claims (atomic UPDATE with status guard) → downloads DEM → runs Python plugin → writes result back → status READY/FAILED

## PC2 Remote Worker

For heavy simulations (CFD, dam break), a remote worker runs on PC2:
- `scripts/cdm_worker_pc2.mjs` — same poll-claim-run pattern, runs on PC2 via systemd
- PC2 has its own Python venv at `/home/pc2/cdm-worker/venv` with numpy, scipy, rasterio, shapely, affine
- DEM tiles download independently on PC2 (each machine caches its own tiles)
- systemd service: `cdm-worker.service` at `/etc/systemd/system/`
- PC2 Supabase credentials must be in `/home/pc2/cdm-worker/worker.env` (separate from LunaV worker env)

## Dam Break Plugin

Uses 2D diffusive wave (Manning's equation + D8 flow direction). For realistic dam break simulation, PC2 is required (HEC-RAS 2D or OpenFOAM interFoam).

## Simulation Pitfalls

- **Plugin Python imports**: Plugins that use `from scipy.ndimage import ...` will fail if scipy is not in the managed venv. Check `~/Library/Application Support/CDM/runtime/venv/` for installed packages before relying on a scipy/numpy function.
- **Study radius column**: The `projects` table may NOT have a `study_radius_m` column. Always default to 1500m: `const radius = 1500;` — never query a column that may not exist.
- **Worker log file permissions**: When a systemd service runs as root, `worker.log` is owned by root. A manually-started worker (via `nohup`) cannot write to it. Fix: `sudo chown pc2:pc2 /home/pc2/cdm-worker/worker.log`.
- **Worker schema cache**: Supabase client caches the table schema. If a column (like `worker_id`) is added AFTER the client connects, queries fail with "Could not find the column". Either restart the worker after schema changes, or omit the column from queries.
- **Diffusive wave instability**: A naive 2D SWE solver with Manning friction produces NaN/inf when depth approaches zero. Always clip velocity (max 20 m/s), cap depth (2× reservoir level), and clean NaN/inf after each timestep. For dam break specifically, a D8 kinematic wave approach is more stable than full SWE.
- **Kinematic wave reference depth**: When computing travel time, use the reservoir level as reference depth — NOT the current cell depth (which may be zero at the dam, making all travel times infinite).
