# Rebrand / logo swap on a Next.js (Supabase) app — field notes

Captured from a full rename of "SS Rover" -> "Digital Twin Inspection Reporting"
on the ss-rover-cloud app (Next + Supabase). One session, many small traps.

## Checklist (do all, in order)
1. **Replace every brand string** across `src/**` (ts/tsx/css):
   grep to find them first, including comments:
   `grep -rniE "ss[ _-]?rover|rover-r|rover sdn|ssrover" --include=*.ts --include=*.tsx --include=*.css src`
   - Visible text: landing `page.tsx`, `layout.tsx` (title + meta description),
     `dashboard/page.tsx` header, `ProjectWorkspace.tsx` header + footer,
     `share/[token]/page.tsx` (Access Denied copy), `Viewer3D.tsx` watermark/footer,
     `login/page.tsx` placeholder.
   - External `ssrover.com` links: repoint to app root (`/`) or make them plain
     brand text. A raw `<a href="https://www.ssrover.com">` triggers the
     `@next/next/no-html-link-for-pages` lint error -> use `<Link>` or a `<span>`.
   - Logo `alt` text often still says the OLD name (e.g. `alt="Rover-R logo"`) ->
     update to the new product name.
2. **Logo file**: copy the new PNG over `public/logo.png`
   (`cp /path/LUNA.png public/logo.png`). Keep it PNG (write_file can't do binary).
3. **Logo on dark UI** (the recurring "make the border small" loop):
   - If the source is a **transparent PNG** (check: `PIL Image.open(f).convert('RGBA').getpixel((2,2))[3]==0`),
     the logo can **float directly on the dark UI** — remove the light-plinth
     `<span>` wrapper entirely. This is what users actually want ("big logo, no border").
   - If the source is **white/opaque background** (common export), baking a light-grey
     `#f1f3f5` backdrop via PIL `Image.alpha_composite(bg, img)` makes it a grey square —
     which then looks like a box. Prefer re-exporting transparent, OR keep the plinth.
   - Keep the logo large on the landing page (e.g. `h-[112px]`) and smaller in headers.
4. **Verify no residual brand**: re-grep src after edits. Build + lint:
   `npm run build` (rolldown may warn on chunk size — cosmetic, exit 0 is fine).
   The `@next/next/no-html-link-for-pages` error is the one you'll introduce if you
   leave an `<a href="/">` — fix with `<Link>` or `<span>`.
5. **Don't push until visual OK** (user rule: push == go live). Offer local dev
   (`:3210`/`:3000`) or commit+push to Vercel for live check.

## Pitfalls
- The logo `alt` attr is easy to miss — it still says the old name and shows in
  a11y/title tooltips. Grep for it specifically.
- A "white rounded square" behind the logo = the **plinth** `<span>`, not the logo
  file. Remove the span to make the logo float; don't just shrink the logo.
- Transparent vs white-bg logo is the single biggest determinant of whether the
  result looks good on dark. Check alpha before deciding plinth-vs-float.
- Repo-level `package.json`/`.vercel/project.json` still say `ss-rover-cloud` —
  that's the *project slug*, not user-facing; leave it unless asked (renaming the
  Vercel project name is a separate dashboard action).
