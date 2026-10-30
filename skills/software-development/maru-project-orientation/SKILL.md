---
name: maru-project-orientation
description: Orient MARU's LunaV-family repos via vault note + live git.
category: software-development
---

# maru-project-orientation

## When to use
MARU asks to "read about X", "what's the status/state of X", "is X kept in GitHub / pushed", or wants an orientation/summary on any project in his LunaV family: **R-Tessera**, **LunaV** (lunavsolution), **LUNASCAN**, **luna-edge** (Luna-EDGE), **LUNASCAN-SONAR**. Also use to produce a project-health / state summary before starting work on one of them.

## Method — vault note + live git, ALWAYS both
1. **Read the canonical vault note.** The Obsidian vault at `~/Documents/obsidian_maru_1/Projects/` is the authoritative project doc. Find the right note(s) with:
   `search_files(pattern='<Name>', path='~/Documents/obsidian_maru_1/Projects', output_mode='files_only')`
   Read the primary note + any `Checkpoint-*`, `*-Linking`, `Dam Demo` siblings. MARU's notes are cross-linked via `[[...]]` wikilinks (e.g. LUNASCAN references [[SS Rover Cloud]], [[R-Tessera]]).
2. **Git-verify the live state.** For each repo, run in terminal:
   - `git -C <repo> remote -v` — confirm it's on GitHub under `kingkymaru-glitch`
   - `git -C <repo> status -sb` — confirm synced with origin (`main...origin/main`) and clean tree
   - `git -C <repo> log --oneline -1` — **actual** HEAD
   - `git -C <repo> log -1 --pretty="%an <%ae>"` — confirm the **last commit author matches the Vercel deploy gate** (`kingkymaru@gmail.com`). A feature only auto-ships to `*.vercel.app` if the triggering commit carries that author; a mismatched author = deploy skipped even on `main`. (2026-08-21 session: a `maru <kingkymaru@gmail.com>` HEAD confirmed the Dimension Tool would auto-deploy.)
3. **Cross-link topology check (LunaV family).** MARU's standing rule: family cross-links must be **LIVE + functional, not merely code-present**. Verify in code, don't assume:
   - For each repo, grep outbound domains: `grep -rno "https://[a-zA-Z0-9./_-]*\(lunav\|r-tessera\)[a-zA-Z0-9./_-]*" <repo>/src` (skip `node_modules`/`dist`).
   - Expected bidirectional pairs: R-Tessera ↔ lunav-labs ↔ lunavsolution (LunaV Studio). The old "Studio has no back-link to Labs" one-way gap has been CLOSED in code (Studio now links Labs + R-Tessera).
   - **Domain-drift watch:** code may hardcode an OLD Labs subdomain (e.g. `lunav-labs-eight.vercel.app`) that no longer matches the live Labs deploy (`lunav-labs.vercel.app`). A stale-looking domain is NOT proof of a broken link — **curl BOTH before calling it a gap**: `curl -s -o /dev/null -w "%{http_code}" <domain>`. Both currently return 200, so a hardcoded old subdomain is cosmetic drift, not a 404. Report it as stale-string drift, never as "the link is dead".
4. **Code count + size profile** (when MARU says "count the code"). Report **source only** — never count `node_modules`, `.git`, `dist`, or `.next`, and never count `public/` assets as code (`.glb`, vendored JS, and HTML pages distort the number). Per-area split is what makes the count useful:
   ```bash
   # one repo: per-area file+line split
   for d in src/app src/components src/lib supabase/functions supabase/migrations; do
     f=$(find $d -type f -not -path '*/node_modules/*' | wc -l)
     n=$(find $d -type f -not -path '*/node_modules/*' -exec cat {} + | wc -l)
     echo "$d: $f files, $n lines"
   done
   # per-extension, and the biggest files
   find src \( -name '*.tsx' -o -name '*.ts' -o -name '*.css' \) | xargs wc -l | sort -rn | head -15
   ```
   State the stack (R-Tessera = Vite+React+Cesium; LunaV = Next.js App Router+Supabase+Tailwind) and the version stamp (`src/lib/app-version.ts` on LunaV — `APP_VERSION = "V0.xx"`). Then flag any gap against MARU's standing version-stamp rule.
