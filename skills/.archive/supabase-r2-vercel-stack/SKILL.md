---
name: supabase-r2-vercel-stack
description: Build/deploy zero-cost SaaS on Supabase (auth/Postgres/RLS/Edge Functions) + Cloudflare R2 (large-file storage, zero egress) + Vercel (Next.js hosting). Covers presigned direct-to-R2 uploads, share-token public read pattern, R2 auth/CORS pitfalls, CLI-only deploys.
---

# Supabase + R2 + Vercel free-tier SaaS stack

Use when: building or debugging an app that stores large files (3D models, media) with Supabase as auth/DB and Cloudflare R2 as object storage, deployed to Vercel. Reference implementation: ~/Documents/ss-rover-cloud (SS Rover 3D inspection SaaS).

## Architecture rules
- NEVER store large files in Supabase Storage — egress fees. R2 has zero egress; serve via public r2.dev subdomain or custom domain.
- Upload path: browser → Supabase Edge Function (auth check + presign PUT, aws4fetch signQuery) → browser PUTs bytes directly to R2 → save public URL row in Postgres. No Base64 anywhere. Use XMLHttpRequest for upload progress (fetch has no upload progress API).
- Public read-only sharing: don't add anon RLS policies. One SECURITY DEFINER SQL function `get_shared_project(share_token uuid) returns jsonb` bundling the whole object graph; grant execute to anon. Token generation = second SECURITY DEFINER fn that checks `owner_id = auth.uid()`. Attack surface = one UUID-keyed function.
- RLS: owner-only `for all using/with check` policies chained through parent tables (markers → models → projects → owner_id).
- Same React workspace component serves inspector and client portal via a `readOnly` prop (hide toolboxes, disable inputs, add watermark).

## Critical pitfalls (each cost real debugging time)
1. **R2 403 on presigned PUT — wrong credential type.** Cloudflare account API tokens start `cfat_...` and DO NOT work with the S3 API. You need the S3 pair shown on token creation: 32-hex Access Key ID + 64-hex Secret. If lost, "Roll" the token to re-display both. Verify credentials directly before blaming code:
   `curl --aws-sigv4 "aws:amz:auto:s3" --user "KEY:SECRET" -X PUT --data-binary @f "https://ACCT.r2.cloudflarestorage.com/BUCKET/key" -w "%{http_code}"`
2. **curl success ≠ browser success.** curl skips CORS preflight. Browser "Preflight response... 403" = bucket has no CORS policy. Object R/W S3 tokens CANNOT set CORS via `?cors` API (AccessDenied) — must paste JSON in dashboard (R2 → bucket → Settings → CORS) or use an Admin token. Include ALL origins up front (localhost dev ports + final vercel.app domain) to avoid a second round.
3. **Next.js build fails prerendering pages that create a Supabase client** when env vars absent: add `export const dynamic = "force-dynamic"` layout for auth-gated routes and keep placeholder values in .env.local until real ones exist.
4. Edge Function secrets hot-reload — `supabase secrets set` needs NO redeploy. Function code changes DO need `supabase functions deploy`.
5. R2_ENDPOINT env var unnecessary — build endpoint from R2_ACCOUNT_ID.

## CLI-only wiring (no dashboard paste-work needed for most steps)
- `supabase login` fails headless; run in background with pty and give the user the device-code URL.
- `supabase projects api-keys --project-ref REF -o json` → programmatically fetch anon/service_role keys, write .env.local directly.
- Verify schema landed: curl REST endpoint with anon key, expect 200.
- Vercel: `npx vercel login` (device code, background+pty, watch "Congratulations"), `npx vercel link --yes --project NAME`, pipe env values: `grep VAR .env.local | cut -d= -f2 | npx vercel env add VAR production`, then `npx vercel deploy --prod --yes`.
- Verify prod from outside: curl each route for 200 AND grep response body for real data (proves DB connectivity server-side).

## Vercel deploy gates — email match + CLI alias hang (cost hours, capture it)
The standing `build → commit → push → vercel deploy --prod` flow hits gates NOT in the happy path:

### Gate A — Vercel "Blocked: commit author email not valid"
Vercel compares the **commit AUTHOR email** against the **Vercel ACCOUNT email** (avatar → Account Settings → General), NOT the GitHub *verified* email and NOT the GitHub public email. If they differ, the Git deploy is blocked: *"The commit author email (X) is not a valid email address. This prevents Vercel from identifying the commit author."* Dashboard → Deployments shows the commit "Blocked" with a "Fix Git Configuration" modal.
- Fix: set local `git config user.email` to the **Vercel account email** and rewrite history: `git rebase --root --exec 'git commit --amend --author="NAME <VERCELACCOUNTEMAIL>" --no-edit'`, then `git push --force-with-lease`. (An empty/trigger commit makes `git commit --amend` fail "would make it empty" — `git rebase --skip` to drop it, or `git reset --hard HEAD~1` first.)
- Gotcha: GitHub primary email and Vercel account email can differ (seen: GitHub primary `kingkymaru@gmail.com`, Vercel account `innovatedmaru@gmail.com`). The Vercel account email is the one that must match.

