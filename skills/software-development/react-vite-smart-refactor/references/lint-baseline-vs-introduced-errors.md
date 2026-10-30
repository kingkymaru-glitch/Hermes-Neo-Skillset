# Baseline vs introduced errors: reporting a red gate honestly

A refactor's verification gate comes back red. The question is never "is lint
passing" — it's **"did I break it?"** These are different questions and the
answer to the second is what the user actually asked for.

## The trap

Two symmetric failure modes, both bad:

- **Overclaiming:** report "clean" because the *mandated* gate (`tsc`) passed,
  never mentioning that `npm run lint` exits 1.
- **Scope explosion:** treat every lint error in the touched file as yours and
  start rewriting Leaflet `any` typings and render-time ref reads across a
  component you were scoped to change narrowly. This is how a one-file task
  becomes a repo-wide refactor nobody asked for.

The correct move is: measure the baseline, attribute precisely, report both.

## Attribution technique

1. **Run the mandated gate first and report it verbatim.**
   ```bash
   npx tsc --noEmit; echo "TSC_EXIT=$?"
   ```
   `echo $?` explicitly — do not infer exit status from absence of output.

2. **Scope the noisy gate to your file** rather than reading the repo-wide tail:
   ```bash
   npx eslint src/components/Foo.tsx 2>&1 | grep -E "error" | head -30
   npx eslint src/components/Foo.tsx 2>&1 | grep "✖"
   ```
   With `npm run lint | tail`, you only ever see the LAST files alphabetically —
   which are usually not yours. Get a repo-wide count for context
   (`✖ 4634 problems (162 errors...)`) but attribute per-file.

3. **Classify each error in your file by whether the pattern pre-dates you.**
   Strong evidence of pre-existing, in rough order of how convincing it is:
   - The error sits on a line you never edited.
   - The rule fires on scaffolding you inherited (`useRef<any>` for a CDN-loaded
     library, existing render-time `mapRef.current` reads).
   - **The killer proof:** a construct you left *byte-identical* is flagged.
     If `deleteArea`'s dependency array is unchanged from the original and the
     react-compiler still reports "memoization could not be preserved" on it,
     that rule was firing before you arrived. Say exactly that.
   - The same rule fires prolifically in files you never opened.

4. **Say the blocker out loud.** "Full green lint is unattainable without a
   repo-wide cleanup of pre-existing violations in files I was told not to
   touch" is a complete, honest answer. Do not fix out-of-scope violations to
   manufacture a green number.

## Reporting shape that works

- Lead with the mandated gate and its exit code.
- Then the red gate, with the repo-wide baseline count next to the per-file count.
- Enumerate the rule categories in your file and why each pre-dates the change.
- Name the blocker and why you did NOT clear it.
- Only then the functional summary.

## Related constraints

Respect explicit "do NOT run X" instructions (`git`, `npm run build`) even when
X would give better evidence. Re-run the *permitted* gate after the final edit
instead of trusting an earlier run — and note that you re-confirmed it.
