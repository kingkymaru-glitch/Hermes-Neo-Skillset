# White-label theming — reusable wiring (ss-rover-cloud Phase 5, 2026-07-28)

Condensed pattern for a Supabase-backed app where an INSPECTOR (seller) configures
a CLIENT portal to look like the client's company. LunaV stays off-screen except
footer line + watermark.

## Data model (Supabase `projects`)
```sql
brand_company_name text,
brand_logo_url     text,
brand_theme        text not null default 'dark'
                    check (brand_theme in ('dark','light','midnight')),
brand_accent       text
```
RPC `update_project_branding(p_project_id, p_company_name, p_logo_url, p_theme, p_accent)`
writes ALL four fields LITERALLY (no COALESCE) — `null` clears. Caller always sends
the full state (see P29 in supabase-backend). `get_shared_project` RPC returns these
columns inside the `project` jsonb so the client portal can read them anon.

## Client state (React)
```ts
const [branding, setBranding] = useState<{
  companyName: string | null; logoUrl: string | null;
  theme: "dark"|"light"|"midnight"; accent: string | null;
}>(initial.branding ?? { companyName:null, logoUrl:null, theme:"dark", accent:null });

// theme + accent applied live
useEffect(() => {
  const root = document.documentElement;
  root.setAttribute("data-theme", branding.theme);
  if (branding.accent) {
    root.style.setProperty("--mb-turquoise", branding.accent);
    root.style.setProperty("--mb-turquoise-dim", hexToRgba(branding.accent, 0.14));
    root.style.setProperty("--glow-turquoise", `0 0 18px ${hexToRgba(branding.accent,0.35)}`);
  } else {
    root.style.removeProperty("--mb-turquoise");
    root.style.removeProperty("--mb-turquoise-dim");
    root.style.removeProperty("--glow-turquoise");
  }
}, [branding.theme, branding.accent]);
```

## Theme CSS (globals.css)
```css
:root { --dash-void:#14171c; --dash-panel:#1b1f26; --txt-primary:#e8eef4;
        --mb-turquoise:#2f9bff; /* ...rest of dark defaults */ }
html[data-theme="light"] { --dash-void:#eef1f5; --dash-panel:#fff; --txt-primary:#16202c;
        --mb-turquoise:#1f7fe0; /* light overrides */ }
html[data-theme="midnight"] { --dash-void:#070a0f; --dash-panel:#0c1016; --txt-primary:#cfe0f0;
        --mb-turquoise:#38a8ff; /* near-black overrides */ }
```
Every surface uses `var(--...)` — one `data-theme` switch re-skins everything.

## Auto accent from logo (canvas average)
```ts
function averageColorFromImage(url: string): Promise<string | null> {
  return new Promise((resolve) => {
    const img = new Image(); img.crossOrigin = "anonymous";
    img.onload = () => {
      try {
        const c = document.createElement("canvas");
        const w = c.width = Math.min(img.width,64), h = c.height = Math.min(img.height,64);
        const ctx = c.getContext("2d")!; ctx.drawImage(img,0,0,w,h);
        const d = ctx.getImageData(0,0,w,h).data;
        let r=0,g=0,b=0,n=0;
        for (let i=0;i<d.length;i+=4){ if(d[i+3]<128) continue; r+=d[i];g+=d[i+1];b+=d[i+2];n++; }
        resolve(n ? rgbToHex(Math.round(r/n),Math.round(g/n),Math.round(b/n)) : null);
      } catch { resolve(null); }   // CORS-tainted canvas -> manual fallback
    };
    img.onerror = () => resolve(null); img.src = url;
  });
}
```

## Client-portal gating
- Read-only mode: filter tabs to drop the builder (`t !== "studio"`), land on `report`.
- Header: `branding.logoUrl ? <img.../> : <img src="/logo.png"/>` and
  `{branding.companyName || "LunaV Studio"}`.
- Footer: `LUNAV STUDIO — ROVER-R` line + `{branding.companyName && (c) name}`.
- Watermark over the 3D canvas: clickable `<a href="https://www.lunavsolution.vercel.app"
  target="_blank" rel="noreferrer">www.lunavsolution.vercel.app</a>` (was "Powered by LunaV Studio").

## Save discipline (why full-state, not patch)
RPC written as `set col = coalesce(p_col, col)` makes "Remove logo" (passes null)
keep the old URL. Fix: literal writes + caller sends `next = {...branding, ...patch}`
on every save. Do NOT pass only the changed field. (supabase-backend P29.)
