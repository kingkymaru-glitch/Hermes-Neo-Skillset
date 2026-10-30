---
name: react-app-shell-customization
description: >
  Make React/Vite app shells generic instead of hardcoding product/company names.
  Covers the pattern of lifting identity text into component props, shared context
  or parent state, localStorage persistence for Phase 1 prototypes, and
  admin-only edit UI surfaces. Trigger: user asks for generic branding, rebranding,
  "change the app name without code changes", admin-editable header/footer, or
  white-label app shell.
---

# React App Shell Customization

## Core pattern
Treat app identity as data, not decoration.

1. Props: `AppShell` accepts `headerTitle`/`footerBranding` props.
2. Shared state: `App.tsx` owns branding state and passes it down.
3. Persistence: localStorage-backed values with generic fallbacks.
4. Admin UI: SuperAdmin-only edit controls in the admin settings panel.

## Phase 1 localStorage persistence
- Namespace keys per app, e.g. `appname:branding:header`.
- Initialize state from `localStorage.getItem(...)` in `useState(() => ...)`.
- Persist on change in the setter path or a memoized effect.

## Role gating
- Edit controls render only for SuperAdmin.
- Other roles see current values but cannot modify.

## Re-injecting CLIENT-SPECIFIC copy into an already-genericized app
When the app was genericized (all customer names stripped) but a specific client demo
needs branded taglines back, do NOT scatter the strings through components. Isolate
them in ONE config module (`src/config/copy.ts` exporting a `copy` object) and import
that into each surface (Login hero, Dashboard header, empty states, app shell). This
keeps the codebase generic — the next client is a one-file swap, not a component hunt.
- Flag the reversal to the user if they previously asked for full genericization; the
  copy file preserves that genericization (it is the only client-specific bit).
- Keep keys stable (`brandHeader`, `dashboardTitle`, `loginTagline`, `emptyTasksTitle`,
  ...) so components import by name and never hardcode the literal sentence.
- If the user prefers literal hardcoded strings instead of a config layer, they will
  say so — default to the single-file approach.

## White-label theming (supabase-backed client portal)
When the SELLER (inspector/admin) wants the read-only CLIENT view to look like
the CLIENT's company, drive theme + accent from persisted branding state, not
hardcoded CSS:

1. **Theme via `data-theme` on `<html>` + CSS-var blocks.** Define `:root` (dark
   default) and `html[data-theme="light"]` / `html[data-theme="midnight"]` blocks
   that override the SAME CSS variables (`--dash-void`, `--dash-panel`,
   `--txt-primary`, `--mb-turquoise`, …). Apply with
   `useEffect(() => document.documentElement.setAttribute("data-theme", theme), [theme])`.
   The whole UI re-skins from one attribute — no component changes.
2. **Accent override inline.** If branding has a custom accent, set it on `:root`
   via `root.style.setProperty("--mb-turquoise", accent)` (plus a dim + glow
   variant) so buttons/gauges pick it up. Clear it (`removeProperty`) when null so
   the theme default returns.
3. **Auto-extract accent from the uploaded logo** (no color-picker dependency):
   draw the logo to a ≤64px canvas, average the opaque pixels
   (`rgbToHex(r/n, g/n, b/n)`), use that as the accent. Wrap in try/catch —
   a CORS-tainted canvas throws; fall back to a manual `<input type=color>`.
4. **Hide the builder from the client.** In read-only mode, filter the tab list
   (e.g. drop the "Studio" builder tab) and land on the report. The seller keeps
   the full nav.
5. **Keep the platform visible but minimal.** Client view shows the seller's logo
   + name in the header; the platform survives only as a footer line + a clickable
   watermark (e.g. a `<a target="_blank">` over the 3D canvas) — NOT a hardcoded
   "Powered by X" string.
6. **RPC state discipline (critical):** the save RPC must write fields LITERALLY,
   and the client must send the FULL branding state on every save (read state →
   merge patch → send all columns). If the RPC uses `coalesce(p_x, col)`, passing
   `null` to CLEAR a field silently keeps the old value (see `supabase-backend` P29).
   So "Remove logo" / "Reset accent" only work if the caller sends the whole object.

## Pitfalls
- Do not hardcode company/product names in `AppShell`, nav, or footer strings.
- When adding props to `AppShell`, update every JSX call site or it stays hardcoded.
- While patching parent state, avoid duplicate `useState` declarations; build immediately to catch silent hook duplication.
- If an edit produces duplicate strings, replace the enclosing function/file instead of repeating the stale patch.
- For generic defaults, prefer neutral names like "Office Task Management" and neutral footer slogans unless the user specifies otherwise.
- When re-adding client copy, do not paste brand sentences directly into JSX — route them through the `copy` config module so the app stays multi-customer swappable.

## Reference
- See `references/phase1-localstorage-branding.md` for the exact verified wiring pattern and default wording.
- See `references/client-copy-config.md` for the `src/config/copy.ts` pattern (single-file client tagline swap).
- See `references/white-label-theming.md` for the full data-theme / CSS-var / canvas-accent / tab-hide wiring
  used in ss-rover-cloud Phase 5 (inspector sets company name + logo + theme + accent; client link re-skins).
