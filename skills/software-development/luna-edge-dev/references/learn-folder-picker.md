# /learn — output-folder picker + image-folder ingestion (added 2026-08-14)

Founder: "add the A, and B as well just in case i came across samples of images."
Delivered as TWO capabilities on the `/learn` tab (video-freeze labeling kept intact):

## 1) Output-folder picker (choose where data + model land)
- Step 1 UI: `<input id="outDir">` + a status pill `#outDirStatus`; `checkOutDir()` (JS)
  POSTs `{dataset, out_dir}` to `/api/learn/settings` and shows ✓/✗.
- Server: `SETTINGS_DIR` = `learn/settings/<dataset>.json` stores `{"out_dir": <abs path>}`.
  `_learn_settings(dataset)` / `_set_learn_setting(dataset,key,val)` helpers in app.py.
- `out_dir` threads through: `capture` (save_capture), `train` (build_dataset + train),
  and the `dataset/list|image|delete` endpoints read `_learn_settings()` to find the
  capture dir. When unset, everything uses the repo defaults (learn/capture, learn/datasets,
  skills/). When set, capture writes to `<out_dir>/learn/capture/<name>_*`, dataset to
  `<out_dir>/learn/datasets/<name>/`, model copy to `<out_dir>/skills/<name>.pt`.
- E2E verified: capture with `out_dir:/tmp/e2e_models_b` wrote 16 frames there and ZERO in
  the repo default (learn/capture). Settings validation endpoint: SEE OPEN ITEM below.

## 2) Image-folder ingestion (label static image samples)
- Step 2 UI: `<input type=file webkitdirectory multiple id="folderInput">` + "Upload image
  folder" button calling `uploadFolder()`; a "Label from my uploaded folder" checkbox
  `#labelFromFolder`.
- `uploadFolder()` POSTs files to `/api/learn/folder/upload?dataset=<name>` (multi-part).
  Existing endpoint `learn_folder_upload` saves to `learn/inbox/<dataset>/`.
- Step 3: if `#labelFromFolder` checked, `useSelectedMedia()` → `startFolderTeach()` steps
  through `learn/inbox/<dataset>/*` as STATIC images (no `<video>`). `loadFolderFrame()`
  sets `#freezeImg` + `#drawCanvas` to the image's natural size; the SAME `toCanvas()`
  mapping (P2-A draw-accuracy) applies, so boxes land correctly on stills too. `saveFrame()`
  auto-advances via `nextFolderFrame()` instead of `unfreeze()`.
- E2E verified: upload 2 PNGs → list returns both → capture from a dataURL works.

## OPEN ITEM (verify before relying on the picker UX)
`/api/learn/settings` POST returned **400 Bad Request** in E2E even after a server restart
(while the co-edited `/api/learn/folder/upload` worked post-restart, proving the server was
NOT stale). So the 400 is a HANDLER bug, not a stale-process issue — inspect the settings
handler (must return `{"valid":bool,"out_dir":<real path>}` and not raise on JSON parse).
The `checkOutDir()` JS expects `j.valid`. Fix + re-E2E before telling the user the folder
picker is live.

## Pitfalls hit while building (also in SKILL.md #14/#15)
- Flask `request.form.get("dataset")` does NOT read the `?dataset=` query string on a POST
  (folder upload silently fell back to "custom", list came back empty). Use
  `request.values.get("dataset")` to capture both query + form.
- A brand-new route returning 404 → stale server, restart. Returning 400 after restart →
  handler bug, not staleness. Don't re-kill the server for a 400.
