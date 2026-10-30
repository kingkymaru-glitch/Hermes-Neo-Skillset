# Interactive Asset Browser — Implementation Notes

## Problem
The Assets panel in `web/index.html` showed only a comma-separated string
(`dji_test, sample, test_pontoon`). No click-to-view, no delete.

## Backend Fix (server.py)
Added `do_DELETE` handler:
- `DELETE /api/assets/<name>` — removes `web/assets/<name>/model.ply`
- Cleans up empty deploy dirs
- Confirmed working: `{"deleted": "scratch"}`

## Frontend Fix (index.html + main.js + styles.css)
- `index.html`: `window.ASSET_ROW` template with View/Delete buttons
- `main.js`: `refreshAssets()` now builds real DOM rows instead of a
  comma-string; falls back to `defaultAssetRow()` if `ASSET_ROW` missing
- `styles.css`: `.asset-row` styling (LunaV-family glass panel look)

## Note
The `dji_test` and `test_pontoon` `.ply` files were lost during a branch
switch shuffle. The UI framework is functional; rebuilds from the pipeline
are needed to populate those assets again.
