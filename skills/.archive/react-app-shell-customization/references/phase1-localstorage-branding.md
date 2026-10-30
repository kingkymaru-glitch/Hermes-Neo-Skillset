# Phase 1 localStorage Branding Pattern

## Verified shape
- `src/components/AppShell.tsx`: props `headerTitle?: string` and `footerBranding?: string`.
- `src/App.tsx`: shared `brandingHeader`/`brandingFooter` state initialized from `localStorage`.
- `src/components/AdminPanel.tsx`: SuperAdmin-only edit form with Save/Cancel.

## Wiring
- Pass branded values into `AppShell` from `App.tsx`.
- Pass branded values plus setters into `AdminPanel` so edits update shared state.
- Use generic non-customer defaults unless the user specifies office branding.

## Defaults observed
- Header: "Office Task Management"
- Footer: "RIINA — Roles.Initiative.Network & Achievement"
