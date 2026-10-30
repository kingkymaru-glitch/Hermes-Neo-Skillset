# Reference: ss-rover-cloud Vercel alias-promotion hang (session 2026-07-25)

## Environment
- macOS sandbox, Next.js app at ~/Documents/ss-rover-cloud, prod domain ss-rover-cloud.vercel.app.
- Vercel CLI 57.0.0, Node 24. Vercel auth via browser session (NO stored token in ~/.vercel, no VERCEL_TOKEN env).
- Standing workflow (user-approved): after each code change → build → git commit → git push → `vercel deploy --prod`.

## What happened (recurring)
1. Made UI changes (Home/Back/Delete buttons) on the 3D twin page. `npm run build` passed. Committed + pushed to GitHub.
2. `npx vercel deploy --prod --yes` minted new build URLs repeatedly (e.g. `ku9qevwai`, `iwnbbrv7h`, `9bazvipr9`, `gphb82jk0`) — all responded 302 and their `.next/static` chunks contained the new strings.
3. BUT `npx vercel inspect ss-rover-cloud.vercel.app` kept reporting the SAME 20-hour-old build `6qk68069v` as the alias target. The new builds were never promoted.
4. CLI symptoms observed:
   - `deploy --prod` died with `Error: fetch failed` after "Uploading [====] (3.2MB/3.2MB)" / "Building…".
   - `vercel alias set <newbuild> <domain>` → `Error: The deployment ... is not ready.` — even after 8–10 retries with sleeps, even though the build returned 302.
   - Killing the deploy CLI mid-promotion (SIGTERM) left the build permanently "not ready" (could never be aliased afterward).
5. User screenshot confirmed: live site still showed the OLD nav (no Home/Back), proving the alias never moved despite "build OK" and the new build being reachable.

## Root cause
The CLI's production alias-promotion network step fails in this environment (fetch errors / stuck readiness gate). The CLI cannot complete the promote, and `vercel ls` only lists CLI deploys, not Git deploys.

## Resolution path that worked (partial — user took the final step)
- `npx vercel git connect <repo>` FAILED: "You need to add a Login Connection to your GitHub account first." → Git link must be done in the Vercel DASHBOARD (browser OAuth), not CLI.
- User connected GitHub in dashboard (Settings → Git). Vercel then read the latest commit (proved by a dashboard "Blocked" with email mismatch).
- Email mismatch: local `git config user.email` = `kingkymaru@gmai.com` (TYPO, missing 'l'); GitHub verified primary = `kingkymaru@gmail.com`. Vercel blocked deploy: "commit email could not be matched to a GitHub account."
- Fixed: `git config user.email "kingkymaru@gmail.com"`, `git config user.name "MaruTheBlackCat"`, then `git rebase --root --exec 'git commit --amend --author="MaruTheBlackCat <kingkymaru@gmail.com>" --no-edit'`, then `git push --force-with-lease origin main`.
- After email fix + push, the Git-connected pipeline is what promotes the alias — NOT the CLI. The final dashboard "Redeploy" / auto Git deploy is what flips the prod domain. (Session ended with user about to click Redeploy; CLI could not finish it.)

## Key takeaways
- Never trust CLI exit code / "build OK" for Vercel prod — verify the alias target with `vercel inspect <domain>` and, for UI, a screenshot via vision_analyze.
- When the alias won't move from the CLI: connect GitHub in the dashboard and let Vercel's own pipeline promote. The CLI alias command is unreliable here.
- Always check `git config user.email` matches a VERIFIED GitHub email before expecting Git deploys to succeed.
- `--prebuilt` requires `vercel build --prod` (not plain `vercel build`) or it errors with target-environment mismatch.
