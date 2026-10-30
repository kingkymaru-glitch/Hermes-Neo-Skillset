---
name: clean-client-fork
description: "Create a clean client fork / rebrand / duplicate of an existing repo for client-specific modification. Covers the sanitized copy (exclude .git/.env/node_modules/dist), identity rebrand (package name/version + in-code build tag), fresh git history, build verification, and pushing to a new GitHub repo via gh (with the unauthed-gh token workaround). Pair with codebase-orientation (run that FIRST)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [fork, rebrand, duplicate, client, github, clean-repo, git]
    related_skills: [software-development:codebase-orientation, github:github-repo-management]
---

# Clean Client Fork (rebrand / duplicate for modification)

Duplicate an existing codebase into a brand-new project with its own git
history and its own GitHub repo — free of the source's secrets, build
artifacts, and old commit log. Designed for the recurring case: a founder
who sells/forks a product (e.g. "MARU") per client and then modifies each
fork part-by-part.

This is the **execution** half. ALWAYS run `codebase-orientation` first
(version check + function map) so the fork starts from a known baseline and
the client gets the map doc. This skill covers the mechanics after that.

## When to Use

- "Start a clean client fork under a new project name"
- "Duplicate this repo for client X, new git, new GitHub project"
- "Rebrand and give it its own repo"
- Any "I'll prompt changes part-by-part" → fork FIRST, modify LATER

## Prerequisites

1. `codebase-orientation` already done: you have a function map `.md` and a
   confirmed version. Bump `package.json` version + in-code `APP_VERSION`
   constant to that baseline BEFORE forking (so the fork's first commit is
   coherent).
2. Confirm `git config user.name/email` is sane in the source repo (it
   carries into the new repo if you `git config` it there).

## Methodology (order matters)

### 1. Inspect environment before copying
Check in parallel:
- Top-level layout (`search_files` target=`files` or `ls -la`).
- Is there a `.gitignore`? (reuse or write one — see below).
- Is there a `.env` / `.env.example`? (the real `.env` must NOT be copied).
- `node_modules` present? (`du -sh` — copy it alongside later for a fast
  build, but never commit it).
- Tooling: `gh auth status`, `rsync --version`, `git config user.{name,email}`.

### 2. Sanitized copy (the critical step)
Create the destination dir on the user's drive (ask where; often
`~/Documents/<NewName>`). Then rsync a secrets/artifacts-free subset:

```
rsync -a \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='dist' --exclude='dist-ssr' \
  --exclude='.env' \
  --exclude='.DS_Store' \
  --exclude='*.log' \
  /path/to/SOURCE/  /path/to/DEST/
```

EXCLUDE `.git` (no old history), `.env` (real secrets), `node_modules` +
`dist` (regenerable). Keep `.env.example` and `.gitignore`.

Verify nothing secret/huge leaked:
```
test -e DEST/.env && echo "BAD" || echo "OK: no .env"
test -d DEST/.git && echo "BAD" || echo "OK: no .git"
```
See `references/fork-recipe.md` for the full, copy-paste command set.

### 3. Rebrand IDENTITY first (not product copy)
For a part-by-part modification workflow, do the *minimum* identity swap and
leave all in-app product wording for the user's later prompts:
- `package.json`: `"name"` → new slug (e.g. `r-tessera`), `"version"` →
  bumped baseline.
- In-code build/version tag (e.g. `App.jsx`: `BUILD_ENGINEER = 'R-TESSERA'`,
  `APP_VERSION`). Search the repo for the old brand string to find every
  spot; rebrand only the *identity* labels, not feature/UI copy, unless
  asked.
- `.env.example` header comment → new project name.
- `README.md`/`ARCHITECTURE.md`: optional to scrub now; can be part-by-part.

Do NOT do a sweeping find-replace of the product name across source — the
user explicitly changes product copy "part by part." Touch only build
identity + package metadata.

### 3b. Full rebrand sweep (later, when the user asks for the whole rename)
When the user wants *everything* renamed (not part-by-part), run a repo-wide
sweep and re-verify. This is the actual MARU→R-Tessera pass that followed the
initial fork:
1. **Grep the whole tree** for every brand/demo token, not just `src/`:
   `search_files` over `*.{js,jsx,ts,tsx,json,html,css,md,mjs,py,yaml,yml,txt}`
   for `OLD|old|Bangi|Temenggor|Gerik|Perak|DamGate|dam-gate|obsidian_old|DEMO_ASSETS|OLD_LS_KEY`.
   Include `docs/`, `server/`, and root `*.md` — demo strings and old brand
   names hide in READMEs, architecture docs, and sub-project folders.
