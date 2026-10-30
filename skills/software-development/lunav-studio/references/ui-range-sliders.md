# Range Sliders — LunaV Studio

## Why this needed a recipe

The app had **14 `input[type="range"]`** (transform drawer Move/Rotate X·Y·Z,
box + dimension sizes, LUNAV Edge frame + confidence) with **no styling at all**
apart from Tailwind `accent-[var(--mb-turquoise)]`. `accent-*` only tints the NATIVE
control, so every slider rendered as a default browser slider — chunky track,
platform-shaped thumb, inconsistent across Safari/Chrome/Firefox.

There is no component wrapper and no `.mb-slider` class: the inputs are raw
`<input type="range">` with `className="w-full accent-[var(--mb-turquoise)]"`.
Style them from `globals.css` on the element selector. `accent-*` becomes inert
once you set `appearance: none` — that is expected, not a bug.

## The style (in `src/app/globals.css`)

```css
input[type="range"] {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 18px;              /* hit area — the track itself is 4px */
  margin: 0;
  background: transparent;   /* track is drawn by the pseudo-elements */
  cursor: pointer;
  vertical-align: middle;
}
input[type="range"]:focus { outline: none; }

/* WebKit / Blink / Safari */
input[type="range"]::-webkit-slider-runnable-track {
  height: 4px; border-radius: 2px;
  background: var(--dash-inset);
  border: 1px solid var(--hairline);
}
input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none; appearance: none;
  width: 13px; height: 13px;
  margin-top: -5.5px;        /* (thumb 13 - track 4 - borders 2) / 2 */
  border-radius: 50%;
  background: var(--mb-turquoise);
  border: 2px solid #04110e;
  box-shadow: 0 0 6px rgba(0, 229, 195, 0.5);
  transition: box-shadow 0.15s ease;
}
input[type="range"]:hover::-webkit-slider-thumb,
input[type="range"]:focus-visible::-webkit-slider-thumb {
  box-shadow: 0 0 10px rgba(0, 229, 195, 0.8);
}

/* Firefox */
input[type="range"]::-moz-range-track {
  height: 4px; border-radius: 2px;
  background: var(--dash-inset);
  border: 1px solid var(--hairline);
}
input[type="range"]::-moz-range-thumb {
  width: 11px; height: 11px; border-radius: 50%;
  background: var(--mb-turquoise);
  border: 2px solid #04110e;
  box-shadow: 0 0 6px rgba(0, 229, 195, 0.5);
}

input[type="range"]:disabled { cursor: not-allowed; opacity: 0.45; }
```

## Rules that make it work

- **Separate the hit area from the track.** Put `height` on the INPUT (18px) and
  the thin `height` on the pseudo-element (4px). If you instead set the input's
  height to 4px, the slider is nearly impossible to grab — the founder will
  report it as "the slider is broken", not "the slider is thin".
- **`margin-top` centres the thumb on the track.** For WebKit the thumb is
  positioned relative to the track, so `margin-top: -(thumb - track - borders)/2`.
  Get it wrong and the thumb floats above or below the line.
- **Both engines need their own pseudo-elements.** `-webkit-slider-runnable-track`
  is WebKit/Blink/Safari; Firefox ignores it and needs `-moz-range-track` /
  `-moz-range-thumb`. Styling only the webkit pair leaves Firefox on the native look.
- **Mobile overrides the thumb, not the track.** Keep the 4px track on touch and
  enlarge only the thumb (20px, with `margin-top` recalculated) — a thick track
  on a phone looks like a progress bar.

## PITFALL — do not read the track/thumb back with `getComputedStyle`

`getComputedStyle(el, '::-webkit-slider-runnable-track')` returns the ORIGINATING
ELEMENT's box, not the pseudo's: a 4px track reports 18px, a 13px thumb reports the
full input width, `backgroundColor` comes back `rgba(0,0,0,0)`. Chrome does not
resolve `-webkit-` pseudo-elements through the two-argument form. Verify with
PIXELS instead — screenshot the control and read the rendered colour bands, or crop
and upscale it. A 6px-tall non-background band across the slider row is the 4px
track plus its two 1px borders: that is the confirmation.

## PITFALL — a leftover mobile rule silently wins

The old `@media (max-width: 640px)` block contained
`input[type="range"] { height: 28px; }` for touch. Adding a base
`input[type="range"] { height: 18px }` does NOT remove it — the media query comes
later in the file and wins on source order, so the mobile height stays 28px and any
new mobile sizing you add at the top of that block is overridden. When you touch a
shared control's sizing, grep for the selector across the WHOLE file, including
inside media queries, and delete the stale rule rather than adding a competing one.

## Verify

Same harness as the button restyle (`references/ui-button-scale.md`): copy the
compiled chunk next to a test page, reproduce the real markup, and assert
- the track band is thin (≤6px rendered) and continuous across the control
- the thumb is round and centred on the track, not floating
- the disabled slider is visibly muted but still shows a thumb
- set the viewport BEFORE navigating, or the phone run repeats the desktop result
