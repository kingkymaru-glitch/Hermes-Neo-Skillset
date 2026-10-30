# Evidence From Session — DTwin Pipeline Hardening

## 1. Exhaustive matcher = 4h18m for 300 frames
TESTMALL.mp4 (1280x720, 211s, sampled to 300 frames) ran exhaustive_matcher
for **4h18m** before hitting the 3.03h timeout. Processed 31/36 blocks;
last block [6/6,2/6] took 6019s (1h40m). This is O(N²) and is unacceptable
for users.

## 2. Sequential matcher = 8–10 min (estimated)
sequential_matcher with overlap=10 reduces pairs from 44,850 to 3,000.
Estimated matching time: ~8–10 min on this Mac.

## 3. [METAL] crash on concurrent training
Two concurrent `train_mlx.py` jobs crashed with:
`[METAL] Command buffer execution failed: Impacting Interactivity`
→ Fixed with a GPU guard (`pgrep -f train_mlx.py` guard before training).

## 4. Timeout actually kills
The perl alarm-kill wrapper was verified to kill `sleep 30` in exactly 2.007s
(exit 142 = SIGALRM). TESTMALL was killed cleanly at 3.03h.

## 5. Pipe-full deadlock
Server.py previously had no stdout drain; a dropped SSE client would hang
the pipeline once the ~64KB OS pipe filled. Fixed with a background reader
thread + ring buffer.

## 6. train_mlx.py output path
Trainer writes to `cwd/results/<name>_mlx_cpp_<ts>/ply/`, NOT
`tools/splat-apple/results/`. Pipeline.sh must use `RESULT_BASE="results"`.

## 7. COLMAP dir separation
When `sfm/` lives inside the images folder, COLMAP scans `db.db`/`.db-shm`
as candidate images → `BITMAP_ERROR` warnings. Fix: `images/` and `sfm/`
as sibling dirs under `frames/<name>/`.

## 8. Asset browser gap (UI)
The Assets panel showed only a comma-separated string. No click-to-view,
no delete. Fixed by:
- Backend: `do_DELETE` handler at `/api/assets/<name>`
- Frontend: `ASSET_ROW` template with View/Delete buttons
- Styles: `.asset-row` LunaV-family glass rows