5. **Report the merged picture.** State what the vault says + what git actually shows + the cross-link state + the code profile. Flag any drift (see pitfalls). MARU is a founder, not an engineer: lead with what each app IS and how they connect, then the numbers. No infra/config detail unless asked.

## PITFALL — repo layout is NOT what the repo name implies (FIRST-CLASS)
`lunavsolution` is a **Next.js App Router** repo: its pages live under **`src/app/`**, not a bare `app/`. A `find app` or `find <repo>/app` returns EMPTY and reads as "no pages" — a false negative. Always `ls -a <repo>` first and confirm the framework before assuming a directory name. Same trap for the components dir: LunaV keeps pages in `src/app/`, workspace tabs in `src/components/workspace/`, shared libs in `src/lib/`.

## PITFALL — package.json scripts can reference files that do not exist
R-Tessera's `package.json` lists `"bridge": "node server/nodes-bridge.mjs"` and `"dev:all": "node server/local-server.mjs & vite"`, but **no `server/` directory exists** (`git ls-files server` is empty). `npm run bridge` / `npm run dev:all` would fail. When reporting a repo's state, sanity-check that each script's target file exists — stale script entries are drift worth flagging, not a bug to fix silently.

## PITFALL — "continue" is ambiguous: restate the thread before building
When the founder says "continue working with X" / "keep going on X", do NOT pick the thread
from the most recent artifact in the repo or vault (a fresh design doc, an open issue list)
and start building. That thread is often a LATER stage he has explicitly deferred. State which
thread you are resuming — naming the concrete surface and the next chunk — and get a yes
before any code. A wrong-thread build costs the whole session and reads as not listening.

Discriminator when the vault holds several threads at once: a note marked `status: design`
or `status: open`, or an issue list with every item unticked, is a FUTURE thread. It looks
like the newest thing because it was written last, but nothing has been built from it.
The ACTIVE thread is the one whose build plan has ticked chunks and a stated next step.
Read the status field before the commit date.

## PITFALL — vault commit hashes drift behind reality (FIRST-CLASS)
Vault `Checkpoint-*` / project notes record HEAD commit hashes that go **STALE** as new commits land. **Never cite a vault-recorded HEAD as "current" without git-verifying.**
- Evidence (2026-08-12 session): vault Checkpoint said R-Tessera HEAD `a947d9e` but actual git HEAD was `e23db1e` (a camera-framing fix had landed since); vault `Luna-Edge-Checkpoint` said `65f54dc` but actual was `f48cf69` (Folder Learning feature added). All four repos were in fact pushed + clean — the notes simply lagged commits.
- Takeaway: trust live `git` for current state; treat vault HEAD numbers as "as of last checkpoint", not "now".

## PITFALL — pushed to GitHub ≠ live on Vercel (FIRST-CLASS)
Vercel's production URL (e.g. lunavsolution.vercel.app) builds the **production
branch** — default `main` — NOT whatever branch you pushed. Pushing a `feat/*`
branch to origin does NOT update the deployed site. In the 2026-08-20 session the
founder opened the live 3D Digital Twin expecting the Dimension tool (built on
`feat/dimension-drag`, pushed to origin) and it was absent — correct behavior,
because that branch was never merged to `main`.
- To answer "is it live?": (1) confirm which branch Vercel builds (default
  `main`; check Vercel project settings or `vercel.json`), (2) `git diff
  main...<branch>` to see what's unreleased. "Pushed" is not "deployed".
- To actually ship a feature branch: merge it into `main` (or set Vercel's prod
  branch to it). Never assume the URL reflects a non-main branch.
