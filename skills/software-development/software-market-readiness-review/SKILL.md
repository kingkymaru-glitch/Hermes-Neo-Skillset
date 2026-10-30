---
name: software-market-readiness-review
description: >-
  Three-hat review to make a build market-ready.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [review, market-ready, QA, critique, UX]
    related_skills: [flutter-ar-dev, github-repo-management]
---

# Market-readiness review (three hats)

## When to Use
- User says "is it ready for market", "review the app", "make it market-ready",
  "optimize and make it easy to use by any age", "does the design make people
  want to use it again", or any post-build "look at it critically" request.
- After an APK/IPA/build completes and the user wants a hard self-review before
  shipping. Adopt engineer + designer + user perspectives; produce fixes AND
  prove they compile/build.

User asks for a critical review of a finished feature/app before shipping. Adopt
THREE distinct perspectives, one at a time, and produce concrete fixes for each —
not praise. The user (MARU) explicitly wants: optimized, usable by any age, and
designed so people come back. A compiling build is NOT "done".

## The three hats (run in this order)

### 1. ENGINEER — robustness / correctness / leaks
Read the actual source (don't guess). Hunt for:
- Resource leaks: streams/subscriptions/timers never cancelled (GPS, Realtime,
  compass) → battery drain after the screen closes. Find the cancel/teardown.
- Permissions: does the app REQUEST Location/Camera, or assume they're on?
  On real devices they're off → silent failure. Gate the sensitive screen.
- Silent data drift: UI using a stale snapshot (e.g. DB copy of "my position")
  instead of live device state. Anchor to live GPS each tick.
- Broken deep links: magic-link / share links can't re-enter the app because no
  custom URL scheme / Android intent-filter / iOS Associated Domain. Verify the
  manifest/plist, not just the Dart code.
- Server holes: can an anon/browser client do something only an authed app user
  should? Enforce server-side (RPC raises on null auth.uid()).
- Dead code paths: buttons/onPressed that do nothing, links to nowhere.
Output: list of bugs + the exact file/method to fix.

### 2. DESIGNER — desire to return / clarity
- First screen: is it a wall of engineer choices (chips, toggles) or one clear
  value-prop + single primary CTA? Default to the latter.
- Can the user choose the focal subject (e.g. which friend the big arrow points
  at)? If it's hard-coded, add tap-to-focus.
- Dead affordances: replace stub onPressed with real dialogs/links.
- Give a payoff state: distance color cool→hot, "Arrived" under X m — the
  satisfying moment that drives reopening.

### 3. USER — any age / first time / low patience
- Steps-to-value: count taps from install to first result. Cut every gate that
  isn't essential (move skin/capacity picks to secondary sheets).
- Plain language: replace techy toggles ("all have app?") with friendly copy
  (5 vs 15 people).
- Always-visible reassurance: TTL countdown, participant count, "live only,
  auto-expires" privacy note, battery-saver toggle.
- Safety: a Report/remove flow the creator can actually trigger.

### 4. FRONT DOOR — the paths a stranger takes before they trust you
Run this as its own hat. These defects are invisible from inside a logged-in
session because you already have an account, and they are exactly what a new
customer or a regulator hits first.
- **Are the legal pages readable WITHOUT auth?** Privacy/Terms/Cookies linked
  from a public landing page must not redirect to login — a privacy notice
  behind an auth wall is a compliance bug (PDPA/GDPR require it before consent),
  not a cosmetic one. Probe every expected-public path for a `307`.
- **Can signup tell the user they already have an account?** Supabase's
  `signUp` returns a fake user with NO error for an existing email
  (anti-enumeration). Code that only checks `if (error)` will tell a returning
  user "awaiting approval" forever. Check
  `data.user?.identities?.length === 0`.
- **Does the public contact address actually exist?** Grep every `mailto:` and
  compare against the real admin address used elsewhere in the repo. A one-letter
  typo (`innovat`ed vs `invent`ed) black-holes customer mail silently and looks
  identical in review.
- **Is the brand mark the canonical one?** A login page pointing at a generic
  `logo.png` when the family has a canonical mark is the first brand impression
  and it is off-brand. Compare file hashes, don't eyeball.
- **Do the marketing claims match what the code does?** Read every promise on the
  landing page (free trial, plan limits, "no credit card") and grep the repo for
  the feature that backs it. A "Free 14-day Pro trial" with zero trial/billing
  code anywhere is a false-advertising exposure the customer can hold you to —
  report it and let the user decide (build it or drop the claim); it is a
  business decision, not a bug to silently fix.
- **Copy fixes leak across surfaces.** A wording fix applied to `/login` does not
  touch the landing page's own CTA — grep the jargon string repo-wide, not just in
  the file you already fixed.
- **Count the hops to the primary action, across every surface.** In a
  multi-surface product family (marketing site → product landing → app), trace
  the literal link chain from each entry point to the first real action. A
  marketing page whose only job is to say "sign in" is a full page load that adds
  nothing; if the family sites link to the *brochure* instead of the *app*, the
  user takes four hops to reach a login form. Decide whether the product landing
  page belongs on the critical path at all.
- **`target="_blank"` on family links destroys the journey.** Every cross-link
  opening in a new tab strands the user in a tab pile and breaks Back. Keep
  same-family navigation in the same tab; reserve new-tab for genuinely external
  destinations.
- **Look for a loop, not a path.** Family cross-links commonly form a cycle
  (A→B, B→A, and both→C) with no single "enter the product" door. Trace it as a
  graph, name the missing edge, and propose the one link that should point at the
  app.
- **Does the auth redirect remember where the user was going?** Middleware that
  rewrites the path to `/login` without carrying the original destination loses
  it — the user signs in, lands on a generic dashboard, and must re-navigate.
  Check that the destination is set on redirect AND honoured after auth. A single
  hardcoded special case (e.g. `?project=`) is not the general fix.

### 5. SECURITY HEADERS — one probe, whole class of missing hardening
Run `curl -sI https://<domain>/` and check for the response headers that should
be there. Their ABSENCE is the finding; an app can ship for months with HSTS
only and look fine in the browser.
- `x-frame-options` — without it any site can iframe the app (clickjacking).
  `SAMEORIGIN` is safe when the only framed content is same-origin (e.g. a
  builder iframe).
- `x-content-type-options: nosniff` — stops MIME guessing.
- `referrer-policy` — **`strict-origin-when-cross-origin` matters most on an app
  whose URLs carry project ids and share tokens**, which otherwise leak to every
  third-party destination via the `Referer` header.
- `permissions-policy` — turn off what the app does not use, but check the one
  feature it DOES (a WebAR/AR route needs `camera=(self)`).
- **CSP: propose, do not blanket-add.** A wrong `Content-Security-Policy`
  silently breaks model/asset loading from storage origins (Supabase Storage,
  R2) and same-origin iframes. Enumerating those origins is its own task — say so
  rather than shipping a CSP that looks hardened and breaks the app.
Add headers via `next.config.ts` → `async headers()` (Next) rather than a
middleware rewrite, and verify with `curl -sI` after the deploy lands.

## Detection techniques (grep for the defect, don't read for it)
Cheap greps that surface whole bug classes before you start reading files:
- **Silent failure:** count writes against error branches and notifications.
  `grep -c 'await supabase' <file>` vs `grep -c 'if (error' <file>` vs
  `grep -c 'toast\|setError' <file>`. Ten mutations, one error branch, zero
  toasts = the user cannot distinguish slow network from permission denied from
  server error. This is usually the single highest-impact UX finding in an
  internal-tool-turned-product.
- **Unconfirmed destructive actions:** list every `.delete()` and then list every
  `confirm(`. Any delete with no matching confirm is data loss one click away.
  Sibling deletes in the same file usually DO confirm — the stragglers are the
  ones added in a different era, so check each, don't assume the pattern held.
- **Accessibility gap:** ratio of `aria-label` to `<button>`. A large ratio
  imbalance means icon-only controls are unlabelled for screen readers.
- **Missing safety-net routes:** absence of `not-found.tsx`, `error.tsx`,
  `loading.tsx` in the app dir — a render error then blanks the app with no
  recovery path.
- **Toast caps:** `slice(-N)` on a notification queue silently DISCARDS the
  oldest messages — which are the errors, during a burst of failures. Confirm
  errors are never the ones dropped.
- **Security headers:** `curl -sI https://<domain>/ | grep -iE
  'x-frame|nosniff|referrer|permissions-policy'`. Zero output = the app ships
  with no hardening beyond HSTS. Whole class found in one command.
- **Navigation chain:** list every external `href` and its `target` across the
  family repos in one grep, then follow the chain from each entry point to the
  first action. `grep -rn 'https\?://' src/` filtered to your own domains shows
  every hop; the count of hops and the presence of `target="_blank"` is the
  finding. In a client-rendered SPA the served HTML has no links — read the
  source repo, not the page.

## Output format
For each hat: 2-4 bullets of WHAT'S WRONG + the FIX you then implement. Then
actually implement the fixes (patch the code) and PROVE it compiles
(`flutter analyze` / build) — do not stop at the critique. Report the build
artifact path as evidence.

For the silent-failure finding specifically, the repair recipe (toast discipline,
the `friendlyError()` translation table, the session guard, and how to verify the
fix on an auth-gated route) is in `references/error-feedback-remediation.md`.

For the missing-safety-net finding (`not-found.tsx` / `error.tsx` / `loading.tsx`),
the ready-to-adapt implementations — plus the custom-404 verification probe and the
`confirm` state-name collision — are in `references/app-shell-safety-nets.md`.

For the navigation-chain finding (hops to the primary action, `target="_blank"`
damage, the family cross-link loop, and the auth redirect that drops its
destination), the probe and the `?next=` recipe — including the open-redirect
guard it needs — are in `references/navigation-chain-audit.md`.

**Sequencing the fixes.** The findings group naturally into sprints by risk:
front-door/compliance holes and unconfirmed deletes first (small, high impact),
then silent-failure error feedback, then polish (safety-net pages, brand mark,
plain-language copy, a11y), then structural refactors last. Present them that way
and build one sprint at a time — the user wants the risky holes closed before the
cosmetic ones. Bump the app version + tag each sprint so the live stamp moves.

**Re-audit after the fixes — the second pass finds new findings.** Once the
sprints ship, re-run the whole review against the LIVE build before declaring
done. Fresh eyes on the deployed artifact surface defects the first pass could
not see (missing security headers, a marketing claim with no backing code, a
copy fix that missed a surface). A review that stops at "all N original findings
closed" is not finished; the deliverable is the live build re-examined. Treat
those new findings as a separate short sprint, and leave anything that is a
business decision (pricing/trial claims) as an explicit question for the user
rather than editing it yourself.

## Pitfalls
- Don't narrate what you'd do — read the files, find the real bugs, fix them.
- A clean `analyze` with no rebuild is not proof the fixes work; build the
  artifact when the platform allows (APK at minimum).
- "Ready for market" ≠ "compiles". MARU expects engineer+designer+user self-
  review AND hardening to market-ready before "done".
- **When no browser is available, audit the DEPLOYED source, not your memory.**
  Drive the live site with `curl` for status codes and redirect targets, and read
  the exact source that is deployed. Tie every finding to a live HTTP response or
  a `file:line` — an audit that says "this looks like it might break" is not an
  audit. State plainly at the top which flows were verified by hand and which by
  code/HTTP, so the user knows the evidence boundary.
- **Deliver the findings BEFORE proposing the build.** The user asked for a
  review, not a refactor. Group by severity, lead with the few that actually hurt,
  and name what already works well — then offer the fix list as the next step and
  wait. Do not start editing code during a review pass.