2. **Rebrand each hit by file class:**
   - `package.json` name + `README.md`/`ARCHITECTURE.md` → rewrite headers.
   - Source `.jsx`/`.js`: brand strings, support email, repo owner display
     (`R-Tessera · github.com/<owner>`), modal kickers, chat persona name.
   - `localStorage` keys (e.g. `maru.governance.v1` → `r-tessera.governance.v1`)
     and cache prefixes (`maru.layer.` → `r-tessera.layer.`) — these are
     invisible but must change or old client data leaks across the rename.
   - Server `.mjs`: banner + log lines + the node-store vault path.
   - Sub-project folders (e.g. `docs/maru-shifu`): **rename the folder**
     (`git mv docs/maru-shifu docs/r-tessera-shifu`) AND rewrite its README +
     scripts (MQTT topics `maru/shifu/...` → `r-tessera/shifu/...`, k8s
     object names `edgedevice-marushifu-...` → `edgedevice-rtessera-shifu-...`).
3. **Remove demo data, don't just empty it.** Delete demo fallback arrays
   (`DEMO_ASSETS = []`), remove hardcoded demo coordinates (e.g. Bangi
   `SITE_CENTER`), and generalize spatial anchors to env-configurable
   (`VITE_SITE_LON/LAT/ALT`) instead of leaving a zeroed literal.
4. **Delete the stale function-map doc** (e.g. `MARU_FUNCTION_MAP.md`) if it
   references components you removed (DamGateViewerModal, etc.) and
   regenerate a fresh `<NEWNAME>_FUNCTION_MAP.md` from the current tree.
5. **Keep the real repo owner string.** If `github.com/<owner>` is the actual
   GitHub account, keep `<owner>` in the URL/href but prefix the *display*
   text with the new brand (`R-Tessera · github.com/<owner>`). Don't invent a
   new owner.
6. **Re-verify after the sweep** (see Pitfalls: verification checkpoint).

### 3c. Swap the brand mark for a logo image
When the user supplies a logo PNG and wants it in place of a text letter:
- Copy the asset into `public/<name>-logo.png` (served at `/<name>-logo.png`).
- Replace the text node (`<span className="…-mark">R</span>`) with
  `<span className="…-mark"><img src="/<name>-logo.png" alt="…" className="brand-logo" /></span>`
  in **every** place the mark renders (map wordmark + About-modal badge are
  usually two spots).
- Neutralize the old text-styling CSS on those mark classes (kill the gradient
  background / neon `color` / `font-size` / `letter-spacing`) and add a shared
  `.brand-logo { width:100%; height:100%; object-fit:contain; display:block; }`
  rule; give the badge `background:transparent; overflow:hidden; padding:3-4px`.
- White-background logos show a square inside dark UI badges. Two fixes:
  (a) **Bake a light-grey background into the PNG** so it reads on dark
  UI without a CSS plinth — `PIL`: open RGBA, then
  `Image.alpha_composite(Image.new('RGBA', size, (241,243,245,255)), img)`
  and save. This turns white/transparent areas grey while keeping the
  mark intact (verify a corner pixel == (241,243,245)). (b) If a CSS
  plinth still wraps the logo, **shrink the border**: set the plinth
  to `h-[104px] w-[104px]` and the `<img>` to `h-[96px] w-[96px]` →
  ~4px visible frame (was 16px). User ask: "make the logo big, the
  border small."
- If the user dislikes the grey square, offer a transparent-background
  PNG crop instead.

### 4. Bring `node_modules` back for a real build
```
rsync -a --exclude='.cache' /path/to/SOURCE/node_modules/ DEST/node_modules/
```
Same lockfile → identical, fast. Then PROVE the fork is clean:

```
cd DEST
npm run lint      # expect 0 errors (pre-existing warnings OK)
npm run build     # expect success; confirm output shows the NEW package name
```

A passing build is your evidence the fork is viable. Report the build line
(e.g. `> r-tessera@0.2.0 build`) to prove the rebrand took.

### 5. Fresh git history
```
cd DEST
rm -rf dist                       # don't commit build output
git init -q
git symbolic-ref HEAD refs/heads/main
git config user.name "..."; git config user.email "..."   # match source
git add -A
git status --short | grep -E '\.env|node_modules' || echo "OK: clean"
git commit -q -m "Initial <NewName> fork (clean) — based on <OldName> vX.Y.Z

Clean client fork: new git history, rebranded package identity, no source
secrets (.env excluded), no original history. Verified lint 0 errors and
production build pass."
```
Single initial commit, no old history. Confirm only `.env.example` (never
`.env`) is tracked: `git ls-files | grep -i env` and `git check-ignore .env`.

