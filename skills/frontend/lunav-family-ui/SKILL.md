---
name: lunav-family-ui
description: Sync LUNAV/R-Tessera/Luna-EDGE theme; deploy before "done".
---

# LunaV Family UI — cross-repo theme sync & deploy discipline

Three repos form ONE product family and MUST share one look. When the founder
says "make them look the same" / "sync the theme" / "adjust the top banner", this
is the playbook.

## The three repos
- **LunaV** — `~/lunavsolution-code` (github.com/kingkymaru-glitch/lunavsolution).
  Next.js + Vercel. Design system LIVES HERE: `src/app/globals.css` (glass theme,
  `--mb-turquoise`, `.mb-btn`, `.lv-brand-name`, `.ph-*` homepage classes, footer
  bottom-rail). This is the source of truth for every other project's styling.
- **R-Tessera** — `~/Documents/R-Tessera` (github.com/kingkymaru-glitch/R-Tessera).
  Vite + React + Cesium. Own `src/App.css`; mirrors LunaV glass tokens BY HAND
  (no shared import). Live at r-tessera.vercel.app.
- **Luna-EDGE** — `~/luna-edge` (github.com/kingkymaru-glitch/luna-edge). Flask +
  a SINGLE `templates/index.html` (ALL CSS/JS inline). Runs LOCALLY only: double-
  click `Luna-EDGE.app` on Desktop, or `cd ~/luna-edge && source .venv/bin/activate
  && python app.py` → http://localhost:8000. There is NO Vercel for this one.

## RULE #0 — "LunaV Labs" is AMBIGUOUS: TWO different surfaces (this cost a revert)
The founder says "LunaV Labs" / "the Labs page" — there are TWO, and editing the
wrong one means redoing the work (this bit the agent 2026-08-13):
1. **In-app Labs showcase INSIDE R-Tessera** — `~/Documents/R-Tessera/src/labs/`
   (`LabsPage.jsx` + `projects.js`), reachable via the header toggle OR
   `r-tessera.vercel.app/?view=labs`. Content = per-product `function/advantage/
   technology` blurbs.
2. **Standalone LunaV Labs HERO site** — `~/lunav-labs`
   (github.com/kingkymaru-glitch/lunav-labs), its OWN Vercel project at
   **lunav-labs-eight.vercel.app**. This is the marketing scrollytelling page.
   Content lives in `src/content.js` (`HERO/OPPORTUNITY/PROOF/PRODUCTS/INSIGHT/
   CASE/CTA`); `App.jsx` imports `PRODUCTS` from `./content.js` and renders it
   (lines ~4-5, ~142). `src/projects.js` + `src/labs/` in this repo are STALE
   leftovers NOT imported by anything — do not edit them.

DISAMBIGUATE BEFORE EDITING: "hero / landing / marketing / scrollytelling /
description of a product card" → the standalone `~/lunav-labs` site. "the in-app
showcase / back-to-globe" → R-Tessera `src/labs/`. Product-card *descriptions*
almost always mean the standalone hero site's `PRODUCTS[].desc`.
Note: `lunavlabs.vercel.app` and `lunav-labs.vercel.app` are unrelated v0-placeholder
apps — the real one is `lunav-labs-eight.vercel.app`.

## LUNAV-LABS HERO: page-number mapping (floating nav counts 01–07)
The nav "Page N" is the section `data-idx` = N−1:
- Page 1 = HERO · Page 2 = Opportunity · Page 3 = Proof · **Page 4 = "The Family"
  (5 product cards, `.lv-cap-card`, each with an animated `.lv-cap-visual` box)** ·
  **Page 5 = INSIGHT (text left, right visual box `.lv-insight-visual`)** ·
  Page 6 = Case Study (`.lv-case-image`, on the LEFT) · Page 7 = CTA footer.
The founder's filter class is literally named `.insight-image-box` — when he says
"Page 5, the box on the right", that IS the `.lv-insight-visual` box (right column
of a `1fr 1.1fr` grid). Do NOT guess it's the Case Study image (that box is on the
LEFT). When in doubt, match the filter class name + nav count.

## PLACING A SCREENSHOT ON THE LUNAV-LABS HERO (image workflow)
Founder passes a screenshot (e.g. "RT SS.png", "LunaVstudio3dmodel.png" from
`~/Desktop/Marketing LunaV/...`) to sit in a specific box. Do this:
1. Copy into `~/lunav-labs/src/assets/` and OPTIMIZE — screenshots compress badly
   as PNG (3.5MB stays ~2.7MB). Convert to JPEG:
   `sips -s format jpeg -s formatOptions 82 --resampleWidth <~1000-1600> <src.png> --out <name>-opt.jpg`
   → ~90-460KB (8-15x smaller). Delete the original PNG so it isn't shipped.
