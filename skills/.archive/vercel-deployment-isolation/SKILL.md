---
name: vercel-deployment-isolation
description: "Duplicate repo for isolated Vercel white-label deployments."
---

# Vercel Deployment Isolation

## Trigger
- Vercel project builds from the wrong branch despite repo connection
- Need a white-label/deployment that must not touch the live project
- Vercel UI does not expose branch selection clearly
- Authentication wall or edge 404 persists even after disabling deployment protection

## Why this exists (captured automatically)
Auto-captured after a hard multi-step solve. Reuse instead of re-deriving.

## Core Pattern
When in doubt, **duplicate the repo** and point Vercel at the copy. This removes branch-config ambiguity and isolates the deployment completely.

## Steps
1. Mirror the canonical repo to a new repo under the same account:
   - `git clone --mirror <canonical-repo>`
   - `cd <repo>-mirror.git`
   - `git push --mirror https://github.com/<account>/<new-repo>.git`
2. Clone the new repo locally:
   - `git clone https://github.com/<account>/<new-repo>.git`
   - `cd <new-repo>`
   - `git checkout <feature-branch>`
3. Set identity defaults in the new repo:
   - Update `.env.example` to the target app mode
   - Rename `package.json` name if desired
   - Update hardcoded branding/links to the new app name
4. Push to the new repo:
   - `git add -A`
   - `git commit -m "chore: identity defaults for <app-name>"`
   - `git push origin <branch>`
5. In Vercel:
   - Create new project from the new repo
   - Select the correct branch during import
   - Add env vars with `visibility: config`
   - Disable Vercel Authentication if public access is needed
   - Deploy

## Verification
- Curl the canonical alias: `curl -sL https://<project>.vercel.app | head`
- Confirm the page title/body shows the new app name, not the old one
- Confirm the source in Vercel Deployments shows the correct branch

## Pitfalls
- Vercel Git page may not show branch selection; if the wrong code ships, delete and recreate the project
- Hash deployment URLs are often behind auth; test the canonical alias instead
- `.env*` files must remain in `.gitignore`; do not copy secrets into the new repo
- After rebranding, search the codebase for old hardcoded names/links/domains
- Disconnecting/reconnecting a repo in Vercel does not always prompt for branch selection

## When NOT to use
- If the existing Vercel project already shows the correct branch and you only need a config/env change, just update env vars and redeploy
- For one-off static prototypes, use `vercel-static-deploy` instead

## Evidence
- Verified ARRAS isolation via `kingkymaru-glitch/ARRAS` from `kingkymaru-glitch/lunavsolution`
- Vercel URL `arras-seven.vercel.app` showed LunaV landing until repo was duplicated and rebranded
