# UI visibility — "I don't see the function" ≠ "the code is missing"

## Symptom
User says "I don't see the function to group/ungroup/select all/reset" but a code search shows
the buttons and their `addEventListener` calls ARE in the file.

## Diagnosis
The controls existed at the BOTTOM of a scrollable sidebar:
`<div class="... max-h-[calc(100vh-100px)] overflow-y-auto">` with many sections above them
(AI Generation, 2D Builder, ...). They were below the fold / easy to miss.

## Fix
1. Move the critical control block to the TOP of the panel, immediately under the panel header.
2. Wrap it in a highlighted container so it's unmistakable:
   ```
   <div class="bg-cyan-500/10 border border-cyan-500/40 rounded-lg p-3">
     <h2 ...>Scene Tools</h2>
     <div class="grid grid-cols-2 gap-2">
       <button id="select-all-btn" ...>Select All</button>
       <button id="group-btn" ...>Group</button>
       <button id="ungroup-btn" ...>Ungroup</button>
       <button id="reset-btn" class="btn-danger ...">Reset Scene</button>
     </div>
     ...mode select, sel-count...
   </div>
   ```
3. After moving, re-search for duplicate `id=` — a duplicate ID silently breaks `getElementById`
   listeners (the listener binds to the first match only).

## Verification
- Confirm each id appears exactly once: `select-all-btn`, `group-btn`, `ungroup-btn`, `reset-btn`.
- Confirm the four handlers + sandbox each defined once (no dup definitions).
- `node --check` on the extracted `<script type="module">` body.

## Lesson
When a user reports a missing UI control, FIRST grep the file for the id and its listener.
If present, the issue is layout/visibility, not code — don't rewrite logic. Pin to top + highlight.
