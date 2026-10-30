---
name: vercel-deploy
description: Deploy to Vercel and troubleshoot when the production domain never updates. Use when running `npx vercel deploy --prod`, when the build succeeds but the prod URL (e.g. yourapp.vercel.app) still serves old code, when Vercel shows a Blocked deployment with an email-mismatch error, or when the user reports "my changes aren't live on Vercel." Covers the CLI alias-promotion hang and the Git-connection fix.
---

# Vercel Deploy & Alias Promotion

## When to use
- Deploying any project to Vercel (`npx vercel deploy --prod --yes`).
- The build mints a new URL but the production domain still serves OLD code.
- Vercel dashboard shows a deployment "Blocked" with an email-mismatch error.
- User says "I pushed/deployed but the changes aren't there" / "the button isn't showing."

## Standard deploy (often works for static sites)
For Vite/React built to `dist/`: `npm run build && npx vercel deploy --prod --yes`. Usually completes in <30s; the auto-generated URL is live immediately. No custom-domain alias step needed.

For Next.js the same command works ONLY if the prod alias promotion succeeds — see PITFALL.

## PITFALL — CLI alias promotion hangs / fails (Next.js + custom prod domain)
In sandboxed/CLI environments, `npx vercel deploy --prod --yes` builds successfully and mints a new build URL (e.g. `yourapp-xxxx-rover-r-3d.vercel.app`) but then HANGS at the alias step and dies with:
- `Error: fetch failed` (during the Uploading/alias phase), or
- later `vercel alias set <build> <domain>` → `Error: The deployment ... is not ready.`

Symptom: `npx vercel inspect <domain>` → `url` STILL points to a much older build. The new build responds (curl → 302/200) and its bundle contains your change, but the domain doesn't serve it. Retrying `vercel alias set` 10+ times against a fully-built, 302-responding deployment STILL reports "not ready" — this is an environmental readiness gate the local CLI cannot pass. Killing the CLI mid-promotion leaves the build permanently "not ready" and unusable for aliasing.

### Fix — let Vercel's OWN pipeline promote the alias (Git connection)
1. Vercel dashboard → Project → Settings → Git → Connect GitHub (browser OAuth — only the USER can do this; the CLI cannot). Link the repo, set Production Branch = `main`.
2. Fix the commit-email mismatch if Vercel shows "Blocked" (see next PITFALL).
3. Push a fresh commit (or click **Redeploy** on the latest deployment in the dashboard). Vercel's Git pipeline builds AND auto-promotes the prod alias — no CLI alias step.
4. Verify with `npx vercel inspect <domain>` (alias `url` should now be the new build) and curl the domain.

NOTE: `npx vercel git connect <url>` fails with "You need to add a Login Connection to your GitHub account first." That OAuth must happen in the dashboard, not the CLI.

## PITFALL — Blocked deployment, commit email not matched to GitHub account
Vercel rejects Git deploys when the commit author email is not a verified email on the connected GitHub account. Most common cause: a local `git config user.email` typo.

Diagnose:
```
git config user.email                 # local value, e.g. kingkymaru@gmai.com (typo)
gh api user/emails --jq '.[] | "\(.email) verified=\(.verified) primary=\(.primary)"'
```
In one session the local email was `kingkymaru@gmai.com` (missing an 'l') while GitHub's verified primary was `kingkymaru@gmail.com` — Vercel blocked every deployment until fixed.

### Fix
```
git config user.email "correct@email.com"
git config user.name "GitHubUsername"
# rewrite author on ALL commits
git rebase --root --exec 'git commit --amend --author="GitHubUsername <correct@email.com>" --no-edit'
git push --force-with-lease origin main
```
After that Vercel matches the commits and deploys. (Use `--force-with-lease`, never blind `--force`, when history was rewritten.)

## Verification checklist (don't trust the CLI exit code)
- `npm run build` passes; for the repo standard also `npm run lint`.
- New build URL minted: `npx vercel ls --limit 3`.
- Confirm the prod alias actually moved: `npx vercel inspect <domain> --timeout 20 | grep -i url` — compare the build hash to the one you just deployed.
- For an SPA, the domain HTML won't contain your change (client-rendered). Instead grep the built chunk: `grep -rl "unique string from your change" .next/static/chunks/` (Next.js) or `dist/assets/`.
- If the user says "it's not there," request a screenshot and run `vision_analyze` on it to confirm the ACTUAL served nav/build before claiming success. This caught a 20-hour-stale deploy that the CLI reported as "ready."

## References
- `references/alias-promotion-hang.md` — condensed transcript of the ss-rover-cloud session where this recurred across 4 builds / 20+ alias retries, plus the exact resolution steps.
