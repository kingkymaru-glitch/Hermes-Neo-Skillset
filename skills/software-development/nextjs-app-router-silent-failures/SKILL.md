---
name: nextjs-app-router-silent-failures
description: Next.js link/tab/iframe silently blank or dead, no error.
---

# Next.js App Router — Silent Failures

Class of bug: app builds clean, route "exists", but clicking a button / opening a tab /
loading an iframe does nothing or shows blank/redirect with no stack trace. Two common
causes + a verify-with-real-tooling method.

## 1. Middleware auth-gating STATIC files (incl. .html iframes)

Symptom: a workspace/library tab opens `<iframe src="/studio/foo.html">` but the panel is
blank / shows the login page. No JS error on the parent page.

Root cause: `middleware.ts` matcher excludes some static extensions but NOT `.html` (or the
specific path). Middleware runs on the static request, finds no session, and
`NextResponse.redirect("/login")` → iframe loads `/login` instead of the builder.

Verify (real probe): boot dev server, then
  curl -sI http://localhost:3000/studio/foo.html
  → `HTTP/1.1 307` + `location: /login` on a static .html IS the bug. After fix → `200`.

Fix: extend matcher negative-lookahead to exclude `.html?` + the static dir:
  matcher: ["/((?!_next/static|_next/image|favicon.ico|studio/|.*\\.(?:svg|png|jpg|jpeg|gif|webp|glb|obj|html?)$).*)"]
  (Keep existing excluded extensions; ADD `html?` + explicit `studio/` prefix.)

## 1b. Middleware's `isPublic` allowlist is DENY-BY-DEFAULT — a new public route 307s to /login

Symptom: you add a page that MUST be reachable logged-out (a legal page, a status page, a
public share route) and it silently bounces to `/login`. No error; the page simply never renders.

Root cause: `middleware.ts` gates EVERYTHING, then exempts a hand-maintained `isPublic` list of
path prefixes. Creating `src/app/privacy/page.tsx` does NOT make `/privacy` public — the list is
the authority and it is deny-by-default. This is a DIFFERENT mechanism from §1's matcher regex:
the matcher decides whether middleware RUNS at all; `isPublic` decides what it lets through once
it runs. A path can pass the matcher and still be redirected.

Verify: `curl -s -o /dev/null -w "%{http_code} %{redirect_url}\n" https://<host>/<newpath>`
— `307 https://<host>/login` IS the bug; `200` after the fix. Probe EVERY expected-public path
in one loop, since the list drifts as routes are added.

Fix: add the prefix to `isPublic` alongside the existing entries:
  path.startsWith("/privacy") || path.startsWith("/terms") || path.startsWith("/cookies") ||

Compliance note: legal pages (Privacy / Terms / Cookies) linked from a public landing page MUST
be readable BEFORE registration/consent (PDPA/GDPR). A privacy notice behind an auth wall is a
compliance defect, not a cosmetic one — treat any 307 on those paths as high severity.

Rule: whenever you add a route a logged-out visitor must reach, add it to `isPublic` in the SAME
commit, and curl the path to prove it.

## 2. React #418 hydration mismatch from locale/TZ-dependent dates

Symptom: console `Minified React error #418` (text content does not match server HTML) on a
page that otherwise works. Often paired with an unrelated 400 RPC in the same dump — do NOT
conflate them.

Root cause: component renders `new Date(x).toLocaleDateString()` / `.toLocaleString()`
DURING render. Server (Node/UTC) and browser (local locale + TZ) emit different strings →
hydration mismatch. Worst when data comes from server-component props (available on first SSR
pass). Client-fetched data (inside useEffect) does NOT mismatch (renders "loading" first).

Fix: deterministic formatter:
  new Intl.DateTimeFormat("en-CA", { year:"numeric", month:"short", day:"2-digit",
    timeZone:"UTC" }).format(d)
  (add hour/minute + hour12:false for datetime). `timeZone:"UTC"` makes server+client identical.

## 3. Deep-link tab guard silently drops a valid tab

Symptom: a nav entry (e.g. Settings dropdown "LunaV Studio") does
`router.push('/x?tab=studio')`; the route reads `searchParams.tab` and passes it as an
`initialTab` prop, but the user lands on the DEFAULT tab (e.g. "3d"), not the deep-linked
one. No error — the target just never activates.

Root cause: an explicit exclusion in the tab-init logic, e.g.
  const effectiveInitialTab = initialTab && initialTab !== "studio" ? initialTab : "3d";
Written when the studio tab was "removed", then a Settings entry was added that deep-links
to it — so the guard and the new link contradict. `router.push` works; the receiving
component throws the value away.

Verify: grep the tab-init code for `!== "<value>"` / `&& initialTab` exclusions; check
every `?tab=` value the UI can emit is accepted by `effectiveInitialTab`. The studio tab
is still rendered for owners (`.filter(([t]) => !(readOnly && t === "studio"))`), so
allowing it as an initial tab is safe.

Fix: accept the deep-linked value unless it must be forced (readOnly -> "report"):
  const effectiveInitialTab = readOnly ? "report" : initialTab ?? "3d";

## 7. Sub-tabs inside a hidden parent tab render invisibly
Symptom: you add a sub-tab row (e.g. `LUNASCAN | Model Library | Builder`) inside an
existing tab, and clicking a sub-tab appears to do nothing — or the panel content is
blank while the tab buttons themselves work.

