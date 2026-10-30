# Worked example — LUNASCAN dissect + rebuild (2026-08-10)

## Context
LUNASCAN is a PyInstaller-bundled macOS app (`.app` + `.dmg`) for drone
photogrammetry. The validated pipeline path is:
    ingest -> masking -> odm (Docker/ODM 3.6.1) -> optimize (Node.js glb)

Earlier iterations had left legacy modules that the ODM engine superseded but
which were still bundled (bloating the .dmg and confusing the codebase).

## Dead code removed (proven via `lunascan/`-scoped import grep)
- `lunascan/sfm/`  (COLMAP SfM — replaced by ODM docker)
- `lunascan/export/` (PLY/glb export — ODM emits .glb directly)
- `lunascan/storage/` (Cloudflare R2 upload + manifest — local-only directive)
- `app/publish.py` + `pipeline._upload_to_r2` (zero callers)
- `rover_body.py`, `scripts/sfm_speedup_benchmark.py` (stray)
- orphan tests: `test_sfm.py`, `test_export.py`, `test_storage.py`

## Verification markers grep'd in the BUNDLED source
Absent (exact dir check, NOT substring — torch/ultralytics ship `export/`/`storage/`):
    [ -d "$RES/lunascan/sfm" ]   -> gone
    [ -d "$RES/lunascan/export" ] -> gone
    [ -d "$RES/lunascan/storage" ] -> gone
    [ -f "$RES/app/publish.py" ]  -> gone
Present:
    pipeline.py: "from lunascan.odm import run_odm"
    pipeline.py: "0.95" (overlap default)
    odm.py: "matcher-order" (bounded fast matching)
    odm.py: "WITHOUT GPS" (telemetry graceful degrade)
    pipeline.py: NO "def _upload_to_r2"

## Pitfall hit during this session
First pass grep'd substring `export`/`storage` -> lit up
`torch/_export/...` and `ultralytics/utils/export/` — false positives.
Switched to EXACT-dir assertions. The bundled `odm.py` DOES contain the
"continuing WITHOUT GPS" strings (lines 45-57) — confirms the telemetry fix
survived into the artifact.

## Result
- 51/51 pytest green after deletion (added `test_odm_failure_aborts_early`
  to replace the deleted `test_sfm_failure_aborts_early`).
- New DMG 359 MB (was 358 MB; size barely changed because dead code was
  Python, dwarfed by torch/ultralytics in the bundle).
- Committed `d161d76` (dead-code dissection); DMG rebuilt from that commit.