### 6. Push to a NEW GitHub repo
`gh` is frequently NOT authed on the user's machine. Handle it:
- If `gh auth status` works → `gh repo create <NewName> --private
  --source=. --push` (creates + pushes in one step).
- If unauthed AND no `GH_TOKEN` env → you CANNOT create the repo. Do NOT
  guess credentials. Options to offer the user (see the clarify pattern):
  1. They run `gh auth login` elsewhere, then you proceed.
  2. They paste a GitHub PAT (classic `ghp_` or fine-grained `github_pat_`,
     with `repo`/`public_repo` scope). You set it ONLY as an in-memory env
     var for the `gh` call, never write it to a file, never commit it, and
     `unset` it after.
  3. They create the repo themselves at github.com/new and give you the URL
     → `git remote add origin <url>; git push -u origin main`.
  4. Skip GitHub; keep local.

Token recipe (in-memory only):
```
export GH_TOKEN=ghp_xxx            # from user's message, never committed
gh repo create <NewName> --private --source=. --push
unset GH_TOKEN
```
A GitHub *password* will NOT work — must be a PAT. Flag that.

## Pitfalls

- **`.env` leakage is the #1 risk.** The source `.env` has REAL secrets.
  rsync EXCLUDE it, keep only `.env.example`. Verify with `git ls-files |
  grep -i env` (must show only `.env.example`) AND `git check-ignore .env`.
- **The `.env.example` substring trap:** after committing, a naive
  `git status | grep .env` will MATCH `.env.example` and look like a leak.
  Grep for the exact `\.env$` or check `git ls-files` (shows only tracked
  files — `.env.example` is the only match, which is correct).
- **`rm -rf dist` before `git add -A`** — never commit build output.
- **Rebrand identity, not copy.** The user changes product wording
  part-by-part; a sweeping brand find-replace now creates churn they'll
  re-edit. Limit edits to package metadata + build/version tag labels.
- **Build-verify BEFORE claiming done.** A clean fork is only proven by a
  green `npm run build`. Report the package-name line from the build output
  as proof of rebrand.
- **Orphaned CSS after deleting a component.** When you remove a modal/feature
  (e.g. DamGateViewerModal), grep `App.css` for its class names (e.g.
  `.dam-gate-modal`) and delete the dead block — Vite won't warn, and stale
  CSS lingers forever. Also fix any inline prose/comments that name the old
  brand (e.g. collision-proofing comments saying `"M.A.R.U"`).
- **Two verification checkpoints, not one.** (a) After the initial fork +
  identity swap (Step 4). (b) After a later full rebrand sweep (Step 3b/3c) —
  re-run `npm run lint` + `npm run build` and a final
  `search_files` for the old brand/demo tokens across the WHOLE tree
  (incl. docs/) to prove zero residual matches. The rebrand isn't done until
  that grep returns only the intentional survivors (real repo owner in the
  GitHub URL, the configured vault path).
- **Lint "stale" system nudges are noise.** After an edit turn, the harness
  may warn verification is stale even if you already ran lint/build this
  session — re-run both once at the end of a multi-step rebrand and report the
  fresh output. The pre-existing warnings (e.g. exhaustive-deps) are fine;
  only 0 errors matters.
- **`gh` unauthed is normal, not a blocker** — it's a credential state, not a
  tool failure. Offer the 4 options above; never invent or reuse credentials.
- **Destination on the user's drive, not inside the source repo.** Avoids
  nested `.git` confusion.
- **`git symbolic-ref HEAD refs/heads/main`** makes the first branch `main`
  (newer git defaults to `master` on `init`); keeps it consistent with the
  source's `main`.

## Verification

- `npm run lint` → 0 errors.
- `npm run build` → success, output prefixed with new package name.
- `git log --oneline -1` → single "Initial <NewName> fork" commit.
- `git ls-files | grep -i env` → only `.env.example`.
- Post-push (if done): `gh repo view <NewName>` or the user confirms the
  repo exists on GitHub.

## References

- `references/fork-recipe.md` — full copy-paste command sequence (rsync,
  rebrand grep, build-verify, fresh-git, gh push incl. token recipe).
- `references/rebrand-sweep-checklist.md` — when the user wants the WHOLE
  rename (not part-by-part): per-file token list, demo-data removal specifics,
  intentional survivors, and the end-of-sweep lint/build/grep verification.