Root cause: the parent tab container is toggled with `hidden`, and the inner layout uses
`h-full`/`min-h-0 flex-1`. A `hidden` ancestor gives its subtree no box, so the child's
`h-full` resolves against zero height. Switching sub-tabs re-renders but the content has
no height to occupy. Also common: the parent is `absolute inset-0` WITHOUT `flex flex-col`,
so a sub-tab bar + a flex-1 body cannot share the space.

Fix — make the parent a real flex column so the bar is fixed and the body takes the rest:
```tsx
<div className={tab === "studio" ? "absolute inset-0 z-10 flex flex-col" : "hidden"}>
  <div className="flex shrink-0 items-center gap-2 border-b px-4 py-2">{/* sub-tab buttons */}</div>
  <div className="min-h-0 flex-1">{/* active sub-tab body */}</div>
</div>
```
`shrink-0` on the bar + `min-h-0 flex-1` on the body is the combination that works; without
`min-h-0` a flex child refuses to shrink below its content and pushes the body off-screen.

## 8. The sub-tab state must be RESET when the entry point changes
A Settings dropdown entry that deep-links into a tab (`setTab("studio")`) leaves the
previously-selected sub-tab active. If the user last visited "Builder" and the header
chip's "open jobs" button sets only the parent tab, they land on the wrong sub-tab and
conclude the feature is missing. Every entry point must set BOTH: `setStudioTab("lunascan");
setTab("studio")`. Grep each `setTab("<parent>")` call site and confirm it also sets the
intended sub-tab.

## 9. Verify with real tooling (don't trust "build passes")

- `npm run build` = type-check gate. Exit 0 → compiles + TS clean. Run after edits.
- Route/redirect bugs: boot dev server, `curl -sI <route>`, read status + `location`.
  307→/login on a static asset = middleware gate bug.
- Lint errors in unrelated files (e.g. Viewer3D.tsx) are NOT your regression; lint the
  single changed file: `npx eslint <file>`.
- "Button does nothing": grep the label, trace onClick/tab state, then curl the target
  route/iframe to see what it actually returns.

## 5. Verify an RPC is actually deployed (no SQL access)

When a `supabase.rpc()` 400/404 is suspected to be an undeployed function, confirm
presence on the LIVE DB via anon REST (no creds beyond the public anon key):
anon `POST /rest/v1/rpc/<fn>` with a dummy uuid arg returns `401` = deployed+auth-gated
(good), `404` = missing (SQL not run). Full recipe + result table:
`references/supabase-rpc-presence-probe.md`.

## 6. Static prerender crash from top-level Supabase client creation

Symptom: `npm run build` (Next.js App Router) fails during "Generating static pages":
  Error occurred prerendering page "/update-password".
  Error: @supabase/ssr: Your project's URL and API key are required to create a Supabase client!
Only one page fails (the one that constructs the client at module/render time); other
Supabase pages build fine because they create the client inside effects/handlers.

Root cause: a `"use client"` page component calls `createClient()` (browser or server) at
the TOP of the component body, so Next's static prerender pass executes it with no env
vars loaded and `@supabase/ssr` throws. The other pages defer client creation into
`useEffect`/handlers, so they never hit it during prerender.

Fix: lazy-init the client through a getter invoked only inside the effect/handler, so the
prerender pass never constructs it. Example:
  const supabaseRef = useRef<ReturnType<typeof createClient> | null>(null);
  function getSupabase() {
    if (!supabaseRef.current) supabaseRef.current = createClient();
    return supabaseRef.current;
  }
  // then: useEffect(() => { getSupabase().auth.getSession()... }, [getSupabase]);
  //       await getSupabase().auth.updateUser(...)
Also tidy any implicit-`any` on the `.then(({ data }) => ...)` callback (prerender type-check
will fail on `data` otherwise): type it as `{ data: { session: unknown } }`.

Verify: `npm run build` → "✓ Generating static pages" with no prerender-error line, EXIT 0.
Full reproduction recipe + known-good template: `references/next-prerender-supabase.md`.

## Pitfalls
- **Never ask the user to paste a god-key into chat when you can have them write it to a file.** `service_role` bypasses all RLS; R2 keys write the bucket. Both land permanently in the session transcript. Offer the file path + line numbers and let them edit it themselves. If they DO paste one, do not echo it back, and flag the exposure once — then move on.
- **Verify a pasted secret before declaring it invalid.** A key copied out of a notes app can show its middle elided (`eyJhbG..._7_8`) — a DISPLAY artifact, not a truncated value. Decode a JWT payload and check `ref` matches the project, or make one authenticated call. Judging by appearance alone and telling the user their key is broken wastes their time and is usually wrong.
- A 400 from supabase.rpc is usually a MISSING/UNDEPLOYED function or signature mismatch on
  the LIVE DB, not client code. If no SQL access (env rule: DDL applied manually in Supabase
  Dashboard), prepare an idempotent `CREATE OR REPLACE FUNCTION ...` SQL file for the user;
  never claim it was applied. (Verify it landed with the §5 probe — `401` confirms deploy.)
- Don't assume the visible console error is the only bug. The studio-link (#1) and the
  hydration (#2) were independent and both needed fixing in one session.
- A deep-link tab guard that excludes a valid `?tab=` value is a SILENT failure: the nav
  link works but lands on the default tab. After adding any `?tab=` deep-link, grep
  `effectiveInitialTab` / `initialTab` exclusions to confirm the new value isn't dropped.
- Next.js may warn "middleware file convention is deprecated, use proxy" — functional, not an error.
- A page that builds locally (env present in .env.local) but fails prerender in CI with
  "URL and API key are required" means a Supabase client is created at render time, not
  lazily. Audit for top-level `createClient()` calls and defer them into effects/handlers.
