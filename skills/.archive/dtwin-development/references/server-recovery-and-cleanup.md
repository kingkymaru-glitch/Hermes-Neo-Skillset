# DTWIN — server recovery & safe cleanup (from 2026-08-16 session)

## Server gone but web/ + assets intact? server.py was never committed
`~/DTwin/server.py` is NOT tracked in the DTwin git repo (it was a local
untracked file). During the TriniD workspace split it got orphaned/moved, so a
clean state has NO server.py and DTWIN goes dark even though `web/` and
`web/assets/*` are perfectly fine. Do NOT assume the app is broken — recreate
the server.

**Recovery (verified working this session):**
1. If `~/DTwin/server.py` missing, copy `templates/server.py` into `~/DTwin/`.
   It is a stdlib `ThreadingHTTPServer`, ROOT = script dir, port 8753, sends
   COOP/COEP headers (required for gaussian-splats-3d SharedArrayBuffer worker).
2. Launch with **system python**, not homebrew 3.14:
   `cd ~/DTwin && /usr/bin/python3 server.py > /tmp/dtwin_server.log 2>&1 &`
   The `/opt/homebrew/Cellar/python@3.14/.../Python` binary failed silently
   (process exited immediately, no log) — do not use it for the server.
3. Verify: `curl -sI localhost:8753/ | grep -i cross-origin` → both headers;
   `curl -s localhost:8753/web/assets/sample/model.ply` → 200.

**What the DTWIN web app actually needs:** pure static serving of `web/`,
`web/assets/*`, `deployments/*`. `main.js` loads `assets/<name>/model.ply`
(MODEL_URL) + `deployments/<deploy>/tags.json` via fetch — it does NOT use
`/api/assets` or `/api/mesh` (those were an earlier server iteration). So a
minimal static server with COOP/COEP is sufficient; no Flask/SSE needed.

## Cleanup pitfall — `rm -rf` of a transient dir that is TRACKED stages mass deletes
The pipeline transient dirs `frames/`, `train/`, `results/`, `ingest/` are
gitignored in principle, but `frames/` and `train/` were committed earlier, so
`rm -rf frames/ train/ results/ ingest/` does NOT just delete files — it stages
a deletion of every tracked file in those dirs (`git status` shows hundreds of
`D frames/sample/frame_*.jpg`). That leaves the repo in a messy staged-delete
state and a `git status` that looks like you nuked the project.

**Correct cleanup pattern (verified):**
- To remove transient dirs WITHOUT corrupting git: `git rm -r --cached <dir>`
  (untrack) then `rm -rf <dir>` (disk), OR — if they're already tracked and you
  just want disk clean + repo clean — `git checkout -- <dir>` restores the
  tracked files (reproducible; the pipeline regenerates them).
- For a targeted test-artifact removal (e.g. `web/assets/dji_701/`), `rm -rf`
  that specific untracked dir is fine — it's not tracked.
- NEVER `rm -rf` a broad set of pipeline dirs in one command without first
  checking `git ls-files <dir>` to see if they're tracked. If tracked, restore
  with `git checkout -- <dir>` instead of leaving staged deletes.
- The security scan may auto-flag a burst of deletions — that's expected for a
  legitimate cleanup; just confirm the intended dirs.

## Handshake-relevant server note
If a server is up but serving the WRONG assets (e.g. rooted at `~/TriniD`), the
model "disappears" though the file is on disk. Always `lsof -i :8753` +
`pwdx <pid>` to confirm ROOT = `~/DTwin` before concluding a model is missing.
Kill the wrong-rooted instance and relaunch from `~/DTwin`.
