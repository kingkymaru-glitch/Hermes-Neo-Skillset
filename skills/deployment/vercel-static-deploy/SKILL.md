---
name: vercel-static-deploy
description: Deploy no-build static HTML to Vercel CLI correctly.
---

# Vercel Static (no-build) Deploy

## When to use
You have a folder of static assets (index.html, *.js, *.css, .wasm, .mind, images) with NO framework build step, and want it on Vercel via `vercel` CLI (not GitHub push-to-deploy). Typical cases: standalone WebAR / A-Frame / MindAR pages, three.js demos, single-file HTML prototypes, QR-or-marker print-sheet generators.

## CRITICAL: framework must be set to "Other"
Vercel's project setting often defaults to a framework (`node` is common), which triggers a build that serves nothing useful for raw HTML. You MUST clear it:

```
npx vercel project update <project-name> --framework "other"
```

Why not put it in vercel.json: the CLI forwards a `framework` key in `vercel.json` to the project-settings API, which only accepts the enum (`nextjs`, `node`, `vite`, `astro`, ...). `"static"`, `"other"`, and `""` are ALL REJECTED there with:
`Error: Invalid request: projectSettings.framework should be equal to one of the allowed values "container, blitzjs, nextjs, ... node, go, services, mastra, ".`
Only `--framework "other"` via the `project update` subcommand clears the preset correctly.

If a deploy ever errors with that enum message, the framework is mis-set — run the `project update --framework "other"` command and redeploy.

## vercel.json (minimal)
```
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "outputDirectory": ".",
  "rewrites": [ { "source": "/(.*)", "destination": "/$1" } ]
}
```
`outputDirectory: "."` serves the repo root as-is. Do NOT add a `framework` key here.

## Deploy
```
npx vercel deploy --prod --yes
```
- Do NOT pass `--name <x>`. `--name` (or a directory not linked to the existing project) makes Vercel CREATE A NEW project instead of updating the existing one — the new project loses your framework="other" setting and serves stale/wrong content. If the project already exists, deploy with no `--name` from the linked directory (uses `.vercel/project.json`).
- The CLI prints a hash URL like `https://webarr-screen-b8qqg1em6-rover-r-3d.vercel.app`. Ignore it for testing (see below).

## Verify the new content actually shipped (the non-obvious part)
1. Hash deployment URLs are NOT publicly testable. Curling `https://webarr-screen-XXXX-rover-r-3d.vercel.app/...` redirects to a Vercel login (`https://vercel.com/login?next=...`). Test the CANONICAL alias instead: `https://<project>.vercel.app`.
2. Hash URLs can all return an identical `data-dpl-id="dpl_..."` (a cached earlier build) regardless of which deployment — so grepping a hash URL for your new marker is misleading and will report "old code". Always grep the canonical alias.
3. Real verification:
```
L=https://<project>.vercel.app
for p in viewer.html setup.html ar-core.js; do
  curl -sL -o /dev/null -w "$p %{http_code}\n" "$L/$p"
done
curl -sL "$L/viewer.html" | grep -c "modelAnchor"   # expect your new marker string
```

## Companion commands
- `npx vercel ls --prod` → lists production deployment hash URLs (these are the non-public ones; use the canonical alias for testing).
- `npx vercel project ls` → lists projects under the team (confirm the real project name).
- `npx vercel inspect <deployId>` → inspect one deployment. NOTE: `npx vercel inspect --prod` is INVALID (no `--prod` flag).
- `.vercel/project.json` shows linked `projectId` / `orgId` / `projectName` — confirms you're deploying to the right place.

## Design tip: keep static apps decoupled
For AR/prototype features, keep the static app in its OWN repo/folder (e.g. `~/webarr-screen`) rather than inside a forked/bespoke Next.js app. It deploys independently, is testable on a phone without the parent app's build pipeline, and the parent app just deep-links into it with query params (`?token=...&sup=...&key=...`). This avoids fighting the parent framework's engine entirely.
