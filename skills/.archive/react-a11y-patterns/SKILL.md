---
name: react-a11y-patterns
description: React (esp. React 19) accessibility debugging patterns for drawers, modals, and overlays — focus management, the aria-hidden + inert conflict, and the "Blocked aria-hidden" console warning. Use whenever a React app logs a Chrome DevTools accessibility warning about aria-hidden, or when adding/closing side panels, drawers, or modals that must hide from assistive tech while closed.
---

# React Accessibility Patterns

Class-level skill for the recurring React a11y bugs that show up the moment you add
toggleable drawers / modals / flyouts. The signature symptom is a yellow Chrome
DevTools warning:

  Blocked aria-hidden on (index):N — focus must not be hidden from assistive tech
  users. Focused element: button.<something-close>. Ancestor: <aside ... aria-hidden="true">.

## Pattern: `inert` resolves the aria-hidden + focus conflict

**Root cause.** An ancestor element is marked `aria-hidden="true"` (so screen readers
ignore it) while a descendant inside it still retains keyboard focus (e.g. a close
`X` button in a *closed* drawer). WAI-ARIA forbids hiding a focused element from
assistive tech. Chrome blocks the `aria-hidden` and logs the warning. Functionally
harmless to the app, but it's a real a11y defect and it spams the console.

**Fix (React 19+).** Add `inert={!open}` to the SAME element that already gets
`aria-hidden={!open}`. `inert` removes the whole subtree from the tab/focus order AND
hides it from assistive tech — so no focusable child can ever live inside the hidden
drawer. The contradiction is gone.

```jsx
// before
<aside className={`sensors-drawer ${open ? 'open' : ''}`} aria-hidden={!open}>
// after
<aside className={`sensors-drawer ${open ? 'open' : ''}`} aria-hidden={!open} inert={!open}>
```

Apply to **every** drawer/overlay that toggles `aria-hidden` (cmd, chat, insights,
settings, sensors, modal backdrops). A single missed panel keeps throwing the warning.

**React version gate (check `package.json` `react` field first):**
- React **19**: `inert` is a native boolean DOM prop → `inert={bool}` works directly, no ref.
- React **18 and below**: `inert` is NOT a native React prop. Set it via a ref
  (`el.inert = !open`) or as a string attribute. Do NOT write `inert={bool}` on 18 — it
  silently does nothing / warns.

**Verification:** re-run the build, refresh, toggle each drawer open→closed, confirm the
warning no longer appears in the console.

## Pitfalls
- Do NOT just delete `aria-hidden` to silence the warning — that removes the a11y benefit
  (screen readers would then read closed-drawer contents). Pair `aria-hidden` WITH `inert`.
- `inert` on an OPEN panel disables it. Always write the inverted form `inert={!open}`,
  never `inert={open}`.
- The warning names a *focused descendant*, not the hidden ancestor — search for the
  focused element's class (e.g. `.sensors-close`) to find which drawer is at fault.

## When to reach for this
- Any new toggleable side panel / flyout / modal in a React app.
- A console warning containing the phrase "Blocked aria-hidden".
- Pre-commit a11y self-check on drawers (part of the standing UI/UX recheck loop).

See `references/inert-aria-hidden.md` for the full error text, root-cause walkthrough,
and a worked 4-drawer example from the MARU app.

## Pitfall — backdrop-blur traps an absolutely-positioned dropdown
A parent card with `backdrop-blur` (or any `filter`/`backdrop-filter`) creates a
**stacking context**. An `absolute` dropdown inside it can't escape that context:
opening it DOWN gets it covered by the NEXT sibling card (the sibling paints above
it), and opening it UP clips against the container border (`z-index` can't help —
it's scoped inside the card's context). Symptom: "the settings menu is blocked by
the other box" no matter the z-index.

**Fix that worked:** render the dropdown in **normal document flow** below the
card's action row so the card **grows downward** to hold it — not as an
`absolute` overlay. In-flow expansion can't overlap the next card or clip the
panel, regardless of backdrop-blur on the card. For short menus (2 items) this
is cleaner and removes the whole class of stacking bugs. Applies to any React app
using glassmorphism cards + per-item overflow menus.
