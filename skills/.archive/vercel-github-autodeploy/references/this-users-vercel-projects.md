# This user's Vercel projects (Git auto-deploy from `main`)

Source of truth: `~/Documents/obsidian_maru_1/GITHUB.md` and `GEMINI R-TESSERA CEO.md`.

## Author convention (CRITICAL for auto-deploy to fire)
- Vercel webhook / build is tied to commits authored as **`kingkymaru@gmail.com`**.
- Repo `user.email` is already `kingkymaru@gmail.com`; if you override the author
  (e.g. `hermes@local`) the deploy webhook does NOT fire and live stays stale.
- When you must override: `git -c user.name=maru -c user.email=kingkymaru@gmail.com commit ...`
- GitHub account: `kingkymaru@gmail.com`. Vercel owner account: `inventedmaru@gmail.com`.

## Known auto-deploy projects (push `main` = live)
- **R-Tessera** — repo `~/Documents/R-Tessera`, GH `kingkymaru-glitch/R-Tessera`,
  live https://r-tessera.vercel.app, projectId `prj_DiBzTVO0zSDSqtWYfNyb0MCD5B8L`,
  team `team_dXOs0u9mPL28Ss0DmAfaBnhl`. Build: `npm run build`, out `dist`, framework `vite`.
- **RINA** (`kingkymaru-glitch/riina`) — Vercel auto-deploy from main.
- **LUNAV Solutions** (`kingkymaru-glitch/lunavsolution`) — live https://lunavsolution.vercel.app,
  auto-deploy from main.

## Verify-after-push recipe (curl, no browser)
1. `sleep 25`
2. `curl -s -o /dev/null -w "%{size_download}" https://<site>/<asset>`  (compare to local `dist/`)
   - R-Tessera: `submarine-cables.json` full = 736516 B (718 routes); partial/filtered = 665094 B.
3. `curl -s https://<site>/ | grep -o 'assets/index-[A-Za-z0-9]*\.js'` — new hash = new deploy.
4. If unchanged → webhook didn't fire → check commit author, re-push.

## Notes
- `vercel` CLI not installed globally (permission-blocked); install locally `npm i -D vercel`
  and run `./node_modules/.bin/vercel ...` only if Git link is absent or preview needed.
- SPA rewrite means a missing asset returns `index.html` (200, ~500 B), NOT 404 — always
  check byte size, never "HTTP 200" alone.
