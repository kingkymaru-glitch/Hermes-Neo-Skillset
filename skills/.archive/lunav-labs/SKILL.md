---
name: lunav-labs
description: Edit the standalone LunaV Labs site (~/lunav-labs).
version: 1.0.0
author: hermes
license: MIT
metadata:
  hermes:
    tags: [lunav, labs, marketing, scrollytelling, vite, react, cesium, maru]
    related_skills: [r-tessera-dev, lunav-family-ui, lunav-studio, cesium-scrollytelling, vite-build-verification]
---

# LunaV Labs (standalone site)

## When to Use
Use whenever MARU says "edit / change content in LunaV LABS", "edit the Labs page", "place this image on LunaV Labs", "rewrite a LunaV Labs product description", or names the LunaV Labs site / its deploy URL. This is the standalone marketing site, distinct from R-Tessera's in-app Labs showcase — getting the two confused caused a user correction (see the CRITICAL rule below).

## CRITICAL — which repo is "LunaV Labs"?
There are TWO things called "LunaV Labs". MARU means the **standalone** site below. Mixing them up caused a major user-correction ("Neo u made huge mistake!").

1. **Standalone LunaV Labs site (THIS skill)** — repo `~/lunav-labs`, deploy `https://lunav-labs-eight.vercel.app`. A McKinsey-style scroll-driven marketing/scrollytelling page: fixed Cesium globe stage on the right, narrative sections (HERO → Opportunity → Return → Family → Insight → Case → CTA). THIS is what MARU calls "LUNAV LABS" and wants edited.
2. **R-Tessera's in-app Labs showcase** — `/Users/kamarulhk/Documents/R-Tessera/src/labs/` (LabsPage.jsx + projects.js), opened by the header "LunaV Labs" button inside r-tessera.vercel.app. Do NOT edit this when MARU says "edit LunaV Labs". R-Tessera's header button now links OUT to the standalone site (new tab).

Rule: "edit / change content in LunaV LABS" → work in `~/lunav-labs`. If a task names "R-Tessera header LunaV Labs button" that's the only time R-Tessera is relevant (and its button should point to the standalone URL, not the in-app page).

## Repo facts
- Path: `~/lunav-labs`, git remote `github.com/kingkymaru-glitch/lunav-labs.git`, Vercel auto-deploy on push.
- Deploy URL: `https://lunav-labs-eight.vercel.app` (the primary production; `lunav-labs.vercel.app`/`lunavlabs.vercel.app` are unrelated v0/Next placeholders — ignore them).
- Stack: Vite + React 19 + CesiumJS (GlobeStage.jsx fixed right-half globe, scroll-driven dolly-out). No router, single App.jsx.
- **Content lives in `src/content.js`**, NOT projects.js. It exports HERO, OPPORTUNITY, PROOF, PRODUCTS, INSIGHT, CASE, CTA. `App.jsx` imports all of them (line 4-5).
  - Product descriptions = `PRODUCTS[].desc` (5 products, indexed 01-05: Studio, R-Tessera, Scan, Edge, Sonar).
  - `src/projects.js` and `src/labs/` are STALE leftovers not imported by anything — do not edit them.
- Section order (nav counts 01-07): 0 Hero, 1 Opportunity, 2 Return/PROOF, 3 Family/PRODUCTS (the 5 cards), 4 Insight, 5 Case, 6 CTA.

## Editing product descriptions
Edit `PRODUCTS[].desc` in `src/content.js`. Status/num/name/visual stay. "Page N" by the floating nav = data-idx (0-based): Page 5 = Insight, Page 4 = Family/cards, Page 6 = Case. Ask/clarify if a "page number" is ambiguous against the card index.

## Product-screenshot placement workflow (repeatable, MARU-standard)
MARU keeps product screenshots under `~/Desktop/Marketing LunaV/<Product>/`. To place one in a card or section box:

1. **Optimize**: copy into `src/assets/`, then `sips -s format jpeg -s formatOptions 82 --resampleWidth 1000 <src>.png --out <name>-opt.jpg`. This cuts a ~3.5MB PNG to ~90-140KB. Verify with `sips -g pixelWidth -g pixelHeight`. (PNG screenshots compress poorly; always convert to JPEG.)
2. **Wire**: add the `img` field to that product in `src/content.js` (e.g. `img: 'studio3d'`), import the JPEG in `App.jsx`, and add it to the `CAP_IMG` map. The card render is generic: `{p.img ? <div className="lv-cap-visual v-cap-image"><img className="lv-cap-img" .../>{animation divs}</div> : <animation-only div>}`.
3. **CSS** (`.v-cap-image img` in `src/index.css`): `position:absolute; inset:0; width/height:100%; object-fit:cover; object-position:center top; opacity:0.88; filter:contrast(1.05) brightness(1.28)`. `object-position:center top` keeps the app's header bar in frame (centering crops it out — the recurring bug).
4. **Animation overlay**: the card's globe/grid/scan/nodes divs are absolutely positioned; give them `.v-cap-image .lv-cap-* { z-index:2 }` so the animation floats OVER the image. This is the desired look ("overlap the animation on top of the image").
5. **Verify**: `npm run build`, then confirm the new asset hash is in the live bundle AND the asset returns HTTP 200 at `https://lunav-labs-eight.vercel.app/assets/<hashed-name>`. Minified CSS turns `z-index: 2` into `z-index:2` (grep without the space).

## Pitfalls
- Do not commit a large original PNG; it ships to the bundle. Delete the source PNG after producing the JPEG.
- Vercel deploy takes ~30-60s after push; the live HTML's asset hash updates on roll. Confirm the real deploy URL (lunav-labs-eight) — the v0 placeholders at lunavlabs/lunav-labs.vercel.app serve unrelated Next.js apps.
- Commit author must be `maru <kingkymaru@gmail.com>` for the Vercel webhook to fire (same as other MARU repos): `git -c user.name=maru -c user.email=kingkymaru@gmail.com commit ...`.
