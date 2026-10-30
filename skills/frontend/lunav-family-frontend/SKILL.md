---
name: lunav-family-frontend
description: LunaV/R-Tessera/Luna-EDGE theme and UI consistency sync.
---

# LunaV Family — Frontend Theme & UI Consistency

MARU runs three front-ends that must look/feel like one system. LunaV Solutions is
the reference design; R-Tessera and Luna-EDGE adopt its glassmorphism language.

## 0. THEME-AUDIT MANDATE (read before any theme port — burned two rounds)
Swapping CSS variables is NOT a complete theme port. Rules with HARDCODED literal colors
(`rgba(27,31,38`, `#1b6fd0`, `47,155,255`, `2f9bff`) stay old-colored and the user sees a
half-themed page. MARU's "did you even check X / the background / the header / the railings"
is a FIRST-CLASS signal the port is incomplete. After every theme pass, grep the literal old
colors and key them out (full rule list + script in
`references/logo-swap-edge-gold-retheme.md` §0/§2). If it renders and you didn't grep it,
you didn't verify it.

## The three repos (local paths + live)
- **LunaV Solutions** — `~/lunavsolution-code` (github.com/kingkymaru-glitch/lunavsolution).
  Next.js + Supabase (project `okzmblyboudjffaifixa`, Sydney). Live: lunavsolution.vercel.app.
  Reference design system in `src/app/globals.css` (tokens + `.mb-btn` styles).
- **R-Tessera** — `~/Documents/R-Tessera` (github.com/kingkymaru-glitch/R-Tessera).
  Vite + React 19 + resium + cesium. Live: r-tessera.vercel.app. Styles in `src/App.css`.
  NO top bar originally — it had floating banners; now has a LunaV-style glass header.
- **LunaV Intel-M** — `~/LUNAV-Intel-M` (github.com/kingkymaru-glitch/LUNAV-Intel-M). Next.js 14 + TypeScript + recharts, FastAPI backend. Predictive maintenance monitoring. Dark glass theme matching LunaV family. Run: `cd backend && .venv/bin/uvicorn app.main:app --port 8001` + `cd frontend && npx next dev -p 3000`. WebSocket requires `NEXT_PUBLIC_WS_URL=http://localhost:8001` in `.env.local` (Next.js rewrites do NOT proxy WS upgrades). Port 8000 is reserved for Luna-EDGE — always use 8001 for Intel-M.
- **Luna-EDGE** — `~/luna-edge` (github.com/kingkymaru-glitch/luna-edge).
  Flask + WebSocket + ultralytics YOLO, single `templates/index.html` (all CSS/JS inline).
  Local only: `cd ~/luna-edge && source .venv/bin/activate && python app.py` → localhost:8000.
  LunaV glass tokens mirrored in the file's `:root` as `--lv-*`.
  ⚠ EDGE's theme source of truth is **LunaV LABS** (`~/lunav-labs/src/index.css`) = gold/navy
  ink + SHARP buttons, NOT LunaV Solutions (teal). The `design-tokens.md` reference below is
  the LunaV-Solutions token table and is STALE for EDGE — use `references/logo-swap-edge-gold-retheme.md`
  (§2/§8) for current EDGE tokens. Don't mirror `.mb-btn` teal into EDGE.

