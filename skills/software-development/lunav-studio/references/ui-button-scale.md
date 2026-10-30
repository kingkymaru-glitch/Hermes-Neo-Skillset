# UI Button Scale — LunaV Studio

`.mb-btn` is the shared button class used by every surface in the app: header
(Home, Project Home, the six tabs, Settings), the finding drawer, the Defect
Detail modal, dashboard, login, admin, CCTV/Vision, and every modal. Editing it
in `src/app/globals.css` therefore restyles the whole app in one edit.

## Tier table (compact restyle)

| tier | class | font | padding | radius | use |
|---|---|---|---|---|---|
| standard | `.mb-btn` | 0.66rem | 4px 6px | 6px | everything |
| dense | `.mb-btn mb-btn-sm` | 0.62rem | 4px 5px | 6px | drawer / defect-modal tab strips |
| menu row | `.mb-menu-item` | 0.68rem | 8px 12px | — | header Settings + readOnly kebab rows |
| pill | `.status-chip` | 0.6rem | 3px 8px | 999px | severity + action pills (shared class) |
| active | + `.mb-btn-primary` | inherits | inherits | 2px | the selected tab |

`.mb-btn-danger` / `.mb-btn-armed` only recolour; they inherit the scale.
Note `.mb-btn-primary` forces `border-radius: 2px` while inactive buttons are
6px — the selected tab reads as a sharper corner than its neighbours. That is
intentional contrast, but do not "fix" it by rounding the active state unless
the founder asks.

## Rule: width comes from the LABEL, not the padding

A button is `text + 2×padding + 2×border`. At this scale the text dominates:
"3D Digital Twin" is ~84px of text against 12px of padding, so cutting side
padding from 10px to 6px narrows the button only ~6%. When the founder asks to
"reduce the width of all buttons/tabs", padding reduction will NOT visibly
deliver it — the only lever that moves width meaningfully is the FONT SIZE.
Say that plainly and offer the font-size change up front rather than iterating
padding twice and reporting a 2px win.

Height and radius move the "slicker" read more than width does: a 27.8px-tall,
10px-radius pill reads as roomy where a 25.8px-tall, 6px-radius box reads as a
flat segmented strip at almost the same width. When asked for "sleeker tabs",
cut vertical padding and radius first.

## Rule: buttons sit INSIDE the label band, not above it

The app's existing text scale:

| element | class | font |
|---|---|---|
| field label | `.mb-label` | 0.64rem |
| panel header | `.dash-panel-header` | 0.68rem |
| standard button | `.mb-btn` | 0.66rem |
| menu row | `.mb-menu-item` | 0.68rem |
| input / select | `.mb-input` | 0.85rem |
| brand name | `.lv-brand-name` | 0.85rem |

A button below 0.64rem is smaller than the label beside it and reads as a
defect rather than a style. When the founder asks to "shrink all buttons to
match" some compact surface, land at or above 0.66rem and keep only the
space-constrained strip one tier tighter. Do not drag the entire app down to
the smallest tier — that inverts the type hierarchy.

## Never shrink the 44px phone tap target

`@media (max-width: 640px)` sets `.mb-btn { min-height: 44px;
padding-top/bottom: 0.65rem }`. It appears AFTER `.mb-btn` in the file, so it
wins on source order at equal specificity. A desktop padding reduction cannot
collapse touch targets. Confirm by reading the compiled CSS rather than
assuming — the compiled chunk is minified but keeps the media query intact.

## Inventory overrides before shrinking a shared class

Some call sites pin their own size and are therefore untouched by a global
change — they silently become the new outliers:

- `mb-btn text-[0.6rem] px-2 py-1` — dashboard table row actions (already tiny)
- `mb-btn mb-btn-primary w-full py-3` — login submit (stays tall via `py-3`)
- `mb-btn flex h-9 w-9` — readOnly kebab (fixed 36px box)

