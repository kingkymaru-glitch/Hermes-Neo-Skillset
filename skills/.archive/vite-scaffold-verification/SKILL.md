---
name: vite-scaffold-verification
description: >
  Scaffold and verify standalone Vite + React + TypeScript front-end projects from scratch without relying on create-vite. Use when the user asks for a new standalone demo app, a separate repo, or a fast one-hour prototype. Covers exact file structure, extension hygiene, render/build verification, and common Vite+React+TS failure modes observed across initial scaffolds.
---

# Vite Scaffold & Verification

## Trigger
- “new project”, “new app”, “quick demo”, “1-hour demo”, “standalone project”, “create separate repo”, or any request to bootstrap a separate front-end from zero without SPFx/Tooling.

## Core Approach
Work in three phases: Project Hub, Scaffold, Verify. Do not claim done until `npm run build` passes for a new project.

## Phase 1: Project Hub (Obsidian + GitHub)
1. Create an Obsidian project note: `Projects/<PROJECT> — <one-line descriptor>.md`
2. Include: overview, scope, roles, database schema, routes, success criteria, timeline, architecture diagram, deliverable checklist, update log.
3. Ask for the GitHub owner/repo preference. Do not assume public/private — ask.
4. If GitHub auth is unavailable, do not block; note “GitHub push pending auth” and proceed.

## Phase 2: Scaffold Without create-vite
If `npm create vite@latest` is unavailable or rejected, write the app manually.

### Required Files
- `package.json`
- `vite.config.ts`
- `tsconfig.json`
- `index.html`
- `src/main.tsx`
- `src/vite-env.d.ts`
- `src/types.ts`
- `src/App.tsx`
- React components in `src/components/` — always `.tsx`

### Hard Rules
1. The manifest devDependency line must match what the installer actually resolves:
- If `@vitejs/plugin-react@6` is present, use `"vite": "^8.1.1"` or newer.
- Otherwise Vite will error with peer dependency conflicts during install.
2. Use `.tsx` for JSX in a TS/TSX project. Do not use `.jsx` with TS-style `import type ...`/JSX syntax — that triggers parser/build errors.
3. Import paths in `App.tsx` must be real file path. For example:
```ts
import App from './App';
```
inside `App.tsx` self-references are invalid. If components live in `src/components/`, import from `'./components/AppShell'`.
4. Keep React/Vite imports consistent across the workspace. Once a file is `.tsx`, treat all React code as TS/TSX.
5. Use `npm install --legacy-peer-deps` only when peer resolution blocks the demo and you’ve already aligned the versions. Prefer fixing manifest mismatch first.

## Phase 3: Verify
Run these in order. Do not move on until they pass or you have a single concrete blocker.

1. `npm install`
2. `npm run build`
3. `npm run lint`

If `npm run build` fails:
- First check unresolved imports and extension mismatch (`.jsx` vs `.tsx`).
- Then check dangling imports that reference missing files.
- Then check dependency manifest/peer conflicts.

If `npm run lint` shows only external warnings in `node_modules`, stop. Only clean up project-local warnings where they are cheap and visible to the user.
For creative UI work, hold test/lint interrupts until the user confirms the visual result or you are about to commit; build is still fine to rerun after edits, but linter noise shouldn't break pacing before polish is checked.

## Fast-Mode Demo Adjustments
When the user explicitly asks for a 1-hour demo:
- Use localStorage or a lightweight in-memory mock instead of real backend/auth.
- Use role-selected login — no real Azure AD or Graph credentials.
- Use a professional color scheme from the brand spec.
- Include position analytics and plan-vs-actual indicators.
- Deliver a working build they can view with `npm run dev`.

## Identity / Data-Layer Decision
In fast-prototype scaffolds, do not invent demo accounts if the app already contains a seeded user model. Use the seeded identities as the login source of truth so downstream fields—`assignedTo`, filters, org-chart relationships—can use stable IDs instead of human names. This avoids later rewiring when the UI adds “mine”, owner filters, per-position analytics, or delegation. See `references/seed-first-identity-pattern.md`.

## TSX Iterative-Edit Hygiene
When evolving an existing Vite+React+TSX demo, prefer a shared component over inline copy-paste.
- When a small reusable control like `BackButton` is needed in multiple views, create it once under `src/components/` and import it everywhere.
- If repeated edits corrupt a component header or leave duplicate/undeclared JSX references, read the whole file and rewrite the top block cleanly rather than patching the same region again.
- After shared-component extraction, remove now-dead inline imports and unused type imports; oxlint often flags lightweight lint noise like unused `ReactNode`, unused `View`, or duplicate imports quickly.
- Run `npm run build && npm run lint` after every 2-3 UI patches; early verification prevents long debugging tails on file-level regressions.
- See `references/tsx-iterative-edit-hygiene.md`.

## Pitfalls
1. Do not put TS syntax into `.jsx` files unless you add a parallel TS page at the same relative path. Mixed extensions break the module graph.
2. Project-local relative-import drift is common when adding siblings/aliases later: `src/App.tsx` may be edited to `import ... from '../data/mock'` even though siblings like `./components/...` now dictate `./data/...`. Treat any `UNRESOLVED_IMPORT` from `src/App.tsx` as a relative-path review first.
3. Do not skip `npm run build` after creating a new project. Passing dev mode is not evidence of a solid scaffold.
4. Do not commit until the user explicitly asks. Leave secrets and tenant credentials out.
5. For prototype lint hygiene, do not allow linter config drift to mask project-source issues. When oxlint reports only external `node_modules` noise, fix the config—usually by scoping lint to `src`, adding a minimal `.oxlintrc.json`, and fixing project-local type/env references—instead of weakening verification. See `references/oxlint-project-scoping.md`.
6. Do not let the app shell hide unfinished pages behind generic placeholder panels. It looks polished but the UI remains functionally empty. Wire real view components through the shell, and keep placeholders inside feature components only if a feature is genuinely incomplete.
7. If mock data defines seeded identities, login should select from that source of truth instead of fabricating ephemeral accounts. Human-name identity wiring breaks owner filters, `mine`, and per-position analytics later. See `references/seed-first-identity-pattern.md`.

For root-relative import fixes after sibling component additions, see `references/relative-import-drift.md`.

## Verification Evidence
Always report:
- `npm run build` status: pass/fail
- `npm run lint` status: pass/fail
- If blocked, state the concrete blocker and last failing command output.
