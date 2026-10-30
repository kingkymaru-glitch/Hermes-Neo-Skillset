---
name: project-handover-docs
description: Author a complete handover documentation set (README, ARCHITECTURE, CONTRIBUTING, LICENSE, .env.example) for an existing codebase so a new owner can understand and run it without the original author. Emphasizes reading real source before writing and documenting limitations honestly.
---

# Project handover documentation

Use when: the user asks to "write a README", "document this so others can understand it", "complete the documentation", or prepare a repo for hand-off to another developer/team/client.

## Golden rule: read the source before you document
NEVER write docs from the project name, folder listing, or an Obsidian spec note alone — those describe intent, not the shipped code. Read the actual files first:
- Entry point + top-level app file (routing/state) — how screens/modules connect.
- Type definitions / data models — the real data shape.
- Seed/mock/fixture data — what the app runs on.
- Auth/login file — the real sign-in mechanism (often a demo shortcut, not real auth).
- package.json — real scripts, deps, and versions (don't guess the framework or commands).
Every claim in the docs must trace to something you saw in the code.

## The standard doc set
1. **README.md** — the front door. Include: one-line what-is-it, a feature-tour table, roles/permissions if any, tech stack with versions, exact clone/install/run/build/deploy commands, an npm-scripts table, project-structure tree with per-file one-liners, a data/persistence section, a roadmap/handover section, license pointer.
2. **ARCHITECTURE.md** — high-level flow diagram (ASCII is fine), data model, business rules and where they live, state/persistence story, styling approach, known limitations, a "where to change things" table.
3. **CONTRIBUTING.md** — setup, the lint+build gates to pass before commit, code style, commit-message convention (match existing git history), good first tasks.
4. **LICENSE** — ask or infer; default to proprietary/internal for a commercial/client project, never assume MIT.
5. **.env.example** — even if the app needs no env vars, add a placeholder documenting that fact and where future config would go.

## Document limitations HONESTLY — this is the highest-value part
The most useful thing for a new owner is the truth about what looks done but isn't. Actively hunt for and call out gaps, e.g.:
- A localStorage/persistence layer that exists in `hooks/` but is NOT wired into the app (edits reset on refresh) — this exact trap appeared in RIINA. State it plainly in README + ARCHITECTURE and make wiring it the #1 "good first task".
- Placeholder screens, mock auth ("any password works"), data shapes with no backing feature (e.g. `attachments` field with no upload).
Papering over these to make the project look finished actively harms the hand-off.

## Inconsistencies: flag, don't silently "fix"
If you find a naming/spelling/branding inconsistency (e.g. repo "RIINA" vs in-app footer "RINA"), document both as-is and ASK the user whether to standardize. Silently rewriting brand/name strings during a docs pass is scope creep and may be wrong.

## Verify + ship
- Run `npm run build` and `npm run lint` (or project equivalents) before committing docs — proves the setup instructions you just wrote actually work.
- Commit with a `docs:` conventional message and push. For version-control/gitignore/gh-auth pitfalls when pushing to GitHub, see the `supabase-r2-vercel-stack` skill's version-control section (Keychain gh auth, .gitignore-before-add for bare Vite projects, private repo one-shot create).

## Related
- `codebase-orientation` — for MAPPING an unfamiliar codebase (function/feature inventory). This skill is for AUTHORING the hand-off doc set afterward.
