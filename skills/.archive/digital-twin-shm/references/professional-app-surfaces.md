# Professional App Surfaces (Help / Readme / About / Support)

The "table-stakes" utility surfaces every professional app ships. For MARU
these were added as a shared accessible modal shell + content modals, plus a
Support section in the Settings flyout. Verified green (oxlint 0/0, vite build)
in my-digital-twin.

## Design rules the user insisted on
- ONE primary nav surface (the left command flyout). Nothing floats in a corner
  that duplicates a flyout action. Professional ≠ cluttered.
- Matching design language: reuse the app's glass tokens (`--glass-bg`,
  `--glass-blur`, `--neon-cyan`) and hand-authored stroke SVGs (NO icon library
  — user dislikes menu icons). SF-Symbols-style, `viewBox="0 0 24 24"`.
- Content must be REAL and on-brand, not empty stubs. Help = quick-start tour of
  each surface. Readme = the Five-Box architecture + getting started. About =
  branded badge + metadata table (Version/Region/Stack/Edition) + copyright.
- "Clean, yet complex" = restrained chrome, but dense, credible information.

## Architecture
`src/InfoModals.jsx` exports a shared `MenuModal` shell + `HelpModal`,
`ReadmeModal`, `AboutModal`, `SupportModal`. The shell handles Esc + backdrop
close and a footer Close button. App holds a single `infoModal` state
(`'help'|'readme'|'about'|null`) and a `supportModal` state
(`'report'|'contact'|null`); renders `{infoModal === 'help' && <HelpModal …/>}`
etc. at z-60 (above all flyouts).

Home flyout footer (`.info-row` under the "Edge Connection" card): Help ·
Readme · About · Feedback — separated by hairline `.info-sep`. Feedback opens
`supportModal('report')`. Settings flyout gets a "Support" section (after
Governance) with two `.settings-action` rows: Report a Problem (warning-triangle
glyph) + Contact (envelope glyph), each opening `SupportModal`.

## Support modal specifics
- Report a Problem → `mailto:support@maru.shm?subject=…&body=…` (prefilled
  triage body). Placeholder email — swap before go-live.
- Contact → a "Copy support email" button (`navigator.clipboard.writeText`).
- Both wrapped in `.modal-callout` noting the placeholder address.

## CSS tokens used
Modal shell: `.modal-scrim` (fixed inset:0 z-60, blur(6px)), `.modal-card`
(min(520px,100%), max-height:86vh, scroll), `.modal-head/.modal-title/
.modal-body/.modal-foot`, `.modal-callout` (cyan tint box), `.modal-cta`
(email button). About: `.about-badge/.about-mark/.about-meta/.modal-fine`.

## Verification
Lint + build gate only (`npm run lint` + `npm run build`, then `rm -rf dist`).
Visual approval is a manual eyeball gate — hold lint nags until the user views
the canvas. The user commits after a green build + visual review in their own
tooling (they run the dev server; you don't own the browser here).
