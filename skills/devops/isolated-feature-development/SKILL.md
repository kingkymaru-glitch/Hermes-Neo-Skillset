---
name: isolated-feature-development
description: "Isolated feature dev with separate backend on localhost."
---

# Isolated Feature Development

## Trigger

Starting a new feature, module, or product line that must not touch production data or deploy until complete.

## Hard Gates

1. **Discuss first, no code** — do not write implementation code until the user approves the design/logic. Present options, trade-offs, and the control surface. Await explicit "go" before any code.
2. **Feature-first, not schema-first** — build working software first; schema emerges from real feature needs, not a design document.
3. **Backend isolation** — use a separate Supabase project per feature/module. Never reuse the production Supabase project for development.
4. **Local-first** — run everything on localhost. Push to GitHub for record only. Do not merge to main or trigger deploys during development.

## Workflow

### 1. Design Discussion
- Present the feature scope, UX, data flow, and control surface.
- Do not write code until the user signs off.

### 2. Supabase Isolation
- Create a new Supabase project (free tier is fine).
- Link local Supabase CLI:
  ```bash
  cd <feature-repo>
  supabase init --project-id <short-id>
  supabase link --project-ref <project-ref>
  ```
- Create `.env.local` pointing to the new Supabase project.

### 3. Repository Setup
- Work on a feature branch: `feature/<name>` or `arras/<feature-name>`
- Do not push to main during active development.
- If the repo is connected to a deploy platform, pause Git integration or use skip markers to prevent deploys.

### 4. Build and Verify Locally
- Run the app on localhost.
- Verify the feature works before pushing.
- Push the branch to GitHub for record only.

### 5. Schema Changes
- Write SQL migration files in `supabase/migrations/` with date prefix.
- Apply via `supabase db push` only when the schema is needed for the feature.
- Do not write speculative schema for features not yet built.

### 6. Merge Only When Ready
- Only merge to main and enable deploys when the feature is complete and verified.
- Do not leave half-built features on main.

## Non-invasive variant: restyle the REAL app without touching it

When the ask is "rebuild page X with a different design/layout, but do not modify any
existing function" and "use the actual code and data", do not fork or refactor. Add a
parallel page that IMPORTS the real components and wraps them in new chrome.

**Rules**
- **New files only.** Pages/components you add; never edit the existing ones. Prove it before
  reporting: `git status --porcelain` must show only `??` lines for your new paths. If an
  existing path shows `M`, you broke the constraint — revert it.
- **Wrap, never extend.** If the component lacks the knob you need (a lighting/exposure prop,
  a theme switch), apply it from outside — a CSS filter on a wrapper div, a scaled container,
  a class on the parent. Adding an optional prop still means editing a shipped component, and
  the user's constraint is usually literal.
- **Read-only by construction.** Pass the existing read-only flags (`readOnly`, watermark off)
  and supply no-op callbacks for every mutation handler. Say so in the UI (a `READ-ONLY` tag)
  so nobody assumes clicking Save is safe on production data.

**Getting a new route past an auth wall without editing the middleware**
A Next.js middleware usually whitelists path PREFIXES. Read it, find one already treated as
public, and nest your route under it (`src/app/<public-prefix>/<your-page>/page.tsx`). A static
segment beside a dynamic one (`share/[token]` + `share/twin-console`) is valid — static wins
for the exact path. This beats adding a bypass branch to middleware.

Flag the trade-off explicitly: a page under a public prefix is **publicly reachable if
deployed**. Say it out loud and never push it as-is.

**Data without a login**
Removing the sign-in gate and still showing real data are in tension. Under Supabase RLS an
anonymous visitor reads nothing — confirm it before promising otherwise (call the app's own
list RPC with the public anon key; an empty array is the answer). The only ways to real data
without a session are a server-side service-role key (read it from env, never ship it to the
browser) or a public share token. Pick one, wire it server-side, and surface which source is
active in the UI so an empty page is never mistaken for a bug.

## Pitfalls

- **Implicit model selection**: do not auto-switch models or data sources between tabs. Use explicit user selection instead.
- **Schema-first trap**: avoid designing full schema upfront. It becomes useless when the actual feature shapes it differently.
- **Production pollution**: never run migrations or seed data against the production Supabase during development.
- **Accidental deploy**: feature branches connected to deploy platforms will create preview deploys. Disable Git integration or use skip markers.