2. `import <var> from './assets/<name>-opt.jpg'` in `src/App.jsx`.
3. Render `<img src={var} .../>` inside the target box. For the "Family" cards, the
   card is data-driven (`PRODUCTS.map`), so add an optional `img` flag on the one
   product in `content.js` and branch in JSX — keep the other 4 cards' animations.
4. CSS — THE FOUNDER'S THEME FILTER, "2 tones lighter" (his exact recipe, brightened):
   ```css
   .<box> img { position:absolute; inset:0; width:100%; height:100%;
     object-fit:cover; object-position:center top; /* keep the app HEADER in frame */
     opacity:.88; filter:contrast(1.05) brightness(1.28); }
   ```
   `object-position:center top` is what stops the crop from cutting the app's top
   header/logo bar — the founder explicitly wants the header kept. (Baseline filter
   he provided: `opacity:.85; filter:contrast(1.05)`; "make it 2 tones lighter" →
   add `brightness(1.28)`.)
5. Build, commit as `maru <kingkymaru@gmail.com>`, push, verify the new hashed asset
   + filter string + `HTTP 200` on the image at lunav-labs-eight.vercel.app, and
   confirm in a browser that the specific card shows the img (other cards keep their
   animation). See `references/lunav-labs-hero-images.md` for the full verified recipe.

## RULE #1b — CROSS-PRODUCT NAVIGATION: link INTO the app, same tab
There are three surfaces and the founder navigates between them. The failure he
calls out is a LONG CHAIN: `lunavs.com` (Labs) → "Explore the Platform" → the
marketing LANDING page → "Sign in" → `/login` → `/dashboard`. Four hops, and every
cross-link opened a new tab so Back didn't work. Do not reintroduce this.

- **Point cross-product links at `/dashboard`, never at the marketing root.**
  `https://lunavsolution.vercel.app/dashboard` resolves correctly either way: signed
  out the middleware sends you to `login?next=/dashboard`; signed in you land in the
  app. Linking the bare origin forces a pointless landing-page stop first.
- **The auth middleware MUST preserve the intended destination.** When it bounces an
  unauthenticated hit to login, carry the target: `/login?next=<path+query>`, and have
  the login page redirect there after success (guard it: the value must start with `/`
  and not `//`, or it is an open redirect). Dropping the destination dumps every deep
  link on `/dashboard` and the user has to navigate back manually. Also bounce an
  ALREADY-signed-in user off `/login` straight to the app — a login form for a
  logged-in user is a dead end. Verify with
  `curl -s -o /dev/null -w "%{redirect_url}" <protected-path>` and confirm `next=` is
  present and the query string survives.
- **Same tab for in-family hops.** No `target="_blank"` on links between Labs,
  R-Tessera and Studio — Back must work. Keep `_blank` ONLY for genuinely external
  destinations (source links, `Details ↗`, third-party sites).
- **Watch for a circular link graph.** Studio's landing had "← Back to site" → Labs
  while Labs' hero → Studio, and R-Tessera → both. Verify the family forms a
  DIRECTED path into the product, not a loop with no front door.
- **Grep every surface for the old target, not just the one you edited.** The hero
  CTA lives in `~/lunav-labs/src/App.jsx`; the product-card data in `src/content.js`;
  R-Tessera's header buttons in `src/GlobeView.jsx`. A `search_files` for
  `lunavsolution\.vercel\.app|lunav-labs-eight\.vercel\.app|target="_blank"` across all
  three repos finds every hop before you claim the chain is fixed.
- **Marketing copy must describe what the product actually does.** A landing page
  advertised a "Free 14-day Pro trial" while the codebase had no trial or billing
  anywhere (signup went to an admin-approval queue). That is a claim a customer can
  hold the company to. When you see a promise in the copy, grep for the feature that
  backs it; if it does not exist, replace the copy with what actually happens
  (e.g. "book a guided demo" + a prefilled `mailto:`) rather than inventing the
  feature. Founder is liability-averse — surface the mismatch, don't paper over it.

