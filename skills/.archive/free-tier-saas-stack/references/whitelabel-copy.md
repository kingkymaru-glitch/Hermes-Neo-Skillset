# White-label copy centralization for multi-customer apps

When an app will be deployed for multiple customers (e.g. one product, TNB today, a different client next), do NOT hardcode client-specific strings (names, taglines, "to X's strategic goals") into components. Isolate them.

## Pattern that shipped cleanly
- Create `src/config/copy.ts` exporting a single `copy` object: brandHeader, brandFooter, tagline, subtext, loginTagline, loginSubtext, dashboardTitle/Subtitle, empty-state strings, etc.
- Components import `{ copy }` and render `{copy.loginTagline}` etc. — no literal client strings in JSX.
- To onboard the next customer, edit ONLY `copy.ts`. No component surgery.

## Why this matters mid-build
A user asked to "remove all TNB" to make the repo generic, then two turns later asked to inject TNB taglines "for our TNB client." If the taglines had been hardcoded across Login/Dashboard/empty-states, the second request would have scattered TNB across the codebase and destroyed the generic goal. Centralizing meant the second request was a one-file edit AND the generic capability survived.

## Inject points that earned strategic value (RINA case)
- Login hero (above the account picker): tagline `<h1>` + subtext `<p>`.
- Dashboard header block: title + subtitle above analytics.
- Empty states ("No active initiatives yet" / create-first prompt) instead of generic "No tasks".
- Default app-shell header title should fall back to `copy.brandHeader`, not a hardcoded generic label, so the nav reads consistently.

## Reusable client onboarding brief
When handing a build to another agent (e.g. "lead deployment for client X like we did for Y"), summarize: stack, repo, local path, what's done, the genericization choice, the deploy playbook (build → commit → push → Vercel for a static SPA; add Supabase+auth for multi-user shared data), and watch-outs (Supabase free email rate limit; set Site URL to the live domain so confirm emails don't point to localhost).
