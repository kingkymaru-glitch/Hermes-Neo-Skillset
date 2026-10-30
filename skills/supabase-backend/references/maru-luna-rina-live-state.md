# MARU / LunaV / RINA live project facts
Generated 2026-07-30 from MARU/R-Tessera work session.

## Project IDs
- MARU / SSR / LunaV Supabase = `okzmblyboudjffaifixa` (Sydney free tier)
- RINA Supabase = `joliwavzczzfiwpwrbtf` (Sydney)
- AnglerGO live project = `merfmrlkjoqrhijzfwbn`
- AnglerGO anon key = `sb_publishable_nWaGtmaE74mzv6-RJgy3fg_RlBkDscB` (verified live 2026-07-27)

## Deployment surface
- MARU live site = `https://lunavsolution.vercel.app`
- LunaV dashboard `/login`, `/dashboard`, brand site `https://www.luna-v.io`
- Vercel auto-promotes from `git push` to GitHub main. `vercel deploy/alias` CLI commonly fails from unauthenticated local CLI; do not block on it. Build green + push is the reliable path.

## Migration / DB-fix trap (repeat offender)
- Vercel builds do NOT run `supabase db push` or migrations against the live DB.
- If the local Supabase project is unlinked or `.env.local` has no access token, `supabase db push`/psql cannot work.
- In that state, the ONLY working path is the Supabase dashboard SQL Editor.
- Any health-check or local probe script referencing `ss-rover-cloud.vercel.app` is stale — the new live URL is `lunavsolution.vercel.app`.

## Vault read order
Before writing progress for MARU, in this order: `VAULT MAP.md` → `HermesProgress.md` → `Projects/<project>`. Write back only after that read. Native file tools only. Vault path: `/Users/kamarulhk/Documents/obsidian_maru_1`.

## Repo paths
- MARU = `/Users/kamarulhk/my-digital-twin`
- R-Tessera = `/Users/kamarulhk/Documents/R-Tessera`

## Founder style hits this session
- Health-check pass must cover: live-site HTTP, Supabase project health, live DB/app behavior behind auth. Do not report platform OK from a single positive probe when auth endpoints return 401 without a key.
- When a script is stale (URL/src/bug), patch the script first, then rerun, then write the log. Do not leave a stale URL in the log as if it reflected reality.
