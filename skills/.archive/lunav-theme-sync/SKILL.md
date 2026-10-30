---
name: lunav-theme-sync
description: Sync LunaV glass UI across LunaV, R-Tessera, LunaV EDGE.
---

# LunaV Theme Sync — shared glassmorphism across three front-ends

MARU's product family must look like ONE brand. LunaV is the reference; R-Tessera and
LunaV EDGE inherit its glassmorphism. When the founder asks to "sync the theme" or "make
the header the same", apply this skill.

## The three front-ends (paths are stable)
- **LunaV** — `~/lunavsolution-code` (Next.js App Router + Tailwind + globals.css).
  Canonical design system. Header lives in `src/components/ProjectWorkspace.tsx` (the
  `.mb-btn` / `.mb-btn-primary` buttons + glass `<nav>`) AND `src/components/ProjectHomepage.tsx`.
  Theme tokens in `src/app/globals.css` under `:root` / `html[data-theme="..."]`.
- **R-Tessera** — `~/Documents/R-Tessera` (Vite + React 19 + Resium + Cesium).
  Plain CSS in `src/App.css`; markup in `src/App.jsx`. No Tailwind. Had NO header bar
  before sync — only floating banners. Now has a `<header class="rt-header">`.
- **LunaV EDGE** — `~/luna-edge` (Flask + single static `templates/index.html`).
  All CSS/HTML inline in that one file. Has a `<header>` already; brand style was the
  model for the EDGE wordmark.

## The reference header (copy these from LunaV)
- Bar: `background: rgba(20,23,28,0.82); backdrop-filter: blur(22px); -webkit-backdrop-filter: blur(22px);`
  `border-bottom: 1px solid rgba(150,175,205,0.14);` height 56–64px.
- Buttons (`.mb-btn`): pill-ish `border-radius: 10px`, `padding: 8–10px 14–18px`,
  `font-size: 0.78rem`, `font-weight: 600`, `letter-spacing: 0.06em`, subtle gradient
  `linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.01))`,
  border `1px solid var(--hairline)`, idle text = secondary color, hover lifts 1px.
  Active/primary variant tints with the accent turquoise and adds a soft glow.
