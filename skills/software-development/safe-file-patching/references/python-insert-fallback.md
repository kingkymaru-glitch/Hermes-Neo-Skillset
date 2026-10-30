# Python-script fallback when `patch` cannot win (RINA AdminPanel Level column)

## When this is needed
`patch` (mode=replace) can fail repeatedly on the SAME multi-line JSX/TSX edit:
- "Escape-drift detected" on any block containing a Tailwind class string (the
  `">` terminator gets serialized as `\"`).
- "Found N matches" on lines that contain `—` (em-dash) repeated many times, so
  a minimal anchor like `{u.department || '—'}` is not unique.

After 2 failed patch attempts, switch tools. `write_file` + `terminal` (Python)
never mangle quotes or em-dashes — only the `patch` JSON serializer does.

## Verified recipe
```python
path = '/Users/kamarulhk/riina/src/components/AdminPanel.tsx'
lines = open(path, encoding='utf-8').read().split('\n')

new_block = '''                      <td className="px-3 py-2 align-top">
                        {isEditing ? (
                          <input type="number" min={0} className="w-16 ..." value={d?.level ?? ''} />
                        ) : (
                          <div className="...">{u.level ?? '—'}</div>
                        )}
                      </td>'''

anchor = 'w-44 space-y-1'            # unique token just AFTER the insertion point
i = next(j for j, l in enumerate(lines) if anchor in l)
td = i
while not lines[td].strip().startswith('<td'):   # walk up to the next cell's <td>
    td -= 1
for l in reversed(new_block.split('\n')):
    lines.insert(td, l)
open(path, 'w', encoding='utf-8').write('\n'.join(lines))
```
Run with `terminal`: `python3 /tmp/insert.py`. Then `npx tsc --noEmit` to confirm.

## Why this beats fighting the matcher
The patch tool's find/replace is implemented over a serialized JSON representation
of your strings; the serializer escapes `">` and the matcher then sees a quote that
isn't in the file. A Python script operates on the real bytes, so class strings,
em-dashes, and apostrophes are all literal and safe. Prefer this for inserting a
whole new JSX/HTML cell next to quote-heavy neighbors.
