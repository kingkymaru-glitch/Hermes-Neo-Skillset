# LUNASCAN dead-code dissection + clean rebuild (2026-08-10, commit `d161d76`)

The validated pipeline path is `ingest -> masking -> odm(docker) -> optimize`.
A static import scan found these modules only referenced by `setup.py` entry
points + tests, never by the real pipeline (which uses `odm.run_odm`). They were
deleted.

## Deleted (unreachable)

- `lunascan/sfm/`        — COLMAP SfM (superseded by ODM docker engine)
- `lunascan/export/`     — old mesh/.glb packaging (ODM emits the .glb)
- `lunascan/storage/`    — R2 presigned upload (local-only directive)
- `app/publish.py`       — R2 + Supabase model-attach (zero callers)
- `lunascan/pipeline.py::_upload_to_r2` — no callers
- `rover_body.py`, `scripts/sfm_speedup_benchmark.py` — stray, separate project
- `tests/test_sfm.py`, `tests/test_export.py`, `tests/test_storage.py` — orphan tests

## Dissection method (reuse for any dead-code pass)

1. Static scan for internal imports (exclude `dist/` + `.venv/` — they swamp grep):
   ```bash
   SRC="lunascan app tests scripts setup.py"
   grep -rn "lunascan.sfm\|lunascan.export\|lunascan.storage" $SRC | grep -v "lunascan/sfm/"
   # repeat per suspect module; test files count as live refs
   ```
2. Confirm NO caller of the module OR its `_run_*` wiring in `pipeline.py`/`worker.py`.
3. Delete the dirs/files.
4. Remove dead `setup.py` entry_points + fix any test that mocks the deleted module
   (the old `test_sfm_failure_aborts_early` mocked `lunascan.sfm.cli.main` — replaced
   with `test_odm_failure_aborts_early` patching `lunascan.pipeline._run_sfm`).
5. `git add -A && git commit` the dissection separately from the rebuild.
6. Run the suite: `PYTHONPATH=. .venv/bin/python -m pytest tests/ -q`.

## PyInstaller rebuild gotchas

- `build_app.py` wipes `build/` AND `dist/` at the start of every `--dmg` run, so
  stale onedir output is always regenerated. Safe to `rm -rf build dist/LUNASCAN
  dist/LUNASCAN.app dist/LUNASCAN.dmg` before building.
- Build is slow (bundles torch/ultralytics). Run background with `notify_on_complete`.
- After build, PROVE the deletions landed in the bundle (substring grep lies — see
  `macos-dmg-verification` skill). Exact-dir check:
  ```bash
  MNT=$(hdiutil attach dist/LUNASCAN.dmg -nobrowse -quiet; ls -d /Volumes/LUNASCAN)
  RES="$MNT/LUNASCAN.app/Contents/Resources"
  for m in sfm export storage publish; do
    [ -d "$RES/lunascan/$m" ] && echo "BAD $m present" || echo "ok $m gone"
  done
  hdiutil detach "$MNT" -quiet
  ```
- The 3rd-party-lib false positive: `grep -r "export"` matches `torch/_export/`,
  `ultralytics/utils/export/` — those are NOT your modules. Assert exact dirs only.

## Result

- Source: 51 tests -> after adding ODM-abort test, 51; after security suite, 66.
- DMG 359 MB; dead modules absent; success-method markers (`0.95`, `--matcher-order 8`,
  graceful telemetry) present and verified.
