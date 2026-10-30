# LunaV EDGE → R3 logo + LunaV LABS gold theme + R-Tessera Geist (2026-08-14)

## Context
Founder called twice on 2026-08-14:
1. First: "adopt LunaV Labs styling into EDGE; use R1 logo" → Cormorant Garamond serif wordmark + JetBrains Mono labels, keep EDGE blue.
2. Extended: "change logo to R3.png, remove its background, make the logo area match live R-Tessera font, and change EDGE's color theme to match LunaV LABS."

Final state = R3 mark + **gold/navy LunaV LABS palette** + **Geist** wordmark (R-Tessera's brand font). The blue `#2f9bff` era is OVER for EDGE.

## 1. R3 logo — copy + background removal
R3.png (on `~/Desktop`) is OPAQUE: a metallic "TR" monogram (blue letters + orange bar) on a solid light-gray (~205) background. No alpha.

Copy: `cp ~/Desktop/R3.png luna-edge/static/R3.png` (Flask serves `static/` → `/static/R3.png` automatically; NO new route).

Remove bg via PIL per-pixel chroma-key (neutral-light backgrounds key out; keep colored artwork):
```python
from PIL import Image
im = Image.open("/Users/kamarulhk/Desktop/R3.png").convert("RGBA")
W,H = im.size; px = im.load(); out = im.copy(); opx = out.load()
def near(c, t, tol=28):
    return all(abs(c[i]-t[i]) <= tol for i in range(3))
TARGET=(205,205,205)  # sampled background gray
for y in range(H):
    for x in range(W):
        r,g,b,a = px[x,y]
        if near((r,g,b), TARGET): opx[x,y]=(r,g,b,0)
out.save("luna-edge/static/R3.png")
```
~57% transparent; blue "TR" + orange bar intact. VERIFY with `vision_analyze` on the result before wiring in (confirm no holes eaten into letters, no gray specks).

Wire into BOTH `templates/index.html` and `templates/learn.html`: header brand mark + collapsed launcher pill:
`<div class="mark"><img src="/static/R3.png" alt="R3" /></div>`
Mark style — **NO back-layer box** (Founder: remove the box/frame behind the logo). Keep R3
**uncropped** (save full native canvas after keying; never crop — the logo height is intentional):
`.brand .mark, #launcher .mark { display:inline-flex; align-items:center; justify-content:center; background:none; border:none; border-radius:0; box-shadow:none; padding:0; }`
`.brand .mark img, #launcher .mark img { width:100%; height:100%; object-fit:contain; }`
No gold glow, no plate, no rounded container behind the TR.

## 2. Color theme → LunaV LABS gold/navy (replace ALL blue)
Old EDGE blue tokens → new gold set. Replace the `:root` block in BOTH templates:
```
--lv-void:#030508; --lv-panel:#0A1628; --lv-panel-raised:#111E2E; --lv-inset:#06101C;
--lv-hairline:rgba(240,235,227,0.14); --lv-hairline-strong:rgba(240,235,227,0.26);
--lv-turq:#C9A96E; --lv-ice:#E6D5B0; --lv-amber:#C9A96E;
--lv-red:#ff4d4d; --lv-green:#00c878;
--lv-txt1:#F0EBE3; --lv-txt2:rgba(240,235,227,0.62); --lv-txt3:rgba(240,235,227,0.38);
--lv-glow:0 0 18px rgba(201,169,110,0.35);
--lv-radius:14px; --lv-radius-sm:10px;
--lv-shadow:0 10px 30px rgba(0,0,0,0.55);
--lv-font:'Geist',ui-sans-serif,system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
--lv-serif:'Cormorant Garamond',Georgia,serif;
--lv-mono:'JetBrains Mono','Geist Mono',ui-monospace,monospace;
```
Then grep for leftover `rgba(47,155,255` (blue accent tints) — every one must become gold `rgba(201,169,110`. Spots that bit this session: `.brand .mark` glow, `.status.s-ws .dot`, `select/input:focus` ring, `.tab-link.active`, `.rail` bg, `.step.active`, `.railing .rail-dot`. Header bg also changed `rgba(20,23,28,0.82)` → `rgba(10,22,40,0.82)`.
**TWO BLUE RELICS THE FIRST PORT MISSED (founder caught them later — always grep these too):**
- `rgba(27,31,38` — the DARK-BLUE panel/rail ink. Appears in `.railing` (bottom bar), `.panel` (sidebar), and `#launcher` pill in `index.html`. Founder's exact complaint: "EDGE railings are dark blue, causing the looks of it to be off compared to LABS." Fix → Labs ink `rgba(3,5,8,0.85)` for header+railing, `rgba(10,14,20,0.6)` for side panels + launcher pill (matches Labs `.lv-top.scrolled` + `.lv-panel`).
- `#1b6fd0` — the BLUE PRIMARY-BUTTON GRADIENT. The base `button { ... }` rule still had `background: linear-gradient(135deg,var(--lv-turq),#1b6fd0); color:#fff` (old EDGE blue). Fix → gold `linear-gradient(135deg,#C9A96E,#a8854f); color:#0e1116; border:1px solid rgba(201,169,110,0.4); border-radius:6px;` (Labs `.lv-btn-primary`: gold fill, ink text, sharp ~6px, gold hairline). The `var(--lv-turq)` here resolves to gold `#C9A96E`, so only the `#1b6fd0` second stop + white text + `border:0` were the blue leak.
**FINAL EDGE ink (post all passes, = LunaV LABS):** header `rgba(3,5,8,0.85)`, bottom railing `rgba(3,5,8,0.85)`, side panel `rgba(10,14,20,0.6)`, launcher pill `rgba(10,14,20,0.6)`. (Earlier `rgba(10,22,40,0.82)` header was an intermediate; the founder's final nudge to `rgba(3,5,8,0.85)` matches Labs ink.)

## 3. Logo-area font → R-Tessera's Geist
R-Tessera's brand wordmark font is **Geist** (`~/Documents/R-Tessera/src/index.css` `--rt-font-sans`, used in `.rt-brand`). So the EDGE text wordmark adopts Geist:
- Google Fonts link (both templates): add `family=Geist:wght@300;400;500;600;700&family=Geist+Mono:wght@400;500` alongside the existing Cormorant/JetBrains.
- `.brand .name { font-family: var(--lv-font); font-size:1.18rem; font-weight:600; line-height:1; letter-spacing:0.005em; }` (Geist, NOT the Cormorant serif). Accent span: `color:var(--lv-turq)` (gold) + `font-weight:600` (drop the earlier `font-style:italic`).
- Keep Cormorant/JetBrains only for eyebrows/labels/panel-titles/rail headings (mono uppercase).

## 4. Header buttons — left-aligned, thin gold line, no green glow (99c7418)
Both EDGE pages' header buttons must be UNIFIED into one `.hdr-btn` style, LEFT-aligned right
after the logo (mirror the Detection / `index.html` layout — do NOT right-align like the old
Learning page `.tab-link`).
- Detection page (`index.html`): buttons already left via `.hdr-btn`.
- Learning page (`learn.html`): was right-aligned `.tab-link`; convert to `.hdr-btn` and place
  BEFORE any `.spacer`. Delete the now-dead `.tab-link` CSS block.
- Selected/active button = a SHARP THIN gold line — `border-color: rgba(201,169,110,0.9)` +
  `box-shadow: inset 0 0 0 1px rgba(201,169,110,0.22)` + faint gold wash. **NO green glow** —
  remove any `rgba(0,229,195,...)` active style.
- `.hdr-btn` base (Labs-sharp thin line): `border:1px solid var(--lv-hairline); border-radius:10px;
  font-size:0.7rem; font-weight:600; letter-spacing:0.12em; text-transform:uppercase;
  color:var(--lv-txt2);` hover `border-color: rgba(201,169,110,0.5); color:var(--lv-txt1);`.
- **PITFALL — nested brand div:** replacing the header mark via naive find/replace made
  `index.html` header become `<div class="brand"><div class="brand">...` (duplicate wrapper).
  After ANY header mark edit, grep `class="brand"><div class="brand"` and collapse to one.

## 5. Header nav buttons — KEEP SLOT ORDER IDENTICAL ACROSS PAGES (no "jumping" button)
EDGE has TWO headers (Detection `index.html`, Learning `learn.html`) that link to each other.
If the two pages list the buttons in DIFFERENT order, the active highlight moves to a different
physical slot and the clicked button appears to *hop sideways* between pages — MARU flagged this
as confusing ("does this make user confused with the swapping button locations").

Symptom we hit: Detection had `[AI Learning][AI Detection*]`, Learning had `[AI Detection][AI Learning*]`.
The inactive button sat in a different slot on each page, so clicking "AI Learning" (left on
Detection) landed you on a page where it was on the RIGHT. Fix = freeze ONE order on BOTH pages:
`[AI Detection] [AI Learning]` with the active button keeping its own slot. Only the `.active`
class changes; the label sequence never does.

Rule for any multi-page top nav: when pages link to each other, copy the EXACT button order from
the reference page to every sibling page. Verify by extracting each header's `<button>` text list
and asserting they are identical (active aside):
```python
import re
def order(f):
    hdr = open(f).read().split("<header>")[1].split("</header>")[0]
    return re.findall(r'<button[^>]*>([^<]+)</button>', hdr)
# order("index.html") must equal order("learn.html") as label lists
```
Also: the active state style must be the SAME class on both (we unified on `.hdr-btn`; the old
`.tab-link` on learn.html was the divergent one — delete it, don't keep both).

## 6. Logo sits on a same-color background → it "disappears" (R3 on navy header)
The raw R3.png is NOT just a gray-bg logo — its artwork carries a BAKED-IN navy plate behind the
"TR" that is *exactly* the header's `--lv-panel` (#0A1628). So after dropping it on the navy
header, the logo flattened into the background and looked dull/tacit — the "they don't even pay
attention to the details" failure mode. Two-part fix:

(a) **Key out the internal baked plate too**, not just the outer gray bg. After keying light
    backgrounds (min(r,g,b)>=170), ALSO key pixels that are dark-navy and bluish (the plate):
    `max(r,g,b) < 75 and b >= g`. That leaves only the blue TR + orange bar on true transparency.
    Keep the FULL native canvas — do NOT crop (MARU: "do not crop it in any way").
```python
from PIL import Image
src = Image.open("/Users/kamarulhk/Desktop/R3.png").convert("RGBA")
W,H = src.size; out = src.copy(); opx = out.load(); spx = src.load()
for y in range(H):
    for x in range(W):
        r,g,b,a = spx[x,y]
        if min(r,g,b) >= 170:            # light gray/white outer bg
            opx[x,y] = (0,0,0,0)
        elif max(r,g,b) < 75 and b >= g: # R3 internal navy plate (== header color)
            opx[x,y] = (0,0,0,0)
out.save("luna-edge/static/R3.png")      # full canvas, no crop
```
(b) **Add a soft, restrained halo** so the logo reads as a deliberate lit accent, NOT a hard box
    (MARU: remove the back box, but make it not dull). Apply to the mark container, not the img:
    `.brand .mark { background:none; border:none; border-radius:0;
       box-shadow: 0 0 8px 2px rgba(201,169,110,0.30), 0 0 20px 6px rgba(201,169,110,0.12); }`
    plus a faint drop-shadow on the img: `filter: drop-shadow(0 0 5px rgba(201,169,110,0.22));`
    This is a GLOW, not a plate — the logo still has no frame/box behind it. Tune opacity
    (0.30/0.12) up/down on verbal feedback; never reintroduce a solid background box.

Rule for any monochrome-on-matching-bg logo: a logo whose artwork plate == the surface color
needs (1) the baked plate keyed out and (2) a contrast halo/glow, otherwise it vanishes. The
"remove the back box" request and the "make it visible" request are reconciled by glow-not-box.

## 7. Verification (reuse every time)
```
# no R1, no blue, R3 present, Geist linked
grep -c "/static/R1.png" templates/*.html   # expect 0
grep -c "47,155,255"    templates/*.html     # expect 0  (blue accent tints)
grep -c "rgba(27,31,38" templates/*.html     # expect 0  (dark-blue panel/rail ink — Labs uses rgba(3,5,8,0.85))
grep -c "#1b6fd0"       templates/*.html     # expect 0  (blue primary-button gradient — gold now)
grep -c "/static/R3.png" templates/*.html     # >=1
grep -c "family=Geist"  templates/*.html     # 2
# detection tab untouched
grep -c 'id="feed"' templates/index.html && grep -c "requestAnimationFrame" templates/index.html && grep -c "ws.onmessage" templates/index.html
# live
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/        # 200
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/learn   # 200
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/static/R3.png  # 200
```
(Restart Flask after edits: `pkill -9 -f "app.py"; cd ~/luna-edge && .venv/bin/python app.py`. Browser tool is BLOCKED on localhost — use curl+grep, not screenshots.)

## 8. EDGE theme source of truth = LunaV LABS, NOT LunaV Solutions
EDGE's color/button language now mirrors **LunaV LABS** (`~/lunav-labs/src/index.css`), which is gold/navy ink — NOT LunaV Solutions (teal `#2f9bff`) and NOT the old EDGE blue. When syncing EDGE theme, read `lunav-labs/src/index.css` for the target tokens; do NOT copy LunaV's teal `var(--mb-turquoise)` or R-Tessera's gold into EDGE blindly. Key Labs facts to mirror:
- Ink surface `rgba(3,5,8,0.85)` (`.lv-top.scrolled`, `.lv-cta-footer`).
- Panel `rgba(10,14,20,0.6)` (`.lv-panel`).
- Accent gold `#C9A96E` (`.lv-accent`), gold glow `rgba(201,169,110,0.35)`.
- Buttons: `.lv-btn-primary` = solid gold `#C9A96E→` gradient + ink `#0e1116` text + NO border (sharp, ~6px); `.lv-cta-top` = transparent + 1px gold hairline. Both SHARP (no pill rounding).
- Font: Geist (also R-Tessera's brand font) — already applied to EDGE wordmark.
If MARU says "match LunaV LABS," he means THIS file's tokens, not the teal LunaV landing.

## Pitfalls
- R3 is OPAQUE with gray bg — naively dropping it in shows a gray box. Must chroma-key first.
- Don't keep the Cormorant italic wordmark — the FINAL call matched R-Tessera's Geist; italic serif reads as the superseded first pass.
- EDGE is no longer blue: any "keep EDGE blue" guidance (older skill text) is stale.
- Never touch Detection-tab JS (`#feed`, `requestAnimationFrame`, `ws.onmessage`) — CSS/logo only.
