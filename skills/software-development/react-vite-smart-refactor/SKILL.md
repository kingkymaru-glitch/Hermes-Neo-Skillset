---
name: react-vite-smart-refactor
description: >
  Systematic cross-cutting refactors in an existing Vite/Next + React +
  TypeScript app — renaming a product/brand label across the UI and storage
  layer, broadening role-scoped behavior to global visibility, a safe
  whole-codebase token+behavior change, AND splitting a monolithic component
  file into modules. Use when the user asks to rename the app, change role
  gates to global visibility, or break up a huge component into tabs/modals.
  Distinct from vite-scaffold-verification (new projects) and
  supabase-auth-gate (auth architecture).
trigger:
  - rename app/brand in existing Vite React app
  - change all role-scoped feature to globally visible
  - safe token swap across UI, localStorage, labels, filters
  - adapt a component to a changed schema/type (singular field → array,
    new persisted fields) where types.ts is already updated
  - split a monolithic component file into modules / extract tabs and modals
---

# react-vite-smart-refactor
Systematic cross-cutting refactors in an existing Vite+React TS app where you must rename labels, localStorage keys, and behavior filters together, then verify the app is still healthy.

## Principles
1. Search-first, edit-second. Find every occurrence before changing anything.
2. Tokens travel in pairs: visible label + storage key.
3. Behavior filters often hide the same feature behind a role check; changing visibility requires changing both the filter AND any exclusion lists.
4. Verification is a command, not a feeling.
5. **A red gate is not automatically your fault, and not automatically yours to
   fix.** Measure the baseline and attribute precisely before reporting or
   before expanding scope.
6. Respect explicit "do NOT run X" constraints. Re-run the *permitted* gate
   after the final edit rather than trusting an earlier run.

## Workflow
1. Full search across `src/` for exact and case variants of the token.
2. Edit UI labels, localStorage keys, default strings, and notification copy together.
3. Re-run the same search; expect zero matches.
4. If the refactor widens role visibility:
   - Locate role checks such as `role === 'SuperAdmin' ? ... : [...]`.
   - Locate hardcoded exclusions like `.filter((d) => d !== 'Digital Transformation')`.
   - Make accessible scope equal the full base set, not a role-derived subset.
5. Re-run `npm run lint` and `npm run build`.
6. Smoke-test mentally: what did this change affect, and have I verified all those surfaces?

## Pitfalls
- Adding an import while editing a file you do not otherwise touch will trigger `no-unused-vars`. Remove imports you did not actually use.
- Hardcoded department/role exclusions can hide entire data sets after a "global view" change. Always audit both the role gate AND any domain filter applied inside the gate.
- localStorage keys are case-sensitive. If the app uses both readonly reads and explicit writes, update them all — partial rename silently bricks session state.
- **Fix the default/EMPTY_ constant first** in a schema migration. A stale
  default object errors at every spread site downstream and makes the real
  work look far bigger than it is.
- **Removing an early-return guard is part of array-ification.** Code shaped
  `if (!site?.thing) return;` before teardown leaks stale layers/effects once
  `thing` becomes an array whose empty case still needs cleanup.
- **Do not clear pre-existing lint errors to manufacture a green number.**
  Reporting "162 baseline errors, none introduced by me, here's the proof" is
  the correct deliverable when the task scoped you to one file.
- **A file that returns JSX must be `.tsx`, not `.ts`.** Extracting a helper that
  builds a link or element into a `.ts` file fails the bundler with
  `Expected '>', got 'ident'` at the first tag. Rename to `.tsx`.
- **When extracting helpers, grep the source file for EVERY one before choosing
  the import list.** Importing the ones you remember and missing one the file
  still calls fails type-check late. Let `tsc` name the missing one, then add it.

## Splitting a monolithic component file
When a single component has grown to thousands of lines and the user asks to
break it up, this is a DIFFERENT job from a token rename — treat it as such.
- **Never slice by line range.** Nested JSX makes line arithmetic silently
  wrong: a slice swallows a parent's closing tag or pulls in a sibling section.
  Use `@babel/parser` (already in `node_modules`) to read each child's exact
  `loc.start.line`/`loc.end.line` off the returned JSX root.
- **Extract in this order:** pure helpers → self-contained modals → tab/section
  bodies. The orchestrator stays and keeps the state; it shrinks to composition.
- **A section with 100+ parent deps takes ONE props object**
  (`<Tab {...tabProps} />` + destructure inside), not 100+ named props.
- **Prove it is behaviour-preserving:** parse each extracted file, token-compare
  the body against the original (ignoring indentation and the `: any` / `as X`
  annotations you added), then `tsc --noEmit` + a real production build.
- Full recipe, the babel walker, the verify script, and the type errors that
  always follow a split: `references/component-extraction-ast-boundaries.md`.

## Verification Cheatsheet
```bash
npm run lint
npm run build
# plus exact codebase search for zero-match confirmation
# When a gate is explicitly forbidden, use the mandated one and say so:
npx tsc --noEmit; echo "TSC_EXIT=$?"
# Attribute lint errors per-file, not via repo-wide `| tail`:
npx eslint src/path/File.tsx 2>&1 | grep -E "error" | head -30
```

## References
- `references/tsc-authoritative-detect-and-type-fork.md` — get the REAL `tsc` error list (tool echo lies) + the type-fork / factory-spread root-cause patterns + two-gate (tsc + vite build) verification.
- `references/singular-to-array-schema-migration.md` — adapting a component when a field goes singular → array or gains persisted fields: indexed-access type aliases, ref-array teardown, append-not-overwrite, conditional field spread, and pixel-positioned map overlay sync/resize patterns.
- `references/lint-baseline-vs-introduced-errors.md` — how to distinguish pre-existing lint/compiler violations from ones you introduced, and how to report a red gate honestly without scope-exploding.
- `references/component-extraction-ast-boundaries.md` — splitting a monolithic component file: the `@babel/parser` boundary walker, extraction order, one-props-object pattern for 100+ deps, token-comparison proof of behaviour preservation, and the type errors that follow a split.

## When Not To Use
- New project scaffolding → use vite-scaffold-verification.
- Auth architecture → use supabase-auth-gate.
- Bug-specific debugging with unknown root cause → use systematic-debugging first.
