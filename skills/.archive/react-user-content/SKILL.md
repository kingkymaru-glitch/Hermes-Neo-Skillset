---
name: react-user-content
description: >-
  Safely rendering user-supplied content in React — plain text that may
  contain URLs, and the decision of when/whether to inline-embed media
  (YouTube iframes). Trigger on: "make links clickable in this text",
  "linkify", "auto-link URLs", "user pasted a youtube link", "render
  user text as HTML", "dangerouslySetInnerHTML", "embed youtube/video in
  a table", "why did my table layout break", "Tailwind color class not
  applying", or any field where an end-user types free text that later
  displays (comments, summaries, findings, remarks, chat).
category: frontend
---

# React User-Content Rendering (linkify + safe embeds)

Class-level playbook for the recurring problem: a user types free text
(URLs, notes) that you must display, and you want links clickable and
media playable WITHOUT XSS, WITHOUT breaking layout, and WITHOUT leaking
the project's theming convention.

## Pattern 1 — Linkify with React nodes (NEVER dangerouslySetInnerHTML)

When a field stores a plain string (e.g. an executive summary, a finding
"remarks" column, a comment) and you want bare `http(s)://…` URLs to
become clickable, split on a URL regex and wrap ONLY the matched parts in
`<a>`. Return an array of React nodes. The non-URL text is rendered as a
plain string child, so React escapes it — no injection surface.

```jsx
const URL_RE = /(https?:\/\/[^\s<>"'`]+)/gi;
function linkify(text: string): React.ReactNode {
  if (!text) return text;
  const parts = text.split(URL_RE);
  return parts.map((part, i) => {
    if (i % 2 === 1) {                       // odd indices = the captured URLs
      const href = part;
      return (
        <a
          key={i}
          href={href}
          target="_blank"
          rel="noopener noreferrer"            // opens new tab, blocks reverse-tabnabbing
          style={{ color: "var(--mb-turquoise)", textDecoration: "underline" }}
        >
          {href}
        </a>
      );
    }
    return part;                              // escaped plain text — safe
  });
}
// usage:  {linkify(summary)}   instead of   {summary}
```

**Why not `dangerouslySetInnerHTML`?** It parses the whole string as HTML;
any `<script>`/attribute the user typed executes. The node-split approach
keeps all non-URL text as escaped React children. This is the single most
important rule here.

Covers youtube.com / youtu.be / any http(s) host automatically. Works in
BOTH an editable-component's display mode and its read-only "client portal"
mode if the same component is reused for both (see Pitfall 4).

## Pattern 2 — Embed-media decision (table vs modal)

A naive inline `<iframe>` YouTube embed is fine in a free-flowing container
but DESTROYS a table layout. Decide by container:

- **READ-ONLY SCROLL-CAPPED MODAL** (e.g. `maxHeight: 85vh; overflow-y:
  auto`): safe to embed. The video adds scrollable height; nothing around
  it moves. Prefer a click-to-expand thumbnail so you don't load N iframes
  at once.
- **TABLE CELL with `-webkit-line-clamp`**: DO NOT embed. The 3-line clamp
  rule applies to TEXT only. An iframe is a fixed 16:9 box (~56% as tall as
  wide); dropping it into the cell ignores the clamp, the row grows to the
  video's full height, and the whole table reflows (column widths jump,
  every row sizes to its tallest cell). Keep the table as **clickable
  links** (Pattern 1); let the link open the video in a new tab, or open it
  in the detail modal.

Detect YouTube specifically and use the privacy/lightweight form
`https://www.youtube-nocookie.com/embed/<ID>` if you do embed.

## Pattern 3 — Theming via CSS custom properties, not Tailwind tokens

Some projects theme with CSS variables (e.g. `var(--mb-turquoise)`,
`var(--hairline)`, `var(--txt-secondary)`) and do NOT define Tailwind color
tokens named after them. Writing `className="bg-turquoise/10"` or
`border-turquoise/40` produces NO valid utility class — it silently does
nothing (no compile error, just missing style). Use inline style instead:

```jsx
// WRONG (no such Tailwind token):
<div className="bg-turquoise/10 border-turquoise/40" />
// RIGHT (matches the project's CSS-var theme):
<div style={{ background: "rgba(0,229,195,.1)", border: "1px solid rgba(0,229,195,.4)" }} />
// or for text color:
<p style={{ color: "var(--mb-turquoise)" }} />
```

Before inventing a class, grep the project for the variable name to learn
the exact token (e.g. `search_files` for `mb-turquoise`). When in doubt,
inline `style` with the existing `var(--…)` is always safe.

## Pitfalls

- **P1 — `dangerouslySetInnerHTML` on user text = XSS.** Always prefer the
  node-split `linkify()`. Only reach for sanitized HTML (e.g. `DOMPurify`)
  if you must render rich formatting, and never from a raw user string.
- **P2 — Inline iframe in a line-clamped table breaks layout.** The clamp
  is text-only; the video inflates its row and reflows the table. Keep
  tables = links; embed only in a scroll-capped modal. See
  `references/linkify-and-embeds.md` for the exact failure mode.
- **P3 — Missing `rel="noopener noreferrer"` on `target="_blank"`.** Without
  it, the opened page can `window.opener` the parent (reverse tabnabbing).
  Always pair `target="_blank"` with `rel="noopener noreferrer"`.
- **P4 — Fix display rendering once, apply to both modes.** If a component
  has an inspector (edit) mode AND a read-only client-portal mode driven by
  the same component (e.g. a `readOnly` prop), render the user text through
  ONE shared display path. Then a `linkify()` change automatically reaches
  both the inspector's view AND the client's shared link — no second edit.
- **P5 — Tailwind color utility with a non-existent token is a silent no-op.**
  When a project themes via CSS vars, use inline `style={{ color:
  "var(--token)" }}`; don't assume a `bg-<name>` / `text-<name>` class exists.

## Verification
- Render a sample containing a YouTube URL + plain text; confirm the URL is
  an `<a>` (inspect element), plain text is NOT wrapped in tags, and
  clicking opens a new tab.
- For a table: paste a URL in a cell, confirm the row height stays clamped
  (no iframe). For a modal: confirm the embed appears and the modal scrolls.
- `npm run build` / type-check passes (the `linkify` helper returns
  `React.ReactNode`).

## Support files (this skill)
- `references/linkify-and-embeds.md` — the full `linkify()` helper, the
  table-vs-modal embed decision with the exact `-webkit-line-clamp` failure
  mode, and the CSS-var theming fix, with the LUNAV/ss-rover-cloud
  (2026-07-29) case as the worked example.
