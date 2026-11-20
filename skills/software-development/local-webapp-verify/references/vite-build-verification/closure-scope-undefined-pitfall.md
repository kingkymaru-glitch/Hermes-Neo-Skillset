# Pitfall 6b — closure-scope undefined identifier (runtime crash, build green)

## Symptom
After introducing a gating flag `edgeUnlocked` via a hook (`useIsEdgeUnlocked()`)
inside `DashboardInner`, the flag was referenced inside a nested `AssetEntities`
component that did NOT call the hook. `npm run lint` (0 errors) + `npm run build`
(green) passed. The page only crashed at runtime with
`ReferenceError: edgeUnlocked is not defined` when the gated branch rendered.

## Why the Pitfall-6 grep gate missed it
Grepping the file for `edgeUnlocked` finds the parent's `const edgeUnlocked = ...`
line, so "import + usage both present" looks satisfied. But the *usage* is in a
different component scope that never bound the name. Identifier text present
ANYWHERE in the file is NOT proof each reading scope has it in scope.

## Root cause
A `const` declared in a parent React component is NOT visible inside a separately
defined nested function component. Function-component boundaries are lexical: the
child has its own scope and must bind the value itself (prop or hook).

## Fix (one line)
Add the hook call at the top of the child that reads it:
```js
function AssetEntities({ assets }) {
  const { mode, geo, mockSensors } = useEdgeData()
  const edgeUnlocked = useIsEdgeUnlocked()   // <- was missing
  const showS22 = mode === 'android' && geo && edgeUnlocked
```

## Detection rule
After introducing a gating flag/hook, confirm EVERY component reading it either
receives it as a prop OR calls the hook itself. The grep gate only catches the
un-imported/un-destructured case; for closure scope, you must read each reader.

## Build behavior reminder
- unresolved module import (file missing) → build FAILS
- in-file undefined identifier (incl. parent-scoped flag in nested component) → build PASSES (slips through)
