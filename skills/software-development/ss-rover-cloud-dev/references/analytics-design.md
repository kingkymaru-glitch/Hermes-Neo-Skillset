# Dashboard & Analytics Design Patterns

## User's visual preference (correction from live session)
After the first analytics rewrite (stacky bar charts), the user said:
"yes its done but its ugly, make it more modern looking, slim, and for the time
series, make it line graph or something better looking. by better i mean something
that looks exclusive and expensive."

**Durable expression of that preference — compact component scale.** The same
user later asked for *every* button in the app to be shrunk to match the compact
drawer tab strip, and warned against "extended gaps between buttons, or
overlapping buttons". Slim is the standing default ask for this product; do not
propose chunky controls. The resulting tier table, the "buttons sit inside the
label band" rule, and the geometry verification recipe live in the
current-codebase skill: `lunav-studio` → `references/ui-button-scale.md`.

## Rules
1. **No chunky div-bar charts.** Use SVG-based visualizations for time-series data.
2. **Line graphs > bar charts** for temporal data. Three overlapping lines
   (PASS/WARNING/FAIL), gradient fills beneath each line, dot markers with hover
   tooltips. Use `<svg viewBox="...">` with inline JSX — no chart library needed.
3. **Model breakdown bars:** ultra-slim 4px rounded pill bars (not 24px blocks).
   No inline number labels inside bars — counts go outside. Use CSS class with
   `border-radius:6px` and `transition:width 0.5s cubic-bezier(0.3,0,0.2,1)`.
4. **Severity summary:** single horizontal strip with colored dot + label + bold
   number + percentage per severity. NOT three chunky cards. Use a border-wrapper
   `overflow-hidden rounded-xl` with equal-width flex children.
5. **Commentary block:** subtle inset card (`background: var(--dash-inset)`,
   `border: 1px solid var(--hairline)`) instead of bright amber left-border.
6. **Typography:** section labels in `text-[0.6rem] font-bold tracking-[0.2em]
   uppercase` (all-caps, wide tracking). Headers stay `text-2xl font-bold`.
7. **Max width:** `max-w-4xl` for analytics (was `max-w-5xl`). Tighten don't spread.
8. **Spacing:** `mb-10` between major sections, `rounded-xl` on all panels,
   `overflow-hidden` on panels that contain bars/strips.

## SVG line chart recipe
```tsx
const PAD = { top: 24, right: 24, bottom: 36, left: 32 };
const W = 720, H = 280;
const graphW = W - PAD.left - PAD.right;
const graphH = H - PAD.top - PAD.bottom;
const maxY = Math.max(...dailyDefects.map(d => d.total), 1);
const stepX = dailyDefects.length > 1 ? graphW / (dailyDefects.length - 1) : graphW;

// Compute point arrays for each severity
const points = (severity: "pass" | "warning" | "fail") =>
  dailyDefects.map((d, i) => ({
    x: PAD.left + i * stepX,
    y: PAD.top + graphH - (d[severity] / maxY) * graphH,
    val: d[severity],
  }));

// In SVG:
// - Grid lines: dashed stroke at y-tick positions
// - Areas: <path d={area(pts)} fill="url(#gPass)"/> etc.
// - Lines: <path d={polyline(pts)} fill="none" stroke={color} strokeWidth="2" .../>
// - Dots: <circle cx={p.x} cy={p.y} r="3" fill={color} className="analytics-dot">
//           <title>PASS: {p.val}</title></circle>
```

Gradient defs use `stopOpacity` 0.25 at top fading to 0.02 at bottom.
Grid uses `stroke-dasharray:4 3` at `stroke-width:0.5` in `var(--hairline)`.

## Model pill bar recipe
```css
.model-bar-track { background:var(--dash-inset); border-radius:6px; height:4px; overflow:hidden; }
.model-bar-fill { height:100%; border-radius:6px; transition:width 0.5s cubic-bezier(0.3,0,0.2,1); }
```

```tsx
<div className="model-bar-track">
  {m.fail > 0 && <span className="model-bar-fill inline-block"
    style={{ width: `${(m.fail/max)*100}%`, background: "var(--mb-red)" }} />}
  {/* same for warning (amber) and pass (turquoise) */}
</div>
```

No text inside the bar. Counts go in a separate row below as `text-[0.62rem] font-medium`.

## Severity strip recipe
```tsx
<div className="mb-10 flex gap-0 overflow-hidden rounded-xl border"
  style={{ borderColor: "var(--hairline)" }}>
  {(["PASS","WARNING","FAIL"] as const).map((s) => {
    const c = s === "PASS" ? "var(--mb-turquoise)" :
              s === "WARNING" ? "var(--mb-amber)" : "var(--mb-red)";
    const n = counts[s];
    const pct = allMarkers.length > 0 ? Math.round((n / allMarkers.length) * 100) : 0;
    return (
      <div key={s} className="flex flex-1 items-center justify-between px-5 py-3"
        style={{ background: "var(--dash-panel)" }}>
        <div className="flex items-center gap-3">
          <span className="inline-block h-2 w-2 rounded-full" style={{ background: c }} />
          <span className="text-[0.65rem] font-bold tracking-[0.15em] uppercase"
            style={{ color: "var(--txt-tertiary)" }}>{s}</span>
        </div>
        <div className="text-right">
          <span className="text-xl font-extrabold tracking-tight" style={{ color: c }}>{n}</span>
          <span className="ml-1.5 text-[0.6rem]" style={{ color: "var(--txt-tertiary)" }}>{pct}%</span>
        </div>
      </div>
    );
  })}
</div>
```