# Client-side image resize before R2 upload (kill the hard byte cap)

Seen in ss-rover-cloud: users uploaded 3MB phone photos, the app rejected
anything >200KB (`file.size > MAX` → error, skipped). That's the wrong tool —
a hard byte cap just blocks people. Better: downscale in the BROWSER before
the bytes ever leave the tab, so any photo uploads small.

## Helper (drop into the upload lib, e.g. src/lib/r2-upload.ts)

```ts
export async function resizeImage(
  file: File,
  maxDim = 1280,
  quality = 0.8,
): Promise<File> {
  if (!file.type.startsWith("image/")) return file;
  try {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, maxDim / Math.max(bitmap.width, bitmap.height));
    const w = Math.round(bitmap.width * scale);
    const h = Math.round(bitmap.height * scale);
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    if (!ctx) return file;
    ctx.drawImage(bitmap, 0, 0, w, h);
    bitmap.close?.();
    const blob: Blob | null = await new Promise((res) =>
      canvas.toBlob((b) => res(b), "image/jpeg", quality),
    );
    if (!blob) return file;
    const name = file.name.replace(/\.[^.]+$/, "") + ".jpg";
    return new File([blob], name, { type: "image/jpeg" });
  } catch {
    return file; // fall back to original on any decode failure
  }
}
```

## Call sites (ss-rover-cloud ProjectWorkspace.tsx)

- Node photos: keep the 3-photo limit, replace the size rejection with a
  LOOSE raw safety cap (~15MB) so a 200MB RAW can't freeze the tab:
  ```ts
  if (file.size > 15 * 1024 * 1024) { toast("too large (max 15MB original)"); continue; }
  const resized = await resizeImage(file, 1280, 0.8);
  const { publicUrl } = await uploadToR2(resized, initial.projectId, "photo");
  ```
- Proxy textures: `resizeImage(file, 1024, 0.85)` before upload.

## Why this works
- 3MB → ~100–300KB (object-contain display is instant, R2 storage small).
- No backend / Edge Function change; the original bytes never hit the network.
- Display path (`<img src={r2url}>`) is unchanged.

## Pitfalls
- `createImageBitmap` + `canvas.toBlob` are browser-only — do NOT call from
  server components or Node scripts.
- Keep `quality` 0.7–0.85; 0.9+ barely shrinks, 0.6 looks soft.
- maxDim is the LONGEST edge; portrait/landscape both handled by the scale math.
- If you also store the original somewhere (audit), keep a separate path; this
  helper is for the displayed/public copy only.