## RULE #1 — "build passes" ≠ "user can see it"  (this bit the user hard)
Verifying `npm run build` only proves it compiles. The user looks at the LIVE
site. You MUST deploy before saying "done":
- **Vercel repos (LunaV, R-Tessera):** commit as the webhook author or the deploy
  NEVER fires:
  `git -c user.name=maru -c user.email=kingkymaru@gmail.com commit -m "..."`
  then `git push origin main`. Vercel auto-deploys. CONFIRM with
  `curl -s -o /dev/null -w "%{http_code}" https://<site>.vercel.app` → 200.
  **Do not assume the webhook fired — but do not assume it FAILED either.** Confirm
  with the deployments API, never by watching a bundle hash:
  `TOKEN=$(python3 -c "import json;print(json.load(open('$HOME/Library/Application Support/com.vercel.cli/auth.json'))['token'])")`
  then `curl -s "https://api.vercel.com/v6/deployments?projectId=<prj_id>&teamId=<team_id>&limit=5" -H "Authorization: Bearer $TOKEN"`
  (ids are in `<repo>/.vercel/project.json`). `source=git` + your commit SHA + `state=READY`
  means it fired on its own — done. Only if there is NO deployment row for your SHA did the
  webhook truly miss; then deploy manually from the repo dir: `vercel --prod --yes`.
  NOTE: for a Vite code-split app the `index-*.js` hash does NOT change when the edit
  is in a lazy chunk (e.g. `GlobeView-*.js`) — so an unchanged index hash is NOT evidence
  of a failed deploy. Find which chunk holds your string first
  (`grep -l '<marker>' dist/assets/*.js`), then fetch that chunk from the live origin.
  This exact false alarm fired on R-Tessera: the webhook HAD fired automatically, but an
  unchanged entry-chunk hash made it look like a miss and triggered a needless manual deploy.
- **Luna-EDGE (local Flask):** restart the server. Kill any running `python app.py`
  and relaunch; a stale dev process serves old code. Open http://localhost:8000.
- NEVER tell the user "verified / everything is done" until the change is actually
  visible on the URL they're watching. A passing build is not evidence of a
  deployed change.

## Shared design system (copy these tokens from LunaV globals.css)
- **Header bar:** `backdrop-filter: blur(22px)`, ~56px tall, bottom hairline border,
  `background: var(--glass)`.
- **Buttons `.mb-btn`:** subtle bordered glass pill — `padding ~9px 16px`,
  `border-radius 10px`, `color: var(--txt-secondary)`, hover lifts (`translateY(-1px)`).
  Active/primary = teal tint (`.mb-btn-primary`). Flat turquoise solid fills are NOT
  the house style — use the glass pill.
- **Brand `.lv-brand-name`:** `<b>LunaV</b> <span>PROJECT</span>` where PROJECT
  (STUDIO / R-TESSERA / EDGE) is `var(--mb-turquoise)`. "STUDIO" is bold (700).
  Mirror exactly in the other repos: Luna-EDGE uses `.brand .name` (font-size 0.85rem,
  `span` color turquoise, weight 700, letter-spacing 0.06em); R-Tessera uses `.rt-name`.
- **Footer bottom-rail (THE FAMILY SIGNATURE — apply to ALL THREE):** fixed full-width
  bar, glass `blur(22px)`, `border-top`, `font-size: 0.62rem; letter-spacing: 0.15em;
  text-transform: uppercase;`. Left = teal status dot (`box-shadow` glow) + "LunaV
  <PRODUCT> — 3D Engine Online"; right = "LUNAV <PRODUCT> — ROVER-R". The three
  variants:
  - LunaV Studio: left "LunaV Studio — 3D Engine Online", right "LUNAV STUDIO — ROVER-R"
  - R-Tessera:    left "LunaV R-Tessera — 3D Engine Online", right "LunaV R-Tessera - ROVER-R"
  - Luna-EDGE:     left "LunaV EDGE — 3D Engine Online", right "LUNAV EDGE — ROVER-R"
  STANDING: the Luna-EDGE rail was historically the "LunaV Labs" wordmark — that is
  OUTDATED; founder mandated the LunaV-family bar (2026-08-12 session). Use the
  "3D Engine Online / ROVER-R" form for every repo. Do NOT reintroduce "LunaV Labs".
- **Equal spacing:** use ONE gap value across the whole nav — `gap-2` (8px).
  Do NOT mix `gap-3` (12px) in one group and `gap-2` in another; the user flags the
  inconsistency. Keep "Settings" pinned right via `ml-auto`; everything else left.
- **Back buttons:** founder removes them from top banners. Don't add new ones;
  if a top bar has "← Back", expect to delete it on request.

