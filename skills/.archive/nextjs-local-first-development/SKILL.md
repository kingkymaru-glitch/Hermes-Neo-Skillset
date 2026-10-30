---
name: nextjs-local-first-development
description: "Local-first Next.js + Supabase dev with branch isolation."
---

# Next.js Local-First Development

## Trigger

Use when:
- Building or modifying a Next.js + Supabase app
- Working on a feature that should not affect production
- User wants localhost-first with GitHub as the only remote
- Avoiding Vercel auto-deploy for in-progress work

## Workflow

1. **Create feature branch**
   ```bash
   git checkout -b <feature>/<name>
   ```

2. **Local dev only**
   - Run `npm run dev` on a local port
   - Point `.env.local` at local Supabase or a separate cloud project
   - Never merge to main until feature is complete

3. **Prevent Vercel deploys**
   - Add `[skip deploy]` to commit messages on feature branches
   - Or temporarily pause Vercel Git integration for the repo
   - Feature branches should only push to GitHub

4. **Separate Supabase projects**
   - Each product line gets its own Supabase project
   - Never mix development data with production data
   - Use Supabase CLI to link local config to the correct project

5. **Design before code**
   - Always discuss UX/architecture with user before writing code
   - User preference: "no code, discuss" — present options, get agreement
   - Big upfront schema is discouraged; schema should evolve from working features

6. **Build verification**
   - Run `npm run build` before considering work complete
   - Fix TypeScript errors before proceeding

## Pitfalls

- Don't use the production Supabase project for development work
- Don't push feature branches to Vercel-enabled remotes without deploy guards
- Don't design big upfront schemas; let features drive schema evolution
- If localhost hangs after state changes, kill the dev server and restart fresh

## References

- `references/arras-model-slots.md` — ARRAS-specific dual-model slot pattern
