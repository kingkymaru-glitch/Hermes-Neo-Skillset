---
name: frontend-icons
description: "Produce professional icons for web/React UIs. Covers the SF Symbols dead-end (SF Symbols.app has no export CLI; Apple Symbols.ttf is a system font not addressable by name in browsers) and the fix: hand-author inline SVG stroke icons (24x24 viewBox, 1.5-1.6 stroke, round caps/joins, currentColor) matching the SF Symbols aesthetic. Includes reusable copy-paste icon components."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [frontend, icons, svg, sf-symbols, ui, react]
---

# Frontend Icons — SF Symbols → Inline SVG

Use when a web/React UI needs clean, professional icons and the user points you
at SF Symbols (or the current emoji glyphs look unprofessional).

## The SF Symbols dead-end (verify before you go hunting)
- `SF Symbols.app` IS installed on macOS (`/Applications/SF Symbols.app`) but has
  **no scripting/export CLI** — you cannot `osascript` or shell it to dump a
  glyph's SVG.
- The system ships `Apple Symbols.ttf` (`~/Library/Fonts`, `/System/Library/Fonts`)
  but a browser CANNOT reference an SF Symbols glyph by name (no reliable
  `font-family: 'SF Symbols'; content: '\u{...}'` cross-browser, and the
  private-use codepoints aren't stable).
- `mdfind "kMDItemFSName == 'SF Symbols*'"` finds the app — that's as far as
  automation goes.

CONCLUSION: don't hunt for an export path. **Reproduce the glyph as inline SVG.**
SF Symbols' visual language is simple: 24×24 grid, 1.5–1.6 stroke, round line
caps + joins, optional filled accents. Matching that reads as "professional",
stays identical-crisp at any size, and `currentColor` makes it theme-aware.

## Workflow
1. Open `SF Symbols.app`, eyeball the target glyph (e.g.
   `antenna.radiowaves.left.and.right`, `map`, `link`, `cpu`) to get the
   geometry in your head.
2. Hand-author an inline `<svg viewBox="0 0 24 24">` with
   `stroke="currentColor" stroke-width="1.6" stroke-linecap="round"
   stroke-linejoin="round" fill="none"` for outlines; `fill="currentColor"`
   for solid accents. Optional `opacity="0.55"` on secondary arcs for depth.
3. Wrap as a tiny React component or drop inline. Size via `width`/`height`
   props. Inherits text color — no separate color prop needed.
4. Avoid emoji glyphs (📡🗺️🔗🤖) in professional UIs — the user explicitly
   dislikes them; they render inconsistently across platforms and break the
   design language.

## Fits-with / anti-patterns
- DON'T: `<span>📡</span>` for menu icons. DO: inline SVG or an icon component.
- DON'T: try to `require` an SF Symbols export or `@font-face` the system
  symbol font for web glyphs.
- DO: ask the user for the exact SF Symbols glyph name if you want pixel-fidelity
  to a specific symbol; otherwise approximate the geometry.

## Templates
- `templates/icons.jsx` — 4 reusable icon components (RadioTower, FoldedMap,
  Link, CpuChip) in SF-Symbols style, copy-paste ready.

## References
- `references/sf-symbols-web.md` — the dead-end verification detail + how to
  eyeball glyphs for accurate reproduction.
