# Placing screenshots on the LunaV Labs hero site (verified 2026-08-13)

Live site: **https://lunav-labs-eight.vercel.app** (repo `~/lunav-labs`,
github.com/kingkymaru-glitch/lunav-labs). Vercel auto-deploys on commit as
`maru <kingkymaru@gmail.com>`.

## The founder's theme filter (verbatim, then "2 tones lighter")
He provided this baseline for a boxed image:
```css
.insight-image-box { position:relative; width:100%; aspect-ratio:1/1;
  background:#0f1720; border:1px solid rgba(255,255,255,.06); overflow:hidden; }
.insight-image-box img { width:100%; height:100%; object-fit:cover;
  opacity:.85; filter:contrast(1.05); }
```
"just make it 2 tone lighter" → I use `opacity:.88` + `filter:contrast(1.05)
brightness(1.28)`. Tune brightness if he wants it lighter/darker.

## Optimization (screenshots → JPEG, huge size drop)
Raw screenshot PNGs are huge (2918×2236 = 3.5MB; 4112×2406 = 3.7MB) and stay big
as PNG (sips PNG re-encode only got 3.5→2.7MB). JPEG is the win:
```bash
cd ~/lunav-labs/src/assets
sips -s format jpeg -s formatOptions 82 --resampleWidth 1600 "<src>.png" --out "<name>-opt.jpg"
# 2918px→1600 ≈ 452KB ; 4112px→1000 ≈ 92KB
rm -f "<src>.png"   # don't ship the heavy original
```

## Wiring into App.jsx
- Import: `import <var> from './assets/<name>-opt.jpg'`
- Render inside the target box. For the "Family" card (Page 4), the cards are
  `PRODUCTS.map` in `content.js`; add an optional field (e.g. `img:'studio3d'`) to
  ONLY the target product, then branch in JSX:
  ```jsx
  {p.img === 'studio3d' ? (
    <div className="lv-cap-visual v-studio v-cap-image">
      <img src={studio3d} alt="..." className="lv-cap-img" />
    </div>
  ) : (
    <div className={`lv-cap-visual v-${p.visual}`}>...animation...</div>
  )}
  ```

## CSS — keep the app header in frame
The crop must keep the screenshot's top header/logo bar visible:
```css
.<box> img { position:absolute; inset:0; width:100%; height:100%;
  object-fit:cover; object-position:center top;
  opacity:.88; filter:contrast(1.05) brightness(1.28); }
```
`object-position:center top` (computed `50% 0%`) is the critical bit — without it
`cover` centers the image and cuts the top header.

## Verify after deploy
1. Build green; `ls dist/assets/` shows the new `<name>-opt-<hash>.jpg`.
2. Commit as `maru <kingkymaru@gmail.com>` + push (webhook fires).
3. Poll until the hashed asset is served: check the JS references the image hash,
   the CSS has the filter, and `curl -o /dev/null -w "%{http_code}"` on the image =
   200.
4. Browser (text-first, no screenshots): confirm the target card has an `<img>`
   with `loaded:true` while the other cards still show their animation.

## Disambiguation trap (this caused a wrong edit)
R-Tessera ALSO has a Labs showcase at `~/Documents/R-Tessera/src/labs/projects.js`
(in-app `?view=labs`). The founder's product *descriptions* and screenshot placement
are for the STANDALONE hero (`~/lunav-labs/src/content.js`). Verify which repo/source
the "Labs" request targets before editing — grep `App.jsx` for the import if unsure.
