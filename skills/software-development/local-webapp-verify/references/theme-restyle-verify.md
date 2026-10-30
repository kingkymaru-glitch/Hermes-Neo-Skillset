# Verifying a CSS / theme restyle in a served page

## When
You restyled a page (palette swap, dark mode, brand colors) and must prove the
new colors actually paint — on a standalone HTML file or any served page.

## Why computed styles, not screenshots
You cannot read images, so the proof has to come from `getComputedStyle`. That is
stronger than a screenshot anyway: it names the exact rule that won.

## Recipe
Serve the file (Pitfall 2), then in one `js()` call return a JSON map of the
selectors that carry the theme:

```js
(() => {
  const g = s => { const e = document.querySelector(s); return e ? getComputedStyle(e) : null; };
  const p = (s,k) => { const c = g(s); return c ? c[k] : 'MISSING'; };
  return JSON.stringify({
    bodyBg: p('body','backgroundColor'),
    cardBg: p('.card','backgroundColor'),
    header: (p('header.top','backgroundImage')||'').slice(0,55),
    h2Color: p('.card h2','color'),
    bdrCellBg: p('.st.bdr','backgroundColor'),
    offCellBg: p('.st.off','backgroundColor'),
    theadBg: p('thead th','backgroundColor'),
    segOnBg: p('.seg button.on','backgroundColor'),
    primaryBtn: (p('button.primary','backgroundImage')||'').slice(0,50),
    rows: document.querySelectorAll('tbody tr').length
  }, null, 1);
})()
```

Read the result as an assertion list:
- `MISSING` = selector not found → your selector is wrong, not the theme.
- `backgroundColor: rgba(0,0,0,0)` with a non-empty `backgroundImage` = the color
  is a gradient; read `backgroundImage` instead. A gradient cell is NOT unstyled.
- Also assert the app still WORKS, not just that it is colored: row counts, a stat
  value, a rendered cell count. A theme edit that also killed the JS must not be
  reported as done.

## Pitfall — custom property used as a foreground color
A `:root` variable usually gets reused in two roles: a fill/background AND a text
color on a light surface (`.rmember{color:var(--brand)}`, `.card h2{color:var(--brand)}`,
`.st.off{color:var(--brand)}`). Changing only the variable's VALUE follows both
roles, so when the palette flips from light-background/dark-text to a dark
background, those text colors become dark-on-dark and the UI goes unreadable with
no error.

Rule: before swapping a palette, grep every use of the variable and split it into
fill-role and text-role. Give text-role uses their own light value (`--ink` /
`--on-dark`) rather than the brand color. Do the same for hardcoded hexes sitting
in those same rules.

## Pitfall — don't patch a whole <style> block with the patch tool
A theme restyle touches most rules in the block, so `old_string` would be the
entire block: a huge, fragile fuzzy match. Splice it programmatically instead —
write the new CSS to a scratch file, then replace the text between the tags:

```bash
python3 - <<'PY'
import io
p='/path/to/file.html'
src=io.open(p,encoding='utf-8').read()
css=io.open('/scratch/new.css',encoding='utf-8').read()
a=src.index('<style>')+len('<style>'); b=src.index('</style>')
io.open(p,'w',encoding='utf-8').write(src[:a]+'\n'+css+src[b:])
PY
```

Then sweep for leftovers: grep the file for every old-palette hex and confirm
zero hits, and grep for the new ones to confirm they landed.

## Pitfall — inline styles written by the script
Theme colors are often also hardcoded in `style="color:#999"` attributes and in
`style="..."` strings inside the script's generated HTML. The `<style>` block sweep
will NOT catch those. Grep the whole file for the old hexes across markup AND
script, not just the CSS block.

## Pitfall — back up before an in-place restyle
A restyle is a broad, hard-to-reverse diff. Copy the original aside first
(`cp file.html file_vN.html`) so the founder keeps both, and say in the report
that the edit was in place and where the backup is.

## Pitfall — keep semantic colors semantic
When the user asks for "gold and dark blue", they mean the brand/accent palette.
Do not recolor status colors (error red, holiday red, warning amber) into the new
palette — those carry meaning and must stay distinguishable. Say in the report
which colors you deliberately left alone.
