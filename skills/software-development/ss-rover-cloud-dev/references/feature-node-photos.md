# Feature pattern: per-node evidence photos (Phase 4)

Used in the 3D Digital Twin inspection app for "attach photos to a defect/node".

## Requirement shape
- Node detail tab: upload **max 3 photos**, **200KB each**.
- Gallery render in both the right-side 3D drawer AND the Defect Detail modal.
- Per-photo remove.

## Data model change
`markers` gained `photos_json jsonb not null default '[]'::jsonb` (array of up to 3
public URLs). The legacy single `image_url` column is kept for backward compat and
migrated into `photos_json[0]` on apply.

Migration (idempotent, pushed via `supabase db push --linked`):
```sql
alter table public.markers
  add column if not exists photos_json jsonb not null default '[]'::jsonb;

update public.markers
  set photos_json = jsonb_build_array(image_url)
  where image_url is not null
    and (photos_json is null or jsonb_array_length(photos_json) = 0);
```

## Client code (src/components/ProjectWorkspace.tsx)
- Replace single `attachPhoto(file)` with `attachPhotos(files: FileList | File[])`.
- Enforce in-app BEFORE upload:
  ```ts
  const MAX_PHOTOS = 3;
  const MAX_BYTES = 200 * 1024;            // 200KB
  const existing = activeMarker.photos_json ?? [];
  let remaining = MAX_PHOTOS - existing.length;
  // skip if remaining<=0; reject file.size > MAX_BYTES; append to array
  ```
- UI: `<input type="file" accept="image/*" multiple>`; show count `(n/3)`; hide
  uploader at 3; render `photos_json.map(...)` gallery with a per-photo remove
  that calls `removePhoto(url)` -> `saveMarker({ photos_json: next })`.
- Report table evidence thumbnail: use `m.photos_json?.[0]`.
- Defect Detail modal: grid of up to 3 photos, each zoomable.

## Pitfalls
- **Client-side limit only.** The R2 upload (`uploadToR2`) does NOT re-check size —
  a crafted client could exceed 200KB. If bulletproof enforcement is needed, add a
  size check in the `r2-presign` Edge Function or a DB constraint/trigger. For
  internal inspector use, client-side is accepted.
- Type `Marker.photos_json: string[]` must be added to `src/lib/types.ts` or the
  build fails on `m.photos_json?.map`.
- Remove ALL legacy `image_url` UI references (sidebar, modal, report) or stale
  LSP "Cannot find name 'attachPhoto'" errors surface after the rename.

## Rebrand note (same session)
Product rebranded SS Rover Cloud → **LunaV Solutions**. Logo = LUNA.png
(transparent, floats on dark UI, no plinth). Footer copy becomes
"Visualising Asset Maintenance — © LunaV Solutions". External link → luna-v.io.