- **"Is it deployed?" — ask GitHub, not the site.** A push to `main` creates a Vercel
  deployment whose state is queryable without a browser or a Vercel token:
  `gh api "repos/kingkymaru-glitch/<repo>/deployments?per_page=1" --jq '.[0] | {sha: .sha[0:7], id: .id}'`
  then `gh api "repos/kingkymaru-glitch/<repo>/deployments/<id>/statuses" --jq '.[0] | {state, env_url}'`.
  `state: success` on the pushed SHA is the evidence to report; a bare `git push`
  transcript is not.
- **Do NOT verify a deploy by fetching a chunk from the local build**
  (`/_next/static/chunks/<hash>.js` from `.next/`) — Vercel's build produces different
  hashes, so it 404s even when the deploy is fine and reads as a false negative. The
  deployments/statuses check above is the reliable probe; the live URL only confirms the
  site responds (`curl -s -o /dev/null -w "%{http_code}" <url>/login` → 200).
- See `lunav-studio` → `references/proxy_shape_extension.md` for the Dimension
  branch state.

## Cross-cutting architecture (one family)
All four repos are under `github.com/kingkymaru-glitch/`, share **ONE Supabase backend `okzmblyboudjffaifixa`** (Sydney), and the **LunaV glassmorphism theme**.
- **R-Tessera** = public CesiumJS globe, Viewer front-end (anon client) to that Supabase.
- **LunaV** (lunavsolution) = inspector SaaS (2D Leaflet homepage + 3D twin + reports).
- **luna-edge** = offline edge-AI YOLO brain (localhost:8000); feeds LUNAV post-mission.
- **LUNASCAN** + **LUNASCAN-SONAR** = capture front-ends filling the twin with `.glb` / sonar point clouds.

### 3D generation pipelines — which component uses what

| Component | Input → Output | Engine | Blender? |
|-----------|---------------|--------|----------|
| **LUNASCAN** | video → `.glb` | VideoToolbox ingest → CoreML masking → **OpenDroneMap** (Docker, dense SfM→MVS→textured mesh) → web-optimize | **NO** |
| **CDM Surroundings** | OSM bbox → `.glb` | headless Blender + blosm addon | **YES** |
| **CDM "OSM buildings"** | OSM bbox → Cesium polygon entities | in-browser extrusion (`osm-buildings.mjs`) — **no `.glb` at all** | **NO** |
| **DTwin** | video → `.ply` splat → `.glb` mesh | COLMAP SfM + MLX 3D Gaussian Splatting → `ply_to_glb.py` / `splat_to_mesh.py` | **NO** (Blender named in docs as a *viewer* for `model_raw.ply` only) |
| **3D Building Builder** | coordinates → `.glb` | headless Blender + blosm/BlenderGIS, procedural | **YES** |

**Key distinction:** LUNASCAN is the video→GLB pipeline but does NOT use Blender. CDM's "Surroundings" feature is the only LunaV-family function that shells out to headless Blender (`blender --background --python`), and it imports OSM map data via the blosm addon — not video. When the user asks about "headless Blender" in the LunaV context, they may be conflating these two; clarify which pipeline they mean.

CDM exposes **two** OSM paths and the UI wording is the tell: **"Build detailed (Blender)"** in `SurroundingsPanel.tsx` produces a real `.glb` via the Blender worker; the plain OSM-buildings path extrudes footprints as Cesium polygon entities in the browser and never writes a file. Do not describe the second as a Blender/GLB pipeline.

### Attributing an artifact to its generator (do this before agreeing or disagreeing)
When MARU asserts "X produced this" — especially a claim that a model looks too clean for photogrammetry — settle it with artifact forensics, not with the vault or with reasoning about how the asset looks.

