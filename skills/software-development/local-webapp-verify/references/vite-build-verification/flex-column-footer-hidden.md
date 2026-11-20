# Pitfall — fixed-height footer hidden by a `height: 100%` sibling in a flex column

## Symptom
A bottom bar (footer / status rail) is in the JSX and "should" show, but the user
reports it's missing. No console error, no crash — the element is simply off-screen
or zero-height. Build + lint stay green (CSS geometry is never scope-checked).

## Root cause
The root is a flex column with a fixed total height, e.g.:
```html
<div class="flex flex-col" style="height: 100dvh">
  <nav>...</nav>
  <div class="ph-shell" style="height: 100%"> ...map... </div>   <!-- the culprit -->
  <footer class="h-9 shrink-0"> ... </footer>
</div>
```
`ph-shell { height: 100% }` grabs the FULL column height, leaving no room for the
footer — so the footer is pushed below the viewport (clipped by the parent's fixed
height / `overflow:hidden` wrapper). The element exists in the DOM; it's just not
visible. This bit the LunaV Project Homepage: a static footer was invisible, then
still invisible after restyling — the real cause was the `height:100%` sibling
eating the space, not the footer's own styling.

## Fix
Make the filler element flex-grow instead of taking a fixed 100%:
```css
.ph-shell { position: relative; flex: 1 1 auto; width: 100%; min-height: 0; }
```
`flex: 1 1 auto` + `min-height: 0` lets it shrink to fill the REMAINING space after
the nav and footer take their natural heights. The footer (`shrink-0 h-9`) then
sits as the bottom row, fully visible.

## Hardened alternative (guaranteed top-layer above a canvas/map)
If the footer must sit ABOVE an absolutely-positioned map/canvas regardless of flex
math, make it `position: fixed; left:0; right:0; bottom:0; z-40`. This sidesteps any
flex/overflow clipping entirely. Then lift any `position:absolute; bottom:Npx`
overlays (remarks card, save indicator) above it (e.g. `bottom: 52px` when the bar is
36px) so they don't sit under the fixed bar.

## Detection rule
When a flex-column child "disappears," check siblings for `height: 100%` (or
`height: 100vh`) that competes with a `shrink-0` sibling for the same fixed-height
parent. Prefer `flex: 1` for the filler. Also verify the wrapper isn't
`overflow: hidden` clipping a statically-positioned footer — `position: fixed`
escapes that.
