# LunaV Deploy Checklist

Quick reference for a fresh LunaV deploy (new Supabase, new Vercel), for shipping a
release, and for proving a deploy actually landed.

## Database

1. Open SQL Editor: https://supabase.com/dashboard/project/okzmblyboudjffaifixa
2. Run `supabase/schema.sql` FIRST (creates all 6 tables + RLS + share functions)
3. Only then run individual migrations from `supabase/migrations/`
4. Schema changes reach the live DB ONLY by the founder pasting bare SQL (SQL hand-off rule) —
   a code-only Vercel deploy never touches the schema. Keep a strip of the committed
   migration as `~/Desktop/apply_<topic>.sql` (bare, comment-free) so select-all-copy-paste
   works directly.

## Edge Functions

Deploy from dashboard or CLI:

### r2-presign (already deployed)
- Generates presigned PUT URLs for browser-to-R2 upload
- Needs secrets: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET

### r2-list
- Lists R2 objects by LUNASCAN job prefix
- Same 4 secrets as r2-presign
- Dashboard: Edge Functions → "Deploy a new function" → "Via Editor" → name `r2-list`, paste `supabase/functions/r2-list/index.ts`

### notify-admin (already deployed)
- Admin notification webhook

## Build & Deploy

1. Ensure `.env.local` exists with at minimum:
   ```
   NEXT_PUBLIC_SUPABASE_URL=https://okzmblyboudjffaifixa.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=<real or placeholder>
   ```
   (`.env*` is gitignored — not committed)
2. `npx tsc --noEmit && npm run build` — should pass green
3. Push to `kingkymaru-glitch/lunavsolution` main → Vercel auto-deploys to `lunavsolution.vercel.app`
4. Real NEXT_PUBLIC_* values are set in Vercel dashboard env vars

## Version stamp, tag and Release (every release)

1. Bump `src/lib/app-version.ts` **and confirm the constant is actually rendered** — see the
   stamp pitfall in SKILL.md (global footer in `src/app/layout.tsx`, next to Cookies).
2. `npx tsc --noEmit && npm run build` green before committing.
3. Commit/tag with the deploy-gate author, or the Vercel webhook never fires:
   ```bash
   git -c user.name=maru -c user.email=kingkymaru@gmail.com commit -m "V0.xx: <headline>"
   git -c user.name=maru -c user.email=kingkymaru@gmail.com tag -a V0.xx -m "V0.xx — <headline>"
   git push origin main --follow-tags
   ```
4. Publish the Release:
   ```bash
   gh release create V0.xx --repo kingkymaru-glitch/lunavsolution \
     --title "V0.xx — <headline>" --notes "<what shipped, what the founder must run>"
   ```

## Verifying a deploy actually landed

`git push` is not evidence. Run these in order, ~45-60s after the push:

```bash
cd ~/lunavsolution-code
git log --oneline -1
gh api "repos/kingkymaru-glitch/lunavsolution/deployments?per_page=1" \
  --jq '.[0] | "sha=\(.sha[0:7]) env=\(.environment)"'
ID=$(gh api 'repos/kingkymaru-glitch/lunavsolution/deployments?per_page=1' --jq '.[0].id')
gh api "repos/kingkymaru-glitch/lunavsolution/deployments/$ID/statuses" --jq '.[0].state'
```

Pass condition: `state=success` against the EXACT commit sha, `env=Production`.

Then a content check on a string that is **server-rendered**, so it survives into the HTML:

```bash
curl -s https://lunavsolution.vercel.app/login | grep -o "Cookies.\{0,200\}"
```

- Do NOT try to string-match a CLIENT bundle: Vercel's per-build chunk filenames are not
  reproducible from a local `npm run build` (the local hash 404s on the deployment), and the
  per-deployment URL sits behind deployment protection. For client-only changes, report the
  deployment status + `curl` 200 and say plainly that the click-through is the founder's —
  never imply more was verified than was.
- Session-gated surfaces (owner workspace) can't be exercised from the CLI. But a real
  `lunav_share_token` CAN be read from the public `project_nodes` index with the anon key,
  which is enough to POST `get_shared_project` directly and inspect the live payload
  (also the way to confirm which vintage of that RPC is live before re-creating it).
