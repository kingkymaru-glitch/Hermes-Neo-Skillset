# LunaV-family repo map + drift evidence

## The four repos (all under github.com/kingkymaru-glitch/)
| Project | Local path | GitHub repo | Layout | Deploy |
|---|---|---|---|---|
| R-Tessera | ~/Documents/R-Tessera | kingkymaru-glitch/R-Tessera | Vite SPA, `src/` flat (no app dir) | Vercel r-tessera.vercel.app |
| LunaV | ~/lunavsolution-code | kingkymaru-glitch/lunavsolution | **Next.js App Router — pages in `src/app/`** | Vercel lunavsolution.vercel.app |
| Trip.Pancing | ~/Desktop/Trip.Pancing | kingkymaru-glitch/Trip.Pancing | private | Vercel trip-pancing.vercel.app |
| LUNASCAN | ~/Documents/LUNASCAN | kingkymaru-glitch/LUNASCAN | private (MIT) | — |
| luna-edge | ~/luna-edge | kingkymaru-glitch/luna-edge | private | localhost:8000 |

*Visibility per vault notes; verify with `gh repo view --json isPrivate` if it matters.

## Domain names — resolve BEFORE reporting (status as of last orientation)
| Domain | Status |
|---|---|
| `lunavsolutions.com` / `www.lunavsolutions.com` | **NXDOMAIN** — never registered or lapsed. NEVER report this as the site. |
| `lunavs.com` | 308 → `https://www.lunavs.com/` (the live marketing/Labs landing domain). |
| `r-tessera.vercel.app` | 200 (live). |
| `lunavsolution.vercel.app` | 200 (live LunaV Studio). |
| `lunav-labs.vercel.app` | 200 (live Labs deploy). |
| `lunav-labs-eight.vercel.app` | **200 — still resolves**, but it is the OLD Labs subdomain. Hardcoded in code in 5 places across R-Tessera + LunaV. Stale string, not a dead link. |

- A domain that LOOKS stale is not automatically broken: `curl -s -o /dev/null -w "%{http_code}" <domain>` before calling it a gap. Both Labs subdomains answer, so the old one is cosmetic drift.
- Always `dig +short <domain>` (and `dig @8.8.8.8`) before repeating a domain from a note, vault, or pasted URL — stale domain strings in notes are common.

## Trip.Pancing — separate stack, separate backend
NOT part of the shared LunaV spine. Own Supabase project (ref
`sxexzecaxxoynemqtvjx`, Sydney), Next.js App Router + Supabase + Cesium, Cesium fishing
marketplace. Live URL is the Vercel alias `trip-pancing.vercel.app`; prod deploy state is
readable with `cd ~/Desktop/Trip.Pancing && vercel ls trip-pancing --json --yes`.
- Its ops digest is a python collector at `~/trip-pancing-ops/collect.py` writing
  `digests/latest.json`. See `project-health-check` TRAP E for how that digest can report a
  healthy site as fully down.

## Shared spine
- ONE Supabase backend `okzmblyboudjffaifixa` (Sydney, rover-r-platform).
- LunaV glassmorphism theme (turquoise/green) — R-Tessera + LunaV headers/footers/bottom-railing pixel-matched 2026-08-12.

## Drift evidence (2026-08-12 session — why vault HEADs lie)
Vault Checkpoint/notes recorded HEADs that had fallen behind actual commits:
- R-Tessera: vault `a947d9e` → actual `e23db1e` (camera-framing fix landed after checkpoint).
- luna-edge: vault `Luna-Edge-Checkpoint` `65f54dc` → actual `f48cf69` (Folder Learning feature added).
- LunaV + LUNASCAN: also newer than checkpoint (basemap toggle; ODM docker hardening).
All four repos were PUSHED + clean (`main...origin/main`, no uncommitted/unpushed). Conclusion: **live `git` is truth; vault HEAD numbers are stale checkpoints.** Always `git` before citing a hash.

## Known stale-script entries (flag, don't silently fix)
- **R-Tessera** `package.json`: `"bridge": "node server/nodes-bridge.mjs"` and `"dev:all": "node server/local-server.mjs & vite"` reference a `server/` dir that does not exist (`git ls-files server` empty). Those two scripts fail if run.

## Known version-stamp gaps
- **R-Tessera** has NO version stamp in its footer. **LunaV** carries `src/lib/app-version.ts` = `APP_VERSION = "V0.40"` in the global footer. MARU's standing rule is every build visibly stamped — R-Tessera is the one that breaks it.

## Quick verify one-liner
```
for d in ~/Documents/R-Tessera ~/lunavsolution-code ~/Documents/LUNASCAN ~/luna-edge; do
  echo "=== $d ==="; git -C "$d" remote -v | head -2; git -C "$d" status -sb | head -1; git -C "$d" log --oneline -1
done
```
