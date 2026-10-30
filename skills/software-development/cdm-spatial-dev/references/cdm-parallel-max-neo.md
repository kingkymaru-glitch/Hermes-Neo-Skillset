# CDM Parallel-Agent Pattern (MAX + Neo)

MARU runs TWO agents on the SAME ~/CDM repo: **Neo (canonical)** and **MAX (parallel)**.
Unlike the DTwin Trinity pattern, there is no handshake file — coordination is via
git tags + Vercel deployment state.

## Key Differences from DTwin Pattern

- **No AGENT_HANDSHAKE.md** — coordination is implicit via version numbers
- **MAX deploys directly to Vercel** — may not push to GitHub, causing drift
- **Same branch (main)** — both agents commit to main, not separate branches
- **Version stamp is the arbiter** — `lib/app-version.ts` + git tags must match live

## Version Drift Symptoms

- Live production shows V0.87 but GitHub repo is at V0.83
- `app-version.ts` says V0.87 but no git tag exists
- CHANGELOG.md missing entries for deployed versions

## Recovery Procedure

1. `curl -s https://cdm-eta.vercel.app | grep -oE 'V0\.[0-9]+'` — check live
2. `cat lib/app-version.ts` — check local stamp
3. `git tag -l 'V0.8*'` — find untagged commits
4. `git tag V0.84 <sha>` — tag each missing version
5. Update CHANGELOG.md with all versions
6. `git push origin V0.84 V0.85` — push tags

## Pitfall: Deployed ≠ Committed

MAX may deploy V0.86-V0.87 directly to Vercel without git commits. These exist
only as Vercel deployments. Document them in CHANGELOG as "deployed directly to
Vercel" and note the gap. There is no commit to tag.

## Pitfall: Vercel Auth Wall

`curl` to the production URL returns a Vercel login page, not the app. To verify
the live version, open the URL in a browser (logged into Vercel) or check
deployment logs via `vercel logs <deployment-id>`.

## Production URL

- Live: `https://cdm-eta.vercel.app`
- Deployment: `https://cdm-h7g3qhms9-lunavs.vercel.app`
- Vercel project: `lunavs/cdm`
