# LunaV UI density & button system

Depth for the SKILL.md rules "Button system & UI density", "UI density — inputs,
tables, alignment", and "Dead / undefined class audit". Load this when restyling
buttons or inputs, changing type scale, changing table density, or hunting a class
that has no CSS rule.

## Always-on rules for a UI change

- **Bump `APP_VERSION` in the SAME commit as the change.** The footer stamp is how the
  founder confirms he is looking at the new build; a stale stamp reads as "your change
  did not ship". `src/lib/app-version.ts` is a one-liner, and the git tag should match
  (`v0.47` for `V0.47`).
- **Confirm the stamp before you push.** After `npm run build`, grep the SERVED page for
  the version — `curl -s http://127.0.0.1:3210/login | grep -o 'V0\.[0-9]*'` — and check
  it matches the commit message. It is easy to write "bump V0.x → V0.y" in the commit body
  and never edit `src/lib/app-version.ts`; the founder then inspects a build whose footer
  still reads the old number and reports the change as missing.
- **Rebuild AND restart the local server before measuring.** `npx next start` serves
  the build it started with, so a running server keeps serving the OLD CSS and your
  measurement page silently reports the pre-change numbers. Kill it, `npm run build`,
  restart, then copy the fresh chunk (`ls -t .next/static/chunks/*.css | head -1`)
  next to the test page.
- **Sweep the class, not the instance.** When the founder says "inspect all" or "do the
  same for X", grep the class across `src/` and fix every call site in one pass. A
  partial fix reads as an inconsistent UI and will be reported again.
- **Port 3000 is not yours.** On this Mac it is the LUNAV Intel-M frontend; run LunaV's
  verification server on 3210.
- **Ship behind a version bump, then let the founder look.** He wants to see the result
  before the next decision, so push and point him at `http://localhost:3210` rather than
  describing it. Production follows from the push via Vercel.

## The button scale

Every button in the app comes from ONE shared class, so a single edit restyles all
of them. Current values (in `src/app/globals.css`):

| class | where | font | padding | radius |
|---|---|---|---|---|
| `.mb-btn` | every button app-wide | 0.66rem | 4px 6px | 6px |
| `.mb-btn-sm` | dense tab strips (finding drawer, Defect Detail modal) | 0.62rem | 4px 5px | 6px |
| `.mb-menu-item` | header Settings / kebab dropdown rows | 0.68rem | 8px 12px | — |
| `.mb-input.mb-input-sm` | toolbar search / filter controls | 0.66rem | 5px 8px | 6px |
| `.status-chip` | severity + action pills in tables and cards | 0.6rem | 3px 8px | 999px |

History: `.mb-btn` was 0.78rem / 10px 18px / 10px radius, then 0.66rem / 6px 10px
/ 7px. The compact scale puts it INSIDE the app's existing label band
(`.mb-label` 0.64rem, `.dash-panel-header` 0.68rem) rather than above it.

### Why 0.66rem and not lower
Buttons smaller than the labels beside them read as broken. The app's own scale is
0.58rem (stat tile keys) to 0.85rem (brand name, inputs), with labels at 0.64rem and
section headers at 0.68rem. 0.66rem sits in that band; 0.62rem (the `.mb-btn-sm`
tier) is already at the floor.

### The 44px tap target is a SEPARATE rule — protect it
`globals.css` ends with:

```css
@media (max-width: 640px) {
  .mb-btn, .mb-input, .mb-select, .mb-textarea, .mb-label { min-height: 44px; }
  .mb-btn { padding-top: 0.65rem; padding-bottom: 0.65rem; }
}
```

It comes AFTER `.mb-btn` in the file and wins on source order, so shrinking the
desktop padding never collapses the phone tap target. **Never edit that block** when
compacting the button scale — that is the one way to make the change dangerous.

### The capped-container case
The finding drawer is `sm:max-w-96` (384px) and holds 4 tabs (Details · Observation
· Certificates · Drawings & Files). Four default `.mb-btn` tabs total ~424px, so the
last one runs past the drawer edge and clips behind the panel border. Fix: a tighter
tier (`.mb-btn-sm`) plus `flex-wrap: wrap` on the strip as a guard so a future fifth
tab wraps instead of clipping.

## Verifying a shared-class restyle

Never eyeball it. Render the real compiled CSS plus the real markup and assert, in one
`js()` call: zero clipped children (`child.right > container.right`), zero wrapped
labels (`height > minHeight * 1.6`), zero pairwise overlaps, and **unchanged
inter-button gaps**. The full 5-step method is in `references/ui-button-scale.md`
("Verify a restyle by geometry"); the viewport-ordering trap and the fixture recipe are
in the `local-webapp-verify` skill (Pitfall 6 and the standard recipe).

