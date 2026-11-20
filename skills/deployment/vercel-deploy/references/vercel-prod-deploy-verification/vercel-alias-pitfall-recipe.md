# Vercel Alias Pitfall — Condensed Recipe (from a real session)

## Environment
- macOS sandbox, Node 24, Vercel CLI 57.0.0.
- Next.js app deployed to `ss-rover-cloud.vercel.app` (project `prj_4CSyQEb29UoKePoaxA5fxkgI4LIT`, team `team_dXOs0u9mPL28Ss0DmAfaBnhl`).
- Vercel + Supabase + Cloudflare R2 SaaS. GitHub: `kingkymaru-glitch/ss-rover-cloud` (private).

## What happened
- Multiple `npx vercel deploy --prod --yes` runs built fine (new build URLs minted, e.g. `ss-rover-cloud-9bazvipr9-rover-r-3d.vercel.app` responded 302, bundle contained the new "Back to all projects" string), but the prod alias `ss-rover-cloud.vercel.app` stayed on a 19-hour-old build (`ss-rover-cloud-6qk68069v`, created Fri Jul 24 15:45).
- CLI consistently failed at the alias step:
  - `Error: fetch failed` at end of `vercel deploy --prod --yes` (and at end of `vercel deploy --prebuilt --prod`).
  - `Error: The deployment https://... is not ready.` from `vercel alias set <build> <domain>`, even after 5–8 retries.
- Root cause: the deploy process was killed mid-promotion (either by session timeout or explicit kill), leaving builds in a permanent "not ready" state so they could never be aliased.

## Exact error strings to recognize
- `Error: fetch failed` (CLI dies at upload/alias promotion)
- `Error: The deployment https://<build>.vercel.app is not ready.` (alias gate)
- `Error: Failed to link <repo>. You need to add a Login Connection to your GitHub account first. (400)` (git connect from CLI — must do in dashboard)
- `Error: The "--prebuilt" option was used with the target environment "production", but the prebuilt output found in ".vercel/output" was built with target environment "preview".` (need `vercel build --prod` before `--prebuilt --prod`)

## Verification commands that worked
- Build artifact contains change: `grep -rl "Back to all projects" .next/static/chunks/*.js`
- Prod alias target: `npx vercel inspect ss-rover-cloud.vercel.app --timeout 20` → read `url` under "General"
- Newest build: `npx vercel ls --limit 3`
- Live domain up: `curl -s -o /dev/null -w "%{http_code}\n" https://ss-rover-cloud.vercel.app/`

## Fix that worked
User connected GitHub in the Vercel dashboard (Settings → Git → Connect GitHub → link `kingkymaru-glitch/ss-rover-cloud`, prod branch `main`). After that, pushes auto-build + auto-promote the alias on Vercel's servers — no CLI alias step. This is the durable fix; the CLI alias hang is environmental.

## Email-mismatch blocker (second session, same project)
After GitHub was connected, Vercel dashboard showed the latest commit as "Blocked" with:
`The deployment was blocked because the commit email <X> could not be matched to a GitHub account.`
- Cause: local `git config user.email` = `kingkymaru@gmai.com` (TYPO, missing 'l'); GitHub verified primary = `kingkymaru@gmail.com`. Vercel matches commit author email against verified GitHub emails.
- The dashboard "Fix Git Configuration" button does NOT rewrite commits — only `git rebase` does.
- Fix applied:
  ```
  git config user.email "kingkymaru@gmail.com"
  git config user.name "MaruTheBlackCat"
  git rebase --root --exec 'git commit --amend --author="MaruTheBlackCat <kingkymaru@gmail.com>" --no-edit'
  git push --force-with-lease origin main
  ```
  Followed by a fresh empty commit (`git commit --allow-empty -m "trigger redeploy" && git push`) to guarantee the GitHub webhook fired, then a dashboard **Redeploy** so Vercel's own pipeline promoted the prod alias.
- Lesson: before expecting Git deploys to succeed, verify `git config user.email` is a VERIFIED email on the connected GitHub account. Use `--force-with-lease` (never blind `--force`) after rewriting history.

## Session lesson
A screenshot from the user ("the home button is not there") was ground truth and caught a deploy that was claimed live but was not. Always run the verification loop before saying "done".

