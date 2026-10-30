# Vercel deployment for CDM (lunavs team)

CDM deploys to Vercel under team `lunavs`, project name `cdm`.

## Prerequisites

- Vercel CLI at `~/.local/bin/vercel` (not globally npm-installed)
- Repo linked already? Check `~/.config/vercel` or run `vercel link`
- `.env.local` must exist with Supabase credentials

## Link the project (first time only)

```bash
cd ~/CDM
~/.local/bin/vercel link --scope lunavs --project cdm --yes
```

**Project name MUST be `cdm`** — Vercel auto-detects "CDM" from the repo name and it fails validation. Always specify `--project cdm`.

## Add environment variables

All four Supabase vars are needed. The anon key is used client-side (via `NEXT_PUBLIC_`), so it must be added as `--type config`. **Also add `NEXT_PUBLIC_REVIEW_BASE_URL`** pointing to the current deployed URL — used by `InvitesContext` to build invite links. If this points to an old URL, invitees get a broken link:

```bash
cd ~/CDM
~/.local/bin/vercel env add NEXT_PUBLIC_SUPABASE_URL production --value "$(grep NEXT_PUBLIC_SUPABASE_URL .env.local | cut -d= -f2-)"
~/.local/bin/vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY production --type config --value "$(grep NEXT_PUBLIC_SUPABASE_ANON_KEY .env.local | cut -d= -f2-)"
~/.local/bin/vercel env add SUPABASE_URL production --value "$(grep SUPABASE_URL .env.local | cut -d= -f2-)"
~/.local/bin/vercel env add SUPABASE_SERVICE_ROLE_KEY production --value "$(grep SUPABASE_SERVICE_ROLE_KEY .env.local | cut -d= -f2-)"
~/.local/bin/vercel env add NEXT_PUBLIC_REVIEW_BASE_URL production --value "$(grep NEXT_PUBLIC_REVIEW_BASE_URL .env.local | cut -d= -f2-)"
```

## Deploy

```bash
cd ~/CDM
~/.local/bin/vercel deploy --scope lunavs --prod
```

## Verify

- The site URL is on the `lunavs` team, so it sits behind Vercel's **Deployment Protection** (SSO/login wall). This is expected — a 302 redirect on all routes means the functions EXIST and route correctly.
- A 404 on a route would mean the function is missing. A 302 means it's deployed and protected.
- **Verify all routes**, including the newer ones: `/review/[token]`, `/review/nodes`, `/review/zones`, `/collab`, `/collab/logs`. They share the same auth wall (302) as the original routes.
- To check the deployment is ready: `vercel inspect <deployment-id> --scope lunavs`
- Build logs show lambda sizes and all routes being READY.
- Curl returns 302 for every route — follow with `-L` if you need the final content (behind auth).
- Check `NEXT_PUBLIC_REVIEW_BASE_URL` env var is set to the **current** deployment URL, not an old one. If invite links are being built with a stale URL, the invitee gets a broken link.

## Troubleshooting

- **Build fails**: check `~/.local/bin/vercel deploy --scope lunavs` output. Common cause: missing env vars on routes that read `process.env.`
- **Function throws at runtime**: the route exists (302) but errors internally. Check the Vercel dashboard logs. Most often a missing env var that wasn't added to Vercel but exists in `.env.local`
- **`vercel env add` fails**: check the CLI syntax. The `--value` flag takes the value directly, not a pipe. Use `$(grep ...)` substitution as shown above.
- **Project not found**: the link is stale or pointing to the wrong team. Re-run `vercel link --scope lunavs --project cdm --yes`

## Env vars reference

| Variable | Type | Purpose |
|---|---|---|
| `NEXT_PUBLIC_REVIEW_BASE_URL` | `normal` | Base URL for the reviewer shell (`/review/[token]`). Used by `InvitesContext` to build invite links. Must point to the deployed Vercel URL, NOT localhost — a link built from `window.location.origin` works for nobody else. |
| `NEXT_PUBLIC_SUPABASE_URL` | `normal` | Supabase URL, exposed to browser |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `config` | Anon key for client-side Supabase SDK |
| `SUPABASE_URL` | `normal` | Supabase URL for server-side routes |
| `SUPABASE_SERVICE_ROLE_KEY` | `normal` | Service role key for server-side routes |

Note: `NEXT_PUBLIC_` vars are automatically sent to the browser. Non-`NEXT_PUBLIC_` vars stay server-side. The anon key must be `config` type because it is consumed by the client-side Supabase client but should not be treated as a secret exposed in the build output.