- Brand mark: a 34px rounded square with an "L" glyph. The gradient differs by repo —
  LunaV + Luna-EDGE use blue `linear-gradient(135deg,#2f9bff,#1b6fd0)`; **R-Tessera uses GOLD**
  `linear-gradient(135deg,#C9A96E,#a8854f)` + gold glow (recolored 2026-08-13 to match the LunaV
  Labs gold port; supersedes the earlier GREEN `#00e5c3` mark). Do NOT copy the blue mark into
  R-Tessera, and do NOT copy the gold mark into LunaV/EDGE. R-Tessera's chrome is now full GOLD
  (#C9A96E) — node markers, link pin, projects tag, footer code, and the Labs "visit" link were all
  recolored from cyan/blue to gold at founder's "full unity" call.

## The EDGE-style brand wordmark (KEY requirement)
The founder wants "LunaV" written normally with the PROJECT name in caps + accent color,
NOT "LunaV Studio" as one plain string. Markup pattern:

    <b>LunaV</b> <span>PROJECTNAME</span>

where `span` is the accent color. Apply per project:
- R-Tessera: `<b>LunaV</b> <span>R-TESSERA</span>` (GOLD `#C9A96E` — recolored 2026-08-13, was blue `#2f9bff`).
- LunaV EDGE: `<b>LunaV</b> <span>EDGE</span>` (already shipped in `templates/index.html`).
- LunaV itself: default brand renders `<b>LunaV</b> <span>STUDIO</span>` (turquoise
  `--mb-turquoise`); only when `branding.companyName` is set does it show the white-label name.

## Token-name crosswalk (TRAP — do not mix these up)
These are DIFFERENT variables in DIFFERENT repos. Using the wrong one silently breaks color:
- LunaV (Next): accent = `--mb-turquoise` (default `#0a84ff` iOS blue; dark theme `#2f9bff`).
  Also `--hairline`, `--txt-primary`, `--txt-secondary`, `--glass`, `--glow-turquoise`.
- LunaV EDGE (HTML): accent = `--lv-turq` (`#2f9bff`). Also `--lv-hairline`, `--lv-txt1/2/3`,
  `--lv-void`, `--lv-panel`, `--lv-glow`. Its `--lv-*` set mirrors LunaV Studio globals.css.
- R-Tessera (CSS): NO token system — hardcode the same hex values inline.
  Accent is GOLD `#C9A96E` (recolored 2026-08-13; was turquoise `#2f9bff`). Hairline
  `rgba(150,175,205,0.14)`, glass `rgba(20,23,28,0.82)`. Do not import `--mb-turquoise`; it
  does not exist there. When porting a LunaV style to R-Tessera, translate `--mb-turquoise` →
  `#C9A96E` (R-Tessera's own gold), NOT LunaV's teal.

## Pitfalls (encode these — they bit this session)
1. **Fixed-header offset.** Adding a `position: fixed; top:0` header bar hides any floating
   panel docked at `top: 14px`. After adding the header, shift those panels DOWN by the
   header height+gap: R-Tessera's `.mcp-trigger` moved `top:14px → top:70px` and `.mcp-drawer`
   `top:64px → top:120px`. Always re-audit every `position: fixed` element's top offset.
2. **LunaV EDGE base-button margin.** The global `button { margin-top: 12px }` rule pushes
   header buttons down. The `.hdr-btn` header class MUST set `margin-top: 0` and
   `box-shadow: none` to override the gradient primary `button` style, or the header misaligns.
3. **Remove old banners, don't layer.** R-Tessera previously had floating `.rt-banner` /
   `.rt-railing` labels. Replace them with the real header — delete the old CSS blocks so
   they don't linger (grep-confirm they're gone).
4. **Active-state wiring.** R-Tessera's "Projects" header button reflects `showProjects`;
   "Data Layers" reflects any of the overlay toggles. Wire `is-active` to real state, not static.
5. **Cesium globe z-index.** R-Tessera header `z-index` must sit ABOVE the Cesium canvas
   (use z-index 35; the globe chrome is ~z-index 8). Keep globe draggable by leaving the
   header as the only pointer-capturing top element.

6. **Static footer hidden by a flex-clip (LunaV Project Homepage).** The Project Homepage
   page wraps the component in `<main class="ph-page">` (`height:100vh; overflow:hidden`),
   root is `height:100dvh` flex column. A `ph-shell` set to `height:100%` grabs the FULL
   column height and shoves a trailing static footer off-screen below the viewport — invisible.
   FIX: footer `position: fixed; left:0; right:0; bottom:0; z-40` (top-layer bar, unclippable)
   + `ph-shell { flex:1 1 auto; min-height:0 }` so the map fills above it. Lift any
   `bottom:16px` corner widgets (remarks card, save indicator, base selector) to `bottom:52px`+
   so they clear the fixed bar. R-Tessera's full-width footer uses `justify-content:
   space-between` (left teal dot + "3D Engine Online", right brand); base selector at `bottom:60px`.
   General recipe → `vite-build-verification` `references/flex-column-footer-hidden.md`.

## Current verified R-Tessera state
- **Header:** LunaV glass bar. Brand `<b>LunaV</b> <span>R-TESSERA</span>` (R-TESSERA GOLD
  `#C9A96E`). Buttons: Projects + Data Layers left-aligned; "LunaV Studio" link pinned right
  (`margin-left:auto` / `.rt-push-right`) → lunavsolution.vercel.app. As of 2026-08-13 the
  `.rt-hdr-link` is SQUARE (`border-radius: 2px`) to mark it as a priority cross-project link.
- **L-logo box:** GOLD `linear-gradient(135deg,#C9A96E,#a8854f)` + gold glow (recolored 2026-08-13,
  supersedes the earlier GREEN `#00e5c3` mark).
- **Buttons (mixed square/soft-edge, 2026-08-13):** priority actions are SQUARE (`border-radius: 2px`,
  thin 1px hairline) — `.proj-actions .mb-btn`, `.link-pinpoint .mb-btn-primary`, `.rt-hdr-link`;
  labs-nav `.labs-nav-btn` uses `4px`. Ambient chrome (Menu, Labs header, panels) stays SOFT `10px`.
- **Typography (Geist, 2026-08-13):** R-Tessera now uses Geist via `@fontsource/geist-sans` +
  `@fontsource/geist-mono` wired in `src/index.css` (`--font-geist-sans/mono` vars + `body`
  family). Cesium entity labels (WeatherEntities/SituationalEntities) use **Geist Mono** — written
  as `'Geist Mono'` (single quotes), NOT `&quot;Geist Mono&quot;`. LunaV already referenced Geist
  via CSS vars; syncing only needed the box change there.
- **Projects:** opened from the top banner "Projects" button (no edge tab). Panel corners
  squared (`border-radius:12px` all sides). Header label "PROJECTS (n)" matches Map Control's
  "MAP CONTROL" (11px / 700 / 0.14em / `#7dd3fc` / uppercase).
- **Bottom railing:** full-width LunaV-family bar — teal dot + "LunaV R-Tessera — 3D Engine
  Online" (left) / "LunaV R-Tessera - ROVER-R" (right).
- **Default view:** 3D globe + Esri World Imagery satellite (`raster='satellite'`, `scene='3d'`).
- **Node click:** flies to node AND opens its LunaV STUDIO Project Homepage in a NEW BROWSER
  TAB via the public share URL (`/project/<id>/home?share=<token>`). No in-app detail card
  (this removes the overlap with the project list panel). List rows fly-to only.
- **PALETTE FROZEN ON SYNC:** R-Tessera stays GOLD `#C9A96E`; LunaV stays teal `--mb-turquoise`.
  A "sync the buttons/font to both" task must NOT recolor — only change border-radius, borders,
  font-family/font-size. (If a stray cyan/blue leak is found in R-Tessera, recolor to its OWN gold,
  not LunaV's teal.)

## Verification
Run `scripts/verify-theme.sh` after edits — it greps each repo for the expected brand
string, header class, glass blur, and confirms the old R-Tessera banner CSS is gone, and
runs `npm run build` on LunaV + R-Tessera (Luna-EDGE is verified by loading the Flask app:
`cd ~/luna-edge && source .venv/bin/activate && python -c "from app import app"`).

## Support files
- `references/token-crosswalk.md` — full token table + the three header implementations side by side.
- `scripts/verify-theme.sh` — grep + build verification across all three repos.