1. **Read the GLB's own generator stamp.** Every glTF carries `asset.generator` in its JSON chunk; the producing tool writes it. Run `scripts/glb_provenance.py <path…|dir>` (or hand-parse — see `references/glb-provenance-forensics.md`). `Khronos glTF Blender I/O v<ver>` ⇒ Blender. A custom string (`DTwin ply_to_glb`, `DTwin splat_to_mesh`) ⇒ that script. `draco_decoder` ⇒ a Draco-optimised export (LUNASCAN's post-ODM `3d-optimize` stage rewrites the stamp, so it is NOT evidence of Blender). Absent ⇒ third-party CAD export.
2. **Grep the code, not the docs.** `grep -rn -e blender -e bpy <repo> --include='*.py' --include='*.sh' --include='*.mjs' --include='*.js' --include='*.ts' --include='*.tsx'` — comments and markdown name Blender for *viewing*, so only hits that actually shell out (`subprocess`/`execFile` of the Blender binary, `import bpy`) count. Exclude `site-packages`, `mesh-venv`, `node_modules`, `dist` or third-party libs (fontTools, open3d, matplotlib) produce false positives.
3. **Ask git whether the pipeline ever used Blender:** `git -C <repo> log --all -S'blender' --oneline` — an empty result across all history is a durable negative.
4. **Report the split.** A "too perfect" model in this fleet is a *procedural* Blender build (a builder, not a reconstructor) — that is why it is clean. Never let "this looks too good for photogrammetry" turn into a pipeline claim without steps 1–3.

See `references/glb-provenance-forensics.md` for the per-artifact generator table and the GLB binary layout, and `references/repo-map.md` for local paths, GitHub URLs, visibility, and the 2026-08-12 drift evidence.

## LunaV local dev & data access (what actually blocks a local run)

`lunavsolution` does not run locally out of the box. `src/lib/supabase/*` reads
`NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` from `.env.local`, and the
committed `.env.local` contains a literal placeholder string, not a key. `npm run dev`
starts fine, the pages render, and every query silently returns nothing.

- **The anon key is public by design** — it ships in the browser bundle. Rather than asking
the founder for it, extract it from the deployed app: fetch `/dashboard` and its
`_next/static/*.js` chunks and regex for `eyJ...` JWTs, keeping the one whose decoded
payload reads `"role":"anon"` and `"ref":"<project-ref>"`.
- `vercel env pull` cannot help: the Supabase vars are stored as Vercel *Secrets*, so the
pull writes `[SENSITIVE]` placeholders even when the CLI is authenticated.
- The **Supabase CLI is logged into a different org** — `supabase projects list` does not
include `okzmblyboudjffaifixa`, so `supabase link` / `db push` / schema inspection are not
available for LunaV. Read the live schema from the repo's `supabase/` SQL instead, and note
that `supabase/schema.sql` is an older vintage than what is live.
- `.env*` is gitignored, so real keys in `.env.local` never ship. Back up the placeholder
before overwriting it.

**The anon key alone reads nothing.** RLS gates `projects` on `auth.uid() = owner_id`, and
the app's own `search_projects` RPC returns `[]` for an anonymous caller — verify with a
single curl before promising a populated page. Real data needs one of: a signed-in session,
a server-side `service_role` key kept in env (never in the browser bundle), or a public
`client_share_token` via `get_shared_project`.

**The auth gate** (`src/middleware.ts`) redirects every non-public path to
`/login?next=<path+query>`. Public prefixes: `/`, `/login*`, `/share*`, `/auth*`,
`/privacy|terms|cookies`, `/project/*/home`, `/wedge*`, `/api/wedge`. It additionally
requires `profiles.approved`, so an authenticated-but-unapproved user is bounced to
`/login?reason=pending` — which presents to the founder as "I can't log in" and is worth
checking before touching anything else.

## References
- `references/repo-map.md` — the four repos (path / GitHub / visibility / deploy) + drift evidence.
- `references/glb-provenance-forensics.md` — determine which tool produced any `.glb`: `asset.generator` values seen across the fleet, GLB chunk layout, and the code/git negative proofs.
- `scripts/glb_provenance.py` — stdlib-only probe; prints generator + mesh/node/material counts for one or many `.glb` files.