Grep the class name across `src/` and count per file before editing:
`grep -rn "mb-btn" src --include=*.tsx -l | while read f; do printf "%4d  %s\n" "$(grep -o 'mb-btn' "$f" | wc -l)" "$f"; done | sort -rn`

## Replace ad-hoc menu-row classNames with a real class

The header Settings/kebab rows were `block w-full px-4 py-2.5 text-left text-sm`
(14px — larger than the old buttons), so shrinking `.mb-btn` alone does not
reach them. `.mb-menu-item` is the class. `patch` with `replace_all` on the
identical className string is safe here because it is a complete className
value and not a substring of a longer line; grep with `-F` first to confirm
the count matches the number of replacements you expect.

## Verify a restyle by geometry, not by eyeballing

Render the real compiled CSS with the real markup and measure. Do not rely on
"it looks fine" — the failure mode is invisible at a glance.

1. Copy the compiled chunk out of the build: `ls -t .next/static/chunks/*.css | head -1`.
   Serving it from the repo root can 404; copy it next to the test page instead.
2. Build a page that reproduces the container markup verbatim (same Tailwind
   classes, same inline styles) and link the compiled CSS. **Write kebab-case in
   the fixture's `style=` attribute** — see the pitfall below.
3. Measure per button: `getBoundingClientRect()` for width/height/right, and
   `getComputedStyle` for `fontSize` / `padding` / `borderRadius`.
4. Assert the four things that actually break:
   - **wrapped labels** — any button taller than ~1.6× the shortest button in the row
   - **overlap** — pairwise rect intersection among the row's buttons
   - **overflow** — any button's `right` past its container's `right`
   - **air** — the gap between adjacent buttons must be unchanged from before
5. Repeat at desktop, tablet, and phone widths.

## PITFALL — `getComputedStyle` lies about `::-webkit-*` pseudo-elements

Reading a slider's track/thumb via
`getComputedStyle(el, '::-webkit-slider-runnable-track')` returns the
ORIGINATING ELEMENT's box — a 4px track reports 18px, a 13px thumb reports the
full input width, `backgroundColor` comes back transparent. Chrome does not
resolve `-webkit-` pseudo-elements through the two-argument form. Do NOT conclude
the rule failed: confirm with pixels instead — screenshot the control, or crop and
upscale it, and read the rendered colour bands. `getComputedStyle` on the element
ITSELF (`fontSize` / `padding` / `borderRadius`) is reliable; only the
pseudo-element form is not.

## PITFALL — raw HTML `style=` attributes need kebab-case

When the fixture is a hand-written `.html` file, `style="tableLayout:fixed"` is
INVALID CSS. Browsers parse a `style` attribute as CSS, where the property is
`table-layout`. React's `style={{ tableLayout: "fixed" }}` object form maps camelCase
to kebab-case for you; a raw HTML fixture does not. The declaration is silently
dropped, the table falls back to auto layout, the `<colgroup>` percentages stop
applying, and every column-width measurement is wrong — the fixture looks fine and
lies. Write `style="table-layout:fixed;min-width:760px"`.

## PITFALL — set the viewport BEFORE navigating

`Emulation.setDeviceMetricsOverride` does not reflow an already-loaded page.
Set the metrics first, THEN `goto_url` — otherwise every width you measure is the
previous viewport's, and the phone-width run silently repeats the desktop result
(same numbers at 390px and 1280px is the tell).

## `.mb-btn-ghost` was an undefined class

It was applied to five buttons (admin, dashboard, CCTV/Vision cancel rows) with no
definition in `globals.css`, so they silently rendered as plain `.mb-btn`. It now
carries a TEMPORARY orange audit highlight (border + fill + glow, `!important`) so
the founder can spot every instance before a real ghost style is chosen — remove
the highlight once the variant is decided.

An undefined class is silent, not an error: nothing warns you. Grep the class name
across `src/` before assuming a button is unstyled, and when the founder needs to
SEE a set of instances, paint them an unmistakable colour (border + fill + glow,
not text colour alone) rather than listing file:line in prose.
