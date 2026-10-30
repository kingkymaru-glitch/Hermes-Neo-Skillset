---
name: maru-ui-theme-sync
description: Sync LunaV/R-Tessera/Luna-EDGE UI + the build≠deployed rule.
---

# MARU Frontend Theme Sync & Deploy-Verify

## When to use
- Syncing look / feel / theme / header / branding across MARU's three frontends:
  **LunaV** (Next.js · lunavsolution.vercel.app), **R-Tessera** (Vite+React · r-tessera.vercel.app),
  **Luna-EDGE** (Flask+HTML · local http://localhost:8000).
- After ANY UI edit, if MARU says "I don't see the change" / "no difference before and after"
  — that is the #1 symptom of the deploy-verify gap below. Fix the deploy, not the code.

## THE RULE: a passing build is NOT verification

## Header chrome — version stamp + button affordance (MARU standing preferences)
- **Visible version stamp:** every shipped app renders its version in the header as a pill (e.g.
  `POC Shell · V0.12`) from ONE source constant, bumped in the same commit as the release. He reads
  it to confirm the screen matches the build he was told shipped — a stale/hardcoded stamp is a bug.
  (Full rule + rationale: `founder-workflow` → "Visible version stamp".)
- **Label over icon:** for a recognisable action use a **text-labelled button**, not a bare icon
  glyph (MARU: a "Setting" text button, NOT a gear icon — "to make it look professional"). Reserve
  icon-only buttons for compact toolbars.
- **Respect placement calls literally:** "shift it to the most right" = reorder the header so it is
  the LAST item in the right `ml-auto` group.
These frontends go live two ways. A change is only visible after the matching step:

1. **Vercel (LunaV, R-Tessera):** must `git commit` + `git push origin main`. Vercel auto-deploys,
   BUT the webhook only fires if the commit author is `kingkymaru@gmail.com`. Commit with:
   `git -c user.name=maru -c user.email=kingkymaru@gmail.com commit -m "..."`
   Then confirm the live URL returns 200 and the change is actually present.
2. **Local Flask (Luna-EDGE, ~/luna-edge):** must restart the server. Editing
   `templates/index.html` does nothing until restart:
   `pkill -f luna-edge/app.py` then `cd ~/luna-edge && source .venv/bin/activate && python app.py`
   (or double-click Luna-EDGE.app on the Desktop).
3. `npm run build` / `npm run dev` starting clean only proves it **compiles**. It does NOT prove
   MARU can see it. **Never say "done/verified" until the artifact is live and visible.**
   Session 2026-08-12: claimed all three "done" on build pass; MARU saw zero change because
   nothing was committed/pushed/restarted. That was the miss.

## MANDATORY DEPLOY SEQUENCE (run as one flow, never stop early)
After editing UI, do ALL of these in order before reporting done. Do not tell MARU
"done/verified" at the build stage:

1. **Build** (`npm run build` for Vercel apps; Luna-EDGE needs only a Flask restart, no build).
   Check the REAL build exit code (NOT the pipe's): `npm run build > /tmp/b.log 2>&1; echo "EXIT=$?"; tail -6 /tmp/b.log`.
   NOTE: `npm run build 2>&1 | tail -6; echo "EXIT=$?"` is WRONG — `$?` is `tail`'s exit (always 0), not the build's, so it hides build failures.
2. **Commit** with the Vercel author so the webhook fires:
   `git -c user.name=maru -c user.email=kingkymaru@gmail.com commit -am "..."`
3. **Push**: `git push origin main`.
4. **Wait** ~45–60s for Vercel to build + auto-promote (the alias lag is timing, not failure).
5. **Curl-verify live** BEFORE claiming done:
   - `curl -s -o /dev/null -w "%{http_code}" https://lunavsolution.vercel.app` → 200
   - `curl -s -o /dev/null -w "%{http_code}" https://r-tessera.vercel.app` → 200
   - Luna-EDGE: `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000` → 200
   (restart Flask first if you touched its HTML: `pkill -f luna-edge/app.py; cd ~/luna-edge && source .venv/bin/activate && python app.py &`)
6. Only now say "done" — and note it's live, not just built.

A reusable helper exists: `scripts/verify-theme-deploy.sh` runs the curl checks for all three
in one shot. It ALSO takes a search string and greps the freshly built `dist/assets` bundle, so
you can prove the change is IN the artifact — not just that the server is up. That content gate
is the difference between "deployed" and "live with the change." Usage:
  ./scripts/verify-theme-deploy.sh "LunaV R-Tessera - ROVER-R"          # liveness + content gate
  ./scripts/verify-theme-deploy.sh "search term" ~/Documents/R-Tessera  # custom repo dir
Pair it with the `vercel-prod-deploy-verification` skill if the live URL still serves old code
(alias-lag vs webhook-miss).

## TRIAGE ORDER when MARU says "I can't see it / still no difference"
Decide deploy-miss vs CSS-clip BEFORE editing more code — they need opposite fixes:
1. **Is the artifact even live + containing the change?** Run
   `scripts/verify-theme-deploy.sh "<unique new string>"`.
   - curl non-200 → deploy/restart miss (commit author, push, or Flask restart).
   - 200 but the string is NOT in `dist/assets` → build didn't run / didn't pick up the edit
     (rebuild, check exit code, re-verify). This is exactly how the 2026-08-12 `&&`-masked build
     failure was caught: `grep -c "proj-drawer-tab" dist/assets` returned 1 (stale bundle) because
     the failed build never regenerated `dist`.
2. **Artifact is live + string present, but invisible on screen** → CSS clipping, NOT deploy.
   Reach for `position:fixed` (top-layer rule) or fix the flex `height:100%` trap. Verify with a
   browser DOM/computed-style check or screenshot. Do NOT push again — it's already deployed.
Never re-edit-and-repush blindly; that masks a CSS bug as a deploy bug and wastes cycles.

THE MISTAKE PATTERN TO AVOID: editing → `npm run build` → "done, verified." That skips
commit/push/restart entirely, so the running site is still old code. MARU catches this
every time with "I don't see any difference." Build success is a STEP, not the FINISH.

## Shared design system (reference = LunaV glassmorphism)
- **Glass surface:** `backdrop-filter: blur(22px)`, translucent bg `rgba(20,23,28,0.82)`
  (LunaV exposes it as `var(--glass)`), 1px hairline `rgba(150,175,205,0.14)`. Header height 56px.
- **Brand wordmark (EDGE-style):** `LunaV` in primary white + project name in turquoise accent.
  R-Tessera → `LunaV R-TESSERA`; Luna-EDGE → `LunaV EDGE`; LunaV itself → `LunaV STUDIO`
  (STUDIO bold + turquoise). The "L" mark gradient differs by repo: LunaV/EDGE use blue
  `linear-gradient(135deg,#2f9bff,#1b6fd0)`; **R-Tessera's mark is GOLD** — `linear-gradient(135deg,#C9A96E,#a8854f)`
  + gold glow (recolored 2026-08-13 to match the LunaV Labs gold port; supersedes the earlier
  green `#00e5c3` mark). Do NOT copy the blue mark into R-Tessera. R-Tessera's chrome is now
  full GOLD (#C9A96E) — node markers, link pin, `.proj-row-tag.public`, `.mcp-foot code`, and the
  Labs "visit" link were all recolored from cyan/blue to gold at founder's "full unity" call.
- **The family MARK is one shared FILE — copy it, never redraw it.** LunaV Labs and R-Tessera ship
  a byte-identical `favicon.svg` (purple zigzag ribbon, `viewBox 48x46`, `#863bff`/`#7e14ff` with
  `#ede6ff` 3D highlights) — confirm two marks match with `md5 -q` rather than by eye. When bringing
  a repo into the family (CDM did it via a thin `LunaVMark` component rendering
  `<img src="/favicon.svg">`, plus `app/icon.svg`), copy that same file and keep the component thin
  so the mark cannot drift. Do NOT hand-draw a lookalike.
  TRAP: `Documents/R-Tessera/public/r-tessera-logo.png` is a navy/orange asset referenced NOWHERE in
  the codebase — it is NOT the family mark, and neither is `ARRAS/public/logo.png` (teal `#04bfd0`
  on `#0b1220`). Grep for a reference before treating an orphaned logo file as canonical.
- **Buttons:** reuse LunaV's `.mb-btn` glass pill — subtle bordered, hover lift `translateY(-1px)`,
  active/primary state teal `rgba(0,229,195,...)`. Apply the same class to all three headers so
  they match. Exact CSS in `references/design-tokens.md`.
- **Mixed square/soft-edge boxing (design language, confirmed 2026-08-13):** NOT every button is a
  pill. Founder wants *selective* squaring — sharp square = the important link/action, soft edge =
  ambient chrome. Rule:
  - SHARP (square, `border-radius: 2px`, thin 1px hairline border) → priority links & actions:
    project detail buttons, pin-save, labs nav, the header cross-project link (R-Tessera's
    `.rt-hdr-link` "LunaV Studio" → lunavsolution.vercel.app), and the primary action variant
    (`.mb-btn-primary`). Labs-nav gets `4px`; everything else `2px`.
  - SOFT (`border-radius: 10px`) → ambient chrome: Menu, Labs header bar, panels, non-primary
    `.mb-btn`.
  - Applied to R-Tessera via `.proj-actions .mb-btn`, `.link-pinpoint .mb-btn-primary`,
    `.labs-nav-btn` (4px), `.rt-hdr-link` (2px); to LunaV via `.mb-btn-primary` (2px). When syncing
    a NEW repo, square the `.mb-btn-primary` + any explicit priority/brand-link class; leave plain
    `.mb-btn` soft. NEVER recolor to square — only change `border-radius` (+ optional hairline
    border). Palette stays frozen (gold R-Tessera, teal LunaV).
- **Typography — Geist, unified (2026-08-13):** both repos use Geist (type + size).
  - LunaV already references Geist via CSS vars `var(--font-geist-sans)` / `var(--font-geist-mono)`
    in `layout.tsx` + `globals.css`; only the box change was needed there.
  - R-Tessera (Vite, NO token system, NO Tailwind) needed it installed + wired:
    `npm i @fontsource/geist-sans @fontsource/geist-mono`, then in `src/index.css` add the
    `@fontsource` imports + `--font-geist-sans/mono` vars + set `body { font-family: var(...) }`.
    Cesium entity labels (WeatherEntities/SituationalEntities JSX) use **Geist Mono** — note the
    quote trap: write the font attr as `'Geist Mono'` (single quotes), NOT `&quot;Geist Mono&quot;`
    (HTML-escaped double quotes break the Cesium label font at runtime).
- **PALETTE IS FROZEN ON SYNC PASSES.** When MARU says "sync X to both, but do NOT touch the color
  palette / don't recolor" — change ONLY typography + border-radius + borders. R-Tessera stays gold
  `#C9A96E`; LunaV stays teal `--mb-turquoise`. Do not let a "unify the buttons" task bleed into a
  recolor. If a stray cyan/blue leaked earlier (pre-2026-08-13 R-Tessera), recolor those to the
  repo's OWN accent — not the other repo's.
- **Layout:** one top header bar on all three. Each project keeps its OWN buttons
  (Edge keeps AI Learning / AI Detection — NOT Audit Report etc.). Settings pinned far-right
  (`ml-auto`); other buttons left-aligned with equal `gap-2`.
- **Subtitle:** project name under brand = grey `var(--txt-secondary)` (same grey as button text),
  baseline-aligned to button bottoms (`items-end` on the brand block).

## Pitfalls
- Claiming "verified" from a build exit code. Verify deployed/live FIRST.
- Forgetting the `kingkymaru@gmail.com` commit author → push succeeds, Vercel never redeploys.
- Editing Luna-EDGE HTML then not restarting Flask → no visible change.
- Over-applying LunaV's tab row (3D / Audit / Analytics / Docs) to R-Tessera or Edge — they have
  their OWN button sets. Sync the *style*, not the *contents*.
- **Build-failure masked by `&&` pipe chain.** Never write `npm run build 2>&1 | tail ... && git add && commit && push` — piping the build through `tail`/`head`/`grep` makes the pipe exit 0 even when the build FAILS, so the chain commits + pushes BROKEN code and the whole call's `exit_code` reads 0. Check the build's own exit (`> /tmp/b.log 2>&1; echo EXIT=$?`) and STOP on non-zero BEFORE committing. This bit the 2026-08-12 session: a React `Identifier already declared` PARSE_ERROR was committed + pushed because the `| tail` hid the failure; Vercel then failed to build. Always guard: `npm run build > /tmp/b.log 2>&1; if [ $? -ne 0 ]; then echo BUILD FAILED; tail -15 /tmp/b.log; exit 1; fi` before any commit.
- **React state-lift PARSE_ERROR ("Identifier already declared").** When lifting a `useState`
  flag from child → parent (e.g. top-bar button toggles a panel owned by a child), you MUST
  delete the child's own `const [x,setX]=useState(...)` — both the prop destructure and the
  leftover `useState` declare the same identifier and esbuild throws at build. Pattern: parent
  owns `const [drawerOpen,setDrawerOpen]=useState(false)`, passes them as props; child
  destructures from props, has NO local `useState` for them. Grep the child for the old
  `useState(...)` before building.
- **Panel toggle via header button, not edge tab.** MARU prefers a top-banner button to open/
  close a side panel — remove the floating edge-docked tab entirely. Banner button:
  `onClick={()=>setDrawerOpen(v=>!v)}` + `is-active` when open; child renders panel body only
  when `drawerOpen` is true.
- **Fixed overlay = guaranteed "top layer above map".** For chrome meant to sit ABOVE a
  full-screen canvas (bottom rail, side panel), prefer `position: fixed` over flex-static when
  MARU says "top layer / I can't see it" — flex-static gets clipped by `height:100dvh` +
  `overflow:hidden` ancestors. When you fix a bar to `bottom:0`, lift any
  `position:absolute; bottom:16px` siblings (remarks card, save indicator, base selector) to
  `bottom: ~52–60px` so they clear the bar.

## Verify before reporting done
- Vercel: `curl -s -o /dev/null -w "%{http_code}" https://lunavsolution.vercel.app` (expect 200)
  and `... https://r-tessera.vercel.app`.
- Local: `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000` (expect 200).
- Bonus: screenshot via browser_navigate + browser_vision; if vision 404s, the DOM snapshot still
  proves structure rendered.

## References
- `references/design-tokens.md` — exact CSS for glass header, `.mb-btn`, EDGE brand mark.
- `scripts/verify-theme-deploy.sh` — one-shot liveness + content-gate verifier (run AFTER push).

## One-shot live-verify (run AFTER push + ~45s wait, before saying "done")
Paste this in the terminal — it curls all three surfaces in one shot:
```bash
echo "LunaV:       $(curl -s -o /dev/null -w '%{http_code}' --max-time 12 https://lunavsolution.vercel.app)"
echo "R-Tessera:   $(curl -s -o /dev/null -w '%{http_code}' --max-time 12 https://r-tessera.vercel.app)"
echo "Luna-EDGE:   $(curl -s -o /dev/null -w '%{http_code}' --max-time 8 http://localhost:8000)"
```
All three should print `200`. A 200 proves the server is up + serving SOME build — it does
NOT prove the NEW code is live. If MARU still reports "no difference" after a 200, the deploy
didn't pick up the change: run the bundle-grep / alias check from
`vercel-prod-deploy-verification` (webhook miss or alias lag). Keep this script as the
first-pass liveness gate, not proof of content.

## Bottom-rail visibility pitfall (real this session — not a deploy miss)
A bottom rail/footer can be **in the deployed build yet invisible**. Two causes observed:
1. Parent `height:100dvh` + `overflow:hidden` (LunaV `<main className="ph-page">`) wrapping a flex
   column where the rail's sibling used `height:100%` → rail pushed *below viewport*. Fix: rail's
   sibling → `flex:1 1 auto; min-height:0` (fill remaining space), not `height:100%`.
2. To GUARANTEE "top layer above the map" (MARU's words): make the rail
   `position:fixed; left:0; right:0; bottom:0; z-40`. Sidesteps all flex/overflow quirks. Then lift
   any `position:absolute; bottom:16px` siblings (remarks card, save indicator) to `bottom:52px`
   so they clear the 36px rail instead of hiding under it.
If the markup is in the bundle but MARU says "still can't see it," assume clipping, not deploy.
Catch it with a browser DOM/computed-style check or screenshot — curl-200 only proves "in build."

