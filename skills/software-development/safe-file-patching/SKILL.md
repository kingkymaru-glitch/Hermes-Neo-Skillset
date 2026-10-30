---
name: safe-file-patching
description: Apply patch-tool find/replace edits to source files without tripping the serialization "escape-drift" error, especially in TSX/JSX/HTML with Tailwind classes (rgba(...) etc.) that end a token with `">`. Use whenever a patch call fails with "Escape-drift detected".
---

# Safe file patching (avoiding escape-drift)

The `patch` tool (mode=replace) rejects an edit when the `old_string`/`new_string`
you send appear to contain a *spurious* escaped quote — the tool reports:

> Escape-drift detected: old_string and new_string contain the literal sequence
> `'\\"'` but the matched region of the file does not. This is almost always a
> tool-call serialization artifact where an apostrophe or quote got prefixed with
> a spurious backslash. Re-read the file with read_file and pass old_string/new_string
> without backslash-escaping '"' characters.

## What actually triggers it
The artifact is produced by the serialization layer when a line in your
old/new string ends a token with the two characters `>` immediately after a
closing double-quote — i.e. `">`. This is extremely common in:
- Tailwind classNames inside JSX/TSX attributes, e.g.
  `className="px-3 py-6 text-[rgba(30,18,48,0.55)]\">No users yet...`
- Any HTML/JSX text node that follows an attribute on the same line.

The `>` right after `"` is what the serializer mangles into `\"`.

## Workaround (the reliable pattern)
1. Do NOT try to include the problematic `">` segment in old/new.
2. Re-read the exact bytes with `read_file` (note the line numbers).
3. Patch the **smallest unique ASCII-only substring** around the change instead.
   Example that failed (full class string with `">`):
     old: `<tr><td colSpan={5} className="px-3 py-6 text-center text-[rgba(30,18,48,0.55)]\">No users yet...`
   Working minimal patch:
     old: `colSpan={5}`   new: `colSpan={6}`
   The surrounding long class string is left untouched and the edit applies.
4. For a *new* line insertion (e.g. adding a `<th>`), keep the surrounding
   context to lines that do NOT end in `">`. Insert before the empty `<th></th>`
   or after a plain line, never as part of a string that terminates with `">`.
5. If a `replace` still refuses, split the change into two smaller `replace`
   calls, each on an ASCII-only unique anchor.

## Many known strings to change (copy passes, version bumps, docs/status syncs): script it, assert each target

When a change touches more than a handful of known strings — a copy/wording pass, a version bump
across a doc, a status sync — do NOT fire N `patch` calls. Write one small Python script holding
explicit `(old, new)` pairs, and assert each `old` occurs **exactly once** before replacing; abort
the whole script otherwise.

```python
for old, new in ((A_OLD, A_NEW), (B_OLD, B_NEW)):
    n = src.count(old)
    if n != 1:
        raise SystemExit(f"ABORT: expected 1 occurrence, found {n} for:\n{old[:140]}...")
    src = src.replace(old, new, 1)
P.write_text(src, encoding="utf-8")
```

Why: it is atomic, and it fails LOUDLY on the first stale target instead of silently skipping it. A
remembered string that no longer matches is exactly the signal you want — that is how a stale version
header or an out-of-date status line gets caught rather than half-updated. It also bypasses the
escape-drift serializer entirely, because the script reads real bytes.

Run it with the project's own interpreter (`<venv>/bin/python script.py`) when it imports project
deps. Then verify with `head` / `grep -n '^## '` on the file — do not trust the exit code alone.

See references/scripted-bulk-replacement.md for the full recipe and the verification step.

## General rules
- Prefer short, unique anchors (`colSpan={5}`, `Only Super Admin ...`, `canManageUsers`,
  a function name) over long multi-line blocks that happen to end in `">`.
- Multiple identical lines: add enough surrounding context (a neighboring unique
  line) to make `old_string` unique, OR use `replace_all` only when every
  occurrence should change.
- Only use minimal ASCII anchors when the full-string patch fails; full-context
  patches are still preferred for ordinary edits (they're safer against drift).

## Pitfalls
- **A whitespace-only patch swallows the following line.** If `old_string` ends in a
  newline that `new_string` omits, the match consumes that newline and the next line is
  joined onto the selector — `.mb-btn-armed {\n` → `.mb-btn-armed {` produced
  `.mb-btn-armed {  border-color: …` on one line. Never send a patch whose new_string is
  the old_string minus trailing whitespace: it changes nothing and mangles the file.
  Re-read the region after any patch that returns a diff you did not expect.
- **Inline LSP diagnostics can be STALE mid-edit after a multi-anchor JSX patch.** A patch
  into a large `.tsx` file can come back carrying `JSX element ... has no corresponding
  closing tag`, `',' expected`, or `Cannot find name 'x'` from a half-applied parse — and
  `npx tsc --noEmit` then passes clean on the same revision. Treat the compiler as the
  authority; do not start "fixing" phantom errors the diagnostics describe.
- **A JSX block comment must close `*/}`.** Writing `{/* note */` (missing the closing
  brace) breaks the enclosing element silently and surfaces as a parse error far below the
  real line.
- **Restructure a JSX block with SEPARATE opening and closing anchor patches** (the opening
  tag / `map(...)` head, then the `))}` / `</tbody>` tail), re-reading the region before
  each. One giant multi-line replacement inside a 3k-line component is where brace counting
  goes wrong; splitting it makes the failure obvious and recoverable.
- **Hoist shared derived state above its consumers.** A memo added in a later section that
  reads a variable declared further down fails with `Block-scoped variable 'X' used before
  its declaration` — move the derivation up next to the state it comes from rather than
  duplicating it.
- "Duplicate tool output — same content as a more recent call" means an earlier
  call in the same batch already applied the change; just re-read to confirm.
- "Found N matches" means `old_string` isn't unique — add a neighbor line, don't
  guess.
- After a `patch` that warned "was last read with offset/limit pagination",
  re-read the whole region before doing another overwrite-style edit.

See references/escape-drift-example.md for the real transcript from a RINA
AdminPanel edit where this bit and how the minimal-substring fix resolved it.
