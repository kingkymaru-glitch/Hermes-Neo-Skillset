# Vercel `--prod` deploy hang + recovery (observed, recurring)

## Symptom
`npx vercel deploy --prod --yes` completes the build and upload but hangs forever on
alias promotion. The terminal never returns. Foreground calls time out at 600s;
backgrounded ones run 30+ minutes. Meanwhile a NEW deployment URL
`https://<project>-<random>-<scope>.vercel.app` was already minted.

## How to detect without waiting
```bash
# 1. Did the build actually include your change? Grep the compiled client bundle:
grep -rl "known-string" .next/static && echo BUNDLE_OK

# 2. List recent deployments — a fresh <random> URL means the build finished:
npx vercel ls --limit 3

# 3. Live check on the prod alias (does NOT depend on the hung CLI):
curl -s -o /dev/null -w "prod: %{http_code}\n" https://<project>.vercel.app/
```

## Recovery sequence
1. Deploy in background, never foreground:
   terminal(background=true, notify_on_complete=true):
     cd <repo> && npx vercel deploy --prod --yes 2>&1 | tail -5
2. If stuck (process poll still "running" after many minutes AND a new URL is minted),
   KILL it: process(action=kill, session_id=<stuck_id>)  # SIGTERM
   NOTE: killing orphans the build — that URL fails alias with "deployment is not ready".
3. Run a FRESH `npx vercel deploy --prod --yes` (background) and let it finish
   uninterrupted. OR after a clean completed deploy, promote explicitly:
   # macOS has NO `timeout` binary — do NOT use `timeout 90 ...`
   npx vercel alias set <ready-build-url> <prod-alias>
   (The alias step can also hang — same kill + curl-verify pattern.)
4. Confirm live with curl BEFORE telling the user it's done:
   curl -s -o /dev/null -w "%{http_code}\n" https://<project>.vercel.app/

## Pitfalls
- `--prebuilt` fails ("no prebuilt output found in ./.vercel/output") unless you ran
  `vercel build` first. Not a usable shortcut here.
- macOS lacks GNU `timeout`; use background terminal + process(wait/poll).
- A killed `vercel deploy --prod` leaves a "not ready" build — alias it and you get
  `Error: The deployment ... is not ready.` Re-deploy cleanly instead.
- The CLI exit code is unreliable when it hangs; verify via curl, not the process exit.
