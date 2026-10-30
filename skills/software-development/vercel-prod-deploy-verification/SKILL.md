---
name: vercel-prod-deploy-verification
description: Deploy a Next.js/Vite app to Vercel production AND VERIFY the live domain actually serves your new code. Covers the silent failure where "vercel deploy --prod" builds successfully but the production alias never reassigns (domain keeps serving OLD code), the "fetch failed" / "deployment not ready" alias gate, why the GitHub to Vercel Git integration is the durable fix, and the verification loop that proves a deploy is truly live. Trigger any vercel deploy, production deploy, "changes are not showing on the live URL", "I deployed but the site is old", manually attaching a Vercel domain alias, or wiring GitHub to Vercel.
---

# Vercel Production Deploy Verification

The build passing and the commit being pushed do NOT mean the live domain serves your change. On Vercel, a deploy has two stages: (1) build + upload produces a unique build URL like `app-xxxx-rover-r-3d.vercel.app`; (2) alias promotion attaches the production domain (`yourapp.vercel.app`) to that build. Stage 1 can succeed while stage 2 silently fails, leaving the public URL on a build from hours or days ago. This is the number-one way to falsely tell the user "it's live" when it isn't.

## The trap (seen repeatedly in sandboxed/macOS CLI environments)
- `npx vercel deploy --prod --yes` prints `Production https://app-XXXX.vercel.app` and `Building…`, then the process hangs at the alias step or exits with `Error: fetch failed` or `Error: The deployment … is not ready`.
- The new build URL responds (curl returns 302/200) and grep confirms your new string is in its bundle, but `yourapp.vercel.app` STILL serves the old build.
- Retrying `vercel alias set <new-build> <domain>` fails with `Error: The deployment … is not ready` even after many attempts, because the parent deploy CLI was killed mid-promotion and Vercel left that build in a permanently "not ready" state.

Symptom the user reports: they open the live URL and the new button/feature/color is simply not there. They are right. Do not argue. Verify.

## Verification loop (do this BEFORE saying "done")
1. Confirm the build artifact contains your change: `grep -rl "your-new-copy-string" .next/static/chunks/*.js` (Next) or `dist/assets/*.js` (Vite). If not found, the build did not pick up your edit — stop and rebuild.
2. Find what the prod alias actually points to: `npx vercel inspect yourapp.vercel.app --timeout 20` and read the `url` line under "General". Compare the hash to your latest build URL.
3. `npx vercel ls --limit 3` shows the newest build URL at the top.
4. `curl -s -o /dev/null -w "%{http_code}\n" https://yourapp.vercel.app/` (auth-gated apps return 302 — that means the server is up; the point is the code it serves).
5. Only claim success when `vercel inspect` shows the prod alias `url` equals your latest build hash AND, ideally, you confirm the feature visually. A screenshot from the user is ground truth — trust it over your CLI output.

## Durable fix: GitHub to Vercel Git integration
The alias hang is an environment/CLI issue, not a code issue. The robust fix is to let Vercel build and promote on its own servers via Git:
- In the Vercel dashboard: Project -> Settings -> Git -> Connect GitHub -> authorize the correct account -> link `owner/repo` -> set Production Branch = `main`.
- After that, every `git push` to `main` auto-builds AND auto-promotes the alias reliably — no flaky local CLI alias step.

CLI-only blocker: `npx vercel git connect <url>` fails with `Error: Failed to link … You need to add a Login Connection to your GitHub account first. (400)`. This is a browser OAuth step the user must do in the Vercel dashboard — you cannot complete it from the CLI. Hand the user the exact dashboard steps and wait for them to confirm.

## LOCAL-FIRST GATE (user standing rule, ss-rover-cloud — REVERSED 2026-07-26)

> **REVERSED by the user on 2026-07-26:** *"stop with this local dev only
> thing… make changes directly push to GH, no localhost drama."* The user
> wants speed — after a green `npm run build`, push `git push origin main`
> directly, SKIPPING the local visual-OK step. The deploy mechanism (Git
> integration auto-promotes the alias) is unchanged; only the pre-push
> sign-off is now optional. **Do NOT silently re-impose the local-visual-OK
> requirement once reversed — that is exactly what the user told us to stop.**