### Gate B — GitHub GH007 "push would publish a private email"
Once commit email = Vercel account email (a real Gmail), GitHub may reject the push: `remote: error: GH007: Your push would publish a private email address.` This is GitHub's "Block command line pushes that expose my email" rule (Settings → Emails, bottom). It wants the `ID+user@users.noreply.github.com` address, which would then NOT match Vercel (Gate A) — a direct conflict.
- Resolution: UNCHECK **"Block command line pushes that expose my email"** in GitHub Emails settings. Then real-email commits push fine AND Vercel matches them. Do NOT switch the commit email to the noreply address — that re-triggers Gate A.
- If GitHub "Keep my email addresses private" is OFF (noreply not forced), this is the only box to flip.

### CLI alias-promotion HANGS in this sandbox — use the Git pipeline instead
`npx vercel deploy --prod --yes` BUILDS successfully (new `ss-rover-cloud-XXXX.vercel.app` URLs appear and respond 302) but the final **"Assigning alias"** step never completes: it hangs until killed or fails `Error: fetch failed`, and `npx vercel alias set <url> ss-rover-cloud.vercel.app` reports `Error: The deployment ... is not ready` every time — even on fully-built, responding deployments. Killing the deploy leaves the build permanently "not ready".
- Working fix: connect GitHub to Vercel (dashboard → Project → Settings → Git → Connect GitHub → link `kingkymaru-glitch/ss-rover-cloud`, prod branch `main`). Then every `git push` to `main` triggers Vercel's OWN pipeline, which builds AND auto-promotes the prod alias — no CLI alias step, so no hang.
- `vercel git connect <url>` from CLI fails "You need to add a Login Connection to your GitHub account first" — that OAuth must be done in the dashboard.
- Verify the alias moved: `npx vercel inspect ss-rover-cloud.vercel.app` prints the `url` + `created` the prod domain points to. To prove a UI change SHIPPED (not just 200): find the local built chunk with the new string (`grep -l "NEW TEXT" .next/static/chunks/*.js`), then `curl` that same `/_next/static/chunks/<hash>.js` from prod and `diff -q` against the local file — byte-identical = live.
- DO NOT loop `vercel alias set` retries expecting success; the gate is environmental. Connect Git and let Vercel promote.

## Verify the public share path (anon client)
- Test share-token path exactly as anon client: POST to `/rest/v1/rpc/get_shared_project` with only the anon key.

