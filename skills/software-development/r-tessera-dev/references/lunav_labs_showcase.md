# LunaV Labs Showcase — reference detail

Public roadmap page on R-Tessera. Added 2026-08-12. Deep-link:
`r-tessera.vercel.app/?view=labs`.

## Files
- `src/labs/projects.js` — data only. Exports `labsProjects` array.
- `src/labs/LabsPage.jsx` — maps over `labsProjects`, renders cards + badges.
- `src/App.css` — `.labs-*` rules appended (glass theme, status badges).
- `src/App.jsx` — `view` state, header button `LunaV Labs`, conditional render,
  `?view=labs` deep-link + `replaceState`.

## Data schema (`src/labs/projects.js`)
```js
export const labsProjects = [
  {
    name: 'LunaV Studio',          // MUST follow "LunaV ***" prefix
    status: 'LIVE',                // 'LIVE' | 'BETA' | 'R&D'
    liveUrl: 'https://lunavsolution.vercel.app', // optional "Visit live ↗"
    function: '…',                // ~200-word, value-first
    advantage: '…',
    technology: '…',
    preview: undefined,            // omit → "Preview coming soon" box
    // OR:  preview: { type: 'image', src: '/labs/x.png', caption: '…' }
    // OR:  preview: { type: 'text', body: 'Output: geo-referenced .glb' }
  },
  // LunaV Tessera (LIVE), LunaV Scan (LIVE), LunaV Edge (BETA), LunaV Sonar (R&D)
]
```
Edit ONLY this file to add/rename/reorder cards. No JSX change needed.

## Status badge CSS
```css
.labs-badge.live { background: rgba(0,229,195,0.16); color:#00e5c3; border-color:rgba(0,229,195,0.4); }
.labs-badge.beta { background: rgba(47,155,255,0.16); color:#7db4ff; border-color:rgba(47,155,255,0.4); }
.labs-badge.rnd  { background: rgba(255,179,64,0.16); color:#ffb340; border-color:rgba(255,179,64,0.4); }
```

## Layout
- `labs-root` = `position:fixed; inset:0; z-index:45` (sits above the globe).
  Flex column: `.labs-header` (reuses `.rt-header` but `position:relative` so it
  scrolls with the page, NOT fixed over the viewport) + `.labs-main` (scrollable,
  `padding: 28px clamp(16px,5vw,64px) 40px`) + `.rt-railing` footer.
- `.labs-grid` = `grid-template-columns: repeat(auto-fill, minmax(330px,1fr))`.
- `.labs-preview-empty` = `aspect-ratio:16/9` hatched box with
  "PREVIEW COMING SOON".

## Key decisions (from session)
- NO react-router in this repo. View switching is `view` state + `?view=` param.
- The globe `<header>` MUST be inside the `{view==='globe' && (<>…</>)}`
  fragment, or the globe header + Labs header stack (double banner bug).
- Multi-element `&& (…)` blocks need a `<>…</>` wrapper or the build fails.
- App renamed "R-Tessera"→"LunaV Tessera" on the public roadmap to honor the
  `LunaV ***` prefix; deployed app URL unchanged.

## Verification that passed (browser, not just build)
`npm run preview -- --port 4181`, browser → `http://localhost:4181/?view=labs`:
- one header (LunaV LABS + "← Back to Globe"), 5 cards, correct statuses,
  PREVIEW COMING SOON boxes. Clicked Back → live `<Canvas>` globe + controls.
- `npm run build` exit 0 (only the Cesium 500kB chunk-size warning, harmless).
