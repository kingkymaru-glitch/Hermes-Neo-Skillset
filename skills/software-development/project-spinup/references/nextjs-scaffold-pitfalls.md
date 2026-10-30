# Next.js 14 App Router + Tailwind + shadcn/ui scaffold pitfalls

Verified while standing up a fresh dark-mode Next.js 14 project from `create-next-app`
followed by `shadcn init` + `add`. These bite regardless of who the project is for.

## create-next-app rejects an UPPERCASE repo/project name
`npx create-next-app@14 .` in a dir whose name has a capital (e.g. `CDM`) fails with
`name can no longer contain capital letters`. Workaround — scaffold into a lowercase
temp dir inside the repo, then move the contents up:

```bash
cd <repo> && npx --yes create-next-app@14 <lowercase-tmp> --typescript --tailwind \
  --eslint --app --no-src-dir --import-alias "@/*" --use-npm --yes
shopt -s dotglob && mv <lowercase-tmp>/* . && rmdir <lowercase-tmp>
```
Then fix `package.json` `name` from the temp dir name to the real (lowercase) name.
Note create-next-app scaffolds the SAME project with `tailwindcss@^3` + `next@14`;
react 18; no `geist` npm package — use the vendored `next/font/local` fonts in
`app/fonts/` as scaffolded, do NOT `import { GeistSans } from "geist/font/sans"`
(no such module is installed → tsc 2307).

## shadcn 2.x `init` writes oklch() tokens but leaves hsl() tailwind wrappers
Modern `npx shadcn init` writes `oklch(...)` values into `globals.css` `:root`/`.dark`,
but the generated `tailwind.config.ts` still maps every color through
`hsl(var(--background))`. Wrapping an `oklch()` string in `hsl()` is invalid CSS and
kills ALL themed colors (blank/black UI). Fix after init: rewrite the color block in
`tailwind.config.ts` to reference the CSS variable directly, e.g.
`background: "var(--background)"` — no `hsl()`/`oklch()` wrapper.

## shadcn 2.x `globals.css` omits `--destructive-foreground`
The generated tokens define `--destructive` but NOT `--destructive-foreground` in either
theme, so the `destructive` Tailwind utility has no foreground and any destructive
button renders broken. Add `--destructive-foreground` to BOTH `:root` and `.dark`.

## shadcn 2.x init flags
`shadcn@2.3.0 init -d -y` (defaults). There is NO `-b <base>` color option on this CLI
version — `-b` errors as `unknown option`. `-d`/`-y` are the non-interactive flags.
Then `npx shadcn add <components...>` pulls the base set. Base color choice (slate/zinc)
is a registry/config concern, not an init CLI flag at this version.

## Verify a static Next shell compiles AND contains the panels
- `npx tsc --noEmit` (must exit 0).
- `npm run build` — for a static route you get `○ /` prerendered; confirm build exits 0.
- Prove the SSR markup really carries your panels (catches a build that silently drops
a component): `grep` the prerendered HTML for each expected heading/label string in
`.next/server/app/index.html`. Static routes render that file; a `"use client"`
component's shell markup still appears there because Next pre-renders it.
- `h-4.5`/`w-4.5` are not valid Tailwind spacing classes — use `h-4 w-4` (or a real value).
