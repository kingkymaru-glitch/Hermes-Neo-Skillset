# ODM matching flags — authoritative reference (ODM 3.12.3)

Captured 2026-08-10 while making LUNASCAN's 703 run finish. ODM's image-matching
control flags are counter-intuitive; the wrong one makes ODM run for HOURS on
1610 keyframes.

## Source of truth
```
docker run --rm opendronemap/odm:latest --help   # output goes to stderr
```
(ODM 3.12.3, built 2026-06-19.)

## The three matching flags

| Flag | Meaning | Default | Notes |
|------|---------|---------|-------|
| `--matcher-type` | FLANN (default) or BOW | FLANN | matcher algorithm, NOT the driver of which pairs |
| `--matcher-neighbors <N>` | match each image to its **N GPS-EXIF-nearest** neighbors | **0** | 0 = match by triangulation (FULL graph). This default is the trap. |
| `--matcher-order <N>` | match each image to nearest **N by filename order** | 0 | "applied only on **non-georeferenced** datasets. Set to 0 to disable." |

## Key gotcha
LUNASCAN geotags keyframes before ODM (for GPS). Because the dataset is then
georeferenced, **`--matcher-order` is SILENTLY IGNORED** and ODM falls back to
GPS-neighbor / triangulation matching regardless. So `--matcher-order 8` does NOT
give bounded sequential matching when GPS is embedded.

## Failure sequence observed (do not repeat)
1. `--matcher-neighbors 0` (full graph) → ~300K+ pairs on 1610 frames → 16+ min, never finished.
2. `--matching-algorithm sequential` → `error: unrecognized arguments` → ODM exit 2 in 5.6s. **This flag does not exist in 3.12.3.**
3. `--matcher-order 8` (GPS still embedded) → ignored → full graph → 126K pairs, killed.
4. `--matcher-neighbors 8` (GPS-KNN) → ~86K pairs after a few min, still expanding via covisibility; run in progress at session end. **Current state in `odm.py`.**

## Open decision (presented to founder, not yet resolved)
- **Strip GPS before ODM** → `--matcher-order 8` engages → truly bounded ~13K pairs.
  Trade-off: loses geo-anchoring (model still builds). Defensible because telemetry
  is a non-fatal 'bonus' (commit `bb11e09`).
- **Keep GPS + `--matcher-neighbors 8`** → correct geo-anchored result, ~15-25 min
  matching at 1610 frames.

## Diagnostic commands
```
# total matching pairs logged so far
docker logs <cid> 2>&1 | grep -c "Matching frame"
# rate (should approach 0 when done)
docker logs --since 20s <cid> 2>&1 | grep -c "Matching frame"
# success rate
docker logs <cid> 2>&1 | grep "Matching frame" | grep -c "Success: True"
# fan-out per image (8-neighbor should be ~8-16)
docker logs <cid> 2>&1 | grep "Matching frame_000000.jpg" | wc -l
```

## Verification trap
Do NOT assert flag presence with naive substring `in` on `odm.py` source — the
explanatory comments name `--matching-algorithm` and `--matcher-neighbors`. Parse
real flag tuples: `re.findall(r'-{2}[\w-]+', ' '.join(cmd))`. See
`scripts/verify-odm-command.py`.
