# SOP: Rename a Vercel-deployed SaaS PROJECT (cross-surface)

Scope: the Vercel PROJECT name (the URL slug, e.g. `rover-r-3d` → `lunavsolution`).
Renaming the TEAM/account name is cosmetic and needs NONE of this.

Proven on `ss-rover-cloud` → `lunavsolution` (2026-07-28). After the dashboard
rename, do these in order. The dashboard rename itself does NOT propagate anything.

## 0. Grep every surface for the old name FIRST (one pass)
```
search_files  pattern:  ss-rover-cloud\.vercel\.app|ss-rover-cloud\.git|kingkymaru-glitch/ss-rover-cloud|~/Documents/ss-rover-cloud|SS Rover
```
Run it against (a) the repo root and (b) the Obsidian vault (`~/Documents/obsidian_maru_1`).
This reveals every string you must rewrite before you touch anything.

## 1. Repo-internal strings (commit + push)
- `r2-cors.json` → `AllowedOrigins`: old `…vercel.app` → new `https://<new>.vercel.app`.
  Keep `http://localhost:3000` + `http://localhost:3210`.
- `package.json` + `package-lock.json` → `"name"` (cosmetic npm name; does NOT drive URL).
- Branding strings the rename can leave stale:
  - `supabase/functions/notify-admin/index.ts` — email `from:` / subject prefix
    (e.g. `"SS Rover Cloud"` → `"LunaV Solutions"`).
  - SQL migration comments referencing the old name.
  - `README.md` architecture table (R2 bucket note, deploy notes).
- Build must stay green: `npm run build` (check BUILD_EXIT). Commit + `git push origin main`.

## 2. Cloudflare R2 CORS — RE-APPLY to the bucket (dashboard or CLI)
Editing `r2-cors.json` is NOT enough; the live bucket config must be re-pushed.
- Dashboard: R2 → bucket → Settings → CORS Policy → paste corrected JSON → Save.
  (The saved JSON is exactly the file content from step 1.)
- CLI: `aws s3api put-bucket-cors --bucket <bucket> --cors-configuration file://r2-cors.json --endpoint-url https://<acct>.r2.cloudflarestorage.com`
- WARN: the committed CORS origin may already be STALE vs the real live URL
  (here the file said `ss-rover-cloud.vercel.app` but prod was `rover-r-3d.vercel.app`).
  Trust the new target, but verify the live bucket allowlist once.
- If you want zero-downtime, add BOTH old + new origins to the bucket during transition.

## 3. Supabase dashboard — redirect URLs (NOT in repo)
Auth → URL Configuration → Redirect URLs. Add `https://<new>.vercel.app/**`
if the old domain is listed. Same for Site URL. Repo grep will NOT find these.

## 4. GitHub repo rename — flags matter
```
gh repo rename lunavsolution -R kingkymaru-glitch/ss-rover-cloud -y
git remote set-url origin https://github.com/kingkymaru-glitch/lunavsolution.git
```
- `gh repo rename <new>` with NO `-R`/`-y` FAILS with a usage error
  (`fatal: not a git repository` if run outside a repo, or the usage banner).
  From inside the repo you still need `-y` to skip the confirm prompt.
- After rename, `git remote -v` must show the new URL or pushes go to a dead name.

## 5. Obsidian vault sync (the user's PRIMARY update surface)
Grep the vault (step 0) and patch every hit:
- `Projects/SS Rover Cloud.md` — all `ss-rover-cloud.vercel.app` URLs → new domain;
  tick the "R2 CORS allows <new>" checkbox; update the Supabase redirect pending item.
- `VAULT MAP.md` — live URL line.
- `HermesKeyMemories.md` — add GitHub `<new>` + live URL to the product line.
- `GITHUB.md` — add a repo line `https://github.com/kingkymaru-glitch/<new>`.
Keep `~/Documents/ss-rover-cloud` folder references AS-IS unless step 6.

## 6. Local folder name — DO NOT rename live
Renaming `~/Documents/ss-rover-cloud` while a dev server runs breaks the server
and every `~/Documents/ss-rover-cloud` path in the vault. Leave the folder name
unless the user explicitly asks; if you must, stop the dev server first, `mv`,
then update all vault paths.

## 7. Verify
- `npm run build` green + pushed (Vercel auto-promotes via Git integration).
- Open `https://<new>.vercel.app` — loads.
- Do an ACTUAL R2 model/photo upload from the new URL — confirms CORS applied.
- Click a sample `/share/<token>` link under the new domain — confirms portals resolve.
- Supabase magic-link / redirect tied to the old domain must not silently fail.
- Project ID (`prj_...`) is UNCHANGED — API integrations keyed on it keep working.
