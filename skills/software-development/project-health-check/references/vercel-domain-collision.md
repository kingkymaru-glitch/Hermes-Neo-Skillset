# Vercel domain collision — RINA case study

## What happened
Asked to health-check "RINA" (`~/riina`, Vite+React+Supabase). Naively curled
`https://rina.vercel.app` → HTTP 200, title "Rina Luxuries". That is a DIFFERENT app
owned by another Vercel account that grabbed the `rina` host name first. The real RINA
deploy is NOT on `rina.vercel.app`.

Confirmed wrong host:
  - `rina.vercel.app` → "Rina Luxuries" (wrong)
  - `www.rina.vercel.app` → 200 but redirects to the same wrong app
  - `app.rina.vercel.app` → 000 (no DNS)
  - `riina-app.vercel.app`, `rina-office.vercel.app` → 404

Real deploy (found via the repo, not by guessing the host):
  - `~/riina/.vercel/project.json` → projectName "riina", orgId "team_dXOs0u9mPL28Ss0DmAfaBnhl" (team "Rover R-3D")
  - `npx vercel ls` in the repo lists the real URLs:
    `riina-<hash>-rover-r-3d.vercel.app` (preview deploys, all HTTP 200).

## Rule
NEVER report a project's status off a guessed `<name>.vercel.app` host. Another account
may own that exact host. Find the real deploy URL from the repo:
  - `cat <repo>/.vercel/project.json` → projectName / projectId / orgId
  - `cd <repo> && npx vercel ls` → real deployment URLs
  - OR curl the candidate host and check `<title>` for a mismatch.
Same trap applies to `www.` / `app.` subdomains — they 404/000 or point elsewhere.
