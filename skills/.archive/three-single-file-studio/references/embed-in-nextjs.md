# Embedding the single-file Three.js studio inside the `ss-rover-cloud` Next.js 16 app

## 1. Place the file in public/
```bash
mkdir -p public/studio
cp /path/to/lunav_studio_safe.html public/studio/lunav_studio_safe.html
# Confirm it has no backend wiring before shipping:
grep -ci "supabase\|r2-upload\|uploadToR2" public/studio/lunav_studio_safe.html   # -> 0
```
Served at `/studio/lunav_studio_safe.html`. Never import it as a module.

## 2. Add the tab (THREE coordinated edits in the workspace component)
The studio lives inside `ProjectWorkspace.tsx`. All three must change together:

**(a) Tab type union**
```ts
type Tab = "3d" | "report" | "analytics" | "docs" | "studio";
```

**(b) Nav tab bar** — add entry right after "3D Digital Twin":
```tsx
{(
  [
    ["3d", "3D Digital Twin"],
    ["studio", "LunaV Studio"],
    ["report", "Audit Report"],
    ["analytics", "Analytics"],
    ["docs", "Documents"],
  ] as [Tab, string][]
).map(([t, label]) => (
  <button key={t} onClick={() => setTab(t)}
    className={`mb-btn ${tab === t ? "mb-btn-primary" : ""}`}>{label}</button>
))}
```

**(c) Stage panel** — place near the other tab stages:
```tsx
{/* ---- LUNAV STUDIO TAB ---- */}
<div className={tab === "studio" ? "absolute inset-0 z-10" : "hidden"}>
  <iframe
    src="/studio/lunav_studio_safe.html"
    title="LunaV Studio — 3D Model Builder"
    className="h-full w-full border-0 bg-[#0b0e12]"
  />
</div>
```

## 3. Verify
- `npm run build` → green (Next 16 uses Turbopack; TS check catches missing union members).
- Missing (b) or (c) → tab renders but shows nothing, or tab button does nothing. Missing (a) → TS error (exhaustiveness).
- Click the studio tab, confirm the iframe loads (needs network for `cdn.tailwindcss.com` + `unpkg`).

## 4. Host-page collapse gotcha (separate from the studio)
The 3D Digital Twin page's left "Project Models" console had a broken collapse:
the collapsed class used `sm:w-80` (re-expanded at ≥640px) and the toggle was `sm:hidden`.
Fix: collapsed state keeps `w-10` at all breakpoints; toggle is NOT `sm:hidden`.
