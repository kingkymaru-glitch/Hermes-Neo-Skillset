---
name: single-file-webapp-editing
description: Surgically edit self-contained HTML web apps that embed an inline <script type="module"> (Three.js / Tailwind-CDN 3D studios, AI generators, single-file prototypes) and verify the changes statically WITHOUT a browser. Use when the user asks to add, remove, or fix features in a single .html file, or reports "buttons not working / dead UI" in such a file.
---

# Single-File Web App Editing (inline module script)

## Trigger
- The target is one `.html` file (e.g. `~/Downloads/lunav_studio_safe.html`) that contains its JS inline in `<script type="module">`, pulling libs from CDN (Three.js, Tailwind, etc.). No build step, no dev server available for a live check.
- User asks to remove/add/fix controls, buttons, or panels in that file.

## Workflow
1. **Read structure first.** `search_files` for the element IDs and function names you'll touch, then `read_file` the exact regions (HTML panel + the JS that wires/shows/hides it) before patching. Fuzzy `patch` needs the real surrounding lines.
2. **Edits come in 4 coupled places** for any UI control — miss one and you get a dangling reference or a dead button:
   - the HTML markup (the panel/button),
   - the function that *populates/syncs* it (e.g. `updatePrecisionInputs`),
   - the `selectObject`/`deselectObject` (or equivalent) show/hide calls,
   - the `addEventListener` wiring block.
   When removing a control, delete ALL FOUR. Then grep to confirm zero hits.
3. **Verify statically** (no browser here). Use `scripts/verify_inline_js.py`:
   ```
   python3 scripts/verify_inline_js.py <file.html> --refs slider-controls mov-x rot-x updatePrecisionInputs
   ```
   It extracts the inline module, runs `node --check`, and prints any dangling token counts. SYNTAX_OK + zero dangling refs = safe to ship.

## Pitfalls (learned the hard way)
- **MODULE-ABORT BLAST RADIUS (top danger).** In an inline `<script type="module">`, a reference to a removed DOM element at the TOP LEVEL throws at load and aborts the WHOLE module — every listener defined afterward silently never attaches. Symptom: MANY unrelated buttons die at once ("all buttons dead / can't draw anything"), not one. Example from this file: the `Generation Mode` `<select id="gen-mode">` was deleted but `getElementById('gen-mode').addEventListener(...)` and `getElementById('gen-mode').value` remained → null throw → Generate/Reset/Draw/Delete all dead. FIX: when removing a control, delete every JS reference (the listener AND any `.value`/`.textContent` read), not just the markup. Suspect this whenever multiple unrelated controls break simultaneously.
- **Dangling listeners inside functions.** A removed function referenced by `transformControls.addEventListener('change', updatePrecisionInputs)` throws at runtime even though `node --check` passes. Replace with a no-op `() => {}` or remove the line.
- **Brace-mangling when removing a call before a block.** If you delete a line such as `updatePrecisionInputs();` that sits *above* a following `if (object.userData.isParametric) {`, a careless `old_string` can swallow that `if (...) {` opening line, turning it into a premature `}` and breaking the whole function. MITIGATION: include the `if (...) {` (or next real statement) inside `old_string` so it survives, OR re-read the function immediately after and confirm brace balance. Always re-read after a multi-line deletion inside a function body.
- **Button rename/replace = 3-part matched edit.** Swapping a button (e.g. Polygon→Sphere) means markup id + listener target id + handler branch all change together. Doing HTML only leaves a dead listener AND a missing branch (shape builds nothing). Patch all three in one pass.
- **`node --check` only catches syntax, not undefined symbols / missing ids.** Run `scripts/verify_inline_js.py <file>` — it now AUTO-detects any `getElementById`/`querySelector` id referenced in JS but missing from the HTML (`DANGLING_DOM_IDS`) and runs `node --check`. SYNTAX_OK + clean DOM + clean refs = safe to ship. Don't skip this on a removal/edit.
- **Don't re-add what was removed.** If you strip a control and the user later reverses, comply fast — don't argue or re-justify the old design.
- **Stale `read_file` state across a long edit session (new this session).** When you make MANY edits to ONE file in one session — especially after a compaction boundary — earlier `read_file` line offsets can be OUT OF DATE because a prior turn already changed the bytes. Your fuzzy `old_string` then won't match and `patch` throws "Could not find a match" repeatedly. This session burned many calls on exactly that. MITIGATION: before each `patch`, re-fetch the LIVE region with a fresh `search_files`/`read_file` of the exact token (or do the whole edit as one `execute_code` regex substitution on the current file bytes) — and NEVER blindly retry the same `old_string` more than once. If a patch fails twice, the file moved under you; `grep -c` the target token immediately to see the real current text before re-patching.
- **Re-skinning a standalone iframe/doc to a parent-app theme (new this session).** A single-file `.html` loaded via `<iframe src=...>` or opened directly is a SEPARATE document — it CANNOT inherit the parent app's CSS variables (`--mb-turquoise`, `--glass`, etc.) even if the parent is the same origin. When the user says the iframe "doesn't match the rest of the app's look and feel," you must HARDCODE a mirrored token set into the file's `<style>` and rewrite every Tailwind class that uses a theme color. Steps that worked for the LunaV Studio reskin:
  1. Pull the real palette from the source of truth (e.g. `src/app/globals.css`): base bg `#14171c`, panel `#1b1f26`, accent `#2f9bff` (was `cyan-500`/`#0ea5e9`), secondary text `#8fa1b3`, tertiary `#55677a`, hairline `rgba(150,175,205,0.14)`, inset bg `rgba(15,18,22,0.6)`.
  2. Define a `:root{ --lv-* }` block inside the file's own `<style>` so shared JS color constants and any added CSS can reference them instead of raw hex — keeps future edits consistent.
  3. Rewrite Tailwind classes to arbitrary values (the CDN JIT supports `text-[#8fa1b3]`, `bg-[rgba(47,155,255,0.10)]`, `border-[rgba(150,175,205,0.14)]`). Map the old→new per category: `cyan-400/300`→`#2f9bff`/`#7db4ff` (accent), `slate-400/500`→`#8fa1b3`/`#55677a` (text), `slate-700`→hairline, `slate-900/50`→inset bg, `cyan-500/10`+`cyan-500/40`→accent tint+border, `file:bg-slate-700`→`#232831`. Use `replace_all` for the repeated `text-cyan-400`/`text-slate-400`/`border-slate-700`/`bg-slate-900/50`/`bg-cyan-500` hits.
  4. Also remap JS-side THREE.js colors that won't be touched by class edits: `scene.background`/`scene.fog` hex, `DEFAULT_COLOR`, sphere/extrude material `color`, grid helper colors, and the `<input type="color" value="#0ea5e9">` default. These are the ones that still leak the old palette after the class pass.
  5. **False-positive watch:** `grep` for `slate` after — `translateX`/`translateY`/`translate` contain the substring "slate" but are NOT Tailwind `slate-*` colors. Confirm a hit is a real class before replacing.
  6. Verify: no `cyan-`/`slate-*` Tailwind classes and no old hex (`#0ea5e9`, `#0f172a`, `0x0ea5e9`, `0x0f172a`) remain. Full token map + remap table in `references/lunav_theme_reskin.md`.