The gap check is the one people skip. A shrink that leaves the container's `gap-*`
utility alone still gets reported as "extended gaps between buttons" — the air between
buttons grew even though no gap value changed. Compare the numbers, don't judge them.

## Compact input tier — `.mb-input.mb-input-sm`

Toolbar search/filter controls must sit on the button scale, not the form scale.
`.mb-input` is 0.85rem / 11px 14px / 10px radius — far larger than the button beside
it, so a search box next to filter pills reads as a different UI generation.

`.mb-input.mb-input-sm` is `5px 8px / 0.66rem / 6px radius`, applied as
`className="mb-input mb-input-sm"` (or `mb-select mb-input-sm`). Call sites: the
Certificates toolbar (3 selects + search), Docs toolbar (2 selects + search), the
Audit Report and Analytics zone filters, the dashboard rename + project search, and
the Vision camera filter.

**The selector MUST be compound.** `.mb-input` is defined further down `globals.css`
than the modifier, so a plain `.mb-input-sm` loses to it on source order and silently
does nothing — the input stays at 13.6px. Two equal-specificity rules resolve by source
order, and "later wins" even though the modifier is semantically stronger. Either place
the modifier after the base, or write the compound selector; the compound form is safer
because it survives re-ordering. Read the computed `fontSize` / `padding` back after
building — a silent no-op is the entire failure mode here.

Mobile keeps a tap target: the media query adds
`.mb-input.mb-input-sm { min-height: 40px }` (the base `.mb-input { min-height: 44px }`
loses to the compound selector, so it must be re-added explicitly).

## Table density — font and cell padding must shrink together

The Audit Report table was `<table class="w-full text-left text-sm">` with
`tableLayout: fixed` and `px-5 py-4` cells. Under fixed layout column widths are
percentages of the table, so 14px text plus 20px horizontal padding overflows the narrow
columns and the text breaks the row borders. The founder reported it as "the table
borders are broken", not "the font is too big" — fix the density, not the borders.

Fix: shrink BOTH. Table font `text-[0.66rem]`, cells `px-3 py-2`. Shrinking only one
side does not work: a compact font with wide padding still overflows, and wide-padding
cells at a compact font leave the table sparse.

The same defect existed in five more tables, all fixed the same way: the Certificates
register, Docs files, admin users (`text-sm` → 0.66rem), and the LUNAV Edge / LUNASCAN
job tables (`text-xs` → 0.66rem). Before any density pass, grep `<table` across `src/`
and check each one's font class and cell padding TOGETHER — the pair is the unit.

### Verify at the container's MINIMUM width, not the viewport

A `table-layout: fixed` table with `minWidth` stretches to fill its container, so at a
wide viewport every column is generous and nothing overflows. The breach only appears
at the floor. Measure with the test container pinned to the `minWidth` value (a 760px
floor → set the wrapper to 760px), never at the browser width. A pill that fits at
1280px can spill 46px past its column at 760px.

### Pills: the class is shared, so one edit standardises the app

`.status-chip` (FAIL / WARNING / PASS, and "Action needed" / "No action") is used in
the Audit Report, Certificates, dashboard cards, the Project Home badge, the finding
drawer and the Defect Detail modal. Editing it restyles every pill at once — which is
what "standardise the pills" means, and also why a per-cell override would be wrong.

Two rules that make a pill fit a column:

- **Shrinking the pill is necessary but not sufficient.** A pill is
  `text + 2×padding + gap + dot`; at 0.6rem a "WARNING" pill is ~83px, so the column
  needs ~107px to hold it with its cell padding. If the column is fundamentally too
  narrow, no legible font size will fit — widen the column instead, by rebalancing the
  `<colgroup>` percentages and taking the width from the long text columns.
- **`white-space: nowrap` is required.** Without it a pill whose text is slightly too
  long WRAPS onto a second line inside its cell — it stays inside the column, so it
  looks like a fit, but the row doubles in height and the pill reads as broken. Assert
  `pillHeight` is the single-line value, not just `pill.right <= cell.right`.

### Rebalance BOTH variants of a variant table

The Audit Report `<colgroup>` is written per variant —
`<col style={{ width: readOnly ? "12%" : "13%" }} />` — because the read-only
(client-share) view has an extra Action column. A rebalance tuned for the inspector
view leaves the read-only view breaching: its Severity column needs the same ~15%
(a WARNING pill is ~83px regardless of view), and its Action column holds a BUTTON
("Action: Yes", ~54px), not a pill, so it needs ~11% too.