## Client-portal & UI pitfalls (post-launch iteration)
- **Silent clipboard failure = stale paste.** A Share button that copies the link in the background with `navigator.clipboard.writeText(...).catch(()=>{})` fails silently in some browser contexts; the user then pastes whatever was on the clipboard before (looks like the app "generated garbage"). Fix: open a modal with the link in a readOnly, selectable `<input>` + an explicit Copy button that toasts success OR "clipboard blocked — copy manually". Never rely on silent background copy.
- **Don't rotate the share token on every click.** Minting a new token each time Share is clicked silently kills links already sent to clients. Generate once if none exists; put token rotation behind an explicit "Generate New Link" button + confirm().
- **Supabase confirm-emails point to localhost by default.** For real remote users, set Auth → URL Configuration → Site URL to the vercel.app domain and add `https://DOMAIN/**` to Redirect URLs, else confirmation links are dead for anyone off the dev machine. Email confirmation itself is ON by default on new projects. Free-tier built-in mailer is rate-limited (few/hour) — plug in Resend for volume.
- **"email rate limit exceeded" is the free-tier mailer, not an app bug.** On signup this surfaces as a red form error, so it looks like broken registration. The signup itself succeeded up to the send step. Two causes to check: (a) genuine burst of real signups, (b) YOUR OWN verification probes ate the ~3-4/hour quota. It self-resets in ~1h. Fix for real users = Resend SMTP. When probing signup via `/auth/v1/signup`, note Supabase rejects `@example.com` as `email_address_invalid` — use a realistic domain (`@gmail.com`); unconfirmed accounts can't log in so they're harmless, but tell the user to delete throwaway probe users in Auth → Users. And budget your probes — each one burns the same quota the user needs for their own test.
- **New column on the client portal? Update the share RPC too.** The public portal reads ONLY through `get_shared_project`'s `jsonb_build_object`. Adding a column (e.g. `analytics_comment`) via `alter table` + a client-side field is not enough — clients see nothing until you also add the field inside the RPC's jsonb and re-run it (`create or replace`), plus extend the `Pick<Project, ...>` type on the shared bundle. Ship the alter + RPC replace as one migration.
- **Onboarding model:** inspectors who create/edit = real accounts at /login → Create Account (RLS walls each user's projects). Viewers who only look = the no-login share link. Match the path to the need.
- **Fixed-layout tables prevent blowout.** A long unbroken string in one cell stretches the whole table and pushes right-hand columns (thumbnails, action buttons) off-screen. Use `table-layout:fixed` + `<colgroup>` percentage widths, clamp long text (`-webkit-line-clamp` + `overflow-wrap:anywhere`), keep full text in a detail modal. `whitespace-nowrap` on action buttons so they never wrap.
- **Dark navy logos need a light plinth on a black dash.** A dark-colored logo (navy R mark) vanishes on a near-black MBUX background. Wrap it in a small light rounded tile with a soft shadow so it reads as a machined badge.
- **Near-black 3D scene hides dark models.** If models "hard to see", lift `scene.background`/fog from near-black to steel blue-grey (~0x232d3a), bump ambient (~0.85) and key light (~2.0), lighten floor/grid — keep surrounding UI chrome black so the stage looks like a lit instrument cluster.
- **Scrollable sub-panel vs. growing page.** A left/right console (`aside` with `maxHeight: calc(100% - 32px); overflowY:auto`) still lets an inner list push the whole panel taller. Give the *inner* list its own bound: `maxHeight: "34vh"; overflowY:"auto"` on the list container, not just the wrapper. Add new items → list scrolls, the rest of the console stays put.
- **Pie/donut chart without a chart dependency.** This project has NO recharts installed. A severity donut is ~30 lines of inline SVG: a base `<circle>` (track) + one `<circle>` per segment using `strokeDasharray="${frac*circ} ${circ-frac*circ}"` and `strokeDashoffset={-offset}` (advance offset by each segment's dash length), `rotate(-90 cx cy)` to start at 12 o'clock, center `<text>` for the total. Colors pulled from the shared `STATUS_COLOR` map so pins + chart stay in sync. Prefer this over adding a dep.
- **Theme swap = change CSS custom properties, not component code.** The whole cockpit skin is driven by `:root` vars in `globals.css` (surfaces, `--mb-turquoise` accent, glows). Swapping green→electric-blue and near-black→dark-grey was a handful of var VALUE edits in `globals.css` + the `STATUS_COLOR.PASS` literal in `types.ts` (used by 3D pins). Don't grep-replace hex codes across components — they read `var(--mb-...)`. Watch the two hardcoded `rgba(0,229,195,...)` leftovers (dash-bg gradient, scrollbar thumb) that don't use the var.

## Version-controlling the shipped project
- After deploy, users often want the repo on GitHub for progress tracking. Before pushing: confirm `.env*` is gitignored and grep tracked files for any secret literal (`git grep -l "SECRET_FRAGMENT"`) — create-next-app gitignores `.env*` by default, but verify. For projects scaffolded WITHOUT a .gitignore (e.g. a bare Vite project), write one first (node_modules/, dist/, .env*) then `git add -A`; verify `git diff --cached --name-only | grep -c node_modules` returns 0 before committing.
- Standing workflow when a user asks to track progress on GitHub: after each change run build → git commit → git push → vercel deploy so repo + live app always mirror. Save this as a per-project memory preference so future sessions do it without being asked.
- If `gh auth status` shows logged-out but the user says "this Mac already has GitHub access", the token is usually in the macOS Keychain from prior git HTTPS use — extract and auth `gh` non-interactively (no browser):
  `TOKEN=$(printf "protocol=https\nhost=github.com\n\n" | git credential-osxkeychain get 2>/dev/null | grep password= | cut -d= -f2); echo "$TOKEN" | gh auth login --with-token` (the same query's `username=` line confirms the account). Check this BEFORE asking for an interactive `gh auth login`.
- Create + push private repo in one shot: `gh repo create NAME --private --source=. --remote=origin --push`. Verify: `gh api repos/OWNER/NAME/commits --jq 'length'` and `gh repo view OWNER/NAME --json visibility`.

## Security hygiene
- If user pastes live secrets in chat, proceed but tell them to rotate after launch (rolling the R2 token also fixes the lost-S3-keys problem — two birds).
- service_role key: fetch via CLI for verification queries, never write it to app env.

## Support files
- `references/ss-rover-buildout.md` — full session detail: schema shape, presign function, verification transcript.