## BUTTON BOXING CONVENTION (family-wide, decided 2026-08-13)
The founder wants a MIXED box style, not uniform rounding — and each corner style
carries MEANING:
- **SHARP SQUARE (border-radius ~2px, hairline 1px outline, near-flat fill)** =
  the IMPORTANT link or action. Apply to: primary action buttons (e.g. "View
  Homepage", "Go to Project", "Pin & save"), and priority OUTBOUND links
  (e.g. the header "LunaV Studio" link → lunavsolution.vercel.app).
- **SOFT EDGE (border-radius 10px, gradient + soft border)** = ambient CHROME.
  Apply to: nav buttons, header Menu/Labs toggles, panels/cards themselves.
So "some buttons totally thin-border square, some soft edge" is intentional —
square signals "this link/action matters", soft signals "quiet structure".
When porting to LunaV/R-Tessera/EDGE, square the priority items, leave chrome soft.
R-Tessera's first implementation lives in `src/App.css` (`.proj-actions .mb-btn`,
`.link-pinpoint .mb-btn-primary`, `.rt-hdr-link` = square; `.rt-hdr-btn` = soft).

## FONT-UNIFY PITFALL (verify BEFORE re-adding a font)
"Make the font match across the family" does NOT mean inject the same font into
every repo blindly:
- **LunaV Studio** ALREADY uses Geist via `next/font/google` in
  `src/app/layout.tsx` (`Geist` + `Geist_Mono`, vars `--font-geist-sans/mono`,
  body `font-family: var(--font-geist-sans), "Helvetica Neue", ...`). Do NOT add
  `@fontsource/geist` there — it's already Geist. Just confirm the var is wired.
- **R-Tessera** (Vite, no next/font) needed it self-hosted:
  `npm i @fontsource/geist-sans @fontsource/geist-mono`, then `@import` the weights
  in `src/index.css` + set `--rt-font-sans/mono` + `body { font-family: var(...) }`.
  Cesium on-globe labels also need the mono face explicitly
  (`'Geist Mono', ui-monospace, monospace`) since they render in a canvas, not DOM.
STEP: grep each repo for its existing `font-family` / font setup FIRST; only add
where absent. The goal is visual uniformity (same typeface + sizes), not identical
import mechanism.

## STANDING GUARD — never recolor during a font/box sync
A "match the font / match the box" request is about SHAPE + TYPEFACE only.
KEEP each repo's existing accent palette:
- LunaV = teal (`--mb-turquoise` `#2f9bff` / `#0a84ff`).
- R-Tessera = gold (`#C9A96E`).
Do NOT port LunaV teal into R-Tessera or vice-versa when unifying font/box.
The founder has flagged invisible/recolored changes twice — unify shape, not color.

## RULE #2 — flex layout pitfall: footer pushed off-screen
In a `height:100dvh` flex-col root (nav / map / footer), the map container must be
`flex: 1`, NOT `height: 100%`. `height:100%` makes it grab the full column height
and shoves the footer below the viewport (invisible). Fix = `flex: 1 1 auto;
min-height: 0`. This is why an adopted bottom-rail "wasn't seen" once.

## RULE #2b — the global footer is `fixed bottom-0 z-50` and WILL cover new chrome
LunaV's global footer (version stamp + legal links, rendered in `src/app/layout.tsx`) is
fixed to the viewport at z-50. Any new full-bleed page or bottom status strip you add at
`bottom: 0` renders UNDERNEATH it — your bar vanishes and you cannot tell from the DOM or
from `tsc` that it happened. Measure it in the browser
(`document.querySelector('footer[class*=fixed]').getBoundingClientRect().height`, 33px at
the time of writing) and offset your own root by that amount
(`position:fixed; top:0; left:0; right:0; bottom:33px`). Do NOT simply raise your z-index
above 50 — that hides the version stamp, and a VISIBLE version stamp is a standing rule.

## RULE #3 — a sub-view that grew up should become its own page/repo (Option B)
When a section of an app (a showcase, a roadmap, a "Labs" page) is no longer a small
toggle but something you'd show customers at a demo, PREFER extracting it into its own
standalone page over parking it as an in-app `view` state. This session: LunaV Labs was
first built as a `?view=labs` toggle inside R-Tessera, then promoted to its own private
repo (github.com/kingkymaru-glitch/lunav-labs) deployed as its own Vercel project.

WHY it matters (the bug that forced it):
- Mounting a Cesium globe and a non-globe view (Labs) as SIBLINGS toggled by React state
  causes a runtime crash on transition — Cesium's `viewer.destroy()` runs during the same
  commit as the Labs mount, throws `t.remove is not a function`, and blanks the page
  (see `vite-build-verification` Pitfall 16). A separate page/route eliminates this class
  entirely because the globe app fully tears down before the new page mounts.
- A standalone page ships ZERO Cesium → it loads in ~200 kB (63 kB gzip) instead of
  228 kB + 306 kB of globe. For a demo on a flaky/offline network this is the difference
  between "instant" and "spinner".
