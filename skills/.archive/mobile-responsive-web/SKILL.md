---
name: mobile-responsive-web
description: >-
  Make a desktop-first web app usable on phone + tablet without a rewrite. Covers
  the Next.js App Router mobile viewport, bottom-sheet drawers, 44px touch targets,
  iOS safe-area insets (notch + home indicator), and collapsible side panels. Trigger
  on: "optimize for mobile", "make it work on tablet/phone", "responsive", "touch
  targets", "bottom sheet", "safe-area inset", "viewport meta", or any "this panel
  overflows on my phone" task. Mostly Tailwind utility classes + one or two state
  flags — desktop layout must stay UNCHANGED (guard every change with `sm:`/`md:` so
  it only kicks in below the breakpoint).
---

# Mobile / Tablet Web Optimization (desktop-first apps)

The goal is NOT a separate mobile app — it's making an existing desktop layout
survive a 375px screen. Golden rule: **every mobile change is gated behind a
breakpoint (`sm:` = 640px) so desktop is untouched.** If a change affects desktop,
it's wrong.

## 1. Mobile viewport (the #1 silent killer)

If phones render the desktop layout "zoomed out", the app is missing the viewport
meta. In **Next.js App Router**, set it via the `viewport` export — do NOT drop a raw
`<meta name="viewport">` in `<body>` (App Router antipattern; it gets hoisted/ignored).

```ts
// src/app/layout.tsx
export const viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,            // allow pinch-zoom but cap it
  viewportFit: "cover",       // REQUIRED for env(safe-area-inset-*) to be non-zero
  themeColor: "#0b0e12",
};
```

Without `viewportFit: "cover"`, iOS reports all safe-area insets as `0` — your
safe-area padding below will do nothing.

## 2. Bottom-sheet drawers (the highest-value pattern)

A right-side drawer (`absolute right-4 top-4 w-96`) overflows a phone. Turn it into a
bottom sheet on mobile, revert to side panel on `sm+`. One conditional className:

```
"absolute inset-x-0 bottom-0 top-auto z-20 w-full rounded-t-2xl rounded-b-none
 p-6 pb-[max(1.5rem,env(safe-area-inset-bottom))]
   sm:inset-auto sm:right-4 sm:top-4 sm:w-[calc(100vw-2rem)] sm:max-w-96 sm:rounded-2xl"
```

- `max-h-[82vh]` + `overflow-y-auto` so a tall sheet scrolls instead of covering the screen.
- `rounded-t-2xl` gives the sheet its "pull-up" look.
- The `pb-[max(1.5rem,env(safe-area-inset-bottom))]` clears the iPhone home indicator
  (needs `viewportFit: "cover"` from step 1).
Apply this to ANY modal/drawer that sits on the 3D/canvas stage (finding details,
proxy editor, settings).

## 3. 44px touch targets (mobile media query)

Buttons/inputs sized for mouse are too small for thumbs. Add ONE mobile-only media
query — zero desktop impact (desktop buttons keep their size):

```css
@media (max-width: 640px) {
  .mb-btn, .mb-input, .mb-select, .mb-textarea { min-height: 44px; }
  .mb-btn { padding-top: .65rem; padding-bottom: .65rem; }
  input[type="range"] { height: 28px; }          /* fatter slider track = easier drag */
  button, [role="button"] { touch-action: manipulation; }  /* kills 300ms tap delay */
}
```