## Email blockers — THREE distinct variants (consolidated)

### Variant 0 — typo in local git email (earlier session)
`git config user.email` = `kingkymaru@gmai.com` (missing 'l'); GitHub verified primary = `kingkymaru@gmail.com`. Vercel "commit email could not be matched". Fix: rewrite authors to the verified email, force-push.

### Variant 1 — GitHub GH007 "push declined due to email privacy restrictions"
Seen after reconnecting GitHub with the corrected author email. GitHub (not Vercel) rejects the push:
```
remote: error: GH007: Your push would publish a private email address.
remote: You can make your email public or disable this protection by visiting:
remote: https://github.com/settings/emails
 ! [remote rejected] main -> main (push declined due to email privacy restrictions)
```
Cause: GitHub setting "Block command line pushes that expose my email" is ON, and the commit author email isn't a GitHub noreply address. The commit author email WAS the Vercel account email (`innovatedmaru@gmail.com`, a verified primary) — so Vercel is happy, but GitHub blocks the push.
Fix (GitHub side, dashboard): Settings → Emails → UNCHECK "Block command line pushes that expose my email". Then the same push succeeds.

### Variant 2 — Vercel account email ≠ commit author email (the real cause this session)
Vercel dashboard shows commit "Blocked" with: `The commit author email (kingkymaru@gmail.com) is not a valid email address.` even though `kingkymaru@gmail.com` IS a verified GitHub email.
Root cause: Vercel matches the commit author against the **Vercel account email** (Vercel dashboard → Account Settings → email), which was `innovatedmaru@gmail.com` — NOT against verified GitHub emails. The "Fix Git Configuration" modal's suggested `git config --global user.email` doesn't help unless that value equals the Vercel account email.
Diagnose both:
```bash
git config user.email                                    # e.g. kingkymaru@gmail.com
gh api user/emails --jq '.[] | "\(.email) verified=\(.verified) primary=\(.primary)"'   # GitHub side
# Vercel account email: ask the user to read Vercel → Account Settings → email (CLI can't read it)
```
Fix: set local git email = **Vercel account email**, rewrite ALL authors, force-push:
```bash
git config user.email "innovatedmaru@gmail.com"
git config user.name "MaruTheBlackCat"
git rebase --root --exec 'git commit --amend --author="MaruTheBlackCat <innovatedmaru@gmail.com>" --no-edit'
# rebase pauses on an EMPTY commit (amend makes it empty): resolve with `git rebase --skip` (drops it) or re-run with --allow-empty
git push --force-with-lease origin main
```
After this, the push triggers a Vercel Git build that succeeds AND auto-promotes the prod alias (no CLI alias step, no dashboard Redeploy needed).

KEY INSIGHT: Vercel's email check is against its OWN account email, not GitHub's. If the user later changes their GitHub primary email, that does NOT change the Vercel account email — keep them aligned deliberately.

## Build-harness false-positive (this session)
The terminal `npm run build` reported `verification_evidence: {status: "passed"}` while the actual command exited `BUILD_EXIT=1` ("Turbopack build failed with 1 errors … Expected '{', got 'interface'"). The harness summary is NOT reliable. Always capture the real exit code:
```bash
npm run build 2>&1 | tail -8; echo "BUILD_EXIT=${PIPESTATUS[0]}"
```
This session's build broke because a `types.ts` edit (via patch against a stale partial file view) injected a duplicate `MarkerStatus` type inside the middle of the `Model3D` interface, so the file no longer parsed. Only the real exit code caught it. When BUILD_EXIT=1, grep the cause: `npm run build 2>&1 | grep -iE "error|Expected|got 'interface'"`.

## DB migration shipping (this session)
New DB columns (markers.kind, markers.geometry_json) were applied to the linked Supabase remote with:
```bash
supabase db push --include-all     # applies supabase/migrations/*.sql; project pre-linked via supabase/.temp/linked-project.json
```
Write idempotent migrations (`alter table if exists … add column if not exists …`); keep `supabase/schema.sql` in sync. Apply BEFORE the app push so the Git deploy doesn't hit a missing-column runtime error.
