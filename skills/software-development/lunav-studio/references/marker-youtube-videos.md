# Marker YouTube Video Links (shipped 2026-08-17, commit 4dc7070)

Owner adds YouTube video links per marker (3D Defect Detail drawer); client/share
view shows them read-only. This is the reference for the implementation.

## Storage — JSONB array column on `markers` (NOT a new table)
```sql
alter table public.markers
  add column if not exists videos_json jsonb not null default '[]'::jsonb;
```
Model: `videos_json: { title: string; url: string }[]`. Mirrors the existing
`photos_json` pattern (array column on the marker row). Why this over a
`marker_videos` table:
- **Fastest:** markers are already loaded with the project; videos ride in the
  same payload. No extra fetch, no N+1, no join.
- **Robust:** same RLS scoping as photos (owner edits, anon reads via `?share=`).
- **Safe:** no new table, no migration ordering concerns.

## CRITICAL — YouTube embed must be an HTML overlay, NOT a 3D texture
A video "on the model surface" (THREE.CanvasTexture on a plane billboard at the
node) only works with a **direct .mp4 file URL** (uploaded to R2). It does NOT
work with YouTube: the browser **taints the canvas on readback** from YouTube's
CDN, so `toDataURL`/`getImageData` returns blank/black. There is no clean
workaround for YouTube specifically. Therefore YouTube links MUST render as an
`<iframe src="https://www.youtube.com/embed/<id>?rel=0">` overlay in the DOM.

Memory/crash safety: an iframe is HTML overlay, NOT a 3D scene object. It does
not touch WebGL or the .glb, so it can't bloat the model or trigger geometry
re-renders. YouTube streams in buffered chunks (doesn't load the whole file).
Closing the drawer unmounts the iframes → frees memory. Realistic limit is a
few simultaneously-playing embeds; only autoplay the first 1–2 (rest show
thumbnails on click) to keep memory flat.

## YouTube URL validator + embed converter (`src/lib/youtube.ts`)
Accept watch / shorts / youtu.be / embed forms only; reject everything else.
```ts
export function youtubeVideoId(url: string): string | null {
  // youtu.be/<id> | youtube.com/embed/<id> | /shorts/<id> | /watch?v=<id>
  // must also validate host is youtube.com
}
export function youtubeEmbedUrl(url: string): string | null {
  return youtubeVideoId(url) ? `https://www.youtube.com/embed/${id}?rel=0` : null;
}
```
Always validate before storing and convert to the embed form at render time
(`youtubeEmbedUrl(v.url)`), so a stored bad link just renders nothing instead
of an XSS-able raw `src`.

## Placement in the Defect Detail drawer (`ProjectWorkspace.tsx`)
Insert the video section **between the Findings & Remarks textarea and the
Photo Proof block** in the `activeMarker` drawer (owner) AND in the `detailMarker`
modal (client/share read-only). Two spots, same relative position:
- Owner: `activeMarker.videos_json` — list with ✕ Remove per video + an
  "Add a YouTube video" form (title input + url input + validate + add).
- Client: `detailMarker.videos_json` — read-only list (embeds only, no controls).
Guarded by `readOnly` so the add form only renders for the owner.

## saveMarker persistence
`safeMarker(patch)` already does a generic `supabase.from("markers").update(patch)`
by id, so any new column persists via `saveMarker({ videos_json: next })`. No
special-casing needed. Ensure the marker INSERT default includes `videos_json: []`
so new markers have the field.

## Iframes — props used
```tsx
<iframe
  className="h-full w-full"
  src={embed}
  title={v.title || "Video"}
  loading="lazy"
  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
  referrerPolicy="strict-origin-when-cross-origin"
  allowFullScreen
/>
```
Wrap in `<div className="aspect-video w-full bg-black">` for a proper 16:9 box.
