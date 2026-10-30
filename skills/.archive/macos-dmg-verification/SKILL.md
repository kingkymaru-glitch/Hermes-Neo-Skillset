---
name: macos-dmg-verification
description: Rebuild a macOS .dmg? Mount and verify the bundled source.
---

# macOS .app / .dmg Build Verification

## When to use
After any change to a PyInstaller-bundled macOS app (`.app` from `--onedir`/`--onefile`, wrapped in `.dmg` via `hdiutil`), especially when you:
- dissected / deleted modules and must PROVE they are GONE from the shipped bundle
- fixed a bug and must PROVE the FIX is IN the bundle (not only in the source tree)
- rebuilt the artifact and the test suite is green — but the artifact itself is unverified

"Build exit 0 + pytest green" is NOT evidence the artifact is correct. The bundle is a *separate copy* of the code made at build time; verify it independently or you ship stale/oversized junk.

## The method (mount and inspect — never trust the build log)
1. Build as normal (`python build_app.py --dmg`). Note the final `.dmg` path.
2. Mount read-only, no Finder noise:
   `hdiutil attach /path/to/dist/APP.dmg -nobrowse -quiet`
3. Locate the mount point + bundle Resources (PyInstaller `--onedir` puts your source at `$RES/<pkg>/` and `$RES/app/`):
   `MNT=$(ls -d /Volumes/<VOLNAME>)`
   `RES="$MNT/<APP>.app/Contents/Resources"`
4. Grep the BUNDLED source for what must be ABSENT and what must be PRESENT:
   - Absent (deleted modules) — exact dir check, NEVER substring:
     `for m in sfm export storage publish; do [ -d "$RES/lunascan/$m" ] && echo "BAD $m present" || echo "ok $m gone"; done`
   - Present (fix markers): `grep -rl "0.95" "$RES/lunascan/pipeline.py"` etc.
   - AST-parse key bundled files to catch syntax rot:
     `python -c "import ast; ast.parse(open(f).read())"`
   - **Security-fix verification:** when a fix changes a command string or adds a
     function, assert BOTH that the NEW marker is present AND the OLD form is
     absent. Example (LUNASCAN docker hardening, 2026-08-10): present =
     `ODM_IMAGE_DIGEST`, `:ro`, `def is_valid_glb`; absent = the old whole-project
     rw mount `project_dir.resolve()}:/datasets"`. See
     `references/lunascan-security-rebuild.md`.
5. Detach: `hdiutil detach "$MNT" -quiet` (see pitfall — always detach in the same script).

## Pitfalls (learned the hard way)
- **Substring grep false-positives.** `grep -r "export"` or `find ... -path "*export*"` will MATCH `torch/_export/...` and `ultralytics/utils/export/` — third-party libs bundled inside the app. Your check will scream "export still present!" when it's just PyTorch. ALWAYS assert on EXACT package dirs (`[ -d "$RES/lunascan/export" ]`), never substring-on-path globs, when proving a module is gone.
- **Mount may show as `?`** in `ls /Volumes` if the volume has no clean name; capture the path explicitly rather than relying on `ls` output parsing.
- **`write_file` refuses the harness-mandated ad-hoc verify path.** The harness asks for `/private/var/folders/.../T/hermes-verify-*.py`, but `write_file` rejects it as "sensitive system path". Write the temp verify script to `/tmp` instead, run it, then `rm` it. Same evidence value, no blocker.
- **Always `hdiutil detach`.** If you forget, the dmg stays mounted and the next build's `hdiutil create -ov` can fail or corrupt the volume. Detach in the same script block.
- **A ~3 KB `.dmg` is a PARTIAL/BROKEN build.** `hdiutil` writes the final file last; the bundle `.app` is built first. If `ls` shows a tiny `.dmg` while the build is still running, it's incomplete. Wait for the log line `created: .../APP.dmg` before verifying. Size should be hundreds of MB for a torch/ultralytics app.
- **PyInstaller rebuild is slow** (bundling torch takes minutes). Run it background with `notify_on_complete`, don't block foreground.
- **Security/command-string fixes: check BOTH directions.** Grep the bundle for the
  NEW token (`:ro`, digest pin, new function name) AND confirm the OLD unsafe token
  is GONE (e.g. whole-project `:/datasets` rw mount). A hit on the new marker alone
  isn't proof the old code was removed — verify absence too.
- **A fix can silently NOT land if the build used a cached copy.** Always grep the
  BUNDLED file, not the source tree. If the bundle still shows the old form, rebuild
  from a clean `dist/` (`rm -rf dist build` first) — stale sources won't re-bundle.

## Verification script (re-runnable)
See `scripts/verify_bundle.py` — a parametric skeleton: mounts a dmg, asserts exact-dir absence of a given module list, asserts presence of marker strings in given files, AST-parses key files, detaches, exits non-zero on any failure. Copy and edit the dir/marker lists per project.

## Worked example (session-specific)
See `references/lunascan-dissection.md` for the concrete LUNASCAN case: which modules were dead, the validated pipeline path, and the exact markers grep'd. Use as a worked example, NOT a template — the module names are project-specific.
- For a *security-harden* rebuild (verify digest pin / read-only mount / glb validation actually landed in the bundle), see `references/lunascan-security-rebuild.md`.

## Related Skills
- For the dead-code dissection step that precedes this (cross-reference imports, delete unreachable modules, fix setup.py entry points + tests, gate with pytest), see general code-cleanup workflows. This skill only covers PROVING the rebuilt artifact is correct.
