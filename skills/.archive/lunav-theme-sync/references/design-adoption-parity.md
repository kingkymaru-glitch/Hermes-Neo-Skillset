# Design-adoption parity — why an adopted LunaV Labs hero looks "cheap"

## Symptom (observed 2026-08-13)
MARU admired the LunaV Labs landing hero (`~/lunav-labs`), then tested adopting that
design into the R-Tessera "Labs" page (`~/Documents/R-Tessera/src/labs/LabsPage.jsx`)
served locally. The adoption "does not meet the standard — font and boxing looks cheap"
vs lunav-labs. Root cause is NOT a missing component; it's four missing design-system
properties that lunav-labs carries and the port dropped.

## Reference (the sharp one)
- `~/lunav-labs/src/App.jsx` — hero markup, line-mask `.lv-reveal` headline, `.lv-title`
- `~/lunav-labs/src/content.js` — `HERO` (eyebrow, `lines`, `emLine`/`emWord`, sub, CTAs)
- `~/lunav-labs/src/index.css` — Geist font, tight `letter-spacing`, glass + veil + scan
- Served locally: `cd ~/lunav-labs && npx vite --port 4204 --host` (HTTP 200)

## Adopted (the cheap one)
- `~/Documents/R-Tessera/src/labs/LabsPage.jsx` — `.labs-hero` with plain `<h1>LunaV Labs</h1>`
- `~/Documents/R-Tessera/src/App.css` lines ~774–833 — `.labs-hero`, `.labs-root`, `.labs-project`
- `~/Documents/R-Tessera/src/index.css:17` — `font-family: ui-sans-serif, system-ui, ...` (the cheap tell)
- `.labs-hero h1` uses `background: linear-gradient(135deg,#ffffff,#e7cfa0)` (gold/tan foil) +
  `font-weight:800`, no tracking discipline, no `<em>`, no reveal.

## The 4 root causes (each independently makes it look cheap)
1. **System font, not Geist.** lunav-labs loads Geist (next/font). R-Tessera inherits
   `ui-sans-serif, system-ui` → heavier, looser, generic. Fix: add Geist (or Inter via
   `@fontsource`) and apply to `.labs-root`.
2. **Gold/tan gradient on dark.** `linear-gradient(#fff,#e7cfa0)` clipped to text = "gold foil".
   Fix: turquoise/ice gradient (`#fff → #7dd3fc` or the family `--mb-turquoise` hex `#2f9bff`).
3. **Accent clash.** R-Tessera badges/brand use gold `#C9A96E`. The Labs overlay should match
   the LunaV family turquoise, not the globe's legacy gold. Swap `#C9A96E` → `#2f9bff` in the
   Labs page scope only (leave globe chrome as-is unless told).
4. **No motion/sharpness system.** lunav-labs' sharpness = masked multi-line reveal, veil,
   scan lines, deliberate `letter-spacing`. R-Tessera Labs is static. Add a `.lv-reveal`-style
   fade/line-mask to the hero headline.

## Minimal fix recipe (scoped to the Labs page — do NOT touch the globe)
- Import Geist in `index.css` (or main.jsx): `@import '@fontsource/geist-sans';` then
  `.labs-root { font-family: 'Geist Sans', ui-sans-serif, system-ui, sans-serif; }`
- `.labs-hero h1` → `background: linear-gradient(135deg,#ffffff,#7dd3fc); -webkit-background-clip:text;
  background-clip:text; color:transparent; letter-spacing:-0.02em; font-weight:700;` + wrap an
  `<em>` around the key word in the JSX (e.g. "above and below") tinted turquoise.
- Swap `.labs-badge.live` gold → turquoise `#2f9bff` (Labs scope only).
- Add reveal: `.labs-hero { opacity:0; transform:translateY(12px); transition:.5s; } .labs-hero.in{opacity:1;transform:none;}` and toggle `.in` via IntersectionObserver (or reuse the existing pattern).

## Verify
Serve R-Tessera (`npm run dev`, default :5174) and eyeball against lunav-labs on :4204.
Confirm: font matches, headline is turquoise not gold-foil, badges turquoise, hero fades in.
Do NOT claim done until visually compared — build pass ≠ visual parity.

## Note on accent authority
lunav-labs is the *reference* for the Labs/landing surface. The R-Tessera globe chrome uses
green `#00e5c3` mark + gold legacy accents by separate decision (see SKILL.md "Current verified
R-Tessera state"); that is a different surface. Keep them distinct unless MARU merges them.