When a table has an editor/viewer variant:

1. Grep the `<colgroup>` for `readOnly ?` — if present the widths are per-variant and
   BOTH need rebalancing. A single set of percentages cannot serve both.
2. Check the columns that exist in only ONE variant: the extra read-only column carries
   its own control (a button, a textarea), which can breach exactly like a pill.
3. Assert the percentages SUM TO 100 for EACH variant. An over-100 colgroup makes the
   browser rescale every column and silently invalidates the arithmetic you just did.
4. Verify BOTH variants by rendering each as its own fixture page and asserting zero
   breaches in each. Measuring only the default view is how a second breach ships.

### A cell's content box is `cell width - 2×cell padding`

When checking "does this control fit its column", compare against the CONTENT box, not
the border box. A pill can sit inside the cell's border box while overlapping the cell's
padding and ending 3px from the next column — technically not a breach, visibly cramped.
Compute `cellWidth - 2*paddingX` and require the control to be under that.

### An empty-state placeholder below a state pill is noise

A cell that renders a placeholder (an em dash) when it is empty, DIRECTLY ABOVE a pill
that already carries that same state, states the same thing twice and gets reported as
visual clutter — "there is a '-' before every No action pill". Drop the placeholder and
its spacer margin; render the content only when it exists
(`{value?.trim() && (<div>…</div>)}`, and gate the margin on the same condition).

Keep placeholders on empty INPUTS (a textarea with a placeholder string) — those tell
the user where to type and are not redundant with anything.

## Sibling flex groups must share one `items-*` value

The header nav has a brand group and a tab group as siblings. The brand group was
`flex items-end gap-2`; the tab group was `flex items-center gap-2`. Because the brand
block (logo + name + project title) is TALLER than the buttons, `items-end` anchored
Home/Project Home to the brand block's bottom edge while the tabs sat on the nav's
centre line — the two rows ended up ~5px apart, reported as "Project Home and 3D Digital
Twin shifted badly".

When two sibling groups must have their controls on one axis, both must use the same
`items-*` value. `items-center` on both puts every child on the parent's centre line.
`items-end` / `items-start` are only safe when every child in the group is the same
height.

**Verify alignment numerically, not by eye:** assert every button in the nav shares the
same `getBoundingClientRect().top` (delta 0.00px), not "looks level". A 5px offset is
invisible at a glance and obvious in the numbers.

## Gap tightening is a container edit, not a button edit

Tightening the gap between buttons is a `gap-*` change on the CONTAINER, not a padding
change on the button. "Tabs against each other" is the container gap (8px → 4px) and
requires no `.mb-btn` edit at all. Strip the gap values across every tab container in
one pass — header tabs, drawer tabs, defect-modal tabs, homepage nav, zone strips — or
some surfaces stay loose and the result reads as inconsistent.

## Dead / undefined class audit

A class can be used all over the markup while having NO rule in the CSS — those
controls silently render as the base class and nothing errors. Common after a rename or
a half-applied design system.

Recipe:
1. Grep the class name across `src` (markup) and across `globals.css` (definition).
   Markup-only hits with no CSS rule = dead class.
2. For each dead class, apply a TEMPORARY loud highlight — thick bright border + fill +
   glow, `!important` so inline overrides cannot mask it — and comment the block
   "TEMPORARY — remove once the style is decided". The founder wants to SEE every
   instance before choosing a style, not be handed a list of them.
3. Verify the highlight landed on EVERY size variant: the same class usually carries
   several inline padding overrides (`px-4 py-2 text-xs`, `px-2 py-1 text-[0.6rem]`, …).
   Render one of each and read `getComputedStyle` for border / background / colour.
4. Include a CONTROL (a normal `.mb-btn` in the same render) so it is provable the
   highlight is not leaking onto unrelated buttons.
5. Ship the highlight behind a version bump, let the founder locate the instances, then
   strip it and apply the real style.

Known instance: `.mb-btn-ghost` was used on 5 buttons with no definition — the Admin
link on the dashboard and admin pages, plus Cancel ×2 and Use My Location in
`CctvVisionPage`. All are secondary actions, so a real ghost style should be a quiet
outline, not a filled button.

## Other dead / legacy classes seen
- `.mb-btn-ghost` — used, undefined (see above).
- Watch for classes that only ever appear in markup after any design-system pass; the
  grep-in-both-places check is cheap and catches them all at once.
