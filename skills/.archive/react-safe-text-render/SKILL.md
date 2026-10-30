---
name: react-safe-text-render
description: >-
  Safely render user-entered plain text in React where bare URLs (YouTube
  links, etc.) must become clickable — WITHOUT dangerouslySetInnerHTML.
  Trigger on: "make links clickable", "linkify summary", "URLs not
  clickable in report", "user pasted a youtube link", "render text with
  links", "turn URLs into links in <user text>", or any place showing
  user-generated text as dead/unclickable strings.
category: frontend
---

# React safe text render (linkify without dangerouslySetInnerHTML)

Recurring need: a user types/pastes text (audit summary, finding remarks,
comments, bios) that contains a URL. Rendered as `{text}` it shows as literal
dead text — the viewer can SEE `https://youtu.be/abc` but cannot click it.

## The safe pattern

Split the string on a URL regex and map the parts to React nodes. Only the
matched URL substrings become `<a>`; everything else stays an escaped text
node (React escapes it — no XSS). NEVER use `dangerouslySetInnerHTML` to
inject user text.

```jsx
const URL_RE = /(https?:\/\/[^\s<>"'`]+)/gi;
function linkify(text: string): React.ReactNode {
  if (!text) return text;
  const parts = text.split(URL_RE);
  return parts.map((part, i) =>
    i % 2 === 1 ? (
      <a
        key={i}
        href={part}
        target="_blank"
        rel="noopener noreferrer"
        style={{ color: "var(--mb-turquoise)", textDecoration: "underline" }}
      >
        {part}
      </a>
    ) : (
      part
    )
  );
}
// usage: <div>{linkify(summary)}</div>   (NOT {summary})
```

Why this works: `String.split` with a CAPTURING group keeps the delimiters in
the result array at ODD indices; even indices are plain text. React renders
text nodes escaped, so pasted `<script>` / `<img onerror>` can't execute.

## Pitfalls
- **No `dangerouslySetInnerHTML`.** It's the obvious shortcut but injects raw
  user HTML → stored-XSS. The split/map approach is safer AND simpler.
- **Always `rel="noopener noreferrer"`** on `target="_blank"` links — without
  it, the opened page can reach `window.opener` (reverse tabnabbing).
- **Apply it to EVERY display surface, not just one.** In ss-rover-cloud the
  SAME `ProjectWorkspace` component feeds BOTH the inspector view and the
  client share view (the share page passes `readOnly` + data into it), so
  fixing `linkify` there covered both. But per-finding text lived in FOUR
  render spots (report-table title + description, defect-detail modal title +
  description); the editable `<textarea>`/`<input>` fields don't need it
  (they're form controls). Grep for every `{m.title}` / `{m.description}` /
  `{summary}` render and linkify each, or the client sees a clickable summary
  but dead links inside findings.
- **Keyed map.** Give the `<a>` a `key={i}` (index is stable here since the
  array is derived deterministically from the string) to avoid React key
  warnings.
- **Truncation/clamping still works.** If the parent uses `-webkit-line-clamp`
  on the linkified node, links inside the clamped region just truncate like
  normal text — no special handling needed.

## When to reach for this
- Any user-generated text that may contain links and is SHOWN (not edited).
- "Can the client click the YouTube link in the report?" → yes, after this.
- The client-safety rule (escape everything, linkify only URLs) is the same
  one to apply to ANY user text rendered as HTML elsewhere.

See `references/linkify-example.md` for the exact ss-rover-cloud diff and the
grep-the-render-spots checklist.
