# Linkify user text + safe media embeds (worked example)

Case: LUNAV / ss-rover-cloud (Next.js + Supabase + Vercel), 2026-07-29.
An inspector pastes a YouTube link into (a) the Audit Report executive
summary, and (b) per-finding "remarks". The client views these via a
read-only share link. Requirement: client can CLICK the link and open it.

## The `linkify()` helper (single source of truth)

Added once in `ProjectWorkspace.tsx`. Used in BOTH the inspector report
and the client-portal component, because the share page renders the SAME
component with `readOnly: true` — one fix covers both modes.

```jsx
const URL_RE = /(https?:\/\/[^\s<>"'`]+)/gi;
function linkify(text: string): React.ReactNode {
  if (!text) return text;
  const parts = text.split(URL_RE);
  return parts.map((part, i) => {
    if (i % 2 === 1) {
      return (
        <a key={i} href={part} target="_blank" rel="noopener noreferrer"
           style={{ color: "var(--mb-turquoise)", textDecoration: "underline" }}>
          {part}
        </a>
      );
    }
    return part; // escaped plain text — no XSS
  });
}
```

Applied at the four display spots:
- executive summary: `{linkify(summary)}`
- report table finding title: `{linkify(m.title)}`
- report table finding description/remarks: `{m.description ? linkify(m.description) : "—"}`
- Defect Detail popup title + description: `linkify(detailMarker.title)` / `linkify(detailMarker.description)`

(The editable `<textarea>`/`<input>` fields deliberately do NOT linkify —
those are form controls the inspector types into.)

## The table-vs-modal embed decision (DEFERRED in this case)

Founder asked: "if you put an inline embedded video, will it push everything
around it to haywire?" Answer: in the report TABLE, YES.

Mechanism:
- The report table clamps finding text with `-webkit-line-clamp: 3`
  (plus `WebkitBoxOrient: vertical; overflow: hidden`). That rule ONLY works
  on TEXT. A `<iframe>` is a fixed 16:9 box; inside the cell it ignores the
  clamp and the row grows to the video's full height. Table rows size to
  their tallest cell, so one video row inflates that row and reflows the
  columns. "Haywire" = confirmed.
- The Defect Detail popup is `maxHeight: 85vh; overflow-y: auto` (scrolls
  inside), so an embed there only adds scrollable height — nothing around it
  moves. That is the ONLY embed-safe spot.

Decision taken: keep the TABLE as clickable links (Pattern 1), and only the
Defect Detail modal would be embed-safe. Left as links for now — founder
opted out of in-place video. If you later add embed:
- table: keep as link (open in new tab). DO NOT iframe.
- modal: click-to-expand thumbnail → `https://www.youtube-nocookie.com/embed/<ID>`
  (lazy: swap on click so you don't load N iframes at once).

## Theming pitfall (Tailwind token vs CSS var)

The LUNAV project themes with CSS variables, NOT Tailwind color tokens.
`bg-turquoise/10` / `border-turquoise/40` are NOT valid utilities → silent
no-op (no build error, style just missing). Fixed by using inline styles
with the existing vars:

```jsx
// confirmation block — correct form for this project
<p style={{ color: "var(--mb-turquoise)", border: "1px solid rgba(0,229,195,.4)",
            background: "rgba(0,229,195,.1)" }}
   className="rounded-xl px-3 py-2 text-xs font-semibold">
  {linkify(summary)}
</p>
```

Always grep the project for the variable (e.g. `mb-turquoise`) to learn the
exact token before styling user-content surfaces.

## Verification performed
- `npm run build` green (Next.js, TypeScript passed).
- Pushed `main` → Vercel auto-deployed; links clickable in both inspector
  and client-portal views.
