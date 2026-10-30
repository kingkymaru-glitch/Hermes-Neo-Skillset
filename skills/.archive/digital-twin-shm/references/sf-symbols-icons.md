# SF Symbols → clean inline stroke icons (my-digital-twin UI polish)

## Corrected finding (this session)
A terminal probe with `mdfind "kMDItemCFBundleIdentifier == 'com.apple.Symbols'"`
FINDS **SF Symbols.app is installed** on the user's Mac. BUT it has **no headless
CLI / scripting surface** to export exact glyph SVGs, and the system symbol font
is NOT present in `/System/Library/Fonts` or `~/Library/Fonts` (so you cannot
address a named glyph from CSS `font-family` in the browser). Prior notes that
claimed "SF Symbols not installed" are WRONG — the app is there, it just can't be
scripted.

## Technique (durable)
When the user wants "icons from my Mac's SF Symbols" to replace emoji, author
clean **inline stroke SVG icons** that match the SF Symbols aesthetic. They render
crisp at any size, inherit `currentColor`, and need no font/asset:
- `viewBox="0 0 24 24"`, `width`/`height` 22.
- `fill="none" stroke="currentColor" strokeWidth="1.6"`
  `strokeLinecap="round" strokeLinejoin="round"` (SF's rounded-humanist look).
- Use `<svg>` directly inside the `.action-glyph` span (replaces the emoji text).

## The four replacements shipped (command drawer menu)
- Sensor Clusters → **radio-tower**: signal arcs + base dot.
- Map Control Systems → **folded map**: two-page fold, second page at lower opacity.
- System Integrations → **link**: interlocked chain.
- Summon MARU AI → **cpu**: die rect + 8 pin stubs + center core (kept in
  `accent-ai` purple card).

## If the user names a specific glyph
Ask for the exact SF Symbols name (e.g. `antenna.radiowaves.left.and.right`,
`map`, `link`, `cpu`). Reproduce that glyph's exact geometry as a stroke path —
do NOT grab a random emoji. The app can't export it for you.