- **UI control overlapped by an absolutely-positioned toggle (new this session).** When adding a collapse/close button to a panel, do NOT `position: absolute` it at the panel's corner — it floats over the first content block ("Scene Tools" / "Editor") and the user will reject it as "overlapping / unprofessional". Put the button in a **sticky in-flow header bar**: `position: sticky; top:0; margin:-16px -16px 12px; padding:12px 16px; background:rgba(15,23,42,.92); backdrop-filter:blur(8px); border-bottom:1px solid rgba(148,163,184,.18); border-radius:.5rem .5rem 0 0`, with a panel label on the left and the chevron on the right. Reads as real app chrome; can never overlap content. Known-good markup + JS in `templates/collapsible_panel.html`.

## User preference (correction captured)
When this user says an app is "full of bugs / most buttons not working" and asks to **remove** dead controls, they mean REMOVE — do NOT replace with new panel UI. In the LunaV-style 3D studio, the **gizmo (Move/Rotate/Scale mode buttons + on-screen drag handles) is the intended transform path**; adding Move/Rotate/Scale sliders or number inputs was explicitly rejected as redundant ("ths slider is also a dead funtion, useless. remove the slider"). Default to: strip the broken thing, keep the already-working gizmo, leave Color + Delete + (parametric) shape controls.

## Support files
- `scripts/verify_inline_js.py` — extract inline `<script type="module">`, `node --check`, and AUTO-detect any `getElementById`/`querySelector` id referenced in JS but missing from the HTML (`DANGLING_DOM_IDS`). Run it after every removal/edit.
- `references/lunav_studio_bugs.md` — condensed reproduction recipes for this file's recurring failures (module-abort-on-removed-control; button-rename mismatch). Read before debugging "all buttons dead".
- `references/lunav_theme_reskin.md` — full LunaV token map + old→new Tailwind/THREE.js remap table for re-skinning a standalone iframe to the parent app theme. Read before any "make this match the app look and feel" task.
- `templates/collapsible_panel.html` — known-good copy-paste markup + CSS + JS for a collapsible side panel with an IN-FLOW sticky header bar (no overlap) and a floating safe-area-aware reopen button. Use when adding collapse to a panel.
