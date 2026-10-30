# Flex footer pushed off-screen (LunaV Project Homepage)

## Symptom
Bottom-rail footer (the "LunaV Studio — 3D Engine Online" / "LUNAV STUDIO —
ROVER-R" bar) is in the DOM, `z-30`, but NOT visible. User says "the rail isn't
seen / ensure it's on the top layer above the map."

## Root cause
Root element is `height: 100dvh` flex column: `<nav>` / `<ph-shell>` / `<footer>`.
The map area CSS was:

    .ph-shell { position: relative; height: 100%; width: 100%; }

`height: 100%` makes ph-shell grab the FULL column height, leaving no room for
the `shrink-0 h-9` footer — so the footer is rendered *below* the 100dvh box,
off-screen. (The workspace pages avoid this because their map area uses
`flex: 1`, not `height: 100%`.)

## Fix
    .ph-shell { position: relative; flex: 1 1 auto; width: 100%; min-height: 0; }

Now ph-shell fills the space ABOVE the footer; the footer sits as the bottom
row of the column, above the map (map is `position:absolute; inset:0; z-index:1`
INSIDE ph-shell, so it cannot paint over the footer, which is a sibling).

## Why this matters for the family sync
When you "adopt" the workspace bottom-rail onto the Project Homepage, the
homepage's `height:100%` shell will silently eat it. Always switch the
container to `flex: 1 1 auto; min-height: 0` first.