(Original gate text, kept for when the user flips back: build locally —
`cd ~/Documents/ss-rover-cloud && npm run dev -- --port 3210` — confirm
`curl …/localhost:3210/ → 200`, `npm run build` BUILD_EXIT=0, get the
USER's visual OK, THEN `git push origin main`.)

## PITFALL — Commit-author email mismatches Vercel (two distinct failures)
Vercel compares the **commit author email** against accounts it knows. There are TWO different blocks, both seen this project:

### Variant A — GH007: "Your push would publish a private email address" / "email privacy restrictions"
GitHub REJECTS the push (not Vercel). Cause: GitHub's "Block command line pushes that expose my email" rule, combined with a commit author email that isn't a GitHub noreply address. Fix is in GitHub, not Vercel:
- GitHub → Settings → Emails → uncheck **"Block command line pushes that expose my email"**.
- (The commit author email should be a verified primary on the GitHub account; here that was `innovatedmaru@gmail.com`.)
This is separate from the Vercel-side block below — you may need to fix BOTH.

### Variant B — Vercel "commit email could not be matched" / "not a valid email address"
Vercel BLOCKS the deploy (red "Blocked" alert). The local `git config user.email` does NOT equal the **Vercel account email** (Settings → Account → email), even if it IS a verified GitHub email. In this project the Vercel account email was `innovatedmaru@gmail.com` while commits were authored `kingkymaru@gmail.com` — both valid, but Vercel only checks against its OWN account email. The "Fix Git Configuration" dashboard button does NOT rewrite commit authors.
Diagnose both sides before rewriting:
```bash
git config user.email                                    # what commits use
npx vercel inspect <domain> 2>/dev/null | head         # (or ask user for Vercel account email)
gh api user/emails --jq '.[] | "\(.email) verified=\(.verified) primary=\(.primary)"'
```
Fix: set local git email to the **Vercel account email**, rewrite ALL commit authors, force-push:
```bash
git config user.email "vercel-account-email@example.com"
git config user.name "GitHubUsername"
git rebase --root --exec 'git commit --amend --author="GitHubUsername <vercel-account-email@example.com>" --no-edit'
git push --force-with-lease origin main
```
CAUTION: `git rebase --root --exec` aborts on an EMPTY commit (the amend makes it empty) — the rebase pauses. Resolve with `git rebase --skip` (drops the empty commit) or `--allow-empty` on that step, then continue. Always `--force-with-lease`, never blind `--force`.
After the push, Vercel's Git pipeline builds AND auto-promotes — no CLI alias step. A no-op `git commit --allow-empty -m "trigger redeploy"` after the rebase guarantees GitHub fires the webhook if the force-push alone doesn't.

## PITFALL — Do NOT trust the build-harness summary
The terminal build tool can report `verification_evidence: {status: "passed"}` while the real build exited non-zero (e.g. `BUILD_EXIT=1`, "Turbopack build failed"). A corrupted source file (e.g. a mid-interface duplicate type from a partial-view patch) fails the build but the harness may still claim pass. Always check the actual exit code: `npm run build 2>&1 | tail -6; echo "BUILD_EXIT=${PIPESTATUS[0]}"`. If 1, grep the real error (`grep -iE "error|Expected|got 'interface'"`).
This session: a `types.ts` edit applied against a stale partial view duplicated `MarkerStatus` inside the `Model3D` interface, breaking the build — only caught by reading the exit code, not the harness summary.

## PITFALL — Vite SPA builds GREEN with UNSET `VITE_*` env (silent runtime failure)
A Vite/React SPA build SUCCEEDS even when `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY`
are not set in Vercel — Vite just inlines empty strings into the bundle. The app
loads, but every auth/DB call fails silently at runtime (no exception, just dead
buttons / infinite "Loading"). This is a DIFFERENT failure from a stale bundle: the
bundle grep shows your new code is live, yet the feature doesn't work because the
client has no backend URL.
- The env vars must be set in the Vercel dashboard (Project → Settings → Environment
  Variables) for the DEPLOYED build. `.env.local` only covers local dev. There is no
  Vercel CLI/token in this environment, so this is a manual dashboard step the agent
  CANNOT complete — hand the user the exact key/value pairs and ask them to redeploy.
- After they add env vars, Vercel must REBUILD (env changes don't apply to an already
  built deployment) — a push or "Redeploy" triggers it.
- **Harden the client so a missing env shows a message, not a blank crash.** A Vite SPA
  that does `createClient(import.meta.env.VITE_SUPABASE_URL, ...)` with empty strings
  THROWS at module import (`supabaseUrl is required`) → the whole React tree never mounts
  → blank white page. This bit RINA: the user saw a white screen + DevTools error
  `supabaseUrl is required` / `Missing VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY`.
  Fix in `src/lib/supabase.ts`: if `url && anonKey` are absent, build a placeholder client
  (`createClient('https://placeholder.supabase.co','placeholder-anon-key', …)`) and export
  `SUPABASE_CONFIGURED=false`; App renders a "Backend not configured — set
  VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY in Vercel → Settings → Env, then redeploy"
  screen instead of crashing. This turns a silent white-screen into an actionable message
  AND keeps `npm run build` green (no import-time throw).
- **PITFALL — Vite `vite build` uses esbuild: NO type-check, so undefined references pass build and crash at runtime.** `vite build` strips TS types and does NOT resolve identifiers. A referenced-but-undefined symbol compiles cleanly and only throws in the browser. This session: a data-layer refactor left `onClick={submitNewUser}` in AdminPanel while `submitNewUser` was never redeclared → `npm run build` was GREEN, but clicking "Create user" threw `ReferenceError: submitNewUser is not defined`. The harness `verification_evidence: passed` was false comfort because esbuild never checked the reference.
  - **Always run `npx tsc --noEmit` (or `npm run lint`) before declaring a refactor done** on a Vite+React+TS app — it catches dangling references, missing props, and wrong signatures that `vite build` silently ignores. Add it to the pre-push checklist.
  - If you can't type-check, at minimum LOAD the page and exercise the changed path; a blank white screen or console `ReferenceError` is the tell.
- Related: the multi-tenant Supabase pattern (org-scoped tables + `on_auth_user_created`
  host; if it's an empty string / `undefined`, the env wasn't injected. (For a
  backend-backed SPA this is the complement to the bundle-grep: that proves the BUILD
  is new; this proves the build was BUILT WITH the right env.)
- Related: the multi-tenant Supabase pattern (org-scoped tables + `on_auth_user_created`
  trigger) and the Vercel env gap are covered together in `supabase-r2-saas` →
  references/multitenant-vite-supabase.md.

## Shipping DB migrations with the deploy
New DB columns must exist before the app that uses them goes live.

**PROJECT-SPECIFIC (ss-rover-cloud) — `supabase db push` is UNUSABLE here.** The Supabase project is NOT linked locally (no token in `.env.local`), and Vercel does NOT run migrations on deploy. So every schema change for THIS repo must be applied MANUALLY: write an idempotent, guarded SQL file in `supabase/migrations/` (use `add column if not exists`, `create or replace function`, `if exists` guards so it is safe to re-run), then the USER pastes it into the Supabase dashboard → SQL Editor → Run. Keep the file committed so the change is documented and re-runnable. (For OTHER projects where the CLI IS linked, `supabase db push` works — see the NOTE below.)

For linked projects, apply migrations with:
```bash
supabase db push --linked      # applies only NEW supabase/migrations/*.sql to the linked remote
```
NOTE — `--include-all` DOES exist and is the FIX when `db push` holds back a
migration. Normally `supabase db push` diffs against the remote
`_supabase_migrations` table and applies ONLY files not yet recorded (idempotent:
use `create or replace function` / `add column if not exists`). BUT when a NEW
local migration is OUT OF ORDER vs the remote's latest recorded version, the CLI
REFUSES to apply it and asks for `--include-all`. Symptom: `db push` exits 0 yet
the migration is still pending (a re-run still lists it) or the CLI prints
"Use --include-all to apply all migrations". Fix:
```bash
supabase migration list                  # see which local migrations are NOT on remote
supabase db push --include-all --yes     # applies the pending one(s); safe + idempotent
supabase db push --include-all --yes     # re-run -> "Remote database is up to date."
```
`--include-all` only runs files not already recorded; it does NOT re-apply
already-applied migrations. CONFIRMED on CLI v2.109.1 (2026-07-28): applied
`20260728_client_branding.sql`; second run reported "Remote database is up to
date." Write idempotent migrations and keep `supabase/schema.sql` in sync. Apply
BEFORE pushing app code so the Git deploy doesn't hit a missing-column runtime
error. Confirm a new build with `npx vercel ls --limit 1`.

## PITFALL — A green `git push` does NOT guarantee the live bundle is your new code (grep the DEPLOYED JS)
For a Vite/React SPA the HTML is an empty shell that loads a HASHED JS bundle (`assets/index-<hash>.js`). After `git push` + Vercel build there is a lag (often ~1 min; sometimes the build is queued behind others) during which `yourapp.vercel.app` still serves the PREVIOUS bundle. Worse: if the build silently fails or the Git webhook is flaky, the old bundle stays up indefinitely and the user sees none of your changes (e.g. a new "Help" button missing from their screenshot) while you insist "it's deployed."

Definitive check — fetch the deployed bundle and grep it for a marker only your new code contains:
```bash
# 1) find the hashed asset the live HTML points at — MUST re-derive from the LIVE HTML each time
A=$(curl -s https://yourapp.vercel.app/ | grep -oE "assets/index-[a-zA-Z0-9_-]+\.js" | head -1)
echo "live bundle: $A"
curl -s "https://yourapp.vercel.app/$A" -o /tmp/live.js
# 2) NEW-code markers must be PRESENT; OLD/demo markers must be GONE
grep -c "your-new-copy-string"   /tmp/live.js   # expect >=1
grep -c "old-demo-string-to-remove" /tmp/live.js   # expect 0 (no match = good)
```
- **PITFALL — re-derive the asset hash every time, never reuse a prior turn's `$A`.** The live HTML swaps the referenced bundle hash on each deploy. Reusing a stale hash (e.g. an `index-BiY2Syht.js` captured in an earlier turn) silently fetches the OLD bundle and reports "markers present" even when the new build is live — a FALSE PASS. Always re-run the `curl ... | grep -oE` step against the live HTML in the SAME command as the grep, so you never grep a cached asset.
- **PITFALL — the HTML hash swaps ~seconds AFTER the push, so grep immediately and you'll read a stale hash.** Right after `git push`, the live HTML can still reference the PREVIOUS bundle for 5–30s while Vercel propagates the new build + edge cache. A bundle-grep in that window gives a FALSE "markers absent / build not live" reading. Fix: `sleep 5` then re-derive the hash from the live HTML inside the SAME command, and if the new marker is still absent, `sleep 45` and re-grep once more before concluding the deploy failed. The two greps in this session that "failed" were both just pre-propagation reads — re-deriving after a short wait proved the new build was live. Concretely: `sleep 5; A=$(curl -s https://yourapp.vercel.app/ | grep -oE "assets/index-[a-zA-Z0-9_-]+\.js" | head -1); curl -s "https://yourapp.vercel.app/$A" -o /tmp/live.js; grep -c "your-new-string" /tmp/live.js`.
  - **BETTER — poll the hash until it CHANGES instead of guessing a fixed wait.** The propagation delay is variable (5s–60s+, sometimes the build is queued). A fixed `sleep 45` is both too slow when it's fast and too fast when it's slow. Loop on the hash itself and grep only once it flips:
    ```bash
    OLD=$(curl -s https://yourapp.vercel.app/ | grep -oE "assets/index-[a-zA-Z0-9_-]+\.js" | head -1)
    for i in $(seq 1 12); do
      sleep 10
      H=$(curl -s https://yourapp.vercel.app/ | grep -oE "assets/index-[a-zA-Z0-9_-]+\.js" | head -1)
      if [ "$H" != "$OLD" ]; then break; fi   # hash flipped -> new build propagated
    done
    curl -s "https://yourapp.vercel.app/assets/$H" -o /tmp/live.js
    grep -c "your-new-string" /tmp/live.js      # expect >=1 NOW
    ```
    Confirmed 2026-08-13 (Labs content edit): first poll still showed the OLD hash (`index-ObtoTNAt.js`), try 2 flipped to `index-BC_kiNBa.js`, and the new marker grep hit immediately. This also self-confirms the deploy is current (same hash as the local `dist/` build + same byte count = byte-identical), so you KNOW you're grepping the right artifact.
- If the NEW string is missing but the OLD string is present → the deploy did NOT pick up your change (stale build). Wait 45–60s and re-grep; if still stale, the build failed or didn't trigger — check the Vercel dashboard build log / re-push.
- This is more reliable than `vercel inspect` (which can show the alias on a build still propagating) and faster than a screenshot round-trip. Trust the user's screenshot as ground truth too — if they say "I still see the old screen," re-derive the live hash / re-probe the server before claiming fixed.
- Separate concern: bundle-grep proves the BUILD is new. If the build is new but the user STILL sees old content, their BROWSER has stale `localStorage` from a prior build. Don't conflate "build is new" with "browser shows new data." For a localStorage-only (no-backend) prototype, a seed-flag bump alone is NOT enough to clear data already written under the old flag — you must add an explicit legacy-purge keyed to the old flag, then tell the user to HARD-RELOAD (Cmd+Shift+R) once so the new build's purge runs. The full pattern (seed flag + hook fallbacks + seeded-login fallback + hardcoded demo labels/gates + legacy purge) is captured in the `vite-build-verification` skill's `references/localStorage-mock-removal.md`.

## PITFALL — `git push` rejected by a DIVERGENT remote (another workstation/account pushed first)
If `git push origin main` returns `[rejected] main -> main (fetch first)` / "remote contains work that you do not have locally", the remote (`origin/main`) has commits you never pulled — typically because the SAME repo was pushed from a DIFFERENT machine (user edited on their laptop; you're on the desktop). NOT a conflict in your code yet; it's a non-fast-forward. Fix WITHOUT force-push (force-push would clobber their commit):

1. `git fetch origin` then `git log --oneline HEAD..origin/main` to see what's incoming.
2. INSPECT before merging — `git show --stat <sha>` shows which files the incoming commit touched. If it's a different feature (it will be), you want to KEEP it, not overwrite it.
3. `git rebase origin/main` — replays YOUR commit(s) on top of theirs. Conflicts surface only if BOTH commits edited the SAME region.
4. RESOLVE BY KEEPING BOTH edits. Common case (this project): two commits both added a button to the same model-row cluster in `ProjectWorkspace.tsx` — one added a "Replace" (↻) button, yours added a "Transform" (⤢) button. The correct merge keeps BOTH. Mechanically: delete the `<<<<<<<`/`=======`/`>>>>>>>` markers and splice both sides' JSX in. After: `search_files` for `^<<<<<<< |^>>>>>>> |^=======` MUST return 0 hits.
5. `npx tsc --noEmit` — a leftover `</>` or stray marker breaks the TS parse and cascades hundreds of FALSE errors; the real signal is a single "Merge conflict marker encountered" line. Fix the merge, re-check.
6. `GIT_EDITOR=true git rebase --continue` — `GIT_EDITOR=true` stops an interactive editor from hanging the rebase on the commit-message step (a plain `git rebase --continue` can block forever waiting for an editor that never opens in a non-interactive shell). `true` is a no-op editor that accepts the default message.
7. `git push origin main` — now fast-forwards; Vercel auto-builds + auto-promotes on its own servers.

Do NOT `git pull --no-rebase` blindly (makes a merge commit / can duplicate changes), and NEVER `git push --force` here — you'd delete the other machine's commit. Rebase + keep-both is the safe path. Full recipe in `references/git-push-divergent-remote-rebase.md`.

## PITFALL — Changing Vercel Git repo/branch does NOT always update the deploy source
After disconnecting/reconnecting a repo in Vercel, or changing the production branch, the live deploy can still serve old code from the previous repo/branch. The UI may show the new repo name, but the actual Deployment row can still say `Source: main` or the old repo's latest commit.
- After any repo/branch change in Vercel, force a redeploy and verify the Deployment row Source actually changed.
- Then bundle-grep the live URL for a marker that only exists in the new repo/branch. Absence = the deploy is still old, regardless of what the Settings page shows.

## What does NOT work (do not waste turns)
- Repeated `vercel alias set` against a build whose parent CLI was killed — permanently "not ready".
- `vercel deploy --prebuilt` without first running `vercel pull --yes` (needs `.vercel/project.json`).
- `vercel build --prod` then `vercel deploy --prebuilt --prod` can also hit the same `fetch failed` at upload/alias, so prebuilt is not a guaranteed fix in this environment — it only skips the remote build, not the promotion network call.
- Killing the deploy process to "check if it finished" — this is what leaves builds stuck "not ready". Let a deploy run to completion; verify via `vercel inspect`, not by killing.

## Pre-flight for a clean CLI deploy attempt (if Git integration unavailable)
1. `npx vercel pull --yes` (fetch project settings once).
2. `npm run build` (or the app's build) — confirm exit 0.
3. `npx vercel deploy --prod --yes` in background; do NOT kill it.
4. Poll with `vercel inspect <domain>` until the alias `url` flips to the new build hash. If it never flips after a long wait, fall back to asking the user to connect GitHub.

## Communication rule
Never tell the user "it's deployed/live" based only on a green build or a pushed commit. State explicitly: built OK, committed OK, alias points to X (or "alias still on old build — promoting"). If you cannot confirm the alias moved, say so and give the user the GitHub-connect path rather than claiming success.

## PITFALL — "I see no difference" = edits never reached a running instance (multi-project theme/UI pass)
When touching the LOOK of several apps in one session (e.g. syncing a header/theme across LunaV, R-Tessera, Luna-EDGE), the #1 way to falsely tell the user "it's done" is to stop at `npm run build` green. The user judges done by what they SEE in the browser. A green build is invisible until the change is actually LIVE somewhere — and "live" means different things per project type:

- **Vercel-backed (LunaV `lunavsolution`, R-Tessera `R-Tessera`):** the running site only updates on a new production build, which only happens on `git push` to `main` (Git integration auto-builds + auto-promotes). If you edited the file, built, but did NOT `git add -A && git commit && git push`, the deploy never ran and the user saw the old UI. This is the trap that burned a full theme-sync session: three apps were "done" by build alone; none were pushed, so the user saw zero change.
  - Repair: `git -C <repo> add -A && git -c user.name=maru -c user.email=kingkymaru@gmail.com commit -m "..." && git push origin main`. Then WAIT 45–60s and verify the live bundle (see bundle-grep below). The commit-author override is REQUIRED or the Vercel webhook won't fire (see commit-author pitfall).
- **Local-only server app (Luna-EDGE Flask `~/luna-edge`):** the browser talks to a long-lived `python app.py` process. Editing `templates/index.html` does nothing until that process is RESTARTED. If it's still running from before your edit (or you never started it this session), the user sees the old page.
  - Repair: `pkill -f luna-edge/app.py`, then `cd ~/luna-edge && source .venv/bin/activate && python app.py` in background; probe `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000`.
- **Local Vite dev preview (R-Tessera `~/Documents/R-Tessera` for eyeballing):** `npm run dev -- --host` must be (re)started; a stale dev server won't reflect edits. Kill via `lsof -nP -iTCP:5174 -sTCP:LISTEN` → `kill <pid>`, then relaunch background.

Definitive "did it actually change?" loop BEFORE claiming done on a visual pass:
1. For each touched app, confirm the change is in the RUNNING instance, not just the source tree:
   - Vercel: bundle-grep the live JS (re-derive hash each time) for a marker only your new code has.
   - Local Flask: `curl -s http://localhost:8000 | grep -o "your-marker"`.
   - Local Vite: open `http://localhost:5174`, or `curl -s http://localhost:5174/src/App.jsx | grep -o "your-marker"` for dev-served (unbundled) modules.
2. If the marker is absent from the running instance, you skipped the push/restart step — do it, then re-verify.
3. Only then say "done." The user's screenshot is ground truth; if they say "still no change," re-derive the live hash / re-probe the server before claiming fixed.

Hard rule for multi-project UI syncs: **edit → build (check exit) → commit+push OR restart server → verify marker in the running instance → THEN report.** Skipping the push/restart step is the most common reason a "finished" theme pass shows the user nothing.

## "Before vs after — I see no difference" triage (user report)
When the user says the UI didn't change after you claimed done:
1. `git -C <repo> status --short` — if your edits are UNCOMMITTED, you never pushed → commit+push (Vercel) or just commit if local-only.
2. `git -C <repo> log --oneline -1` vs the newest Vercel Deployment row — if local HEAD is ahead and Vercel has no new row, the webhook missed → no-op `git commit --allow-empty -m "trigger redeploy"` + push.
3. For local apps: `lsof -nP -iTCP:<port> -sTCP:LISTEN` — is the server even running, and on the right port/interface? Stale/loopback-only/zombie = restart with `--host`.
4. Browser cache: tell the user to HARD-RELOAD (Cmd+Shift+R) — Vercel edge cache + service-worker/localStorage can serve a stale paint.
5. Re-derive the live bundle hash and grep for your new marker. Absent = not actually deployed/restarted; present = browser cache or wrong URL.

## PITFALL — A green `git push` can SILENTLY NOT TRIGGER a Vercel build (webhook miss), not just a stale alias
The usual failure mode is "build ran, alias lagged." A DIFFERENT, equally real failure is: the commit pushes fine (GitHub shows it, `git log origin/main..HEAD` is empty) but Vercel's Git webhook NEVER fired, so the newest commit has NO deployment at all — the live site stays on a build from days earlier and the user is right that "there's no new deployment." This bit RINA: local HEAD `2eaf580` ("Fix RINA TypeScript build") was committed + pushed, but Vercel's newest prod deploy was `cf37ab2` from 3 days prior. The webhook had simply not fired for that commit.
- **How to catch it (before telling the user it's live):** check whether a deployment row exists for your commit SHA. If the Vercel CLI has been used on this machine, query the API directly (see "BETTER — the Vercel API directly" below) — `source=git` + your SHA + `READY` means it fired; NO row for your SHA means it genuinely missed. Absent a token, fall back to `git log -1 --format='%h %ci %s' HEAD` vs the newest row in the user's Vercel Deployments list; if the Vercel newest-hash ≠ your HEAD hash and is several commits/days older, the build did NOT trigger.
- **Fix — re-fire the webhook with a no-op commit** (Vercel's own recommended "trigger redeploy" pattern; safe, changes no code):
  ```bash
  git commit --allow-empty -m "chore: trigger redeploy to ship <sha-of-real-fix>"
  git push origin main
  ```
  This re-runs the build on the EXACT current code (your real fix), producing a fresh deployment row. (Works because the GitHub→Vercel webhook fires on any new commit to `main`.)
- **PRE-PUSH habit to prevent the miss:** after `git push`, confirm a build appears on Vercel within ~60s. If no new deploy row shows up, assume webhook miss and push the no-op redeploy. Don't wait for the user to notice the gap.
- Distinct from the alias-lag pitfall below: there the build ran but alias lagged; here the build never ran. Both end with "user sees old site," so verify BOTH the build triggered AND the alias moved before claiming live.

## Verify a deploy by COMMIT via GitHub's deployment API (no Vercel token needed)
When the Vercel Git integration is connected, Vercel records a GitHub Deployment per build, so you can answer "did MY commit ship, and did the build succeed?" with no Vercel CLI/token:
```bash
gh api "repos/<owner>/<repo>/deployments?per_page=3" --jq '.[] | {sha: .sha[0:7], env: .environment, created: .created_at, id: .id}'
gh api "repos/<owner>/<repo>/deployments/<id>/statuses" --jq '.[] | {state, created_at, env_url: .environment_url}'
```
A deployment whose `sha` equals your local HEAD with `state: success` IS the proof that commit's production build completed; `env_url` is its build URL. This is the cheapest honest evidence for an AUTH-GATED app, where the live HTML/JS is not greppable without a session.

### BETTER — the Vercel API directly, when the CLI has been used on this machine
The Vercel CLI stores a bearer token at the CLI auth path; if it exists you can query deployments and their `source` outright (this is the definitive webhook-fired check, and it beats both the file-hash guess and the screenshot round-trip):
```bash
# macOS:
TOKEN=$(python3 -c "import json;print(json.load(open('/Users/$USER/Library/Application Support/com.vercel.cli/auth.json'))['token'])")
# then, with the project + team ids from <repo>/.vercel/project.json:
curl -s "https://api.vercel.com/v6/deployments?projectId=<prj_id>&teamId=<team_id>&limit=5" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```
Read per deployment: `source` (`git` = webhook fired, `cli` = manual), `state` (`READY`/`BLOCKED`/`ERROR`), `target`, `meta.githubCommitSha`, `created`/`ready` epoch-ms. `source=git` + your SHA + `READY` is the full proof. `gitCredentialId`/`link` on `GET /v9/projects/<prj_id>` confirms the repo is still connected (and `gitProviderOptions.createDeployments == 'enabled'`).
- **A `BLOCKED` cluster that is OLD is history, not a live fault.** Deployment protection blocks builds during initial project setup; once disabled, later pushes deploy normally. Judge the webhook by the RECENT rows, not by a count of blocked ones.
- **Deployment protection makes per-deployment preview URLs unfetchable** (`curl <slug>-<hash>-<team>.vercel.app/...` returns `302`). That is not a failed deploy — verify against the production alias instead.
- **PITFALL — never probe a prod deploy by curling a chunk filename taken from your LOCAL build.** Next/Vite prod builds emit their own content hashes, so `curl https://<domain>/_next/static/chunks/<local-name>.js` 404s even when the deploy is live and correct — a FALSE NEGATIVE that reads exactly like a failed deploy. Verify by commit (above), or re-derive the asset path from the LIVE HTML; never from `.next/`/`dist/`.
- **PITFALL — in a Next App Router app the landing HTML lists only the ENTRY chunks, so a fix inside a lazy route's component is not in them.** Scanning "every chunk referenced by `/`" reports your fix as ABSENT even when it is deployed, because a big route component (e.g. a workspace/panel) loads in a route-level chunk that `/` never references. Two reliable checks instead: (a) grep the LOCAL build output (`.next/static/chunks/`) for the new string — that proves the build picked up the edit; (b) fetch the chunk that IS referenced from the route you actually changed (e.g. the login chunk from `/login`) to prove the deploy is new. Absence from `/`'s chunk list is NOT evidence of a failed deploy.
- **PITFALL — the `env_url` build URL is usually NOT fetchable (deployment protection).** Vercel serves per-deployment URLs behind authentication unless protection is disabled, so `curl <env_url>/...` returns `302` (sometimes `401`), not your asset. Do not read that 302 as a failed deploy. On an auth-gated app the honest evidence chain is: deployment `sha` == local HEAD with `state: success` + the production root returning 200. Report it exactly that way.
- When the app is auth-gated and you verified by commit, say precisely that — "deployment for `<sha>` = success, UI not visually verified" — instead of implying you saw the new screen.

- **PITFALL — the change lives in a LAZY chunk, so the entry-chunk hash does NOT move.** A Vite SPA with route/component code-splitting emits the edited component as its OWN file (`assets/GlobeView-<hash>.js`) while the entry `assets/index-<hash>.js` can stay byte-identical. Polling the index hash therefore never flips and reads exactly like a failed deploy. Before concluding "not deployed", grep the LOCAL `dist/assets/*.js` for your new string to learn WHICH chunk holds it, then fetch that exact chunk from the live origin. (This session: the Studio link edit was in `GlobeView-*.js`; the index hash was unchanged and nearly caused a false "deploy didn't fire" report.)
- **PITFALL — "the webhook must have missed" is usually a WRONG diagnosis; check the deployments API before believing it.** The tempting story when a live bundle looks unchanged is "the Git webhook silently missed for this repo." Verify it before acting — a webhook-miss and a lazy-chunk misread produce the identical symptom (live bundle looks old) but need opposite responses. This exact false alarm happened on R-Tessera: the bundle appeared unchanged for many minutes of polling, so the webhook was blamed and a manual `vercel --prod` was run — but the API showed the webhook had fired automatically 7 minutes earlier (`source=git`, correct commit, READY). The real cause was polling the entry `index-*.js` hash while the edit lived in the lazy `GlobeView-*.js` chunk. Running a needless manual deploy is harmless but wastes a turn and reports a false fault to the user.
- **Query the deployments API — the token IS available locally** (see "Verify a deploy by COMMIT" below). One call settles webhook-fired vs not: `source=git` with your commit SHA and `state=READY` means it fired; no row at all means it truly missed. Never infer a webhook miss from a file hash.
- Only if the API shows NO deployment for your SHA should you fall back to the manual path — `cd <repo> && vercel --prod --yes` (the project is already linked via `.vercel/project.json`).
- **Multi-repo session habit:** after pushing N repos, verify EACH live origin independently — a green push on all N says nothing about whether all N built. But verify via the deployments API / commit SHA, not by polling a bundle hash; then report per-repo truthfully: deployed + verified, or genuinely no deployment row (webhook missed) + manually deployed.

## PITFALL — Git push auto-promotes (alias lag is usually timing, not failure)
After a force-push / push with the correct commit-author email, Vercel's Git pipeline builds AND auto-promotes the production alias on its own servers — no dashboard click, no CLI `vercel alias` command. This session confirmed it repeatedly (the email-fix push and several later code-fix pushes all flipped the prod alias to the new Git build within ~1 min). The earlier "alias didn't move" readings were FALSE ALARMS: `vercel inspect` was checked before the Git build finished (it was still "Building…").
- After a Git push, WAIT 45–60s, then `npx vercel inspect <domain> --timeout 20` and read the `url` + `created` lines. If `created` is recent (seconds/minutes ago) and the hash matches your latest build (`npx vercel ls --limit 1`), it promoted on its own.
- A failed background `vercel deploy --prod` job does NOT corrupt or move the live alias — the prod domain stays on the last good Git build. Its `Error: fetch failed` / `not ready` is harmless noise; do NOT panic-promote via the dashboard unless `vercel inspect` shows the alias genuinely stale AFTER the wait + re-check.
- Cheap liveness probe for an auth-gated SPA where bundle strings aren't greppable from the initial HTML: curl a STATIC asset you changed. e.g. after swapping `logo.png` for a cropped file or adding `logo.svg`, `curl -s -o /dev/null -w "%{http_code}\n" https://<domain>/logo.png` returns 200 on the NEW build and 404 on the OLD (asset didn't exist) — definitive proof the new build is live without a screenshot. (Hash-named JS/CSS won't work as a probe, but a renamed/replaced static asset in `public/` is a stable probe.)
- **Cheap no-token liveness probe (when no Vercel CLI/token locally — the common case here).** You can't `vercel inspect`, so verify the deploy with plain `curl`:
  ```bash
  # 1) app is actually served (not a Vercel error/404 page that still returns 200)
  curl -s https://<domain> | grep -ioE "<title>[^<]*</title>"   # expect YOUR app title, not a Vercel 404
  # 2) fresh deploy vs cached: x-vercel-cache: MISS => just rebuilt/served new content
  curl -s -I https://<domain> | grep -iE "x-vercel-cache|server"
  # 3) find the REAL prod domain when a guessed slug 404s — probe variants:
  for u in https://<slug>.vercel.app https://<otherslug>.vercel.app; do \
    echo "$u -> $(curl -s -o /dev/null -w '%{http_code}' --max-time 8 "$u")"; done
  ```
  This bit RINA: `riina.vercel.app` 404'd, but `rina.vercel.app` returned 200 with `<title>Rina Luxuries</title>` and `x-vercel-cache: MISS` — proving the new build (from an 8-min-old push) was live without any Vercel token. Use the `<title>` + `MISS` combo as ground truth when you can't query Vercel; trust the user's Deployments screenshot as the second source.
- CONFIRMED SEQUENCE (this session, `ss-rover-cloud` client-branding feature): edit code → `npm run build` (check BUILD_EXIT) → `supabase db push --include-all --yes` (apply new columns BEFORE pushing app; `--include-all` IS valid — applies only not-yet-recorded files, see Shipping DB migrations) → `git push origin main` → wait 45–60s → `npx vercel inspect <domain>` shows alias `url` flipped to the new Git build (auto-promoted, no dashboard click) → `curl <domain>/logo.png` returns 200 (static-asset probe) = definitively live. This full green-path works in this environment; trust it.
  > **CORRECTION (2026-08-04):** the `supabase db push` step above does NOT work for `ss-rover-cloud` — its Supabase project is unlinked (no local token), so that command errors out. The schema-change step for THIS repo is instead: author a guarded `supabase/migrations/<date>_<feature>.sql` and have the USER paste it into the Supabase dashboard → SQL Editor → Run (see "Shipping DB migrations with the deploy"). Everything else in the sequence (build → git push → auto-promote) is unchanged.

## PITFALL — Renaming a Vercel PROJECT changes its .vercel.app URL; team rename does NOT
The dashboard Project Settings > General shows TWO distinct names — do NOT conflate them:
- **TEAM / account name** (center dropdown with an up-arrow next to it): cosmetic only. Renaming it does NOT touch the deployment URL. Safe, no follow-ons.
- **PROJECT name** (editable field on the right): this IS the URL slug. Renaming `rover-r-3d` → `lunavsolution` moves the live site to `lunavsolution.vercel.app`.
When the PROJECT is renamed, Vercel auto-applies nothing downstream. Follow-ons (in order):
1. **Repo grep for hardcoded prod domains** first: `search_files` for `vercel\.app|<oldname>` (also `<oldname>\.vercel`). In ss-rover-cloud the ONLY reference was `r2-cors.json` → `AllowedOrigins: "https://ss-rover-cloud.vercel.app"`. Patch it, commit, push. (In that session the committed CORS origin was already stale vs the real live `rover-r-3d.vercel.app` URL — verify the live bucket allowlist before trusting the file's old value.)
2. **Cloudflare R2 CORS must be re-applied** — updating the JSON file is NOT enough; the bucket config must be re-pushed: `aws s3api put-bucket-cors --bucket <bucket> --cors-configuration file://r2-cors.json --endpoint-url https://<acct>.r2.cloudflarestorage.com`. Without this, browser uploads to R2 get CORS-blocked on the new URL. Keep the `localhost:3000` + `localhost:3210` dev origins.
3. **Supabase dashboard** (NOT in repo): Auth → URL Configuration → Redirect URLs. Add `https://<new>.vercel.app/**` if the old domain is listed. Repo grep will NOT find these — they live only in the dashboard. Same for Site URL if set.
4. **Project ID (`prj_...`) is UNCHANGED** by a rename — API integrations keyed on the ID keep working; only the URL slug changes.
5. **The dashboard orange "OIDC Token claims" warning is IRRELEVANT** for git-push deploys (you deploy via the Git integration, not GitHub Actions OIDC federation). Ignore it.
6. **GitHub repo rename needs `-R` + `-y`.** `gh repo rename lunavsolution` (no flags) fails with a usage error; from inside the repo it still needs `-y` to skip the confirm. Correct form: `gh repo rename lunavsolution -R kingkymaru-glitch/ss-rover-cloud -y` then `git remote set-url origin https://github.com/kingkymaru-glitch/lunavsolution.git`. Verify `git remote -v` shows the new URL.
7. **Audit source-code branding strings the rename leaves stale** (beyond `r2-cors.json`): `package.json`/`package-lock.json` `"name"`, the Edge-Function email `from:`/subject (e.g. `notify-admin/index.ts` `"SS Rover Cloud"` → `"LunaV Solutions"`), SQL migration comments, the `README.md` arch table.
8. **Obsidian vault is the user's PRIMARY update surface** — rename leaves stale `.vercel.app` URLs + the old GitHub repo URL there. Grep the vault for `ss-rover-cloud\\.vercel\\.app|kingkymaru-glitch/ss-rover-cloud` and patch `Projects/SS Rover Cloud.md` (all URLs + tick the CORS checkbox), `VAULT MAP.md`, `HermesKeyMemories.md`, `GITHUB.md`. Keep the `~/Documents/ss-rover-cloud` folder path AS-IS — renaming it live breaks a running dev server + every vault path that references it.
9. **Do NOT rename the local folder live.** Renaming `~/Documents/ss-rover-cloud` while a dev server runs breaks the server and all vault paths. Only do it if the user explicitly asks, and then stop the dev server first, `mv`, then update vault paths.
10. **Hardcoded URLs in vault-backed scripts go stale after rename and produce false health artifacts.** The vault is not just markdown — scripts like `~/riina/healthcheck.mjs` write automated rows into `HEALTH_LOG.md`. After a rename, those scripts may still probe the old slug (`ss-rover-cloud.vercel.app` → 404). The log then records the 404 as if it were a live outage, when the real site at the new slug is healthy. After any rename, grep vault scripts for `vercel\.app|<oldname>` and update the live domain string there too. Re-run the script and re-read the resulting log — do not trust the last appended row until you've spot-checked the new live URL yourself with a direct `curl` or browser request.
Verify after: site loads at new URL + an actual R2 upload from the new URL succeeds (CORS) + no Supabase magic-link redirects silently fail. If a custom domain is attached, the `.vercel.app` change is cosmetic for end users but the R2 CORS still must allow the new `.vercel.app` origin for any non-custom-domain paths.

## STATIC HTML DEPLOY (no framework, no Git integration) — VALIDATED 2026-08-22

For a folder of plain `.html`/`.js`/`.css` (e.g. an A-Frame/WebAR viewer, a QR printer page, a docs site) Vercel does NOT need a build step. This is the fastest path to real HTTPS for a no-install phone experience. It is a different flow from the Next.js/Vite Git-integration path above and has its own three gotchas.

### Gotcha 1 — `framework: "static"` is an INVALID value
`vercel.json` with `"framework": "static"` fails the deploy with:
`"projectSettings.framework" should be equal to one of the allowed values ...` (a long enum list; "static" is NOT in it).
Fix: **omit `framework` entirely.** A plain static site is the default when there's no build script. Use only:
```json
{ "outputDirectory": ".", "rewrites": [{ "source": "/(.*)", "destination": "/$1" }] }
```
(Don't put `"name"` in vercel.json either — the `--name` flag and the `name` property are both deprecated; Vercel derives the project name from the deploy command's context or the folder.)

### Gotcha 2 — new Vercel CLI uses DEVICE-CODE login, not a browser popup
`npx vercel login --github` (or any `vercel login`) does NOT auto-open a browser in a headless/sandboxed CLI. It prints:
`Visit https://vercel.com/oauth/device?user_code=XXXX-XXXX  Waiting for authentication...`
Hand the URL + code to the user; they approve in their browser; the CLI detects it and prints `Congratulations! You are now signed in.` Then run the deploy.

### Gotcha 3 — cross-team STALE domain collision
If `https://<slug>.vercel.app` 404s on a page you just deployed, it may be a *different project* from another team/account that owns that exact slug (Vercel slugs are global-ish per the `*.vercel.app` wildcard, and a stale project from another team can hold `<slug>.vercel.app`). Your deploy lives under YOUR team's build URL `<slug>-<hash>-<team>.vercel.app`. Always verify against the **deployment URL** (the one printed by `npx vercel ls --prod`), not a guessed `<slug>.vercel.app`. Don't waste turns trying to `vercel domains add <slug>.vercel.app` — it errors `invalid_domain` because that alias isn't valid for your team.
- `vercel domains add <slug>.<team>.vercel.app` also fails (`invalid_domain`) for the team's default region alias — skip it; the deployment URL is already stable + public.

### The validated sequence (this session, webarr-screen)
```bash
cd ~/webarr-screen
npx --yes vercel@latest login --github          # device-code; user approves in browser
# edit vercel.json: REMOVE framework:"static"
npx --yes vercel@latest deploy --prod --yes      # prints build URL <slug>-<hash>-<team>.vercel.app
LATEST=$(npx --yes vercel@latest ls --prod 2>/dev/null | grep -oE "https://[a-z0-9-]+\.vercel\.app" | head -1)
# verify BOTH pages serve 200 + correct content:
curl -sL -o /dev/null -w "viewer.html HTTP %{http_code}\n" "$LATEST/viewer.html"
curl -sL -o /dev/null -w "index.html  HTTP %{http_code}\n" "$LATEST/index.html"
curl -s "$LATEST/viewer.html" | grep -oE "<title>[^<]*</title>"   # expect YOUR app title, not Vercel 404
```
Both pages returned 200 and the title grep matched → confirmed live, no Git integration needed.
- Re-deploy after any file change: `npx vercel deploy --prod --yes` (the deployment URL increments its hash each time; the old URL may 404 as Vercel rotates — use `vercel ls --prod` to get the current one, or `curl` both and trust the 200).
- No-build static means there is no "stale bundle hash" problem (no hashed JS); the HTTP 200 + title/content grep IS the verification. This is simpler than the bundle-grep dance above.

### iOS Safari gotcha for the WebAR itself (not Vercel)
Inline `<video>` painted from a MediaStream on iOS Safari goes black / flashes unless the video element has `playsinline` + `muted` AND `webkit-playsinline`. For A-Frame/MindAR the camera is handled by the library, but if YOU add any preview/stream video element, set those attributes or iOS shows a black box. (DOM overlays / report panels are safer than video-paint on iOS — prefer a scrollable DOM panel over compositing video.)

## PITFALL — Next.js App Router: don't duplicate a route as both `page.tsx` AND `route.ts`
A directory can hold EITHER a `page.tsx` (UI) OR a `route.ts` (handler), never both at the same segment. Adding `src/app/share/[token]/route.ts` next to an existing `src/app/share/[token]/page.tsx` fails `next build` with:
```
Error: Conflicting route and page at /share/[token]: route at .../route and page at .../page
```
Fix: pick ONE. If a client portal `page.tsx` already exists at that segment (e.g. a Phase-3 read-only share portal), DO NOT add a `route.ts` — extend the existing page instead. Symptom check: if `curl https://<domain>/<segment>/<anything>` returns the portal's own guard page (e.g. "Access Denied"/"Invalid or Expired") rather than a 404, the `page.tsx` is already live and serving — stop building a second one.
Also: Next 16 route handlers receive `params` as a **Promise** — `export async function GET(_req, { params }: { params: Promise<{ token: string }> })` then `const { token } = await params;`. A non-Promise `params` type compiles under `tsc` but breaks at build/runtime on Next 16.

## PITFALL — Verifying a live Next+Supabase app's data path WITHOUT a DB session
RLS hides tables from the anon key, and auth-only RPCs (e.g. `generate_share_token`) can't mint a token for you. You still need to prove the deploy is live and the route works. Recipe (full script in `references/verify_deployed_next_supabase.md`):
1. Extract the real anon key from the DEPLOYED bundle (it's a public `NEXT_PUBLIC_*` client key, inlined in a `_next/static/chunks/*.js` chunk — grep the live HTML for chunk refs, then grep each chunk for the supabase URL + key).
2. Probe the RPC with a dummy token: `curl '.../rest/v1/rpc/get_shared_project' -H "apikey: $KEY" -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' -d '{"share_token":"<dummy>"}'` → expect `null` (RPC callable, RLS works), NOT a 500. That proves the route + security-definer + readOnly shell are wired.
3. `curl https://<domain>/<segment>/<bad-token>` → expect HTTP 200 + the portal's guard text. A raw 404 means the page isn't deployed; a custom guard page means it IS, and the render path is exercised.
4. Confirm photos/documents render by reading the `ProjectWorkspace` (or equivalent) `readOnly` branch in source — grep for the per-marker `photos_json`/image fields and the `documents`/`file_url` download block. Code-proven + live-routed = verifiable without ever minting a token.
You CANNOT see a valid token's rendered pixels from this seat — that requires the user's authenticated session (open the dashboard, click the share/QR button). Say so plainly; don't fake a "verified visually" claim.

## PITFALL — First-time Vercel link requires `--project` flag when auto-detection names the project wrong

`vercel link` auto-detects the project name from the repo directory name. When that name fails Vercel's project-name validation (must be lowercase, no consecutive dashes, etc.) — e.g. a repo dir called `CDM` — the link fails with a 400 before you can even deploy.

**Fix:** pass `--project <name>` to override the detected name:
```bash
cd ~/CDM && vercel link --scope <team> --project cdm --yes
```
This both links the repo AND creates the project if it doesn't exist. After linking, Vercel writes `.vercel/project.json` and the project is ready for deploys.

## PITFALL — Vercel env vars must be added AFTER linking, not before

A linked project without its env vars will build but fail at runtime (or fail to build for API routes that read env at module scope). Setting env vars in `.env.local` does NOT cover Vercel builds — Vercel inlines env vars at build time from its own project configuration.

**Add all env vars via CLI after linking:**
```bash
# URL and service-role key: safe as secrets
vercel env add NEXT_PUBLIC_SUPABASE_URL production --value "<url>" --yes
vercel env add SUPABASE_URL production --value "<url>" --yes
vercel env add SUPABASE_SERVICE_ROLE_KEY production --value "<key>" --yes

# Publishable anon key: NEXT_PUBLIC_ prefix triggers a credential warning
# Vercel requires explicitly choosing --type config (public) or --type secret (private)
# Since the anon key IS used client-side (NEXT_PUBLIC_), use --type config:
vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY production --type config --value "<key>" --yes
```

**Type choice for NEXT_PUBLIC_ keys:**
- `NEXT_PUBLIC_*` vars are exposed to the browser bundle by Next.js/Vite — Vercel warns they look like credentials
- Use `--type config` for publishable keys that MUST be in the client bundle
- Use `--type secret` only for server-side keys never referenced by `NEXT_PUBLIC_`
- If you forget `--type config`, the `vercel env add` command fails with `public_prefix_requires_type`

**After adding env vars, REDEPLOY** — env changes don't apply to an already-built deployment.

**Note the anon key naming:** Supabase renamed `anon` to `Publishable key` (`sb_publishable_...`) in the new dashboard (P6 in supabase-backend skill). Use the Publishable key value, not an old anon string.

## References
- references/vercel-alias-pitfall-recipe.md — condensed command transcript and the exact error strings to recognize.
- references/static-html-vercel-deploy.md — full static-HTML deploy transcript: device-code login, the framework:"static" rejection, cross-team domain collision, and the curl verification that proved it live.
- references/verify_deployed_next_supabase.md — how to prove a live Next+Supabase route/RPC works WITHOUT a DB session (extract anon key from deployed bundle, dummy-token RPC probe, bad-token guard-page check, App Router page.tsx/route.ts collision + Next 16 params Promise).
- references/project-rename-sop.md — full cross-surface rename checklist (R2 CORS re-apply, Supabase redirect URLs, GitHub `-R`/`-y` rename flags, Obsidian vault sync, do-NOT-rename-folder-live).
- references/git-push-divergent-remote-rebase.md — `git push` rejected by a divergent remote (another machine pushed first): rebase + keep-both recipe, no force-push.