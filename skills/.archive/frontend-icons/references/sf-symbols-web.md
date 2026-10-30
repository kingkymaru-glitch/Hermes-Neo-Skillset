# SF Symbols → Web: the dead-end, and how to beat it

## What actually exists on a Mac
- `SF Symbols.app` at `/Applications/SF Symbols.app` — a GUI viewer/reference.
  NO scripting bridge, NO `osascript` dictionary, NO export CLI. `mdfind
  "kMDItemFSName == 'SF Symbols*'"` confirms the app exists; that's the limit of
  automation.
- The symbols ship as `Apple Symbols.ttf` (`~/Library/Fonts`,
  `/System/Library/Fonts`), NOT as addressable glyphs for the web. A browser
  cannot reliably `font-family: 'SF Symbols'` + `content: '\u{...}'` — the
  private-use codepoints are unstable and cross-browser support is nil.

## Therefore
Do NOT hunt for an export path or a font-face trick. Reproduce the glyph as
inline SVG. SF Symbols' visual language is deliberately simple:

- viewBox `0 0 24 24`
- stroke width 1.5–1.6
- `stroke-linecap="round"` + `stroke-linejoin="round"`
- `fill="none"` for outlines, `fill="currentColor"` for solid accents
- optional `opacity="0.55"` on secondary arcs for depth (e.g. outer radio waves)
- `stroke="currentColor"` so the icon inherits text color → theme-aware for free

## Eyeballing for fidelity
Open the glyph in SF Symbols.app, note the anchor geometry (where bars meet,
radii, the fold lines), then encode those coordinates. You do not need the exact
path data — a faithful approximation reads as "professional" and matches the
design language. If the user wants a SPECIFIC symbol's exact geometry, ask for
the SF Symbols glyph name (e.g. `antenna.radiowaves.left.and.right`) and mimic
its anchors.

## Why not emoji
Emoji (📡 🗺️ 🔗 🤖) render inconsistently across OS/browser, ignore your color
theme, and break the minimal/tech aesthetic. User explicitly rejected them for a
glassmorphic dashboard. Use SVG.
