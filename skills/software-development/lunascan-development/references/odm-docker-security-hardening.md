# LUNASCAN ODM Docker hardened design (2026-08-10, commit `4e2f8d5`)

Security + robustness hardening applied to `lunascan/odm.py` after a SWE/security
review of the `.dmg`. All five findings are in the production path. Pinned image
is `opendronemap/odm:3.6.1`, digest-resolved on this host to
`opendronemap/odm@sha256:b5fda2c0f02308c1a7fb7a07b4405aa051cf509bcc8c46eb12d10af9cbfbaf8d`.

## Findings -> fixes

| ID | Class | Issue | Fix |
|----|-------|-------|-----|
| SEV-1 | docker | whole `project_dir` mounted `:rw` into ODM container | split mounts: images read-only (`:ro`), separate writable `code/` output mount |
| SEV-2 | supply-chain | `ODM_IMAGE` was a mutable `global`, reassigned from `--odm-image` (arbitrary `docker run`) | `_resolve_odm_image()` allowlist `^opendronemap/odm:\d+\.\d+\.\d+$`; never mutate global; resolve once into a local var |
| SEV-3 | supply-chain | tag `:3.6.1` not digest-pinned (upstream can re-publish) | default image is digest-pinned `@sha256:...` |
| BUG-2 | local TOCTOU | CLI `--output-dir` default `/tmp/lunascan` (predictable, symlink-plant risk) | `tempfile.mkdtemp(prefix="lunascan-")` when no dir given; `masking/cli.py` defaults next to keyframes |
| BUG-4 | correctness | non-zero ODM exit accepted as success if ANY `.glb` existed (could be 0-byte/truncated) | `is_valid_glb()` requires exists + size>=12 + magic `b"glTF"` before accepting degraded-success |

## `build_docker_command` (post-fix shape)

```python
cmd = [
    docker_bin, "run", "--rm",
    "-v", f"{images_dir.resolve()}:/datasets/code/images:ro",
    "-v", f"{(project_dir / 'code').resolve()}:/datasets/code",
    odm_image,   # opendronemap/odm@sha256:... when no override
] + flags
```

Assertions used in `tests/test_odm_security.py`:
- `f"{images_dir.resolve()}:/datasets/code/images:ro"` in cmd
- `f"{(project/'code').resolve()}:/datasets/code"` in cmd
- `f"{project.resolve()}:/datasets"` NOT in cmd (old unsafe form gone)
- image token startswith `opendronemap/odm@sha256:`

## `_resolve_odm_image` contract

```python
def _resolve_odm_image(odm_image):
    if odm_image is None:
        return ODM_IMAGE_DIGEST          # digest-pinned
    if _ODM_IMAGE_ALLOW_RE.match(odm_image):
        return odm_image                 # tag form allowed (pull enforces tag)
    raise ValueError("refusing unapproved ODM image ...")
```

Rejected in tests: `evil/custom:latest`, `opendronemap/odm:3.6` (not X.Y.Z),
`docker.io/library/alpine:latest`, `../../opendronemap/odm:3.6.1`.

## `is_valid_glb` contract

glTF binary: 12-byte header, first 4 bytes magic `b"glTF"`. Reject if missing,
size < 12, or wrong magic. Used in `run_odm` to gate the "degraded success"
path (non-zero exit but model produced).

## Verification

- `tests/test_odm_security.py` (15 cases) added; full suite 66 passed.
- DMG bundle re-verified: `ODM_IMAGE_DIGEST` present (3 hits), `:ro` present (2),
  `def is_valid_glb` present, old rw whole-project mount gone (0).
- Live run log confirms hardened command:
  `docker run --rm -v .../images:/datasets/code/images:ro -v .../odm/code:/datasets/code opendronemap/odm@sha256:b5fda2c...`
