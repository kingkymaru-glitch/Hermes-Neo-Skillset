# Worked example — LUNASCAN security-harden rebuild (2026-08-10)

## What changed (source, commit 4e2f8d5)
- SEV-1: docker images mounted read-only (`:ro`); separate writable `code/` mount
- SEV-2: `--odm-image` override allowlist-checked (`^opendronemap/odm:\d+\.\d+\.\d+$`)
- SEV-3: default ODM image digest-pinned (`opendronemap/odm@sha256:b5fda2c0...`)
- BUG-2: CLI default output dir = unique `tempfile.mkdtemp(prefix="lunascan-")`
- BUG-4: `is_valid_glb()` rejects empty/truncated/non-glTF before "degraded success"

## Bundle verification (after `python build_app.py --dmg`)
Mount + grep the BUNDLED source
(`$RES` = `/Volumes/LUNASCAN/LUNASCAN.app/Contents/Resources`):

PRESENT (new code landed):
  grep -c "ODM_IMAGE_DIGEST"          "$RES/lunascan/odm.py"   # >=1
  grep -c ":ro"                       "$RES/lunascan/odm.py"   # read-only mount
  grep -c "def is_valid_glb"          "$RES/lunascan/odm.py"   # BUG-4 guard
  grep -c "opendronemap/odm@sha256:"  "$RES/lunascan/odm.py"   # digest pin

ABSENT (old unsafe code gone):
  grep -c 'project_dir.resolve()}:"/datasets"' "$RES/lunascan/odm.py"  # 0 = good

API/CLI default check:
  grep -c 'default="/tmp/lunascan/masks"' "$RES/lunascan/masking/cli.py"  # 0 = fixed

## Result
358 MB DMG; 66 pytest pass; hardened code confirmed PRESENT in bundle, old
whole-project rw mount confirmed ABSENT.
