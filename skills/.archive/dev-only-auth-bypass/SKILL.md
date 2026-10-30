---
name: dev-only-auth-bypass
description: Add a localhost-only skip-login path to an auth-gated web app (Next.js App Router plus Supabase, or Vite React SPA) for local debugging, double-guarded so it can never fire in production.
triggers:
  - user cannot log in on localhost or the dev server
  - add a dev-only bypass
  - skip login for local testing
  - debugging an auth-gated app without real credentials
  - mark it dev only on an auth shortcut
category: software-development
---

# Dev-only auth bypass (local debugging ONLY)

Goal: let the developer reach the app's main page locally WITHOUT fighting the
real auth gate (Supabase email-confirm, approval-pending, forgotten password),
while making it physically impossible for the bypass to work in production.

## Hard rules (non-negotiable)
- NEVER gate on a custom env var the user could forget. Gate on
  NODE_ENV !== "production" AND a localhost host check. Production builds
  (Vercel next build / next start, vite build) run NODE_ENV=production, so the
  bypass self-disables with zero config and zero chance of leakage.
- The bypass must REDIRECT (not render) when the guard fails, so a prod hit just
  bounces to /login and leaks nothing.
- Never put real credentials in the bypass, and never call it from shared code
  paths that run in prod.

## Pattern A — Next.js App Router + Supabase (SSR)
1. Create src/app/dev-login/page.tsx (Server Component route):
   - import { headers } from "next/headers" and const host = (await headers()).get("host").
     PITFALL: in Next 15 headers() returns a Promise — you MUST await it,
     else: Property 'get' does not exist on type 'Promise<ReadonlyHeaders>'.
   - Guard: process.env.NODE_ENV !== "production" && isDevHost(host).
   - If allowed: supabase.auth.admin.listUsers() -> find/create the admin user
     (auth.admin.createUser with email_confirm true), upsert an approved
     profiles row, then auth.admin.generateLink({ type: "magiclink", email })
     and redirect("/auth/callback?token_hash=...&type=magiclink") (the existing
     auth callback sets the session cookie). Fallback redirect("/dashboard").
   - If NOT allowed: redirect("/login").
2. PITFALL - middleware: the auth middleware runs BEFORE the page and bounces
   unauthenticated /dev-login to /login. Add /dev-login to the middleware's
   isPublic list (e.g. path.startsWith("/dev-login")). The page re-guards
   anyway, so this is safe.
3. (Optional) a "Dev: skip login" link on landing/login pages, rendered only
   when typeof window !== "undefined" && process.env.NODE_ENV !== "production".

See references/nextjs-supabase.md for the exact route + middleware code.

## Pattern B — Vite / React SPA + Supabase (client-only)
- No server route. Add src/lib/devbypass.ts exporting:
  - isLocalDev(): !import.meta.env.PROD && localhost host.
  - devLogin(email): try signInWithPassword with a FIXED dev password; if the
    user is missing, signUp with company metadata + the same fixed password,
    then sign in again (email confirm is usually off in dev projects).
- Render a guarded "Dev: skip login (localhost only)" button in the Login
  component that calls devLogin(...) then the app's onLogin().
- SPA session is read from Supabase (getSessionUser), so creating+signing in a
  real (dev) user is enough — no fake localStorage session needed.

See references/vite-spa.md for the RINA-style code.

## Verification (do this before claiming done)
- Start a CLEAN dev server (next dev / vite), NOT a stale prod-mode instance.
  PITFALL: a leftover next dev started with NODE_ENV=production makes the guard
  refuse (correct behavior) and you will think the bypass is broken. Kill stale
  servers / clear the .next/dev lock before testing.
- Curl the dev route: expect 307 -> /dashboard then 200 with content.
- Confirm prod-mode refusal: a prod-mode server returns 307 -> /login.
- Both npm run build / vite build must stay green.

## Pitfalls
- headers() is async in Next 15 -> await it.
- Middleware intercepts /dev-login -> whitelist it in isPublic.
- Stale dev server from a prior prod-mode run masks the bypass — restart clean.
- Do not bake the bypass into the real login POST handler.
- The skip-login link must be gated client-side too (it will not render in
  prod because process.env.NODE_ENV / import.meta.env.PROD is production there).

## PER-USER OPT-OUT — this user/project (LunaV Solutions / ss-rover-cloud) is OFF
The founder (kamarulhk) explicitly rejected the dev-bypass on 2026-07-26:
"stop with this local dev only thing now", "no localhost drama again", "make the
changes directly push to GH". For THIS project do NOT add `/dev-login`,
`devbypass.ts`, or "Dev: skip login" buttons — even though the pattern below is
technically sound. If the user "can't log in on localhost", diagnose the REAL
cause instead of bolting on a bypass:
- Wrong email spelling: it is `inventedmaru@gmail.com` (**E**, not `innovated`).
- Email-confirm toggle still ON (Supabase dashboard: Authentication → Emails →
  Templates → "Confirm sign up").
- Approval gate: new signups need admin approval (redirects to /login?reason=pending).
This skill remains valid for OTHER users/projects; just respect the standing
preference for this one. (Recorded in `ss-rover-cloud-dev` too.)

## References
- references/nextjs-supabase.md — full route + middleware snippet (SSR Cloud).
- references/vite-spa.md — RINA Vite SPA devbypass.ts + Login button.
