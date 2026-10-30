---
name: shadcn-tailwind-scaffold
description: Fix shadcn UI init traps (colors, names, version stamp).
---

# shadcn/ui + Tailwind scaffold pitfalls

Standing procedure when standing up a shadcn/ui app (this founder builds many Next/Vite
frontends — the same init traps recur on every fresh project):

## Procedure
1. create-next-app rejects an UPPERCASE package/repo name (`Could not create a project
   called "X" because of npm naming restrictions`). Do not fight it: scaffold into a
   lowercase temp dir, then move contents into the uppercase repo dir:
   `create-next-app <lowercase-tmp> ...` then `shopt -s dotglob; mv <tmp>/* .` and
   `rmdir <tmp>`. Fix the package.json `name` field back to the intended name.
2. Init shadcn with the version compatible with your Tailwind major. For Next 14 +
   Tailwind v3, pin the CLI: `npx shadcn@2.3.0 init -d -y`. Older/newer `shadcn` majors
   may target Tailwind v4 and produce an incompatible config.
3. `shadcn add <button card sheet tabs switch badge ...>` for the components you need
   (slider is NOT included by default — add it explicitly when a milestone needs it).

## The silent color killer: oklch() tokens vs hsl() config (MUST fix every init)
shadcn 2.x writes CSS custom properties in `oklch(...)` in `globals.css`, but the
generated `tailwind.config.ts` still maps colors as `hsl(var(--background))` etc. That
wraps an `oklch()` value in an `hsl()` function = INVALID CSS → every color silently
fails (backgrounds/foregrounds resolve to nothing/black). `next build` passes; only the
rendered page looks broken, so it reads as a CSS/design bug, not a config bug.

Fix: rewrite the tailwind config color map to reference the var directly —
`background: "var(--background)"`, not `hsl(var(--background))` — across all of
background/foreground/card/popover/primary/secondary/muted/accent/destructive/border/
input/ring/chart/sidebar. Also add the missing `--destructive-foreground` token to BOTH
`:root` and `.dark` in globals.css if absent (shadcn omits it; destructive buttons then
reference an undefined var).

## Verification after any scaffold
- Confirm `npx tsc --noEmit` is clean.
- `npm run build` clean is the real gate — the eslint `no-explicit-any` rule runs during
  build and is a HARD failure even when tsc passes (relevant when a client-heavy lib like
  Cesium forces untyped `any`).
- Hard proof a scaffold is visually intact needs a browser (this founder runs one; do not
  headless-launch on his machine). To diagnose "colors wrong/blank" structurally, inspect
  the built config: confirm no `hsl(var(` remains where an oklch value lives.

## Version-stamp preference (this founder, all shipped webapps)
Every shipped webapp must carry a visible version stamp in the header, fed from a single
source constant (e.g. `lib/app-version.ts` `APP_VERSION = "V0.xx"`), NOT a hardcoded
string in the page. Bump the constant on every release so localhost/deployed reflects the
milestone tag the user quotes. A stale hardcoded stamp reads as a versioning failure.