## LunaV design system (the reference)
See `references/design-tokens.md` for the full token table. Core facts:
- Glass: `backdrop-filter: blur(22px)`, panel bg `rgba(27,31,38,0.82)` (dark) / `rgba(30,38,64,0.55)` (glass theme).
- Accent: `--mb-turquoise` (#2f9bff dark / #0a84ff glass), teal active `#00e5c3`.
- Button `.mb-btn`: bordered glass pill, `padding 8-10px 14-18px`, `border-radius 10px`,
  `font-size 0.78rem`, `letter-spacing 0.06em`, grey text `--txt-secondary` at rest,
  teal `.mb-btn-primary` when active, hover lifts `-1px`.
- Font: Inter (EDGE) / Geist (LunaV). LunaV brand mark = `L` glyph in gradient box.

## EDGE-style brand (founder's explicit spec)
Brand reads as **"LunaV" + PROJECT-TOKEN**, where "LunaV" is primary-color white/bold
and the project token is the accent color, often uppercased:
- LunaV Solutions nav: `LunaV` + `STUDIO` (STUDIO bold, turquoise). Class `.lv-brand-name`.
- R-Tessera header: `LunaV` + `R-TESSERA` (turquoise).
- Luna-EDGE header: `LunaV` + `EDGE` (gold `var(--lv-turq)` now via Geist font; was turquoise/blue in the old EDGE theme). Logo = external `R3.png` mark with NO back box. See `references/logo-swap-edge-gold-retheme.md`.

## Founder UI preferences (embedded — start every LunaV-family UI task knowing these)
- **Top banner**: glass `blur(22px)`, min-h-16. Brand LEFT. Action/tab buttons
  LEFT-aligned with EQUAL spacing (use Tailwind `gap-2` = 8px uniformly — do NOT mix
  `gap-3` and `gap-2`, that was a real defect). **Settings pinned far RIGHT** via `ml-auto`.
- **NO "← Back" button** in top banners (removed from workspace + homepage on request).
- **Project-name subtitle**: grey (`--txt-secondary`, same as button text), NOT the accent
  blue. Baseline-align it with the button bottoms (inner brand `<div>` = `items-end`;
  the nav itself = `items-center` for vertical centering — mixing these up made buttons
  sit on the border line).
- **Tool/action FAB**: round (border-radius 50%, ~42px), NOT a square `.mb-btn`. Use an
  SVG icon, not a text label, when collapsing a tools palette.
- **Bottom railing** "LunaV Labs" (gradient `L` mark + "LunaV Labs", Labs in accent): present
  on Luna-EDGE, R-Tessera, and the LunaV Project Homepage. Make it `pointer-events:none`,
  `max-width:70vw`, centered, `z-index:20` so it never collides with corner cards
  (remarks bottom-right, save indicator bottom-left, draw-tools top-right).
- Buttons must follow each project's NEEDS — EDGE does not get Audit Report etc.; it gets
  its own (AI Learning / AI Detection). Don't force LunaV's tab set onto the others.

- **Glass card containing blocks break `position: fixed` modals.** `backdrop-filter: blur()` on a parent element creates a CSS containing block for fixed-position descendants — a modal rendered inside a `.glass-card` gets trapped within the card bounds instead of covering the viewport. Fix: use a `Portal` component that renders into `document.body` via `createPortal`, escaping the containing block. Any modal/dropdown/overlay inside a glass card must use this pattern.

## CRITICAL PITFALL — build-passing ≠ visible (this burned a session)
Editing source + a green `npm run build` does NOT mean the user can see the change.
Two distinct failure modes, both happened this session:

**A. Not deployed / not restarting.** Vercel needs the commit+push (kingkymaru@gmail.com
author) and Luna-EDGE needs a Flask restart. Covered below.

**B. Deployed but INVISIBLE (the one MARU flagged twice: "i still cant see the bottom
railing").** The element is in the DOM and the build is green, but it renders off-screen
or behind the canvas. MARU's literal phrase "i still cant see the X" is a FIRST-CLASS
signal the thing is rendered-but-hidden, NOT that code didn't ship. Common causes + fixes:
  - A `height:100%` sibling in a `flex flex-col` shell eats the column height and pushes a
    static `<footer>`/status-bar below the viewport. Fix: give the sibling `flex:1 1 auto;
    min-height:0` (NOT height:100%), OR make the bar `position:fixed; bottom:0; left:0;
    right:0` as a top layer above the map/canvas. (Hit on both LunaV Project Homepage and
    R-Tessera this session.)
  - A `position:fixed` bar covers a `position:absolute; bottom:Npx` corner control (base
    selector, remarks card, save indicator). Fix: lift those corners to `bottom:52px`+ so
    they sit above the fixed bar.
  - CSS class-name mismatch (JSX className ≠ any selector in CSS) → element unstyled,
    zero-size, drops behind the canvas. Grep the COMPILED css for the exact class token.
  - Verify by INSPECTING the live DOM (browser) or grepping the compiled bundle for the
    marker string — do NOT trust "build passed". When you cannot see it, say so and
    re-open the deployed URL / restart local, then re-inspect.

For these projects the change is only LIVE after a deploy step:
- **Vercel apps (LunaV, R-Tessera):** must `git commit` with author
  `kingkymaru@gmail.com` (`git -c user.name=maru -c user.email=kingkymaru@gmail.com commit`)
  then `git push origin main`. The webhook only fires on that author — wrong author = silent
  no-deploy. After push, `curl -s -o /dev/null -w "%{http_code}" https://<site>` and confirm 200
  BEFORE telling the user it's done.
  - **MARU manages Vercel deploy state manually.** He rolls back to a "last stable
    deployment" and later promotes a deployment from the Vercel dashboard himself. So a
    freshly pushed commit may NOT be live until he promotes it — after pushing, verify the
    LIVE bundle actually contains your change (`curl -s <live>/assets/index-*.js | grep -c
    "<marker>"`) rather than assuming the push went live. If it's still the old hash, tell
    him to promote the latest deployment (as he did on 2026-08-13).
- **Luna-EDGE (local):** the Flask server holds the OLD `templates/index.html` in memory.
  Restart it (`pkill -f luna-edge/app.py`, then `python app.py`) — and note uncommitted
  `launch.log` / `learn/datasets/` are normal, don't block on them.
- **R-Tessera dev:** `npm run dev` hot-reloads, but verify the port (5174) actually serves 200.
- Rule: never say "done / verified" until you have confirmed the LIVE URL (or restarted local
  server + curl 200). "Build succeeded" is necessary but NOT sufficient.

## SUB-APP PAGES MUST SHIP ON THE LUNAV DOMAIN — NOT a separate project (burned 2026-08-22)
MARU corrected: WebAR / other standalone sub-app pages must live on the LunaV app's own
deploy, NOT a separate Vercel project. A separate `webarr-screen` project was built, then
he said "i thought we firm that this will live on lunav solution webapp?" → consolidate.
- RULE: put standalone HTML sub-apps (MindAR WebAR, etc.) in `~/lunavsolution-code/public/ar/`.
  Next.js serves `public/**` as-is at `/ar/...` on `lunavsolution.vercel.app` — same domain,
  one deploy, no second project, no CORS/credential juggling. They are full standalone HTML
  docs (A-Frame + MindAR need their own `<a-scene>`/camera/WebGL), so they open in a NEW TAB
  when deep-linked — exactly the "fresh browser while LunaV stays open" behavior. No iframe
  (iframes + camera + iOS Safari are fragile).
- Deep-link from the React app with RELATIVE paths: `const AR_BASE = "/ar";` then
  `${AR_BASE}/viewer.html?token=…` opened via `window.open(url, "_blank")`. Do NOT hardcode
  the sub-project origin. If you must allow an override, gate it behind an
  `(window as any).__AR_APP_BASE__` env flag defaulting to `/ar`, never to a foreign domain.
- Tear down any now-redundant separate project after migration (`npx vercel rm <name> --yes`).
- MindAR script/asset hosting for these pages: see `webar-image-target-streaming` (host
  aframe + mindar + qrcode + card.mind locally under `public/ar/assets/`).

## Logo & typography swap — LunaV EDGE (R3 logo + LunaV LABS gold theme)
The full, CURRENT recipe (R3 mark + LunaV LABS gold/navy theme + Geist wordmark + left-aligned
thin-gold-line header buttons + NO back box, uncropped logo) lives in
`references/logo-swap-edge-gold-retheme.md`. Summary of the STALE→CURRENT shift so you don't
re-apply the old pass:
- EDGE is NO LONGER blue `#2f9bff`. It is gold/navy (LunaV LABS palette). Any "keep EDGE blue"
  guidance below is superseded.
- Logo is now `R3.png` (not `R1.png`), background removed, rendered UNCROPPED with NO back-layer box.
- Wordmark font is Geist (R-Tessera brand font), accent gold — not Cormorant italic.
- **Multi-page nav**: EDGE's two headers must keep IDENTICAL button order so the active highlight moves but buttons don't "hop slots" between pages — see reference §5.
- **Sharp-square ALL highlighted buttons**: when MARU says "make selected/active buttons sharp,"
  radius 0 on `.hdr-btn.active` (top-nav tab), `.step.active` (learning step row), AND the gold
  `button` CTA — not only the primary. Keep `.ghost`/`.amber`/`.stop`/`.step .num`/`.icon` soft.
  See reference §9. (2026-08-14 "tiny tweak" round, 11d455e.)
- **Logo on same-color bg**: R3 carries a baked navy plate == the header color, so it vanishes; key the plate out AND add a soft gold glow (glow, not a box) — see reference §6.
Legacy reusable recipe (see reference for the live version):

**Typography (Labs → EDGE):** add to the Google Fonts link
`family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400;1,600&family=JetBrains+Mono:wght@400;500`.
Define `--lv-serif: 'Cormorant Garamond', Georgia, serif;` and `--lv-mono: 'JetBrains Mono', ui-monospace, monospace;`.
Apply: brand wordmark → serif (weight 600, `font-style: italic` on the accent span);
eyebrows/labels/panel-titles/rail headings → mono (`font-size:0.6rem; font-weight:500;
letter-spacing:0.2em; text-transform:uppercase`); buttons → `border-radius:10px; font-size:0.7rem;
font-weight:600; letter-spacing:0.12em; text-transform:uppercase; hover: translateY(-1px)`.
(Current EDGE accent = LunaV LABS gold `#C9A96E`; the old "EDGE stays blue" rule is superseded — see reference.)

**Logo swap (Flask, CURRENT — R3):** `cp ~/Desktop/R3.png luna-edge/static/R3.png`. Flask's
`app = Flask(__name__)` already maps `static/` → `/static/<file>` — NO new route needed.
R3 is OPAQUE (gray bg) → chroma-key the bg out (script in reference). Replace the mark in BOTH
headers (Detection + /learn) and the collapsed launcher pill:
`<div class="mark"><img src="/static/R3.png" alt="R3" /></div>`
Mark has NO back box: `.brand .mark { display:inline-flex; ...; background:none; border:none; box-shadow:none; }`
Keep R3 UNCROPPED. (Full token table + keying script in `references/logo-swap-edge-gold-retheme.md`.)

**PITFALLS for the logo swap:**
- **Mark element differs per template.** `index.html` used `<span class="mark">L</span>` (header AND
  collapsed launcher pill); `learn.html` used `<div class="mark">L</div>`. Patch EVERY occurrence;
  `grep -c '"mark">L' templates/*.html` must be 0 afterward.
- **Flask static is automatic** — do NOT add a redundant `@app.route('/static/...')`.
- **Never touch Detection-tab JS.** EDGE detection runs on `<canvas id="feed">` +
  `requestAnimationFrame(paint)` + `ws.onmessage` inference loop. Edits are CSS/typography/logo only —
  confirm `#feed`, `requestAnimationFrame`, `ws.onmessage` still present after editing.
- **Browser tool cannot hit localhost** (private-IP guard) — verify with curl + grep on the served
  HTML (`curl -s localhost:8000/ | grep -o 'static/R3.png'`), NOT screenshots. Restart Flask
  (`pkill -f luna-edge/app.py && python app.py`) so it re-reads the templates, then curl 200 each page.

## Typical theme-sync task shape
1. Read LunaV `globals.css` for the current token/button spec (it is the source of truth).
2. Apply the same look to R-Tessera `App.css` / `App.jsx` and Luna-EDGE `templates/index.html`.
3. Keep each project's own buttons; only unify STYLE (glass, font, size, color, spacing).
4. Build → commit (kingkymaru@gmail.com) → push → curl live URL 200 → report.

## LunaV Labs — standalone animated landing page (2026-08-12)
MARU wanted LunaV Labs as its OWN clean page, not a `?view=labs` sub-view of R-Tessera. Built standalone:
- Private repo `kingkymaru-glitch/lunav-labs`, own Vercel project (`lunav-labs-eight.vercel.app`), local `~/lunav-labs`.
- Vite + React 19 + Cesium (resium) + `vite-plugin-cesium`. Real Cesium globe as a fixed right-half stage behind a scroll document.
- ALL R-Tessera layers ON by default: submarine cables from bundled `public/submarine-cables.json` (keyless), live USGS 2.5/week quakes (keyless fetch), and local LunaV project pins (embedded in `projects.js` — no Supabase needed for Labs).
- **Scroll-driven DOLLY-OUT camera** (the centerpiece): progress 0→1 maps to camera height (600k→2.4M m, exponential) + pitch (-55°→-5°). Globe stays centered (lon/lat ~0) so it's a pure pull-back, not a pan. Continuous rotation runs every frame independent of scroll. Reads as: top 1/4 sphere → bottom quarter → whole globe → globe+space.
- Per-project choreography: giant ghost name slides in + docks above content, image column flies in from alternating side, text fades up — triggered by an IntersectionObserver adding `.in` to each `.lv-proj` section. Dim veil + scanline over the globe keep copy crisp.
- Data-driven: **hero copy lives in `src/content.js`** (`PRODUCTS[].desc` for the 5 LunaV-family product cards — Studio/R-Tessera/Scan/Edge/Sonar; also `HERO`/`OPPORTUNITY`/`PROOF`/`INSIGHT`/`CASE`/`CTA`). App.jsx imports from `./content.js`. `src/projects.js` (a scrollytelling variant with `focus`/`pin` coords) is NOT imported by App.jsx — do not edit it for hero copy. Verify via App.jsx imports, not the README.
- **"LunaV Labs" is ambiguous — there are TWO surfaces.** The standalone hero (Surface A, copy in `src/content.js`) vs the in-app R-Tessera Labs showcase (Surface B, `src/labs/`). The R-Tessera header button now links OUT to Surface A. Resolve WHICH one MARU means before editing; see `references/lunav-labs-two-surfaces.md` for the mapping, page-number→section decider, revert recipe, and image-box placement.
- Full build recipe + camera math + verification in `references/lunav-labs-scrollytelling.md`.

## LunaV Studio 3D Digital Twin — Viewer3D known fixes (2026-08-13)
`~/lunavsolution-code/src/components/Viewer3D.tsx` is the Three.js stage. Two classes of fix proved out:

**Cursor ownership (was "cursor vanishes over the GLB" after upload).**
- OrbitControls and `handleMove` both wrote `renderer.domElement.style.cursor` and fought each other; `handleMove` clobbered OrbitControls' `grabbing` on the next pointermove, and the idle canvas had no affordance. There is NO `cursor:none` anywhere in the repo — the symptom is a clobbered/ambiguous cursor, not a hidden one.
- Fix pattern: (1) after `new OrbitControls(...)`, add `start`/`end` listeners setting a `let orbitDragging` flag, and set the idle cursor to `'grab'`; (2) in `handleMove`, `if (orbitDragging) return;` so the drag state is never stomped; (3) non-hover fallback = `'grab'` (not `'default'`), hover-over-marker = `'pointer'`, add-mode = `'crosshair'`. Single owner of the cursor = the component, not OrbitControls.

**Line path endpoint must scale WITH thickness (was "endpoint doesn't shrink when line thins").**
- The "along" marker builds a `TubeGeometry` of `thickness` plus per-vertex `SphereGeometry` node spheres. The spheres had a floor `Math.min(Math.max(thickness * 0.9, 0.18), 1.5)` so below ~0.2 thickness they stopped shrinking. Remove the floor: `new THREE.SphereGeometry(thickness * 0.9, 12, 12)` — endpoint now tracks the line exactly.
- To let users thin BOTH further, lower the thickness slider in `ProjectWorkspace.tsx`: `min={0.02}` `step={0.02}` (was `min={0.1}` `step={0.1}`). Endpoint = `thickness*0.9`, so it scales with no extra code.

**Verification rule for these:** `npx tsc --noEmit` is the gate (one-line numerics, no new symbols). Hold the slow `npm run build` until MARU eyeballs the live 3D result or says "commit". Then commit as kingkymaru@gmail.com + push + curl 200.

## LunaV Studio — ProjectWorkspace node detail drawer LAYOUT ORDER
The node detail drawer is the right-side / bottom-sheet panel in
`~/lunavsolution-code/src/components/ProjectWorkspace.tsx` (rendered when `activeMarker`
is set, ~line 1604 `aside.dash-panel`). Its vertical order is a founder-set convention —
do NOT rearrange blocks arbitrarily. When MARU says "push the slider to the bottom / above
the delete button", this is the intended arrangement (set 2026-08-21):

TOP → BOTTOM of the node tab:
1. Finding Title
2. Audit Severity
3. Annotation Style (Color / Dashed / Thickness for `along`; plus Size / Move / Rotate for `box`)
4. Findings & Remarks (textarea)
5. Video Links
6. Attach Photo Proof
7. **Position (World Units) sliders — X / Y / Z**  ← sits HERE, just above delete
8. Delete Marker button (`mb-btn-danger`, inside `{!readOnly && <div className="mt-5 border-t pt-4">…}`)

PITFALL — Position sliders "lost at the top": originally the Position block lived right
under Severity (~line 1641). MARU asked to move it to the bottom, above Delete. Reordering
a JSX block = (a) DELETE the `<div>` block at its old location, (b) re-INSERT the identical
block immediately before the `{!readOnly && (<div className="mt-5 border-t pt-4">` Delete-Marker
wrapper. Keep the block internals byte-identical: label `Position (World Units)`, the
`space-y-2 rounded-lg border p-3` wrapper, the `(["x","y","z"] as const).map` range inputs
with `min={-50} max={50} step={0.1}` and `onChange={(e) => savePosition(axis, Number(e.target.value))}`.
Do NOT merge the Position sliders into the Annotation-Style box or wrap them in another
conditional — they apply to ALL marker kinds, so they must stay OUTSIDE the
`kind === "along" || kind === "box"` guard.

Verification gate for this file: `npx tsc --noEmit` (one-line JSX moves, no new symbols)
catches breakage before committing. Hold the slow `npm run build` + Vercel push until MARU
eyeballs the live drawer or says "commit". Then commit as kingkymaru@gmail.com + push + curl 200.

## FOUNDER DESIGN MANDATE — 'designer hat'
For visual/UI/landing-page work MARU explicitly wants the agent to **interpret, not literal-follow**: *'put on your designer hat, don't take what i instruct literally, u may adjust things to make it look awesome, but stay with the idea.'* Apply: read the brief for intent, exercise judgment, ship a working artifact, then iterate on his verbal feedback. He pivots mid-stream ('standby', 'change of mind, u deploy it') — adapt and execute the new direction WITHOUT re-litigating superseded constraints. Prefer previewing a running version over long up-front planning for visual work.