Swap the class list for your app's actual button/input classes. `touch-action:
manipulation` also stops double-tap-to-zoom hijacking single taps.

## 4. Collapsible side panels (free the canvas)

### 4a. React / Next.js App Router
A left "models / layers" console eats the whole phone screen. Add a `useState` flag
(e.g. `modelsOpen`, default `true`) and toggle:

- **Open (mobile):** floating top panel — `left-2 right-2 top-2 max-h-[60vh] overflow-y-auto`
  (never full-screen; leaves the 3D view visible).
- **Collapsed (mobile):** thin edge tab — `left-0 top-1/2 w-9 -translate-y-1/2` with a
  vertical `writing-mode: vertical-rl` label ("Models ›"); tap expands.
- **Desktop (`sm+`):** unchanged full side panel (`sm:left-4 sm:right-auto sm:top-4 sm:w-80`).
- Hide the collapse chevron on desktop (`sm:hidden`) so desktop users never see the toggle.

### 4b. Vanilla / single-file HTML (no framework, inline `<script type="module">`)
Pattern used in the LunaV 3D studio (a self-contained `.html`): slide the panel off-screen
with a `transform` + `.collapsed` class; a sticky in-flow header bar holds the toggle; a
floating reopen button appears only when collapsed; auto-collapse both panels on
`matchMedia('(max-width: 768px)')`.

- **CRITICAL — do NOT absolutely-position the collapse button inside the panel.**
  `position: absolute; top:8px; right:8px` parks the button ON TOP of the first content
  block (e.g. "Scene Tools"), which is exactly the overlap the user will flag as
  "unprofessional / overlapping". Put the toggle in a **sticky header bar that is part of
  normal flow**: `position: sticky; top:0; margin:-16px -16px 12px` (negative margins cancel
  the panel's 16px padding so the header bleeds edge-to-edge), with a panel label on the
  left and the chevron on the right. Reads as real app chrome, can never overlap content.
- **Reopen affordance is mandatory.** A fixed, circular, safe-area–inset edge button
  (`left: calc(env(safe-area-inset-left,0px) + 10px)`) shown via `display:flex` only when
  `.collapsed` is set. Without a visible reopen target, the user can't get the panel back.
- Keep desktop identical: slide/collapse only triggers via the media query, so `sm+` stays
  two open side panels.

Known-good copy-paste markup + JS: `single-file-webapp-editing` skill →
`templates/collapsible_panel.html`.

## 5. Responsive nav (don't let the top bar overflow)

A top nav with logo + buttons + tabs in one `flex` row overflows on phone. Fix:
- `flex-wrap` + `gap-y-2` on the nav, and `px-4 py-2 pt-[max(0.5rem,env(safe-area-inset-top))]`
  on mobile (clears the notch).
- Make the tab/group row `overflow-x-auto` so 4 tabs scroll horizontally instead of squishing.

## 6. 3D viewers are usually fine

`three`'s `OrbitControls` is **touch-enabled by default** (one-finger rotate, two-finger
pan/zoom). The real mobile breakers for a 3D app are the *overlay UI* (drawers, nav,
side panels) — not the canvas. Spend effort on steps 1–5; the model itself will orbit.

## 7. Modal/dialog "stuck at top" — the ancestor-`transform` trap

A centered modal built with `position: fixed; inset: 0` is NOT truly viewport-fixed
if ANY ancestor has a `transform` (or `filter`/`perspective`). It gets positioned
relative to that ancestor instead — so it sits at the top of the page and won't center
or scroll. This bites hard with view-transition / animation wrappers like a
`fade-up` container (`transform: translateY(...)`) or a shared page-transition parent.
Symptom the user reports: "the modal opened but it's stuck at the top / I can't reach
the buttons / it scrolls with the page."

Fix — render the modal through a portal to `<body>` so no transformed ancestor sits
between it and the viewport:

```tsx
"use client";
import { createPortal } from "react-dom";
import { useEffect, useState } from "react";

function Modal({ onClose, children }: { onClose: () => void; children: React.ReactNode }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) return null;                       // avoid SSR body mismatch
  return createPortal(
    <div className="fixed inset-0 z-[1000] flex items-start justify-center overflow-y-auto p-4">
      {/* backdrop click closes; inner card stops propagation */}
      <div className="fixed inset-0 bg-black/60" onClick={onClose} />
      <div
        onClick={(e) => e.stopPropagation()}
        className="relative my-auto w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-2xl bg-[#0b0e12] p-5"
      >
        {children}
      </div>
    </div>,
    document.body
  );
}
```

- `flex items-start` + `my-auto` + `overflow-y-auto` on the outer fixed div → modal
  centers when short, scrolls when tall, never clips the action bar.
- Put the action buttons in a `sticky bottom-0` bar inside the card so they're always
  reachable on a tall phone form.
- Show errors INSIDE the modal, not in the page behind it — an error banner rendered
  behind the overlay is invisible and reads as "the button does nothing" (same class of
  bug as the "Register does nothing" report).

Note: `createPortal` needs `"use client"` — do NOT put it in a server component.

## Decision lens (scope)

Ask which surface matters before coding:
- **Client/portal viewing** (highest value, most-opened-on-phone): bottom sheets + safe-area.
- **Tablet editing** (field use): bottom sheets + 44px targets + collapsible panels.
- **Phone editing** of 3D is awkward and rarely worth forcing — flag it, don't build a
  cramped editor. Rule of thumb: *mobile = great viewing, tablet = usable editing.*

## Pitfalls
- **Raw `<meta viewport>` in body** under App Router — use the `viewport` export instead.
- **Forgetting `viewportFit: "cover"`** → safe-area insets read 0, bottom-sheet padding
  invisible. The two must ship together.
- **Mobile change leaking to desktop** — if you didn't prefix it with `sm:`/`md:`, you
  broke the desktop layout. Build + visually diff both widths.
- **`max-h-[82vh]` sheets without `overflow-y-auto`** → content clipped, no scroll.
- **Collapsed edge-tab with no tap target** → user can't reopen. Give it a visible
  label and full-height hit area.
- **Collapse button overlapping the first content block** (vanilla/static panels) →
  NEVER `position: absolute` the toggle inside the panel; it lands on the first section
  ("Tools" / "Editor") and reads as broken. Use a sticky in-flow `panel-header` instead
  (see 4b). The user will call this "unprofessional / overlapping" and ask you to fix it.
- **Touch sliders too thin** → set `input[type=range]{height:28px}` in the media query.
- **Modal "stuck at top"** → `position: fixed` is hijacked by any ancestor `transform`
  (e.g. a `fade-up`/`page-transition` wrapper). Portal it to `<body>` (see §7). Also
  render error/feedback INSIDE the modal, not in the page behind it, or the user sees
  "nothing happened" when a save silently fails.

## Support files
- `references/snippets.md` — copy-paste Tailwind className strings for bottom-sheet,
  collapsible panel, and the responsive-nav pattern, plus the Next `viewport` export.
