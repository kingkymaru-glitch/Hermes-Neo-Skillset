# LunaV Labs — the TWO surfaces, and where the copy lives (2026-08-13)

## Problem this exists to prevent
MARU says "edit LunaV Labs" and the agent edited the WRONG surface, forcing a full
revert + re-apply. "LunaV Labs" is ambiguous across two distinct codebases. Resolve
WHICH one he means BEFORE editing anything.

## Surface A — the standalone LunaV Labs hero landing page (default meaning)
- Repo: `~/lunav-labs` (github.com/kingkymaru-glitch/lunav-labs)
- Live: **https://lunav-labs-eight.vercel.app**
- Stack: Vite + React 19 + Cesium (resium), `vite-plugin-cesium`.
- **Copy lives in `src/content.js`.** Exports `HERO`, `OPPORTUNITY`, `PROOF`,
  `PRODUCTS`, `INSIGHT`, `CASE`, `CTA`.
  - The 5 product cards are `PRODUCTS[]`, each `{num, name, status, desc, visual}`.
  - **Edit `PRODUCTS[].desc` to change a card's description.** (Cards: Studio,
    R-Tessera, Scan, Edge, Sonar.)
  - `App.jsx` imports these from `./content.js` and renders `PRODUCTS.map(...)` at
    ~line 142. That import is the ground truth for where copy lives.
- **Stale files do NOT drive the hero page (do NOT edit for hero copy):**
  - `src/projects.js` — a scrollytelling variant (`focus`/`pin` globe coords,
    `function`/`advantage`/`technology`). Not imported by App.jsx.
  - `src/labs/` — empty directory. Dead.
  - Verify by grepping App.jsx's imports before trusting the README or an older note.
- Deploy: `npm run build`, commit as `maru <kingkymaru@gmail.com>`, `git push origin
  main`. Live URL's JS asset hash changes each deploy; confirm the new string via
  `curl -s <live>/assets/index-*.js | grep -c "<text>"`.

## Surface B — the in-app Labs showcase inside R-Tessera
- Repo: `~/Documents/R-Tessera`
- **Header "LunaV Labs" button NO LONGER opens this surface (2026-08-13).** The
  GlobeView.jsx header button was changed to an external `<a>` pointing at Surface A
  (`https://lunav-labs-eight.vercel.app`, new tab) — the header now links OUT to the
  hero. The in-app surface is still reachable only via the `?view=labs` deep-link
  (App.jsx reads `view === 'labs'` on load).
- Files: `src/labs/LabsPage.jsx` (UI) + `src/labs/projects.js` (data, `labsProjects[]`
  with `function`/`advantage`/`technology` blurbs).
- He calls THIS "the Labs page in R-Tessera" / "the in-app showcase" — rarely bare
  "LunaV Labs."

## Decider
- Bare "LunaV Labs" / "the hero" / "landing page" → **A (lunav-labs)**.
- "R-Tessera's Labs" / "the Labs page" alongside the globe or R-Tessera → **B**.
- When unsure, state the repo path + which surface you're editing in your summary
  BEFORE writing.

## Revert recipe (if you hit B when he meant A)
1. Find the last good commit: `git log --oneline -6`.
2. Restore the file: `git checkout <pre-edit-commit> -- <file>` (e.g.
   `git checkout cb1c9ab -- src/labs/projects.js`).
3. Confirm the wrong strings are gone (`grep -c "<bad text>" <file>` → 0) and the
   original is back.
4. Build, commit as `maru <kingkymaru@gmail.com>`, push. Note the revert is a NEW
   commit (e.g. `69ed8c4`) — the original commits stay in history.
5. Re-apply the intended copy to Surface A, rebuild, push, verify live.

## Surface A page-number → section mapping (nav counts 01–07)
The floating nav shows `01/07 … 07/07`. When MARU says "Page N" he means the nav
count (1-indexed), which matches `data-idx` minus 1:
- Page 01 = HERO (idx 0)
- Page 02 = OPPORTUNITY (idx 1) — the cited-stats band
- Page 03 = PROOF (idx 2) — "What a living twin returns"
- Page 04 = CAPABILITIES (idx 3) — the 5 product cards
- **Page 05 = INSIGHT (idx 4)** — philosophy quote + the RIGHT-side visual box
- Page 06 = CASE STUDY (idx 5) — headline + paragraphs + metrics
- Page 07 = CTA footer (idx 6)

Gotcha (hit 2026-08-13): "Page 5, the box on the right" = the **INSIGHT** section's
`.lv-insight-visual` (the right column of its `1fr 1.1fr` grid), NOT the CASE-study
image. The CASE `.lv-case-image` sits on the LEFT of its grid. The `.insight-image-box`
class name the user pastes is a strong hint it's the INSIGHT box. When in doubt, read
`App.jsx`'s section order + the grid `grid-template-columns` to tell left from right
before editing.

## Placing a screenshot/image into the INSIGHT right box (theme filter)
- Copy the asset into the repo: `mkdir -p src/assets && cp "<src>" src/assets/<Name>.png`,
  then `import <name> from './assets/<Name>.png'` in `App.jsx` (Vite bundles it).
- Markup: replace `<div className="lv-insight-visual"><div className="lv-lattice" /></div>`
  with `<div className="lv-insight-visual insight-image-box"><img src={...} className="lv-insight-img" /></div>`.
- CSS on `.lv-insight-visual img`: `position:absolute; inset:0; width/height:100%;
  object-fit:cover; opacity:0.88; filter:contrast(1.05) brightness(1.28);` — the
  user's stock filter is `opacity:0.85; filter:contrast(1.05)`; he asked for "2 tones
  lighter", which reads as adding ~`brightness(1.28)`. Adjust brightness on his feedback.
- **Proven optimization + crop-fix (2026-08-13):** screenshots as PNG bundle huge (a 2918px
  shot ≈ 3.7MB) and `object-fit: cover` CROPS the top off a UI screenshot (the R-Tessera
  header vanished) because the box (1.7:1) is wider than the image (1.3:1). Two fixes:
  1. **Shrink it** on macOS with `sips` (8x smaller, 3.7MB → 452KB, still crisp for a screenshot):
     `sips -s format jpeg -s formatOptions 82 --resampleWidth 1600 <src>.png --out src/assets/RT-SS-opt.jpg`
     PNG doesn't compress for UI shots — JPEG at q82 is the win. Import the `.jpg`, then
     `rm` the old `.png` so it doesn't ship.
  2. **Pin the crop to the top** so the header bar stays in frame (it was centered by default):
     add `object-position: center top;` to the `.lv-insight-visual img` rule alongside
     `object-fit: cover`.
  - Verify in the browser that the image actually loaded with the intended crop/filter, NOT
    just that the build passed: `img.complete && img.naturalWidth > 0` (a 3.7MB asset may take
    a moment to fetch — poll or wait before declaring "rendered"), and
    `getComputedStyle(img).objectPosition` should read `50% 0%`.
