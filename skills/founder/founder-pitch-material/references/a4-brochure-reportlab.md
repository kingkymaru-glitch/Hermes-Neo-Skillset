# A4 brochure with reportlab — working recipe

Built 2026-09-28 for the LunaV Studio 2-page A4 brochure. Source kept at
`~/Desktop/lunav-brochure/` (`build_brochure.py`, `brochure_lib.py`, `assets/`),
PDF delivered to `~/Desktop/LunaV-Studio-Brochure.pdf`.

## Setup

```bash
mkdir -p ~/Desktop/<name>/assets && cd ~/Desktop/<name>
python3 -m venv .venv
./.venv/bin/pip install reportlab svglib pypdf
```
(Homebrew python3 = 3.14 works; the Xcode `/usr/bin/python3` 3.9 has no pyobjc/Quartz,
so there is NO native CoreGraphics route.)

## Brand mark (vector, from the canonical SVG)

```python
from svglib.svglib import svg2rlg
from copy import deepcopy
MARK = svg2rlg("assets/lunav-mark.svg")          # ~/Documents/R-Tessera/public/favicon.svg
def mark(c, x, y, size):
    d = deepcopy(MARK); f = size / d.width; d.scale(f, f); d.drawOn(c, x, y)
```
The SVG's P3 `color(display-p3 …)` fills log "Can't handle color" warnings — harmless;
the `#863bff` base paths render correctly, and the mark reads well on the dark page.
Do not use `qlmanage -t favicon.svg`: it pads the 48×46 SVG onto a white 1024×1024 canvas.

## Page + palette

A4 = 595.276 × 841.89 pt, margin 34. Top-origin helper `T = lambda v: H - v` keeps the
layout readable; every element is placed with `bottom_y = T(top_edge + height)`.

Dark brand palette (matches the live app): bg `#0A0E14`, band `#0E1520`, panel `#121B28`,
panel-hi `#16202F`, hairline `#233149`, turquoise `#00E5C3`, violet `#863BFF`,
lavender `#EDE6FF`, amber `#FFB020`, red `#FF5A5F`, text `#EEF3F8/#A9B6C7/#6E7E93`.
Fonts: base-14 Helvetica (no embedding, prints anywhere, supports `—` and `·`).

## Reusable primitives (`brochure_lib.py`)

`panel()`, `rule()`, `txt()`, `head()` (letter-spaced uppercase label), `wrap()`
(returns the y below the last line), `bullets()`, `chip()/chiprow()/chipflow()`
(chipflow wraps chips into rows inside `maxw` — use it for any chip strip),
`arrow()`, `mark()`, `donut()`, plus drawn glyphs `g_cube/g_pin/g_layers/g_report/
g_chart/g_share/g_globe/g_cpu/g_camera`. Abstract geometric glyphs in one accent colour
look intentional and cost nothing.

## Verification — do all three

1. **Structure:**
   ```python
   from pypdf import PdfReader
   r = PdfReader("out.pdf"); assert len(r.pages) == 2
   for p in r.pages:
       b = p.mediabox; assert abs(float(b.width)-595.276) < 1 and abs(float(b.height)-841.89) < 1
   ```
2. **Content:** extract text, normalise whitespace, assert every intended string is
   present (wrapped lines break naive `in` checks), and assert overclaim words are ABSENT
   (`"10 minutes"`, `"guaranteed"`, `"ISO "`).
3. **Geometry audit** (catches what the eye misses): for every wrapped block compute
   `len(simpleSplit(text, font, size, width)) * leading` vs the available height; for every
   chip row compute `sum(stringWidth(s, font, size) + pad*2 + 1)` vs the available width.
   Keep the chip padding used by `chiprow` and `chipflow` IDENTICAL to `chip()`'s.
4. **Visual:** split pages with pypdf, render with `sips -s format png -Z 1500 page.pdf`,
   then `vision_analyze`. For a suspicious region, crop with PIL at 2× and ask again —
   the full-page view is too dense for reliable reading.

## Defects this recipe caught (check for these every time)

- Decorative card accent bar anchored at `y + height - 2.5` instead of `y` → stray line.
- Diagram elements bounded by the inner dashed box rather than the outer panel → 5pt spill.
- Label wider than its own box (50.8pt label in a 49pt box) → glyph clipped.
- Chip strip totals (`522pt`) exceeding the available width (`461pt`) → run-off the page.
