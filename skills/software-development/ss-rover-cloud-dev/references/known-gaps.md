# LunaV — Known UI gaps / pending features

## Executive Summary: pasted URLs are not clickable
The Audit Findings Report → Executive Summary is edited in a textarea and stored as a
plain string (`projects.executive_summary`). It is rendered in BOTH places as a raw
React child, so any URL (YouTube, etc.) shows as dead text:

- Inspector Report tab: `src/components/ProjectWorkspace.tsx` (~lines 1487-1494):
  ```tsx
  {summary.trim() && (
    <div className="dash-panel mb-8 p-6 ..." style={{...}}>
      {summary}        {/* raw string → plain text, NOT an <a> */}
    </div>
  )}
  ```
- Client shared view: `src/app/share/[token]/page.tsx` passes the same
  `executive_summary` into `ProjectWorkspace` with `readOnly`. Same dead-text render.

So today a client CANNOT click a YouTube link the inspector pasted. The inspector also
can't (it's non-interactive text). Answer given to user 2026-07-29: NO, not clickable.

### Recommended fix (linkify only)
Split on `https?://[^\s]+`, wrap each match in
`<a href={url} target="_blank" rel="noreferrer">`, render the rest as text. Build an
array of React nodes (text + `<a>`) — because the field is a plain string, this is the
safe path. NEVER use `dangerouslySetInnerHTML` (XSS risk from stored user text). One fix
covers inspector + client since both render the same `summary`/`executiveSummary` value.

### Option B (heavier)
Upgrade the field to a small rich-text editor, or render YouTube URLs as inline
`<iframe>` embeds. More work, risks the stored-string model. Only if the client wants
to watch in-place.