- The "go to Labs" button becomes a plain `<a href>` link, not a state toggle — no
  unmount-during-WebGL hazard.

Extraction recipe (verified this session, minimal Vite + React, NO Cesium):
- New repo, `package.json` with ONLY `react` + `react-dom` + `@vitejs/plugin-react` + `vite`
  (drop cesium/resium/three/@supabase/supabase-js — Labs never used them).
- Lift the self-contained component (e.g. `src/labs/LabsPage.jsx`) + its data file
  (`projects.js`) verbatim. NO changes needed if the data file is the only source.
- Lift ONLY the CSS the page uses: copy the shared `.rt-header` / `.rt-brand` / `.rt-mark`
  / `.rt-name` / `.rt-railing*` base classes + the page-specific `.labs-*` rules into a
  single `App.css`. Do NOT bring `vite-plugin-cesium` or the globe `index.css` unless the
  page imports it — add a minimal `index.css` reset if `main.jsx` imports one.
- Swap the "Back to Globe" button for a link: `<a className="rt-hdr-btn" href="https://r-tessera.vercel.app">← LunaV R-Tessera</a>`.
- Build must pass: if you see `[UNRESOLVED_IMPORT] Could not resolve './index.css'`, you
  dropped a CSS file `main.jsx` still imports — add it back (even minimal).
- Commit as the Vercel webhook author and push:
  `git -c user.name=maru -c user.email=kingkymaru@gmail.com commit -m "..."`
  `gh repo create <name> --private --description "..."` then
  `git remote add origin https://github.com/kingkymaru-glitch/<name>.git && git push -u origin main`
  (NOTE: `gh repo create` does NOT auto-add the local `origin` remote — add it yourself
  before the first `git push`.)
- Deploy: Vercel dashboard → Add New → Project → import the repo → Vite preset, no env vars.
  The `vercel` CLI may not be installed locally; the dashboard path needs no CLI.

Full step-by-step + verified file tree → `references/extract-standalone-landing-page.md`.

## EDGE-specific
- All CSS/JS is inline in `templates/index.html`. Mirror `.mb-btn` as `.hdr-btn`.
- Brand "LunaV EDGE" is already EDGE-style. Tool button = round `.ph-tool-fab`,
  light grey `#cfd6e0`, no teal fill.
- AI Learning and AI Detection are TWO SEPARATE banner buttons, each opening its OWN
  panel (`#learnPanel` / `#aiDetPanel`) — NOT a single mode-toggle. See the
  luna-edge-dev skill for the exact independent-toggle pattern; do not reintroduce
  the old `setLearning` mutual-swap that hid one button.
- To preview your edit: restart `python app.py`, open localhost:8000.

## DESIGN EXPLORATION — look & feel BEFORE any build
When the founder asks to "improve the look and feel" / "make it look professional" / "kill the AI-generated feel", build throwaway standalone HTML and serve it on localhost. Do NOT touch the repo — no branch, no commit, no push — until he picks a direction. He judges by feel, not by spec: state the aesthetic bar back to him, build 2-3 variants that differ in STANCE (not pixels), and opinionate on which is strongest. Full bar, the anti-"AI-generated" rules, the 3D scene conventions (unlit wireframe edges, de-colliding projected labels) and the correct way to verify a visual change → `references/design-mocks.md`.

## Resume anchors (do NOT rely on chat memory)
- Luna-EDGE: read `~/luna-edge/luna-edge-checkpoint.md` (durable).
- R-Tessera / LunaV: live at *.vercel.app; check `git log --oneline -1` before
  assuming state. Canonical project notes live in
  `~/Documents/obsidian_maru_1/Projects/`.

## Verification checklist (run before reporting done)
- [ ] Change committed + pushed as kingkymaru@gmail.com (Vercel) OR server restarted (EDGE)
- [ ] Prod URL returns 200 (Vercel) OR localhost:8000 returns 200 (EDGE)
- [ ] Visual diff requested by founder is actually present in the DOM/screenshot
- [ ] No regressions: footer visible, buttons aligned, no overlap with map/remarks/save pill
- [ ] All three rails use the "3D Engine Online / ROVER-R" LunaV-family form
- [ ] FONT/BOX sync only: confirm each repo kept its OWN accent (LunaV teal / R-Tessera gold) — no recolor leaked
- [ ] FONT/BOX sync only: priority actions/links are square, ambient chrome is soft (mixed box convention)
- [ ] FONT/BOX sync only: did NOT re-add a font to a repo that already had it (grep first)
