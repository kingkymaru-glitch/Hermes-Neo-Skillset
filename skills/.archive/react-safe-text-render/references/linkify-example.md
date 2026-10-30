# linkify example — ss-rover-cloud (LUNAV) 2026-07-29

## The ask
Inspector pastes a YouTube link into the Audit Report's Executive Summary.
Client opens the shared report and must be able to CLICK it. Before the fix,
summary was rendered as `{summary}` → dead text (React renders a raw string
child as plain text; it does NOT auto-linkify).

## The helper (added once, near top of ProjectWorkspace.tsx)
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
    return part;
  });
}
```

## Render spots changed (all in ProjectWorkspace.tsx)
- Executive summary: `{summary}` → `{linkify(summary)}`  (line ~1492)
- Report table finding title: `{m.title}` → `{linkify(m.title)}`
- Report table finding description: `{m.description || "—"}` →
  `{m.description ? linkify(m.description) : "—"}`
- Defect-detail modal title: `{detailMarker.title}` → `{linkify(detailMarker.title)}`
- Defect-detail modal description: `{detailMarker.description}` →
  `{linkify(detailMarker.description)}`

The editable drawer `<input>`/`<textarea>` fields were left alone (form
controls — the user is typing there, not reading a link).

## Why one component fixed both views
The client share page (`app/share/[token]/page.tsx`) renders the SAME
`ProjectWorkspace` component with `readOnly={true}` and passes the project's
`executive_summary` / markers in. So linkifying inside `ProjectWorkspace`
covered inspector + client in one change.

## Checklist for any similar component
1. Add the `linkify` helper once (module scope).
2. Grep `{...}` renders of the user-text fields (title, description, summary,
   remarks, note, comment).
3. Replace each display render with `linkify(...)`. Skip `<input>`/`<textarea>`.
4. `npm run build` green, then push (Vercel auto-deploys).
